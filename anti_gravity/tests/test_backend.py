"""
Anti-Gravity Backend — Integration Tests (Sprint 3)
Tests every API endpoint using httpx AsyncClient against a real SQLite in-memory DB.

Run with:
    python -m pytest tests/test_backend.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.database import Base, get_db
from backend.main import app
from backend.services.game_service import _active_round_internal


# ── Test DB setup (in-memory SQLite, isolated per test) ───────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


from sqlalchemy.pool import StaticPool


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a fresh in-memory SQLite DB for each test."""
    # Ensure no stale in-memory round seeds from a previous test
    _active_round_internal.clear()

    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        import backend.models  # noqa: F401 — register models with Base
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()
        # Clean up seeds that belong to this DB's rounds
        _active_round_internal.clear()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """AsyncClient wired to the FastAPI app with the test DB session."""
    _active_round_internal.clear()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    _active_round_internal.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _register(client: AsyncClient, username="testuser", password="testpass123"):
    resp = await client.post("/api/auth/register", json={"username": username, "password": password})
    return resp


async def _login(client: AsyncClient, username="testuser", password="testpass123"):
    resp = await client.post("/api/auth/login", json={"username": username, "password": password})
    return resp


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ════════════════════════════════════════════════════════════════════════════════
# Health
# ════════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.2.0"
    assert data["mode"] == "demo"


# ════════════════════════════════════════════════════════════════════════════════
# Auth — Register
# ════════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_register_success(client):
    resp = await _register(client)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["username"] == "testuser"
    assert data["balance"] == 10_000   # starting balance


@pytest.mark.asyncio
async def test_register_duplicate_username(client):
    await _register(client)
    resp = await _register(client)   # same username
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password(client):
    resp = await client.post("/api/auth/register", json={"username": "user1", "password": "abc"})
    assert resp.status_code == 422   # validation error


@pytest.mark.asyncio
async def test_register_invalid_username(client):
    resp = await client.post("/api/auth/register", json={"username": "u$er!", "password": "validpass"})
    assert resp.status_code == 422


