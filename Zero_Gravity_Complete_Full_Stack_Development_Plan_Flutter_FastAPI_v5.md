# Zero Gravity — Complete Full-Stack Development Plan
## Flutter Android Frontend + FastAPI Backend + Admin Panel + Database + Security + Deployment

> **Document version:** 5.0  
> **Last updated:** 2026-10-07  
> **Status:** Active — single source of truth  
> **Project:** Zero Gravity  
> **Developer environment:** Antigravity IDE on Windows  
> **Player platform:** Android first  
> **Player frontend:** Flutter + Dart  
> **Backend:** Python + FastAPI  
> **Database:** SQLite for development, PostgreSQL for production  
> **Admin:** Separate authenticated web application using protected FastAPI Admin APIs  
> **Game model:** Virtual credits only  
> **Architecture principle:** The phone displays the game; the server controls the game.

---

# 0. Purpose of This Document

This is the **single consolidated development plan** for Zero Gravity.

Frontend and backend are planned together in this one document so that implementation does not drift between separate specifications.

It covers:

- Flutter Android player application
- FastAPI backend
- REST API
- WebSocket real-time game synchronization
- Server-authoritative game engine
- Multiplier engine
- Crash-point generation
- Fairness / verification system
- Authentication
- Virtual-credit wallet
- Cash-out race protection
- PostgreSQL production database
- SQLite development database
- Anti-cheat
- Reconnection
- Error handling
- Security
- Admin Panel
- RBAC
- Audit logging
- Analytics
- Testing
- Windows development
- Physical Android phone testing
- ADB / Logcat
- Flutter Android build
- GitHub Actions CI/CD
- Production deployment
- Monitoring
- Backup and recovery
- Sprint-by-sprint implementation order
- Final acceptance criteria
- Antigravity implementation prompt

The old Python/Kivy mobile plan is **replaced** by Flutter + Dart. The FastAPI backend architecture remains the authoritative backend design.

---

# 1. Product Overview

## 1.1 App

**Name:** Zero Gravity

## 1.2 Genre

Crash / multiplier arcade game.

## 1.3 Visual concept

Instead of an airplane, a futuristic **cyber spider** climbs upward through a deep-space / neon environment.

Example multiplier progression:

```text
1.00x → 1.05x → 1.20x → 1.50x → 2.00x → 5.00x → 10.00x
```

At an unpredictable server-determined point, the spider crashes.

The player may cash out before the crash.

Example:

```text
Bet = 100 virtual credits
Cash-out = 2.35x

Payout = 100 × 2.35
       = 235 virtual credits
```

If the server declares the crash before a valid cash-out:

```text
Bet = 100
Result = LOST
Payout = 0
```

---

# 2. Absolute Product Boundary

Zero Gravity V1 is a **free-to-play virtual-credit game**.

The system must NOT implement:

- Real-money deposits
- Real-money withdrawals
- Cash prizes
- Cryptocurrency wagering
- Payment-based betting
- Real-money wallet
- Automated real-money betting

All balances are virtual credits.

Use integer credits in the backend to avoid floating-point wallet errors.

Example:

```text
10,000 credits
100 credits bet
9,900 credits remaining

Cash-out at 2.50x
250-credit payout
10,150 credits final balance
```

---

# 3. Core Architecture

## 3.1 High-level architecture

```text
                         ZERO GRAVITY
                              |
              +---------------+----------------+
              |                                |
       Flutter Android App              Admin Web App
              |                                |
         HTTPS / WSS                      HTTPS
              |                                |
              +---------------+----------------+
                              |
                       FastAPI Backend
                              |
        +---------------------+----------------------+
        |            |             |                 |
   Auth System   Game Engine   Fairness Engine   Admin APIs
        |            |             |                 |
        +------------+-------------+-----------------+
                              |
                         PostgreSQL
                       (production)
                              |
                     SQLite (development)
```

## 3.2 Critical authority rule

The Flutter application is an **untrusted client**.

Flutter must never be authoritative for:

```text
Crash point
Multiplier result
Payout
Wallet balance
Cash-out success
Round result
Transaction settlement
Fairness seed
```

The server is authoritative.

---

# 4. Technology Stack

## 4.1 Player frontend

```text
Flutter
Dart
Android
Material / custom cyber UI
HTTP REST client
WebSocket client
Secure token storage
```

Recommended packages:

```text
http
web_socket_channel
flutter_secure_storage
provider
audioplayers
```

Versions should be pinned after the first successful build and regression test.

Do not add packages unnecessarily.

## 4.2 Backend

```text
Python 3.11+
FastAPI
Uvicorn
Pydantic v2
SQLAlchemy 2.x
Alembic
PostgreSQL
SQLite
Argon2id
JWT
HMAC-SHA256
```

## 4.3 Development

```text
Windows
Antigravity IDE
Git
GitHub
Android Studio
Android SDK
ADB
Android Logcat
Flutter SDK
Python
```

## 4.4 Production

```text
HTTPS
WSS
FastAPI
Uvicorn
PostgreSQL
Reverse proxy
TLS certificate
Firewall
Monitoring
Backups
```

---

# 5. Complete Repository Structure

The entire project should be maintained as one repository.

