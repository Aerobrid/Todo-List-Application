import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from typing import Generator

# SQLite in-memory engine combined with StaticPool keeps the schema cached
# and accessible inside a single connection state across unit/integration tests
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="db_session", scope="function")
def db_session_fixture() -> Generator[Session, None, None]:
    """
    Creates and drops schemas automatically for each unit test.
    Ensures isolated state transitions for database queries.
    """
    Base.metadata.create_all(bind=engine)
    session: Session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="client", scope="function")
def client_fixture(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Overrides the FastAPI dependency injector to redirect DB transactions
    to the temporary testing session instead of the local tasks.db.
    """
    def _override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
        
    # clear overridden dependencies to avoid test leaking into other modules
    app.dependency_overrides.clear()
