"""Review API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload
from app.database import get_session
from app.models.user import User
from app.models.project import Project
from app.models.review import (
    Review, ReviewAgent, Issue, Suggestion,
    ReviewCreate, ReviewRead, ReviewAgentRead, IssueRead, IssueReadWithSuggestions,
    SuggestionRead, IssueUpdate
)
from app.api.deps import get_current_user
from app.orchestrators.review import ReviewOrchestrator
from app.utils.access import verify_project_access, verify_review_access

router = APIRouter(prefix="/reviews", tags=["reviews"])
projects_router = APIRouter(prefix="/projects/{project_id}/reviews", tags=["reviews"])


async def run_review_in_background(
    review_id: int,
    provider: str | None,
    model: str | None,
    api_keys: dict[str, str] | None = None,
    agent_configs: dict | None = None
):
    """Run review in background task."""
    from app.database import Session, engine
    from app.models.review import AgentConfig

    # Convert dict to AgentConfig objects if provided
    parsed_agent_configs = None
    if agent_configs:
        parsed_agent_configs = {}
        for role, config in agent_configs.items():
            if isinstance(config, dict):
                parsed_agent_configs[role] = AgentConfig(**config)
            else:
                parsed_agent_configs[role] = config

    with Session(engine) as session:
        orchestrator = ReviewOrchestrator(session)
        await orchestrator.conduct_review(review_id, provider, model, api_keys, parsed_agent_configs)


@projects_router.post("", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
async def create_review(
    project_id: int,
    review_data: ReviewCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Utwórz i uruchom nowy review dla projektu.

    Wspiera dwa tryby:
    1. COUNCIL MODE (domyślny): Agenci współpracują nad jednym review
       - Podaj agent_roles i opcjonalnie agent_configs
    2. COMBAT ARENA: Porównanie dwóch pełnych schematów (A vs B)
       - Nie używaj tego endpoint! Użyj POST /arena/sessions zamiast tego

    Args:
        project_id: ID projektu do przeanalizowania
        review_data: Konfiguracja review (tryb, role, konfiguracje agentów)
        background_tasks: FastAPI BackgroundTasks
        current_user: Zalogowany użytkownik
        session: Sesja bazodanowa

    Returns:
        Utworzony Review (status: "pending")

    Raises:
        HTTPException 400: Jeśli tryb Arena użyty bezpośrednio
        HTTPException 404: Jeśli projekt nie istnieje
    """
    project = await verify_project_access(project_id, current_user, session)

    # === WALIDACJA TRYBU ===
    # Arena review MUSZĄ być tworzone przez POST /arena/sessions, nie bezpośrednio
    review_mode = review_data.review_mode or "council"

    if review_mode == "combat_arena":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Combat Arena nie może być utworzone bezpośrednio przez ten endpoint",
                "hint": "Użyj POST /arena/sessions aby utworzyć sesję Arena",
                "provided_mode": review_mode
            }
        )

    # Handle deprecated conversation_mode field
    if review_data.conversation_mode and not review_data.review_mode:
        review_mode = review_data.conversation_mode
        if review_mode not in ["council", "combat_arena"]:
            review_mode = "council"

    # === TWORZENIE COUNCIL REVIEW ===
    moderator_type = review_data.moderator_type or "debate"

    review = Review(
        project_id=project_id,
        created_by=current_user.id,
        status="pending",
        review_mode=review_mode,  # "council"
        moderator_type=moderator_type  # "debate", "consensus", or "strategic"
    )
    session.add(review)
    session.commit()
    session.refresh(review)

    # Create agent records
    for role in review_data.agent_roles:
        # Use per-agent config if available, otherwise fall back to global config
        if review_data.agent_configs and role in review_data.agent_configs:
            config = review_data.agent_configs[role]
            provider = config.provider
            model = config.model
        else:
            provider = review_data.provider or "mock"
            model = review_data.model or "default"

        agent = ReviewAgent(
            review_id=review.id,
            role=role,
            provider=provider,
            model=model,
            parsed_successfully=False
        )
        session.add(agent)

    session.commit()

    # Start review in background with agent configs
    agent_configs_dict = None
    if review_data.agent_configs:
        agent_configs_dict = {
            role: config.model_dump() for role, config in review_data.agent_configs.items()
        }

    background_tasks.add_task(
        run_review_in_background,
        review.id,
        review_data.provider,
        review_data.model,
        review_data.api_keys,
        agent_configs_dict
    )

    return ReviewRead(
        **review.model_dump(),
        agent_count=len(review_data.agent_roles),
        issue_count=0
    )


