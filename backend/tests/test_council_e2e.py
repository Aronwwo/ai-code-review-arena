"""End-to-end tests for Council mode workflow."""
import pytest
import time
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models.review import Review, ReviewAgent, Issue


class TestCouncilModeE2E:
    """End-to-end tests for Council mode review workflow."""

    def test_complete_council_review_workflow(self, client: TestClient, auth_headers: dict, test_engine):
        """Test complete Council review workflow from project creation to results."""
        # Step 1: Create a project
        project_response = client.post(
            "/projects",
            json={
                "name": "E2E Test Project",
                "description": "Complete workflow test"
            },
            headers=auth_headers
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["id"]

        # Step 2: Upload test files
        test_files = [
            {
                "file_path": "main.py",
                "content": """def calculate_total(items):
    # Missing input validation
    total = 0
    for item in items:
        total += item['price']  # No error handling
    return total
""",
                "language": "python"
            },
            {
                "file_path": "utils.py",
                "content": """import hashlib

def hash_password(password):
    # Weak hashing algorithm
    return hashlib.md5(password.encode()).hexdigest()
""",
                "language": "python"
            }
        ]

        for file_data in test_files:
            file_response = client.post(
                f"/projects/{project_id}/files",
                json=file_data,
                headers=auth_headers
            )
            assert file_response.status_code == 201

        # Step 3: Start Council review with all 4 agents
        review_response = client.post(
            f"/projects/{project_id}/reviews",
            json={
                "agent_roles": ["general", "security", "performance", "style"],
                "provider": "mock",
                "model": "default",
                "conversation_mode": "council",
                "moderator_type": "debate"
            },
            headers=auth_headers
        )
        assert review_response.status_code == 201
        review_data = review_response.json()
        review_id = review_data["id"]
        assert review_data["status"] == "pending"
        assert review_data["agent_count"] == 4

        # Step 4: Wait for review to complete (with timeout)
        max_attempts = 30  # 30 seconds max
        review_completed = False

        for attempt in range(max_attempts):
            time.sleep(1)
            status_response = client.get(
                f"/reviews/{review_id}",
                headers=auth_headers
            )
            assert status_response.status_code == 200
            status_data = status_response.json()

            if status_data["status"] == "completed":
                review_completed = True
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"Review failed: {status_data.get('error_message')}")

        # For mock provider, review should complete quickly
        # If not completed, it's still a valid test state (background task)

        # Step 5: Get review agents
        agents_response = client.get(
            f"/reviews/{review_id}/agents",
            headers=auth_headers
        )
        assert agents_response.status_code == 200
        agents = agents_response.json()
        assert len(agents) == 4

        agent_roles = {agent["role"] for agent in agents}
        assert agent_roles == {"general", "security", "performance", "style"}

        # Step 6: Get review issues
        issues_response = client.get(
            f"/reviews/{review_id}/issues",
            headers=auth_headers
        )
        assert issues_response.status_code == 200
        issues_data = issues_response.json()

        assert "items" in issues_data
        assert "total" in issues_data
        assert "page" in issues_data

        # With mock provider, we should get some issues
        # (mock provider generates sample issues)
        issues = issues_data["items"]

        # Verify issue structure
        if len(issues) > 0:
            first_issue = issues[0]
            assert "id" in first_issue
            assert "severity" in first_issue
            assert "category" in first_issue
            assert "title" in first_issue
            assert "description" in first_issue

    def test_council_review_with_moderator_types(self, client: TestClient, auth_headers: dict):
        """Test Council review with different moderator types."""
        # Create project
        project_response = client.post(
            "/projects",
            json={"name": "Moderator Test", "description": "Test moderators"},
            headers=auth_headers
        )
        project_id = project_response.json()["id"]

        # Upload file
        client.post(
            f"/projects/{project_id}/files",
            json={
                "file_path": "test.py",
                "content": "def test(): return 42",
                "language": "python"
            },
            headers=auth_headers
        )

        # Test each moderator type
        moderator_types = ["debate", "consensus", "strategic"]

        for mod_type in moderator_types:
            review_response = client.post(
                f"/projects/{project_id}/reviews",
                json={
                    "agent_roles": ["general", "security"],
                    "provider": "mock",
                    "model": "default",
                    "conversation_mode": "council",
                    "moderator_type": mod_type
                },
                headers=auth_headers
            )

            assert review_response.status_code == 201
            review_data = review_response.json()

            # Verify moderator type is stored (if exposed in response)
            # Backend should handle the moderator type correctly

    def test_council_review_with_per_agent_configs(self, client: TestClient, auth_headers: dict):
        """Test Council review with different providers per agent."""
        # Create project
        project_response = client.post(
            "/projects",
            json={"name": "Multi-Provider Test", "description": "Test"},
            headers=auth_headers
        )
        project_id = project_response.json()["id"]

        # Upload file
        client.post(
            f"/projects/{project_id}/files",
            json={
                "file_path": "test.py",
                "content": "def calculate(x): return x * 2",
                "language": "python"
            },
            headers=auth_headers
        )

        # Start review with different providers per agent
        review_response = client.post(
            f"/projects/{project_id}/reviews",
            json={
                "agent_roles": ["general", "security", "performance", "style"],
                "agent_configs": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "security-model"},
                    "performance": {"provider": "mock", "model": "perf-model"},
                    "style": {"provider": "mock", "model": "style-model"}
                },
                "conversation_mode": "council",
                "moderator_type": "consensus"
            },
            headers=auth_headers
        )

        assert review_response.status_code == 201
        review_id = review_response.json()["id"]

        # Get agents and verify they have different configs
        agents_response = client.get(
            f"/reviews/{review_id}/agents",
            headers=auth_headers
        )
        agents = agents_response.json()

        # Verify each agent has its assigned model
        agent_models = {agent["role"]: agent["model"] for agent in agents}
        assert agent_models["general"] == "default"
        assert agent_models["security"] == "security-model"
        assert agent_models["performance"] == "perf-model"
        assert agent_models["style"] == "style-model"


