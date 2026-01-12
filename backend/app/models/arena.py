"""Arena session models - system walki dwóch zespołów AI.

Arena to tryb porównywania dwóch konfiguracji zespołów:
- Zespół A: 4 agentów (general, security, performance, style) z wybranymi modelami
- Zespół B: 4 agentów z innymi modelami
- Oba zespoły analizują ten sam kod
- Użytkownik głosuje który zespół dał lepszą odpowiedź
- Na podstawie głosów budowany jest ranking
"""
from datetime import datetime, timezone
from typing import Literal
from sqlmodel import Field, Relationship, SQLModel, Column, JSON

# Typy
ArenaStatus = Literal["pending", "running", "voting", "completed", "failed"]
ArenaWinner = Literal["A", "B", "tie"]


class ArenaSession(SQLModel, table=True):
    """Sesja Arena - pojedyncza walka między dwoma zespołami.

    Przepływ:
    1. pending - sesja utworzona, czeka na uruchomienie
    2. running - oba zespoły analizują kod
    3. voting - analiza zakończona, czeka na głos użytkownika
    4. completed - użytkownik zagłosował
    5. failed - błąd podczas analizy
    """
    __tablename__ = "arena_sessions"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    created_by: int = Field(foreign_key="users.id", index=True)

    # Status sesji
    status: str = Field(default="pending", index=True)
    error_message: str | None = Field(default=None, max_length=2000)

    # Konfiguracje zespołów (JSON z konfiguracją dla każdej roli)
    # Format: {"general": {"provider": "ollama", "model": "qwen2.5"}, "security": {...}, ...}
    team_a_config: dict = Field(default={}, sa_column=Column(JSON))
    team_b_config: dict = Field(default={}, sa_column=Column(JSON))

    # Wyniki zespołów (JSON z podsumowaniem od moderatora)
    team_a_summary: str | None = Field(default=None, max_length=10000)
    team_b_summary: str | None = Field(default=None, max_length=10000)

    # Szczegółowe wyniki (issues znalezione przez każdy zespół)
    team_a_issues: list = Field(default=[], sa_column=Column(JSON))
    team_b_issues: list = Field(default=[], sa_column=Column(JSON))

    # Głosowanie użytkownika
    winner: str | None = Field(default=None, max_length=10)  # "A", "B" lub "tie"
    vote_comment: str | None = Field(default=None, max_length=2000)
    voted_at: datetime | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class TeamRating(SQLModel, table=True):
    """Ranking konfiguracji zespołu na podstawie głosów w Arena.

    Każda unikalna konfiguracja (hash 4 modeli) ma swój rating.
    Rating jest obliczany metodą ELO na podstawie wyników walk.
    """
    __tablename__ = "team_ratings"

    id: int | None = Field(default=None, primary_key=True)

    # Hash konfiguracji (SHA-256 z JSON config)
    config_hash: str = Field(max_length=64, unique=True, index=True)

    # Konfiguracja zespołu (dla wyświetlania)
    config: dict = Field(default={}, sa_column=Column(JSON))

    # Statystyki ELO
    elo_rating: float = Field(default=1500.0)
    games_played: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    ties: int = Field(default=0)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === API Schemas ===

class ArenaSessionCreate(SQLModel):
    """Schema do tworzenia nowej sesji Arena."""
    project_id: int
    team_a_config: dict  # {"general": {"provider": "...", "model": "..."}, ...}
    team_b_config: dict
    api_keys: dict | None = None


class ArenaSessionRead(SQLModel):
    """Schema odpowiedzi dla sesji Arena."""
    id: int
    project_id: int
    created_by: int
    status: str
    error_message: str | None
    team_a_config: dict
    team_b_config: dict
    team_a_summary: str | None
    team_b_summary: str | None
    team_a_issues: list
    team_b_issues: list
    winner: str | None
    vote_comment: str | None
    voted_at: datetime | None
    created_at: datetime
    completed_at: datetime | None


class ArenaVoteCreate(SQLModel):
    """Schema do głosowania w sesji Arena."""
    winner: ArenaWinner  # "A", "B" lub "tie"
    comment: str | None = None


class TeamRatingRead(SQLModel):
    """Schema odpowiedzi dla rankingu zespołu."""
    id: int
    config_hash: str
    config: dict
    elo_rating: float
    games_played: int
    wins: int
    losses: int
    ties: int
    win_rate: float = 0.0
