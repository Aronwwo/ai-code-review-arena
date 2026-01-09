"""Access control utilities for authorization checks."""
from fastapi import HTTPException, status
from sqlmodel import Session
from app.models.user import User
from app.models.project import Project
from app.models.review import Review


async def verify_project_access(
    project_id: int,
    current_user: User,
    session: Session
) -> Project:
    """Verify user has access to the project.

    Args:
        project_id: ID of the project to check
        current_user: Current authenticated user
        session: Database session

    Returns:
        Project object if user has access

    Raises:
        HTTPException: 404 if project not found, 403 if user doesn't own project
    """
    project = session.get(Project, project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project"
        )

    return project


async def verify_review_access(
    review_id: int,
    current_user: User,
    session: Session
) -> Review:
    """Verify user has access to the review.

    Args:
        review_id: ID of the review to check
        current_user: Current authenticated user
        session: Database session

    Returns:
        Review object if user has access

    Raises:
        HTTPException: 404 if review not found, 403 if user doesn't own review
    """
    review = session.get(Review, review_id)

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    # Check if user owns the project that this review belongs to
    project = session.get(Project, review.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this review"
        )

    return review
