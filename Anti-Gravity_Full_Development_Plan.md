# Anti-Gravity --- Full Development Plan

## 1. Project Overview

**App Name:** Anti-Gravity\
**Genre:** Crash / Multiplier Arcade Game\
**Platform:** Android first, with optional Windows/Web builds\
**Primary Language:** Python\
**Development Environment:** Antigravity\
**Recommended Python UI:** Kivy + KivyMD\
**Backend:** FastAPI\
**Database:** SQLite for development, PostgreSQL for production\
**Game Model:** Virtual credits / non-cash gameplay

### Core Concept

Anti-Gravity is inspired by the visual and gameplay structure of
crash-style games.

Instead of an airplane:

> A **spider** climbs/flys upward through an animated environment.

The multiplier starts at **1.00x** and increases continuously.

Example:

`1.00x → 1.05x → 1.20x → 1.50x → 2.00x → 5.00x → 10.00x`

At an unpredictable point, the spider crashes/falls.

The player must press **CASH OUT** before the crash.

If cashing out at 2.35x with 100 virtual credits:

`100 × 2.35 = 235 virtual credits`

If the spider crashes before cash-out:

`100 virtual credits → 0`

This plan intentionally uses virtual credits and does not implement
deposits, withdrawals, or real-money wagering.

------------------------------------------------------------------------

# 2. Product Goals

## MVP Goals

The first release should provide:

-   Attractive spider-themed crash animation
-   Live multiplier
-   Virtual-credit wallet
-   Bet amount selection
-   Start round
-   Cash-out button
-   Crash animation
-   Win/loss calculation
-   Round history
-   Statistics
-   Sound effects
-   Settings
-   Tutorial
-   Local account/profile
-   Server-synchronized game rounds
-   Fair/random crash generation
-   Basic admin/debug panel

## Future Goals

Possible future additions:

-   Multiplayer spectators
-   Leaderboards
-   Achievements
-   Missions
-   Daily virtual-credit rewards
-   Skins
-   Spider animations
-   Multiple environments
-   Seasonal themes
-   Cloud accounts
-   Push notifications

------------------------------------------------------------------------

# 3. Important Product Boundary

Anti-Gravity should initially remain a **free-to-play virtual-credit
game**.

Do not implement:

-   Deposits
-   Withdrawals
-   Cash prizes
-   Cryptocurrency wagering
-   Payment-based betting
-   Real-money wallet
-   Automated betting with real money

If the product is later intended to involve real-money gambling, that
requires a separate legal/compliance architecture, jurisdiction-specific
licensing, age verification, responsible-gaming controls, payment
compliance, auditability, and certified game/RNG processes.

------------------------------------------------------------------------

# 4. Recommended Technology Stack

## Mobile App

``` text
Python
Kivy
KivyMD
Buildozer
Android SDK
Android NDK
```

## Backend

``` text
Python
FastAPI
Uvicorn
Pydantic
SQLAlchemy
```

## Database

Development:

``` text
SQLite
```

Production:

``` text
PostgreSQL
```

## Networking

``` text
REST API
WebSocket
JSON
HTTPS
```

## Development

``` text
Git
GitHub
Antigravity
VS Code (optional)
Android Studio (for SDK/logging)
```

------------------------------------------------------------------------

# 5. Overall Architecture

``` text
                    ANTI-GRAVITY
                         |
          +--------------+--------------+
          |                             |
      Android App                  Backend Server
       Kivy/KivyMD                    FastAPI
          |                             |
          | REST/WebSocket              |
          +-------------+---------------+
                        |
                    PostgreSQL
```

For offline development/testing:

``` text
Kivy App
   |
Local Game Engine
   |
SQLite
```

------------------------------------------------------------------------

# 6. Game Screen

The main screen should contain:

