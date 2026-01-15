#!/usr/bin/env python3
"""Seed large number of Arena sessions to test rankings.

Creates many users/projects and 1000 arena sessions with votes to update ELO.
Idempotency: creates new users/projects with unique suffix to avoid conflicts.
"""
import argparse
import os
import random
import string
import sys
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from sqlalchemy import text

from app.database import engine, create_db_and_tables
from app.models.user import User
from app.models.project import Project
from app.models.file import File
from app.models.arena import ArenaSession, TeamRating
from app.utils.auth import hash_password
from app.api.arena import calculate_elo, get_config_hash


DEFAULT_USERS = 50
DEFAULT_SESSIONS = 1000
DEFAULT_PROJECTS_PER_USER = 1
DEFAULT_SEED = 42
DEFAULT_TEAM_POOL = 50

ROLE_NAMES = ["general", "security", "performance", "style"]
MODEL_POOL = [
    "mock-fast",
    "mock-smart",
    "qwen2.5-coder:latest",
    "llama3.1:8b",
    "mixtral-8x7b",
    "gemini-1.5-flash",
    "gpt-4o-mini",
]
PROVIDER_POOL = ["mock", "ollama", "gemini", "openai"]

SAMPLE_CODE = """def add(a, b):
    return a + b

def slow_sum(items):
    total = 0
    for item in items:
        total += item
    return total
"""


def _random_suffix(length: int = 6) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def build_team_config() -> dict:
    config = {}
    for role in ROLE_NAMES:
        provider = random.choice(PROVIDER_POOL)
        model = random.choice(MODEL_POOL)
        config[role] = {"provider": provider, "model": model}
    return config


def build_team_pool(size: int) -> list[dict]:
    pool: list[dict] = []
    seen: set[str] = set()
    attempts = 0
    while len(pool) < size and attempts < size * 20:
        attempts += 1
        config = build_team_config()
        config_hash = get_config_hash(config)
        if config_hash in seen:
            continue
        seen.add(config_hash)
        pool.append(config)
    return pool


def seed_users(session: Session, count: int) -> list[User]:
    existing = session.exec(select(User).where(User.username.like("seeduser%"))).all()
    if len(existing) >= count:
        return existing[:count]

    users: list[User] = list(existing)
    idx = len(existing)
    while len(users) < count:
        suffix = _random_suffix()
        email = f"seeduser{idx}_{suffix}@local.test"
        username = f"seeduser{idx}_{suffix}"
        email_exists = session.exec(select(User).where(User.email == email)).first()
        username_exists = session.exec(select(User).where(User.username == username)).first()
        if email_exists or username_exists:
            continue
        user = User(
            email=email,
            username=username,
            hashed_password=hash_password("Test1234!"),
            is_active=True,
            is_superuser=False,
        )
        session.add(user)
        users.append(user)
        idx += 1

    session.commit()
    for user in users:
        session.refresh(user)
    return users


def seed_projects_and_files(session: Session, users: list[User], projects_per_user: int) -> list[Project]:
    projects: list[Project] = []
    for user in users:
        for i in range(projects_per_user):
            project = Project(
                name=f"Seed Project {user.username} #{i + 1}",
                description="Seed project for ranking tests",
                owner_id=user.id,
            )
            session.add(project)
            projects.append(project)
    session.commit()
    for project in projects:
        session.refresh(project)

    for project in projects:
        file = File(
            project_id=project.id,
            name="seed.py",
            content=SAMPLE_CODE,
            language="python",
            size_bytes=len(SAMPLE_CODE.encode("utf-8")),
            content_hash=File.compute_hash(SAMPLE_CODE),
        )
        session.add(file)
    session.commit()
    return projects


