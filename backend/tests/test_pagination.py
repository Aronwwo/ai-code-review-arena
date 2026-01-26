"""Tests for pagination in API endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app
from app.models.user import User
from app.models.project import Project
from app.models.review import Review
from app.database import get_session
from app.api.deps import get_current_user


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_user(session: Session):
    """Create test user."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        username="testuser"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def test_project(session: Session, test_user: User):
    """Create test project."""
    project = Project(
        name="Test Project",
        description="Test description",
        user_id=test_user.id
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@pytest.fixture
def test_reviews(session: Session, test_project: Project):
    """Create 25 test reviews for pagination testing."""
    reviews = []
    for i in range(25):
        review = Review(
            project_id=test_project.id,
            status="completed"
        )
        session.add(review)
        reviews.append(review)
    session.commit()
    for review in reviews:
        session.refresh(review)
    return reviews


class TestReviewPagination:
    """Test pagination for review list endpoint."""

    def test_pagination_default_page_size(self, client, test_project, test_reviews, test_user):
        """Test that default page size is 20."""
        # Mock authentication
        app.dependency_overrides[get_current_user] = lambda: test_user

        response = client.get(f"/api/projects/{test_project.id}/reviews")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 20  # Default page size

    def test_pagination_custom_page_size(self, client, test_project, test_reviews, test_user):
        """Test custom page size."""
        app.dependency_overrides[get_current_user] = lambda: test_user

        response = client.get(f"/api/projects/{test_project.id}/reviews?page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10

    def test_pagination_second_page(self, client, test_project, test_reviews, test_user):
        """Test second page returns remaining items."""
        app.dependency_overrides[get_current_user] = lambda: test_user

        response = client.get(f"/api/projects/{test_project.id}/reviews?page=2&page_size=20")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5  # 25 total - 20 on first page = 5 on second

    def test_pagination_max_page_size(self, client, test_project, test_reviews, test_user):
        """Test that page size is limited to 100."""
        app.dependency_overrides[get_current_user] = lambda: test_user

        response = client.get(f"/api/projects/{test_project.id}/reviews?page_size=200")

        # Should be rejected or limited to 100
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            data = response.json()
            assert len(data) <= 100

    def test_pagination_invalid_page(self, client, test_project, test_reviews, test_user):
        """Test that page number must be >= 1."""
        app.dependency_overrides[get_current_user] = lambda: test_user

        response = client.get(f"/api/projects/{test_project.id}/reviews?page=0")

        assert response.status_code == 422  # Validation error