```text
zero_gravity/
│
├── mobile/
│   ├── android/
│   ├── ios/                         # optional future
│   ├── lib/
│   │   ├── main.dart
│   │   ├── app.dart
│   │   │
│   │   ├── config/
│   │   │   └── app_config.dart
│   │   │
│   │   ├── core/
│   │   │   ├── auth/
│   │   │   │   ├── auth_service.dart
│   │   │   │   └── token_storage.dart
│   │   │   ├── networking/
│   │   │   │   ├── api_client.dart
│   │   │   │   └── websocket_client.dart
│   │   │   ├── errors/
│   │   │   ├── constants/
│   │   │   └── utils/
│   │   │
│   │   ├── models/
│   │   │   ├── user.dart
│   │   │   ├── wallet.dart
│   │   │   ├── round.dart
│   │   │   ├── bet.dart
│   │   │   ├── transaction.dart
│   │   │   └── fairness.dart
│   │   │
│   │   ├── repositories/
│   │   │   ├── auth_repository.dart
│   │   │   ├── player_repository.dart
│   │   │   ├── game_repository.dart
│   │   │   └── fairness_repository.dart
│   │   │
│   │   ├── features/
│   │   │   ├── splash/
│   │   │   ├── auth/
│   │   │   ├── home/
│   │   │   ├── game/
│   │   │   ├── history/
│   │   │   ├── profile/
│   │   │   ├── settings/
│   │   │   └── tutorial/
│   │   │
│   │   ├── widgets/
│   │   │   ├── cyber_spider.dart
│   │   │   ├── multiplier_display.dart
│   │   │   ├── cashout_button.dart
│   │   │   ├── bet_panel.dart
│   │   │   ├── game_background.dart
│   │   │   ├── connection_status.dart
│   │   │   └── balance_display.dart
│   │   │
│   │   └── theme/
│   │       └── app_theme.dart
│   │
│   ├── assets/
│   │   ├── images/
│   │   ├── sounds/
│   │   └── fonts/
│   │
│   ├── test/
│   └── pubspec.yaml
│
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── wallet.py
│   │   ├── round.py
│   │   ├── bet.py
│   │   ├── transaction.py
│   │   ├── game_settings.py
│   │   ├── audit_log.py
│   │   └── session.py
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── player.py
│   │   ├── game.py
│   │   ├── wallet.py
│   │   ├── fairness.py
│   │   └── admin.py
│   │
│   ├── api/
│   │   ├── auth.py
│   │   ├── player.py
│   │   ├── game.py
│   │   ├── fairness.py
│   │   ├── health.py
│   │   └── admin/
│   │       ├── auth.py
│   │       ├── dashboard.py
│   │       ├── users.py
│   │       ├── rounds.py
│   │       ├── transactions.py
│   │       ├── wallet_adjustments.py
│   │       ├── fairness.py
│   │       ├── audit_logs.py
│   │       ├── settings.py
│   │       └── system.py
│   │
│   ├── game/
│   │   ├── engine.py
│   │   ├── state.py
│   │   ├── multiplier.py
│   │   └── fairness.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── wallet_service.py
│   │   ├── game_service.py
│   │   ├── fairness_service.py
│   │   └── audit_service.py
│   │
│   ├── middleware/
│   │   ├── auth.py
│   │   ├── rate_limit.py
│   │   ├── request_id.py
│   │   └── security_headers.py
│   │
│   └── migrations/
│
├── admin/
│   ├── frontend/
│   └── README.md
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   ├── e2e/
│   └── load/
│
├── .github/
│   └── workflows/
│       ├── flutter_android.yml
│       ├── backend_tests.yml
│       └── release.yml
│
├── .env.example
├── .gitignore
├── README.md
└── CHANGELOG.md
```

---

# 6. Flutter Application Responsibilities

Flutter is responsible for:

- UI
- animations
- sounds
- user input
- REST communication
- WebSocket communication
- secure token storage
- displaying server state
- displaying wallet state returned by server
- local preferences
- reconnection UI
- error presentation

Flutter is NOT responsible for:

- deciding crash point
- deciding payout
- deciding wallet balance
- creating authoritative rounds
- settling bets
- modifying server transactions
- storing production secrets

---

# 7. Flutter Screens

## 7.1 Splash

```text
ZERO GRAVITY

Cyber Spider Crash Adventure

Loading...
```

Tasks:

1. Initialize app.
2. Load secure session.
3. Check backend availability.
4. Refresh token if required.
5. Fetch profile/balance.
6. Navigate to login or home.

## 7.2 Login

Fields:

```text
Username / Email
Password
```

Actions:

```text
LOGIN
REGISTER
FORGOT PASSWORD
```

## 7.3 Register

Fields:

```text
Username
Email
Password
Confirm Password
```

Server validates all fields.

## 7.4 Home

```text
ZERO GRAVITY

Balance: 10,000

[ PLAY ]

[ HISTORY ]
[ PROFILE ]
[ SETTINGS ]
[ HOW TO PLAY ]
```

## 7.5 Game screen

```text
+--------------------------------+
| Balance             Connection |
|                                |
|             2.37x              |
|                                |
|        CYBER SPIDER            |
|          ↑                     |
|       animated                 |
|                                |
| Bet Amount                     |
| [10] [50] [100] [500]          |
| [ Custom ]                     |
|                                |
|       [ CASH OUT ]             |
|                                |
| Round: AG-xxxxx                |
| Status: RUNNING                |
+--------------------------------+
```

## 7.6 History

Display:

```text
Round
Crash multiplier
Player bet
Cash-out multiplier
Result
Payout
Time
```

## 7.7 Profile

Display:

```text
Username
Member since
Games played
Wins
Losses
Best cash-out
Current balance
```

## 7.8 Settings

```text
Sound effects
Music
Vibration
Animations
Particle effects
Session timer
Break reminder
Logout
Change password
```

---

# 8. Game Screen State

The Flutter game screen must represent explicit states:

```text
DISCONNECTED
WAITING
BETTING
RUNNING
CASHED_OUT
CRASHED
ROUND_END
```

UI must never show a fake running round when the server says the round is over.

---

# 9. Spider Animation

The cyber spider is a visual representation only.

Animation states:

```text
idle
climbing
fast_climbing
warning
falling
crashed
```

Animation must be driven from authoritative server timing/state.

Do not use:

```text
multiplier += 0.01 per frame
```

because different devices run at different FPS.

Use:

```text
server start timestamp
        +
authoritative multiplier updates
        ↓
visual interpolation
```

The animation can interpolate between server updates for smooth rendering, but it cannot create an authoritative result.

---

# 10. Backend Architecture

FastAPI is the central authority.

