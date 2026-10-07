# Anti-Gravity — Complete App & Backend Development Plan

> **Document:** App + Core Backend Source of Truth  
> **Version:** 3.0  
> **Status:** Active  
> **Owner:** Mafizul Khan  
> **Development Environment:** Antigravity IDE · Windows · Python  
> **Primary Device:** Physical Android phone  
> **Product:** Anti-Gravity — virtual-credit-only online crash arcade game

## 0. Purpose of This Document

This document is the complete implementation specification for the **player Android application and its production backend**.

It covers:

- Python/Kivy/KivyMD Android application.
- Python/FastAPI production backend.
- PostgreSQL production database.
- REST and WebSocket networking.
- Online-only production operation.
- Server-authoritative game engine.
- Virtual-credit wallet.
- Fairness system.
- Player authentication and security.
- Anti-cheat.
- Reconnection and failure handling.
- Android build and physical-device testing.
- GitHub Actions APK/AAB pipeline.
- Testing, performance, deployment, monitoring, backup and recovery.

The **Admin Panel has its own dedicated specification**:
`Anti-Gravity_Admin_Panel_Development_Plan.md`

The Admin Panel must use the protected FastAPI admin APIs defined by this project and must never become a backdoor to authoritative game outcomes.

## 0.1 Non-Negotiable Product Boundary

Anti-Gravity is a **free-to-play virtual-credit game**.

Never implement:

- Real-money deposits.
- Real-money withdrawals.
- Cash prizes.
- Cryptocurrency wagering.
- Payment-based betting.
- Real-money wallet.
- Automated real-money betting.

## 0.2 Production Online-Only Rule

Development Demo Mode may use a local Python game engine and SQLite.

**Production must be 100% online.**

```text
Android APK
    |
 HTTPS / WSS
    |
 FastAPI Backend
    |
 +-- Authentication
 +-- Game Engine
 +-- Fairness Engine
 +-- Wallet
 +-- Anti-Cheat
 +-- REST API
 +-- WebSocket
    |
 PostgreSQL
```

If the production server is unavailable:

- Do not start a new round.
- Do not accept a new bet.
- Do not allow cash-out.
- Do not alter the wallet locally.
- Show connection/server status.
- Reconnect automatically.
- Synchronize authoritative state after reconnection.

The production APK must never silently fall back to Demo Mode.

## 0.3 Security Objective

No Internet-connected application can honestly be guaranteed to be "unhackable."

The security objective is **defense in depth**:

> Even if the APK is reverse-engineered, modified, repackaged, instrumented, or used to send malicious requests, the attacker must not be able to control the authoritative game, wallet, payout, round result, authentication system, or production database.

## 1. Project Overview

| Field | Value |
|---|---|
| **App Name** | Anti-Gravity |
| **Genre** | Crash / Multiplier Arcade Game |
| **Platform** | Android first — optional Windows / Web builds |
| **Primary Language** | Python (frontend and backend) |
| **Frontend** | Python + Kivy + KivyMD |
| **Backend** | Python + FastAPI |
| **Dev Environment** | Antigravity IDE |
| **Developer Laptop** | Windows |
| **Primary Test Device** | Physical Android phone |
| **Dev Database** | SQLite |
| **Prod Database** | PostgreSQL |
| **Game Model** | Virtual credits — no real money |

### Core Concept

Anti-Gravity is inspired by the visual and gameplay structure of crash-style games.

Instead of an airplane:

> A **cyber spider** climbs upward through a futuristic animated environment.

The multiplier starts at **1.00x** and increases continuously:

```
1.00x → 1.05x → 1.20x → 1.50x → 2.00x → 5.00x → 10.00x
```

At an unpredictable point, the spider crashes/falls. The player must press **CASH OUT** before the crash.

**Win example** — cash out at 2.35x with 100 credits:

```
100 × 2.35 = 235 virtual credits  (+135 profit)
```

**Loss example** — spider crashes before cash-out:

```
100 virtual credits → 0  (bet lost)
```

> [!IMPORTANT]
> This plan intentionally uses **virtual credits only** and does not implement deposits, withdrawals, or real-money wagering of any kind.

---

## 2. Product Goals

### MVP Goals

The first release must provide:

- Attractive spider-themed crash animation
- Live multiplier display
- Virtual-credit wallet
- Bet amount selection (preset + custom)
- Start round
- Cash-out button
- Crash animation with effects
- Win/loss calculation
- Round history
- Statistics screen
- Sound effects
- Settings screen
- Tutorial / How to Play
- Local account / profile
- Server-synchronized game rounds
- Fair / random crash generation
- Basic admin / debug panel

### Future Goals

Possible post-MVP additions:

- Multiplayer spectators
- Global leaderboards
- Achievements system
- Daily missions
- Daily virtual-credit login rewards
- Spider skins and visual themes
- Additional spider animations
- Multiple game environments
- Seasonal themes
- Cloud-synced accounts
- Push notifications

---

## 3. Important Product Boundary

Anti-Gravity must remain a **free-to-play virtual-credit game**.

**Never implement:**

- Deposits or withdrawals
- Cash prizes
- Cryptocurrency wagering
- Payment-based betting
- Real-money wallet
- Automated betting with real money

> [!WARNING]
> If the product is later intended to involve real-money gambling, that requires a **separate** legal/compliance architecture, jurisdiction-specific licensing, age verification, responsible-gaming controls, payment compliance, auditability, and certified game/RNG processes. This is entirely out of scope for V1.

---

## 4. Recommended Technology Stack

### Mobile App

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| UI Framework | Kivy 2.x |
| UI Components | KivyMD |
| Android Packaging | Buildozer + python-for-android |
| Android Tooling | Android SDK / NDK |

### Backend

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI |
| ASGI Server | Uvicorn |
| Validation | Pydantic v2 |
| ORM | SQLAlchemy 2.x |
| Password Hashing | passlib + argon2-cffi |
| Auth Tokens | python-jose (JWT) |

### Database

| Environment | Database |
|---|---|
| Development | SQLite |
| Production | PostgreSQL 15+ |

### Networking

```
REST API    — HTTP/HTTPS JSON endpoints
WebSocket   — live game updates (/ws/game)
HTTPS       — all production traffic encrypted
```

### Development Environment

```
Windows Laptop
   |
   +-- Antigravity IDE  -->  Python frontend + Python backend
   +-- Git / GitHub     -->  version control + CI
   +-- Android Studio   -->  Android SDK / Platform-Tools / Logcat
   +-- ADB              -->  physical Android phone debugging
   +-- GitHub Actions   -->  Linux Buildozer APK builds
```

**Rules:**
- Antigravity is the primary development environment.
- The developer laptop is Windows.
- Both frontend and backend are Python.
- The primary Android test target is a physical phone.
- Ubuntu/WSL2 is **not required** on the developer laptop for the planned CI APK workflow.
- Android Studio is used for Android tooling and debugging; the application is **not** rewritten as native Kotlin/Java.

---

## 5. Overall Architecture

```
                    ANTI-GRAVITY
                         |
          +--------------+--------------+
          |                             |
      Android App                  Backend Server
       Kivy/KivyMD                    FastAPI
          |                             |
          |   REST / WebSocket          |
          +-------------+---------------+
                        |
                   PostgreSQL
```

**Offline development / testing (Demo Mode):**

```
Kivy App
   |
Local Game Engine (Python)
   |
SQLite
```

---

## 6. Game Screen

