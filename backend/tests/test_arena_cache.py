"""Integration tests for Arena cache behavior."""
from fastapi.testclient import TestClient
from sqlmodel import select
from app.models.arena import ArenaSession
from app.models.project import Project
from app.models.user import User
from app.utils.cache import cache


def _create_project(client: TestClient, auth_headers: dict) -> int:
    response = client.post(
        "/projects",
        json={"name": "Arena Cache Project", "description": "Cache"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_stats_and_rankings_cache_invalidated_on_vote(client: TestClient, auth_headers: dict, test_session):
    cache.clear()
    project_id = _create_project(client, auth_headers)

    user = test_session.exec(select(User)).first()
    assert user is not None

    arena_session = ArenaSession(
        project_id=project_id,
        created_by=user.id,
        status="completed",
        schema_a_config={
            "general": {"provider": "mock", "model": "default"},
            "security": {"provider": "mock", "model": "default"},
            "performance": {"provider": "mock", "model": "default"},
            "style": {"provider": "mock", "model": "default"},
        },
        schema_b_config={
            "general": {"provider": "mock", "model": "default"},
            "security": {"provider": "mock", "model": "default"},
            "performance": {"provider": "mock", "model": "default"},
            "style": {"provider": "mock", "model": "default"},
        },
    )
    test_session.add(arena_session)
    test_session.commit()
    test_session.refresh(arena_session)

    stats_response = client.get("/arena/stats", headers=auth_headers)
    assert stats_response.status_code == 200
    assert cache.get("arena:stats") is not None

    rankings_response = client.get("/arena/rankings?limit=10&min_games=0", headers=auth_headers)
    assert rankings_response.status_code == 200
    assert cache.get("arena:rankings:limit:10:min_games:0") is not None

    vote_response = client.post(
        f"/arena/sessions/{arena_session.id}/vote",
        json={"winner": "A"},
        headers=auth_headers,
    )
    assert vote_response.status_code == 200
    assert cache.get("arena:stats") is None
    assert cache.get("arena:rankings:limit:10:min_games:0") is None
