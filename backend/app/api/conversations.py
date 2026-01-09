"""Conversation API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select, func
from app.database import get_session
from app.models.user import User
from app.models.review import Review, Issue
from app.models.project import Project
from app.models.conversation import (
    Conversation, Message,
    ConversationCreate, ConversationRead,
    MessageRead, DebateIssueRequest
)
from app.api.deps import get_current_user
from app.orchestrators.conversation import ConversationOrchestrator
from app.utils.access import verify_review_access

router = APIRouter(prefix="/conversations", tags=["conversations"])
reviews_router = APIRouter(prefix="/reviews/{review_id}/conversations", tags=["conversations"])
issues_router = APIRouter(prefix="/issues/{issue_id}/debate", tags=["conversations"])


async def run_conversation_in_background(conversation_id: int, provider: str | None, model: str | None):
    """Run conversation in background task."""
    from app.database import Session, engine
    with Session(engine) as session:
        orchestrator = ConversationOrchestrator(session)
        await orchestrator.run_conversation(conversation_id, provider, model)


@reviews_router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    review_id: int,
    conversation_data: ConversationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create and start a new conversation for a review."""
    review = await verify_review_access(review_id, current_user, session)

    # Create conversation
    conversation = Conversation(
        review_id=review_id,
        mode=conversation_data.mode,
        topic_type=conversation_data.topic_type,
        topic_id=conversation_data.topic_id,
        status="pending"
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    # Start conversation in background
    background_tasks.add_task(
        run_conversation_in_background,
        conversation.id,
        conversation_data.provider,
        conversation_data.model
    )

    return ConversationRead(
        **conversation.model_dump(),
        message_count=0
    )


@reviews_router.get("", response_model=list[ConversationRead])
async def list_review_conversations(
    review_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """List all conversations for a review."""
    await verify_review_access(review_id, current_user, session)

    statement = (
        select(Conversation)
        .where(Conversation.review_id == review_id)
        .order_by(Conversation.created_at.desc())
    )
    conversations = session.exec(statement).all()

    # Build responses with counts
    result = []
    for conversation in conversations:
        message_count_stmt = select(func.count(Message.id)).where(Message.conversation_id == conversation.id)
        message_count = session.exec(message_count_stmt).one()

        result.append(ConversationRead(
            **conversation.model_dump(),
            message_count=message_count
        ))

    return result


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get a specific conversation with all messages."""
    conversation = session.get(Conversation, conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Verify access through review and project
    review = session.get(Review, conversation.review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    project = session.get(Project, review.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this conversation"
        )

    # Get messages
    message_stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.turn_index)
    messages = session.exec(message_stmt).all()
    message_reads = [MessageRead(**msg.model_dump()) for msg in messages]

    # Return dict to avoid circular import
    return {
        **conversation.model_dump(),
        "message_count": len(message_reads),
        "messages": [m.model_dump() for m in message_reads]
    }


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
async def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all messages for a conversation."""
    conversation = session.get(Conversation, conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Verify access through review and project
    review = session.get(Review, conversation.review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    project = session.get(Project, review.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this conversation"
        )

    # Get messages
    message_stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.turn_index)
    messages = session.exec(message_stmt).all()

    return [MessageRead(**msg.model_dump()) for msg in messages]


@router.post("/{conversation_id}/run", response_model=ConversationRead)
async def run_conversation(
    conversation_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    provider: str | None = None,
    model: str | None = None
):
    """Manually trigger a conversation to run (if not auto-started)."""
    conversation = session.get(Conversation, conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Verify access
    review = session.get(Review, conversation.review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    project = session.get(Project, review.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to run this conversation"
        )

    # Start conversation in background
    background_tasks.add_task(
        run_conversation_in_background,
        conversation.id,
        provider,
        model
    )

    # Get message count
    message_count_stmt = select(func.count(Message.id)).where(Message.conversation_id == conversation.id)
    message_count = session.exec(message_count_stmt).one()

    return ConversationRead(
        **conversation.model_dump(),
        message_count=message_count
    )


@issues_router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def debate_issue(
    issue_id: int,
    debate_request: DebateIssueRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Start an adversarial debate for a specific issue."""
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
            detail="Not authorized to debate this issue"
        )

    # Create adversarial conversation
    conversation = Conversation(
        review_id=review.id,
        mode="adversarial",
        topic_type="issue",
        topic_id=issue_id,
        status="pending"
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    # Start debate in background
    background_tasks.add_task(
        run_conversation_in_background,
        conversation.id,
        debate_request.provider,
        debate_request.model
    )

    return ConversationRead(
        **conversation.model_dump(),
        message_count=0
    )
