"""API endpoints dla Combat Arena - porównywanie pełnych schematów review.

Endpointy:
- POST /arena/sessions - utworzenie nowej sesji Arena
- GET /arena/sessions/{session_id} - pobranie szczegółów sesji
- POST /arena/sessions/{session_id}/vote - głosowanie na zwycięzcę
- GET /arena/rankings - ranking schematów (ELO)
- GET /arena/sessions - lista sesji Arena
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlmodel import Session, select, func, desc
from app.database import get_session
from app.models.user import User
from app.models.project import Project
from app.models.arena import (
    ArenaSession, SchemaRating,
    ArenaSessionCreate, ArenaSessionRead, ArenaVoteCreate, SchemaRatingRead
)
from app.models.review import Review, ReviewRead, Issue
from app.api.deps import get_current_user
from app.orchestrators.arena import ArenaOrchestrator
from app.utils.access import verify_project_access
from app.utils.cache import cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/arena", tags=["arena"])


async def run_arena_in_background(
    arena_session_id: int,
    api_keys: dict[str, str] | None = None
):
    """Uruchom sesję Arena w tle.

    Funkcja background task dla FastAPI.
    Tworzy osobną sesję bazodanową i uruchamia ArenaOrchestrator.

    Args:
        arena_session_id: ID sesji Arena do uruchomienia
        api_keys: Klucze API dla providerów
    """
    from app.database import Session, engine

    with Session(engine) as session:
        orchestrator = ArenaOrchestrator(session)
        await orchestrator.conduct_arena(arena_session_id, api_keys)


@router.post("/sessions", response_model=ArenaSessionRead, status_code=status.HTTP_201_CREATED)
async def create_arena_session(
    arena_data: ArenaSessionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Utwórz nową sesję Combat Arena.

    Proces:
    1. Waliduj dostęp do projektu
    2. Waliduj schematy (oba muszą mieć wszystkie 4 role)
    3. Utwórz ArenaSession
    4. Uruchom w tle (ArenaOrchestrator przeprowadzi oba review)

    Args:
        arena_data: Dane do utworzenia sesji (project_id, schema_a_config, schema_b_config)
        background_tasks: FastAPI BackgroundTasks
        current_user: Zalogowany użytkownik
        session: Sesja bazodanowa

    Returns:
        Utworzona ArenaSession (status: "pending")

    Raises:
        HTTPException 404: Jeśli projekt nie istnieje
        HTTPException 400: Jeśli schematy są nieprawidłowe
    """
    # Waliduj dostęp do projektu
    project = await verify_project_access(arena_data.project_id, current_user, session)

    # Waliduj schematy - oba muszą mieć wszystkie 4 role
    required_roles = {"general", "security", "performance", "style"}

    schema_a_roles = set(arena_data.schema_a_config.keys())
    if schema_a_roles != required_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Schema A musi mieć wszystkie 4 role",
                "required": list(required_roles),
                "provided": list(schema_a_roles),
                "missing": list(required_roles - schema_a_roles),
                "extra": list(schema_a_roles - required_roles)
            }
        )

    schema_b_roles = set(arena_data.schema_b_config.keys())
    if schema_b_roles != required_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Schema B musi mieć wszystkie 4 role",
                "required": list(required_roles),
                "provided": list(schema_b_roles),
                "missing": list(required_roles - schema_b_roles),
                "extra": list(schema_b_roles - required_roles)
            }
        )

    # Waliduj strukturę każdej konfiguracji roli (musi mieć provider i model)
    for schema_name, schema_config in [("A", arena_data.schema_a_config), ("B", arena_data.schema_b_config)]:
        for role, config in schema_config.items():
            if "provider" not in config or "model" not in config:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Schema {schema_name}, rola '{role}': brakuje 'provider' lub 'model'"
                )

    # Konwertuj AgentConfig do dict dla zapisu w JSON column
    schema_a_dict = {
        role: {k: v for k, v in (config.model_dump() if hasattr(config, "model_dump") else config).items() if k != "prompt"}
        for role, config in arena_data.schema_a_config.items()
    }
    schema_b_dict = {
        role: {k: v for k, v in (config.model_dump() if hasattr(config, "model_dump") else config).items() if k != "prompt"}
        for role, config in arena_data.schema_b_config.items()
    }

    # Utwórz ArenaSession
    arena_session = ArenaSession(
        project_id=arena_data.project_id,
        created_by=current_user.id,
        status="pending",
        schema_a_config=schema_a_dict,
        schema_b_config=schema_b_dict
    )
    session.add(arena_session)
    session.commit()
    session.refresh(arena_session)

    logger.info(
        f"Arena session {arena_session.id} utworzona - "
        f"projekt: {project.name}, użytkownik: {current_user.username}"
    )

    # Uruchom w tle
    background_tasks.add_task(
        run_arena_in_background,
        arena_session.id,
        arena_data.api_keys
    )

    # Zwróć odpowiedź
    return ArenaSessionRead(
        id=arena_session.id,
        project_id=arena_session.project_id,
        created_by=arena_session.created_by,
        status=arena_session.status,
        schema_a_config=arena_session.schema_a_config,
        schema_b_config=arena_session.schema_b_config,
        review_a_id=arena_session.review_a_id,
        review_b_id=arena_session.review_b_id,
        winner=arena_session.winner,
        vote_comment=arena_session.vote_comment,
        voter_id=arena_session.voter_id,
        voted_at=arena_session.voted_at,
        error_message=arena_session.error_message,
        created_at=arena_session.created_at,
        completed_at=arena_session.completed_at
    )


