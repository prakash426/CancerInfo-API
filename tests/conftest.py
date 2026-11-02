"""
Pytest Test Configuration and Fixtures
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from app.core.security import rate_limiter
from app.database.session import Base, get_db
from app.ingestion.seed import seed_database
from app.main import app


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.clients.clear()
    yield
    rate_limiter.clients.clear()


# In-memory SQLite for fast, isolated tests
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_database(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def public_seed_evidence(db_session):
    """Explicit disposable reviews for legacy API behavior tests only.

    The real seed rights are not changed. Closing the test session rolls these
    test-only decisions back; rights tests use unmodified seed decisions.
    """
    from app.models import SourceDocument
    from publication_support import approve_test_document
    for doc in db_session.query(SourceDocument):
        approve_test_document(doc)
    db_session.flush()
    yield
    db_session.rollback()