``` text
+------------------------------------------------+
|                 ANTI-GRAVITY                   |
|                                                |
|             Current Multiplier                 |
|                    2.37x                       |
|                                                |
|                    🕷️                          |
|                 /                              |
|              SPIDER                            |
|                                                |
|        Animated sky/background                 |
|                                                |
|   +----------------------------------------+   |
|   | Bet Amount                             |   |
|   | [ 10 ] [ 50 ] [ 100 ] [ 500 ]         |   |
|   +----------------------------------------+   |
|                                                |
|             [ CASH OUT ]                       |
|                                                |
| Balance: 10,000 credits                        |
|                                                |
| Previous: 1.24x  3.55x  1.08x  7.21x         |
+------------------------------------------------+
```

------------------------------------------------------------------------

# 7. Main Game Flow

## Step 1 --- Open App

Show:

``` text
ANTI-GRAVITY
Loading...
```

Then load the player profile.

## Step 2 --- Wallet

Example:

``` text
Balance
10,000 Credits
```

## Step 3 --- Select Bet

Example:

``` text
10
50
100
500
1000
```

The player can also enter a custom amount within the configured
virtual-credit limits.

## Step 4 --- Start Round

The server creates a unique round:

``` text
round_id
server_seed_hash
start_timestamp
```

## Step 5 --- Multiplier Starts

``` text
1.00x
```

Then increases continuously.

## Step 6 --- Spider Animation

The spider moves upward while the multiplier increases.

## Step 7 --- Cash Out

Player presses:

``` text
CASH OUT
```

The server validates that the round is still active.

Example:

``` text
Bet = 100
Cash-out = 2.85x

Payout = 285 credits
Profit = 185 credits
```

## Step 8 --- Crash

If the crash occurs first:

``` text
CRASHED AT 1.73x
```

The bet is lost.

## Step 9 --- Round History

Store:

``` text
Round ID
Bet
Crash multiplier
Cash-out multiplier
Result
Timestamp
```

------------------------------------------------------------------------

# 8. Multiplier Engine

The multiplier must be controlled by the server rather than trusting the
mobile client.

Conceptually:

``` python
multiplier = calculate_multiplier(elapsed_time)
```

The client only displays the server state.

Example:

``` text
0.0 sec  → 1.00x
1.0 sec  → 1.08x
2.0 sec  → 1.18x
3.0 sec  → 1.31x
4.0 sec  → 1.46x
5.0 sec  → 1.64x
```

The exact growth curve should be configurable.

------------------------------------------------------------------------

# 9. Crash Point Generation

For a fair virtual game, generate the crash point before the round
starts.

Use a cryptographically secure random generator.

Example concept:

``` python
import secrets

random_value = secrets.randbits(256)
```

Then convert the random value into a crash multiplier using a documented
mathematical function.

Important:

The mobile application must never determine the crash point.

------------------------------------------------------------------------

# 10. Provably-Fair Style Design

A useful design is:

### Before Round

Generate:

``` text
server_seed
```

Publish:

``` text
SHA256(server_seed)
```

This is the commitment hash.

### During Round

The server uses:

``` text
server_seed
round_id
optional client_seed
```

to derive the deterministic random value.

### After Round

Reveal:

``` text
server_seed
```

The client can verify:

``` text
SHA256(server_seed)
```

matches the previously published hash.

This makes the virtual game result auditable.

------------------------------------------------------------------------

# 11. Example Fairness Module

File:

``` text
backend/game/fairness.py
```

Responsibilities:

``` text
generate_seed()
hash_seed()
generate_round_randomness()
calculate_crash_point()
verify_round()
```

Example API:

``` python
class FairnessEngine:

    def create_seed(self):
        ...

    def commit_seed(self, seed):
        ...

    def calculate_result(self, seed, round_id):
        ...

    def verify_result(self, seed, round_id):
        ...
```

------------------------------------------------------------------------

# 12. Game State Machine

Use explicit game states.

