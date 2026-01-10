"""Tests for Arena parallel execution behavior."""
from types import SimpleNamespace
import pytest
from sqlmodel import Session
from app.models.user import User
from app.models.project import Project
from app.models.arena import ArenaSession
from app.orchestrators.arena import ArenaOrchestrator
import app.orchestrators.arena as arena_module


@pytest.mark.asyncio
async def test_conduct_arena_uses_asyncio_gather(test_session: Session, monkeypatch):
    user = User(email="arena-parallel@example.com", username="arena-parallel", hashed_password="hash")
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)

    project = Project(name="Arena Parallel Project", owner_id=user.id)
    test_session.add(project)
    test_session.commit()
    test_session.refresh(project)

    schema_config = {
        "general": {"provider": "mock", "model": "mock-model"},
        "security": {"provider": "mock", "model": "mock-model"},
        "performance": {"provider": "mock", "model": "mock-model"},
        "style": {"provider": "mock", "model": "mock-model"},
    }

    arena_session = ArenaSession(
        project_id=project.id,
        created_by=user.id,
        schema_a_config=schema_config,
        schema_b_config=schema_config,
    )
    test_session.add(arena_session)
    test_session.commit()
    test_session.refresh(arena_session)

    orchestrator = ArenaOrchestrator(test_session)
    called = {"gather": False, "task_count": 0}

    async def fake_create_and_run_review(*args, **kwargs):
        schema_name = kwargs.get("schema_name") or args[1]
        return SimpleNamespace(id=1 if schema_name == "A" else 2)

    async def fake_gather(*tasks, **kwargs):
        called["gather"] = True
        called["task_count"] = len(tasks)
        results = []
        for task in tasks:
            results.append(await task)
        return results

    monkeypatch.setattr(orchestrator, "_create_and_run_review", fake_create_and_run_review)
    monkeypatch.setattr(arena_module.asyncio, "gather", fake_gather)

    result = await orchestrator.conduct_arena(arena_session.id)

    assert called["gather"] is True
    assert called["task_count"] == 2
    assert result.review_a_id == 1
    assert result.review_b_id == 2
    assert result.status == "completed"
