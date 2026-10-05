"""
Anti-Gravity — WebSocket Client Service
Manages real-time live game state synchronization via WebSocket (/ws/game).

States:
- CONNECTING
- CONNECTED
- DISCONNECTED
- RECONNECTING
- ERROR

Thread-safe: All UI callbacks are dispatched to the Kivy main thread using Clock.schedule_once.
"""

import json
import threading
import time
import logging
from typing import Callable, Dict, List, Optional, Any

from app.config import WS_URL

logger = logging.getLogger("anti_gravity.ws_client")


class ConnectionState:
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


STATE_DISPLAY_TEXT = {
    ConnectionState.CONNECTING: "Connecting...",
    ConnectionState.CONNECTED: "Connected",
    ConnectionState.DISCONNECTED: "Connection lost",
    ConnectionState.RECONNECTING: "Reconnecting...",
    ConnectionState.ERROR: "Connection error",
}


def _dispatch_ui(fn: Callable, *args, **kwargs):
    """Safely dispatch callback to Kivy UI main thread if Kivy is active."""
    try:
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: fn(*args, **kwargs))
    except Exception:
        # If Clock is unavailable or in non-Kivy test environment, call directly
        try:
            fn(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in direct callback dispatch: {e}")


class GameWebSocketClient:
    """
    Client-side WebSocket synchronization client for Anti-Gravity.
    Handles background connection, reconnection, message validation, and UI dispatching.
    """

    def __init__(self, url: str = WS_URL, auto_reconnect: bool = True, reconnect_delay: float = 2.0):
        self.url = url
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay
        self.state = ConnectionState.DISCONNECTED

        self._ws_app = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = False
        self._should_reconnect = False
        self._reconnect_attempts = 0

        # Event listeners: event_type -> list of callables
        self._listeners: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        # State listeners: list of callables(state: str, display_text: str)
        self._state_listeners: List[Callable[[str, str], None]] = []
        # Reconnect sync callback: called on successful reconnect
        self._reconnect_sync_hook: Optional[Callable[[], None]] = None

    @property
    def is_connected(self) -> bool:
        return self.state == ConnectionState.CONNECTED

    @property
    def display_status(self) -> str:
        return STATE_DISPLAY_TEXT.get(self.state, "Disconnected")

    # ── Listener Management ───────────────────────────────────────────────────
    def add_listener(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback for a specific WebSocket event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        if callback not in self._listeners[event_type]:
            self._listeners[event_type].append(callback)

    def remove_listener(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        """Unregister an event callback."""
        if event_type in self._listeners and callback in self._listeners[event_type]:
            self._listeners[event_type].remove(callback)

    def add_state_listener(self, callback: Callable[[str, str], None]):
        """Register a callback for connection state changes (state, display_text)."""
        if callback not in self._state_listeners:
            self._state_listeners.append(callback)

    def remove_state_listener(self, callback: Callable[[str, str], None]):
        """Unregister a state listener."""
        if callback in self._state_listeners:
            self._state_listeners.remove(callback)

    def set_reconnect_sync_hook(self, callback: Optional[Callable[[], None]]):
        """Set a callback invoked on reconnect to synchronize current round state."""
        self._reconnect_sync_hook = callback

    # ── State Notification ────────────────────────────────────────────────────
    def _set_state(self, new_state: str):
        """Update internal state and notify listeners on UI thread."""
        self.state = new_state
        display_text = STATE_DISPLAY_TEXT.get(new_state, "Disconnected")
        for listener in list(self._state_listeners):
            _dispatch_ui(listener, new_state, display_text)

    # ── Connection Management ─────────────────────────────────────────────────
    def connect(self, url: Optional[str] = None):
        """Start background connection to WebSocket server."""
        if url:
            self.url = url
        if self._is_running and self.state in (ConnectionState.CONNECTED, ConnectionState.CONNECTING):
            return

        self._is_running = True
        self._should_reconnect = self.auto_reconnect
        self._reconnect_attempts = 0

        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self._run_loop, name="AntiGravityWSClient", daemon=True)
        self._thread.start()

    def disconnect(self):
        """Gracefully disconnect from WebSocket and disable auto-reconnection."""
        self._should_reconnect = False
        self._is_running = False
        if self._ws_app:
            try:
                self._ws_app.close()
            except Exception:
                pass
        self._set_state(ConnectionState.DISCONNECTED)

    def _run_loop(self):
        """Background thread executing connection attempts and reconnection loop."""
        import websocket

        while self._is_running:
            if self._reconnect_attempts == 0:
                self._set_state(ConnectionState.CONNECTING)
            else:
                self._set_state(ConnectionState.RECONNECTING)

            try:
                self._ws_app = websocket.WebSocketApp(
                    self.url,
                    on_open=self._on_ws_open,
                    on_message=self._on_ws_message,
                    on_error=self._on_ws_error,
                    on_close=self._on_ws_close,
                )
                self._ws_app.run_forever(ping_interval=15, ping_timeout=5)
            except Exception as e:
                logger.warning(f"WebSocket run error: {e}")
                self._set_state(ConnectionState.ERROR)

            if not self._is_running or not self._should_reconnect:
                break

            self._reconnect_attempts += 1
            self._set_state(ConnectionState.RECONNECTING)
            # Short backoff sleep
            backoff = min(self.reconnect_delay * (1 + 0.5 * min(self._reconnect_attempts, 4)), 5.0)
            time.sleep(backoff)

        self._set_state(ConnectionState.DISCONNECTED)

    # ── WebSocket Callbacks ───────────────────────────────────────────────────
    def _on_ws_open(self, ws):
        logger.info("WebSocket connection established")
        was_reconnect = self._reconnect_attempts > 0
        self._reconnect_attempts = 0
        self._set_state(ConnectionState.CONNECTED)

        if was_reconnect and self._reconnect_sync_hook:
            _dispatch_ui(self._reconnect_sync_hook)

    def _on_ws_message(self, ws, message: str):
        self.handle_raw_message(message)

    def _on_ws_error(self, ws, error):
        logger.warning(f"WebSocket error: {error}")
        self._set_state(ConnectionState.ERROR)

    def _on_ws_close(self, ws, close_status_code, close_msg):
        logger.info(f"WebSocket closed (code: {close_status_code})")
        if self._should_reconnect and self._is_running:
            self._set_state(ConnectionState.RECONNECTING)
        else:
            self._set_state(ConnectionState.DISCONNECTED)

    # ── Message Parsing & Validation ──────────────────────────────────────────
    def handle_raw_message(self, raw_data: str) -> bool:
        """
        Validate and dispatch an incoming raw text message.
        Returns True if message was valid and dispatched, False otherwise.
        Guaranteed not to raise exceptions on malformed payloads.
        """
        try:
            payload = json.loads(raw_data)
        except Exception:
            logger.warning("Received invalid JSON on WebSocket")
            return False

        if not isinstance(payload, dict):
            logger.warning("WebSocket message is not a JSON object")
            return False

        event_type = payload.get("type")
        if not isinstance(event_type, str):
            logger.warning("WebSocket message missing 'type' field")
            return False

        # Validate specific event types
        if not self._validate_payload(event_type, payload):
            logger.warning(f"Invalid payload schema for event {event_type}: {payload}")
            return False

        # Dispatch to registered listeners
        self._dispatch_event(event_type, payload)
        return True

    def _validate_payload(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Ensure message contains required fields according to event type."""
        try:
            if event_type == "ROUND_WAITING":
                return "round_id" in data
            elif event_type == "ROUND_STARTED":
                return "round_id" in data
            elif event_type == "MULTIPLIER_UPDATE":
                return "round_id" in data and isinstance(data.get("multiplier"), (int, float))
            elif event_type == "ROUND_CRASHED":
                return "round_id" in data and isinstance(data.get("crash_multiplier"), (int, float))
            elif event_type == "ROUND_ENDED":
                return "round_id" in data
            elif event_type in ("CONNECTED", "ERROR", "pong"):
                return True
            # Allow custom or forward-compatible message types
            return True
        except Exception:
            return False

    def _dispatch_event(self, event_type: str, data: Dict[str, Any]):
        """Dispatch event payload to all registered listeners on the UI thread."""
        listeners = list(self._listeners.get(event_type, []))
        for listener in listeners:
            _dispatch_ui(listener, data)

    def send_ping(self):
        """Send a ping frame to server."""
        if self._ws_app and self.is_connected:
            try:
                self._ws_app.send(json.dumps({"type": "ping"}))
            except Exception as e:
                logger.warning(f"Failed to send ping: {e}")


# ── Global Singleton Access ───────────────────────────────────────────────────
_ws_client_instance: Optional[GameWebSocketClient] = None


def get_ws_client() -> GameWebSocketClient:
    """Retrieve or create the shared GameWebSocketClient instance."""
    global _ws_client_instance
    if _ws_client_instance is None:
        _ws_client_instance = GameWebSocketClient()
    return _ws_client_instance
