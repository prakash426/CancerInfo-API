"""Request-local use approval. Anonymous and unrecognized keys stay commercial."""
from contextvars import ContextVar
import hashlib
import hmac

from app.core.config import settings

publication_use = ContextVar("publication_use", default="COMMERCIAL")


def approved_use(key):
    if not key or len(key) < 32:
        return "COMMERCIAL"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    if any(hmac.compare_digest(digest, expected) for expected in settings.NONCOMMERCIAL_API_KEY_SHA256):
        return "NONCOMMERCIAL"
    return "COMMERCIAL"