``` text
WAITING
   ↓
BETTING
   ↓
RUNNING
   ↓
CASHED_OUT
   ↓
ROUND_END
```

Or:

``` text
RUNNING
   ↓
CRASHED
   ↓
ROUND_END
```

Never allow invalid transitions.

Example:

``` python
VALID_STATES = {
    "WAITING",
    "BETTING",
    "RUNNING",
    "CASHED_OUT",
    "CRASHED",
    "ROUND_END"
}
```

------------------------------------------------------------------------

# 13. Backend API

## Authentication

``` http
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
```

## Player

``` http
GET /api/player/profile
GET /api/player/balance
GET /api/player/history
```

## Game

``` http
GET /api/game/current
POST /api/game/join
POST /api/game/cashout
GET /api/game/history
```

## Fairness

``` http
GET /api/fairness/{round_id}
GET /api/fairness/{round_id}/verify
```

## Health

``` http
GET /api/health
```

------------------------------------------------------------------------

# 14. WebSocket

Use WebSocket for live game updates.

Endpoint:

``` text
/ws/game
```

Example server message:

``` json
{
    "type": "multiplier_update",
    "round_id": "AG-20261002-00123",
    "multiplier": 2.37,
    "status": "running"
}
```

Crash:

``` json
{
    "type": "crash",
    "round_id": "AG-20261002-00123",
    "crash_multiplier": 3.42,
    "status": "crashed"
}
```

Cash-out:

``` json
{
    "type": "cashout",
    "round_id": "AG-20261002-00123",
    "multiplier": 2.81,
    "payout": 281
}
```

------------------------------------------------------------------------

# 15. Database Design

## users

``` text
id
username
email
password_hash
created_at
status
```

## wallets

``` text
id
user_id
balance
updated_at
```

## rounds

``` text
id
round_number
server_seed_hash
server_seed
crash_multiplier
started_at
ended_at
status
```

## bets

``` text
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

``` text
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

``` text
id
minimum_bet
maximum_bet
starting_balance
game_speed
animation_speed
maintenance_mode
```

------------------------------------------------------------------------

# 16. Wallet Logic

Use integer virtual credits whenever possible.

Example:

``` text
Starting balance = 10,000

Bet = 100

Balance after bet = 9,900

Cash-out at 2.50x

Payout = 250

Final balance = 10,150
```

All balance changes should be processed server-side.

Never trust:

``` text
client_balance
client_payout
client_multiplier
```

------------------------------------------------------------------------

# 17. Anti-Cheat Architecture

The client is untrusted.

Never calculate final payout exclusively on the phone.

Server validates:

``` text
User
Round
Bet
Round state
Timestamp
Cash-out request
Crash status
Payout
Wallet balance
```

Protection mechanisms:

-   HTTPS
-   Authentication tokens
-   Request validation
-   Rate limiting
-   Server-side game state
-   Transaction IDs
-   Idempotent cash-out endpoint
-   Database transactions
-   Audit logs

------------------------------------------------------------------------

# 18. Python Project Structure

Recommended structure:

``` text
anti_gravity/
│
├── app/
│   ├── main.py
│   ├── config.py
│   │
│   ├── screens/
│   │   ├── home.py
│   │   ├── game.py
│   │   ├── history.py
│   │   ├── profile.py
│   │   └── settings.py
│   │
│   ├── widgets/
│   │   ├── spider.py
│   │   ├── multiplier.py
│   │   ├── cashout_button.py
│   │   ├── bet_panel.py
│   │   └── history_list.py
│   │
│   ├── services/
│   │   ├── api.py
│   │   ├── websocket.py
│   │   ├── auth.py
│   │   └── wallet.py
│   │
│   ├── assets/
│   │   ├── images/
│   │   ├── sounds/
│   │   └── fonts/
│   │
│   └── kv/
│       ├── main.kv
│       ├── game.kv
│       └── widgets.kv
│
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── wallet.py
│   │   ├── round.py
│   │   └── bet.py
│   │
│   ├── api/
│   │   ├── auth.py
│   │   ├── player.py
│   │   ├── game.py
│   │   └── fairness.py
│   │
│   └── game/
│       ├── engine.py
│       ├── fairness.py
│       ├── multiplier.py
│       └── state.py
│
├── tests/
│   ├── test_game.py
│   ├── test_fairness.py
│   ├── test_wallet.py
│   └── test_api.py
│
├── requirements.txt
├── buildozer.spec
├── README.md
└── .env
```

