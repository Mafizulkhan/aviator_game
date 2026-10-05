# Anti-Gravity — History Screen

from kivy.uix.screenmanager import Screen
from kivy.properties import ListProperty
from app.engine.game_engine import RoundResult
import time


class HistoryScreen(Screen):
    """
    Shows a scrollable list of past rounds with:
    round #, bet, crash point, cash-out multiplier, payout, result.
    """

    history_data = ListProperty([])   # list of dicts for RecycleView

    def on_enter(self):
        self._load_history()

    def _load_history(self):
        # Access history from the game screen's engine
        game_screen = self.manager.get_screen("game")
        rounds: list[RoundResult] = list(reversed(game_screen._engine.history))
        self.history_data = [
            {
                "round_id": r.round_id,
                "crash": f"{r.crash_multiplier:.2f}x",
                "bet": f"{r.bet:,}",
                "payout": f"{r.payout:,}",
                "cashout": f"{r.cashout_multiplier:.2f}x" if r.won else "—",
                "result": "WIN" if r.won else "LOSS",
                "result_color": [0.2, 1.0, 0.6, 1.0] if r.won else [1.0, 0.2, 0.2, 1.0],
                "seed_hash": r.server_seed_hash[:16] + "…",
            }
            for r in rounds
        ]

    def on_back(self):
        self.manager.current = "home"