```
+--------------------------------------------------+
|                  ANTI-GRAVITY                    |
|                                                  |
|             Current Multiplier                   |
|                   2.37x                          |
|                                                  |
|                    spider                        |
|                  / (climbing)                    |
|                                                  |
|        Animated deep-space background            |
|        Stars / neon grid / particles             |
|                                                  |
|  +--------------------------------------------+  |
|  | Bet Amount                                 |  |
|  | [ 10 ]  [ 50 ]  [ 100 ]  [ 500 ]          |  |
|  | [ Custom amount ]                          |  |
|  +--------------------------------------------+  |
|                                                  |
|              [ CASH OUT ]                        |
|                                                  |
| Balance: 10,000 credits                          |
|                                                  |
| Recent: 1.24x  3.55x  1.08x  7.21x             |
+--------------------------------------------------+
```

---

## 7. Main Game Flow

### Step 1 — Open App

Display splash screen:

```
ANTI-GRAVITY
A Spider Crash Adventure
Loading...
```

Then load the player profile and fetch current round state from server.

### Step 2 — Wallet Display

```
Balance
10,000 Credits
```

### Step 3 — Select Bet

Preset options:

```
10 | 50 | 100 | 500 | 1,000
```

Player may also enter a custom amount within the configured virtual-credit limits.

### Step 4 — Start Round

Server creates a unique round:

```
round_id          AG-20261002-00123
server_seed_hash  sha256(server_seed)
start_timestamp   UTC ISO-8601
```

### Step 5 — Multiplier Starts

```
1.00x
```

Then increases continuously using the server-side multiplier function.

### Step 6 — Spider Animation

Spider moves upward while multiplier increases. Animation state is driven by server time, not frame count.

### Step 7 — Cash Out

Player presses **CASH OUT**. Server validates round is still active.

```
Bet           = 100
Cash-out      = 2.85x
-------------------------------
Payout        = 285 credits
Profit        = 185 credits
```

### Step 8 — Crash

If crash occurs before cash-out:

```
CRASHED AT 1.73x
```

Bet is lost. Wallet is not updated.

### Step 9 — Round History

Stored per round:

| Field | Description |
|---|---|
| Round ID | Unique round identifier |
| Bet amount | Virtual credits wagered |
| Crash multiplier | Server-generated crash point |
| Cash-out multiplier | Player's exit point (if any) |
| Result | WON / LOST |
| Timestamp | UTC round end time |

---

## 8. Multiplier Engine

The multiplier is **server-controlled**. The client only displays the server state.

```python
multiplier = calculate_multiplier(elapsed_time)
```

**Reference growth curve:**

| Elapsed | Multiplier |
|---|---|
| 0.0 s | 1.00x |
| 1.0 s | 1.08x |
| 2.0 s | 1.18x |
| 3.0 s | 1.31x |
| 4.0 s | 1.46x |
| 5.0 s | 1.64x |
| 10.0 s | ~2.70x |

The exact growth curve (exponential base, speed factor) must be configurable via `game_settings`.

> [!IMPORTANT]
> The mobile application **must never** calculate or trust its own multiplier value. All multiplier values come from the server.

---

## 9. Crash Point Generation

For a fair virtual game, generate the crash point **before the round starts** using a cryptographically secure random generator.

```python
import secrets

random_value = secrets.randbits(256)
```

Then convert the random value into a crash multiplier using a documented mathematical function.

**Reference formula concept:**

```python
def calculate_crash_point(random_int: int, house_edge: float = 0.01) -> float:
    """
    Converts a 256-bit random integer to a crash multiplier.
    house_edge: fraction retained by house (e.g. 0.01 = 1%)
    """
    e = 2**256
    h = e - int(e * house_edge)
    if random_int % e < h // 100:
        return 1.0  # instant crash
    result = h / (e - random_int % e)
    return max(1.0, round(result, 2))
```

> [!CAUTION]
> The mobile application must **never** determine the crash point. Crash logic lives exclusively on the server.

---

## 10. Provably-Fair Style Design

### Before Round

1. Server generates `server_seed` (cryptographically secure).
2. Server publishes `SHA256(server_seed)` — the **commitment hash**.

### During Round

Server uses:

```
server_seed + round_id + optional client_seed
```

to derive a deterministic random value via HMAC-SHA256.

### After Round

Server reveals `server_seed`.

Any player can verify:

```python
import hashlib
assert hashlib.sha256(server_seed.encode()).hexdigest() == commitment_hash
```

This makes the virtual game result fully **auditable**.

---

## 11. Example Fairness Module

**File:** `backend/game/fairness.py`

**Responsibilities:**

```
generate_seed()            — cryptographically secure seed
hash_seed(seed)            — SHA256 commitment
generate_round_randomness(seed, round_id, client_seed)
calculate_crash_point(randomness)
verify_round(round_id)     — post-round audit
```

**Skeleton:**

```python
import hashlib
import hmac
import secrets


class FairnessEngine:

    def create_seed(self) -> str:
        """Generate a new cryptographically secure server seed."""
        return secrets.token_hex(32)

    def commit_seed(self, seed: str) -> str:
        """Return SHA256 commitment hash to publish before the round."""
        return hashlib.sha256(seed.encode()).hexdigest()

    def calculate_result(
        self, seed: str, round_id: str, client_seed: str = ""
    ) -> float:
        """Derive crash multiplier deterministically from seed + round_id."""
        message = f"{round_id}:{client_seed}".encode()
        digest = hmac.new(seed.encode(), message, hashlib.sha256).hexdigest()
        random_int = int(digest, 16)
        return self._to_crash_multiplier(random_int)

    def verify_result(self, seed: str, round_id: str, expected_hash: str) -> bool:
        """Confirm seed matches the published commitment hash."""
        return self.commit_seed(seed) == expected_hash

    def _to_crash_multiplier(self, random_int: int) -> float:
        e = 2**256
        house_edge = 0.01
        h = e - int(e * house_edge)
        if random_int % e < (h // 100):
            return 1.0
        result = h / (e - random_int % e)
        return max(1.0, round(result, 2))
```

---

## 12. Game State Machine

Use explicit, validated game states. Never allow invalid transitions.

```
WAITING
   |
BETTING
   |
RUNNING --------+
   |            |
CASHED_OUT   CRASHED
   |            |
ROUND_END ------+
```

```python
VALID_STATES = {
    "WAITING", "BETTING", "RUNNING",
    "CASHED_OUT", "CRASHED", "ROUND_END",
}

VALID_TRANSITIONS = {
    "WAITING":    {"BETTING"},
    "BETTING":    {"RUNNING"},
    "RUNNING":    {"CASHED_OUT", "CRASHED"},
    "CASHED_OUT": {"ROUND_END"},
    "CRASHED":    {"ROUND_END"},
    "ROUND_END":  {"WAITING"},
}
```

Raise an error on any attempted invalid transition.

---

## 13. Backend API

### Authentication

```http
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/refresh
```

### Player

```http
GET    /api/player/profile
GET    /api/player/balance
GET    /api/player/history
PATCH  /api/player/settings
```

### Game

```http
GET    /api/game/current
POST   /api/game/join
POST   /api/game/cashout
GET    /api/game/history
```

### Fairness

```http
GET    /api/fairness/{round_id}
GET    /api/fairness/{round_id}/verify
```

### Health

```http
GET    /api/health
GET    /api/health/detailed
```

### Admin (protected — requires admin JWT)

```http
POST   /api/admin/auth/login
POST   /api/admin/auth/logout

GET    /api/admin/dashboard
GET    /api/admin/users
GET    /api/admin/users/{user_id}
PATCH  /api/admin/users/{user_id}/status

GET    /api/admin/rounds
GET    /api/admin/rounds/{round_id}

GET    /api/admin/transactions
POST   /api/admin/wallet-adjustments

GET    /api/admin/audit-logs

GET    /api/admin/fairness/{round_id}

GET    /api/admin/system/health

GET    /api/admin/settings
PATCH  /api/admin/settings
```

