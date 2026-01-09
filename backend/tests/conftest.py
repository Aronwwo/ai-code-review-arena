"""Shared test fixtures and configuration."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
from app.main import app
from app.database import get_session
from app.config import settings


@pytest.fixture(name="test_engine")
def test_engine_fixture():
    """Create test database engine."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="test_session")
def test_session_fixture(test_engine):
    """Create test database session."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(test_engine):
    """Create test client with test database."""
    # Disable rate limiting for tests
    original_rate_limit_enabled = settings.rate_limit_enabled
    settings.rate_limit_enabled = False

    def get_test_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session

    # Create TestClient without context manager to avoid lifespan issues
    client = TestClient(app, raise_server_exceptions=True)
    yield client
    client.close()

    app.dependency_overrides.clear()

    # Restore original rate limit setting
    settings.rate_limit_enabled = original_rate_limit_enabled


@pytest.fixture(autouse=True)
def setup_test_database(test_engine):
    """Setup and teardown test database for each test."""
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)
