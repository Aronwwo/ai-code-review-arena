"""Modele dla Combat Arena - porównywanie pełnych schematów review.

Combat Arena pozwala użytkownikowi porównać dwa kompletne schematy konfiguracji review
(Schemat A vs Schemat B), gdzie każdy schemat ma pełną konfigurację dla wszystkich 4 ról:
- general (ogólna jakość kodu)
- security (bezpieczeństwo)
- performance (wydajność)
- style (styl i konwencje)

System ocenia który schemat jest lepszy i aktualizuje rankingi ELO.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal
from sqlmodel import Field, Relationship, SQLModel, Column, JSON
from sqlalchemy import ForeignKey, Integer

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project
    from app.models.review import Review

# Typy dla walidacji
ArenaStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
ArenaWinner = Literal["A", "B", "tie"]


class ArenaSession(SQLModel, table=True):
    """Sesja Arena porównująca dwie pełne konfiguracje review.

    Arena Session tworzy dwa osobne review (A i B), każdy z pełną konfiguracją
    dla wszystkich 4 ról. Po zakończeniu użytkownik głosuje który lepszy,
    a wyniki trafiają do rankingów ELO.
    """

    __tablename__ = "arena_sessions"

    # Podstawowe pola
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    created_by: int = Field(foreign_key="users.id", index=True)
    status: str = Field(default="pending", index=True)  # pending, running, completed, failed

    # Konfiguracje schematów (JSON)
    # Struktura: {"general": {"provider": "groq", "model": "...", ...}, "security": {...}, ...}
    schema_a_config: dict = Field(sa_column=Column(JSON), description="Pełna konfiguracja Schematu A")
    schema_b_config: dict = Field(sa_column=Column(JSON), description="Pełna konfiguracja Schematu B")

    # ID review utworzonych dla każdego schematu
    review_a_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("reviews.id", use_alter=True, name="fk_arena_review_a"),
            index=True
        )
    )
    review_b_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("reviews.id", use_alter=True, name="fk_arena_review_b"),
            index=True
        )
    )

    # Wynik głosowania
    winner: str | None = None  # "A", "B", "tie"
    vote_comment: str | None = Field(default=None, max_length=2000)
    voter_id: int | None = Field(default=None, foreign_key="users.id")
    voted_at: datetime | None = None

    # Metadane
    error_message: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    # Relationships
    # Trzeba określić foreign_keys dla wielokrotnych relacji do User
    project: Project = Relationship()
    created_by_user: User = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ArenaSession.created_by]"}
    )
    voter: User = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ArenaSession.voter_id]"}
    )
    # Relacje do Review - również trzeba określić foreign_keys
    review_a: Review = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ArenaSession.review_a_id]"}
    )
    review_b: Review = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ArenaSession.review_b_id]"}
    )


class SchemaRating(SQLModel, table=True):
    """Ranking ELO dla pełnych schematów konfiguracji review.

    Przechowuje rating dla konkretnej kombinacji konfiguracji wszystkich 4 ról.
    Schemat identyfikowany przez hash konfiguracji.
    """

    __tablename__ = "schema_ratings"

    id: int | None = Field(default=None, primary_key=True)

    # Identyfikator schematu (SHA-256 hash posortowanej konfiguracji JSON)
    schema_hash: str = Field(max_length=64, unique=True, index=True)
    schema_config: dict = Field(sa_column=Column(JSON), description="Pełna konfiguracja schematu")

    # Ranking ELO (start: 1500)
    elo_rating: float = Field(default=1500.0, description="Aktualny rating ELO")
    games_played: int = Field(default=0, description="Liczba rozegranych pojedynków")
    wins: int = Field(default=0, description="Liczba wygranych")
    losses: int = Field(default=0, description="Liczba przegranych")
    ties: int = Field(default=0, description="Liczba remisów")

    # Statystyki (opcjonalne)
    avg_issues_found: float | None = None  # Średnia liczba znalezionych issues
    last_used_at: datetime | None = None  # Kiedy ostatnio użyty

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== API Schemas ====================

class ArenaSessionCreate(SQLModel):
    """Schema do tworzenia nowej sesji Arena."""

    project_id: int = Field(description="ID projektu do przeanalizowania")

    # Schemat A - pełna konfiguracja wszystkich 4 ról
    schema_a_config: dict[str, dict] = Field(
        description="Konfiguracja Schematu A. Klucze: general, security, performance, style"
    )

    # Schemat B - pełna konfiguracja wszystkich 4 ról
    schema_b_config: dict[str, dict] = Field(
        description="Konfiguracja Schematu B. Klucze: general, security, performance, style"
    )

    # API keys dla providerów (opcjonalne)
    api_keys: dict[str, str] | None = Field(
        default=None,
        description="Klucze API dla providerów (np. {'openai': 'sk-...', 'anthropic': 'sk-ant-...'})"
    )


class ArenaVoteCreate(SQLModel):
    """Schema do głosowania w sesji Arena."""

    winner: ArenaWinner = Field(description="Zwycięzca: A, B lub tie (remis)")
    comment: str | None = Field(
        default=None,
        max_length=2000,
        description="Opcjonalny komentarz (dlaczego ten schemat jest lepszy?)"
    )


class ArenaSessionRead(SQLModel):
    """Schema odpowiedzi z danymi sesji Arena."""

    id: int
    project_id: int
    created_by: int
    status: ArenaStatus
    schema_a_config: dict
    schema_b_config: dict
    review_a_id: int | None
    review_b_id: int | None
    winner: ArenaWinner | None
    vote_comment: str | None
    voter_id: int | None
    voted_at: datetime | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class SchemaRatingRead(SQLModel):
    """Schema odpowiedzi z rankingiem schematu."""

    id: int
    schema_hash: str
    schema_config: dict
    elo_rating: float
    games_played: int
    wins: int
    losses: int
    ties: int
    avg_issues_found: float | None
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime
