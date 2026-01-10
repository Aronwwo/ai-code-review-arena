"""Review, Issue, and Suggestion models."""
from __future__ import annotations

from datetime import datetime, UTC
from typing import TYPE_CHECKING, Literal
from sqlmodel import Field, Relationship, SQLModel, Column, JSON

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project
    from app.models.file import File
    from app.models.conversation import Conversation
    from app.models.arena import ArenaSession


ReviewStatus = Literal["pending", "running", "completed", "failed"]
ReviewMode = Literal["council", "combat_arena"]
ModeratorType = Literal["debate", "consensus", "strategic"]
IssueSeverity = Literal["info", "warning", "error"]
IssueStatus = Literal["open", "confirmed", "dismissed", "resolved"]


class Review(SQLModel, table=True):
    """Code review performed by AI agents.

    Wspiera dwa tryby:
    - Council Mode: Agenci współpracują, jeden zestaw konfiguracji
    - Combat Arena: Review jest częścią porównania dwóch schematów (A vs B)
    """

    __tablename__ = "reviews"

    # Podstawowe pola
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    status: str = Field(default="pending", index=True)
    created_by: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    error_message: str | None = Field(default=None, max_length=2000)

    # Nowe pola dla trybu Arena
    review_mode: str = Field(
        default="council",
        max_length=20,
        index=True,
        description="Tryb review: 'council' (współpraca) lub 'combat_arena' (porównanie)"
    )
    moderator_type: str = Field(
        default="debate",
        max_length=20,
        description="Typ moderatora: 'debate' (Moderator Debaty), 'consensus' (Syntezator), 'strategic' (Strategiczny)"
    )
    arena_schema_name: str | None = Field(
        default=None,
        max_length=1,
        description="Nazwa schematu w Arena: 'A' lub 'B' (tylko dla combat_arena)"
    )
    arena_session_id: int | None = Field(
        default=None,
        foreign_key="arena_sessions.id",
        index=True,
        description="ID sesji Arena (tylko dla combat_arena)"
    )

    # Relationships
    project: Project = Relationship(back_populates="reviews")
    created_by_user: User = Relationship(back_populates="reviews")
    agents: ReviewAgent = Relationship(back_populates="review")
    issues: Issue = Relationship(back_populates="review")
    conversations: Conversation = Relationship(back_populates="review")
    # arena_session_id jest foreign key, ale nie definiujemy Relationship
    # aby uniknąć circular import issues (ArenaSession -> Review -> ArenaSession)


class ReviewAgent(SQLModel, table=True):
    """Agent that participated in a review."""

    __tablename__ = "review_agents"

    id: int | None = Field(default=None, primary_key=True)
    review_id: int = Field(foreign_key="reviews.id", index=True)
    role: str = Field(max_length=50)  # general, security, performance, style
    provider: str = Field(max_length=50)  # groq, gemini, ollama, mock
    model: str = Field(max_length=100)
    raw_output: str | None = Field(default=None, max_length=50_000)
    parsed_successfully: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    review: Review = Relationship(back_populates="agents")


class Issue(SQLModel, table=True):
    """Issue found during code review."""

    __tablename__ = "issues"

    id: int | None = Field(default=None, primary_key=True)
    review_id: int = Field(foreign_key="reviews.id", index=True)
    file_id: int | None = Field(default=None, foreign_key="files.id", index=True)

    severity: str = Field(default="info", index=True)
    category: str = Field(max_length=100, index=True)  # security, performance, style, etc.
    title: str = Field(max_length=500)
    description: str = Field(max_length=5000)

    # Location information
    file_name: str | None = Field(default=None, max_length=255)
    line_start: int | None = None
    line_end: int | None = None

    # Status tracking
    status: str = Field(default="open", index=True)
    confirmed: bool = Field(default=False)  # Set by arena verdict
    final_severity: str | None = None  # Updated by arena
    moderator_comment: str | None = Field(default=None, max_length=2000)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    review: Review = Relationship(back_populates="issues")
    file: File = Relationship(back_populates="issues")
    suggestions: Suggestion = Relationship(back_populates="issue")