---

## 14. WebSocket

**Endpoint:** `ws://host/ws/game`

The server broadcasts live game events to all connected clients.

### Multiplier Update

```json
{
  "type": "multiplier_update",
  "round_id": "AG-20261002-00123",
  "multiplier": 2.37,
  "elapsed_ms": 8420,
  "status": "running"
}
```

### Crash Event

```json
{
  "type": "crash",
  "round_id": "AG-20261002-00123",
  "crash_multiplier": 3.42,
  "status": "crashed",
  "server_seed_hash": "abc123..."
}
```

### Cash-Out Confirmation (private, per-player)

```json
{
  "type": "cashout",
  "round_id": "AG-20261002-00123",
  "multiplier": 2.81,
  "payout": 281,
  "new_balance": 10181
}
```

### Round Start

```json
{
  "type": "round_start",
  "round_id": "AG-20261002-00124",
  "server_seed_hash": "def456...",
  "start_timestamp": "2026-10-02T14:23:01Z"
}
```

### Heartbeat (server -> client, every 5s)

```json
{
  "type": "ping",
  "timestamp": 1727871781
}
```

---

## 15. Database Design

### `users`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| username | VARCHAR(50) UNIQUE | |
| email | VARCHAR(255) UNIQUE | nullable for guest |
| password_hash | TEXT | Argon2id |
| created_at | TIMESTAMPTZ | |
| last_login_at | TIMESTAMPTZ | |
| status | ENUM | active / suspended / banned |
| role | ENUM | player / admin / super_admin |

### `wallets`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK -> users | |
| balance | BIGINT | integer credits |
| updated_at | TIMESTAMPTZ | |

### `rounds`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| round_number | BIGINT UNIQUE | auto-increment |
| server_seed_hash | TEXT | published before round |
| server_seed | TEXT | revealed after round |
| client_seed | TEXT | optional player contribution |
| crash_multiplier | NUMERIC(10,2) | |
| started_at | TIMESTAMPTZ | |
| ended_at | TIMESTAMPTZ | |
| status | ENUM | waiting / running / crashed |

### `bets`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| round_id | UUID FK -> rounds | |
| user_id | UUID FK -> users | |
| amount | BIGINT | integer credits |
| cashout_multiplier | NUMERIC(10,2) | NULL if lost |
| payout | BIGINT | NULL if lost |
| status | ENUM | placed / cashed_out / lost |
| created_at | TIMESTAMPTZ | |

### `transactions`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK -> users | |
| type | ENUM | bet / payout / adjustment / bonus |
| amount | BIGINT | signed integer |
| balance_before | BIGINT | |
| balance_after | BIGINT | |
| reference_id | UUID | FK to bet or adjustment |
| created_at | TIMESTAMPTZ | |

### `game_settings`

| Column | Type | Default |
|---|---|---|
| id | INTEGER PK | 1 (singleton) |
| minimum_bet | BIGINT | 10 |
| maximum_bet | BIGINT | 10000 |
| starting_balance | BIGINT | 10000 |
| house_edge | NUMERIC(4,4) | 0.0100 |
| game_speed | NUMERIC(5,3) | 1.000 |
| animation_speed | NUMERIC(5,3) | 1.000 |
| betting_window_ms | INTEGER | 5000 |
| maintenance_mode | BOOLEAN | false |
| updated_at | TIMESTAMPTZ | |
| updated_by | UUID FK -> users | |

### `audit_logs`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| admin_user_id | UUID FK -> users | |
| action | VARCHAR(100) | e.g. USER_SUSPENDED |
| target_type | VARCHAR(50) | user / round / setting |
| target_id | UUID | |
| payload_json | JSONB | sanitized change data |
| ip_address | INET | |
| created_at | TIMESTAMPTZ | append-only |

---

## 16. Wallet Logic

Use **integer virtual credits** to avoid floating-point rounding errors.

```
Starting balance  =  10,000
Bet               =    -100
-------------------------------
After bet         =   9,900

Cash-out at 2.50x
Payout            =    +250
-------------------------------
Final balance     =  10,150
```

All balance changes must be processed **server-side** inside a database transaction.

> [!CAUTION]
> Never trust values sent by the client:
> - `client_balance`
> - `client_payout`
> - `client_multiplier`
> - `client_crash_point`

---

## 17. Anti-Cheat Architecture

**The client is untrusted.** Never calculate the final payout exclusively on the phone.

**Server validates on every cash-out request:**

```
Valid JWT / authenticated user
Round exists and belongs to this session
Bet exists for this user in this round
Round status == RUNNING
Server clock has not yet passed crash time
Bet status == PLACED (not already cashed out)
Payout calculation is server-side
Wallet update is within a DB transaction
Result is written to audit log
```

**Protection mechanisms:**

| Mechanism | Purpose |
|---|---|
| HTTPS | Encrypt all traffic |
| JWT bearer tokens | Authenticate every request |
| Request validation (Pydantic) | Reject malformed inputs |
| Rate limiting | Block flooding / brute-force |
| Server-side game state | Authoritative source of truth |
| Idempotency keys | Prevent duplicate cash-out |
| DB transactions + row locking | Prevent race conditions |
| Audit logs | Tamper evidence |

---

## 18. Python Project Structure

```
anti_gravity/
|
+-- app/                          # Kivy mobile frontend
|   +-- main.py                   # App entry point
|   +-- config.py                 # Environment-aware config
|   |
|   +-- screens/
|   |   +-- splash.py
|   |   +-- home.py
|   |   +-- game.py
|   |   +-- history.py
|   |   +-- profile.py
|   |   +-- settings.py
|   |   +-- tutorial.py
|   |
|   +-- widgets/
|   |   +-- spider.py             # Spider animation widget
|   |   +-- multiplier.py         # Live multiplier display
|   |   +-- cashout_button.py
|   |   +-- bet_panel.py
|   |   +-- history_list.py
|   |   +-- background.py         # Animated space background
|   |
|   +-- services/
|   |   +-- api.py                # REST client
|   |   +-- websocket.py          # WebSocket client
|   |   +-- auth.py               # Token storage + refresh
|   |   +-- wallet.py             # Local wallet state
|   |
|   +-- assets/
|   |   +-- images/
|   |   |   +-- spider/           # Spider sprite frames
|   |   |   +-- backgrounds/
|   |   +-- sounds/
|   |   |   +-- button_click.wav
|   |   |   +-- round_start.wav
|   |   |   +-- multiplier_tick.wav
|   |   |   +-- cashout.wav
|   |   |   +-- warning.wav
|   |   |   +-- crash.wav
|   |   |   +-- win.wav
|   |   +-- fonts/
|   |       +-- Orbitron-Regular.ttf
|   |
|   +-- kv/
|       +-- main.kv
|       +-- game.kv
|       +-- screens.kv
|       +-- widgets.kv
|
+-- admin/                        # Separate web admin dashboard
|   +-- frontend/
|   |   +-- index.html
|   |   +-- css/
|   |   +-- js/
|   |   +-- pages/
|   |       +-- dashboard/
|   |       +-- users/
|   |       +-- rounds/
|   |       +-- wallets/
|   |       +-- audit/
|   |       +-- fairness/
|   |       +-- settings/
|   |       +-- system/
|   +-- README.md
|
+-- backend/
|   +-- main.py                   # FastAPI app entry point
|   +-- config.py                 # Settings (pydantic-settings)
|   +-- database.py               # SQLAlchemy engine + session
|   |
|   +-- models/
|   |   +-- user.py
|   |   +-- wallet.py
|   |   +-- round.py
|   |   +-- bet.py
|   |   +-- transaction.py
|   |   +-- game_settings.py
|   |   +-- audit_log.py
|   |
|   +-- api/
|   |   +-- auth.py
|   |   +-- player.py
|   |   +-- game.py
|   |   +-- fairness.py
|   |   +-- health.py
|   |   +-- admin/
|   |       +-- auth.py
|   |       +-- dashboard.py
|   |       +-- users.py
|   |       +-- rounds.py
|   |       +-- transactions.py
|   |       +-- wallet_adjustments.py
|   |       +-- audit_logs.py
|   |       +-- fairness.py
|   |       +-- settings.py
|   |       +-- system.py
|   |
|   +-- game/
|   |   +-- engine.py             # Main game loop
|   |   +-- fairness.py           # FairnessEngine
|   |   +-- multiplier.py         # Multiplier function
|   |   +-- state.py              # GameStateMachine
|   |
|   +-- middleware/
|       +-- auth.py               # JWT validation
|       +-- rate_limit.py
|       +-- audit.py              # Auto-audit middleware
|
+-- tests/
|   +-- unit/
|   |   +-- test_game_engine.py
|   |   +-- test_fairness.py
|   |   +-- test_wallet.py
|   |   +-- test_multiplier.py
|   |   +-- test_state_machine.py
|   +-- integration/
|   |   +-- test_api_auth.py
|   |   +-- test_api_game.py
|   |   +-- test_websocket.py
|   |   +-- test_cashout_race.py
|   +-- stress/
|       +-- test_load.py
|
+-- .github/
|   +-- workflows/
|       +-- build_apk.yml         # GitHub Actions APK build
|
+-- requirements.txt
+-- requirements-dev.txt
+-- buildozer.spec
+-- .env.example
+-- README.md
+-- CHANGELOG.md
```