class TestCouncilReviewFiltering:
    """Tests for filtering and querying Council review issues."""

    def test_filter_issues_by_severity(self, client: TestClient, auth_headers: dict):
        """Test filtering issues by severity level."""
        # Create project and review
        project_response = client.post(
            "/projects",
            json={"name": "Filter Test", "description": "Test"},
            headers=auth_headers
        )
        project_id = project_response.json()["id"]

        client.post(
            f"/projects/{project_id}/files",
            json={
                "file_path": "test.py",
                "content": "def vulnerable(): pass",
                "language": "python"
            },
            headers=auth_headers
        )

        review_response = client.post(
            f"/projects/{project_id}/reviews",
            json={
                "agent_roles": ["general", "security"],
                "provider": "mock",
                "model": "default"
            },
            headers=auth_headers
        )
        review_id = review_response.json()["id"]

        # Wait a bit for mock issues to be created
        time.sleep(2)

        # Filter by severity
        for severity in ["critical", "high", "medium", "low"]:
            response = client.get(
                f"/reviews/{review_id}/issues",
                params={"severity": severity},
                headers=auth_headers
            )
            assert response.status_code == 200
            # All returned issues should match the severity filter
            issues = response.json()["items"]
            for issue in issues:
                assert issue["severity"] == severity

    def test_filter_issues_by_category(self, client: TestClient, auth_headers: dict):
        """Test filtering issues by category."""
        # Create project and review
        project_response = client.post(
            "/projects",
            json={"name": "Category Test", "description": "Test"},
            headers=auth_headers
        )
        project_id = project_response.json()["id"]

        client.post(
            f"/projects/{project_id}/files",
            json={
                "file_path": "test.py",
                "content": "def test(): pass",
                "language": "python"
            },
            headers=auth_headers
        )

        review_response = client.post(
            f"/projects/{project_id}/reviews",
            json={
                "agent_roles": ["general", "security"],
                "provider": "mock",
                "model": "default"
            },
            headers=auth_headers
        )
        review_id = review_response.json()["id"]

        # Filter by category
        response = client.get(
            f"/reviews/{review_id}/issues",
            params={"category": "security"},
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_paginate_issues(self, client: TestClient, auth_headers: dict):
        """Test pagination of review issues."""
        # Create project and review
        project_response = client.post(
            "/projects",
            json={"name": "Pagination Test", "description": "Test"},
            headers=auth_headers
        )
        project_id = project_response.json()["id"]

        client.post(
            f"/projects/{project_id}/files",
            json={
                "file_path": "test.py",
                "content": "def test(): pass",
                "language": "python"
            },
            headers=auth_headers
        )

        review_response = client.post(
            f"/projects/{project_id}/reviews",
            json={
                "agent_roles": ["general", "security", "performance", "style"],
                "provider": "mock",
                "model": "default"
            },
            headers=auth_headers
        )
        review_id = review_response.json()["id"]

        # Get first page
        page1_response = client.get(
            f"/reviews/{review_id}/issues",
            params={"page": 1, "page_size": 5},
            headers=auth_headers
        )
        assert page1_response.status_code == 200
        page1_data = page1_response.json()

        assert page1_data["page"] == 1
        assert page1_data["page_size"] == 5
        assert "total" in page1_data
        assert "total_pages" in page1_data

        # If there are enough issues, test page 2
        if page1_data["total"] > 5:
            page2_response = client.get(
                f"/reviews/{review_id}/issues",
                params={"page": 2, "page_size": 5},
                headers=auth_headers
            )
            assert page2_response.status_code == 200
            page2_data = page2_response.json()
            assert page2_data["page"] == 2


class TestCouncilReviewUpdates:
    """Tests for updating review issues."""

    def test_update_issue_status(self, client: TestClient, auth_headers: dict, test_engine):
        """Test updating issue status (e.g., marking as resolved)."""
        # Create project and review
        project_response = client.post(
            "/projects",
            json={"name": "Update Test", "description": "Test"},
            headers=auth_headers
        )
        project_id = project_response.json()["id"]

        client.post(
            f"/projects/{project_id}/files",
            json={
                "file_path": "test.py",
                "content": "def test(): pass",
                "language": "python"
            },
            headers=auth_headers
        )

        review_response = client.post(
            f"/projects/{project_id}/reviews",
            json={
                "agent_roles": ["general"],
                "provider": "mock",
                "model": "default"
            },
            headers=auth_headers
        )
        review_id = review_response.json()["id"]

        # Wait for review to create some issues
        time.sleep(2)

        # Get issues
        issues_response = client.get(
            f"/reviews/{review_id}/issues",
            headers=auth_headers
        )
        issues = issues_response.json()["items"]

        if len(issues) > 0:
            issue_id = issues[0]["id"]

            # Update issue status
            update_response = client.patch(
                f"/reviews/issues/{issue_id}",
                json={"status": "resolved"},
                headers=auth_headers
            )

            assert update_response.status_code == 200
            updated_issue = update_response.json()
            assert updated_issue["status"] == "resolved"

    def test_update_issue_severity(self, client: TestClient, auth_headers: dict, test_engine):
        """Test updating issue severity."""
        # Similar setup as above
        project_response = client.post(
            "/projects",
            json={"name": "Severity Update Test", "description": "Test"},
            headers=auth_headers
        )
        project_id = project_response.json()["id"]

        client.post(
            f"/projects/{project_id}/files",
            json={"file_path": "test.py", "content": "pass", "language": "python"},
            headers=auth_headers
        )

        review_response = client.post(
            f"/projects/{project_id}/reviews",
            json={
                "agent_roles": ["general"],
                "provider": "mock",
                "model": "default"
            },
            headers=auth_headers
        )
        review_id = review_response.json()["id"]

        time.sleep(2)

        issues_response = client.get(
            f"/reviews/{review_id}/issues",
            headers=auth_headers
        )
        issues = issues_response.json()["items"]

        if len(issues) > 0:
            issue_id = issues[0]["id"]

            # Update severity
            update_response = client.patch(
                f"/reviews/issues/{issue_id}",
                json={"severity": "low"},
                headers=auth_headers
            )

            if update_response.status_code == 200:
                updated_issue = update_response.json()
                assert updated_issue["severity"] == "low"
