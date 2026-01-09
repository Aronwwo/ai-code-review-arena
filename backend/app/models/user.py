"""User model for authentication and authorization."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel
from pydantic import EmailStr

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.review import Review


class User(SQLModel, table=True):
    """User account."""

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    username: str = Field(unique=True, index=True, max_length=100)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships (with from __future__ import annotations, no quotes needed)
    projects: Project = Relationship(back_populates="owner")
    reviews: Review = Relationship(back_populates="created_by_user")


class UserCreate(SQLModel):
    """Schema for user registration."""

    email: EmailStr  # Validates email format automatically
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=100)


class UserLogin(SQLModel):
    """Schema for user login."""

    email: EmailStr  # Validates email format automatically
    password: str


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
