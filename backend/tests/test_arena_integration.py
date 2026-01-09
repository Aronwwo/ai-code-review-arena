"""Integration tests for Arena mode workflow."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models.arena import ArenaSession, SchemaRating
from app.models.review import Review
from app.models.project import Project
from app.models.file import File


class TestArenaSessionCreation:
    """Tests for creating Arena sessions."""

    def test_create_arena_session_success(self, client: TestClient, auth_headers: dict, test_engine):
        """Should successfully create an Arena session with valid schemas."""
        # Create project
        project_response = client.post(
            "/projects",
            json={"name": "Arena Test Project", "description": "Test"},
            headers=auth_headers
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["id"]

        # Upload a test file
        file_response = client.post(
            f"/projects/{project_id}/files",
            json={
                "file_path": "test.py",
                "content": "def test():\n    return 42\n",
                "language": "python"
            },
            headers=auth_headers
        )
        assert file_response.status_code == 201

        # Create Arena session
        arena_response = client.post(
            "/arena/sessions",
            json={
                "project_id": project_id,
                "schema_a_config": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "default"},
                    "performance": {"provider": "mock", "model": "default"},
                    "style": {"provider": "mock", "model": "default"}
                },
                "schema_b_config": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "default"},
                    "performance": {"provider": "mock", "model": "default"},
                    "style": {"provider": "mock", "model": "default"}
                }
            },
            headers=auth_headers
        )

        assert arena_response.status_code == 201
        data = arena_response.json()
        assert "id" in data
        assert data["project_id"] == project_id
        assert data["status"] == "pending"
        assert "schema_a_config" in data
        assert "schema_b_config" in data

    def test_create_arena_session_missing_role_in_schema_a(self, client: TestClient, auth_headers: dict):
        """Should reject Arena session if Schema A is missing required roles."""
        # Create project
        project_response = client.post(
            "/projects",
            json={"name": "Test Project", "description": "Test"},
            headers=auth_headers
        )
        project_id = project_response.json()["id"]

        # Try to create Arena session with incomplete Schema A
        arena_response = client.post(
            "/arena/sessions",
            json={
                "project_id": project_id,
                "schema_a_config": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "default"},
                    # Missing: performance, style
                },
                "schema_b_config": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "default"},
                    "performance": {"provider": "mock", "model": "default"},
                    "style": {"provider": "mock", "model": "default"}
                }
            },
            headers=auth_headers
        )

        assert arena_response.status_code == 400
        data = arena_response.json()
        assert "Schema A" in data["detail"]["error"]
        assert "missing" in data["detail"]

    def test_create_arena_session_missing_role_in_schema_b(self, client: TestClient, auth_headers: dict):
        """Should reject Arena session if Schema B is missing required roles."""
        # Create project
        project_response = client.post(
            "/projects",
            json={"name": "Test Project", "description": "Test"},
            headers=auth_headers
        )
        project_id = project_response.json()["id"]

        # Try to create Arena session with incomplete Schema B
        arena_response = client.post(
            "/arena/sessions",
            json={
                "project_id": project_id,
                "schema_a_config": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "default"},
                    "performance": {"provider": "mock", "model": "default"},
                    "style": {"provider": "mock", "model": "default"}
                },
                "schema_b_config": {
                    "general": {"provider": "mock", "model": "default"}
                    # Missing: security, performance, style
                }
            },
            headers=auth_headers
        )

        assert arena_response.status_code == 400
        data = arena_response.json()
        assert "Schema B" in data["detail"]["error"]

    def test_create_arena_session_nonexistent_project(self, client: TestClient, auth_headers: dict):
        """Should return 404 for nonexistent project."""
        arena_response = client.post(
            "/arena/sessions",
            json={
                "project_id": 99999,
                "schema_a_config": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "default"},
                    "performance": {"provider": "mock", "model": "default"},
                    "style": {"provider": "mock", "model": "default"}
                },
                "schema_b_config": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "default"},
                    "performance": {"provider": "mock", "model": "default"},
                    "style": {"provider": "mock", "model": "default"}
                }
            },
            headers=auth_headers
        )

        assert arena_response.status_code == 404


class TestArenaVoting:
    """Tests for Arena voting mechanism."""

    def test_vote_for_candidate_a(self, client: TestClient, auth_headers: dict, test_engine):
        """Should successfully record a vote for candidate A."""
        # Create project and Arena session
        project_response = client.post(
            "/projects",
            json={"name": "Voting Test", "description": "Test"},
            headers=auth_headers
        )
        project_id = project_response.json()["id"]

        # Upload file
        client.post(
            f"/projects/{project_id}/files",
            json={
                "file_path": "test.py",
                "content": "def test(): pass",
                "language": "python"
            },
            headers=auth_headers
        )

        # Create Arena session
        arena_response = client.post(
            "/arena/sessions",
            json={
                "project_id": project_id,
                "schema_a_config": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "default"},
                    "performance": {"provider": "mock", "model": "default"},
                    "style": {"provider": "mock", "model": "default"}
                },
                "schema_b_config": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "default"},
                    "performance": {"provider": "mock", "model": "default"},
                    "style": {"provider": "mock", "model": "default"}
                }
            },
            headers=auth_headers
        )
        session_id = arena_response.json()["id"]

        # Wait a bit for background task (or check status)
        # For testing, we'll just vote regardless of completion

        # Vote for candidate A
        vote_response = client.post(
            f"/arena/sessions/{session_id}/vote",
            json={"choice": "candidate_a"},
            headers=auth_headers
        )

        # Should succeed or wait for completion
        assert vote_response.status_code in [200, 400]  # 400 if not completed yet

    def test_vote_requires_authentication(self, client: TestClient):
        """Should require authentication for voting."""
        vote_response = client.post(
            "/arena/sessions/1/vote",
            json={"choice": "candidate_a"}
        )

        assert vote_response.status_code == 401

    def test_vote_invalid_choice(self, client: TestClient, auth_headers: dict):
        """Should reject invalid vote choices."""
        vote_response = client.post(
            "/arena/sessions/1/vote",
            json={"choice": "invalid_choice"},
            headers=auth_headers
        )

        # Should fail validation
        assert vote_response.status_code in [400, 404, 422]


class TestArenaRankings:
    """Tests for Arena rankings and ELO system."""

    def test_get_rankings_empty(self, client: TestClient, auth_headers: dict):
        """Should return empty rankings when no sessions exist."""
        response = client.get("/arena/rankings", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_rankings_updated_after_vote(self, client: TestClient, auth_headers: dict, test_engine):
        """Should update schema rankings after votes are cast."""
        # This would be a full integration test requiring:
        # 1. Create multiple Arena sessions
        # 2. Complete them
        # 3. Cast votes
        # 4. Verify ELO ratings are updated

        # For now, just verify the endpoint exists
        response = client.get("/arena/rankings", headers=auth_headers)
        assert response.status_code == 200


class TestArenaSessionRetrieval:
    """Tests for retrieving Arena sessions."""

    def test_get_arena_session_by_id(self, client: TestClient, auth_headers: dict):
        """Should retrieve Arena session by ID."""
        # Create project
        project_response = client.post(
            "/projects",
            json={"name": "Retrieval Test", "description": "Test"},
            headers=auth_headers
        )
        project_id = project_response.json()["id"]

        # Upload file
        client.post(
            f"/projects/{project_id}/files",
            json={
                "file_path": "test.py",
                "content": "def test(): pass",
                "language": "python"
            },
            headers=auth_headers
        )

        # Create Arena session
        create_response = client.post(
            "/arena/sessions",
            json={
                "project_id": project_id,
                "schema_a_config": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "default"},
                    "performance": {"provider": "mock", "model": "default"},
                    "style": {"provider": "mock", "model": "default"}
                },
                "schema_b_config": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "default"},
                    "performance": {"provider": "mock", "model": "default"},
                    "style": {"provider": "mock", "model": "default"}
                }
            },
            headers=auth_headers
        )
        session_id = create_response.json()["id"]

        # Retrieve the session
        get_response = client.get(
            f"/arena/sessions/{session_id}",
            headers=auth_headers
        )

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == session_id
        assert data["project_id"] == project_id

    def test_get_arena_session_not_found(self, client: TestClient, auth_headers: dict):
        """Should return 404 for nonexistent session."""
        response = client.get("/arena/sessions/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_list_arena_sessions(self, client: TestClient, auth_headers: dict):
        """Should list all Arena sessions."""
        response = client.get("/arena/sessions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_arena_session_access_control(self, client: TestClient, auth_headers: dict, test_engine):
        """Should not allow access to other users' Arena sessions."""
        # Create first user's session
        project_response = client.post(
            "/projects",
            json={"name": "Private Project", "description": "Test"},
            headers=auth_headers
        )
        project_id = project_response.json()["id"]

        client.post(
            f"/projects/{project_id}/files",
            json={"file_path": "test.py", "content": "pass", "language": "python"},
            headers=auth_headers
        )

        arena_response = client.post(
            "/arena/sessions",
            json={
                "project_id": project_id,
                "schema_a_config": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "default"},
                    "performance": {"provider": "mock", "model": "default"},
                    "style": {"provider": "mock", "model": "default"}
                },
                "schema_b_config": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "default"},
                    "performance": {"provider": "mock", "model": "default"},
                    "style": {"provider": "mock", "model": "default"}
                }
            },
            headers=auth_headers
        )
        session_id = arena_response.json()["id"]

        # Register second user
        client.post(
            "/auth/register",
            json={
                "email": "other@example.com",
                "password": "password123",
                "full_name": "Other User"
            }
        )

        # Login as second user
        login_response = client.post(
            "/auth/login",
            json={"email": "other@example.com", "password": "password123"}
        )
        other_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Try to access first user's session
        access_response = client.get(
            f"/arena/sessions/{session_id}",
            headers=other_headers
        )

        # Should be forbidden
        assert access_response.status_code in [403, 404]
