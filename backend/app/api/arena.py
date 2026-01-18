"""Arena API endpoints - system walki dwóch zespołów AI.

Endpoints:
- POST /arena/sessions - utwórz nową sesję Arena
- GET /arena/sessions - lista sesji użytkownika
- GET /arena/sessions/{id} - szczegóły sesji
- POST /arena/sessions/{id}/vote - zagłosuj na zwycięzcę
- GET /arena/rankings - rankingi zespołów
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select, func

from app.database import get_session
from app.models.user import User
from app.models.project import Project
from app.models.arena import (
    ArenaSession, TeamRating,
    ArenaSessionCreate, ArenaSessionRead, ArenaVoteCreate, TeamRatingRead
)
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/arena", tags=["arena"])


def get_engine_config(config: dict) -> dict:
    """Wyciągnij konfigurację silnika (provider/model) z config zespołu."""
    general = config.get("general", {}) if isinstance(config, dict) else {}
    provider = (general.get("provider") or "unknown").strip().lower()
    model = (general.get("model") or "unknown").strip()
    return {"provider": provider, "model": model}


def get_engine_hash(engine_config: dict) -> str:
    """Generuj unikalny hash dla silnika (provider/model)."""
    sorted_config = json.dumps(engine_config, sort_keys=True)
    return hashlib.sha256(sorted_config.encode()).hexdigest()


def calculate_elo(winner_rating: float, loser_rating: float, is_tie: bool = False) -> tuple[float, float]:
    """Oblicz nowe ratingi ELO po walce.

    Args:
        winner_rating: Aktualny rating zwycięzcy
        loser_rating: Aktualny rating przegranego
        is_tie: Czy był remis

    Returns:
        tuple: (nowy_rating_zwycięzcy, nowy_rating_przegranego)
    """
    K = 32  # Współczynnik K (jak szybko zmienia się rating)

    # Oczekiwana szansa na wygraną
    expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
    expected_loser = 1 - expected_winner

    if is_tie:
        # Remis - każdy dostaje 0.5
        new_winner = winner_rating + K * (0.5 - expected_winner)
        new_loser = loser_rating + K * (0.5 - expected_loser)
    else:
        # Zwycięstwo/przegrana
        new_winner = winner_rating + K * (1 - expected_winner)
        new_loser = loser_rating + K * (0 - expected_loser)

    return new_winner, new_loser


async def run_arena_in_background(
    session_id: int,
    api_keys: dict | None = None,
    engine_override=None,
):
    """Uruchom analizę Arena w tle."""
    from app.database import Session as DBSession, engine
    from app.orchestrators.arena import ArenaOrchestrator

    with DBSession(engine_override or engine) as session:
        orchestrator = ArenaOrchestrator(session)
        await orchestrator.run_arena(session_id, api_keys)


@router.post("/sessions", response_model=ArenaSessionRead, status_code=status.HTTP_201_CREATED)
async def create_arena_session(
    data: ArenaSessionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Utwórz nową sesję Arena i uruchom analizę.

    Wymagane pola w team_a_config i team_b_config:
    - general: {"provider": "...", "model": "..."}
    """
    # Sprawdź czy projekt istnieje
    project = session.get(Project, data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nie istnieje")

    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Brak dostępu do projektu")

    # Walidacja konfiguracji - wymagamy tylko general (pozostałe role ignorujemy)
    logger.info(
        "🔍 Arena validation: team_a_config keys=%s, team_b_config keys=%s",
        list(data.team_a_config.keys()) if isinstance(data.team_a_config, dict) else 'NOT A DICT',
        list(data.team_b_config.keys()) if isinstance(data.team_b_config, dict) else 'NOT A DICT'
    )

    for team_name, config in [("A", data.team_a_config), ("B", data.team_b_config)]:
        if not isinstance(config, dict):
            raise HTTPException(
                status_code=422,
                detail=f"Zespół {team_name}: konfiguracja musi być obiektem"
            )

        config_keys = set(config.keys())
        if "general" not in config:
            raise HTTPException(
                status_code=422,
                detail=f"Zespół {team_name}: brak konfiguracji dla roli 'general'. Otrzymano klucze: {', '.join(sorted(config_keys))}"
            )

        general_config = config.get("general", {})
        if not isinstance(general_config, dict):
            raise HTTPException(
                status_code=422,
                detail=f"Zespół {team_name}, rola general: konfiguracja musi być obiektem"
            )

        provider = general_config.get("provider")
        model = general_config.get("model")

        # Validate provider
        if provider is None:
            raise HTTPException(
                status_code=422,
                detail=f"Zespół {team_name}, rola general: brak pola 'provider'"
            )
        if not isinstance(provider, str):
            raise HTTPException(
                status_code=422,
                detail=f"Zespół {team_name}, rola general: 'provider' musi być stringiem (otrzymano: {type(provider).__name__})"
            )
        if not provider.strip():
            raise HTTPException(
                status_code=422,
                detail=f"Zespół {team_name}, rola general: 'provider' nie może być pustym stringiem"
            )

        # Validate model
        if model is None:
            raise HTTPException(
                status_code=422,
                detail=f"Zespół {team_name}, rola general: brak pola 'model'"
            )
        if not isinstance(model, str):
            raise HTTPException(
                status_code=422,
                detail=f"Zespół {team_name}, rola general: 'model' musi być stringiem (otrzymano: {type(model).__name__})"
            )
        if not model.strip():
            raise HTTPException(
                status_code=422,
                detail=f"Zespół {team_name}, rola general: 'model' nie może być pustym stringiem"
            )

    # Utwórz sesję
    arena_session = ArenaSession(
        project_id=data.project_id,
        created_by=current_user.id,
        status="pending",
        team_a_config=data.team_a_config,
        team_b_config=data.team_b_config
    )
    session.add(arena_session)
    session.commit()
    session.refresh(arena_session)

    # Uruchom analizę w tle
    background_tasks.add_task(
        run_arena_in_background,
        arena_session.id,
        data.api_keys,
        session.get_bind(),
    )

    logger.info(f"Arena session {arena_session.id} created for project {data.project_id}")

    return ArenaSessionRead(**arena_session.model_dump())


@router.get("/sessions", response_model=list[ArenaSessionRead])
async def list_arena_sessions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Lista sesji Arena użytkownika."""
    query = (
        select(ArenaSession)
        .where(ArenaSession.created_by == current_user.id)
        .order_by(ArenaSession.created_at.desc())
    )
    sessions = session.exec(query).all()
    return [ArenaSessionRead(**s.model_dump()) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ArenaSessionRead)
async def get_arena_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Pobierz szczegóły sesji Arena."""
    arena_session = session.get(ArenaSession, session_id)

    if not arena_session:
        raise HTTPException(status_code=404, detail="Sesja nie istnieje")

    if arena_session.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Brak dostępu do sesji")

    return ArenaSessionRead(**arena_session.model_dump())


@router.post("/sessions/{session_id}/vote", response_model=ArenaSessionRead)
async def vote_arena_session(
    session_id: int,
    vote: ArenaVoteCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Zagłosuj na zwycięzcę sesji Arena.

    Możliwe wartości winner:
    - "A" - Zespół A wygrał
    - "B" - Zespół B wygrał
    - "tie" - Remis
    """
    arena_session = session.get(ArenaSession, session_id)

    if not arena_session:
        raise HTTPException(status_code=404, detail="Sesja nie istnieje")

    if arena_session.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Brak dostępu do sesji")

    if arena_session.status != "voting":
        raise HTTPException(
            status_code=400,
            detail=f"Nie można głosować - sesja ma status '{arena_session.status}'"
        )

    if arena_session.winner:
        raise HTTPException(status_code=400, detail="Już zagłosowano w tej sesji")

    # Zapisz głos
    arena_session.winner = vote.winner
    arena_session.vote_comment = vote.comment
    arena_session.voted_at = datetime.now(timezone.utc)
    arena_session.status = "completed"
    arena_session.completed_at = datetime.now(timezone.utc)

    # Aktualizuj rankingi ELO
    team_a_engine = get_engine_config(arena_session.team_a_config)
    team_b_engine = get_engine_config(arena_session.team_b_config)
    team_a_hash = get_engine_hash(team_a_engine)
    team_b_hash = get_engine_hash(team_b_engine)

    # Pobierz lub utwórz ratingi dla obu zespołów
    team_a_rating = session.exec(
        select(TeamRating).where(TeamRating.config_hash == team_a_hash)
    ).first()
    if not team_a_rating:
        team_a_rating = TeamRating(
            config_hash=team_a_hash,
            config=team_a_engine
        )
        session.add(team_a_rating)

    team_b_rating = session.exec(
        select(TeamRating).where(TeamRating.config_hash == team_b_hash)
    ).first()
    if not team_b_rating:
        team_b_rating = TeamRating(
            config_hash=team_b_hash,
            config=team_b_engine
        )
        session.add(team_b_rating)

    session.commit()
    session.refresh(team_a_rating)
    session.refresh(team_b_rating)

    # Oblicz nowe ratingi
    if vote.winner == "A":
        new_a, new_b = calculate_elo(team_a_rating.elo_rating, team_b_rating.elo_rating)
        team_a_rating.wins += 1
        team_b_rating.losses += 1
    elif vote.winner == "B":
        new_b, new_a = calculate_elo(team_b_rating.elo_rating, team_a_rating.elo_rating)
        team_a_rating.losses += 1
        team_b_rating.wins += 1
    else:  # tie
        new_a, new_b = calculate_elo(
            team_a_rating.elo_rating, team_b_rating.elo_rating, is_tie=True
        )
        team_a_rating.ties += 1
        team_b_rating.ties += 1

    team_a_rating.elo_rating = new_a
    team_b_rating.elo_rating = new_b
    team_a_rating.games_played += 1
    team_b_rating.games_played += 1
    team_a_rating.updated_at = datetime.now(timezone.utc)
    team_b_rating.updated_at = datetime.now(timezone.utc)

    session.add(arena_session)
    session.add(team_a_rating)
    session.add(team_b_rating)
    session.commit()
    session.refresh(arena_session)

    logger.info(f"Arena session {session_id} voted: winner={vote.winner}")

    return ArenaSessionRead(**arena_session.model_dump())


@router.get("/rankings", response_model=list[TeamRatingRead])
async def get_arena_rankings(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    min_games: int = 1
):
    """Pobierz rankingi zespołów z Arena.

    Rankingi są sortowane po ELO rating (najlepsze na górze).
    Można filtrować po minimalnej liczbie gier.
    """
    query = (
        select(TeamRating)
        .where(TeamRating.games_played >= min_games)
        .order_by(TeamRating.elo_rating.desc())
    )
    ratings = session.exec(query).all()

    result = []
    for r in ratings:
        win_rate = (r.wins / r.games_played * 100) if r.games_played > 0 else 0
        result.append(TeamRatingRead(
            **r.model_dump(),
            win_rate=round(win_rate, 1)
        ))

    return result
