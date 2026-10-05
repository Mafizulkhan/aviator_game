"""
Anti-Gravity — Android / Network Server Configuration
======================================================

This module provides a single, clean place to configure the FastAPI backend
URL for all environments (development, staging, production).

HOW TO CHANGE THE SERVER URL:
------------------------------
1. Set the environment variable ANTI_GRAVITY_API_URL before launching, OR
2. Edit the DEFAULT_ENV constant below to point at your server, OR
3. On Android, edit res/values/ag_config.xml (Buildozer post-build step).

DEVELOPMENT (LAN testing with Android device on same WiFi):
   Set API_BASE_URL = "http://192.168.X.X:8000/api"   (your dev machine LAN IP)
   Set WS_BASE_URL  = "ws://192.168.X.X:8000/ws/game"

   ⚠ Do NOT use http://localhost or http://127.0.0.1 on physical Android device.
     localhost on Android refers to the device itself, not your dev machine.

STAGING:
   Set API_BASE_URL = "http://staging.yourdomain.com:8000/api"
   Set WS_BASE_URL  = "ws://staging.yourdomain.com:8000/ws/game"

PRODUCTION:
   Set API_BASE_URL = "https://api.yourdomain.com/api"
   Set WS_BASE_URL  = "wss://api.yourdomain.com/ws/game"

ENVIRONMENT DETECTION:
   The environment is selected by the ANTI_GRAVITY_ENV variable:
     development  → DEV_* constants
     staging      → STAGING_* constants
     production   → PRODUCTION_* constants
   If not set, DEFAULT_ENV is used.

SECURITY:
   - No secrets (JWT signing keys, DB passwords, server seeds) live here.
   - This file contains only client-facing network addresses.
   - Server-side secrets stay in backend/.env (never packaged in APK).
"""

import os

# ── Environment names ──────────────────────────────────────────────────────────
ENV_DEVELOPMENT = "development"
ENV_STAGING = "staging"
ENV_PRODUCTION = "production"

# ── Default environment (change this for your build target) ───────────────────
# For a debug APK pointed at a LAN dev server, change to your LAN IP below.
DEFAULT_ENV = ENV_DEVELOPMENT

# ── Development server (LAN / local machine) ──────────────────────────────────
# IMPORTANT: replace 192.168.1.100 with your dev machine's LAN IP address.
# Run `ipconfig` (Windows) or `ip addr` (Linux) to find it.
# Do NOT use localhost/127.0.0.1 — those resolve to the Android device itself.
DEV_API_BASE_URL = "http://192.168.1.100:8000/api"
DEV_WS_BASE_URL = "ws://192.168.1.100:8000/ws/game"

# ── Staging server ─────────────────────────────────────────────────────────────
STAGING_API_BASE_URL = "http://staging.example.com:8000/api"
STAGING_WS_BASE_URL = "ws://staging.example.com:8000/ws/game"

# ── Production server ──────────────────────────────────────────────────────────
PRODUCTION_API_BASE_URL = "https://api.example.com/api"
PRODUCTION_WS_BASE_URL = "wss://api.example.com/ws/game"

# ── Desktop fallback (for desktop development only, NOT for Android) ───────────
DESKTOP_API_BASE_URL = "http://127.0.0.1:8000/api"
DESKTOP_WS_BASE_URL = "ws://127.0.0.1:8000/ws/game"

# ── URL resolution ─────────────────────────────────────────────────────────────
_ENV_MAP = {
    ENV_DEVELOPMENT: (DEV_API_BASE_URL, DEV_WS_BASE_URL),
    ENV_STAGING: (STAGING_API_BASE_URL, STAGING_WS_BASE_URL),
    ENV_PRODUCTION: (PRODUCTION_API_BASE_URL, PRODUCTION_WS_BASE_URL),
}


def _is_android() -> bool:
    """Return True when running on a real Android device via Kivy/p4a."""
    try:
        import sys
        return sys.platform == "android"
    except Exception:
        return False


def _is_desktop() -> bool:
    """Return True when running on a desktop OS (Windows, Linux, macOS)."""
    import sys
    return sys.platform not in ("android", "ios")


def get_api_base_url() -> str:
    """
    Return the correct REST API base URL for the current environment.

    Priority:
      1. ANTI_GRAVITY_API_URL environment variable (explicit override)
      2. ANTI_GRAVITY_ENV environment variable → maps to configured constant
      3. Desktop dev shortcut → localhost if not on Android
      4. DEFAULT_ENV constant
    """
    # Explicit override wins always
    explicit = os.environ.get("ANTI_GRAVITY_API_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")

    env = os.environ.get("ANTI_GRAVITY_ENV", "").strip().lower() or DEFAULT_ENV

    # On desktop, fall back to localhost for convenience
    if env == ENV_DEVELOPMENT and _is_desktop():
        return DESKTOP_API_BASE_URL

    api_url, _ = _ENV_MAP.get(env, _ENV_MAP[ENV_DEVELOPMENT])
    return api_url


def get_ws_base_url() -> str:
    """
    Return the correct WebSocket URL for the current environment.

    Priority:
      1. ANTI_GRAVITY_WS_URL environment variable (explicit override)
      2. ANTI_GRAVITY_ENV environment variable → maps to configured constant
      3. Desktop dev shortcut → ws://localhost if not on Android
      4. DEFAULT_ENV constant
    """
    explicit = os.environ.get("ANTI_GRAVITY_WS_URL", "").strip()
    if explicit:
        return explicit

    env = os.environ.get("ANTI_GRAVITY_ENV", "").strip().lower() or DEFAULT_ENV

    if env == ENV_DEVELOPMENT and _is_desktop():
        return DESKTOP_WS_BASE_URL

    _, ws_url = _ENV_MAP.get(env, _ENV_MAP[ENV_DEVELOPMENT])
    return ws_url