# ════════════════════════════════════════════════════════════════════════════════
# Auth — Login
# ════════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_login_success(client):
    await _register(client)
    resp = await _login(client)
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await _register(client)
    resp = await client.post("/api/auth/login", json={"username": "testuser", "password": "WRONG"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    resp = await client.post("/api/auth/login", json={"username": "nobody", "password": "pass"})
    assert resp.status_code == 401


# ════════════════════════════════════════════════════════════════════════════════
# Auth — Protected routes reject unauthenticated requests
# ════════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_unauthorized_profile(client):
    resp = await client.get("/api/player/profile")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthorized_balance(client):
    resp = await client.get("/api/player/balance")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthorized_game_current(client):
    resp = await client.get("/api/game/current")
    assert resp.status_code == 401


# ════════════════════════════════════════════════════════════════════════════════
# Player — Profile & Balance
# ════════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_player_profile(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    resp = await client.get("/api/player/profile", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testuser"
    assert data["games_played"] == 0
    assert data["wins"] == 0
    assert data["losses"] == 0


@pytest.mark.asyncio
async def test_player_balance(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    resp = await client.get("/api/player/balance", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["balance"] == 10_000


@pytest.mark.asyncio
async def test_player_history_empty(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    resp = await client.get("/api/player/history", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


# ════════════════════════════════════════════════════════════════════════════════
# Game — Current Round
# ════════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_game_current_round(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    resp = await client.get("/api/game/current", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["round_number"] >= 1
    assert data["status"] in ("pending", "running")
    assert "server_seed_hash" in data
    assert len(data["server_seed_hash"]) == 64


# ════════════════════════════════════════════════════════════════════════════════
# Game — Join (Bet)
# ════════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_join_round_success(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    curr = await client.get("/api/game/current", headers=_auth(token))
    _active_round_internal[curr.json()["round_id"]] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    resp = await client.post("/api/game/join", json={"amount": 100}, headers=_auth(token))
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == 100
    assert data["balance_after"] == 9_900   # 10000 - 100
    assert data["status"] == "active"
    assert "bet_id" in data


@pytest.mark.asyncio
async def test_join_round_insufficient_balance(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    curr = await client.get("/api/game/current", headers=_auth(token))
    _active_round_internal[curr.json()["round_id"]] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    resp = await client.post("/api/game/join", json={"amount": 99999}, headers=_auth(token))
    assert resp.status_code == 400
    assert "balance" in resp.json()["detail"].lower() or "bet" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_join_round_below_min_bet(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    curr = await client.get("/api/game/current", headers=_auth(token))
    _active_round_internal[curr.json()["round_id"]] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    resp = await client.post("/api/game/join", json={"amount": 1}, headers=_auth(token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_join_round_zero_bet(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    resp = await client.post("/api/game/join", json={"amount": 0}, headers=_auth(token))
    assert resp.status_code == 422   # pydantic gt=0


@pytest.mark.asyncio
async def test_join_round_negative_bet(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    resp = await client.post("/api/game/join", json={"amount": -100}, headers=_auth(token))
    assert resp.status_code == 422   # pydantic gt=0


@pytest.mark.asyncio
async def test_no_duplicate_bet_same_round(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    curr = await client.get("/api/game/current", headers=_auth(token))
    _active_round_internal[curr.json()["round_id"]] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    resp1 = await client.post("/api/game/join", json={"amount": 100}, headers=_auth(token))
    assert resp1.status_code == 201
    resp2 = await client.post("/api/game/join", json={"amount": 100}, headers=_auth(token))
    assert resp2.status_code == 400
    assert "already" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_balance_decreases_after_bet(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    curr = await client.get("/api/game/current", headers=_auth(token))
    _active_round_internal[curr.json()["round_id"]] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    join_resp = await client.post("/api/game/join", json={"amount": 500}, headers=_auth(token))
    assert join_resp.status_code == 201
    bal_resp = await client.get("/api/player/balance", headers=_auth(token))
    assert bal_resp.json()["balance"] == 9_500


# ════════════════════════════════════════════════════════════════════════════════
# Game — Cash Out
# ════════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_cashout_success(client):
    reg = await _register(client)
    token = reg.json()["access_token"]

    # Join
    join_resp = await client.post("/api/game/join", json={"amount": 100}, headers=_auth(token))
    assert join_resp.status_code == 201
    bet_id = join_resp.json()["bet_id"]
    round_id = join_resp.json()["round_id"]
    _active_round_internal[round_id] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

    # Cash out immediately (multiplier will be 1.00x, payout = 100)
    cash_resp = await client.post("/api/game/cashout", json={"bet_id": bet_id}, headers=_auth(token))
    assert cash_resp.status_code == 200
    data = cash_resp.json()
    assert data["bet_id"] == bet_id
    assert data["cashout_multiplier"] >= 1.0
    assert data["payout"] >= 100
    assert data["status"] == "cashed_out"


@pytest.mark.asyncio
async def test_no_double_cashout(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    join_resp = await client.post("/api/game/join", json={"amount": 100}, headers=_auth(token))
    assert join_resp.status_code == 201, f"Join failed: {join_resp.json()}"
    bet_id = join_resp.json()["bet_id"]
    round_id = join_resp.json()["round_id"]
    _active_round_internal[round_id] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

    await client.post("/api/game/cashout", json={"bet_id": bet_id}, headers=_auth(token))
    resp2 = await client.post("/api/game/cashout", json={"bet_id": bet_id}, headers=_auth(token))
    assert resp2.status_code == 400
    assert "already" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cashout_wrong_user(client):
    """User B cannot cash out User A's bet."""
    reg_a = await _register(client, username="user_a")
    reg_b = await _register(client, username="user_b")
    token_a = reg_a.json()["access_token"]
    token_b = reg_b.json()["access_token"]

    join_resp = await client.post("/api/game/join", json={"amount": 100}, headers=_auth(token_a))
    bet_id = join_resp.json()["bet_id"]
    round_id = join_resp.json()["round_id"]
    _active_round_internal[round_id] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

    resp = await client.post("/api/game/cashout", json={"bet_id": bet_id}, headers=_auth(token_b))
    assert resp.status_code == 400   # "Bet not found" for user_b


@pytest.mark.asyncio
async def test_balance_increases_after_cashout(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    join_resp = await client.post("/api/game/join", json={"amount": 100}, headers=_auth(token))
    assert join_resp.status_code == 201, f"Join failed: {join_resp.json()}"
    bet_id = join_resp.json()["bet_id"]
    round_id = join_resp.json()["round_id"]
    _active_round_internal[round_id] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

    cash_resp = await client.post("/api/game/cashout", json={"bet_id": bet_id}, headers=_auth(token))
    assert cash_resp.status_code == 200, f"Cashout failed: {cash_resp.json()}"
    payout = cash_resp.json()["payout"]
    balance_after = cash_resp.json()["balance_after"]
    assert balance_after == 9_900 + payout   # 10000 - 100 + payout


# ════════════════════════════════════════════════════════════════════════════════
# Game — History
# ════════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_game_history_endpoint(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    resp = await client.get("/api/game/history", headers=_auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ════════════════════════════════════════════════════════════════════════════════
# Fairness
# ════════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_fairness_info_active_round(client):
    """During an active round, only the seed_hash is revealed."""
    reg = await _register(client)
    token = reg.json()["access_token"]

    # Get current round to get its ID
    round_resp = await client.get("/api/game/current", headers=_auth(token))
    if round_resp.json()["status"] == "crashed":
        round_resp = await client.get("/api/game/current", headers=_auth(token))
    round_id = round_resp.json()["round_id"]

    resp = await client.get(f"/api/fairness/{round_id}", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    if data["status"] in ("pending", "running"):
        assert data["server_seed"] is None            # not revealed yet
        assert data["crash_multiplier"] is None       # not revealed yet
    assert len(data["server_seed_hash"]) == 64


@pytest.mark.asyncio
async def test_fairness_verify_requires_crashed_round(client):
    """Verify endpoint rejects active rounds."""
    reg = await _register(client)
    token = reg.json()["access_token"]
    round_resp = await client.get("/api/game/current", headers=_auth(token))
    round_id = round_resp.json()["round_id"]

    resp = await client.get(f"/api/fairness/{round_id}/verify", headers=_auth(token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_fairness_404_unknown_round(client):
    reg = await _register(client)
    token = reg.json()["access_token"]
    resp = await client.get("/api/fairness/99999", headers=_auth(token))
    assert resp.status_code == 404