------------------------------------------------------------------------

# 19. Kivy Application Screens

## Splash Screen

``` text
ANTI-GRAVITY

A Spider Crash Adventure

Loading...
```

## Home

Buttons:

``` text
PLAY
HISTORY
PROFILE
SETTINGS
HOW TO PLAY
```

## Game

Components:

``` text
Top bar
Balance
Multiplier
Spider
Background
Bet controls
Cash-out
Round history
Status
```

## History

Display:

``` text
Round       Crash
#1021       1.42x
#1022       4.18x
#1023       1.09x
#1024       7.31x
```

## Profile

``` text
Username
Games Played
Total Virtual Credits
Wins
Losses
Best Cash-out
```

------------------------------------------------------------------------

# 20. Spider Animation

Use a sprite sheet or animated PNG.

Animation states:

``` text
idle
climbing
fast_climbing
warning
falling
crashed
```

Example:

``` python
class SpiderWidget(Widget):

    def update_position(self, multiplier):
        self.y = calculate_spider_height(multiplier)
```

Avoid tying animation directly to frame count.

Instead:

``` text
server game time
        ↓
multiplier
        ↓
animation position
```

This keeps all clients synchronized.

------------------------------------------------------------------------

# 21. Visual Design

Suggested identity:

### Primary Theme

Dark futuristic interface.

### Main Elements

``` text
Black / deep-space background
Neon purple
Electric cyan
Bright white text
Red crash warning
```

### Spider

Create an original futuristic spider character.

Possible design:

``` text
Cyber Spider
8 glowing legs
Neon body
Mechanical details
Energy trail
```

Do not copy Aviator's exact artwork, branding, logos, or proprietary
assets.

------------------------------------------------------------------------

# 22. Game Background

Possible environment:

``` text
Dark space
Floating platforms
Stars
Particles
Moon
Neon grid
Gravity field
```

The spider moves vertically through the environment.

At crash:

``` text
screen shake
spider falls
particles
sound
multiplier freezes
```

------------------------------------------------------------------------

# 23. Sound System

Sounds:

``` text
button_click.wav
round_start.wav
multiplier_tick.wav
cashout.wav
warning.wav
crash.wav
win.wav
```

Add settings:

``` text
Music ON/OFF
Sound Effects ON/OFF
Volume
```

------------------------------------------------------------------------

# 24. Animation Timing

The game should use real elapsed time.

Example:

``` python
start_time = time.monotonic()

elapsed = time.monotonic() - start_time

multiplier = multiplier_function(elapsed)
```

Do not use:

``` python
multiplier += 0.01
```

on every frame because different devices have different frame rates.

------------------------------------------------------------------------

# 25. Crash Synchronization

Server:

``` text
Round starts
      ↓
Server records start timestamp
      ↓
Client receives round information
      ↓
Client calculates display interpolation
      ↓
Server remains authoritative
```

The client should never be able to extend a round after the server
declares:

``` text
CRASHED
```

------------------------------------------------------------------------

# 26. Cash-Out Race Handling

This is a critical part.

Suppose:

``` text
Server crash = 2.50x
Client sends cash-out = 2.52x
```

The server must determine the valid result using its authoritative game
clock.

The endpoint should be transactional.

Concept:

``` python
BEGIN TRANSACTION

lock round

if round.status != "RUNNING":
    reject

if current_server_time >= crash_time:
    reject

record cashout

update wallet

mark bet as CASHED_OUT

COMMIT
```

