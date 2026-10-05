"""
Anti-Gravity Client — WebSocket & Live Sync Tests (Sprint 4C)
Validates all 12 required client-side synchronization scenarios:
1. WebSocket connection
2. Connection failure
3. Reconnection
4. ROUND_STARTED handling
5. MULTIPLIER_UPDATE handling
6. ROUND_CRASHED handling
7. ROUND_ENDED handling
8. Invalid message handling
9. Cash-out request handling
10. Duplicate cash-out prevention
11. Current-state synchronization after reconnect
12. Server restart recovery
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
import time
from unittest.mock import MagicMock, patch

from app.services.websocket import GameWebSocketClient, ConnectionState, STATE_DISPLAY_TEXT
from app.services.api_client import ApiClient


# ── 1. WebSocket Connection ───────────────────────────────────────────────────
def test_client_ws_connection():
    """Test WebSocket client initialization and state transition to CONNECTED."""
    client = GameWebSocketClient(url="ws://127.0.0.1:8000/ws/game", auto_reconnect=False)
    assert client.state == ConnectionState.DISCONNECTED
    assert client.display_status == "Connection lost"
    assert client.is_connected is False

    # Simulate connection open
    client._on_ws_open(None)
    assert client.state == ConnectionState.CONNECTED
    assert client.is_connected is True
    assert client.display_status == "Connected"


# ── 2. Connection Failure ─────────────────────────────────────────────────────
def test_client_ws_connection_failure():
    """Test that connection error safely transitions state to ERROR without crashing."""
    client = GameWebSocketClient(url="ws://127.0.0.1:8000/ws/game", auto_reconnect=False)
    state_changes = []
    client.add_state_listener(lambda state, text: state_changes.append(state))

    client._on_ws_error(None, Exception("Connection refused"))
    assert client.state == ConnectionState.ERROR
    assert "ERROR" in state_changes


# ── 3. Reconnection ───────────────────────────────────────────────────────────
def test_client_ws_reconnection():
    """Test that closing socket when auto_reconnect is enabled sets RECONNECTING."""
    client = GameWebSocketClient(url="ws://127.0.0.1:8000/ws/game", auto_reconnect=True)
    client._is_running = True
    client._should_reconnect = True

    client._on_ws_close(None, 1006, "Connection lost")
    assert client.state == ConnectionState.RECONNECTING
    assert client.display_status == "Reconnecting..."


# ── 4. ROUND_STARTED Handling ─────────────────────────────────────────────────
def test_client_round_started_handling():
    """Test receiving and dispatching valid ROUND_STARTED event."""
    client = GameWebSocketClient(url="ws://127.0.0.1:8000/ws/game", auto_reconnect=False)
    received = []
    client.add_listener("ROUND_STARTED", lambda data: received.append(data))

    msg = json.dumps({
        "type": "ROUND_STARTED",
        "round_id": 101,
        "round_number": 5,
        "server_time": "2026-10-03T00:00:00Z",
        "status": "running"
    })
    ok = client.handle_raw_message(msg)
    assert ok is True
    assert len(received) == 1
    assert received[0]["round_id"] == 101
    assert received[0]["status"] == "running"


# ── 5. MULTIPLIER_UPDATE Handling ─────────────────────────────────────────────
def test_client_multiplier_update_handling():
    """Test receiving and validating live MULTIPLIER_UPDATE events."""
    client = GameWebSocketClient(url="ws://127.0.0.1:8000/ws/game", auto_reconnect=False)
    updates = []
    client.add_listener("MULTIPLIER_UPDATE", lambda data: updates.append(data["multiplier"]))

    msg = json.dumps({
        "type": "MULTIPLIER_UPDATE",
        "round_id": 101,
        "multiplier": 2.45,
        "server_time": "2026-10-03T00:00:01Z"
    })
    ok = client.handle_raw_message(msg)
    assert ok is True
    assert updates == [2.45]


# ── 6. ROUND_CRASHED Handling ─────────────────────────────────────────────────
def test_client_round_crashed_handling():
    """Test receiving ROUND_CRASHED event with crash multiplier."""
    client = GameWebSocketClient(url="ws://127.0.0.1:8000/ws/game", auto_reconnect=False)
    crashes = []
    client.add_listener("ROUND_CRASHED", lambda data: crashes.append(data["crash_multiplier"]))

    msg = json.dumps({
        "type": "ROUND_CRASHED",
        "round_id": 101,
        "crash_multiplier": 3.78,
        "server_time": "2026-10-03T00:00:03Z"
    })
    ok = client.handle_raw_message(msg)
    assert ok is True
    assert crashes == [3.78]


# ── 7. ROUND_ENDED Handling ───────────────────────────────────────────────────
def test_client_round_ended_handling():
    """Test receiving ROUND_ENDED event."""
    client = GameWebSocketClient(url="ws://127.0.0.1:8000/ws/game", auto_reconnect=False)
    ended_events = []
    client.add_listener("ROUND_ENDED", lambda data: ended_events.append(data["round_id"]))

    msg = json.dumps({
        "type": "ROUND_ENDED",
        "round_id": 101,
        "server_time": "2026-10-03T00:00:05Z"
    })
    ok = client.handle_raw_message(msg)
    assert ok is True
    assert ended_events == [101]


# ── 8. Invalid Message Handling ───────────────────────────────────────────────
def test_client_invalid_message_handling():
    """Test that malformed JSON or missing fields are safely discarded without exceptions."""
    client = GameWebSocketClient(url="ws://127.0.0.1:8000/ws/game", auto_reconnect=False)

    # 1. Non-JSON string
    assert client.handle_raw_message("not valid json {[[") is False

    # 2. JSON array instead of object
    assert client.handle_raw_message("[1, 2, 3]") is False

    # 3. Missing 'type' attribute
    assert client.handle_raw_message('{"data": 123}') is False

    # 4. Invalid payload for MULTIPLIER_UPDATE (missing multiplier)
    assert client.handle_raw_message('{"type": "MULTIPLIER_UPDATE", "round_id": 1}') is False


# ── 9. Cash-out Request Handling ──────────────────────────────────────────────
def test_client_cashout_request_handling():
    """Test ApiClient cash-out execution with mocked backend response."""
    api = ApiClient(base_url="http://localhost:8000/api")
    api.set_token("fake_jwt_token", "test_user")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "bet_id": 10,
        "round_number": 1,
        "cashout_multiplier": 2.50,
        "payout": 250,
        "balance_after": 10150,
        "status": "cashed_out"
    }

    with patch("httpx.Client.post", return_value=mock_response):
        res = api.cashout_sync(bet_id=10)
        assert res is not None
        assert res["cashout_multiplier"] == 2.50
        assert res["payout"] == 250
        assert api.balance == 10150


# ── 10. Duplicate Cash-out Prevention ─────────────────────────────────────────
def test_client_duplicate_cashout_prevention():
    """Test that UI state prevents duplicate cash-out invocations."""
    from app.screens.game import GameScreen

    screen = GameScreen()
    screen._active_bet_id = 15
    screen.cashout_enabled = True
    screen._is_cashing_out = False

    # First cashout press
    with patch.object(screen._api, "cashout_async") as mock_cashout_async:
        screen.on_cashout()
        assert screen.cashout_enabled is False
        assert screen._is_cashing_out is True
        mock_cashout_async.assert_called_once()

        # Second rapid cashout press while first is in-flight
        screen.on_cashout()
        # Ensure it was not called a second time
        assert mock_cashout_async.call_count == 1


# ── 11. Current-State Synchronization After Reconnect ─────────────────────────
def test_client_state_sync_after_reconnect():
    """Test state synchronization callback is invoked upon reconnect."""
    client = GameWebSocketClient(url="ws://127.0.0.1:8000/ws/game", auto_reconnect=True)
    sync_called = []
    client.set_reconnect_sync_hook(lambda: sync_called.append(True))

    # Initial connect -> hook not called as reconnect
    client._reconnect_attempts = 0
    client._on_ws_open(None)
    assert len(sync_called) == 0

    # Simulate reconnect
    client._reconnect_attempts = 1
    client._on_ws_open(None)
    assert len(sync_called) == 1


# ── 12. Server Restart Recovery ───────────────────────────────────────────────
def test_client_server_restart_recovery():
    """Test client state transitions through close, reconnecting, and recovery."""
    client = GameWebSocketClient(url="ws://127.0.0.1:8000/ws/game", auto_reconnect=True)
    client._is_running = True
    client._should_reconnect = True

    # 1. Connected
    client._on_ws_open(None)
    assert client.state == ConnectionState.CONNECTED

    # 2. Server drops connection
    client._on_ws_close(None, 1006, "Server restart")
    assert client.state == ConnectionState.RECONNECTING

    # 3. Server comes back online and client reconnects
    client._on_ws_open(None)
    assert client.state == ConnectionState.CONNECTED
    assert client.is_connected is True
