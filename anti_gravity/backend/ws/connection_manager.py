"""
Anti-Gravity Backend — Connection Manager
Manages active WebSocket client connections for live game synchronization.

Improvements (Sprint 7):
- Concurrent broadcast via asyncio.gather so one slow client doesn't stall others.
- Dead-connection detection checks WebSocket client_state on every broadcast.
- clean_shutdown() closes all remaining connections gracefully.
- active_count property exposes live metrics without exposing the internal set.
"""

import asyncio
from typing import Set, Dict, Any, Optional
from fastapi import WebSocket
from datetime import datetime, timezone


class ConnectionManager:
    """
    Responsibilities:
    - connect: accept and track WebSocket client connection
    - disconnect: remove client connection
    - broadcast: send message concurrently to all connected clients
    - send_personal_message: send message to a specific client
    - remove_dead_connections: purge disconnected clients
    - clean_shutdown: close all clients gracefully on server shutdown
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    @property
    def active_count(self) -> int:
        """Return number of currently tracked connections."""
        return len(self.active_connections)

    async def connect(self, websocket: WebSocket):
        """Accept connection and add to active pool."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove connection from active pool."""
        self.active_connections.discard(websocket)

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a JSON payload to an individual connection."""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)

    async def send(self, message: Dict[str, Any], websocket: WebSocket):
        """Alias for send_personal_message — preferred in Sprint 4 code."""
        await self.send_personal_message(message, websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast a JSON payload to all connected clients concurrently.

        Uses asyncio.gather so a slow or stalled client does not hold up
        delivery to all other clients.  Any failed send automatically removes
        the dead connection from the active pool.
        """
        if not self.active_connections:
            return

        # Snapshot to avoid modifying the set during iteration
        connections = list(self.active_connections)
        dead: Set[WebSocket] = set()

        async def _send_one(conn: WebSocket):
            try:
                await conn.send_json(message)
            except Exception:
                dead.add(conn)

        await asyncio.gather(*(_send_one(c) for c in connections), return_exceptions=True)

        for conn in dead:
            self.disconnect(conn)

    async def remove_dead_connections(self):
        """
        Clean up any dead or closed connections.
        Checks WebSocket client_state for a DISCONNECTED flag.
        """
        dead: Set[WebSocket] = set()
        for conn in list(self.active_connections):
            try:
                state = getattr(conn, "client_state", None)
                if state is not None and state.name == "DISCONNECTED":
                    dead.add(conn)
            except Exception:
                dead.add(conn)
        for d in dead:
            self.disconnect(d)

    async def clean_shutdown(self):
        """
        Gracefully close all remaining connections on server shutdown.
        Sends a close frame to each client so they know the server is going away.
        """
        connections = list(self.active_connections)
        for conn in connections:
            try:
                await conn.close(code=1001, reason="Server shutting down")
            except Exception:
                pass
            self.disconnect(conn)


manager = ConnectionManager()
