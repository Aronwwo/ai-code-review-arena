"""Project model."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.file import File as FileModel
    from app.models.review import Review


class Project(SQLModel, table=True):
    """Project containing code files."""

    __tablename__ = "projects"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, index=True)
    description: str | None = Field(default=None, max_length=2000)
    owner_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    owner: User = Relationship(back_populates="projects")
    files: File = Relationship(back_populates="project")
    reviews: Review = Relationship(back_populates="project")


class ProjectCreate(SQLModel):
    """Schema for creating a project."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class ProjectUpdate(SQLModel):
    """Schema for updating a project."""

    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class ProjectRead(SQLModel):
    """Schema for project response."""

    id: int
    name: str
    description: str | None
    owner_id: int
    created_at: datetime
    updated_at: datetime
    file_count: int = 0
    review_count: int = 0
