"""
Anti-Gravity Backend — WebSocket Integration Tests (Sprint 4 Preparation)

Tests the /ws/game endpoint for:
- Basic connection acceptance
- CONNECTED confirmation message on connect
- Ping → pong response
- Safe disconnect handling
- ConnectionManager unit behaviour

Run with:
    python -m pytest tests/test_websocket.py -v

NOTES:
- WebSocket tests use Starlette's synchronous TestClient (not httpx AsyncClient)
  because Starlette's WS support is synchronous.
- The TestClient creates its own anyio event loop; the async db_session fixture
  from test_backend.py lives in a different loop and must NOT be mixed here.
- Fixture scope is 'module': a single TestClient is shared across all WS tests
  to avoid multiple anyio event loop / aiosqlite pool lifecycle conflicts.
- The /ws/game endpoint only sends one message on connect in this sprint:
    CONNECTED  (always sent immediately)
  Full round-state snapshots will be added in the next Sprint 4 step.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.services.game_service import _active_round_internal
from backend.ws.connection_manager import ConnectionManager


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def ws_client():
    """
    Synchronous Starlette TestClient for WebSocket tests.

    Scoped to 'module' so all WS tests share a single TestClient (and thus
    a single anyio event loop + SQLAlchemy pool).  Restarting the TestClient
    per-function caused the aiosqlite pool to be GC'd between tests, making
    the next init_db() call fail with 'no active connection'.

    We do NOT inject a DB override: WS tests do not require authentication
    or DB queries (the CONNECTED message is DB-free).
    """
    _active_round_internal.clear()
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
    _active_round_internal.clear()


# ════════════════════════════════════════════════════════════════════════════════
# ConnectionManager Unit Tests
# ════════════════════════════════════════════════════════════════════════════════

class TestConnectionManager:
    """Unit tests for ConnectionManager without a live WebSocket."""

    def test_manager_starts_empty(self):
        cm = ConnectionManager()
        assert len(cm.active_connections) == 0

    def test_disconnect_nonexistent_is_safe(self):
        """disconnect() must not raise even when the socket is unknown."""
        cm = ConnectionManager()

        class FakeSocket:
            pass

        # Should not raise
        cm.disconnect(FakeSocket())  # type: ignore[arg-type]
        assert len(cm.active_connections) == 0

    def test_manager_has_required_methods(self):
        """All four Sprint 4 methods must exist on ConnectionManager."""
        cm = ConnectionManager()
        assert callable(getattr(cm, "connect", None))
        assert callable(getattr(cm, "disconnect", None))
        assert callable(getattr(cm, "send", None))
        assert callable(getattr(cm, "broadcast", None))


# ════════════════════════════════════════════════════════════════════════════════
# WebSocket Endpoint Integration Tests
# ════════════════════════════════════════════════════════════════════════════════

class TestWebSocketEndpoint:

    def test_ws_endpoint_accepts_connection(self, ws_client):
        """The /ws/game endpoint must accept a WebSocket connection."""
        with ws_client.websocket_connect("/ws/game") as ws:
            assert ws is not None

    def test_ws_sends_connected_message_on_connect(self, ws_client):
        """First message must be type=CONNECTED with required fields."""
        with ws_client.websocket_connect("/ws/game") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "CONNECTED"
            assert "message" in msg
            assert "server_time" in msg
            assert "Anti-Gravity" in msg["message"]

    def test_ws_connected_message_fields(self, ws_client):
        """CONNECTED message must include string 'message' and 'server_time'."""
        with ws_client.websocket_connect("/ws/game") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "CONNECTED"
            assert isinstance(msg.get("message"), str)
            assert isinstance(msg.get("server_time"), str)
            assert len(msg["server_time"]) > 0

    def test_ws_ping_pong(self, ws_client):
        """Sending a ping must receive a pong response."""
        with ws_client.websocket_connect("/ws/game") as ws:
            ws.receive_json()  # CONNECTED
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"
            assert "server_time" in pong

    def test_ws_multiple_pings(self, ws_client):
        """Multiple pings in a row must each receive a pong."""
        with ws_client.websocket_connect("/ws/game") as ws:
            ws.receive_json()  # CONNECTED
            for _ in range(3):
                ws.send_json({"type": "ping"})
                pong = ws.receive_json()
                assert pong["type"] == "pong"

    def test_ws_invalid_json_gets_error_response(self, ws_client):
        """Sending invalid JSON must trigger an ERROR message."""
        with ws_client.websocket_connect("/ws/game") as ws:
            ws.receive_json()  # CONNECTED
            ws.send_text("not valid json }{")
            err = ws.receive_json()
            assert err["type"] == "ERROR"
            assert "Invalid message format" in err["message"]

    def test_ws_disconnect_is_safe(self, ws_client):
        """The server must handle client disconnect without crashing."""
        with ws_client.websocket_connect("/ws/game") as ws:
            ws.receive_json()  # CONNECTED
            # Context manager exit triggers disconnect — no exception expected

    def test_ws_unknown_message_type_is_ignored(self, ws_client):
        """Unknown message types must not cause the server to crash.

        The endpoint only handles 'ping' explicitly; everything else is
        silently ignored. We verify the connection stays alive by sending
        a subsequent ping and receiving pong.
        """
        with ws_client.websocket_connect("/ws/game") as ws:
            ws.receive_json()  # CONNECTED

            # Send an unknown message type — should be ignored
            ws.send_json({"type": "UNKNOWN_COMMAND", "data": "irrelevant"})

            # Connection should remain open — send ping and expect pong
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"

    def test_ws_multiple_sequential_connections(self, ws_client):
        """Multiple independent connections must each get CONNECTED."""
        for _ in range(3):
            with ws_client.websocket_connect("/ws/game") as ws:
                msg = ws.receive_json()
                assert msg["type"] == "CONNECTED"
