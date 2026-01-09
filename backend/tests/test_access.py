"""Tests for access control utilities."""
import pytest
from fastapi import HTTPException
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from app.utils.access import verify_project_access, verify_review_access
from app.models.user import User
from app.models.project import Project
from app.models.review import Review


@pytest.fixture(name="session")
def session_fixture():
    """Create test database session."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Create test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed",
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="other_user")
def other_user_fixture(session: Session):
    """Create another test user."""
    user = User(
        email="other@example.com",
        username="otheruser",
        hashed_password="hashed",
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="test_project")
def test_project_fixture(session: Session, test_user: User):
    """Create test project."""
    project = Project(
        name="Test Project",
        description="Test description",
        owner_id=test_user.id
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@pytest.mark.asyncio
async def test_verify_project_access_success(session: Session, test_user: User, test_project: Project):
    """Test successful project access verification."""
    project = await verify_project_access(test_project.id, test_user, session)
    assert project.id == test_project.id
    assert project.owner_id == test_user.id


@pytest.mark.asyncio
async def test_verify_project_access_not_found(session: Session, test_user: User):
    """Test project not found raises 404."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_project_access(999, test_user, session)
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_verify_project_access_forbidden(session: Session, other_user: User, test_project: Project):
    """Test accessing other user's project raises 403."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_project_access(test_project.id, other_user, session)
    assert exc_info.value.status_code == 403
    assert "not authorized" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_verify_review_access_success(session: Session, test_user: User, test_project: Project):
    """Test successful review access verification."""
    review = Review(
        project_id=test_project.id,
        created_by=test_user.id,
        status="pending"
    )
    session.add(review)
    session.commit()
    session.refresh(review)

    verified_review = await verify_review_access(review.id, test_user, session)
    assert verified_review.id == review.id


@pytest.mark.asyncio
async def test_verify_review_access_not_found(session: Session, test_user: User):
    """Test review not found raises 404."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_review_access(999, test_user, session)
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_verify_review_access_forbidden(session: Session, other_user: User, test_project: Project, test_user: User):
    """Test accessing review from other user's project raises 403."""
    review = Review(
        project_id=test_project.id,
        created_by=test_user.id,
        status="pending"
    )
    session.add(review)
    session.commit()
    session.refresh(review)

    with pytest.raises(HTTPException) as exc_info:
        await verify_review_access(review.id, other_user, session)
    assert exc_info.value.status_code == 403
    assert "not authorized" in exc_info.value.detail.lower()
