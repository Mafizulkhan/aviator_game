# Zero Gravity

> **Cyber Spider Crash Multiplier Game**  
> *The phone displays the game. The server controls the game.*

Zero Gravity is a high-octane, provably-fair crash arcade game featuring a cyber spider ascending through deep space. Built with a **Flutter (Dart)** Android mobile application and a high-performance **FastAPI (Python)** authoritative backend, backed by SQLite (development) and PostgreSQL (production).

---

## Architecture Overview

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

- **Client**: Untrusted Flutter player application. Never computes crash multipliers, settlements, or balances.
- **Backend**: Fully authoritative FastAPI server running the real-time game loop, HMAC-SHA256 provably fair commit/reveal engine, and atomic race-safe wallet transactions.
- **Admin**: Dedicated role-based ops console (SUPER_ADMIN, ADMIN, OPERATOR, AUDITOR, SUPPORT) with audit logging.
- **Economy**: 100% Virtual credits only (no real-money wagering, deposits, or withdrawals).

---

## Repository Structure

```text
zero_gravity/
├── mobile/                   # Flutter + Dart Android Player App
│   ├── android/              # Native Android configuration & manifests
│   ├── lib/                  # Application code (Clean Architecture)
│   │   ├── config/           # Build-time environment config
│   │   ├── core/             # Auth, networking, error handling & formatters
│   │   ├── models/           # Domain models (User, Wallet, Round, Bet, Fairness)
│   │   ├── repositories/     # Auth, Player, Game & Fairness repositories
│   │   ├── features/         # Splash, Auth, Home, Game, History, Profile, Settings, Tutorial
│   │   ├── widgets/          # Cyber Spider, Multiplier, Cashout Button, Bet Panel, HUD
│   │   └── theme/            # Zero Gravity Cyber Dark Theme
│   ├── test/                 # Flutter unit & widget tests
│   └── pubspec.yaml          # Flutter dependencies
│
├── backend/                  # FastAPI Authoritative Backend
│   ├── api/                  # REST & WebSocket endpoints (Auth, Player, Game, Fairness, Admin)
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic v2 validation schemas
│   ├── services/             # Auth, Game, Wallet, Fairness & Audit services
│   ├── ws/                   # WebSocket connection manager & server game loop
│   ├── config.py             # Server settings
│   ├── database.py           # Async SQLite / PostgreSQL session engine
│   └── main.py               # Application entry point & lifespan manager
│
├── admin/                    # Admin Web Application
│   ├── frontend/             # Ops Dashboard UI (HTML5, Vanilla CSS, JS)
│   └── README.md             # Admin operational manual
│
├── tests/                    # Comprehensive backend test suite (202 tests)
├── .github/workflows/        # CI/CD Workflows (Flutter Android CI & Backend Tests)
├── .env.example              # Template environment configuration
└── PROJECT_AUDIT_REPORT.md   # Complete codebase audit and verification report
```

---

## Quick Start

### 1. Backend Setup

```bash
cd anti_gravity
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```
- API Documentation (Swagger): `http://localhost:8000/docs`
- Admin Operations Console: `http://localhost:8000/admin`

### 2. Run Backend Tests

```bash
cd anti_gravity
python -m pytest -v --tb=short
```

### 3. Mobile App (Flutter)

```bash
cd mobile
flutter pub get
flutter test
flutter run
```

---

## Security & Fairness Principles

1. **Provably Fair**: Crash points are determined deterministically using `HMAC-SHA256(server_seed, round_id)`. The SHA-256 commitment is published *before* round start, and the server seed is revealed post-crash.
2. **Race Condition Protection**: Cash-out requests are processed atomically against authoritative server timestamps and locked wallet transactions.
3. **No Secrets in APK**: All JWT signing secrets, database credentials, and unrevealed seeds reside strictly on the server.
