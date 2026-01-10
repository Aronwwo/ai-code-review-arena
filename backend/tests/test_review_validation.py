"""Validation tests for review and arena inputs."""
from fastapi.testclient import TestClient


def _create_project(client: TestClient, auth_headers: dict) -> int:
    response = client.post(
        "/projects",
        json={"name": "Validation Project", "description": "Test"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _valid_agent_configs():
    return {
        "general": {"provider": "mock", "model": "default"},
        "security": {"provider": "mock", "model": "default"},
        "performance": {"provider": "mock", "model": "default"},
        "style": {"provider": "mock", "model": "default"},
    }


def test_review_requires_review_mode(client: TestClient, auth_headers: dict):
    project_id = _create_project(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/reviews",
        json={
            "agent_roles": ["general"],
            "agent_configs": _valid_agent_configs(),
            "moderator_type": "debate",
            "moderator_config": {"provider": "mock", "model": "default"}
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_review_requires_moderator_config(client: TestClient, auth_headers: dict):
    project_id = _create_project(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/reviews",
        json={
            "review_mode": "council",
            "agent_roles": ["general"],
            "agent_configs": _valid_agent_configs(),
            "moderator_type": "debate",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
