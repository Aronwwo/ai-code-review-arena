"""Evaluation API endpoints for Model Duel."""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select, desc
from datetime import datetime, UTC
from app.database import get_session
from app.models.user import User
from app.models.project import Project
from app.models.review import Review, ReviewAgent
from app.models.evaluation import (
    EvaluationSession, EvaluationCandidate, EvaluationVote,
    RatingConfig, RatingModel,
    EvaluationSessionCreate, EvaluationSessionRead, EvaluationSessionWithCandidates,
    EvaluationCandidateRead, EvaluationVoteCreate, EvaluationVoteRead,
    RatingConfigRead, RatingModelRead
)
from app.api.deps import get_current_user
from app.utils.access import verify_project_access
from app.utils.elo import elo_update, get_k_factor
from app.orchestrators.review import ReviewOrchestrator
from app.providers.router import CustomProviderConfig

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


async def run_candidate_review(
    candidate_id: int,
    project_id: int,
    api_keys: dict[str, str] | None = None
):
    """Run review for a candidate in background."""
    from app.database import Session, engine
    from app.models.review import AgentConfig

    with Session(engine) as session:
        # Get candidate
        candidate = session.get(EvaluationCandidate, candidate_id)
        if not candidate:
            return

        # Create a review for this candidate
        review = Review(
            project_id=project_id,
            created_by=candidate.session.created_by,
            status="pending"
        )
        session.add(review)
        session.commit()
        session.refresh(review)

        # Create agent record
        agent = ReviewAgent(
            review_id=review.id,
            role=candidate.agent_role,
            provider=candidate.provider,
            model=candidate.model,
            parsed_successfully=False
        )
        session.add(agent)
        session.commit()

        # Update candidate with review_id
        candidate.review_id = review.id
        session.add(candidate)
        session.commit()

        # Prepare agent config
        agent_config = AgentConfig(
            provider=candidate.provider,
            model=candidate.model,
            prompt="Ocena modelu w trybie testowym."
        )

        # Add custom provider if configured
        if candidate.custom_provider_config:
            cp = candidate.custom_provider_config
            agent_config.custom_provider = CustomProviderConfig(
                id=cp.get("id", "custom"),
                name=cp.get("name", "Custom Provider"),
                base_url=cp["base_url"],
                api_key=cp.get("api_key"),
                header_name=cp.get("header_name", "Authorization"),
                header_prefix=cp.get("header_prefix", "Bearer ")
            )

        agent_configs = {candidate.agent_role: agent_config}

        # Run review
        orchestrator = ReviewOrchestrator(session)
        await orchestrator.conduct_review(
            review.id,
            candidate.provider,
            candidate.model,
            api_keys,
            agent_configs,
            None
        )

        # Update candidate with results
        session.refresh(review)
        session.refresh(agent)

        # Count issues found
        from sqlmodel import func
        from app.models.review import Issue
        issue_count_stmt = select(func.count(Issue.id)).where(Issue.review_id == review.id)
        issues_found = session.exec(issue_count_stmt).one()

        candidate.issues_found = issues_found
        candidate.raw_output = agent.raw_output
        candidate.parsed_successfully = agent.parsed_successfully
        session.add(candidate)
        session.commit()


