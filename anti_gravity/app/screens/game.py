"""
Anti-Gravity — Game Screen
The core live game UI synchronized with the server-authoritative WebSocket (/ws/game)
and REST API (/api/game/*).

Handles:
- Live WebSocket event stream (ROUND_WAITING, ROUND_STARTED, MULTIPLIER_UPDATE, ROUND_CRASHED, ROUND_ENDED)
- Smooth spider vertical animation driven by server multiplier
- Double-tap safe cash-out requests via POST /api/game/cashout
- Automatic resynchronization on reconnection
- Non-intrusive connection status indicator
"""

import logging

try:
    from kivy.uix.screenmanager import Screen
    from kivy.clock import Clock
    from kivy.animation import Animation
    from kivy.properties import (
        NumericProperty, StringProperty, BooleanProperty, ListProperty
    )
except ImportError:
    # Graceful fallback for non-Kivy headless testing environments
    class Screen:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class Clock:
        @staticmethod
        def schedule_once(fn, timeout=0):
            try:
                fn(0)
            except Exception:
                pass

        @staticmethod
        def schedule_interval(fn, timeout=0):
            pass

    class Animation:
        def __init__(self, **kwargs):
            pass
        def start(self, widget):
            pass
        @staticmethod
        def stop_all(widget, prop):
            pass

    def NumericProperty(default=0.0):
        return default
    def StringProperty(default=""):
        return default
    def BooleanProperty(default=False):
        return default
    def ListProperty(default=None):
        return default if default is not None else []

from app.services.websocket import get_ws_client, ConnectionState
from app.services.api_client import get_api_client
from app.engine.game_engine import MultiplierEngine, GameEngine, GameState, Wallet
from app.config import (
    STARTING_BALANCE, MIN_BET, MAX_BET,
    MULTIPLIER_TICK_RATE, HISTORY_DISPLAY_COUNT, DEMO_MODE
)
from app.utils.sound_manager import SoundManager

logger = logging.getLogger("anti_gravity.game_screen")