---

## 19. Kivy Application Screens

### Splash Screen

```
+------------------------------+
|                              |
|        ANTI-GRAVITY          |
|    A Spider Crash Adventure  |
|                              |
|           [spider]           |
|                              |
|          Loading...          |
|      [##########---]  60%    |
|                              |
+------------------------------+
```

### Home / Main Menu

```
Buttons:
  [ PLAY ]
  [ HISTORY ]
  [ PROFILE ]
  [ SETTINGS ]
  [ HOW TO PLAY ]
```

### Game Screen

Components (top to bottom):

```
Top bar        --> balance | round ID | connection status
Multiplier     --> large, animated numeric display
Spider canvas  --> animated spider + particle trail
Bet panel      --> preset amounts + custom input
Cash-out btn   --> large, prominent
Recent history --> scrolling multiplier chips at bottom
Status bar     --> WAITING / BETTING / RUNNING / CRASHED
```

### History Screen

```
Round #   Crash    Your Bet   Result
----------------------------------------
#1021     1.42x    100        LOST
#1022     4.18x    50         WON (2.11x)
#1023     1.09x    200        LOST
#1024     7.31x    --         --
```

### Profile Screen

```
Username:        spider_player_01
Member Since:    2026-10-01
Games Played:    142
Wins:            61
Losses:          81
Win Rate:        43%
Best Cash-out:   8.42x
Total Credits:   14,250
```

### Settings Screen

```
Audio
  Music           [ON / OFF]
  Sound Effects   [ON / OFF]
  Volume          [########--]  80%

Display
  Animations      [ON / OFF]
  Particle FX     [ON / OFF]

Responsible Play
  Session Timer   [ON / OFF]
  Break Reminder  [ON / OFF]

Account
  Change Password
  Logout
```

---

## 20. Spider Animation

Use a sprite sheet or a sequence of PNG frames.

**Animation states:**

| State | Trigger |
|---|---|
| `idle` | Waiting for round |
| `climbing` | Multiplier 1.0x – 3.0x |
| `fast_climbing` | Multiplier > 3.0x |
| `warning` | High multiplier zone |
| `falling` | Crash event received |
| `crashed` | Spider hit ground |

```python
class SpiderWidget(Widget):

    def update_state(self, multiplier: float, game_status: str) -> None:
        if game_status == "crashed":
            self.set_animation("falling")
        elif multiplier >= 5.0:
            self.set_animation("fast_climbing")
        elif multiplier >= 1.0:
            self.set_animation("climbing")
        else:
            self.set_animation("idle")

    def update_position(self, multiplier: float) -> None:
        self.y = self._calculate_height(multiplier)

    def _calculate_height(self, multiplier: float) -> float:
        max_height = self.parent.height * 0.85
        return min(max_height, (multiplier - 1.0) * 80)
```

> [!TIP]
> Drive animation from **server game time → multiplier → screen position**. Never tie animation to frame count — different devices run at different FPS.

---

## 21. Visual Design

### Primary Theme

Dark futuristic / deep space aesthetic.

### Color Palette

| Token | Value | Use |
|---|---|---|
| `--bg-primary` | `#050510` | Screen background |
| `--bg-surface` | `#0D0D2B` | Cards, panels |
| `--accent-purple` | `#7B2FFF` | Primary brand color |
| `--accent-cyan` | `#00F5FF` | Highlights, glows |
| `--text-primary` | `#FFFFFF` | Body text |
| `--text-muted` | `#8888AA` | Labels, subtitles |
| `--multiplier-green` | `#00FF88` | Live multiplier |
| `--crash-red` | `#FF2255` | Crash warning / state |
| `--win-gold` | `#FFD700` | Win result |

### Typography

- **Display / Multiplier:** Orbitron (Google Fonts) — futuristic, numeric
- **Body / UI:** Inter or Roboto
- **Monospace / Fairness:** JetBrains Mono

### Spider Design

Original futuristic cyber-spider:

```
Cyber Spider characteristics:
  - 8 glowing neon legs (animated)
  - Metallic / carbon-fiber body
  - Glowing purple/cyan eyes
  - Energy particle trail
  - Mechanical joint details
  - Crash state: sparks + fall animation
```

> [!WARNING]
> Do **not** copy Aviator's exact artwork, branding, logos, or proprietary assets. All Anti-Gravity visual assets must be original.

---

## 22. Game Background

**Environment:**

```
Deep space backdrop
Scrolling parallax star layers (3 depths)
Floating neon-grid platforms
Occasional distant moon / asteroid
Energy particle system
Gravity-distortion field lines
```

**At crash event:**

```
Screen shake          <- camera impulse
Spider falls          <- falling animation + gravity
Explosion particles   <- red + orange sparks
Multiplier freezes    <- number locks with red tint
Sound: crash.wav      <- plays immediately
Cooldown overlay      <- 3-second pause before next round
```

---

## 23. Sound System

**Sound files** (`app/assets/sounds/`):

| File | Trigger |
|---|---|
| `button_click.wav` | Any button press |
| `round_start.wav` | Betting window opens |
| `multiplier_tick.wav` | Each multiplier step (throttled) |
| `cashout.wav` | Successful cash-out |
| `warning.wav` | High multiplier zone (>5x) |
| `crash.wav` | Spider crashes |
| `win.wav` | Player wins |
| `ambient.ogg` | Background music loop |

**Settings:**

```
Music        ON / OFF
Sound FX     ON / OFF
Volume       0 – 100%
```

Use Kivy's `SoundLoader` for cross-platform audio. Lazy-load sounds to avoid startup delay.

---

## 24. Animation Timing

**Always use real elapsed time — never per-frame deltas.**

