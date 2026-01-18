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
    agent_configs: dict | None = None,
    engine_override=None,
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

    with Session(engine_override or engine) as session:
        orchestrator = ReviewOrchestrator(session)
        await orchestrator.conduct_review(
            review_id,
            provider,
            model,
            api_keys,
            parsed_agent_configs
        )


@projects_router.post("", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
async def create_review(
    project_id: int,
    review_data: ReviewCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Utwórz i uruchom nowy review dla projektu.

    Jeden agent analizuje kod i zapisuje issues bezpośrednio do bazy danych.

    Args:
        project_id: ID projektu do przeanalizowania
        review_data: Konfiguracja review (tryb, role, konfiguracje agentów)
        background_tasks: FastAPI BackgroundTasks
        current_user: Zalogowany użytkownik
        session: Sesja bazodanowa

    Returns:
        Utworzony Review (status: "pending")

    Raises:
        HTTPException 400: Nieprawidłowy tryb review
        HTTPException 404: Projekt nie istnieje
        HTTPException 422: Brak wymaganej konfiguracji
    """
    project = await verify_project_access(project_id, current_user, session)

    # Walidacja trybu review - tylko council
    review_mode = review_data.review_mode
    if review_mode != "council":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Nieprawidłowy tryb review",
                "allowed": ["council"],
                "provided": review_mode
            }
        )

    # Walidacja konfiguracji
    if not review_data.agent_configs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="agent_configs jest wymagane"
        )
    if review_data.moderator_type and not review_data.moderator_config:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="moderator_config jest wymagane gdy podano moderator_type"
        )

    provided_roles = set(review_data.agent_roles or [])
    if not provided_roles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="agent_roles jest wymagane"
        )
    if not review_data.agent_configs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="agent_configs jest wymagane"
        )
    missing_configs = provided_roles - set(review_data.agent_configs.keys())
    if missing_configs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Brak konfiguracji dla ról: {', '.join(sorted(missing_configs))}"
        )

    # Tworzenie rekordu Review w bazie
    review = Review(
        project_id=project_id,
        created_by=current_user.id,
        status="pending",
        review_mode=review_mode
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
            if not provider or not provider.strip() or not model or not model.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Rola '{role}': provider i model nie mogą być puste"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Brak konfiguracji dla roli '{role}' w agent_configs"
            )

        agent = ReviewAgent(
            review_id=review.id,
            role=role,
            provider=provider,
            model=model,
            parsed_successfully=False,
            timeout_seconds=config.timeout_seconds
        )
        session.add(agent)

    session.commit()

    # Start review in background with agent configs
    agent_configs_dict = {
        role: {k: v for k, v in config.model_dump().items() if k != "prompt"}
        for role, config in review_data.agent_configs.items()
    }

    background_tasks.add_task(
        run_review_in_background,
        review.id,
        review_data.provider,
        review_data.model,
        review_data.api_keys,
        agent_configs_dict,
        session.get_bind(),
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

    # Build responses with counts and model information
    result = []
    for review in reviews:
        agent_count_stmt = select(func.count(ReviewAgent.id)).where(ReviewAgent.review_id == review.id)
        agent_count = session.exec(agent_count_stmt).one()

        issue_count_stmt = select(func.count(Issue.id)).where(Issue.review_id == review.id)
        issue_count = session.exec(issue_count_stmt).one()

        # Get unique provider/model combinations from agents
        agents_stmt = select(ReviewAgent.provider, ReviewAgent.model).where(ReviewAgent.review_id == review.id)
        agents_data = session.exec(agents_stmt).all()
        # Create list of unique "provider/model" strings
        models_list = list(set([f"{agent.provider}/{agent.model}" for agent in agents_data if agent.provider and agent.model]))

        result.append(ReviewRead(
            **review.model_dump(),
            agent_count=agent_count,
            issue_count=issue_count,
            models=models_list
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

    # Get unique provider/model combinations from agents
    agents_stmt = select(ReviewAgent.provider, ReviewAgent.model).where(ReviewAgent.review_id == review.id)
    agents_data = session.exec(agents_stmt).all()
    # Create list of unique "provider/model" strings
    models_list = list(set([f"{agent.provider}/{agent.model}" for agent in agents_data if agent.provider and agent.model]))

    return ReviewRead(
        **review.model_dump(),
        agent_count=agent_count,
        issue_count=issue_count,
        models=models_list
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
    import logging
    logger = logging.getLogger(__name__)
    
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

    try:
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
        logger.info(f"Found {total} total issues for review {review_id}")

        # Calculate offset and get paginated results with eager loading of suggestions
        # Use selectinload to prevent N+1 query problem
        offset = (page - 1) * page_size
        # IMPORTANT: Don't use .options() with session.exec() - it causes tuple results
        # Instead, use regular query and manually join suggestions later
        statement = (
            base_query
            .order_by(Issue.severity.desc(), Issue.created_at)
            .offset(offset)
            .limit(page_size)
        )
        issues = session.exec(statement).all()
        logger.info(f"Retrieved {len(issues)} issues for review {review_id} (page {page})")
        print(f"DEBUG: Retrieved {len(issues)} issues")  # Direct stdout
    except Exception as e:
        logger.error(f"Error fetching issues for review {review_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching issues: {str(e)}"
        )

    # Build responses with suggestions
    items = []
    for issue in issues:
        try:
            # Manually load suggestions for this issue (N+1 but safer than selectinload issues)
            sugg_stmt = select(Suggestion).where(Suggestion.issue_id == issue.id)
            suggestions_list = session.exec(sugg_stmt).all()
            suggestion_reads = [SuggestionRead(**s.model_dump()) for s in suggestions_list]

            # Create response object with explicit field access
            items.append(IssueReadWithSuggestions(
                id=issue.id,
                review_id=issue.review_id,
                file_id=issue.file_id,
                severity=issue.severity,
                category=issue.category,
                title=issue.title,
                description=issue.description,
                agent_role=getattr(issue, 'agent_role', None),
                file_name=issue.file_name,
                line_start=issue.line_start,
                line_end=issue.line_end,
                status=issue.status,
                confirmed=issue.confirmed,
                final_severity=issue.final_severity,
                moderator_comment=issue.moderator_comment,
                created_at=issue.created_at,
                updated_at=issue.updated_at,
                suggestion_count=len(suggestion_reads),
                suggestions=suggestion_reads
            ))
        except Exception as e:
            logger.error(f"Error serializing issue {issue.id}: {e}", exc_info=True)
            # Continue with other issues rather than failing entire request
            continue

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

    from datetime import datetime, timezone
    issue.updated_at = datetime.now(timezone.utc)

    session.add(issue)
    session.commit()
    session.refresh(issue)

    # Get suggestion count
    suggestion_count_stmt = select(func.count(Suggestion.id)).where(Suggestion.issue_id == issue.id)
    suggestion_count = session.exec(suggestion_count_stmt).one()

    # Build issue dict manually to handle missing agent_role column gracefully
    issue_dict = issue.model_dump()
    if 'agent_role' not in issue_dict:
        issue_dict['agent_role'] = None
    
    return IssueRead(
        **issue_dict,
        suggestion_count=suggestion_count
    )


@router.post("/{review_id}/resume", response_model=ReviewRead)
async def resume_review(
    review_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    provider: str | None = Query(None),
    model: str | None = Query(None),
    api_keys: dict[str, str] | None = None,
    agent_configs: dict | None = None
):
    """Resume a failed or pending review."""
    review = session.get(Review, review_id)
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Verify access
    project = session.get(Project, review.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to resume this review"
        )
    
    # Only resume if failed or pending
    if review.status not in ["failed", "pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resume review with status '{review.status}'. Only 'failed' or 'pending' reviews can be resumed."
        )
    
    # Reset review status to pending
    review.status = "pending"
    review.error_message = None
    session.add(review)
    session.commit()
    
    # Restart review in background
    background_tasks.add_task(
        run_review_in_background,
        review.id,
        provider,
        model,
        api_keys,
        agent_configs
    )
    
    return ReviewRead(
        **review.model_dump(),
        agent_count=0,  # Will be updated by refetch
        issue_count=0
    )


@router.post("/{review_id}/stop", response_model=ReviewRead)
async def stop_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Stop a running or pending review."""
    review = session.get(Review, review_id)
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Verify access
    project = session.get(Project, review.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to stop this review"
        )
    
    # Only stop if running or pending
    if review.status not in ["running", "pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot stop review with status '{review.status}'. Only 'running' or 'pending' reviews can be stopped."
        )
    
    # Mark review as failed with cancellation message
    from datetime import datetime, timezone
    review.status = "failed"
    review.error_message = "Przegląd został zatrzymany przez użytkownika"
    review.completed_at = datetime.now(timezone.utc)
    session.add(review)
    session.commit()
    session.refresh(review)
    
    # Get counts
    agent_count_stmt = select(func.count(ReviewAgent.id)).where(ReviewAgent.review_id == review_id)
    agent_count = session.exec(agent_count_stmt).one()
    
    issue_count_stmt = select(func.count(Issue.id)).where(Issue.review_id == review_id)
    issue_count = session.exec(issue_count_stmt).one()
    
    return ReviewRead(
        **review.model_dump(),
        agent_count=agent_count,
        issue_count=issue_count
    )


@router.post("/{review_id}/recreate", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
async def recreate_review(
    review_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    api_keys: dict[str, str] | None = None,
):
    """Recreate a review with the same configuration (agent roles, providers, models, etc.).
    
    This creates a new review based on an existing one, using the same:
    - Review mode (council/arena)
    - Agent roles and their configurations (provider, model, timeout_seconds)
    - Project
    
    API keys can be optionally provided, otherwise will use defaults from settings.
    """
    original_review = session.get(Review, review_id)
    
    if not original_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Verify access
    project = session.get(Project, original_review.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to recreate this review"
        )
    
    # Get all agents from original review to recreate their configuration
    original_agents = session.exec(
        select(ReviewAgent).where(ReviewAgent.review_id == review_id)
    ).all()
    
    if not original_agents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot recreate review: original review has no agents"
        )
    
    # Create new review with same configuration
    new_review = Review(
        project_id=original_review.project_id,
        created_by=current_user.id,
        status="pending",
        review_mode=original_review.review_mode
    )
    session.add(new_review)
    session.commit()
    session.refresh(new_review)
    
    # Recreate agent configurations from original review
    from app.models.review import AgentConfig
    agent_configs_dict = {}
    agent_roles = []
    
    for original_agent in original_agents:
        # Create agent record
        new_agent = ReviewAgent(
            review_id=new_review.id,
            role=original_agent.role,
            provider=original_agent.provider,
            model=original_agent.model,
            parsed_successfully=False,
            timeout_seconds=original_agent.timeout_seconds
        )
        session.add(new_agent)
        
        # Build agent config dict for orchestrator
        agent_config = AgentConfig(
            provider=original_agent.provider,
            model=original_agent.model,
            timeout_seconds=original_agent.timeout_seconds or 180,
            temperature=0.2,
            max_tokens=2048
        )
        agent_configs_dict[original_agent.role] = agent_config
        agent_roles.append(original_agent.role)
    
    session.commit()
    
    # Convert to dict for background task
    agent_configs_dict_for_task = {
        role: {k: v for k, v in config.model_dump().items() if k != "prompt"}
        for role, config in agent_configs_dict.items()
    }
    
    # Start new review in background (no moderator config - moderator removed)
    background_tasks.add_task(
        run_review_in_background,
        new_review.id,
        None,  # provider (not used, agents have their own)
        None,  # model (not used, agents have their own)
        api_keys,
        agent_configs_dict_for_task
    )
    
    return ReviewRead(
        **new_review.model_dump(),
        agent_count=len(agent_roles),
        issue_count=0
    )


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete a review and all related data."""
    review = session.get(Review, review_id)
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Verify access
    project = session.get(Project, review.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this review"
        )
    
    # Don't allow deleting running reviews - stop them first
    if review.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running review. Stop it first."
        )
    
    # Delete related data (cascade should handle this, but we'll be explicit)
    # Delete agents
    agents = session.exec(select(ReviewAgent).where(ReviewAgent.review_id == review_id)).all()
    for agent in agents:
        session.delete(agent)
    
    # Delete issues and suggestions (cascade should handle suggestions)
    issues = session.exec(select(Issue).where(Issue.review_id == review_id)).all()
    for issue in issues:
        # Delete suggestions for this issue
        suggestions = session.exec(select(Suggestion).where(Suggestion.issue_id == issue.id)).all()
        for suggestion in suggestions:
            session.delete(suggestion)
        session.delete(issue)
    
    # Delete conversations and messages
    from app.models.conversation import Conversation, Message
    conversations = session.exec(select(Conversation).where(Conversation.review_id == review_id)).all()
    for conversation in conversations:
        messages = session.exec(select(Message).where(Message.conversation_id == conversation.id)).all()
        for message in messages:
            session.delete(message)
        session.delete(conversation)
    
    # Delete review
    session.delete(review)
    session.commit()
    
    return None
