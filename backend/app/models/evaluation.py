"""Model Duel evaluation models."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from sqlmodel import Field, Relationship, SQLModel, Column, JSON

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project

EvaluationStatus = Literal["pending", "in_progress", "completed", "cancelled"]
VoteChoice = Literal["candidate_a", "candidate_b", "tie"]


class EvaluationSession(SQLModel, table=True):
    """Evaluation session comparing two model configurations."""

    __tablename__ = "evaluation_sessions"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    created_by: int = Field(foreign_key="users.id", index=True)
    status: str = Field(default="pending", index=True)

    # Session config
    num_rounds: int = Field(default=5)
    current_round: int = Field(default=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    # Relationships
    project: Project = Relationship()
    created_by_user: User = Relationship()
    candidates: list[EvaluationCandidate] = Relationship(back_populates="session")
    votes: list[EvaluationVote] = Relationship(back_populates="session")


class EvaluationCandidate(SQLModel, table=True):
    """Model configuration being evaluated in a session."""

    __tablename__ = "evaluation_candidates"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="evaluation_sessions.id", index=True)

    # Which candidate (A or B)
    position: str = Field(max_length=1)  # "A" or "B"

    # Model configuration
    provider: str = Field(max_length=50)
    model: str = Field(max_length=100)
    agent_role: str = Field(max_length=50)  # general, security, performance, style

    # Custom provider config (JSON)
    custom_provider_config: dict | None = Field(default=None, sa_column=Column(JSON))

    # Results from review
    review_id: int | None = Field(default=None, foreign_key="reviews.id", index=True)
    issues_found: int = Field(default=0)
    raw_output: str | None = Field(default=None, max_length=50_000)
    parsed_successfully: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    session: EvaluationSession = Relationship(back_populates="candidates")


class EvaluationVote(SQLModel, table=True):
    """Vote in an evaluation session."""

    __tablename__ = "evaluation_votes"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="evaluation_sessions.id", index=True)
    round_number: int = Field(index=True)

    # Vote choice
    choice: str = Field(max_length=20)  # "candidate_a", "candidate_b", "tie"
    comment: str | None = Field(default=None, max_length=2000)

    # Voter info
    voter_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    session: EvaluationSession = Relationship(back_populates="votes")
    voter: User = Relationship()


class RatingConfig(SQLModel, table=True):
    """ELO rating for a specific configuration (provider + model + role)."""

    __tablename__ = "rating_configs"

    id: int | None = Field(default=None, primary_key=True)

    # Configuration identity
    provider: str = Field(max_length=50, index=True)
    model: str = Field(max_length=100, index=True)
    agent_role: str = Field(max_length=50, index=True)

    # Rating
    elo_rating: float = Field(default=1500.0)
    games_played: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    ties: int = Field(default=0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RatingModel(SQLModel, table=True):
    """Aggregate ELO rating for a model across all roles."""

    __tablename__ = "rating_models"

    id: int | None = Field(default=None, primary_key=True)

    # Model identity
    provider: str = Field(max_length=50, index=True)
    model: str = Field(max_length=100, index=True)

    # Aggregate rating (average across roles)
    elo_rating: float = Field(default=1500.0)
    games_played: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    ties: int = Field(default=0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# API Schemas

class EvaluationSessionCreate(SQLModel):
    """Schema for creating an evaluation session."""

    project_id: int
    num_rounds: int = Field(default=5, ge=1, le=20)

    # Candidate A configuration
    candidate_a_provider: str
    candidate_a_model: str
    candidate_a_role: str
    candidate_a_custom_config: dict | None = None

    # Candidate B configuration
    candidate_b_provider: str
    candidate_b_model: str
    candidate_b_role: str
    candidate_b_custom_config: dict | None = None

    # API keys for providers
    api_keys: dict[str, str] | None = None


class EvaluationSessionRead(SQLModel):
    """Schema for evaluation session response."""

    id: int
    project_id: int
    created_by: int
    status: EvaluationStatus
    num_rounds: int
    current_round: int
    created_at: datetime
    completed_at: datetime | None


class EvaluationCandidateRead(SQLModel):
    """Schema for evaluation candidate response."""

    id: int
    session_id: int
    position: str
    provider: str
    model: str
    agent_role: str
    custom_provider_config: dict | None
    review_id: int | None
    issues_found: int
    parsed_successfully: bool
    created_at: datetime


class EvaluationVoteCreate(SQLModel):
    """Schema for creating a vote."""

    choice: VoteChoice
    comment: str | None = Field(default=None, max_length=2000)


class EvaluationVoteRead(SQLModel):
    """Schema for vote response."""

    id: int
    session_id: int
    round_number: int
    choice: VoteChoice
    comment: str | None
    voter_id: int
    created_at: datetime


class RatingConfigRead(SQLModel):
    """Schema for rating config response."""

    id: int
    provider: str
    model: str
    agent_role: str
    elo_rating: float
    games_played: int
    wins: int
    losses: int
    ties: int
    created_at: datetime
    updated_at: datetime


class RatingModelRead(SQLModel):
    """Schema for rating model response."""

    id: int
    provider: str
    model: str
    elo_rating: float
    games_played: int
    wins: int
    losses: int
    ties: int
    created_at: datetime
    updated_at: datetime


class EvaluationSessionWithCandidates(EvaluationSessionRead):
    """Schema for evaluation session with candidates."""

    candidates: list[EvaluationCandidateRead] = []
    votes: list[EvaluationVoteRead] = []
