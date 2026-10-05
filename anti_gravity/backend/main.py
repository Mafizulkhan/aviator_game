"""
Anti-Gravity Backend — FastAPI Application
Entry point for the backend server.

Start with:
    uvicorn backend.main:app --reload --port 8000

Swagger UI:  http://localhost:8000/docs
ReDoc:       http://localhost:8000/redoc
"""

import sys
import os

# Ensure project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.services.game_service import _active_round_internal
from backend.api.auth     import router as auth_router
from backend.api.player   import router as player_router
from backend.api.game     import router as game_router
from backend.api.fairness import router as fairness_router
from backend.api.audit    import router as audit_router
from backend.api.websocket import router as websocket_router
from backend.ws.game_loop import game_loop
from backend.ws.connection_manager import manager
from backend.schemas import HealthResponse


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise the in-memory active-round cache
    _active_round_internal.clear()
    # Create database tables on first run
    await init_db()
    # Start the server-authoritative background game loop
    game_loop.start()
    yield
    # Clean shutdown
    await game_loop.stop_async()
    await manager.clean_shutdown()
    from backend.database import engine
    await engine.dispose()


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Anti-Gravity API",
    description=(
        "Backend for the Anti-Gravity virtual-credit crash arcade game. "
        "Virtual credits only — no deposits, no withdrawals, no real money."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# ── Security Headers Middleware ────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ── CORS (allow Kivy/web clients on localhost during dev) ─────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(player_router)
app.include_router(game_router)
app.include_router(fairness_router)
app.include_router(audit_router)
app.include_router(websocket_router)


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/api/health", response_model=HealthResponse, tags=["health"])
async def health():
    """Server health check — returns ok + version."""
    return HealthResponse(status="ok", version="0.2.0", mode="demo")
