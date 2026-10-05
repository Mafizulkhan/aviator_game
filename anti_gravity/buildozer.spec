[app]
# ── Application identity ──────────────────────────────────────────────────────
title = Anti-Gravity
package.name = antigravity
package.domain = com.yourstudio
version = 0.2.0

# ── Source configuration ──────────────────────────────────────────────────────
# Only include the Kivy client (app/) and the root entry point.
# Do NOT include the backend/ directory — the FastAPI server is NOT packaged.
source.dir = .

# File extensions included in the APK
source.include_exts = py,kv,png,jpg,jpeg,gif,wav,mp3,ogg,json,ttf,atlas

# Explicitly exclude backend, tests, dev tooling, and secrets from APK
source.exclude_dirs = backend,tests,.buildozer,.git,__pycache__,.pytest_cache,venv,.venv,dist
source.exclude_patterns = *.db,*.sqlite,*.pyc,*.pyo,.env,*.log,*.spec.bak

# ── Requirements (Android client ONLY) ───────────────────────────────────────
# Only packages required by app/ (Kivy client + network client).
# Backend packages (fastapi, uvicorn, sqlalchemy, aiosqlite, passlib,
# python-jose, pytest, pytest-asyncio) are NOT included — they are
# server-side only and must NOT be bundled in the APK.
#
# websocket-client: sync WS client used by app/services/websocket.py
# requests: used internally by some Kivy ecosystem packages
# httpx: used by app/services/api_client.py for REST calls
# certifi: required by httpx for TLS certificate validation
requirements = python3,kivy==2.3.1,kivymd==1.2.0,requests,websocket-client,httpx,certifi

# ── Display ───────────────────────────────────────────────────────────────────
orientation = portrait
fullscreen = 0

# ── Android SDK / NDK versions ────────────────────────────────────────────────
# Target API 33 (Android 13) — required by Google Play since Aug 2023.
# minapi 21 (Android 5.0) — minimum Kivy-supported Android version.
# NDK 25b — stable, well-tested with Kivy 2.3 / python-for-android.
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33

# ── Architecture ──────────────────────────────────────────────────────────────
# arm64-v8a: modern 64-bit ARM (covers virtually all Android devices since 2015)
# Add armeabi-v7a here if you need to support very old 32-bit-only devices.
android.archs = arm64-v8a

# ── Permissions ───────────────────────────────────────────────────────────────
# INTERNET            — required to reach FastAPI backend over TCP/WebSocket
# ACCESS_NETWORK_STATE — allows detecting network availability before connecting
# No camera, microphone, location, contacts, storage, or phone permissions needed.
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# ── Network security config (Android 9+) ────────────────────────────────────
# This file allows cleartext HTTP to the dev server LAN IP.
# In production, remove cleartext entries and use HTTPS/WSS only.
# See: app/android_network_security.xml
android.manifest.attributes = {"android:networkSecurityConfig": "@xml/ag_network_security"}

# ── KV files (Kivy language layouts) ─────────────────────────────────────────
# All .kv files in app/kv/ are picked up automatically via source.include_exts

# ── Build artifacts ───────────────────────────────────────────────────────────
# debug builds produce a .apk; release builds produce a .aab for Play Store
android.debug_artifact = apk
android.release_artifact = aab

# ── Application icon ─────────────────────────────────────────────────────────
# Uncomment and set path when you have an icon asset:
# icon.filename = %(source.dir)s/app/assets/images/icon.png

# ── Presplash (loading screen) ────────────────────────────────────────────────
# Uncomment and set path when you have a splash asset:
# presplash.filename = %(source.dir)s/app/assets/images/splash.png

# ── Python for Android (p4a) ──────────────────────────────────────────────────
# Branch/version of python-for-android to use (stable release)
p4a.branch = master

# ── Buildozer logging ─────────────────────────────────────────────────────────
[buildozer]
log_level = 2
warn_on_root = 1
