"""Database connection and session management.

Ten plik zarządza połączeniem z bazą danych i sesjami. Używa:
- SQLModel (Pydantic + SQLAlchemy) - ORM dla typowania i validacji
- SQLite dla development (plik: data/code_review.db)
- PostgreSQL możliwy dla production (zmień DATABASE_URL w .env)

Architektura:
1. Engine - główne połączenie z bazą danych (singleton)
2. Session - pojedyncza transakcja (per request)
3. Models - definicje tabel (SQLModel classes)
"""

# ==================== IMPORTS ====================
from sqlmodel import create_engine, Session, SQLModel
from app.config import settings

# ==================== MODEL IMPORTS ====================
# WAŻNE: Musimy zaimportować WSZYSTKIE modele tutaj, żeby SQLModel
# wiedział o nich przy tworzeniu tabel (metadata.create_all)
# noqa: F401 = ignoruj warning "imported but unused" (bo używane są przez SQLModel)

from app.models.user import User  # noqa: F401 - Tabela: users
from app.models.project import Project  # noqa: F401 - Tabela: projects
from app.models.file import File  # noqa: F401 - Tabela: files
from app.models.review import Review, ReviewAgent, Issue, Suggestion  # noqa: F401 - Tabele: reviews, review_agents, issues, suggestions
from app.models.conversation import Conversation, Message  # noqa: F401 - Tabele: conversations, messages
from app.models.audit import AuditLog  # noqa: F401 - Tabela: audit_logs

# ==================== DATABASE ENGINE ====================
# Engine - globalna instancja połączenia z bazą danych
# To jest SINGLETON - tworzona raz przy starcie aplikacji
engine = create_engine(
    settings.database_url,  # Z .env: sqlite:///./data/code_review.db
    echo=settings.debug,  # Jeśli debug=True, wypisuje wszystkie SQL queries do konsoli
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
    # SQLite wymaga check_same_thread=False dla FastAPI (multi-threading)
    # PostgreSQL nie potrzebuje tego parametru
)


# ==================== TABLE CREATION ====================
def create_db_and_tables():
    """Create all database tables if they don't exist.

    Wywołane przy starcie aplikacji (main.py lifespan).

    Tworzy tabele na podstawie wszystkich zaimportowanych modeli:
    - users (User model)
    - projects (Project model)
    - files (File model)
    - reviews (Review model)
    - review_agents (ReviewAgent model)
    - issues (Issue model)
    - suggestions (Suggestion model)
    - conversations (Conversation model)
    - messages (Message model)
    - audit_logs (AuditLog model)

    Używa SQLModel.metadata - rejestr wszystkich modeli SQLModel.
    """
    SQLModel.metadata.create_all(engine)  # CREATE TABLE IF NOT EXISTS


# ==================== SESSION DEPENDENCY ====================
def get_session():
    """Dependency to get database session.

    FastAPI Depends() injection pattern - każdy endpoint dostaje swoją sesję.

    Przykład użycia:
        @app.get("/projects")
        def list_projects(session: Session = Depends(get_session)):
            projects = session.exec(select(Project)).all()
            return projects

    Lifecycle:
    1. Request przychodzi → nowa session się tworzy
    2. Endpoint wykonuje operacje na session
    3. Response wraca → session automatycznie się zamyka (with context manager)

    Korzyści:
    - Automatyczne zarządzanie transakcjami
    - Auto-commit przy sukcesie
    - Auto-rollback przy błędzie
    - Brak memory leaks (zawsze zamyka połączenie)

    Yields:
        Session: Bieżąca sesja bazodanowa
    """
    with Session(engine) as session:
        yield session  # Endpoint dostaje session tutaj
        # Po yield - session automatycznie się zamyka (cleanup)