```python
import time

class GameLoop:

    def start(self):
        self.start_time = time.monotonic()

    def get_multiplier(self) -> float:
        elapsed = time.monotonic() - self.start_time
        return self.multiplier_function(elapsed)
```

> [!WARNING]
> Do **not** use `multiplier += 0.01` on every frame.  
> Different devices run at different frame rates (30 FPS vs 60 FPS vs 120 FPS). Time-based animation keeps all clients visually synchronized.

---

## 25. Crash Synchronization

```
Server side:
  Round starts
       |
  Server records precise UTC start timestamp
       |
  Server broadcasts round_start + start_timestamp
       |
  Client receives round info
       |
  Client interpolates display from (now - start_timestamp)
       |
  Server declares CRASHED
       |
  Client accepts crash -- cannot extend round
```

The client must never be able to extend a round after the server broadcasts `CRASHED`. Any client-side cash-out request received after the crash timestamp is rejected server-side regardless of network delay.

---

## 26. Cash-Out Race Handling

This is a **critical correctness requirement**.

**Scenario:**

```
Server crash time  =  2.50x
Client cash-out    =  2.52x  (sent 40ms late)
```

The server determines the valid result using its authoritative game clock.

**Transactional cash-out pseudocode:**

```sql
BEGIN TRANSACTION;

  SELECT * FROM rounds WHERE id = :round_id FOR UPDATE;
  -- row-level lock prevents concurrent cash-outs

  IF round.status != 'RUNNING' THEN
    ROLLBACK; RETURN error("Round not active");
  END IF;

  IF NOW() >= round.crash_time THEN
    ROLLBACK; RETURN error("Crash already occurred");
  END IF;

  SELECT * FROM bets WHERE id = :bet_id FOR UPDATE;

  IF bet.status != 'PLACED' THEN
    ROLLBACK; RETURN error("Bet already settled");
  END IF;

  -- calculate authoritative payout
  current_multiplier = calculate_multiplier(NOW() - round.started_at);
  payout = bet.amount * current_multiplier;

  UPDATE bets SET status='CASHED_OUT', cashout_multiplier=current_multiplier, payout=payout;
  UPDATE wallets SET balance = balance + payout WHERE user_id = :user_id;
  INSERT INTO transactions (...);

COMMIT;
```

This prevents double cash-outs and race-condition exploits.

---

## 27. Authentication

### MVP (V0.7)

```
Username + Password
Password hashed with Argon2id
JWT access token (short-lived: 15 min)
Refresh token (longer-lived: 7 days)
```

### Production Hardening

```
JWT access token + refresh token rotation
Device fingerprinting
Session management
Concurrent session limits
Suspicious login detection
```

**Password storage:**

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

> [!CAUTION]
> Never store plaintext passwords. Never log passwords or tokens.

---

## 28. Local Development Mode

Before building the server, enable `DEMO_MODE`:

```python
# app/config.py
DEMO_MODE = True  # set False to use real FastAPI backend
```

**Demo Mode flow:**

```
Kivy App
   |
Local Python Game Engine  (backend/game/engine.py)
   |
SQLite (anti_gravity_dev.db)
```

This allows full UI development and testing without a running server.

---

## 29. Production Mode

```
Android APK
     |
   HTTPS
     |
FastAPI on cloud server (Uvicorn + Gunicorn)
     |
PostgreSQL (managed cloud DB)
     |
Redis (optional -- for WebSocket pub/sub scaling)
```

Game engine runs **only** on the backend.

---

## 31. Analytics

Track (server-side, privacy-respecting):

```
DAU / MAU
Games played per day
Average session duration
Average rounds per session
Average virtual credits wagered
Cash-out multiplier distribution
Crash multiplier distribution
Win rate distribution
App crash rate (client-side error reports)
API latency percentiles (p50, p95, p99)
WebSocket disconnect rate
```

> [!NOTE]
> Do not collect unnecessary personal information. Analytics must be compliant with applicable privacy regulations even for a virtual game.

---

## 32. Responsible Game Design

Because crash mechanics can encourage repetitive play, implement:

```
Session timer          -- shows how long player has been playing
Break reminder         -- prompts a break after N minutes
Daily play statistics  -- credits wagered, won, lost today
Virtual-credit economy -- no real money at risk
```

**Prohibited mechanics:**

- Secretly adjusting outcomes based on a player's balance or behavior
- Hiding session duration from the player
- Loot-box-style disguised monetization

---

## 33. Testing Strategy

### Unit Tests

Test in isolation:

```
Multiplier calculation at various elapsed times
Crash point derivation from random seed
FairnessEngine.verify_result() correctness
Wallet integer arithmetic (bet / payout / adjustment)
Cash-out validation logic
State machine transition rules
```

### Integration Tests

Test component interactions:

```
App --> REST API (auth, game join, cash-out)
API --> Database (round creation, bet recording, wallet update)
WebSocket --> Client (multiplier stream, crash event, reconnect)
Full round lifecycle: join --> bet --> cash-out --> balance update
```

### Stress / Load Tests

Simulate concurrent users:

```
100 concurrent users   -- baseline
500 concurrent users   -- target MVP capacity
1,000 concurrent users -- stretch goal
```

Measure:

```
CPU utilization
RAM usage
Database query latency
WebSocket message latency
Cash-out success rate under load
```

---

## 34. Security Tests

Every failure scenario must be **rejected server-side**:

| Attack | Expected Result |
|---|---|
| Duplicate cash-out | 409 Conflict |
| Replay request (old JWT) | 401 Unauthorized |
| Invalid round ID | 404 Not Found |
| Invalid user ID | 403 Forbidden |
| Modified multiplier in body | Ignored — server uses authoritative value |
| Modified payout in body | Ignored — server calculates payout |
| Negative bet amount | 422 Unprocessable Entity |
| Bet > maximum_bet | 422 Unprocessable Entity |
| Expired JWT | 401 Unauthorized |
| Unauthorized admin endpoint | 403 Forbidden |
| SQL injection in input | 422 / sanitized by Pydantic |
| WebSocket message flood | Rate-limited + disconnected |

---

## 35. Offline Handling

When the network disconnects during a round:

```
UI overlay:
  WARNING: DISCONNECTED
  Reconnecting... (attempt 3/5)
```

**Rules:**

- Do **not** assume the player successfully cashed out.
- The server's stored state remains authoritative.
- Client must not update wallet balance until server confirms.

**On reconnection:**

```python
async def on_reconnect():
    round_data = await api.get_current_round()
    balance    = await api.get_balance()
    last_tx    = await api.get_latest_transaction()
    sync_ui(round_data, balance, last_tx)
```

**Reconnect backoff strategy:**

```
Attempt 1 --> wait 1s
Attempt 2 --> wait 2s
Attempt 3 --> wait 4s
Attempt 4 --> wait 8s
Attempt 5 --> wait 16s --> show "Check your connection" message
```

---

## 36. Error Handling

Show **user-friendly** messages on the UI:

| Technical Error | User Message |
|---|---|
| `WebSocketException` | "Connection lost. Trying to reconnect..." |
| `HTTPError 503` | "Server is temporarily unavailable." |
| `HTTPError 401` | "Session expired. Please log in again." |
| `TimeoutError` | "Request timed out. Please try again." |

Log technical details (stack traces, error codes) **separately** in the backend log — never shown to the player.

---

## 37. Logging

**Backend log levels:**

| Level | Use |
|---|---|
| `INFO` | Normal operations, round start/end |
| `WARNING` | Unexpected but recoverable events |
| `ERROR` | Exceptions, failed DB transactions |
| `SECURITY` | Auth failures, rate limit hits, suspicious requests |
| `AUDIT` | All sensitive admin actions (separate audit_logs table) |

