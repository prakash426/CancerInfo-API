"""
Database Engine & Session Management
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

connect_args = {}
engine_kwargs = {}

if settings.is_sqlite:
    connect_args["check_same_thread"] = False
else:
    connect_args.update(connect_timeout=settings.DB_CONNECT_TIMEOUT,
                        options=f"-c statement_timeout={settings.DB_STATEMENT_TIMEOUT_MS}",
                        keepalives=1, keepalives_idle=30,
                        keepalives_interval=10, keepalives_count=5)
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
    engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

# Request accounting runs on a small dedicated pool so limiter checkouts can
# never starve the business pool (and vice versa) under load. SQLite keeps a
# single shared engine; the in-memory limiter uses no connections there.
if settings.is_sqlite:
    limiter_engine = None
else:
    limiter_engine = create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=2,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for database session management"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