@router.get("/sessions/{session_id}", response_model=ArenaSessionRead)
async def get_arena_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Pobierz szczegóły sesji Arena.

    Args:
        session_id: ID sesji Arena
        current_user: Zalogowany użytkownik
        session: Sesja bazodanowa

    Returns:
        ArenaSession z pełnymi danymi

    Raises:
        HTTPException 404: Jeśli sesja nie istnieje
    """
    arena_session = session.get(ArenaSession, session_id)
    if not arena_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arena session {session_id} nie istnieje"
        )

    # Sprawdź dostęp do projektu
    await verify_project_access(arena_session.project_id, current_user, session)

    return ArenaSessionRead(
        id=arena_session.id,
        project_id=arena_session.project_id,
        created_by=arena_session.created_by,
        status=arena_session.status,
        schema_a_config=arena_session.schema_a_config,
        schema_b_config=arena_session.schema_b_config,
        review_a_id=arena_session.review_a_id,
        review_b_id=arena_session.review_b_id,
        winner=arena_session.winner,
        vote_comment=arena_session.vote_comment,
        voter_id=arena_session.voter_id,
        voted_at=arena_session.voted_at,
        error_message=arena_session.error_message,
        created_at=arena_session.created_at,
        completed_at=arena_session.completed_at
    )


@router.post("/sessions/{session_id}/vote", response_model=ArenaSessionRead)
async def vote_arena_session(
    session_id: int,
    vote_data: ArenaVoteCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Głosuj na zwycięzcę w sesji Arena.

    Proces:
    1. Waliduj sesję (musi być completed)
    2. Waliduj że nie zagłosowano wcześniej
    3. Zapisz głos
    4. Zaktualizuj rankingi ELO

    Args:
        session_id: ID sesji Arena
        vote_data: Dane głosowania (winner: A/B/tie, comment)
        current_user: Zalogowany użytkownik
        session: Sesja bazodanowa

    Returns:
        Zaktualizowana ArenaSession z wynikiem głosowania

    Raises:
        HTTPException 404: Jeśli sesja nie istnieje
        HTTPException 400: Jeśli sesja nie jest completed lub już zagłosowano
    """
    arena_session = session.get(ArenaSession, session_id)
    if not arena_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arena session {session_id} nie istnieje"
        )

    # Sprawdź dostęp do projektu
    await verify_project_access(arena_session.project_id, current_user, session)

    # Sprawdź status sesji
    if arena_session.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nie można głosować - sesja ma status '{arena_session.status}', wymagany 'completed'"
        )

    # Sprawdź czy już zagłosowano
    if arena_session.winner is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"W tej sesji już zagłosowano - zwycięzca: {arena_session.winner}"
        )

    logger.info(
        f"Arena session {session_id}: zapisuję głos użytkownika {current_user.username} - "
        f"zwycięzca: {vote_data.winner}"
    )

    # Użyj orchestratora do zapisania głosu i aktualizacji ELO
    orchestrator = ArenaOrchestrator(session)
    updated_session = await orchestrator.submit_vote(
        arena_session_id=session_id,
        winner=vote_data.winner,
        voter_id=current_user.id,
        comment=vote_data.comment
    )

    return ArenaSessionRead(
        id=updated_session.id,
        project_id=updated_session.project_id,
        created_by=updated_session.created_by,
        status=updated_session.status,
        schema_a_config=updated_session.schema_a_config,
        schema_b_config=updated_session.schema_b_config,
        review_a_id=updated_session.review_a_id,
        review_b_id=updated_session.review_b_id,
        winner=updated_session.winner,
        vote_comment=updated_session.vote_comment,
        voter_id=updated_session.voter_id,
        voted_at=updated_session.voted_at,
        error_message=updated_session.error_message,
        created_at=updated_session.created_at,
        completed_at=updated_session.completed_at
    )


