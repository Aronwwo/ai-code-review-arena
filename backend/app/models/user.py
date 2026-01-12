"""User model for authentication and authorization."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import re
from sqlmodel import Field, Relationship, SQLModel
from pydantic import field_validator

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.review import Review


def validate_email_format(email: str) -> str:
    """Validate email format and normalize to lowercase.

    Accepts .test and .local TLDs for development environments.

    Args:
        email: Email address to validate

    Returns:
        Normalized (lowercase) email address

    Raises:
        ValueError: If email format is invalid
    """
    if not email or '@' not in email:
        raise ValueError('nieprawidłowy format email')

    # Basic email regex that accepts .test and .local TLDs
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email.lower()):
        raise ValueError('nieprawidłowy format email')

    return email.lower()


class User(SQLModel, table=True):
    """User account."""

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    username: str = Field(unique=True, index=True, max_length=100)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships (with from __future__ import annotations, no quotes needed)
    projects: Project = Relationship(back_populates="owner")
    reviews: Review = Relationship(back_populates="created_by_user")


class UserCreate(SQLModel):
    """Schema for user registration."""

    email: str = Field(max_length=255)
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=100)

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format using shared validation function."""
        return validate_email_format(v)


class UserLogin(SQLModel):
    """Schema for user login."""

    email: str = Field(max_length=255)
    password: str

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format using shared validation function."""
        return validate_email_format(v)


class UserRead(SQLModel):
    """Schema for user response (without password)."""

    id: int
    email: str
    username: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class Token(SQLModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenWithRefresh(SQLModel):
    """JWT token response with refresh token."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(SQLModel):
    """Request to refresh access token."""

    refresh_token: str


class TokenData(SQLModel):
    """Data stored in JWT token."""

    user_id: int
    email: str


class PasswordChange(SQLModel):
    """Schema for password change request."""

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=100)
