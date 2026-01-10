"""End-to-end tests for Council mode workflow."""
import time
from fastapi.testclient import TestClient


def _agent_configs(roles):
    return {
        role: {
            "provider": "mock",
            "model": "default",
        }
        for role in roles
    }


def _moderator_config():
    return {"provider": "mock", "model": "default"}


def _create_project(client: TestClient, auth_headers: dict) -> int:
    project_response = client.post(
        "/projects",
        json={"name": "E2E Test Project", "description": "Complete workflow test"},
        headers=auth_headers,
    )
    assert project_response.status_code == 201
    return project_response.json()["id"]


def _upload_file(client: TestClient, auth_headers: dict, project_id: int, name: str, content: str):
    response = client.post(
        f"/projects/{project_id}/files",
        json={"name": name, "content": content, "language": "python"},
        headers=auth_headers,
    )
    assert response.status_code == 201


class TestCouncilModeE2E:
    """End-to-end tests for Council mode review workflow."""

    def test_complete_council_review_workflow(self, client: TestClient, auth_headers: dict):
        project_id = _create_project(client, auth_headers)

        _upload_file(
            client,
            auth_headers,
            project_id,
            "main.py",
            """def calculate_total(items):
    total = 0
    for item in items:
        total += item['price']
    return total
""",
        )
        _upload_file(
            client,
            auth_headers,
            project_id,
            "utils.py",
            """import hashlib

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()
""",
        )

        roles = ["general", "security", "performance", "style"]
        review_response = client.post(
            f"/projects/{project_id}/reviews",
            json={
                "review_mode": "council",
                "agent_roles": roles,
                "agent_configs": _agent_configs(roles),
                "moderator_type": "debate",
                "moderator_config": _moderator_config(),
            },
            headers=auth_headers,
        )
        assert review_response.status_code == 201
        review_id = review_response.json()["id"]

        # Wait for completion
        for _ in range(30):
            time.sleep(1)
            status_response = client.get(f"/reviews/{review_id}", headers=auth_headers)
            assert status_response.status_code == 200
            status_data = status_response.json()
            if status_data["status"] == "completed":
                break
            if status_data["status"] == "failed":
                raise AssertionError(f"Review failed: {status_data.get('error_message')}")

        agents_response = client.get(f"/reviews/{review_id}/agents", headers=auth_headers)
        assert agents_response.status_code == 200
        assert len(agents_response.json()) == 4

        issues_response = client.get(f"/reviews/{review_id}/issues", headers=auth_headers)
        assert issues_response.status_code == 200
        issues_data = issues_response.json()
        assert "items" in issues_data

    def test_council_review_with_moderator_types(self, client: TestClient, auth_headers: dict):
        project_id = _create_project(client, auth_headers)
        _upload_file(client, auth_headers, project_id, "test.py", "def test():\n    return 42\n")

        roles = ["general", "security"]
        for mod_type in ["debate", "consensus", "strategic"]:
            response = client.post(
                f"/projects/{project_id}/reviews",
                json={
                    "review_mode": "council",
                    "agent_roles": roles,
                    "agent_configs": _agent_configs(roles),
                    "moderator_type": mod_type,
                    "moderator_config": _moderator_config(),
                },
                headers=auth_headers,
            )
            assert response.status_code == 201

    def test_council_review_with_per_agent_configs(self, client: TestClient, auth_headers: dict):
        project_id = _create_project(client, auth_headers)
        _upload_file(client, auth_headers, project_id, "test.py", "def calculate(x):\n    return x * 2\n")

        review_response = client.post(
            f"/projects/{project_id}/reviews",
            json={
                "review_mode": "council",
                "agent_roles": ["general", "security", "performance", "style"],
                "agent_configs": {
                    "general": {"provider": "mock", "model": "default"},
                    "security": {"provider": "mock", "model": "security-model"},
                    "performance": {"provider": "mock", "model": "perf-model"},
                    "style": {"provider": "mock", "model": "style-model"},
                },
                "moderator_type": "consensus",
                "moderator_config": _moderator_config(),
            },
            headers=auth_headers,
        )
        assert review_response.status_code == 201
        review_id = review_response.json()["id"]

        agents_response = client.get(f"/reviews/{review_id}/agents", headers=auth_headers)
        agents = agents_response.json()
        agent_models = {agent["role"]: agent["model"] for agent in agents}
        assert agent_models["general"] == "default"
        assert agent_models["security"] == "security-model"
        assert agent_models["performance"] == "perf-model"
        assert agent_models["style"] == "style-model"


class TestCouncilReviewFiltering:
    """Tests for filtering and querying Council review issues."""

    def test_filter_issues_by_severity(self, client: TestClient, auth_headers: dict):
        project_id = _create_project(client, auth_headers)
        _upload_file(client, auth_headers, project_id, "test.py", "def vulnerable():\n    return None\n")

        roles = ["general", "security", "performance", "style"]
        review_response = client.post(
            f"/projects/{project_id}/reviews",
            json={
                "review_mode": "council",
                "agent_roles": roles,
                "agent_configs": _agent_configs(roles),
                "moderator_type": "debate",
                "moderator_config": _moderator_config(),
            },
            headers=auth_headers,
        )
        assert review_response.status_code == 201
        review_id = review_response.json()["id"]

        response = client.get(
            f"/reviews/{review_id}/issues?severity=error",
            headers=auth_headers,
        )
        assert response.status_code == 200