**Never log:**

```
password (plain or hashed)
JWT signing secret
Database connection string
Server seed (before round end)
Private tokens / session keys
```

---

## 38. API Security

**Mandatory for all API endpoints:**

```
HTTPS               -- all production traffic
JWT bearer tokens   -- authenticate every request
Rate limiting       -- per IP + per user
Input validation    -- Pydantic v2 strict mode
CORS configuration  -- whitelist known origins only
Secure headers      -- HSTS, X-Frame-Options, CSP
Request IDs         -- UUID per request for tracing
Audit logs          -- sensitive operations logged
```

**Development:**

```
http://localhost:8000
ws://localhost:8000/ws/game
```

**Production:**

```
https://api.antigravity.yourdomain.com
wss://api.antigravity.yourdomain.com/ws/game
```

Use your actual registered domain. Do not hard-code example domains.

---

## 39. Windows + Physical Android Phone Workflow

The developer works on a **Windows laptop** and uses a **physical Android phone** as the primary Android test device.

### Windows Setup

Required tools:

| Tool | Purpose |
|---|---|
| Python 3.11+ | Frontend + backend development |
| Git | Version control |
| Antigravity IDE | Primary development environment |
| Android Studio | SDK Manager + Logcat |
| Android SDK Platform-Tools | ADB |

Android Studio provides the SDK/Platform-Tools and Logcat support. The Anti-Gravity application remains Python/Kivy/KivyMD and is **not** rewritten as Kotlin/Java.

### Phone Debugging

On the phone:

```
Settings --> Developer Options --> ON
USB Debugging                  --> ON
USB connection mode            --> File Transfer (MTP)
```

Verify device is detected:

```powershell
adb devices
```

Expected output:

```
List of devices attached
<device-id>    device
```

Install a debug APK:

```powershell
adb -s <device-id> install "path\to\anti-gravity-debug.apk"
```

View live logs:

```powershell
adb -s <device-id> logcat | Select-String "python"
```

### Local FastAPI Testing (Phone to Laptop)

**Key rule:** Android's `localhost` / `127.0.0.1` refers to the **phone itself**, not the laptop.

Setup:

1. Connect phone and laptop to the same trusted Wi-Fi network.
2. Run FastAPI: `uvicorn main:app --host 0.0.0.0 --port 8000`
3. Find laptop's LAN IP: run `ipconfig` in PowerShell, look for **IPv4 Address**
4. Configure the Android app to use the laptop's LAN IP.

```python
# app/config.py
import os

if os.getenv("ANDROID_ARGUMENT"):
    # Running on Android -- use LAN IP
    API_BASE_URL = os.getenv("API_BASE_URL", "http://192.168.x.x:8000")
else:
    # Running on Windows dev machine
    API_BASE_URL = "http://localhost:8000"
```

Verify connectivity:

```
http://<laptop-LAN-IP>:8000/api/health
```

> [!WARNING]
> Do not expose the development FastAPI server to the public internet. Only use it on a trusted private LAN.

### APK Build (No Ubuntu / WSL2 Required)

```
Windows Laptop
      |
      v
GitHub (push code)
      |
      v
GitHub Actions Linux Runner
      |
      v
Buildozer + python-for-android
      |
      v
Debug APK artifact
      |
      v
Download to Windows
      |
      v
ADB install to physical phone
```

---

## 40. Build Process

### Local Development Testing

```
Python 3.11+
   |
Kivy (desktop mode)
   |
python app/main.py
```

### Android APK (via GitHub Actions)

```
python app/main.py  <-- test locally first
   |
git push origin main
   |
GitHub Actions runner (Ubuntu)
   |
pip install buildozer
   |
buildozer android debug
   |
Download APK artifact from Actions
   |
adb install anti-gravity-debug.apk
```

### Buildozer Commands Reference

```bash
# Initialize spec file (first time only)
buildozer init

# Debug build (via GitHub Actions)
buildozer android debug

# Release build (requires signing key)
buildozer android release
```

> [!IMPORTANT]
> A **release APK/AAB** must be signed with your own keystore file. Never commit the keystore to Git. Use GitHub Actions secrets to supply it during the release build.

---

## 41. Buildozer Configuration

**`buildozer.spec` key settings:**

```ini
[app]
title = Anti-Gravity
package.name = antigravity
package.domain = com.yourstudio.antigravity

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,gif,wav,mp3,ogg,json,ttf

version = 0.1.0

requirements = python3==3.11,kivy==2.3.0,kivymd==1.2.0,requests,websocket-client,argon2-cffi

orientation = portrait
fullscreen = 0

android.minapi = 24
android.targetapi = 34
android.ndk = 25b
android.sdk = 34

android.permissions = INTERNET,VIBRATE

[buildozer]
log_level = 2
```

> [!NOTE]
> Lock exact dependency versions **after** a successful test build. Avoid floating versions in `buildozer.spec` for production.

---

## 42. CI/CD Pipeline — GitHub Actions

**File:** `.github/workflows/build_apk.yml`

```yaml
name: Build Android APK

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  build-apk:
    runs-on: ubuntu-22.04

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            git zip unzip openjdk-17-jdk \
            libffi-dev libssl-dev libsdl2-dev \
            libsdl2-image-dev libsdl2-mixer-dev \
            libsdl2-ttf-dev libportmidi-dev \
            libswscale-dev libavformat-dev libavcodec-dev

      - name: Install Buildozer
        run: pip install buildozer cython

      - name: Build Debug APK
        run: buildozer android debug

      - name: Upload APK artifact
        uses: actions/upload-artifact@v4
        with:
          name: anti-gravity-debug-apk
          path: bin/*.apk
          retention-days: 14
```

---

## 43. Antigravity Development Workflow

Use Antigravity as the primary development assistant for all phases.

### Phase 1 — Project Structure

```
Create the Anti-Gravity Python/Kivy project structure per Section 18.
```

### Phase 2 — Kivy UI

```
Implement: main menu, splash, game screen, multiplier widget,
spider animation widget, virtual wallet display.
```

### Phase 3 — Local Game Engine

```
Implement: FastAPI backend skeleton, SQLite database,
FairnessEngine, GameStateMachine, multiplier function,
Demo Mode for local testing.
```

### Phase 4 — Backend Integration

```
Implement: REST endpoints, WebSocket server,
server-authoritative game loop, cash-out validation.
```

### Phase 5 — Fairness + History

```
Implement: seed commitment, HMAC derivation, crash generation,
fairness verification API, round history, profile, settings.
```

### Phase 6 — Security Hardening

```
Implement: Argon2id passwords, JWT, rate limiting,
input validation, CORS, secure headers, audit sanitization.
```

### Phase 7 — Admin Panel

```
Implement: admin auth + RBAC, dashboard, user management,
wallet adjustments, round monitoring, audit logs, system health.
```

### Phase 8 — Android Build

```
Configure buildozer.spec, set up GitHub Actions workflow,
build debug APK, install via ADB, test on physical phone.
```

---

## 44. Recommended Development Order

Run the **full test suite** after every sprint. Test Android-specific changes on the physical phone after Sprint 8.

### Sprint 1 — Python / Kivy UI Foundation

```
Splash screen
Home / main menu
Game screen (static, no logic)
History screen
Profile screen
Settings screen
Tutorial / How to Play screen
```

### Sprint 2 — Local Virtual Game

```
Multiplier calculation (local)
Spider animation (local)
Crash generation (local, using FairnessEngine)
Cash-out button logic
Virtual wallet (local SQLite)
Local GameStateMachine
Demo Mode working end-to-end
```