```text
HTTP request
     ↓
FastAPI route
     ↓
Pydantic validation
     ↓
Authentication
     ↓
Authorization
     ↓
Service layer
     ↓
Database transaction
     ↓
Response
```

For game events:

```text
Game Engine
     ↓
WebSocket broadcaster
     ↓
Authenticated clients
```

---

# 11. Backend Game Engine

The game engine runs only on the backend.

Responsibilities:

1. Create rounds.
2. Generate secure server seed.
3. Generate commitment hash.
4. Determine crash point.
5. Start round.
6. Track authoritative timing.
7. Broadcast multiplier updates.
8. Detect crash.
9. Settle unresolved bets.
10. Reveal fairness information after round.
11. Store history.
12. Start next round.

---

# 12. Game State Machine

Valid states:

```text
WAITING
BETTING
RUNNING
CASHED_OUT
CRASHED
ROUND_END
```

Valid transitions:

```text
WAITING → BETTING
BETTING → RUNNING
RUNNING → CASHED_OUT
RUNNING → CRASHED
CASHED_OUT → ROUND_END
CRASHED → ROUND_END
ROUND_END → WAITING
```

Invalid transitions must be rejected.

The state machine should be unit-tested independently.

---

# 13. Multiplier Engine

The server calculates the authoritative multiplier.

Concept:

```text
elapsed_time
      ↓
multiplier_function()
      ↓
current multiplier
```

Reference behavior:

```text
0.0 sec → 1.00x
1.0 sec → ~1.08x
2.0 sec → ~1.18x
3.0 sec → ~1.31x
4.0 sec → ~1.46x
5.0 sec → ~1.64x
10 sec  → ~2.70x
```

Exact formula must be centralized in:

```text
backend/game/multiplier.py
```

Do not duplicate the authoritative multiplier formula in Flutter.

Flutter may interpolate visual values only.

---

# 14. Crash Point Generation

The crash point must be generated before the round begins.

Use cryptographically secure randomness.

The server creates:

```text
server_seed
```

Then:

```text
SHA256(server_seed)
```

is published as the commitment.

The round result is derived deterministically using:

```text
HMAC-SHA256(
    server_seed,
    round_id + client_seed
)
```

The derived randomness is converted to a documented crash multiplier.

Important:

```text
Flutter never chooses the crash point.
```

---

# 15. Fairness System

## Before round

```text
Generate server seed
        ↓
SHA256(server seed)
        ↓
Publish commitment hash
```

## During round

```text
server_seed
round_id
optional client_seed
        ↓
HMAC-SHA256
        ↓
randomness
        ↓
crash multiplier
```

## After round

```text
Reveal server seed
        ↓
Player can calculate SHA256(seed)
        ↓
Compare with original commitment
        ↓
Verify result
```

Fairness implementation:

```text
backend/game/fairness.py
backend/services/fairness_service.py
```

---

# 16. Wallet Architecture

Use integer virtual credits.

Never use floating-point money-style balances.

Wallet operations:

```text
CREATE
BET
PAYOUT
ADJUSTMENT
BONUS
```

Every balance-changing operation creates a transaction record.

Example:

```text
Before:       10,000
Bet:             100
After:          9,900
```

Cash-out:

```text
Bet: 100
Multiplier: 2.50
Payout: 250

9,900 + 250 = 10,150
```

---

# 17. Cash-Out Race Protection

This is one of the most important backend correctness requirements.

Example:

```text
Server crash point: 2.50x
Client sends cash-out at 2.52x
```

The server must decide based on authoritative server timing.

Do not trust the multiplier sent by the phone.

Cash-out processing:

```text
BEGIN TRANSACTION

Validate authenticated user
Validate round
Validate bet
Validate round state
Validate server time
Calculate authoritative multiplier
Validate bet has not already settled
Calculate payout
Update bet
Update wallet
Create transaction
Create audit event if applicable

COMMIT
```

If another cash-out request arrives at the same time, only one can succeed.

The previously implemented race-safe approach should remain in the backend; SQLite development mode must use an atomic conditional update/transaction strategy rather than assuming `SELECT FOR UPDATE` behaves like PostgreSQL.

---

# 18. REST API Contract

## Authentication

```http
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/refresh
POST /api/auth/forgot-password
POST /api/auth/reset-password
```

## Player

```http
GET /api/player/profile
GET /api/player/balance
GET /api/player/history
PATCH /api/player/settings
```

## Game

```http
GET /api/game/current
POST /api/game/join
POST /api/game/cashout
GET /api/game/history
```

## Fairness

```http
GET /api/fairness/{round_id}
GET /api/fairness/{round_id}/verify
```

## Health

```http
GET /api/health
GET /api/health/detailed
```

---

# 19. API Request Rules

Every request must be:

```text
Authenticated where required
Validated
Authorized
Rate-limited where appropriate
Logged safely
```

Never trust client fields such as:

```text
balance
payout
crash_point
cashout_multiplier
round_result
```

If a client sends them, ignore/reject them and calculate the authoritative value on the server.

---

# 20. WebSocket Architecture

Endpoint:

```text
/ws/game
```

Production:

```text
wss://your-domain/ws/game
```

Development:

```text
ws://LAN-IP:8000/ws/game
```

## Round start

```json
{
  "type": "round_start",
  "round_id": "AG-20261002-00123",
  "server_seed_hash": "abc123",
  "start_timestamp": "2026-10-02T14:23:01Z"
}
```

## Multiplier update

```json
{
  "type": "multiplier_update",
  "round_id": "AG-20261002-00123",
  "multiplier": 2.37,
  "elapsed_ms": 8420,
  "status": "running"
}
```

## Crash

```json
{
  "type": "crash",
  "round_id": "AG-20261002-00123",
  "crash_multiplier": 3.42,
  "status": "crashed",
  "server_seed_hash": "abc123"
}
```

## Private cash-out confirmation

```json
{
  "type": "cashout",
  "round_id": "AG-20261002-00123",
  "multiplier": 2.81,
  "payout": 281,
  "new_balance": 10181
}
```

