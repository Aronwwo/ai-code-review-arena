"""File model for storing code files."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.review import Issue


class File(SQLModel, table=True):
    """Code file belonging to a project."""

    __tablename__ = "files"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    name: str = Field(max_length=255)
    content: str = Field(max_length=10_000_000)  # 10MB text limit
    content_hash: str = Field(max_length=64, index=True)  # SHA256 hash
    language: str | None = Field(default=None, max_length=50)
    size_bytes: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    project: Project = Relationship(back_populates="files")
    issues: Issue = Relationship(back_populates="file")

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA256 hash of file content."""
        return hashlib.sha256(content.encode()).hexdigest()


class FileCreate(SQLModel):
    """Schema for creating a file."""

    name: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    language: str | None = Field(default=None, max_length=50)


class FileUpdate(SQLModel):
    """Schema for updating a file."""

    name: str | None = Field(default=None, max_length=255)
    content: str | None = None
    language: str | None = Field(default=None, max_length=50)


class FileRead(SQLModel):
    """Schema for file response."""

    id: int
    project_id: int
    name: str
    language: str | None
    size_bytes: int
    content_hash: str
    created_at: datetime
    updated_at: datetime


class FileReadWithContent(FileRead):
    """Schema for file response with full content."""

    content: str