This prevents double cash-outs and race-condition exploits.

------------------------------------------------------------------------

# 27. Authentication

For MVP:

``` text
Username
Password
```

Store only password hashes.

Recommended:

``` text
Argon2id
```

Do not store plaintext passwords.

For a later production version:

``` text
JWT access token
Refresh token
Device/session management
```

------------------------------------------------------------------------

# 28. Local Development Mode

Before building the server:

``` text
DEMO_MODE = True
```

This allows:

``` text
Kivy App
   ↓
Local Python Game Engine
   ↓
SQLite
```

This is useful for building the UI quickly.

------------------------------------------------------------------------

# 29. Production Mode

``` text
Android APK
     |
    HTTPS
     |
FastAPI
     |
PostgreSQL
```

Game engine runs on the backend.

------------------------------------------------------------------------

# 30. Admin Panel

Build a separate web dashboard.

Admin features:

``` text
Dashboard
Users
Rounds
Game statistics
Virtual-credit balances
Game settings
Server health
Error logs
Audit logs
Maintenance mode
```

Important:

The admin interface must not contain a hidden mechanism for manually
changing an individual round result.

Game outcomes should remain generated by the game engine.

------------------------------------------------------------------------

# 31. Analytics

Track:

``` text
DAU
MAU
Games played
Average session duration
Average rounds/session
Average virtual credits
Cash-out distribution
Crash distribution
App crashes
API latency
WebSocket disconnects
```

Do not collect unnecessary personal information.

------------------------------------------------------------------------

# 32. Responsible Game Design

Because crash mechanics can encourage repetitive play, add:

``` text
Session timer
Break reminder
Daily play statistics
Virtual-credit-only economy
No real-money deposits
No real-money withdrawals
```

Avoid manipulative mechanics such as secretly changing outcomes based on
a player's balance or behavior.

------------------------------------------------------------------------

# 33. Testing Strategy

## Unit Tests

Test:

``` text
Multiplier calculation
Crash calculation
Fairness verification
Wallet calculations
Cash-out validation
State transitions
```

## Integration Tests

Test:

``` text
App → API
API → Database
WebSocket → Client
Round → Bet → Cash-out
```

## Stress Tests

Simulate:

``` text
100 users
500 users
1,000 users
```

Measure:

``` text
CPU
RAM
database latency
WebSocket latency
```

------------------------------------------------------------------------

# 34. Security Tests

Test:

``` text
Duplicate cash-out
Replay requests
Invalid round ID
Invalid user ID
Modified multiplier
Modified payout
Negative bet
Huge bet
Expired token
Unauthorized admin request
```

Every failure should be rejected server-side.

------------------------------------------------------------------------

# 35. Offline Handling

If internet disconnects during a round:

``` text
DISCONNECTED
Reconnecting...
```

Do not assume that the player successfully cashed out.

The server's stored state remains authoritative.

After reconnection:

``` text
GET current round
GET player balance
GET latest transaction
```

Then synchronize the UI.

------------------------------------------------------------------------

# 36. Error Handling

Use user-friendly messages.

Example:

``` text
Connection lost.
Trying to reconnect...
```

Instead of:

``` text
WebSocketException: Connection reset by peer
```

Log technical errors separately.

------------------------------------------------------------------------

# 37. Logging

Backend logs:

``` text
INFO
WARNING
ERROR
SECURITY
AUDIT
```

Never log:

``` text
password
authentication secrets
private tokens
```

------------------------------------------------------------------------

# 38. API Security

Use:

``` text
HTTPS
JWT
Rate limiting
Input validation
CORS configuration
Secure headers
Request IDs
Audit logs
```

For development:

``` text
http://localhost
```

For production:

``` text
https://api.antigravity.example
```

Use your actual domain when deployed.

------------------------------------------------------------------------