## Heartbeat

```json
{
  "type": "ping",
  "timestamp": 1727871781
}
```

---

# 21. WebSocket Security

WebSocket connections must:

- authenticate the player
- validate messages
- enforce rate limits
- reject malformed payloads
- close abusive connections
- never accept client-authoritative game results

The server remains authoritative even if a modified APK sends arbitrary WebSocket messages.

---

# 22. Database Design

## users

```text
id
username
email
password_hash
status
role
created_at
last_login_at
```

## wallets

```text
id
user_id
balance
updated_at
```

## rounds

```text
id
round_number
server_seed_hash
server_seed
client_seed
crash_multiplier
started_at
ended_at
status
```

Active/future server seeds must be protected.

## bets

```text
id
round_id
user_id
amount
cashout_multiplier
payout
status
created_at
```

## transactions

```text
id
user_id
type
amount
balance_before
balance_after
reference_id
created_at
```

## game_settings

```text
id
minimum_bet
maximum_bet
starting_balance
house_edge
game_speed
animation_speed
betting_window_ms
maintenance_mode
updated_at
updated_by
```

## audit_logs

```text
id
admin_user_id
action
target_type
target_id
payload_json
ip_address
created_at
```

Audit records should be append-only.

## sessions

Track:

```text
session_id
user_id
device metadata
created_at
last_seen
revoked_at
refresh-token state
```

---

# 23. Database Environment

## Development

```text
SQLite
```

Advantages:

- simple
- local
- fast development
- easy automated tests

## Production

```text
PostgreSQL
```

Production must use:

- proper indexes
- migrations
- transactions
- backups
- restricted DB access
- encrypted connections where applicable
- separate credentials

---

# 24. Authentication

## Player authentication

Use:

```text
Argon2id password hashing
Short-lived access JWT
Refresh token rotation
Token revocation
Session/device tracking
```

Example target:

```text
Access token: ~10–15 minutes
Refresh token: longer-lived and rotated
```

Never store passwords in plaintext.

Never log:

```text
password
access token
refresh token
JWT signing secret
database password
server seed
```

---

# 25. Flutter Secure Storage

Flutter must store session secrets using Android secure storage backed by platform security mechanisms.

Do not use:

```text
plain text file
SharedPreferences for sensitive tokens
hard-coded credentials
```

Do not put:

```text
JWT signing key
database password
server seed
admin credentials
private backend secrets
```

inside the APK.

---

# 26. Token Refresh Flow

```text
Flutter request
     ↓
Access token valid?
     |
   YES → request
     |
    NO
     ↓
Refresh token
     ↓
Backend validates + rotates
     ↓
New access token
     ↓
Retry original request
```

If refresh fails:

```text
Clear secure session
Return to login
```

---

# 27. Anti-Cheat

The client is untrusted.

Every important operation is validated server-side.

Cash-out checks:

```text
JWT valid
User active
Round exists
Round is active
Bet belongs to user
Bet exists
Bet status = PLACED
Server time before crash
Authoritative multiplier calculated
Payout calculated server-side
Wallet transaction succeeds
Bet settled exactly once
```

Potential attacks:

```text
Modified APK
Replay requests
Duplicate cash-out
Fake multiplier
Fake payout
Fake wallet
Fake round ID
WebSocket flood
Expired token
Unauthorized API calls
```

All must be rejected server-side.

---

# 28. Offline and Reconnection Rules

Production is **online-only**.

If backend is unavailable:

```text
Do not start new round
Do not accept new bet
Do not perform local cash-out
Do not change wallet locally
Do not silently switch to Demo Mode
```

Display:

```text
SERVER CONNECTION LOST

Reconnecting...
```

Suggested backoff:

```text
1s
2s
4s
8s
16s
```

After repeated failure:

```text
Please check your internet connection.
```

On reconnection:

```text
GET current round
GET current balance
GET recent transaction
GET player state
Synchronize UI
```

The server decides what happened during the disconnect.

---

# 29. Development Demo Mode

A local Demo Mode is permitted for UI and development testing.

Important distinction:

```text
Development:
Flutter → local/mock repository or development backend
```

Production:

```text
Flutter → HTTPS/WSS → FastAPI → PostgreSQL
```

Do not ship a production APK that silently falls back to a local authoritative game engine.

Demo Mode must be clearly environment-controlled.

---

# 30. Flutter Configuration

Use build-time environment configuration.

Example:

```bash
flutter run ^
  --dart-define=ANTI_GRAVITY_ENV=development ^
  --dart-define=ANTI_GRAVITY_API_URL=http://192.168.1.100:8000 ^
  --dart-define=ANTI_GRAVITY_WS_URL=ws://192.168.1.100:8000/ws/game
```

Production:

```text
ANTI_GRAVITY_ENV=production
ANTI_GRAVITY_API_URL=https://api.example.com
ANTI_GRAVITY_WS_URL=wss://api.example.com/ws/game
```

Never hard-code a developer LAN IP into the production build.

---

# 31. Admin Panel

The Admin Panel is a separate authenticated web application.

Architecture:

```text
Admin Browser
      ↓
HTTPS
      ↓
Protected FastAPI Admin APIs
      ↓
PostgreSQL
```

The Admin Browser never connects directly to PostgreSQL.

The player app never calls admin APIs.

---

# 32. Admin Roles

Use RBAC:

| Role | Access |
|---|---|
| SUPER_ADMIN | Full access + role management |
| ADMIN | Full operational access |
| OPERATOR | Game/user operations, no RBAC management |
| AUDITOR | Read-only audit/fairness |
| SUPPORT | Read-only support/user information |

Sensitive operations should require stronger authorization and preferably MFA/step-up authentication.

---

# 33. Admin Dashboard

Display:

```text
Total Users
Active Users
Online Users

Current Round
Current Multiplier
Players in Round

Games Today
Virtual Credits in Circulation
Cash-out Rate

API Health
Database Health
WebSocket Connections

Recent Security Events
```

---

# 34. Admin User Management