### Sprint 3 — Python FastAPI Backend

```
FastAPI project structure
SQLite via SQLAlchemy
User registration + login (Argon2id + JWT)
Player API endpoints
Game API endpoints
Wallet API endpoints
Database migrations (Alembic)
```

### Sprint 4 — Real-Time Gameplay

```
WebSocket server (/ws/game)
Server-authoritative game loop
Live multiplier broadcast
Crash event broadcast
Cash-out validation (transactional)
Kivy WebSocket client connected to backend
```

### Sprint 5 — Fairness and Audit

```
FairnessEngine (seed, hash, HMAC derivation)
Crash point generation using FairnessEngine
Fairness verification API
Round history stored with seed data
Audit log table + writes
```

### Sprint 6 — Security

```
JWT access + refresh token rotation
Rate limiting (slowapi or custom middleware)
Input validation hardening
Authorization checks on all endpoints
Database transaction safety review
Security headers middleware
Audit log sanitization (no secrets logged)
```

### Sprint 7 — Performance and Stability

```
Database query optimization (indexes)
WebSocket connection pool management
Memory / resource cleanup in game loop
Game loop stability under sustained load
Load test (pytest-asyncio + locust)
API latency profiling
Android-side performance review (FPS, memory)
```

### Sprint 8 — Android Compatibility and Debug APK

```
Environment-aware config (demo vs. real backend)
LAN IP configuration for physical phone testing
buildozer.spec configuration and dependency lock
GitHub Actions APK build workflow
Debug APK built and downloaded
ADB install to physical phone
Logcat debugging session
Real-device test coverage
```

### Sprint 9 — Admin Panel

```
Admin authentication + JWT
RBAC middleware
Admin dashboard (live metrics)
User management CRUD
Wallet adjustment with audit
Round monitoring
Game settings management
Fairness verification UI
Audit log viewer (read-only)
System health display
Maintenance mode
Admin API integration tests
Admin UI tests
```

> [!IMPORTANT]
> The Admin Panel must **never** bypass server-authoritative game outcomes.

### Sprint 10 — Final Release

```
Production environment configuration
PostgreSQL migration from SQLite
Production API / WebSocket URLs
Android signing keystore setup
Release APK / AAB build
Final security review
Final regression test suite
Production deployment (cloud server)
Monitoring + alerting setup
Backup and recovery procedures
```

---

## 45. MVP Acceptance Criteria

The MVP is complete when **all** of the following pass:

**App Lifecycle**
- [ ] App launches on Android without crashing.
- [ ] Splash screen loads and transitions to home screen.

**Account**
- [ ] User can register a new account.
- [ ] User can log in to an existing account.
- [ ] User receives starting virtual-credit balance.

**Game Flow**
- [ ] User can select a virtual bet amount.
- [ ] A round starts with server-generated round ID and seed hash.
- [ ] Multiplier increases smoothly and continuously.
- [ ] Spider animation follows the multiplier value.
- [ ] Crash occurs at the server-generated crash point.
- [ ] Cash-out works correctly before the crash.
- [ ] Cash-out after crash is **rejected** by the server.
- [ ] Wallet updates exactly **once** per settled bet.

**Data**
- [ ] Round history is stored and displayed.
- [ ] Fairness verification returns correct result for past rounds.

**Network**
- [ ] Reconnection after disconnect works correctly.
- [ ] Invalid / malformed API requests are rejected.

**Android**
- [ ] APK installs on physical Android test phone via ADB.
- [ ] Game works on multiple Android screen sizes.
- [ ] Android app connects to development FastAPI server over LAN.
- [ ] ADB and Logcat successfully diagnose Android runtime issues.

**Admin Panel**
- [ ] Admin login and RBAC work correctly.
- [ ] All admin actions generate audit log entries.
- [ ] Admin Panel **cannot** alter an individual authoritative game outcome.

---

## 46. Suggested First Version

Keep Version 1 (V0.1) simple. Do not add features until core loop is solid:

```
+----------------------------------+
|         ANTI-GRAVITY             |
|                                  |
|       [ PLAY ]                   |
|                                  |
| Virtual Balance: 10,000          |
|                                  |
| Bet:  [ - ]  100  [ + ]         |
|                                  |
|         1.00x                    |
|          [spider]                |
|                                  |
|       [ CASH OUT ]               |
|                                  |
| Recent: 1.24x | 2.11x | 5.31x   |
+----------------------------------+
```

---

## 47. Version Roadmap

| Version | Milestone |
|---|---|
| **V0.1** | UI prototype (Kivy screens, no logic) |
| **V0.2** | Local game engine (demo mode) |
| **V0.3** | Virtual wallet (local SQLite) |
| **V0.4** | FastAPI backend + authentication |
| **V0.5** | WebSocket real-time synchronization |
| **V0.6** | Fairness verification system |
| **V0.7** | Authentication hardening (JWT + Argon2id) |
| **V0.8** | Admin dashboard (RBAC + audit) |
| **V0.9** | Testing + performance optimization |
| **V1.0** | Production-ready virtual-credit APK |

---

## 48. Final Architecture

```
         +-------------------------------+
         |        ANDROID APK           |
         |      KIVY / KIVYMD           |
         +----------+--------------------+
                    |
         +----------+---------+
         |                    |
      REST API            WebSocket
         |                    |
         +----------+---------+
                    |
         +----------+--------------------+
         |          FASTAPI              |
         +---------+---------+----------+
                   |         |
           GAME ENGINE   AUTH SYSTEM
           FairnessEngine   JWT + Argon2id
           StateMachine     RBAC
           MultiplierEngine
                   |         |
                   +---------+
                       |
         +-------------+------------------+
         |           DATABASE             |
         |   SQLite (dev)                 |
         |   PostgreSQL (prod)            |
         +--------------------------------+
```

**Game engine flow:**

```
Secure random seed
       |
SHA256 commitment hash  (published pre-round)
       |
HMAC-SHA256 round randomness
       |
Crash point calculation
       |
Multiplier timeline (server authoritative)
       |
Server game state --> broadcast via WebSocket
       |
Cash-out validation (transactional DB)
       |
Wallet transaction
       |
Round history + seed reveal
```

---

## 49. Antigravity Build Prompt

Use the following as the initial implementation prompt in Antigravity:

