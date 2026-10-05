# Anti-Gravity — Tutorial Screen

from kivy.uix.screenmanager import Screen


TUTORIAL_PAGES = [
    {
        "title": "Welcome to Anti-Gravity",
        "body": (
            "A futuristic spider climbs through space.\n"
            "The multiplier starts at 1.00× and keeps rising.\n\n"
            "Your job: cash out before it crashes!"
        ),
        "icon": "🕷️",
    },
    {
        "title": "Place Your Bet",
        "body": (
            "Pick a bet amount from the preset buttons,\n"
            "or use ＋ / － to set a custom value.\n\n"
            "Press PLAY to start the round."
        ),
        "icon": "💰",
    },
    {
        "title": "Cash Out in Time",
        "body": (
            "Press CASH OUT at any point while the spider is flying.\n\n"
            "Cash out at 2.35× on a 100-credit bet → you win 235 credits.\n"
            "Miss it → you lose your bet."
        ),
        "icon": "✅",
    },
    {
        "title": "Provably Fair",
        "body": (
            "Every crash point is generated before the round starts\n"
            "using a cryptographic seed.\n\n"
            "The seed hash is shown before the round.\n"
            "The full seed is revealed after — you can verify it!"
        ),
        "icon": "🔐",
    },
]


class TutorialScreen(Screen):
    def on_back(self):
        self.manager.current = "home"