@projects_router.get("", response_model=list[ReviewRead])
async def list_project_reviews(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """List all reviews for a project."""
    await verify_project_access(project_id, current_user, session)

    statement = (
        select(Review)
        .where(Review.project_id == project_id)
        .order_by(Review.created_at.desc())
    )
    reviews = session.exec(statement).all()

    # Build responses with counts
    result = []
    for review in reviews:
        agent_count_stmt = select(func.count(ReviewAgent.id)).where(ReviewAgent.review_id == review.id)
        agent_count = session.exec(agent_count_stmt).one()

        issue_count_stmt = select(func.count(Issue.id)).where(Issue.review_id == review.id)
        issue_count = session.exec(issue_count_stmt).one()

        result.append(ReviewRead(
            **review.model_dump(),
            agent_count=agent_count,
            issue_count=issue_count
        ))

    return result


@router.get("/{review_id}", response_model=ReviewRead)
async def get_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get a specific review."""
    review = session.get(Review, review_id)

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    # Verify access through project
    project = session.get(Project, review.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this review"
        )

    # Get counts
    agent_count_stmt = select(func.count(ReviewAgent.id)).where(ReviewAgent.review_id == review.id)
    agent_count = session.exec(agent_count_stmt).one()

    issue_count_stmt = select(func.count(Issue.id)).where(Issue.review_id == review.id)
    issue_count = session.exec(issue_count_stmt).one()

    return ReviewRead(
        **review.model_dump(),
        agent_count=agent_count,
        issue_count=issue_count
    )


@router.get("/{review_id}/agents", response_model=list[ReviewAgentRead])
async def get_review_agents(
    review_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all agents that participated in a review."""
    review = session.get(Review, review_id)

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    # Verify access through project
    project = session.get(Project, review.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this review"
        )

    statement = select(ReviewAgent).where(ReviewAgent.review_id == review_id)
    agents = session.exec(statement).all()

    return [ReviewAgentRead(**agent.model_dump()) for agent in agents]


@router.get("/{review_id}/issues")
async def get_review_issues(
    review_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    severity: str | None = Query(None, description="Filter by severity"),
    category: str | None = Query(None, description="Filter by category"),
    status_filter: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """Get all issues from a review with optional filters and pagination."""
    review = session.get(Review, review_id)

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    # Verify access through project
    project = session.get(Project, review.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this review"
        )

    # Build base query with filters
    base_query = select(Issue).where(Issue.review_id == review_id)

    if severity:
        base_query = base_query.where(Issue.severity == severity)
    if category:
        base_query = base_query.where(Issue.category == category)
    if status_filter:
        base_query = base_query.where(Issue.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = session.exec(count_query).one()

    # Calculate offset and get paginated results with eager loading of suggestions
    # Use selectinload to prevent N+1 query problem
    offset = (page - 1) * page_size
    statement = (
        base_query
        .options(selectinload(Issue.suggestions))
        .order_by(Issue.severity.desc(), Issue.created_at)
        .offset(offset)
        .limit(page_size)
    )
    issues = session.exec(statement).all()

    # Build responses with suggestions (already loaded via selectinload)
    items = []
    for issue in issues:
        # Suggestions are already loaded, no additional query needed
        suggestion_reads = [SuggestionRead(**s.model_dump()) for s in issue.suggestions]

        items.append(IssueReadWithSuggestions(
            **issue.model_dump(),
            suggestion_count=len(suggestion_reads),
            suggestions=suggestion_reads
        ))

    # Calculate pagination metadata
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return {
        "items": [item.model_dump() for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


@router.patch("/issues/{issue_id}", response_model=IssueRead)
async def update_issue(
    issue_id: int,
    issue_update: IssueUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update an issue (e.g., mark as resolved, update severity)."""
    issue = session.get(Issue, issue_id)

    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )

    # Verify access through review and project
    review = session.get(Review, issue.review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    project = session.get(Project, review.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this issue"
        )

    # Update fields
    update_data = issue_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(issue, field, value)

    from datetime import datetime
    issue.updated_at = datetime.utcnow()

    session.add(issue)
    session.commit()
    session.refresh(issue)

    # Get suggestion count
    suggestion_count_stmt = select(func.count(Suggestion.id)).where(Suggestion.issue_id == issue.id)
    suggestion_count = session.exec(suggestion_count_stmt).one()

    return IssueRead(
        **issue.model_dump(),
        suggestion_count=suggestion_count
    )
