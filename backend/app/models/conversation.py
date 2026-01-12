"""Conversation and Message models for agent discussions."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal
from sqlmodel import Field, Relationship, SQLModel, Column, JSON

if TYPE_CHECKING:
    from app.models.review import Review


ConversationMode = Literal["cooperative", "adversarial", "council", "arena"]
ConversationStatus = Literal["pending", "running", "completed", "failed"]
TopicType = Literal["project", "file", "issue", "review"]
SenderType = Literal["agent", "user", "moderator"]


class Conversation(SQLModel, table=True):
    """Agent conversation (council or arena mode)."""

    __tablename__ = "conversations"

    id: int | None = Field(default=None, primary_key=True)
    review_id: int = Field(foreign_key="reviews.id", index=True)
    mode: str = Field(index=True)
    topic_type: str = Field(index=True)
    topic_id: int | None = None  # project_id, file_id, or issue_id
    status: str = Field(default="pending", index=True)
    summary: str | None = Field(default=None, max_length=10_000)
    meta_info: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    # Relationships
    review: Review = Relationship(back_populates="conversations")
    messages: Message = Relationship(back_populates="conversation")


class Message(SQLModel, table=True):
    """Message in a conversation."""

    __tablename__ = "messages"

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    sender_type: str = Field(index=True)
    sender_name: str = Field(max_length=100)  # agent role or username
    turn_index: int = Field(default=0, index=True)
    content: str = Field(max_length=20_000)
    is_summary: bool = Field(default=False)  # True for moderator summary messages
    meta_info: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    conversation: Conversation = Relationship(back_populates="messages")


# API Schemas

class ConversationCreate(SQLModel):
    """Schema for creating a conversation."""

    mode: ConversationMode
    topic_type: TopicType
    topic_id: int | None = None
    provider: str | None = None
    model: str | None = None


class ConversationRead(SQLModel):
    """Schema for conversation response."""

    id: int
    review_id: int
    mode: ConversationMode
    topic_type: TopicType
    topic_id: int | None
    status: ConversationStatus
    summary: str | None
    created_at: datetime
    completed_at: datetime | None
    message_count: int = 0


class MessageRead(SQLModel):
    """Schema for message response."""

    id: int
    conversation_id: int
    sender_type: SenderType
    sender_name: str
    turn_index: int
    content: str
    is_summary: bool
    created_at: datetime


class DebateIssueRequest(SQLModel):
    """Schema for starting an adversarial debate on an issue."""

    provider: str | None = None
    model: str | None = None
