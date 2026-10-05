# Anti-Gravity — Profile Screen

from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, NumericProperty
from app.engine.game_engine import RoundResult


class ProfileScreen(Screen):
    username      = StringProperty("Player")
    games_played  = StringProperty("0")
    wins          = StringProperty("0")
    losses        = StringProperty("0")
    best_cashout  = StringProperty("—")
    current_bal   = StringProperty("0")

    def on_enter(self):
        self._compute_stats()

    def _compute_stats(self):
        game = self.manager.get_screen("game")
        history: list[RoundResult] = game._engine.history
        wallet = game._wallet

        wins   = [r for r in history if r.won]
        losses = [r for r in history if not r.won]
        best   = max((r.cashout_multiplier for r in wins), default=None)

        self.games_played = str(len(history))
        self.wins         = str(len(wins))
        self.losses       = str(len(losses))
        self.best_cashout = f"{best:.2f}x" if best else "—"
        self.current_bal  = f"{wallet.balance:,}"

    def on_back(self):
        self.manager.current = "home"
