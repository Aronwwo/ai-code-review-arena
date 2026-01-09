"""Audit logging utility for tracking user actions."""
import logging
from datetime import datetime
from typing import Any
from fastapi import Request
from sqlmodel import Session
from app.models.audit import AuditLog, AuditAction

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Get the client's IP address from the request.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address
    """
    # Check for X-Forwarded-For header (for proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    # Check for X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to client host
    if request.client:
        return request.client.host

    return "unknown"


def get_user_agent(request: Request) -> str:
    """Get the user agent from the request.

    Args:
        request: FastAPI request object

    Returns:
        User agent string (truncated to 500 chars)
    """
    user_agent = request.headers.get("User-Agent", "unknown")
    return user_agent[:500]


async def log_audit_event(
    session: Session,
    action: AuditAction,
    user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    details: str | None = None,
    request: Request | None = None,
):
    """Log an audit event to the database.

    Args:
        session: Database session
        action: Type of action being logged
        user_id: ID of user performing the action
        resource_type: Type of resource (e.g., "project", "file")
        resource_id: ID of the resource
        details: Additional details about the action
        request: FastAPI request object (for IP and user agent)
    """
    try:
        ip_address = None
        user_agent = None

        if request:
            ip_address = get_client_ip(request)
            user_agent = get_user_agent(request)

        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details[:2000] if details and len(details) > 2000 else details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        session.add(audit_log)
        session.commit()

        logger.debug(
            f"Audit: {action.value} by user {user_id} on {resource_type}:{resource_id}"
        )

    except Exception as e:
        # Log error but don't fail the main operation
        logger.error(f"Failed to log audit event: {e}")


def sync_log_audit_event(
    session: Session,
    action: AuditAction,
    user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    details: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    """Synchronous version of log_audit_event for non-async contexts.

    Args:
        session: Database session
        action: Type of action being logged
        user_id: ID of user performing the action
        resource_type: Type of resource
        resource_id: ID of the resource
        details: Additional details about the action
        ip_address: Client IP address
        user_agent: Client user agent
    """
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details[:2000] if details and len(details) > 2000 else details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        session.add(audit_log)
        session.commit()

        logger.debug(
            f"Audit: {action.value} by user {user_id} on {resource_type}:{resource_id}"
        )

    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
