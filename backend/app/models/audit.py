"""Audit log model for tracking user actions."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from sqlmodel import Field, SQLModel


class AuditAction(str, Enum):
    """Types of auditable actions."""
    # Auth actions
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    TOKEN_REFRESH = "token_refresh"

    # Project actions
    PROJECT_CREATE = "project_create"
    PROJECT_UPDATE = "project_update"
    PROJECT_DELETE = "project_delete"

    # File actions
    FILE_CREATE = "file_create"
    FILE_UPDATE = "file_update"
    FILE_DELETE = "file_delete"

    # Review actions
    REVIEW_CREATE = "review_create"
    REVIEW_COMPLETE = "review_complete"

    # Issue actions
    ISSUE_UPDATE = "issue_update"

    # API key actions
    API_KEY_ACCESS = "api_key_access"


class AuditLog(SQLModel, table=True):
    """Audit log entry for tracking user actions."""

    __tablename__ = "audit_logs"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, index=True)
    action: AuditAction = Field(index=True)
    resource_type: str | None = Field(default=None, max_length=50)
    resource_id: int | None = Field(default=None)
    details: str | None = Field(default=None, max_length=2000)
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class AuditLogRead(SQLModel):
    """Schema for reading audit log entries."""
    id: int
    user_id: int | None
    action: AuditAction
    resource_type: str | None
    resource_id: int | None
    details: str | None
    ip_address: str | None
    created_at: datetime