Authorized administrators can:

```text
Search users
Filter users
View user profile
Suspend account
Ban account
Reactivate account
View balance
View game history
View transaction history
View sessions
View security events
```

Every sensitive action is audited.

---

# 35. Admin Wallet Management

Because this is virtual currency, authorized administrators may have a controlled virtual-credit adjustment function.

Requirements:

```text
Required reason
Permission check
Before balance
Adjustment
After balance
Admin ID
Timestamp
Target user
Audit record
```

No real-money transaction functionality.

---

# 36. Admin Round Monitoring

Admin can view:

```text
Round ID
Status
Start time
End time
Multiplier
Crash multiplier
Number of players
Bet volume
Payout volume
Fairness status
```

Critical prohibition:

> The Admin Panel must NEVER provide a visible or hidden function that manually changes an individual authoritative round result.

No:

```text
Force crash
Change crash point
Change payout
Rewrite result
Delete round result
```

The game engine remains authoritative.

---

# 37. Admin Game Settings

Authorized roles may configure validated settings such as:

```text
Minimum bet
Maximum bet
Starting virtual balance
Betting window
Game speed
Maintenance mode
```

Sensitive settings require stronger authorization.

Every configuration change is audited.

---

# 38. Fairness Verification in Admin

Admin can inspect:

```text
Round ID
Commitment hash
Revealed server seed
Crash result
Verification result
Verification timestamp
```

Active/future seeds must remain hidden.

---

# 39. Audit Logging

Audit events include:

```text
Admin login
Admin logout
Failed login
User suspension
User ban
Wallet adjustment
Game setting change
Maintenance change
Fairness verification
Security event
Role change
```

Audit logs must be:

```text
append-only
read-only through UI
sanitized
timestamped
associated with actor
associated with target
```

---

# 40. Admin API

```http
POST /api/admin/auth/login
POST /api/admin/auth/logout

GET /api/admin/dashboard

GET /api/admin/users
GET /api/admin/users/{user_id}
PATCH /api/admin/users/{user_id}/status
GET /api/admin/users/{user_id}/history
GET /api/admin/users/{user_id}/transactions

GET /api/admin/rounds
GET /api/admin/rounds/{round_id}

GET /api/admin/transactions
POST /api/admin/wallet-adjustments

GET /api/admin/audit-logs

GET /api/admin/fairness/{round_id}
POST /api/admin/fairness/{round_id}/verify

GET /api/admin/system/health
GET /api/admin/system/metrics

GET /api/admin/settings
PATCH /api/admin/settings
```

---

# 41. Security Architecture

Use defense in depth.

Layers:

```text
Android secure storage
        ↓
HTTPS/WSS
        ↓
Reverse proxy / firewall
        ↓
Rate limiting
        ↓
FastAPI validation
        ↓
Authentication
        ↓
Authorization
        ↓
Service layer
        ↓
Database transaction
        ↓
Audit logging
```

Do not claim the system is “unhackable”.

The objective is to prevent compromise of:

```text
Game authority
Wallet
Authentication
Database
Fairness
Admin system
```

---

# 42. API Security

Implement:

- strict Pydantic validation
- authentication
- authorization
- rate limiting
- request IDs
- CORS allowlist
- secure headers
- HTTPS
- HSTS in production
- appropriate CSP for admin web app
- safe error responses
- no secret leakage
- no SQL string concatenation
- database parameterization via SQLAlchemy
- WebSocket rate limiting

---

# 43. Security Test Matrix

| Attack | Expected |
|---|---|
| Duplicate cash-out | Reject |
| Replay old JWT | 401 |
| Expired JWT | 401 |
| Invalid round | 404 |
| Unauthorized user data | 403 |
| Fake multiplier | Ignore/recalculate |
| Fake payout | Ignore/recalculate |
| Negative bet | 422 |
| Bet over maximum | 422 |
| Duplicate transaction | Reject |
| Unauthorized admin API | 403 |
| WebSocket flood | Rate-limit/disconnect |
| SQL injection attempt | Reject/sanitize |
| Hidden client balance | Never trusted |

---

# 44. Error Handling

Flutter should show friendly messages.

Examples:

```text
401 → Session expired. Please log in again.
403 → You do not have permission.
404 → Round not found.
409 → This action was already processed.
422 → Please check the entered amount.
429 → Too many requests. Please try again later.
500 → Server error. Please try again.
503 → Service temporarily unavailable.
```

Never expose:

```text
stack traces
database errors
JWT internals
server paths
secret values
```

to normal players.

---

# 45. Logging

## Backend logs

Use structured logs.

Include:

```text
timestamp
request_id
route
status
latency
user_id where appropriate
event type
error category
```

Never log:

```text
passwords
tokens
database passwords
active server seeds
private secrets
```

## Flutter logs

Development only:

```text
API request status
WebSocket state
navigation
debug state
```

Release builds should minimize sensitive logging.

---

# 46. Analytics

Privacy-respecting server-side metrics:

```text
DAU / MAU
Games per day
Average session duration
Rounds per session
Virtual credits wagered
Cash-out distribution
Crash distribution
Win/loss distribution
API p50/p95/p99
WebSocket disconnect rate
App crash rate
```

Do not collect unnecessary personal information.

---

# 47. Responsible Game Design

Even though the economy is virtual, crash mechanics can encourage repetitive play.

Provide:

```text
Session timer
Break reminder
Daily virtual-credit statistics
Clear balance
Clear win/loss history
```

Do not secretly change outcomes based on:

```text
player balance
player behavior
loss streak
session length
```

Do not hide session duration.

---

# 48. Testing Strategy

Testing happens continuously, not only at the end.

## 48.1 Flutter unit tests

Test:

```text
models
API parsing
state management
authentication state
settings
UI controllers
WebSocket event parsing
reconnection logic
```

## 48.2 Flutter widget tests

Test:

```text
login screen
home
game screen
cash-out button
multiplier display
connection state
history
profile
settings
```

## 48.3 Backend unit tests

