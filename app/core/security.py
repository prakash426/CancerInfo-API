"""Administrator access and trusted-peer, shared production request limits."""
import hashlib
import hmac
import math
import time
from ipaddress import ip_address, ip_network
from threading import Lock

from fastapi import Header, Request
from app.core.config import settings
from app.core.errors import UnauthorizedError


def client_address(request: Request) -> str:
    """Walk the proxy chain from the socket peer; never trust a client prefix."""
    peer = request.client.host if request.client else "unknown"
    try:
        address = ip_address(peer)
    except ValueError:
        return peer
    networks = [ip_network(cidr) for cidr in settings.TRUSTED_PROXY_CIDRS]
    trusted = lambda ip: any(ip in network for network in networks)
    if not trusted(address):
        return str(address)
    values = request.headers.getlist("x-forwarded-for")
    # Duplicate, oversized or malformed chains fail closed to the socket peer.
    if len(values) != 1 or len(values[0]) > 1024:
        return str(address)
    chain = values[0].split(",")
    if len(chain) > 16:
        return str(address)
    try:
        chain = [ip_address(item.strip()) for item in chain]
    except ValueError:
        return str(address)
    for hop in reversed(chain):
        if not trusted(address):
            break
        address = hop
    return str(address)


class InMemoryRateLimiter:
    """Bounded, thread-safe sliding window for development only."""
    def __init__(self, requests_per_minute=120, max_clients=10000, clock=time.monotonic):
        self.requests_per_minute = requests_per_minute
        self.max_clients = max_clients
        self.clock = clock
        self.clients = {}
        self.lock = Lock()
        self.next_cleanup = 0

    def check(self, client_ip):
        with self.lock:
            now = self.clock()
            cutoff = now - 60
            if now >= self.next_cleanup:
                self.clients = {k: v for k, v in self.clients.items() if v and v[-1] > cutoff}
                self.next_cleanup = now + 60
            events = [t for t in self.clients.get(client_ip, []) if t > cutoff]
            if not events and client_ip not in self.clients and len(self.clients) >= self.max_clients:
                return False, self.requests_per_minute, 0, 60
            allowed = len(events) < self.requests_per_minute
            if allowed:
                events.append(now)
            self.clients[client_ip] = events
            reset = max(1, math.ceil(events[0] + 60 - now))
            return allowed, self.requests_per_minute, max(0, self.requests_per_minute - len(events)), reset


class PostgresRateLimiter:
    """One sliding window shared by all workers, replicas and process restarts.

    Row locking makes check-and-charge atomic. Keys are hashed IP identities;
    expired buckets are removed in bounded batches without locking busy clients.
    """
    def __init__(self, engine, requests_per_minute=120):
        self.engine = engine
        self.requests_per_minute = requests_per_minute

    def check(self, client_ip):
        from sqlalchemy import select, text, delete
        from sqlalchemy.dialects.postgresql import insert
        from sqlalchemy.orm import Session
        from app.models import RateLimitBucket
        key = hashlib.sha256(client_ip.encode()).hexdigest()
        with Session(self.engine) as db, db.begin():
            db.execute(text("SET LOCAL lock_timeout = '1000ms'"))
            db.execute(text("SET LOCAL statement_timeout = '3000ms'"))
            db.execute(insert(RateLimitBucket).values(id=key, events=[], expires_at=0)
                       .on_conflict_do_update(index_elements=["id"], set_={"id": key}))
            bucket = db.execute(select(RateLimitBucket).where(RateLimitBucket.id == key)
                                .with_for_update()).scalar_one()
            # Time is read after acquiring the lock and comes from the database.
            now = float(db.execute(text("SELECT EXTRACT(EPOCH FROM clock_timestamp())")).scalar_one())
            events = [t for t in bucket.events if t > now - 60]
            allowed = len(events) < self.requests_per_minute
            if allowed:
                events.append(now)
            bucket.events = events
            bucket.expires_at = events[-1] + 60
            reset = max(1, math.ceil(events[0] + 60 - now))
            db.flush()
            expired = (select(RateLimitBucket.id)
                       .where(RateLimitBucket.expires_at <= now, RateLimitBucket.id != key)
                       .order_by(RateLimitBucket.expires_at, RateLimitBucket.id).limit(100)
                       .with_for_update(skip_locked=True))
            db.execute(delete(RateLimitBucket).where(RateLimitBucket.id.in_(expired)),
                       execution_options={"synchronize_session": False})
            return allowed, self.requests_per_minute, max(0, self.requests_per_minute - len(events)), reset


if settings.is_production:
    from app.database.session import engine
    rate_limiter = PostgresRateLimiter(engine, settings.RATE_LIMIT_PER_MINUTE)
else:
    rate_limiter = InMemoryRateLimiter(settings.RATE_LIMIT_PER_MINUTE)


def verify_admin_key(
    x_admin_key: str = Header(None, alias="X-Admin-Key"),
    authorization: str = Header(None, alias="Authorization"),
) -> bool:
    expected = settings.ADMIN_API_KEY
    provided = None
    if x_admin_key:
        provided = x_admin_key.strip()
    elif authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            provided = parts[1].strip()
    if not expected or not provided or not hmac.compare_digest(provided.encode(), expected.encode()):
        raise UnauthorizedError("Valid administrator credentials required for this endpoint.")
    return True
