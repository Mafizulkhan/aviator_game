"""
Anti-Gravity Configuration
Central configuration constants for the app.

Network URLs (API_BASE_URL / WS_URL) are resolved dynamically by
app.android_config so that the same APK works across development, staging,
and production without hard-coding localhost or a developer's LAN IP.
"""

from app.android_config import get_api_base_url, get_ws_base_url

APP_NAME = "Anti-Gravity"
APP_VERSION = "0.2.0"

# ── Wallet ──────────────────────────────────────────────────────────────────
STARTING_BALANCE = 10_000
MIN_BET = 10
MAX_BET = 5_000

# ── Game engine (local demo mode) ───────────────────────────────────────────
DEMO_MODE = True          # True → use local engine; False → use FastAPI backend
MULTIPLIER_TICK_RATE = 0.05   # seconds between multiplier updates

# ── Backend URLs ─────────────────────────────────────────────────────────────
# Resolved at import time via android_config.  Override with env vars:
#   ANTI_GRAVITY_API_URL  — full REST base URL
#   ANTI_GRAVITY_WS_URL   — full WebSocket URL
#   ANTI_GRAVITY_ENV      — "development" | "staging" | "production"
#
# On Android, do NOT assume localhost/127.0.0.1 refers to a remote machine.
# See app/android_config.py for setup instructions.
API_BASE_URL = get_api_base_url()
WS_URL = get_ws_base_url()

# ── UI ───────────────────────────────────────────────────────────────────────
FONT_NAME = "Roboto"
ANIMATION_SPEED = 1.0     # multiplier for all UI animations

# ── Round history displayed on game screen ───────────────────────────────────
HISTORY_DISPLAY_COUNT = 10

# ── Sound ────────────────────────────────────────────────────────────────────
SOUND_ENABLED_DEFAULT = True
MUSIC_ENABLED_DEFAULT = True
VOLUME_DEFAULT = 0.8
