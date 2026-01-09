"""Database connection and session management."""
from sqlmodel import create_engine, Session, SQLModel
from app.config import settings

# Import all models to ensure they are registered with SQLModel
from app.models.user import User  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.file import File  # noqa: F401
from app.models.review import Review, ReviewAgent, Issue, Suggestion  # noqa: F401
from app.models.conversation import Conversation, Message  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401

# Create engine
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency to get database session."""
    with Session(engine) as session:
        yield session
