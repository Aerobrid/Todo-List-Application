from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from app.models import Base

DATABASE_URL = "sqlite:///./tasks.db"

# connect_args is needed for SQLite to run across multiple threads safely in async/await frameworks
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# SQLite by default disables foreign key enforcement for backward compatibility,
# and operates in rollback journal mode which locks the DB file during write operations.
# Setting these PRAGMAs ensures cascade deletes work and increases concurrent performance via WAL.
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    """
    Dependency generator that provides a transactional database session for requests.
    Guarantees session teardown and rollback in case of uncaught request exceptions.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """
    Creates database tables if they do not exist. In production settings,
    this would typically be managed by migrations (e.g. Alembic), but for 
    ephemeral/scaffolded environments, inline Base creation provides immediate startup.
    """
    Base.metadata.create_all(bind=engine)