Test:

```text
multiplier
fairness
state machine
wallet arithmetic
cash-out validation
authentication
authorization
```

## 48.4 Integration tests

Test:

```text
register → login
login → profile
game join
bet
multiplier stream
cash-out
crash
wallet settlement
history
fairness verification
reconnect
```

## 48.5 End-to-end

Run:

```text
Flutter app
+
real FastAPI server
+
real database
+
real WebSocket
+
physical Android phone
```

---

# 49. Race-Condition Tests

Must test:

```text
Two cash-outs simultaneously
Cash-out exactly at crash boundary
Cash-out after crash
Repeated cash-out
Network retry
Duplicate HTTP request
WebSocket reconnect during cash-out
```

Expected:

```text
At most one successful settlement.
Wallet changes exactly once.
```

---

# 50. Load Testing

Targets:

```text
100 concurrent users — baseline
500 concurrent users — MVP target
1,000 concurrent users — stretch target
```

Measure:

```text
CPU
RAM
DB latency
API latency
WebSocket latency
cash-out success rate
error rate
connection count
```

Do not claim performance results until actually measured.

---

# 51. Flutter Android Development on Windows

Required tools:

```text
Flutter SDK
Dart
Android Studio
Android SDK
Platform-Tools
ADB
JDK compatible with Flutter/Android build
Git
Antigravity IDE
```

The physical Android phone remains the primary real-device test target.

No Ubuntu/WSL2 is required for normal Windows-native Flutter development.

---

# 52. Physical Android Phone Workflow

Connect phone with USB debugging enabled.

Verify:

```bash
adb devices
```

Expected:

```text
device
```

Run:

```bash
flutter devices
```

Then:

```bash
flutter run
```

For LAN backend testing:

```text
Phone
  |
Wi-Fi
  |
Windows laptop
  |
FastAPI :8000
```

Use the laptop's LAN IP, not:

```text
localhost
127.0.0.1
```

from the Android phone.

---

# 53. Android Debugging

Use:

```bash
adb logcat
```

Flutter:

```bash
flutter logs
```

Useful workflow:

```text
Flutter build/run
      ↓
Physical phone
      ↓
Reproduce issue
      ↓
ADB / Logcat
      ↓
Fix
      ↓
Flutter test
      ↓
Repeat
```

---

# 54. Flutter Debug APK

After the app builds correctly:

```bash
flutter build apk --debug
```

The actual generated APK path must be checked before installation.

Typical Flutter output:

```text
build/app/outputs/flutter-apk/app-debug.apk
```

Install:

```bash
adb install -r build/app/outputs/flutter-apk/app-debug.apk
```

Do not assume an APK exists until the build command succeeds and the file is present.

---

# 55. Release Build

For Play Store / production distribution:

```bash
flutter build appbundle --release
```

Release signing must use a proper Android keystore.

Never commit:

```text
keystore
key password
signing password
private signing credentials
```

Use GitHub Actions secrets or a secure local signing setup.

---

# 56. GitHub Actions CI/CD

## Flutter CI

Pipeline:

```text
Checkout
   ↓
Install Flutter stable
   ↓
flutter pub get
   ↓
flutter analyze
   ↓
flutter test
   ↓
flutter build apk --debug
   ↓
Upload artifact
```

## Backend CI

```text
Checkout
   ↓
Python setup
   ↓
Install dependencies
   ↓
Run lint/type checks
   ↓
Run unit tests
   ↓
Run integration tests
```

## Release pipeline

```text
Tag release
    ↓
Run Flutter tests
    ↓
Run backend tests
    ↓
Build AAB
    ↓
Sign
    ↓
Upload release artifact
```

---

# 57. Environment Separation

Use:

```text
development
staging
production
```

Development:

```text
SQLite
LAN API
debug logging
test accounts
```

Staging:

```text
PostgreSQL
HTTPS
production-like configuration
test credits
```

Production:

```text
PostgreSQL
HTTPS/WSS
real domain
restricted secrets
monitoring
backups
```

Never connect a debug APK accidentally to production without an explicit production configuration.

---

# 58. Production Deployment Architecture

```text
Internet
   |
DNS
   |
TLS / Reverse Proxy
   |
FastAPI application
   |
+--------------------+
|                    |
Game Engine      REST/WebSocket
|                    |
+---------+----------+
          |
     PostgreSQL
```

Optional later:

```text
Redis
```

may be introduced for distributed WebSocket/pub-sub or caching if scaling requires it.

Do not add infrastructure before needed.

---

# 59. Production Security

Production must use:

```text
HTTPS
WSS
Strong secrets
Firewall
Restricted DB access
Rate limiting
CORS allowlist
Security headers
Monitoring
Backups
Admin MFA
RBAC
Audit logs
```

Database should never be publicly exposed.

---

# 60. Backup and Recovery

Back up PostgreSQL regularly.

Maintain:

```text
database backup
configuration backup
migration history
release version
```

Recovery testing must be performed.

A backup that has never been restored is not a verified recovery plan.

---

# 61. Monitoring

Monitor:

```text
API availability
API latency
5xx errors
authentication failures
WebSocket connections
game loop status
database health
database latency
CPU
RAM
disk
security events
```

Alerts should focus on meaningful failures.

---

# 62. Versioning

Recommended:

```text
V0.1 — Flutter UI prototype
V0.2 — Flutter mock/demo flow
V0.3 — FastAPI + database foundation
V0.4 — Authentication
V0.5 — Server game engine
V0.6 — WebSocket real-time gameplay
V0.7 — Fairness
V0.8 — Security hardening
V0.9 — Admin Panel
V0.95 — Performance + physical-device QA
V1.0 — Production release
```

---

# 63. Sprint Plan

## Sprint 1 — Flutter foundation

Build:

```text
Flutter project
Theme
Navigation
Splash
Login
Register
Home
Game screen
History
Profile
Settings
Tutorial
```

No authoritative game logic yet.

Test:

```text
flutter analyze
flutter test
flutter run
```

