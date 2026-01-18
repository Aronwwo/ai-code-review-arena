"""Review, Issue, and Suggestion models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal
from sqlmodel import Field, Relationship, SQLModel, Column, JSON

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project
    from app.models.file import File
    from app.models.conversation import Conversation


ReviewStatus = Literal["pending", "running", "completed", "failed"]
ReviewMode = Literal["council", "arena"]
IssueSeverity = Literal["info", "warning", "error"]
IssueStatus = Literal["open", "confirmed", "dismissed", "resolved"]


class Review(SQLModel, table=True):
    """Code review performed by AI agents.

    Review wykonywany przez pojedynczego agenta.
    """

    __tablename__ = "reviews"

    # Podstawowe pola
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    status: str = Field(default="pending", index=True)
    created_by: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    error_message: str | None = Field(default=None, max_length=2000)

    # Pola konfiguracji review
    review_mode: str = Field(
        default="council",
        max_length=20,
        index=True,
        description="Tryb review: 'council' (narada)"
    )
    # Podsumowanie moderatora (końcowy raport)
    summary: str | None = Field(default=None, max_length=50_000)

    # Relationships
    project: Project = Relationship(back_populates="reviews")
    created_by_user: User = Relationship(back_populates="reviews")
    agents: ReviewAgent = Relationship(back_populates="review")
    issues: Issue = Relationship(back_populates="review")
    conversations: Conversation = Relationship(back_populates="review")


class ReviewAgent(SQLModel, table=True):
    """Agent that participated in a review."""

    __tablename__ = "review_agents"

    id: int | None = Field(default=None, primary_key=True)
    review_id: int = Field(foreign_key="reviews.id", index=True)
    role: str = Field(max_length=50)  # general
    provider: str = Field(max_length=50)  # groq, gemini, ollama, mock
    model: str = Field(max_length=100)
    raw_output: str | None = Field(default=None, max_length=50_000)
    parsed_successfully: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Timeout handling
    timed_out: bool = Field(default=False, description="Czy agent przekroczył timeout")
    timeout_seconds: int | None = Field(default=None, description="Ustawiony timeout w sekundach")

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
    
    # Agent information - który agent znalazł ten problem
    agent_role: str | None = Field(default=None, max_length=50, index=True)  # general

    # Location information
    file_name: str | None = Field(default=None, max_length=255)
    line_start: int | None = None
    line_end: int | None = None

    # Status tracking
    status: str = Field(default="open", index=True)
    confirmed: bool = Field(default=False)  # Set by arena verdict
    final_severity: str | None = None  # Updated by arena
    moderator_comment: str | None = Field(default=None, max_length=2000)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    prompt: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4096  # Zwiększono z 2048 aby agenci mogli generować pełniejsze odpowiedzi
    timeout_seconds: int = 300  # Domyślnie 5 minut (zwiększono z 180s aby uniknąć timeoutów)
    # For custom providers
    custom_provider: CustomProviderConfig | None = None


class ReviewCreate(SQLModel):
    """Schema do tworzenia nowego review.

    Review wykonywany przez pojedynczego agenta.

    Wymagane pola:
    - review_mode: 'council' lub 'arena'
    - agent_roles: lista ról agentów (np. ['general', 'security'])
    - agent_configs: konfiguracja dla każdej roli (z timeout_seconds)
    """
    # Wybór trybu review
    review_mode: ReviewMode = Field(
        ...,
        description="Tryb review: 'council' (narada)"
    )

    # Konfiguracja agentów
    agent_roles: list[str] = Field(
        default=["general"],
        description="Role agentów: general"
    )
    agent_configs: dict[str, AgentConfig] | None = Field(
        default=None,
        description="Konfiguracja per agent: {role: AgentConfig}"
    )

    # Klucze API
    api_keys: dict[str, str] | None = Field(
        default=None,
        description="Klucze API: {provider_name: api_key}"
    )

    # Deprecated - zachowane dla kompatybilności
    provider: str | None = Field(default=None, description="(Deprecated)")
    model: str | None = Field(default=None, description="(Deprecated)")

    # Moderator (optional, used by council workflows)
    moderator_type: str | None = Field(default=None, description="Typ moderatora (np. debate, consensus, strategic)")
    moderator_config: AgentConfig | None = Field(default=None, description="Konfiguracja moderatora")


class ReviewRead(SQLModel):
    """Schema for review response.

    Zawiera podstawowe informacje o review oraz liczniki agentów i problemów.
    """
    id: int
    project_id: int
    status: ReviewStatus
    created_by: int
    created_at: datetime
    completed_at: datetime | None
    error_message: str | None
    agent_count: int = 0
    issue_count: int = 0
    review_mode: ReviewMode = "council"
    summary: str | None = None
    # Model information - list of unique provider/model combinations used by agents
    models: list[str] | None = None  # List of provider/model combinations (e.g., ['gemini/gemini-2.5-flash', 'groq/llama3'])


class ReviewAgentRead(SQLModel):
    """Schema for review agent response."""

    id: int
    review_id: int
    role: str
    provider: str
    model: str
    parsed_successfully: bool
    timed_out: bool = False
    timeout_seconds: int | None = None
    raw_output: str | None = None  # Odpowiedź agenta
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
    agent_role: str | None = None  # Which agent found this issue (general, security, performance, style)
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
