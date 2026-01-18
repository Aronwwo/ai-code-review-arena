"""WebSocket API endpoints for real-time updates."""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt
from app.config import settings
from app.utils.websocket import ws_manager
from app.database import Session, engine
from app.models.review import Review
from app.models.project import Project

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


def verify_ws_token(token: str) -> dict | None:
    """Verify JWT token for WebSocket connection.

    Args:
        token: JWT token

    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


@router.websocket("/ws/reviews/{review_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    review_id: int,
    token: str = Query(...)
):
    """WebSocket endpoint for real-time review updates.

    Args:
        websocket: WebSocket connection
        review_id: Review ID to subscribe to
        token: JWT token for authentication
    """
    # Verify token
    payload = verify_ws_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return
    user_id = payload.get("user_id")
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Verify user has access to the review
    with Session(engine) as session:
        review = session.get(Review, review_id)
        if not review:
            await websocket.close(code=4004, reason="Review not found")
            return
        project = session.get(Project, review.project_id)
        if not project or project.owner_id != user_id:
            await websocket.close(code=4003, reason="Not authorized")
            return

    # Connect to the review
    await ws_manager.connect(websocket, review_id)

    try:
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for messages (ping/pong or client disconnect)
            data = await websocket.receive_text()
            # Handle ping
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, review_id)
        logger.info(f"Client disconnected from review {review_id}")
    except Exception as e:
        logger.error(f"WebSocket error for review {review_id}: {e}")
        ws_manager.disconnect(websocket, review_id)