```
Build a complete Python/Kivy Android application called "Anti-Gravity".

It is a virtual-credit crash arcade game inspired by the general crash-game mechanic.

The visual theme is a futuristic cyber spider climbing upward through a deep-space environment.

Requirements:

1.  Python + Kivy/KivyMD frontend.
2.  FastAPI Python backend.
3.  SQLite for development (Demo Mode).
4.  PostgreSQL-ready architecture.
5.  WebSocket real-time game updates (/ws/game).
6.  Server-authoritative game engine (multiplier, crash, payout).
7.  Virtual-credit wallet only -- no real money.
8.  No deposits, withdrawals, cryptocurrency, or real-money gambling.
9.  Multiplier starts at 1.00x and continuously increases.
10. A server-generated crash point ends each round.
11. Player can cash out before the crash.
12. Server validates every cash-out inside a database transaction.
13. Use database transactions and row locking for wallet changes.
14. Implement a cryptographically secure, auditable FairnessEngine (HMAC-SHA256).
15. Store round history with seed reveal post-round.
16. Add user authentication (Argon2id passwords, JWT tokens).
17. Add profile screen with stats.
18. Add settings screen (audio, display, responsible play).
19. Add sound effects using Kivy SoundLoader.
20. Add futuristic spider animation driven by server multiplier.
21. Add reconnect handling with exponential backoff.
22. Add comprehensive unit and integration tests.
23. Create a clean modular project structure per the spec.
24. Prepare the project for Android APK generation using Buildozer.
25. Never trust client-side multiplier, balance, payout, or crash state.
26. Add clear comments and docstrings throughout.
27. Make the UI responsive for Android phones (portrait, multiple screen sizes).
28. Use original Anti-Gravity visual assets -- do not copy Aviator assets.
29. Use Python for both the Android frontend and FastAPI backend.
30. The primary developer machine is Windows.
31. Use Antigravity IDE as the primary development environment.
32. Prepare the Android app for physical-phone debugging using ADB.
33. Prepare GitHub Actions + Buildozer workflow for APK builds
    (Ubuntu/WSL2 not required on Windows laptop).
34. Build a separate authenticated web Admin Panel with RBAC and
    protected FastAPI admin APIs.
35. Give authorized administrators operational control over users,
    virtual credits, game settings, maintenance mode, audits,
    fairness verification, and system health.
36. Never give the Admin Panel any mechanism to alter an individual
    authoritative round result.
37. Audit all sensitive administrative actions in an append-only table.

Implementation order:
  1. Project structure (Section 18 of the plan)
  2. Kivy UI (Sprint 1)
  3. Local game engine + Demo Mode (Sprint 2)
  4. FastAPI backend (Sprint 3)
  5. WebSocket + server game loop (Sprint 4)
  6. Fairness verification (Sprint 5)
  7. Security hardening (Sprint 6)
  8. Admin Panel (Sprint 9)
  9. Tests (throughout each sprint)
  10. buildozer.spec + GitHub Actions APK build (Sprint 8)

Do not skip testing between stages.
```

---


## 50. Production Online-Only & Security Hardening

### 50.1 Untrusted Client

Assume the Android APK can be:

- Decompiled.
- Modified.
- Instrumented.
- Debugged.
- Repackaged.
- Reverse engineered.

Never trust client values for:

```text
client_balance
client_payout
client_multiplier
client_crash_point
client_game_state
client_cashout_result
```

The server independently validates every authoritative operation.

### 50.2 Player Authentication

Production authentication must implement:

- Argon2id password hashing.
- Short-lived access JWTs.
- Refresh-token rotation.
- Refresh-token revocation.
- Session management.
- Device/session tracking.
- Concurrent-session limits.
- Login rate limiting.
- Brute-force protection.
- Failed-login detection.
- Temporary account lockout.
- Secure password reset.
- Expiring reset tokens.
- Logout/session invalidation.
- Suspicious-login detection.

Never store or log plaintext passwords or authentication secrets.

### 50.3 Android Secure Token Storage

Do not store access or refresh tokens in ordinary plaintext files, logs, or an unprotected database.

Use Android secure storage backed by Android Keystore where supported by the Python/Kivy implementation.

### 50.4 Production API Security

Mandatory:

- HTTPS.
- TLS.
- HSTS.
- Secure headers.
- Strict CORS allowlist.
- CSP where applicable.
- Clickjacking protection.
- Request IDs.
- Strict Pydantic validation.
- Rate limiting.
- Authentication.
- Authorization.
- Audit logging for sensitive operations.
- Request-size limits.
- Timeouts.
- Safe error responses.

### 50.5 WebSocket Security

Production must use:

```text
wss://
```

WebSocket connections must:

- Authenticate before protected access.
- Validate every incoming message.
- Apply message-rate limits.
- Apply connection limits.
- Use heartbeat/ping.
- Disconnect abusive sessions.
- Resynchronize after reconnect.
- Never modify authoritative game state from the client.

### 50.6 Database Security

Production PostgreSQL must be private and reachable only by authorized backend services.

Use:

- Least-privilege credentials.
- Encrypted DB connections where supported.
- Parameterized queries / ORM protections.
- Connection pooling.
- Migrations.
- Automated backups.
- Tested recovery.

Never expose PostgreSQL directly to Android.

### 50.7 Secrets Management

Never hard-code or commit:

- JWT signing secrets.
- Database passwords.
- Production credentials.
- Encryption keys.
- API private keys.
- Active server seeds.

Use environment variables and/or production secrets management.

Never place production secrets in the APK or frontend JavaScript.

### 50.8 Security Testing

Test and reject:

- Expired JWT.
- Invalid JWT.
- Revoked token.
- Refresh-token replay.
- Brute-force login.
- Rate-limit abuse.
- Unauthorized API access.
- Manipulated payout.
- Manipulated multiplier.
- Manipulated wallet.
- Modified round ID.
- Invalid WebSocket authentication.
- WebSocket flooding.
- SQL injection attempts.
- Malformed JSON.
- Oversized requests.
- Unauthorized wallet adjustment.
- Unauthorized settings modification.
- Attempt to alter crash result.
- Attempt to access another user's data.

## 51. App Definition of Done

### Core App

- [ ] Python project is modular and clean.
- [ ] Kivy/KivyMD UI complete.
- [ ] Splash complete.
- [ ] Home complete.
- [ ] Game screen complete.
- [ ] History complete.
- [ ] Profile complete.
- [ ] Settings complete.
- [ ] Tutorial complete.
- [ ] Spider animation states complete.
- [ ] Sound system complete.
- [ ] Responsive Android layouts complete.

### Backend

- [ ] FastAPI production server works.
- [ ] PostgreSQL production support works.
- [ ] REST API works.
- [ ] WebSocket works.
- [ ] Authentication works.
- [ ] Authorization works.
- [ ] Game engine is server-authoritative.
- [ ] Fairness engine works.
- [ ] Wallet is server-authoritative.
- [ ] Cash-out is transactional and race-safe.
- [ ] Audit/security logging works.
- [ ] Rate limiting works.
- [ ] Security headers work.
- [ ] Production uses HTTPS/WSS.

### Android

- [ ] Debug APK builds.
- [ ] Release APK/AAB builds.
- [ ] Release artifact is signed.
- [ ] APK installs on physical Android phone via ADB.
- [ ] LAN development connection works.
- [ ] Production HTTPS/WSS connection works.
- [ ] Logcat debugging works.
- [ ] Reconnection works.
- [ ] No silent offline gameplay exists in production.

### Quality

- [ ] Unit tests pass.
- [ ] Integration tests pass.
- [ ] WebSocket tests pass.
- [ ] Cash-out race tests pass.
- [ ] Security tests pass.
- [ ] Load tests pass at the defined target.
- [ ] Backup/recovery is tested.

## 52. Current Operating Plan

The following choices are fixed unless explicitly changed:

| Decision | Choice |
|---|---|
| Developer Laptop | Windows |
| IDE | Antigravity |
| Frontend | Python + Kivy + KivyMD |
| Backend | Python + FastAPI |
| Dev Database | SQLite |
| Production Database | PostgreSQL |
| Android Test Device | Physical Android phone |
| Debugging | ADB + Android Studio Logcat |
| APK Build | GitHub Actions + Buildozer |
| Production Networking | HTTPS + WSS |
| Production Mode | Online-only |
| Game Authority | Server |
| Economy | Virtual credits only |
| Admin | Separate web application |

### Core Principle

> **The phone displays the game. The server controls the game.**

Never allow the Android client to decide:

```text
Crash point
Payout amount
Wallet balance
Cash-out success/failure
Round result
```

### Development Order

1. Kivy UI foundation.
2. Local Demo Mode.
3. FastAPI backend.
4. Real-time WebSocket gameplay.
5. Fairness and audit.
6. Authentication/security hardening.
7. Performance/stability.
8. Android compatibility and APK.
9. Admin Panel integration.
10. Production deployment.
11. Final security review.
12. Release APK/AAB.