# 39. Build Process

## Development

``` text
Python
   ↓
Kivy
   ↓
Local testing
```

## Android

``` text
Python
   ↓
Kivy
   ↓
Buildozer
   ↓
Android APK
```

Typical commands:

``` bash
buildozer init
```

Then configure:

``` text
buildozer.spec
```

Finally:

``` bash
buildozer android debug
```

For release:

``` bash
buildozer android release
```

A release APK/AAB must be signed with your own signing key.

------------------------------------------------------------------------

# 40. Buildozer Configuration

Important settings:

``` text
title = Anti-Gravity
package.name = antigravity
package.domain = org.yourcompany
source.include_exts = py,kv,png,jpg,jpeg,wav,mp3,json
requirements = python3,kivy,kivymd,requests,websocket-client
orientation = portrait
fullscreen = 0
```

Exact dependency versions should be locked after testing.

------------------------------------------------------------------------

# 41. Antigravity Development Workflow

Use Antigravity as the development assistant.

## Phase 1

Give it:

``` text
Create the Anti-Gravity Python/Kivy project structure.
```

## Phase 2

Implement:

``` text
Main menu
Game screen
Multiplier
Spider animation
Virtual wallet
```

## Phase 3

Implement:

``` text
FastAPI backend
SQLite
Game engine
```

## Phase 4

Implement:

``` text
WebSocket
Server synchronization
Cash-out validation
```

## Phase 5

Implement:

``` text
Fairness system
History
Profile
Settings
```

## Phase 6

Implement:

``` text
Tests
Security
Error handling
```

## Phase 7

Build:

``` text
APK
```

------------------------------------------------------------------------

# 42. Recommended Development Order

Do not build everything simultaneously.

### Sprint 1 --- UI

``` text
Splash
Home
Game
History
Settings
```

### Sprint 2 --- Local Game

``` text
Multiplier
Spider
Crash
Cash-out
Virtual wallet
```

### Sprint 3 --- Backend

``` text
FastAPI
Database
Authentication
Game API
```

### Sprint 4 --- Real-Time

``` text
WebSocket
Synchronization
Server game engine
```

### Sprint 5 --- Fairness

``` text
Seed
Hash
Crash generation
Verification
```

### Sprint 6 --- Security

``` text
Authentication
Rate limiting
Validation
Transactions
Audit logs
```

### Sprint 7 --- Testing

``` text
Unit
Integration
Load
Android device
```

### Sprint 8 --- APK

``` text
Buildozer
Debug APK
Release APK
Signing
Installation
```

------------------------------------------------------------------------

# 43. MVP Acceptance Criteria

The MVP is complete when:

-   App launches without crashing.
-   User can create/login to a local account.
-   User receives virtual credits.
-   User can select a virtual bet.
-   A round starts.
-   Multiplier increases smoothly.
-   Spider animation follows the multiplier.
-   Crash occurs at the server-generated result.
-   Cash-out works before crash.
-   Cash-out after crash is rejected.
-   Wallet updates exactly once.
-   Round history is saved.
-   Fairness verification works.
-   Reconnection works.
-   Invalid requests are rejected.
-   APK installs on Android.
-   Game works on multiple Android screen sizes.

------------------------------------------------------------------------

# 44. Suggested First Version

Keep Version 1 simple:

``` text
ANTI-GRAVITY

[ PLAY ]

Virtual Balance:
10,000

Bet:
[ - ] 100 [ + ]

          1.00x
           🕷️

       [ CASH OUT ]

Recent:
1.24x | 2.11x | 5.31x | 1.04x
```

Do not add unnecessary features until this works perfectly.

------------------------------------------------------------------------

# 45. Version Roadmap

## V0.1

``` text
UI prototype
```

## V0.2

``` text
Local game engine
```

## V0.3

``` text
Virtual wallet
```

## V0.4

``` text
FastAPI backend
```

