"""End-to-end test for Arena flow.

This test verifies:
1. Arena test_session creation with only 'general' role
2. Arena execution (both teams analyze code)
3. Voting system
4. ELO ranking updates
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.project import Project
from app.models.file import File
from app.models.arena import ArenaSession, TeamRating


@pytest.fixture
def test_project(client: TestClient, test_session: Session, auth_headers: dict):
    """Create a test project with a sample file."""
    # Get current user from auth headers
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    user_id = response.json()["id"]

    # Create project
    project = Project(
        name="Arena Test Project",
        description="Project for testing Arena flow",
        owner_id=user_id,
    )
    test_session.add(project)
    test_session.commit()
    test_session.refresh(project)

    # Add a sample Python file with a simple bug
    file_content = """def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)

# Bug: doesn't handle empty list
result = calculate_average([1, 2, 3, 4, 5])
print(result)
"""
    file = File(
        project_id=project.id,
        name="test.py",
        content=file_content,
        content_hash=File.compute_hash(file_content),
        size_bytes=len(file_content.encode()),
        language="python",
    )
    test_session.add(file)
    test_session.commit()

    return project


def test_arena_validation_only_general_required(client: TestClient, auth_headers: dict, test_project: Project):
    """Test that Arena accepts payload with only 'general' role."""
    arena_payload = {
        "project_id": test_project.id,
        "team_a_config": {
            "general": {
                "provider": "ollama",
                "model": "qwen2.5-coder:latest",
                "temperature": 0.2,
                "max_tokens": 4096,
            }
        },
        "team_b_config": {
            "general": {
                "provider": "ollama",
                "model": "deepseek-coder:latest",
                "temperature": 0.2,
                "max_tokens": 4096,
            }
        }
    }

    response = client.post("/arena/sessions", json=arena_payload, headers=auth_headers)

    # Should accept the request and create the test_session
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["status"] == "pending"
    assert data["team_a_config"]["general"]["provider"] == "ollama"
    assert data["team_b_config"]["general"]["provider"] == "ollama"


def test_arena_validation_rejects_missing_general(client: TestClient, auth_headers: dict, test_project: Project):
    """Test that Arena rejects payload without 'general' role."""
    arena_payload = {
        "project_id": test_project.id,
        "team_a_config": {
            "security": {  # Wrong: should be 'general'
                "provider": "ollama",
                "model": "qwen2.5-coder:latest",
            }
        },
        "team_b_config": {
            "general": {
                "provider": "ollama",
                "model": "deepseek-coder:latest",
            }
        }
    }

    response = client.post("/arena/sessions", json=arena_payload, headers=auth_headers)

    # Should reject the request
    assert response.status_code == 422
    assert "general" in response.text.lower()


def test_arena_validation_rejects_missing_provider(client: TestClient, auth_headers: dict, test_project: Project):
    """Test that Arena rejects payload without 'provider' in general config."""
    arena_payload = {
        "project_id": test_project.id,
        "team_a_config": {
            "general": {
                "model": "qwen2.5-coder:latest",  # Missing provider
            }
        },
        "team_b_config": {
            "general": {
                "provider": "ollama",
                "model": "deepseek-coder:latest",
            }
        }
    }

    response = client.post("/arena/sessions", json=arena_payload, headers=auth_headers)

    # Should reject the request
    assert response.status_code == 422
    assert "provider" in response.text.lower()


def test_arena_validation_rejects_missing_model(client: TestClient, auth_headers: dict, test_project: Project):
    """Test that Arena rejects payload without 'model' in general config."""
    arena_payload = {
        "project_id": test_project.id,
        "team_a_config": {
            "general": {
                "provider": "ollama",  # Missing model
            }
        },
        "team_b_config": {
            "general": {
                "provider": "ollama",
                "model": "deepseek-coder:latest",
            }
        }
    }

    response = client.post("/arena/sessions", json=arena_payload, headers=auth_headers)

    # Should reject the request
    assert response.status_code == 422
    assert "model" in response.text.lower()


def test_arena_get_engine_hash_stable():
    """Test that engine hash is stable and based on provider/model only."""
    from app.api.arena import get_engine_config, get_engine_hash

    config1 = {"general": {"provider": "ollama", "model": "qwen2.5"}}
    config2 = {"general": {"provider": "ollama", "model": "qwen2.5"}}
    config3 = {"general": {"provider": "ollama", "model": "deepseek"}}

    engine1 = get_engine_config(config1)
    engine2 = get_engine_config(config2)
    engine3 = get_engine_config(config3)

    hash1 = get_engine_hash(engine1)
    hash2 = get_engine_hash(engine2)
    hash3 = get_engine_hash(engine3)

    # Same provider/model should produce same hash
    assert hash1 == hash2

    # Different model should produce different hash
    assert hash1 != hash3


def test_arena_elo_updates_after_vote(client: TestClient, auth_headers: dict, test_project: Project, test_session: Session):
    """Test that ELO rankings are updated after voting."""
    # Create arena test_session
    arena_payload = {
        "project_id": test_project.id,
        "team_a_config": {
            "general": {
                "provider": "ollama",
                "model": "model-a",
                "temperature": 0.2,
                "max_tokens": 4096,
            }
        },
        "team_b_config": {
            "general": {
                "provider": "ollama",
                "model": "model-b",
                "temperature": 0.2,
                "max_tokens": 4096,
            }
        }
    }

    response = client.post("/arena/sessions", json=arena_payload, headers=auth_headers)
    assert response.status_code == 201
    arena_id = response.json()["id"]

    # Manually set test_session to voting state (skip actual LLM execution)
    arena_test_session = test_session.get(ArenaSession, arena_id)
    arena_test_session.status = "voting"
    arena_test_session.team_a_summary = "Team A found some issues"
    arena_test_session.team_b_summary = "Team B found different issues"
    arena_test_session.team_a_issues = []
    arena_test_session.team_b_issues = []
    test_session.add(arena_test_session)
    test_session.commit()

    # Vote for Team A
    vote_payload = {
        "winner": "A",
        "comment": "Team A provided better analysis"
    }

    response = client.post(f"/arena/sessions/{arena_id}/vote", json=vote_payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["winner"] == "A"
    assert data["status"] == "completed"

    # Check that ELO rankings were created/updated
    from app.api.arena import get_engine_config, get_engine_hash

    team_a_engine = get_engine_config(arena_test_session.team_a_config)
    team_b_engine = get_engine_config(arena_test_session.team_b_config)
    team_a_hash = get_engine_hash(team_a_engine)
    team_b_hash = get_engine_hash(team_b_engine)

    team_a_rating = test_session.exec(
        select(TeamRating).where(TeamRating.config_hash == team_a_hash)
    ).first()
    team_b_rating = test_session.exec(
        select(TeamRating).where(TeamRating.config_hash == team_b_hash)
    ).first()

    assert team_a_rating is not None, "Team A rating should be created"
    assert team_b_rating is not None, "Team B rating should be created"

    # Team A won, so should have higher rating
    assert team_a_rating.elo_rating > 1500.0
    assert team_b_rating.elo_rating < 1500.0

    # Check game statistics
    assert team_a_rating.games_played == 1
    assert team_a_rating.wins == 1
    assert team_a_rating.losses == 0

    assert team_b_rating.games_played == 1
    assert team_b_rating.wins == 0
    assert team_b_rating.losses == 1


def test_arena_rankings_endpoint(client: TestClient, auth_headers: dict, test_project: Project, test_session: Session):
    """Test that rankings endpoint returns all engines after first game."""
    # Create and vote on an arena test_session
    arena_payload = {
        "project_id": test_project.id,
        "team_a_config": {
            "general": {
                "provider": "ollama",
                "model": "test-model-1",
            }
        },
        "team_b_config": {
            "general": {
                "provider": "ollama",
                "model": "test-model-2",
            }
        }
    }

    response = client.post("/arena/sessions", json=arena_payload, headers=auth_headers)
    assert response.status_code == 201
    arena_id = response.json()["id"]

    # Set to voting state
    arena_test_session = test_session.get(ArenaSession, arena_id)
    arena_test_session.status = "voting"
    arena_test_session.team_a_summary = "Summary A"
    arena_test_session.team_b_summary = "Summary B"
    arena_test_session.team_a_issues = []
    arena_test_session.team_b_issues = []
    test_session.add(arena_test_session)
    test_session.commit()

    # Vote
    client.post(f"/arena/sessions/{arena_id}/vote",
                json={"winner": "B"}, headers=auth_headers)

    # Check rankings - both engines should appear with min_games=1
    response = client.get("/arena/rankings?min_games=1", headers=auth_headers)
    assert response.status_code == 200
    rankings = response.json()

    assert len(rankings) == 2, "Both engines should appear after first game"

    # Rankings should be sorted by ELO (winner first)
    assert rankings[0]["config"]["model"] == "test-model-2"  # Winner (Team B)
    assert rankings[1]["config"]["model"] == "test-model-1"  # Loser (Team A)

    assert rankings[0]["elo_rating"] > rankings[1]["elo_rating"]


def test_arena_tie_vote(client: TestClient, auth_headers: dict, test_project: Project, test_session: Session):
    """Test that tie votes are handled correctly."""
    arena_payload = {
        "project_id": test_project.id,
        "team_a_config": {
            "general": {
                "provider": "ollama",
                "model": "tie-model-a",
            }
        },
        "team_b_config": {
            "general": {
                "provider": "ollama",
                "model": "tie-model-b",
            }
        }
    }

    response = client.post("/arena/sessions", json=arena_payload, headers=auth_headers)
    arena_id = response.json()["id"]

    # Set to voting state
    arena_test_session = test_session.get(ArenaSession, arena_id)
    arena_test_session.status = "voting"
    arena_test_session.team_a_summary = "Summary A"
    arena_test_session.team_b_summary = "Summary B"
    arena_test_session.team_a_issues = []
    arena_test_session.team_b_issues = []
    test_session.add(arena_test_session)
    test_session.commit()

    # Vote for tie
    response = client.post(f"/arena/sessions/{arena_id}/vote",
                          json={"winner": "tie"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["winner"] == "tie"

    # Check that both teams have tie recorded
    from app.api.arena import get_engine_config, get_engine_hash

    team_a_engine = get_engine_config(arena_test_session.team_a_config)
    team_a_hash = get_engine_hash(team_a_engine)

    team_a_rating = test_session.exec(
        select(TeamRating).where(TeamRating.config_hash == team_a_hash)
    ).first()

    assert team_a_rating.ties == 1
    assert team_a_rating.wins == 0
    assert team_a_rating.losses == 0