---

## Sprint 2 — Flutter game UI / mock repository

Build:

```text
Multiplier widget
Cyber spider
Background
Bet panel
Cash-out button
Game state UI
Connection status
Sound system
```

Use mock/fixture data only for UI development.

Do not create a production-style local authoritative game engine in Flutter.

---

## Sprint 3 — FastAPI foundation

Build:

```text
FastAPI
SQLAlchemy
SQLite
Alembic
models
schemas
health endpoints
configuration
```

Test database migrations and basic CRUD.

---

## Sprint 4 — Authentication

Build:

```text
register
login
logout
refresh
password reset
Argon2id
JWT
session tracking
```

Connect Flutter authentication.

Test:

```text
valid login
invalid login
expired token
refresh
logout
```

---

## Sprint 5 — Server game engine

Build:

```text
round state machine
multiplier engine
round lifecycle
secure seed
crash point
wallet integration
```

Backend becomes the only authoritative game engine.

---

## Sprint 6 — WebSocket

Build:

```text
/ws/game
round_start
multiplier_update
crash
cashout
ping
```

Connect Flutter WebSocket client.

Test:

```text
connect
disconnect
reconnect
multiple clients
malformed messages
rate limiting
```

---

## Sprint 7 — Cash-out and wallet correctness

Implement:

```text
bet placement
cash-out
atomic wallet update
transaction records
duplicate protection
race protection
```

Run dedicated race tests.

Acceptance:

```text
Wallet changes once.
Bet settles once.
Only valid cash-out succeeds.
```

---

## Sprint 8 — Fairness

Build:

```text
server seed
commitment
HMAC derivation
crash calculation
reveal
verification endpoint
```

Add Flutter fairness/history display.

---

## Sprint 9 — Security hardening

Implement:

```text
rate limiting
CORS
security headers
request IDs
RBAC
session management
secure token storage
WebSocket protection
audit logging
input validation
```

Run security test matrix.

---

## Sprint 10 — Admin Panel

Build:

```text
admin login
MFA/step-up where required
RBAC
dashboard
users
wallet adjustments
round monitoring
transactions
fairness
audit logs
settings
maintenance
health
metrics
```

Verify that no admin feature can modify an individual authoritative round result.

---

## Sprint 11 — Performance

Run:

```text
API profiling
DB indexes
WebSocket tests
100-user load test
500-user target test
memory review
Flutter performance review
```

---

## Sprint 12 — Android QA

Test on physical phone:

```text
install
launch
login
game
cash-out
crash
reconnect
history
settings
background/foreground
screen rotation behavior
network loss
slow network
```

Use ADB and Logcat.

---

## Sprint 13 — Production preparation

Build:

```text
PostgreSQL production
HTTPS
WSS
secrets
reverse proxy
monitoring
backups
recovery test
release signing
GitHub Actions release pipeline
```

---

## Sprint 14 — Final release

Run:

```text
full backend test suite
full Flutter test suite
security suite
integration suite
E2E suite
physical-device regression
production smoke test
backup/restore verification
```

Then build:

```bash
flutter build appbundle --release
```

---

# 64. Flutter Testing Definition

Every sprint must finish with:

```bash
flutter analyze
flutter test
```

For Android-specific changes:

```bash
flutter build apk --debug
flutter run
```

Only proceed to the next sprint after the current sprint's acceptance criteria pass.

---

# 65. Backend Testing Definition

Use:

```text
pytest
pytest-asyncio
httpx
```

Run:

```bash
pytest
```

Test:

```text
API
database
game engine
fairness
wallet
cash-out
WebSocket
authentication
security
admin
```

---

# 66. Existing Backend Test Baseline

The previous backend/client development reached a strong test baseline before the Flutter migration.

Historical checkpoints included:

```text
Sprint 3: 58 passed
Sprint 4A: 70
Sprint 4B: 84
Sprint 4D: 102
Sprint 5: 116
Sprint 6: 134
Sprint 7: 145
Sprint 8: 191 total
```

These historical results are evidence of the previous implementation state, not automatic proof that the new Flutter frontend is correct.

After migration:

- Preserve backend behavior.
- Re-run backend tests.
- Add Flutter tests.
- Add Flutter ↔ FastAPI integration tests.
- Add physical Android E2E tests.

Do not claim migration success until these tests actually pass.

---

# 67. Final MVP Acceptance Criteria

## Flutter

- [ ] App launches.
- [ ] Splash works.
- [ ] Login works.
- [ ] Registration works.
- [ ] Home works.
- [ ] Game screen works.
- [ ] History works.
- [ ] Profile works.
- [ ] Settings work.
- [ ] Tutorial works.
- [ ] Sound works.
- [ ] Cyber spider animation works.
- [ ] Connection state is visible.

## Backend

- [ ] FastAPI runs.
- [ ] SQLite development works.
- [ ] PostgreSQL production configuration works.
- [ ] Authentication works.
- [ ] Game engine works.
- [ ] WebSocket works.
- [ ] Fairness works.
- [ ] Wallet works.
- [ ] Cash-out is race-safe.
- [ ] History works.
- [ ] Security tests pass.

## Server authority

- [ ] Client cannot determine crash point.
- [ ] Client cannot determine payout.
- [ ] Client cannot determine wallet balance.
- [ ] Client cannot force cash-out success.
- [ ] Client cannot alter round result.

## Admin

- [ ] Admin login works.
- [ ] RBAC works.
- [ ] Dashboard works.
- [ ] User management works.
- [ ] Wallet adjustment is audited.
- [ ] Round monitoring works.
- [ ] Fairness verification works.
- [ ] Audit logs are append-only.
- [ ] Admin cannot alter authoritative round outcomes.

## Android

- [ ] Debug APK builds.
- [ ] APK installs on physical phone.
- [ ] App connects to FastAPI over LAN.
- [ ] ADB debugging works.
- [ ] Logcat debugging works.
- [ ] Release AAB builds and signs correctly.

---

