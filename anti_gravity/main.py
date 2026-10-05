"""
Anti-Gravity — Main Application Entry Point
============================================
Run on desktop:   python main.py
Build for Android: see README.md → Android section

The FastAPI backend (backend/) is NOT started here.
The APK is a client only.  The backend must be running on a reachable server.
"""

import os
import sys

# Ensure the package root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Kivy environment tweaks (must be before kivy imports) ────────────────────
os.environ.setdefault("KIVY_NO_ENV_CONFIG", "1")

# Desktop dev: simulate a phone screen density.
# On Android, Kivy reads the real device metrics — do not force density.
if sys.platform not in ("android", "ios"):
    os.environ.setdefault("KIVY_METRICS_DENSITY", "1.5")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.core.window import Window
from kivy.lang import Builder

from app.screens.splash   import SplashScreen
from app.screens.home     import HomeScreen
from app.screens.game     import GameScreen
from app.screens.history  import HistoryScreen
from app.screens.profile  import ProfileScreen
from app.screens.settings import SettingsScreen
from app.screens.tutorial import TutorialScreen

# ── Load all KV files ────────────────────────────────────────────────────────
# os.path.abspath ensures this works regardless of cwd (important on Android
# where the working directory may differ from the app package directory).
_KV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "kv")
for _kv_file in sorted(os.listdir(_KV_DIR)):
    if _kv_file.endswith(".kv"):
        Builder.load_file(os.path.join(_KV_DIR, _kv_file))


class AntiGravityApp(App):
    """Root Kivy application."""

    title = "Anti-Gravity"
    icon  = ""   # set to icon path if you have one (e.g. app/assets/images/icon.png)

    def build(self):
        # Desktop dev window — phone portrait ratio.
        # On Android, Kivy manages the window automatically; do not set size.
        if sys.platform not in ("android", "ios"):
            Window.size = (400, 750)
            Window.clearcolor = (0.04, 0.04, 0.10, 1)

        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(SplashScreen(name="splash"))
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(GameScreen(name="game"))
        sm.add_widget(HistoryScreen(name="history"))
        sm.add_widget(ProfileScreen(name="profile"))
        sm.add_widget(SettingsScreen(name="settings"))
        sm.add_widget(TutorialScreen(name="tutorial"))

        sm.current = "splash"
        return sm

    def on_pause(self):
        """Called by Android when the app goes to background.
        Return True to allow the app to stay alive (not destroyed).
        This preserves the WebSocket connection state across brief interruptions.
        """
        return True

    def on_resume(self):
        """Called by Android when the app returns from background.
        The WebSocket client auto-reconnects if the connection dropped.
        """
        pass


if __name__ == "__main__":
    AntiGravityApp().run()
