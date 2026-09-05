"""WebSocket stream route for broadcasting real-time incident updates to connected clients."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections and provides robust broadcast delivery."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept new WebSocket connection and register client."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info("Client connected to stream. Active connections: %d", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Unregister disconnected WebSocket client."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("Client disconnected from stream. Active connections: %d", len(self.active_connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast JSON message to all connected clients.

        Gracefully prunes failed/dead connections without interrupting healthy clients.
        """
        async with self._lock:
            clients_snapshot = list(self.active_connections)

        dead_clients: list[WebSocket] = []
        for client in clients_snapshot:
            try:
                await client.send_json(message)
            except Exception as exc:
                logger.warning("Failed to send message to client %s: %s", client, exc)
                dead_clients.append(client)

        if dead_clients:
            async with self._lock:
                for dead in dead_clients:
                    if dead in self.active_connections:
                        self.active_connections.remove(dead)
            logger.info("Pruned %d dead WebSocket client(s). Active connections: %d", len(dead_clients), len(self.active_connections))


# Global singleton connection manager for incident stream
stream_manager = ConnectionManager()


@router.websocket("")
@router.websocket("/")
async def incident_stream_endpoint(websocket: WebSocket) -> None:
    """Real-time WebSocket endpoint for receiving live incident updates."""
    await stream_manager.connect(websocket)
    try:
        # Send initial confirmation event
        await websocket.send_json(
            {
                "event": "connected",
                "message": "Connected to real-time weather incident stream",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        while True:
            # Keep connection open and await any client frames (pings / close frames)
            await websocket.receive_text()
    except WebSocketDisconnect:
        await stream_manager.disconnect(websocket)
    except Exception as e:
        logger.debug("WebSocket connection closed with exception: %s", e)
        await stream_manager.disconnect(websocket)