class GameScreen(Screen):
    """
    Main live game screen.
    Driven by the server-authoritative WebSocket and REST backend.
    """

    # ── KV-bindable properties ────────────────────────────────────────────────
    multiplier_text          = StringProperty("1.00x")
    balance_text             = StringProperty("10,000")
    bet_text                 = StringProperty("100")
    status_text              = StringProperty("PLACE YOUR BET")
    history_items            = ListProperty([])         # last N crash multipliers
    cashout_enabled          = BooleanProperty(False)
    bet_enabled              = BooleanProperty(True)
    spider_y_ratio           = NumericProperty(0.15)    # 0.15 (bottom) → 0.85 (top)
    multiplier_color         = ListProperty([0.2, 1.0, 0.6, 1.0])   # neon green
    result_visible           = BooleanProperty(False)
    result_text              = StringProperty("")
    result_color             = ListProperty([1.0, 1.0, 1.0, 1.0])
    connection_status_text   = StringProperty("● Connecting...")
    connection_status_color  = ListProperty([0.6, 0.6, 0.9, 1.0])

    # ── Preset bet amounts ────────────────────────────────────────────────────
    BET_PRESETS = [10, 50, 100, 500, 1_000]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._wallet = Wallet(STARTING_BALANCE)
        self._engine = GameEngine(self._wallet)
        self._current_bet = 100
        self._active_bet_id = None
        self._has_active_bet = False
        self._is_cashing_out = False
        self._current_round_id = None

        self._ws = get_ws_client()
        self._api = get_api_client()

    def on_enter(self):
        """Called when user enters the game screen."""
        self._current_bet = 100
        self.bet_text = str(self._current_bet)
        self._is_cashing_out = False

        # Register WebSocket event listeners
        self._ws.add_listener("ROUND_WAITING", self._on_ws_round_waiting)
        self._ws.add_listener("ROUND_STARTED", self._on_ws_round_started)
        self._ws.add_listener("MULTIPLIER_UPDATE", self._on_ws_multiplier_update)
        self._ws.add_listener("ROUND_CRASHED", self._on_ws_round_crashed)
        self._ws.add_listener("ROUND_ENDED", self._on_ws_round_ended)
        self._ws.add_state_listener(self._on_ws_state_change)
        self._ws.set_reconnect_sync_hook(self._sync_current_state)

        # Connect WebSocket
        self._ws.connect()
        self._update_connection_ui(self._ws.state)

        # Synchronize current state with server
        self._sync_current_state()

    def on_leave(self):
        """Called when user leaves the game screen."""
        self._ws.remove_listener("ROUND_WAITING", self._on_ws_round_waiting)
        self._ws.remove_listener("ROUND_STARTED", self._on_ws_round_started)
        self._ws.remove_listener("MULTIPLIER_UPDATE", self._on_ws_multiplier_update)
        self._ws.remove_listener("ROUND_CRASHED", self._on_ws_round_crashed)
        self._ws.remove_listener("ROUND_ENDED", self._on_ws_round_ended)
        self._ws.remove_state_listener(self._on_ws_state_change)
        self._ws.set_reconnect_sync_hook(None)

    # ── WebSocket State & Synchronization ────────────────────────────────────
    def _on_ws_state_change(self, state: str, display_text: str):
        self._update_connection_ui(state)

    def _update_connection_ui(self, state: str):
        if state == ConnectionState.CONNECTED:
            self.connection_status_text = "● Connected"
            self.connection_status_color = [0.2, 0.9, 0.4, 1.0]  # Green
        elif state == ConnectionState.RECONNECTING:
            self.connection_status_text = "● Reconnecting..."
            self.connection_status_color = [1.0, 0.8, 0.2, 1.0]  # Yellow
        elif state == ConnectionState.CONNECTING:
            self.connection_status_text = "● Connecting..."
            self.connection_status_color = [0.6, 0.6, 0.9, 1.0]  # Blue
        else:
            self.connection_status_text = "● Connection lost"
            self.connection_status_color = [1.0, 0.3, 0.3, 1.0]  # Red

    def _sync_current_state(self):
        """Fetch current round state from server and sync UI."""
        def worker():
            round_data = self._api.get_current_round_sync()
            bal = self._api.get_balance_sync()
            if round_data:
                Clock.schedule_once(lambda dt: self._apply_synced_state(round_data, bal))

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _apply_synced_state(self, round_data: dict, balance: int = None):
        if balance is not None:
            self.balance_text = f"{balance:,}"

        status = round_data.get("status")
        self._current_round_id = round_data.get("round_id")
        mult = round_data.get("current_multiplier")

        if status == "running" and mult:
            self.multiplier_text = f"{mult:.2f}x"
            self._update_spider_position(mult)
            self.status_text = "FLYING…"
            if not self._has_active_bet:
                self.bet_enabled = False
                self.cashout_enabled = False
        elif status == "crashed":
            self.status_text = "ROUND FINISHED"
            self.bet_enabled = False
            self.cashout_enabled = False
        else:
            self.multiplier_text = "1.00x"
            self.spider_y_ratio = 0.15
            self.status_text = "PLACE YOUR BET"
            if not self._has_active_bet:
                self.bet_enabled = True
                self.cashout_enabled = False

    # ── WebSocket Event Handlers ──────────────────────────────────────────────
    def _on_ws_round_waiting(self, data: dict):
        """ROUND_WAITING: betting window open for next round."""
        self._current_round_id = data.get("round_id")
        self.multiplier_text = "1.00x"
        self.multiplier_color = [0.2, 1.0, 0.6, 1.0]
        self.spider_y_ratio = 0.15
        self.status_text = "PLACE YOUR BET"
        self.bet_enabled = True
        self.cashout_enabled = False
        self._is_cashing_out = False
        self._has_active_bet = False
        self._active_bet_id = None
        self.result_visible = False

    def _on_ws_round_started(self, data: dict):
        """ROUND_STARTED: round takeoff!"""
        self._current_round_id = data.get("round_id")
        self.result_visible = False
        self.multiplier_text = "1.00x"
        self.multiplier_color = [0.2, 1.0, 0.6, 1.0]
        self.spider_y_ratio = 0.15
        self.status_text = "FLYING…"
        self.bet_enabled = False

        if self._has_active_bet and self._active_bet_id:
            self.cashout_enabled = True
        else:
            self.cashout_enabled = False

        SoundManager.get().round_start()

    def _on_ws_multiplier_update(self, data: dict):
        """MULTIPLIER_UPDATE: live server multiplier tick."""
        mult = float(data.get("multiplier", 1.0))
        self.multiplier_text = f"{mult:.2f}x"
        self._update_spider_position(mult)

        # Warning color transitions
        if mult >= 5.0:
            self.multiplier_color = [1.0, 0.4, 0.1, 1.0]  # Orange
            SoundManager.get().warning()
        elif mult >= 3.0:
            self.multiplier_color = [1.0, 0.9, 0.1, 1.0]  # Yellow

    def _on_ws_round_crashed(self, data: dict):
        """ROUND_CRASHED: round ended in crash."""
        crash_mult = float(data.get("crash_multiplier", 1.0))
        self.cashout_enabled = False
        self._is_cashing_out = False
        self.multiplier_color = [1.0, 0.15, 0.15, 1.0]  # Red
        self.spider_y_ratio = 0.05  # Spider falls
        SoundManager.get().crash()
        self.status_text = f"CRASHED @ {crash_mult:.2f}x"

        # Update history strip
        crash_str = f"{crash_mult:.2f}x"
        self.history_items = ([crash_str] + list(self.history_items))[:HISTORY_DISPLAY_COUNT]

        # If user had an active bet, show loss
        if self._has_active_bet and self._active_bet_id:
            self.result_text = f"-{self._current_bet:,} credits  (crashed)"
            self.result_color = [1.0, 0.2, 0.2, 1.0]
            self.result_visible = True
            self._has_active_bet = False
            self._active_bet_id = None

    def _on_ws_round_ended(self, data: dict):
        """ROUND_ENDED: pause before next round."""
        self._has_active_bet = False
        self._active_bet_id = None
        self._is_cashing_out = False
        self.cashout_enabled = False
        self._sync_current_state()

    def _update_spider_position(self, mult: float):
        """Calculate spider height proportionally from multiplier."""
        t = MultiplierEngine.time_at_multiplier(mult)
        target_y = min(0.85, max(0.15, 0.15 + (t / 60.0) * 0.70))
        # Animate smoothly to target position
        Animation.stop_all(self, 'spider_y_ratio')
        anim = Animation(spider_y_ratio=target_y, duration=0.04)
        anim.start(self)

    # ── User Action Handlers ──────────────────────────────────────────────────
    def on_preset_bet(self, amount: int):
        if not self.bet_enabled:
            return
        self._current_bet = max(MIN_BET, min(MAX_BET, amount))
        self.bet_text = f"{self._current_bet:,}"
        SoundManager.get().click()

    def on_bet_minus(self):
        if not self.bet_enabled:
            return
        self._current_bet = max(MIN_BET, self._current_bet - 10)
        self.bet_text = f"{self._current_bet:,}"
        SoundManager.get().click()

    def on_bet_plus(self):
        if not self.bet_enabled:
            return
        self._current_bet = min(MAX_BET, self._current_bet + 10)
        self.bet_text = f"{self._current_bet:,}"
        SoundManager.get().click()

    def on_play(self):
        """Player places a bet."""
        if not self.bet_enabled:
            return

        self.bet_enabled = False
        self.status_text = "PLACING BET..."
        self.result_visible = False

        def on_join_success(data: dict):
            self._active_bet_id = data.get("bet_id")
            self._has_active_bet = True
            bal = data.get("balance_after")
            if bal is not None:
                self.balance_text = f"{bal:,}"
            self.status_text = "BET PLACED — WAITING FOR TAKEOFF"
            self.bet_enabled = False

        def on_join_failure(err: str):
            self.status_text = err
            self.bet_enabled = True

        self._api.join_round_async(self._current_bet, on_join_success, on_join_failure)

    def on_cashout(self):
        """Player requests cash-out."""
        if not self.cashout_enabled or self._is_cashing_out:
            return

        # Immediate lock to prevent double-taps
        self.cashout_enabled = False
        self._is_cashing_out = True

        if not self._active_bet_id:
            self._is_cashing_out = False
            return

        def on_cashout_success(data: dict):
            self._is_cashing_out = False
            cashout_mult = data.get("cashout_multiplier", 1.0)
            payout = data.get("payout", 0)
            bal = data.get("balance_after")
            if bal is not None:
                self.balance_text = f"{bal:,}"

            profit = payout - self._current_bet
            self.result_text = f"+{profit:,} credits  ({cashout_mult:.2f}x)"
            self.result_color = [0.2, 1.0, 0.6, 1.0]
            self.result_visible = True
            self.status_text = f"CASHED OUT @ {cashout_mult:.2f}x"
            self._has_active_bet = False
            self._active_bet_id = None
            SoundManager.get().cashout()

        def on_cashout_failure(err: str):
            self._is_cashing_out = False
            self.status_text = err

        self._api.cashout_async(self._active_bet_id, on_cashout_success, on_cashout_failure)

    def on_back(self):
        SoundManager.get().click()
        if hasattr(self, "manager") and self.manager:
            self.manager.current = "home"