def update_team_ratings(
    session: Session,
    team_a_config: dict,
    team_b_config: dict,
    winner: str,
    ratings_cache: dict[str, TeamRating],
):
    team_a_hash = get_config_hash(team_a_config)
    team_b_hash = get_config_hash(team_b_config)

    team_a_rating = ratings_cache.get(team_a_hash)
    if not team_a_rating:
        team_a_rating = session.exec(select(TeamRating).where(TeamRating.config_hash == team_a_hash)).first()
        if not team_a_rating:
            team_a_rating = TeamRating(config_hash=team_a_hash, config=team_a_config)
            session.add(team_a_rating)
            session.commit()
            session.refresh(team_a_rating)
        ratings_cache[team_a_hash] = team_a_rating

    team_b_rating = ratings_cache.get(team_b_hash)
    if not team_b_rating:
        team_b_rating = session.exec(select(TeamRating).where(TeamRating.config_hash == team_b_hash)).first()
        if not team_b_rating:
            team_b_rating = TeamRating(config_hash=team_b_hash, config=team_b_config)
            session.add(team_b_rating)
            session.commit()
            session.refresh(team_b_rating)
        ratings_cache[team_b_hash] = team_b_rating

    if winner == "A":
        new_a, new_b = calculate_elo(team_a_rating.elo_rating, team_b_rating.elo_rating)
        team_a_rating.wins += 1
        team_b_rating.losses += 1
    elif winner == "B":
        new_b, new_a = calculate_elo(team_b_rating.elo_rating, team_a_rating.elo_rating)
        team_a_rating.losses += 1
        team_b_rating.wins += 1
    else:
        new_a, new_b = calculate_elo(team_a_rating.elo_rating, team_b_rating.elo_rating, is_tie=True)
        team_a_rating.ties += 1
        team_b_rating.ties += 1

    team_a_rating.elo_rating = new_a
    team_b_rating.elo_rating = new_b
    team_a_rating.games_played += 1
    team_b_rating.games_played += 1
    team_a_rating.updated_at = datetime.now(timezone.utc)
    team_b_rating.updated_at = datetime.now(timezone.utc)

    session.add(team_a_rating)
    session.add(team_b_rating)


def seed_sessions(
    session: Session,
    users: list[User],
    projects: list[Project],
    session_count: int,
    team_pool: list[dict],
):
    ratings_cache: dict[str, TeamRating] = {}
    batch_size = 100
    now = datetime.now(timezone.utc)

    for i in range(session_count):
        user = random.choice(users)
        project = random.choice(projects)
        team_a_config = random.choice(team_pool)
        team_b_config = random.choice(team_pool)
        if team_a_config == team_b_config:
            team_b_config = random.choice(team_pool)
        winner = random.choice(["A", "B", "tie"])

        arena_session = ArenaSession(
            project_id=project.id,
            created_by=user.id,
            status="completed",
            team_a_config=team_a_config,
            team_b_config=team_b_config,
            team_a_summary="Seed summary A",
            team_b_summary="Seed summary B",
            team_a_issues=[],
            team_b_issues=[],
            winner=winner,
            vote_comment="Seed vote",
            voted_at=now,
            created_at=now,
            completed_at=now,
        )
        session.add(arena_session)

        update_team_ratings(session, team_a_config, team_b_config, winner, ratings_cache)

        if (i + 1) % batch_size == 0:
            session.commit()
            print(f"Created {i + 1}/{session_count} arena sessions...")

    session.commit()
    print(f"Created {session_count} arena sessions and updated rankings.")


def main():
    parser = argparse.ArgumentParser(description="Seed arena sessions and rankings.")
    parser.add_argument("--users", type=int, default=DEFAULT_USERS, help="Number of users to create")
    parser.add_argument("--sessions", type=int, default=DEFAULT_SESSIONS, help="Number of arena sessions to create")
    parser.add_argument(
        "--projects-per-user",
        type=int,
        default=DEFAULT_PROJECTS_PER_USER,
        help="Projects per user",
    )
    parser.add_argument("--team-pool", type=int, default=DEFAULT_TEAM_POOL, help="Unique team configs to reuse")
    parser.add_argument("--reset-arena", action="store_true", help="Clear arena sessions and team ratings before seeding")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)
    create_db_and_tables()

    with Session(engine) as session:
        if args.reset_arena:
            session.exec(text("DELETE FROM arena_sessions"))
            session.exec(text("DELETE FROM team_ratings"))
            session.commit()
        users = seed_users(session, args.users)
        projects = seed_projects_and_files(session, users, args.projects_per_user)
        team_pool = build_team_pool(args.team_pool)
        print(f"Using team pool size: {len(team_pool)}")
        seed_sessions(session, users, projects, args.sessions, team_pool)


if __name__ == "__main__":
    main()
