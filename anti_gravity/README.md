# Anti-Gravity

> **A Spider Crash Adventure** — Virtual-credit crash arcade game built with Python/Kivy.

---

## Overview

Anti-Gravity is a provably-fair, virtual-credit crash game.  
A cyber-spider climbs through space while a multiplier rises from **1.00×**.  
The player cashes out before the spider crashes to win credits.

**No real money. No deposits. No withdrawals.**

---

## Project Structure

```
anti_gravity/
├── main.py                  ← App entry point (Kivy client only)
├── requirements.txt
├── buildozer.spec           ← Android build config (client APK only)
│
├── app/
│   ├── config.py            ← Central constants
│   ├── android_config.py    ← ⭐ Network URL configuration (dev/staging/prod)
│   ├── android_network_security.xml ← Android cleartext HTTP policy
│   ├── engine/
│   │   └── game_engine.py   ← Fairness, multiplier, wallet, crash logic
│   ├── screens/
│   │   ├── splash.py
│   │   ├── home.py
│   │   ├── game.py          ← Main game loop (server-authoritative)
│   │   ├── history.py
│   │   ├── profile.py
│   │   ├── settings.py
│   │   └── tutorial.py
│   ├── kv/                  ← KV layout files (UI)
│   ├── utils/
│   │   ├── sound_manager.py
│   │   └── kv_loader.py
│   └── assets/
│       ├── images/
│       ├── sounds/
│       └── fonts/
│
├── tests/
│   ├── test_android_config.py  ← Sprint 8: Android compatibility tests
│   └── ...
│
└── backend/                 ← FastAPI backend (server-side only, NOT in APK)
```

---

## Quick Start

### Prerequisites

> ⚠️ **Kivy requires Python 3.9–3.13**.  
> Python 3.14 has no pre-built Kivy wheel for Windows yet.  
> Use `py -3.12` or install via `pyenv`.

```powershell
# Create a virtual environment (Python 3.12 recommended)
py -3.12 -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install kivy[base] kivymd

# Run the app
cd anti_gravity
python main.py
```

### Run Unit Tests (no Kivy required)

```powershell
pip install pytest
cd anti_gravity
python -m pytest tests/ -v
```

---

## Gameplay

| Action | How |
|--------|-----|
| Select bet | Tap preset buttons (10, 50, 100, 500, 1K) or use +/– |
| Start round | Press **PLAY** |
| Cash out | Press **CASH OUT** before crash |
| View history | Main menu → History |
| Verify fairness | History → expand round → seed hash/reveal |

---

## Architecture Principles

- **Server-authoritative** (Sprint 3+): crash point and payouts computed server-side  
- **DEMO_MODE = True**: local Python engine for offline development  
- **Provably fair**: crash point derived from `HMAC-SHA256(server_seed, round_id)`  
- **Never trust client**: no balance/payout/multiplier from mobile app
- **APK is client only**: the FastAPI backend is never packaged inside the APK

---

## 🤖 Android APK — Sprint 8

### Overview

The Android APK contains **only the Kivy client** (`app/`).  
The FastAPI backend runs on a separate server and must be reachable from the device.  
`localhost`/`127.0.0.1` from an Android device resolves to the device itself — **not your dev machine**.

---

## 🚀 Build via GitHub Actions (Recommended — No WSL2 Required)

Build the debug APK entirely in the cloud using GitHub-hosted Ubuntu runners.  
**No local Linux, no WSL2, no Docker needed.**

---

### Step 1 — Ensure your repo is on GitHub

```powershell
# From your project root (d:\Project\aviator) — run once if not already done
git init
git remote add origin https://github.com/<your-username>/<your-repo>.git
```

---

### Step 2 — Commit and push the workflow file

```powershell
cd d:\Project\aviator

# Stage the workflow file and any other changes
git add .github/workflows/android-apk.yml
git add anti_gravity/

# Commit
git commit -m "ci: add GitHub Actions debug APK build workflow"

# Push to GitHub (replace 'main' with your branch name if different)
git push origin main
```

> ⚠️ **The workflow triggers automatically** on push to `main` or `master`.  
> You do **not** need to do anything else — GitHub starts the build immediately.

---

### Step 3 — Trigger a manual build (optional)

If you want to build without pushing code:

1. Go to your repository on **github.com**
2. Click **Actions** tab
3. Select **"Build Debug APK"** from the left sidebar
4. Click **"Run workflow"** → select branch → click **"Run workflow"** (green button)

---

### Step 4 — Monitor the build

The workflow has two sequential jobs:

| Job | What it does | Typical duration |
|-----|-------------|-----------------|
| `Run Test Suite (191 tests)` | Runs all 191 tests — must pass first | ~1–2 min |
| `Build Debug APK (Buildozer / Ubuntu)` | Downloads SDK/NDK, builds APK | ~20–45 min (first run) |

> **Subsequent builds are faster** (~5–15 min) because the SDK/NDK and ccache are cached between runs.

---

### Step 5 — Download the APK artifact

Once the `build-apk` job shows ✅:

1. Click on the completed workflow run
2. Scroll to **Artifacts** at the bottom of the run summary
3. Click **`anti-gravity-debug-apk`** to download a `.zip`
4. Unzip it — the `.apk` file is inside

**Artifact name:** `anti-gravity-debug-apk`  
**Artifact retention:** 30 days  
**APK filename:** determined at build time by `find bin/ -name "*-debug.apk"` — never hardcoded.  
Expected pattern: `antigravity-<version>-arm64-v8a-debug.apk`

---

### Step 6 — Install APK on your Android device via ADB

```powershell
# Verify your device is connected (ADB device ID: 26024877)
adb devices

# Install the APK (update the filename to match what was downloaded)
adb -s 26024877 install path\to\antigravity-0.2.0-arm64-v8a-debug.apk
```

---

### Workflow File Location

```
.github/workflows/android-apk.yml
```

---

### What the Workflow Does (Summary)

```
Job: test
  ├─ Checkout repo
  ├─ Python 3.12 + pip cache
  ├─ pip install -r requirements.txt
  ├─ pytest tests/ -v --tb=short     ← 191 tests must pass
  └─ Verify collected count >= 191

Job: build-apk   (only runs if test passes)
  ├─ Checkout repo
  ├─ apt-get: build-essential, jdk, cmake, autoconf, libtool, ccache ...
  ├─ Python 3.12
  ├─ Cache: pip / ~/.buildozer / .buildozer/ / ccache
  ├─ pip install buildozer cython
  ├─ Pre-accept Android SDK licenses
  ├─ buildozer android debug          ← builds arm64-v8a debug APK
  ├─ find bin/ -name "*-debug.apk"   ← locates actual APK (not hardcoded)
  ├─ Upload artifact: anti-gravity-debug-apk (30 days)
  └─ On failure: upload buildozer-build-log artifact
```

---

### If the Build Fails

1. Click the **failed job** in the Actions tab
2. Expand the **"Build debug APK"** step to see Buildozer output
3. Download the **`buildozer-build-log`** artifact for the full log
4. Common fixes:

| Error | Fix |
|-------|-----|
| `SDK license not accepted` | Already handled by workflow; re-run |
| `NDK not found` | Cache miss — re-run, it will re-download |
| `AIDL not found` | Handled by `build-essential` apt package |
| `Test suite failed` | Fix the failing test first — APK build is blocked |
| `<191 tests collected` | A test file was deleted — restore it |

---

### Prerequisites

Buildozer requires **Linux** (Ubuntu 20.04+ recommended).  
On Windows, use **WSL2 (Windows Subsystem for Linux 2)** — **or use GitHub Actions above (recommended)**.  

#### Install WSL2 on Windows

```powershell
# Run in PowerShell as Administrator
wsl --install
# Restart your computer, then open Ubuntu from Start menu
```

#### Inside WSL2 / Ubuntu — Install Buildozer dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Python and build tools
sudo apt install -y python3 python3-pip python3-venv git \
    build-essential libssl-dev libffi-dev \
    libltdl-dev zlib1g-dev cmake

# Java (required by Android SDK build tools)
sudo apt install -y default-jdk

# Android SDK/NDK dependencies
sudo apt install -y unzip wget autoconf automake libtool \
    libpcre3-dev libpcre2-dev

# Install Buildozer
pip3 install --user buildozer

# Ensure ~/.local/bin is on PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### Verify

```bash
buildozer --version
```

---

### Configure the API Server URL

> ⚠️ **Critical**: The default development URL in `app/android_config.py` uses  
> `192.168.1.100`. You MUST change this to your dev machine's LAN IP before building.