# 68. Final Architecture

```text
                         USER
                          |
                          v
                 Flutter Android App
                          |
                 HTTPS / WebSocket
                          |
                          v
                +-------------------+
                |   FastAPI Server  |
                +-------------------+
                  |       |       |
                  |       |       |
                  v       v       v
                Auth    Game    Admin
                         Engine   APIs
                           |
                     Fairness Engine
                           |
                     Wallet Service
                           |
                           v
                     PostgreSQL
```

Game lifecycle:

```text
Generate secure seed
        ↓
SHA256 commitment
        ↓
Create round
        ↓
Publish round start
        ↓
Accept bets
        ↓
Start server game loop
        ↓
Broadcast multiplier
        ↓
Player requests cash-out
        ↓
Server validates authoritative time
        ↓
Transaction settles once
        ↓
OR
        ↓
Crash occurs
        ↓
Unsettled bet becomes LOST
        ↓
Reveal fairness information
        ↓
Store history
        ↓
Next round
```

---

# 69. The Most Important Rule

> **The phone displays the game. The server controls the game.**

Flutter is the presentation and interaction layer.

FastAPI is the authority.

The database is the durable source of wallet and historical state.

The fairness system makes the round result auditable.

The Admin Panel operates the platform without becoming a backdoor.

---

# 70. Antigravity Master Build Prompt

Use this prompt in Antigravity when starting implementation:

```text
Build the Zero Gravity project according to the complete Full-Stack Development Plan.

PROJECT:
Zero Gravity — futuristic cyber-spider crash arcade game.

ARCHITECTURE:
- Flutter + Dart Android frontend.
- Python + FastAPI backend.
- SQLite for development.
- PostgreSQL for production.
- REST API.
- WebSocket at /ws/game.
- Separate authenticated Admin Web App.
- One repository containing mobile, backend, admin and tests.

CRITICAL:
The Android client is untrusted.
The server is authoritative.

Never allow Flutter to decide:
- crash point
- multiplier result
- payout
- wallet balance
- cash-out success
- round result

GAME:
- virtual credits only
- no real money
- no deposits
- no withdrawals
- no cryptocurrency wagering
- no cash prizes
- cyber spider visual theme
- multiplier begins at 1.00x
- server controls crash point
- player can cash out before crash

BACKEND:
Implement:
- FastAPI
- SQLAlchemy
- Pydantic
- Alembic
- authentication
- Argon2id
- JWT access tokens
- refresh-token rotation
- session tracking
- rate limiting
- CORS
- security headers
- request IDs
- REST APIs
- WebSocket
- game state machine
- multiplier engine
- fairness engine
- wallet service
- atomic cash-out settlement
- audit logging
- health endpoints

FAIRNESS:
- secure server seed
- SHA256 commitment
- HMAC-SHA256 derivation
- round ID/client seed
- post-round reveal
- verification endpoint
- never expose active/future server seeds

DATABASE:
Implement:
- users
- wallets
- rounds
- bets
- transactions
- game_settings
- audit_logs
- sessions

WALLET:
- integer virtual credits
- all changes server-side
- database transactions
- exactly-once settlement
- duplicate cash-out protection
- race-condition tests

FLUTTER:
Create:
- splash
- login
- register
- home
- game
- history
- profile
- settings
- tutorial
- cyber spider
- multiplier display
- bet panel
- cash-out button
- connection status
- secure token storage
- REST client
- WebSocket client
- reconnect logic
- audio

PRODUCTION:
- HTTPS
- WSS
- PostgreSQL
- reverse proxy
- secure secrets
- monitoring
- backups
- recovery testing

ADMIN:
Separate authenticated web application.
Implement:
- admin login
- strong authentication
- MFA/step-up for privileged actions where appropriate
- RBAC
- dashboard
- users
- virtual-credit adjustments
- transactions
- rounds
- fairness
- audit logs
- settings
- maintenance
- health
- metrics

ABSOLUTE ADMIN RULE:
Never implement any visible or hidden mechanism that allows an administrator to manually change an individual authoritative game result.

TESTING:
- Flutter unit tests
- Flutter widget tests
- backend unit tests
- integration tests
- WebSocket tests
- cash-out race tests
- security tests
- admin tests
- load tests
- physical Android E2E tests

ANDROID:
Development environment:
- Windows
- Antigravity IDE
- Flutter SDK
- Android Studio
- Android SDK
- ADB
- physical Android phone

Build:
flutter analyze
flutter test
flutter build apk --debug
flutter build appbundle --release

CI:
GitHub Actions must run Flutter analysis/tests/build and backend tests.

DEVELOPMENT ORDER:
1. Flutter project foundation
2. Flutter UI
3. Mock/demo repository
4. FastAPI foundation
5. Authentication
6. Server game engine
7. WebSocket
8. Wallet/cash-out
9. Fairness
10. Security
11. Admin
12. Performance
13. Android QA
14. Production
15. Release

RULE:
Do not skip testing between stages.
Do not claim a build or test passed unless it actually passed.
Do not rewrite the backend unnecessarily.
Preserve existing backend API/WebSocket behavior during Flutter migration unless a documented contract change is required.
```

---

# 71. Final Definition of Done

Zero Gravity V1 is complete only when:

```text
Flutter frontend       PASS
FastAPI backend        PASS
Database               PASS
Authentication         PASS
Game engine            PASS
WebSocket              PASS
Fairness               PASS
Wallet                 PASS
Cash-out race tests    PASS
Security tests         PASS
Admin Panel            PASS
RBAC                   PASS
Audit logging          PASS
Android build          PASS
Physical phone QA      PASS
CI/CD                  PASS
Production deployment  PASS
Backup/recovery        PASS
Final regression       PASS
```

No single component is considered complete in isolation.

The final system is complete only when:

```text
Flutter
   ↕
REST + WebSocket
   ↕
FastAPI
   ↕
Game + Fairness + Wallet + Auth
   ↕
PostgreSQL
```

works together as one tested system.
