"""Unit tests for moderator JSON issue parsing."""
import json
import pytest
from sqlmodel import Session, select
from app.models.review import Review, Issue
from app.models.user import User
from app.models.project import Project
from app.orchestrators.review import ReviewOrchestrator


@pytest.mark.asyncio
async def test_store_moderator_issues_creates_issues(test_session: Session):
    user = User(email="summary@example.com", username="summary", full_name="Summary User", hashed_password="hash")
    project = Project(name="Summary Project", description="Summary", owner_id=1)
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    project.owner_id = user.id
    test_session.add(project)
    test_session.commit()
    test_session.refresh(project)

    review = Review(
        project_id=project.id,
        created_by=user.id,
        status="pending",
        review_mode="council",
        moderator_type="debate"
    )
    test_session.add(review)
    test_session.commit()
    test_session.refresh(review)

    summary = {
        "summary": "Podsumowanie",
        "issues": [
            {
                "category": "security",
                "severity": "error",
                "description": "Brak walidacji wejścia.",
                "suggested_code": "Dodaj walidacje",
            }
        ],
        "followups": [],
    }

    orchestrator = ReviewOrchestrator(test_session)
    await orchestrator._store_moderator_issues(review, json.dumps(summary))

    issues = test_session.exec(select(Issue).where(Issue.review_id == review.id)).all()
    assert len(issues) == 1