**Step 1**: Find your dev machine's LAN IP:

```powershell
# Windows
ipconfig
# Look for "IPv4 Address" under your WiFi adapter, e.g. 192.168.1.55
```

**Step 2**: Edit `app/android_config.py`:

```python
# Development server (LAN / local machine)
DEV_API_BASE_URL = "http://192.168.1.55:8000/api"   # ← your IP here
DEV_WS_BASE_URL  = "ws://192.168.1.55:8000/ws/game"  # ← your IP here
```

**Step 3**: Also update `app/android_network_security.xml`:

```xml
<domain includeSubdomains="false">192.168.1.55</domain>  <!-- your LAN IP -->
```

#### Environment Variable Override (No Code Change)

Set these before launching the APK (via ADB or intent extras) to override URLs at runtime:

| Variable | Description |
|---|---|
| `ANTI_GRAVITY_ENV` | `development` / `staging` / `production` |
| `ANTI_GRAVITY_API_URL` | Full REST API base URL override |
| `ANTI_GRAVITY_WS_URL` | Full WebSocket URL override |

#### Environments Summary

| Environment | API URL | WS URL |
|---|---|---|
| `development` (desktop) | `http://127.0.0.1:8000/api` | `ws://127.0.0.1:8000/ws/game` |
| `development` (Android) | `http://192.168.1.100:8000/api` ← edit this | `ws://192.168.1.100:8000/ws/game` |
| `staging` | `http://staging.example.com:8000/api` | `ws://staging.example.com:8000/ws/game` |
| `production` | `https://api.example.com/api` | `wss://api.example.com/ws/game` |

---

### Build Debug APK

#### 1. Start the backend on your dev machine

```bash
# On Windows host (not WSL)
cd anti_gravity
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

> `--host 0.0.0.0` makes the backend reachable from Android on the same WiFi network.

#### 2. Build inside WSL2

```bash
# Mount the project (WSL2 accesses Windows drives at /mnt/d/)
cd /mnt/d/Project/aviator/anti_gravity

# First build downloads Android SDK/NDK (~2 GB) — takes 15–30 min
buildozer android debug
```

#### 3. APK output

```
anti_gravity/bin/anti_gravity-0.2.0-arm64-v8a-debug.apk
```

> Exact filename depends on `version` and `android.archs` in `buildozer.spec`.

---

### Install APK on Android Device

#### Enable USB Debugging on the device

1. **Settings → About Phone → tap "Build Number" 7 times** (enables Developer Options)
2. **Settings → Developer Options → USB Debugging → ON**

#### Install via ADB

```bash
# In WSL2 or any terminal with ADB on PATH
adb install bin/anti_gravity-0.2.0-arm64-v8a-debug.apk

# Or with Windows ADB:
adb.exe install bin\anti_gravity-0.2.0-arm64-v8a-debug.apk
```

#### Install via Android Emulator (AVD)

Android emulator uses `10.0.2.2` to reach the host machine's localhost.  
This address is already whitelisted in `android_network_security.xml`.

Set in `android_config.py`:

```python
DEV_API_BASE_URL = "http://10.0.2.2:8000/api"
DEV_WS_BASE_URL  = "ws://10.0.2.2:8000/ws/game"
```

---

### Android Manual Test Checklist

After installing the debug APK, verify each item manually:

| # | Test | Expected |
|---|------|----------|
| 1 | Launch app | Splash screen appears with animation |
| 2 | Splash → Home | Auto-transitions to Home screen |
| 3 | Home screen | All 5 buttons visible and touchable |
| 4 | PLAY → Game screen | Game screen loads |
| 5 | WebSocket connection | "● Connected" indicator turns green |
| 6 | Wallet balance | Balance displayed in top bar |
| 7 | Bet controls | Presets and +/– work with touch |
| 8 | Place bet (PLAY) | "BET PLACED — WAITING FOR TAKEOFF" |
| 9 | Round starts | Spider begins climbing, multiplier rises |
| 10 | Multiplier updates | Live updates from server at ~20 fps |
| 11 | Spider animation | Spider moves smoothly upward |
| 12 | Color change at 3× | Multiplier turns yellow |
| 13 | Color change at 5× | Multiplier turns orange |
| 14 | CASH OUT | Shows payout result, updates balance |
| 15 | Crash event | "CRASHED @ X.XXx" displayed in red |
| 16 | Round ends | Returns to "PLACE YOUR BET" state |
| 17 | History screen | Round history shown |
| 18 | Profile screen | Stats shown |
| 19 | Settings screen | Sound/music toggle works |
| 20 | Tutorial screen | Pages display correctly |
| 21 | Back navigation | All back buttons work |
| 22 | Network disconnect | "● Connection lost" indicator turns red |
| 23 | Network reconnect | Auto-reconnects, turns green again |
| 24 | Background/foreground | App resumes correctly (on_pause/on_resume) |

---

### Buildozer Versions (Required)

These are the recommended versions for a reproducible build:

| Tool | Recommended Version |
|------|---------------------|
| Buildozer | 1.5.0+ |
| python-for-android | master (latest) |
| Kivy (in APK) | 2.3.1 |
| Android API | 33 |
| Android NDK | 25b |
| Android SDK | 33 |
| Target arch | arm64-v8a |

> Actual versions depend on what Buildozer downloads. Check the build log for exact versions.

---

### Troubleshooting

#### "Connection error" on Android

- Verify the backend is running: `curl http://192.168.1.X:8000/api/game/current`
- Verify the device and dev machine are on the same WiFi network
- Check `DEV_API_BASE_URL` in `app/android_config.py` has the correct LAN IP
- Ensure `android_network_security.xml` has that IP in the `<domain>` list
- Check Windows Firewall is not blocking port 8000 (`netsh advfirewall firewall add rule name="Anti-Gravity" dir=in action=allow protocol=TCP localport=8000`)

