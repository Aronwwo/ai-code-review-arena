"""Rankings API endpoints - statistics based on code reviews."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func, and_
from typing import List, Dict, Any
from app.database import get_session
from app.models import Review, ReviewAgent, Issue
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("/models")
async def get_model_rankings(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    agent_role: str | None = None
) -> List[Dict[str, Any]]:
    """Get model rankings based on review performance.

    Returns statistics for each model:
    - Number of reviews participated in
    - Number of issues found
    - Average issues per review
    - Success rate (parsed successfully)
    """
    # Base query (ranking only for general agent)
    query = (
        select(
            ReviewAgent.provider,
            ReviewAgent.model,
            ReviewAgent.role,
            func.count(ReviewAgent.id).label('reviews_count'),
            func.sum(func.cast(ReviewAgent.parsed_successfully, int)).label('successful_parses'),
        )
        .where(ReviewAgent.role == "general")
        .group_by(ReviewAgent.provider, ReviewAgent.model, ReviewAgent.role)
    )

    # Backwards compatibility: ignore non-general role filters
    if agent_role and agent_role != "general":
        raise HTTPException(status_code=400, detail="Rankingi dostępne tylko dla agenta 'general'")

    results = session.exec(query).all()

    # Get issue counts per agent
    rankings = []
    for result in results:
        provider, model, role, reviews_count, successful_parses = result

        # Count issues found by this specific model+role combo
        issues_query = (
            select(func.count(Issue.id))
            .join(Review, Issue.review_id == Review.id)
            .join(ReviewAgent, ReviewAgent.review_id == Review.id)
            .where(
                and_(
                    ReviewAgent.provider == provider,
                    ReviewAgent.model == model,
                    ReviewAgent.role == "general"
                )
            )
        )
        issues_count = session.exec(issues_query).one()

        success_rate = (successful_parses / reviews_count * 100) if reviews_count > 0 else 0
        avg_issues = (issues_count / reviews_count) if reviews_count > 0 else 0

        rankings.append({
            'provider': provider,
            'model': model,
            'role': role,
            'reviews_count': reviews_count,
            'issues_found': issues_count,
            'avg_issues_per_review': round(avg_issues, 2),
            'success_rate': round(success_rate, 1),
            'successful_parses': successful_parses
        })

    # Sort by issues found (descending)
    rankings.sort(key=lambda x: (x['issues_found'], x['success_rate']), reverse=True)

    return rankings


@router.get("/providers")
async def get_provider_rankings(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get provider rankings aggregated across all models."""
    query = (
        select(
            ReviewAgent.provider,
            func.count(ReviewAgent.id).label('reviews_count'),
            func.sum(func.cast(ReviewAgent.parsed_successfully, int)).label('successful_parses'),
        )
        .where(ReviewAgent.role == "general")
        .group_by(ReviewAgent.provider)
    )

    results = session.exec(query).all()

    rankings = []
    for result in results:
        provider, reviews_count, successful_parses = result

        # Count total issues found by this provider
        issues_query = (
            select(func.count(Issue.id))
            .join(Review, Issue.review_id == Review.id)
            .join(ReviewAgent, ReviewAgent.review_id == Review.id)
            .where(
                and_(
                    ReviewAgent.provider == provider,
                    ReviewAgent.role == "general"
                )
            )
        )
        issues_count = session.exec(issues_query).one()

        success_rate = (successful_parses / reviews_count * 100) if reviews_count > 0 else 0
        avg_issues = (issues_count / reviews_count) if reviews_count > 0 else 0

        rankings.append({
            'provider': provider,
            'reviews_count': reviews_count,
            'issues_found': issues_count,
            'avg_issues_per_review': round(avg_issues, 2),
            'success_rate': round(success_rate, 1)
        })

    rankings.sort(key=lambda x: (x['issues_found'], x['success_rate']), reverse=True)

    return rankings


@router.get("/stats")
async def get_overall_stats(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get overall statistics."""
    # Total reviews
    total_reviews = session.exec(select(func.count(Review.id))).one()

    # Completed reviews
    completed_reviews = session.exec(
        select(func.count(Review.id)).where(Review.status == "completed")
    ).one()

    # Total issues found
    total_issues = session.exec(select(func.count(Issue.id))).one()

    # Total agents participated
    total_agents = session.exec(
        select(func.count(ReviewAgent.id)).where(ReviewAgent.role == "general")
    ).one()

    # Reviews by mode
    council_reviews = session.exec(
        select(func.count(Review.id)).where(Review.review_mode == "council")
    ).one()

    return {
        'total_reviews': total_reviews,
        'completed_reviews': completed_reviews,
        'total_issues': total_issues,
        'total_agents_participated': total_agents,
        'avg_issues_per_review': round(total_issues / completed_reviews, 2) if completed_reviews > 0 else 0,
        'council_reviews': council_reviews,
        'arena_reviews': 0
    }