## V0.5

``` text
WebSocket synchronization
```

## V0.6

``` text
Fairness verification
```

## V0.7

``` text
Authentication
```

## V0.8

``` text
Admin dashboard
```

## V0.9

``` text
Testing + optimization
```

## V1.0

``` text
Production-ready virtual-credit APK
```

------------------------------------------------------------------------

# 46. Final Architecture

``` text
                 ANDROID APK
                     |
             KIVY / KIVYMD
                     |
       +-------------+-------------+
       |                           |
   REST API                    WebSocket
       |                           |
       +-------------+-------------+
                     |
                  FASTAPI
                     |
          +----------+----------+
          |                     |
      GAME ENGINE           AUTH SYSTEM
          |                     |
          +----------+----------+
                     |
                 DATABASE
                     |
               PostgreSQL
```

Game engine:

``` text
Seed
 ↓
Hash
 ↓
Round
 ↓
Crash point
 ↓
Multiplier timeline
 ↓
Server state
 ↓
Cash-out validation
 ↓
Wallet transaction
 ↓
History
```

------------------------------------------------------------------------

# 47. Antigravity Build Prompt

Use the following as the initial project prompt in Antigravity:

``` text
Build a complete Python/Kivy Android application called "Anti-Gravity".

It is a virtual-credit crash arcade game inspired by the general crash-game mechanic.

The visual theme is a futuristic spider climbing/flying upward instead of an airplane.

Requirements:

1. Python + Kivy/KivyMD frontend.
2. FastAPI Python backend.
3. SQLite for development.
4. PostgreSQL-ready architecture.
5. WebSocket real-time game updates.
6. Server-authoritative game engine.
7. Virtual-credit wallet only.
8. No deposits, withdrawals, cryptocurrency, or real-money gambling.
9. Multiplier starts at 1.00x and continuously increases.
10. A server-generated crash point ends the round.
11. Player can cash out before the crash.
12. Server validates every cash-out.
13. Use database transactions for wallet changes.
14. Implement a cryptographically secure, auditable fairness mechanism.
15. Store round history.
16. Add user authentication.
17. Add profile screen.
18. Add settings.
19. Add sound effects.
20. Add futuristic spider animation.
21. Add reconnect handling.
22. Add comprehensive unit and integration tests.
23. Create a clean modular project structure.
24. Prepare the project for Android APK generation using Buildozer.
25. Never trust client-side multiplier, balance, payout, or crash state.
26. Add clear comments and documentation.
27. Make the UI responsive for Android phones.
28. Use original Anti-Gravity visual assets and branding rather than copying Aviator assets.

First create the project structure.

Then implement the UI.

Then implement the local game engine.

Then implement the backend.

Then connect the frontend to the backend.

Then implement fairness verification.

Then implement tests.

Finally prepare buildozer.spec and Android build instructions.

Do not skip testing between stages.
```

------------------------------------------------------------------------

# 48. Important Implementation Principle

The most important architectural rule is:

> **The phone displays the game; the server controls the game.**

Never allow the Android client to decide:

``` text
Crash point
Payout
Wallet balance
Cash-out success
Round result
```

Those must be authoritative server operations.

------------------------------------------------------------------------

# 49. Definition of Done

Anti-Gravity V1 is ready for release when:

``` text
[✓] Python project
[✓] Kivy/KivyMD UI
[✓] Spider animation
[✓] Multiplier engine
[✓] Crash engine
[✓] Virtual wallet
[✓] Cash-out
[✓] Round history
[✓] FastAPI backend
[✓] WebSocket
[✓] Database
[✓] Authentication
[✓] Fairness verification
[✓] Server authority
[✓] Security validation
[✓] Automated tests
[✓] Android optimization
[✓] Buildozer configuration
[✓] Debug APK
[✓] Release APK
```

This gives you a complete development path from **idea → Python code →
backend → game engine → Android APK**.