#### Build fails with "SDK not found"

```bash
buildozer android debug 2>&1 | grep -i "error"
# Accept Android SDK licenses
yes | $ANDROID_SDK_ROOT/tools/bin/sdkmanager --licenses
```

#### "AIDL not found"

```bash
sudo apt install aidl
```

#### APK installs but crashes immediately

```bash
adb logcat | grep "anti_gravity\|python\|kivy"
```

#### Buildozer on Windows (without WSL2)

Buildozer does not officially support Windows natively.  
You **must** use WSL2. Install WSL2 first (see Prerequisites above).  
Alternatively, use a GitHub Actions CI pipeline to build the APK in Ubuntu.

---

### Security Notes for Android

- The APK contains **no server secrets** (no JWT keys, no database passwords, no server seeds)
- All game logic, crash points, and payouts are computed server-side
- The client only displays data received from the server
- Production builds must use HTTPS/WSS (remove cleartext config from `android_network_security.xml`)
- **Do not** build a release/signed APK until all production server config is finalized

---

### Do NOT Build Release APK Yet

This sprint produces a **debug APK only**.  
A release/signed APK sprint will cover:
- Keystore generation and storage
- `buildozer android release`
- Google Play signing + App Bundle (AAB)
- ProGuard/minification review
- Final production URL configuration

---

| Sprint | Focus |
|--------|-------|
| 1 | UI screens (Kivy/KivyMD) ✅ |
| 2 | Local game engine ✅ |
| 3 | FastAPI backend + SQLite ✅ |
| 4 | WebSocket real-time sync ✅ |
| 5 | Fairness verification API ✅ |
| 6 | Authentication + security ✅ |
| 7 | Performance + stability ✅ |
| 8 | Android APK via Buildozer + GitHub Actions CI ✅ |
| 9 | Admin Panel Web App + RBAC + Audit Engine ✅ |
| 10 | Release signing + Play Store |

---

## Admin Operations & Audit Panel

The Anti-Gravity Admin Console is accessible via web browser at `http://localhost:8000/admin`.

- **Platform:** Authenticated Single-Page Web Dashboard (`admin/frontend/`)
- **Protected APIs:** `/api/admin/*`
- **Authentication:** Argon2id + JWT token
- **RBAC Roles:** `SUPER_ADMIN`, `ADMIN`, `OPERATOR`, `AUDITOR`, `SUPPORT`
- **Audit Logging:** Append-only database logs for all administrative actions
- **Fairness Inspector:** One-click cryptographic verification of pre-committed seeds and HMAC outcomes
- **Outcome Protection:** Strictly no backdoor or mechanism to manipulate authoritative round outcomes or crash multipliers
- **Maintenance Mode:** Server-side toggle to gracefully stop new bets while allowing active rounds to finish

---

## License

Virtual credits only. This is a game prototype — not a gambling product.
