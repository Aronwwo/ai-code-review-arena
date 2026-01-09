"""Project CRUD API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, func
from app.database import get_session
from app.models.user import User
from app.models.project import (
    Project, ProjectCreate, ProjectUpdate, ProjectRead
)
from app.models.file import File, FileRead, FileReadWithContent
from app.models.review import Review
from app.api.deps import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new project."""
    project = Project(
        **project_data.model_dump(),
        owner_id=current_user.id
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    # Build response with counts
    response = ProjectRead(
        **project.model_dump(),
        file_count=0,
        review_count=0
    )
    return response


@router.get("")
async def list_projects(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """List all projects for the current user with pagination.

    Returns paginated response with metadata including total count, page info.
    """
    # Get total count
    total_stmt = select(func.count(Project.id)).where(Project.owner_id == current_user.id)
    total = session.exec(total_stmt).one()

    # Calculate offset
    offset = (page - 1) * page_size

    # Get projects for current page
    statement = (
        select(Project)
        .where(Project.owner_id == current_user.id)
        .offset(offset)
        .limit(page_size)
        .order_by(Project.created_at.desc())
    )
    projects = session.exec(statement).all()

    # Build responses with counts
    items = []
    for project in projects:
        # Count files
        file_count_stmt = select(func.count(File.id)).where(File.project_id == project.id)
        file_count = session.exec(file_count_stmt).one()

        # Count reviews
        review_count_stmt = select(func.count(Review.id)).where(Review.project_id == project.id)
        review_count = session.exec(review_count_stmt).one()

        items.append(ProjectRead(
            **project.model_dump(),
            file_count=file_count,
            review_count=review_count
        ))

    # Calculate pagination metadata
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return {
        "items": [item.model_dump() for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get a specific project with its files."""
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

    # Get files with content
    file_stmt = select(File).where(File.project_id == project_id).order_by(File.name)
    files = session.exec(file_stmt).all()
    file_reads = [FileReadWithContent(**file.model_dump()) for file in files]

    # Count reviews
    review_count_stmt = select(func.count(Review.id)).where(Review.project_id == project.id)
    review_count = session.exec(review_count_stmt).one()

    # Return dict directly to avoid circular import issues
    return {
        **project.model_dump(),
        "file_count": len(file_reads),
        "review_count": review_count,
        "files": [f.model_dump() for f in file_reads]
    }


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update a project."""
    project = session.get(Project, project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this project"
        )

    # Update fields
    update_data = project_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    from datetime import datetime
    project.updated_at = datetime.utcnow()

    session.add(project)
    session.commit()
    session.refresh(project)

    # Get counts
    file_count_stmt = select(func.count(File.id)).where(File.project_id == project.id)
    file_count = session.exec(file_count_stmt).one()

    review_count_stmt = select(func.count(Review.id)).where(Review.project_id == project.id)
    review_count = session.exec(review_count_stmt).one()

    return ProjectRead(
        **project.model_dump(),
        file_count=file_count,
        review_count=review_count
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete a project and all its files and reviews."""
    project = session.get(Project, project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this project"
        )

    session.delete(project)
    session.commit()

    return None