@router.post("", response_model=EvaluationSessionRead, status_code=status.HTTP_201_CREATED)
async def create_evaluation_session(
    session_data: EvaluationSessionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new evaluation session (Model Duel)."""
    # Verify project access
    project = await verify_project_access(session_data.project_id, current_user, session)

    # Create evaluation session
    eval_session = EvaluationSession(
        project_id=session_data.project_id,
        created_by=current_user.id,
        status="pending",
        num_rounds=session_data.num_rounds,
        current_round=0
    )
    session.add(eval_session)
    session.commit()
    session.refresh(eval_session)

    # Create candidate A
    candidate_a = EvaluationCandidate(
        session_id=eval_session.id,
        position="A",
        provider=session_data.candidate_a_provider,
        model=session_data.candidate_a_model,
        agent_role=session_data.candidate_a_role,
        custom_provider_config=session_data.candidate_a_custom_config
    )
    session.add(candidate_a)

    # Create candidate B
    candidate_b = EvaluationCandidate(
        session_id=eval_session.id,
        position="B",
        provider=session_data.candidate_b_provider,
        model=session_data.candidate_b_model,
        agent_role=session_data.candidate_b_role,
        custom_provider_config=session_data.candidate_b_custom_config
    )
    session.add(candidate_b)
    session.commit()
    session.refresh(candidate_a)
    session.refresh(candidate_b)

    # Update session status
    eval_session.status = "in_progress"
    session.add(eval_session)
    session.commit()

    # Run reviews for both candidates in background
    background_tasks.add_task(
        run_candidate_review,
        candidate_a.id,
        session_data.project_id,
        session_data.api_keys
    )
    background_tasks.add_task(
        run_candidate_review,
        candidate_b.id,
        session_data.project_id,
        session_data.api_keys
    )

    return EvaluationSessionRead(
        id=eval_session.id,
        project_id=eval_session.project_id,
        created_by=eval_session.created_by,
        status=eval_session.status,
        num_rounds=eval_session.num_rounds,
        current_round=eval_session.current_round,
        created_at=eval_session.created_at,
        completed_at=eval_session.completed_at
    )


@router.get("/{session_id}", response_model=EvaluationSessionWithCandidates)
async def get_evaluation_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get evaluation session with candidates and votes."""
    eval_session = session.get(EvaluationSession, session_id)
    if not eval_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation session not found"
        )

    # Verify access to project
    await verify_project_access(eval_session.project_id, current_user, session)

    # Get candidates
    candidates_stmt = select(EvaluationCandidate).where(
        EvaluationCandidate.session_id == session_id
    )
    candidates = session.exec(candidates_stmt).all()

    # Get votes
    votes_stmt = select(EvaluationVote).where(
        EvaluationVote.session_id == session_id
    ).order_by(EvaluationVote.created_at)
    votes = session.exec(votes_stmt).all()

    return EvaluationSessionWithCandidates(
        id=eval_session.id,
        project_id=eval_session.project_id,
        created_by=eval_session.created_by,
        status=eval_session.status,
        num_rounds=eval_session.num_rounds,
        current_round=eval_session.current_round,
        created_at=eval_session.created_at,
        completed_at=eval_session.completed_at,
        candidates=[
            EvaluationCandidateRead(
                id=c.id,
                session_id=c.session_id,
                position=c.position,
                provider=c.provider,
                model=c.model,
                agent_role=c.agent_role,
                custom_provider_config=c.custom_provider_config,
                review_id=c.review_id,
                issues_found=c.issues_found,
                parsed_successfully=c.parsed_successfully,
                created_at=c.created_at
            ) for c in candidates
        ],
        votes=[
            EvaluationVoteRead(
                id=v.id,
                session_id=v.session_id,
                round_number=v.round_number,
                choice=v.choice,
                comment=v.comment,
                voter_id=v.voter_id,
                created_at=v.created_at
            ) for v in votes
        ]
    )


