"""Audit log API endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, func
from app.database import get_session
from app.models.user import User
from app.models.audit import AuditLog, AuditLogRead, AuditAction
from app.api.deps import get_current_user

router = APIRouter(prefix="/audit", tags=["audit"])


def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require superuser access."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )
    return current_user


@router.get("/logs", response_model=list[AuditLogRead])
async def get_audit_logs(
    current_user: User = Depends(require_superuser),
    session: Session = Depends(get_session),
    user_id: int | None = Query(None, description="Filter by user ID"),
    action: AuditAction | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    from_date: datetime | None = Query(None, description="Filter from date"),
    to_date: datetime | None = Query(None, description="Filter to date"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
):
    """Get audit logs with optional filters.

    Only accessible by superusers.
    """
    statement = select(AuditLog)

    # Apply filters
    if user_id is not None:
        statement = statement.where(AuditLog.user_id == user_id)
    if action is not None:
        statement = statement.where(AuditLog.action == action)
    if resource_type is not None:
        statement = statement.where(AuditLog.resource_type == resource_type)
    if from_date is not None:
        statement = statement.where(AuditLog.created_at >= from_date)
    if to_date is not None:
        statement = statement.where(AuditLog.created_at <= to_date)

    # Order by most recent first
    statement = statement.order_by(AuditLog.created_at.desc())

    # Apply pagination
    statement = statement.offset(offset).limit(limit)

    logs = session.exec(statement).all()
    return [AuditLogRead(**log.model_dump()) for log in logs]


@router.get("/logs/count")
async def get_audit_logs_count(
    current_user: User = Depends(require_superuser),
    session: Session = Depends(get_session),
    user_id: int | None = Query(None, description="Filter by user ID"),
    action: AuditAction | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    from_date: datetime | None = Query(None, description="Filter from date"),
    to_date: datetime | None = Query(None, description="Filter to date"),
):
    """Get count of audit logs matching filters.

    Only accessible by superusers.
    """
    statement = select(func.count(AuditLog.id))

    # Apply filters
    if user_id is not None:
        statement = statement.where(AuditLog.user_id == user_id)
    if action is not None:
        statement = statement.where(AuditLog.action == action)
    if resource_type is not None:
        statement = statement.where(AuditLog.resource_type == resource_type)
    if from_date is not None:
        statement = statement.where(AuditLog.created_at >= from_date)
    if to_date is not None:
        statement = statement.where(AuditLog.created_at <= to_date)

    count = session.exec(statement).one()
    return {"count": count}


@router.get("/logs/my", response_model=list[AuditLogRead])
async def get_my_audit_logs(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    action: AuditAction | None = Query(None, description="Filter by action type"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
):
    """Get current user's audit logs.

    Allows users to see their own activity history.
    """
    statement = select(AuditLog).where(AuditLog.user_id == current_user.id)

    if action is not None:
        statement = statement.where(AuditLog.action == action)

    statement = statement.order_by(AuditLog.created_at.desc())
    statement = statement.offset(offset).limit(limit)

    logs = session.exec(statement).all()
    return [AuditLogRead(**log.model_dump()) for log in logs]
