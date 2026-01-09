"""WebSocket manager for real-time updates."""
import json
import logging
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        """Initialize connection manager."""
        # Dict of review_id -> list of connected websockets
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, review_id: int):
        """Accept a WebSocket connection for a review.

        Args:
            websocket: WebSocket connection
            review_id: Review ID to subscribe to
        """
        await websocket.accept()
        if review_id not in self.active_connections:
            self.active_connections[review_id] = []
        self.active_connections[review_id].append(websocket)
        logger.info(f"WebSocket connected for review {review_id}")

    def disconnect(self, websocket: WebSocket, review_id: int):
        """Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection
            review_id: Review ID
        """
        if review_id in self.active_connections:
            if websocket in self.active_connections[review_id]:
                self.active_connections[review_id].remove(websocket)
            if not self.active_connections[review_id]:
                del self.active_connections[review_id]
        logger.info(f"WebSocket disconnected for review {review_id}")

    async def broadcast(self, review_id: int, message: dict[str, Any]):
        """Broadcast a message to all connections for a review.

        Args:
            review_id: Review ID
            message: Message to broadcast
        """
        if review_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[review_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send WebSocket message: {e}")
                    disconnected.append(connection)

            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn, review_id)

    async def send_review_started(self, review_id: int, agent_roles: list[str]):
        """Send review started event.

        Args:
            review_id: Review ID
            agent_roles: List of agent roles in the review
        """
        await self.broadcast(review_id, {
            "type": "review_started",
            "review_id": review_id,
            "agent_roles": agent_roles,
            "status": "running"
        })

    async def send_agent_started(self, review_id: int, agent_role: str):
        """Send agent started event.

        Args:
            review_id: Review ID
            agent_role: Agent role that started
        """
        await self.broadcast(review_id, {
            "type": "agent_started",
            "review_id": review_id,
            "agent_role": agent_role
        })

    async def send_agent_completed(
        self,
        review_id: int,
        agent_role: str,
        issue_count: int,
        parsed_successfully: bool
    ):
        """Send agent completed event.

        Args:
            review_id: Review ID
            agent_role: Agent role that completed
            issue_count: Number of issues found
            parsed_successfully: Whether parsing was successful
        """
        await self.broadcast(review_id, {
            "type": "agent_completed",
            "review_id": review_id,
            "agent_role": agent_role,
            "issue_count": issue_count,
            "parsed_successfully": parsed_successfully
        })

    async def send_review_completed(self, review_id: int, total_issues: int):
        """Send review completed event.

        Args:
            review_id: Review ID
            total_issues: Total number of issues found
        """
        await self.broadcast(review_id, {
            "type": "review_completed",
            "review_id": review_id,
            "status": "completed",
            "total_issues": total_issues
        })

    async def send_review_failed(self, review_id: int, error: str):
        """Send review failed event.

        Args:
            review_id: Review ID
            error: Error message
        """
        await self.broadcast(review_id, {
            "type": "review_failed",
            "review_id": review_id,
            "status": "failed",
            "error": error
        })


# Global connection manager instance
ws_manager = ConnectionManager()