@router.post("/{session_id}/vote", response_model=EvaluationVoteRead)
async def submit_vote(
    session_id: int,
    vote_data: EvaluationVoteCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Submit a vote for an evaluation session."""
    eval_session = session.get(EvaluationSession, session_id)
    if not eval_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation session not found"
        )

    # Verify access
    await verify_project_access(eval_session.project_id, current_user, session)

    # Check if session is still in progress
    if eval_session.status not in ["in_progress", "pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not active"
        )

    # Increment round
    eval_session.current_round += 1
    current_round = eval_session.current_round

    # Create vote
    vote = EvaluationVote(
        session_id=session_id,
        round_number=current_round,
        choice=vote_data.choice,
        comment=vote_data.comment,
        voter_id=current_user.id
    )
    session.add(vote)

    # Get candidates for rating update
    candidates_stmt = select(EvaluationCandidate).where(
        EvaluationCandidate.session_id == session_id
    )
    candidates = session.exec(candidates_stmt).all()

    candidate_a = next((c for c in candidates if c.position == "A"), None)
    candidate_b = next((c for c in candidates if c.position == "B"), None)

    if candidate_a and candidate_b:
        # Update ratings
        await update_ratings(candidate_a, candidate_b, vote_data.choice, session)

    # Check if session is completed
    if current_round >= eval_session.num_rounds:
        eval_session.status = "completed"
        eval_session.completed_at = datetime.now(UTC)

    session.add(eval_session)
    session.commit()
    session.refresh(vote)

    return EvaluationVoteRead(
        id=vote.id,
        session_id=vote.session_id,
        round_number=vote.round_number,
        choice=vote.choice,
        comment=vote.comment,
        voter_id=vote.voter_id,
        created_at=vote.created_at
    )


async def update_ratings(
    candidate_a: EvaluationCandidate,
    candidate_b: EvaluationCandidate,
    vote_choice: str,
    session: Session
):
    """Update ELO ratings for both candidates."""
    # Get or create rating configs
    rating_a = get_or_create_rating_config(
        candidate_a.provider,
        candidate_a.model,
        candidate_a.agent_role,
        session
    )
    rating_b = get_or_create_rating_config(
        candidate_b.provider,
        candidate_b.model,
        candidate_b.agent_role,
        session
    )

    # Calculate new ratings
    k_a = get_k_factor(rating_a.games_played)
    k_b = get_k_factor(rating_b.games_played)
    k_factor = (k_a + k_b) / 2  # Average K-factor

    new_rating_a, new_rating_b = elo_update(
        rating_a.elo_rating,
        rating_b.elo_rating,
        vote_choice,
        k_factor
    )

    # Update rating A
    rating_a.elo_rating = new_rating_a
    rating_a.games_played += 1
    if vote_choice == "candidate_a":
        rating_a.wins += 1
    elif vote_choice == "candidate_b":
        rating_a.losses += 1
    else:
        rating_a.ties += 1
    rating_a.updated_at = datetime.now(UTC)
    session.add(rating_a)

    # Update rating B
    rating_b.elo_rating = new_rating_b
    rating_b.games_played += 1
    if vote_choice == "candidate_b":
        rating_b.wins += 1
    elif vote_choice == "candidate_a":
        rating_b.losses += 1
    else:
        rating_b.ties += 1
    rating_b.updated_at = datetime.now(UTC)
    session.add(rating_b)

    session.commit()

    # Update aggregate model ratings
    update_model_rating(candidate_a.provider, candidate_a.model, session)
    update_model_rating(candidate_b.provider, candidate_b.model, session)


def get_or_create_rating_config(
    provider: str,
    model: str,
    agent_role: str,
    session: Session
) -> RatingConfig:
    """Get or create rating config for a configuration."""
    stmt = select(RatingConfig).where(
        RatingConfig.provider == provider,
        RatingConfig.model == model,
        RatingConfig.agent_role == agent_role
    )
    rating = session.exec(stmt).first()

    if not rating:
        rating = RatingConfig(
            provider=provider,
            model=model,
            agent_role=agent_role,
            elo_rating=1500.0
        )
        session.add(rating)
        session.commit()
        session.refresh(rating)

    return rating


def update_model_rating(provider: str, model: str, session: Session):
    """Update aggregate model rating based on all role ratings."""
    # Get all config ratings for this model
    stmt = select(RatingConfig).where(
        RatingConfig.provider == provider,
        RatingConfig.model == model
    )
    configs = session.exec(stmt).all()

    if not configs:
        return

    # Calculate aggregate stats
    total_rating = sum(c.elo_rating for c in configs)
    avg_rating = total_rating / len(configs)
    total_games = sum(c.games_played for c in configs)
    total_wins = sum(c.wins for c in configs)
    total_losses = sum(c.losses for c in configs)
    total_ties = sum(c.ties for c in configs)

    # Get or create model rating
    stmt = select(RatingModel).where(
        RatingModel.provider == provider,
        RatingModel.model == model
    )
    model_rating = session.exec(stmt).first()

    if not model_rating:
        model_rating = RatingModel(
            provider=provider,
            model=model
        )

    # Update stats
    model_rating.elo_rating = avg_rating
    model_rating.games_played = total_games
    model_rating.wins = total_wins
    model_rating.losses = total_losses
    model_rating.ties = total_ties
    model_rating.updated_at = datetime.now(UTC)

    session.add(model_rating)
    session.commit()


@router.get("/rankings/configs", response_model=list[RatingConfigRead])
async def get_config_rankings(
    agent_role: str | None = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get configuration rankings (provider + model + role)."""
    stmt = select(RatingConfig)

    if agent_role:
        stmt = stmt.where(RatingConfig.agent_role == agent_role)

    stmt = stmt.order_by(desc(RatingConfig.elo_rating)).limit(limit)
    configs = session.exec(stmt).all()

    return [
        RatingConfigRead(
            id=c.id,
            provider=c.provider,
            model=c.model,
            agent_role=c.agent_role,
            elo_rating=c.elo_rating,
            games_played=c.games_played,
            wins=c.wins,
            losses=c.losses,
            ties=c.ties,
            created_at=c.created_at,
            updated_at=c.updated_at
        ) for c in configs
    ]


@router.get("/rankings/models", response_model=list[RatingModelRead])
async def get_model_rankings(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get aggregate model rankings."""
    stmt = select(RatingModel).order_by(desc(RatingModel.elo_rating)).limit(limit)
    models = session.exec(stmt).all()

    return [
        RatingModelRead(
            id=m.id,
            provider=m.provider,
            model=m.model,
            elo_rating=m.elo_rating,
            games_played=m.games_played,
            wins=m.wins,
            losses=m.losses,
            ties=m.ties,
            created_at=m.created_at,
            updated_at=m.updated_at
        ) for m in models
    ]


@router.get("", response_model=list[EvaluationSessionRead])
async def list_evaluation_sessions(
    project_id: int | None = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """List evaluation sessions."""
    stmt = select(EvaluationSession)

    if project_id:
        # Verify access if filtering by project
        await verify_project_access(project_id, current_user, session)
        stmt = stmt.where(EvaluationSession.project_id == project_id)

    stmt = stmt.order_by(desc(EvaluationSession.created_at)).limit(limit)
    sessions_list = session.exec(stmt).all()

    return [
        EvaluationSessionRead(
            id=s.id,
            project_id=s.project_id,
            created_by=s.created_by,
            status=s.status,
            num_rounds=s.num_rounds,
            current_round=s.current_round,
            created_at=s.created_at,
            completed_at=s.completed_at
        ) for s in sessions_list
    ]
