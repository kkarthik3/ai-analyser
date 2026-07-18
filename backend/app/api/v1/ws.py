"""
WebSocket endpoint for real-time data streaming to frontend.

Streams live tick data, option chain updates, scores, and
AI reports to connected clients via WebSocket.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.dependencies import get_data_manager_instance

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections to frontend clients."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        logger.info(f"Client connected. Total: {len(self._connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.remove(websocket)
        logger.info(f"Client disconnected. Total: {len(self._connections)}")

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        if not self._connections:
            return

        data = json.dumps(message, default=str)
        disconnected = []

        for connection in self._connections:
            try:
                await connection.send_text(data)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self._connections.remove(conn)

    @property
    def client_count(self) -> int:
        return len(self._connections)


# Global connection manager
ws_manager = ConnectionManager()


@router.websocket("/ws/market")
async def market_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time market data.

    Streams:
      - Tick updates (every tick)
      - Option chain snapshots (every poll cycle)
      - Score updates (when recalculated)
      - AI reports (when generated)
    """
    await ws_manager.connect(websocket)

    # Register as a data subscriber
    dm = get_data_manager_instance()

    async def on_tick(tick: dict[str, Any]) -> None:
        await ws_manager.broadcast({"type": "tick", "data": tick})

    if dm:
        dm.subscribe(on_tick)

    try:
        while True:
            # Keep connection alive, handle incoming messages
            data = await websocket.receive_text()
            # Client can send subscription preferences
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")

                if msg_type == "subscribe":
                    symbols = msg.get("symbols", [])
                    logger.info(f"Client subscribed to: {symbols}")

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