@router.get("/rankings", response_model=list[SchemaRatingRead])
async def get_arena_rankings(
    limit: int = Query(default=50, ge=1, le=200, description="Liczba wyników do zwrócenia"),
    min_games: int = Query(default=3, ge=0, description="Minimalna liczba rozegranych gier"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Pobierz ranking schematów według ELO.

    Zwraca schematy posortowane według ratingu ELO (malejąco).
    Można filtrować po minimalnej liczbie rozegranych gier.

    Args:
        limit: Maksymalna liczba wyników (1-200, domyślnie 50)
        min_games: Minimalna liczba rozegranych gier (domyślnie 3)
        current_user: Zalogowany użytkownik
        session: Sesja bazodanowa

    Returns:
        Lista SchemaRating posortowana według ELO (malejąco)
    """
    cache_key = f"arena:rankings:limit:{limit}:min_games:{min_games}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Query z filtrem i sortowaniem
    stmt = (
        select(SchemaRating)
        .where(SchemaRating.games_played >= min_games)
        .order_by(desc(SchemaRating.elo_rating))
        .limit(limit)
    )

    ratings = session.exec(stmt).all()

    response = [
        SchemaRatingRead(
            id=rating.id,
            schema_hash=rating.schema_hash,
            schema_config=rating.schema_config,
            elo_rating=rating.elo_rating,
            games_played=rating.games_played,
            wins=rating.wins,
            losses=rating.losses,
            ties=rating.ties,
            avg_issues_found=rating.avg_issues_found,
            last_used_at=rating.last_used_at,
            created_at=rating.created_at,
            updated_at=rating.updated_at
        )
        for rating in ratings
    ]

    cache.set(cache_key, [item.model_dump() for item in response])
    return response


@router.get("/sessions", response_model=list[ArenaSessionRead])
async def list_arena_sessions(
    project_id: int | None = Query(default=None, description="Filtruj po project_id"),
    status_filter: str | None = Query(default=None, description="Filtruj po statusie"),
    limit: int = Query(default=20, ge=1, le=100, description="Liczba wyników"),
    offset: int = Query(default=0, ge=0, description="Offset dla paginacji"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Pobierz listę sesji Arena.

    Zwraca sesje posortowane według daty utworzenia (malejąco).
    Można filtrować po project_id i statusie.

    Args:
        project_id: Opcjonalnie filtruj po ID projektu
        status_filter: Opcjonalnie filtruj po statusie (pending/running/completed/failed)
        limit: Maksymalna liczba wyników (1-100, domyślnie 20)
        offset: Offset dla paginacji (domyślnie 0)
        current_user: Zalogowany użytkownik
        session: Sesja bazodanowa

    Returns:
        Lista ArenaSession posortowana według created_at (malejąco)
    """
    # Buduj query
    stmt = select(ArenaSession)

    # Filtr po project_id (jeśli podany, waliduj dostęp)
    if project_id is not None:
        await verify_project_access(project_id, current_user, session)
        stmt = stmt.where(ArenaSession.project_id == project_id)

    # Filtr po statusie
    if status_filter:
        stmt = stmt.where(ArenaSession.status == status_filter)

    # Sortowanie i paginacja
    stmt = stmt.order_by(desc(ArenaSession.created_at)).offset(offset).limit(limit)

    arena_sessions = session.exec(stmt).all()

    return [
        ArenaSessionRead(
            id=arena.id,
            project_id=arena.project_id,
            created_by=arena.created_by,
            status=arena.status,
            schema_a_config=arena.schema_a_config,
            schema_b_config=arena.schema_b_config,
            review_a_id=arena.review_a_id,
            review_b_id=arena.review_b_id,
            winner=arena.winner,
            vote_comment=arena.vote_comment,
            voter_id=arena.voter_id,
            voted_at=arena.voted_at,
            error_message=arena.error_message,
            created_at=arena.created_at,
            completed_at=arena.completed_at
        )
        for arena in arena_sessions
    ]

@router.get("/stats")
async def get_arena_stats(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Pobierz globalne statystyki Arena (jak LLM Arena).

    Zwraca:
    - Całkowitą liczbę głosów
    - Liczbę unikalnych głosujących
    - Liczbę schematów w rankingu
    - Ostatnie głosy
    - Top 3 schematy

    Returns:
        Dict ze statystykami Arena
    """
    cache_key = "arena:stats"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Całkowita liczba sesji z głosami
    total_votes_stmt = select(func.count(ArenaSession.id)).where(ArenaSession.winner.isnot(None))
    total_votes = session.exec(total_votes_stmt).one()

    # Liczba unikalnych głosujących
    unique_voters_stmt = select(func.count(func.distinct(ArenaSession.voter_id))).where(ArenaSession.voter_id.isnot(None))
    unique_voters = session.exec(unique_voters_stmt).one()

    # Liczba schematów w rankingu
    total_schemas_stmt = select(func.count(SchemaRating.id))
    total_schemas = session.exec(total_schemas_stmt).one()

    # Top 3 schematy
    top_schemas_stmt = (
        select(SchemaRating)
        .where(SchemaRating.games_played >= 1)
        .order_by(desc(SchemaRating.elo_rating))
        .limit(3)
    )
    top_schemas = session.exec(top_schemas_stmt).all()

    # Ostatnie 5 głosów
    recent_votes_stmt = (
        select(ArenaSession)
        .where(ArenaSession.winner.isnot(None))
        .order_by(desc(ArenaSession.voted_at))
        .limit(5)
    )
    recent_votes = session.exec(recent_votes_stmt).all()

    response = {
        "total_votes": total_votes,
        "unique_voters": unique_voters,
        "total_schemas": total_schemas,
        "top_schemas": [
            {
                "schema_hash": s.schema_hash,
                "elo_rating": round(s.elo_rating, 1),
                "games_played": s.games_played,
                "win_rate": round((s.wins / s.games_played * 100) if s.games_played > 0 else 0, 1)
            }
            for s in top_schemas
        ],
        "recent_votes": [
            {
                "session_id": v.id,
                "winner": v.winner,
                "voted_at": v.voted_at.isoformat() if v.voted_at else None,
                "project_id": v.project_id
            }
            for v in recent_votes
        ]
    }

    cache.set(cache_key, response)
    return response
