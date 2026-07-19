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

from app.dependencies import get_cache_instance, get_data_manager_instance

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
        if websocket in self._connections:
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
            if conn in self._connections:
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
      - Snapshot of latest cached prices immediately on connect
      - Tick updates (every tick from FYERS)
      - Option chain snapshots (every poll cycle)
      - Score updates (when recalculated)
      - AI reports (when generated)
    """
    await ws_manager.connect(websocket)

    dm = get_data_manager_instance()
    cache = get_cache_instance()

    # ── 1. Send initial snapshot so the UI isn't blank ──────────────────
    if cache:
        try:
            snapshot = await cache.get_all_cached_ticks()
            if snapshot:
                await websocket.send_text(
                    json.dumps({"type": "snapshot", "data": snapshot}, default=str)
                )
        except Exception as exc:
            logger.warning("Failed to send initial snapshot: %s", exc)

    # ── 2. Subscribe to live ticks ───────────────────────────────────────
    async def on_tick(tick: dict[str, Any]) -> None:
        try:
            await websocket.send_text(
                json.dumps({"type": "tick", "data": tick}, default=str)
            )
        except Exception:
            pass  # Client disconnected — will be cleaned up below

    subscriber_registered = False
    if dm:
        dm.subscribe(on_tick)
        subscriber_registered = True
    else:
        logger.warning("DataManager not available — client will receive no ticks until pipeline starts")

    try:
        while True:
            data = await websocket.receive_text()
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
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # ── 3. Clean up subscriber to prevent memory leaks ──────────────
        if subscriber_registered and dm and on_tick in dm._subscribers:
            dm._subscribers.remove(on_tick)
        ws_manager.disconnect(websocket)
