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
        "general": {"provider": "mock", "model": "default", "prompt": "General prompt"},
        "security": {"provider": "mock", "model": "default", "prompt": "Security prompt"},
        "performance": {"provider": "mock", "model": "default", "prompt": "Performance prompt"},
        "style": {"provider": "mock", "model": "default", "prompt": "Style prompt"},
    }


def test_review_requires_review_mode(client: TestClient, auth_headers: dict):
    project_id = _create_project(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/reviews",
        json={
            "agent_roles": ["general"],
            "agent_configs": _valid_agent_configs(),
            "moderator_type": "debate",
            "moderator_config": {"provider": "mock", "model": "default", "prompt": "Moderator"}
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


def test_review_rejects_empty_prompt(client: TestClient, auth_headers: dict):
    project_id = _create_project(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/reviews",
        json={
            "review_mode": "council",
            "agent_roles": ["general"],
            "agent_configs": {
                "general": {"provider": "mock", "model": "default", "prompt": ""}
            },
            "moderator_type": "debate",
            "moderator_config": {"provider": "mock", "model": "default", "prompt": "Moderator"}
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_arena_requires_prompt_in_schema(client: TestClient, auth_headers: dict):
    project_id = _create_project(client, auth_headers)
    response = client.post(
        "/arena/sessions",
        json={
            "project_id": project_id,
            "schema_a_config": {
                "general": {"provider": "mock", "model": "default", "prompt": ""},
                "security": {"provider": "mock", "model": "default", "prompt": "Security"},
                "performance": {"provider": "mock", "model": "default", "prompt": "Performance"},
                "style": {"provider": "mock", "model": "default", "prompt": "Style"},
            },
            "schema_b_config": _valid_agent_configs(),
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