class Suggestion(SQLModel, table=True):
    """Suggested fix for an issue."""

    __tablename__ = "suggestions"

    id: int | None = Field(default=None, primary_key=True)
    issue_id: int = Field(foreign_key="issues.id", index=True)
    suggested_code: str | None = Field(default=None, max_length=10_000)
    explanation: str = Field(max_length=2000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    issue: Issue = Relationship(back_populates="suggestions")


# API Schemas

class CustomProviderConfig(SQLModel):
    """Configuration for a custom provider."""

    id: str
    name: str
    base_url: str
    api_key: str | None = None
    header_name: str | None = "Authorization"
    header_prefix: str | None = "Bearer "


class AgentConfig(SQLModel):
    """Configuration for a single agent."""

    provider: str
    model: str
    prompt: str
    temperature: float = 0.2
    max_tokens: int = 2048
    # For custom providers
    custom_provider: CustomProviderConfig | None = None


class ReviewCreate(SQLModel):
    """Schema for creating a review.

    Wspiera dwa tryby:
    1. Council Mode (review_mode='council'):
       - Użyj agent_roles + agent_configs
       - Agenci współpracują nad jednym review

    2. Combat Arena (review_mode='combat_arena'):
       - Użyj arena_config_a + arena_config_b
       - Tworzy dwa osobne review do porównania
       - Każdy schemat musi mieć wszystkie 4 role
    """

    # Wybór trybu
    review_mode: ReviewMode = Field(
        ...,
        description="Tryb review: 'council' (współpraca) lub 'combat_arena' (porównanie A vs B)"
    )
    moderator_type: ModeratorType = Field(
        ...,
        description="Typ moderatora: 'debate' (Moderator Debaty), 'consensus' (Syntezator Konsensusu), 'strategic' (Strategiczny Koordynator)"
    )

    # === COUNCIL MODE ===
    agent_roles: list[str] = Field(
        default=["general"],
        description="Role agentów dla Council Mode (general, security, performance, style)"
    )
    provider: str | None = Field(
        default=None,
        description="(Deprecated) Global provider - użyj agent_configs zamiast tego"
    )
    model: str | None = Field(
        default=None,
        description="(Deprecated) Global model - użyj agent_configs zamiast tego"
    )
    agent_configs: dict[str, AgentConfig] | None = Field(
        default=None,
        description="Konfiguracja per agent dla Council Mode: {role: config}"
    )

    moderator_config: AgentConfig | None = Field(
        default=None,
        description="Konfiguracja moderatora dla Council Mode"
    )

    # === COMBAT ARENA ===
    arena_config_a: dict[str, AgentConfig] | None = Field(
        default=None,
        description="Schemat A dla Arena: musi zawierać wszystkie 4 role {general, security, performance, style}"
    )
    arena_config_b: dict[str, AgentConfig] | None = Field(
        default=None,
        description="Schemat B dla Arena: musi zawierać wszystkie 4 role {general, security, performance, style}"
    )

    # === WSPÓLNE ===
    api_keys: dict[str, str] | None = Field(
        default=None,
        description="Klucze API dla providerów: {provider_name: api_key}"
    )

    # Pole conversation_mode zachowane dla kompatybilności wstecznej (DEPRECATED)
    conversation_mode: str | None = Field(
        default=None,
        description="(Deprecated) Użyj review_mode zamiast tego"
    )


class ReviewRead(SQLModel):
    """Schema for review response."""

    id: int
    project_id: int
    status: ReviewStatus
    created_by: int
    created_at: datetime
    completed_at: datetime | None
    error_message: str | None
    agent_count: int = 0
    issue_count: int = 0

    # Nowe pola dla Arena
    review_mode: ReviewMode = "council"
    moderator_type: ModeratorType = "debate"
    arena_schema_name: str | None = None
    arena_session_id: int | None = None


class ReviewAgentRead(SQLModel):
    """Schema for review agent response."""

    id: int
    review_id: int
    role: str
    provider: str
    model: str
    parsed_successfully: bool
    created_at: datetime


class IssueRead(SQLModel):
    """Schema for issue response."""

    id: int
    review_id: int
    file_id: int | None
    severity: IssueSeverity
    category: str
    title: str
    description: str
    file_name: str | None
    line_start: int | None
    line_end: int | None
    status: IssueStatus
    confirmed: bool
    final_severity: IssueSeverity | None
    moderator_comment: str | None
    created_at: datetime
    updated_at: datetime
    suggestion_count: int = 0


class SuggestionRead(SQLModel):
    """Schema for suggestion response."""

    id: int
    issue_id: int
    suggested_code: str | None
    explanation: str
    created_at: datetime


class IssueReadWithSuggestions(IssueRead):
    """Schema for issue response with suggestions."""

    suggestions: list[SuggestionRead] = []


class IssueUpdate(SQLModel):
    """Schema for updating an issue."""

    status: IssueStatus | None = None
    confirmed: bool | None = None
    final_severity: IssueSeverity | None = None
    moderator_comment: str | None = None
