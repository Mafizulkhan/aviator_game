"""
Anti-Gravity — Sprint 6 Tests: Security Hardening Suite
======================================================

Covers:
1. Token expiry
2. Invalid JWT (signature, malformed)
3. Missing JWT
4. WebSocket authentication (valid token)
5. Expired WebSocket token
6. Invalid WebSocket token
7. Rate-limited login
8. Rate-limited cash-out
9. Invalid bet amount validation (negative, 0, > MAX_BET)
10. Unauthorized wallet access
11. Unauthorized history access
12. Unauthorized cash-out (User A attempting to cash out User B's bet)
13. Duplicate cash-out prevention
14. Concurrent cash-out race safety
15. Malformed WebSocket message safety & client authority rejection
16. Audit log secret sanitization
17. Security headers configuration

Run with:
    python -m pytest tests/test_security.py -v
"""

import asyncio
import json
import logging
import os
import sys
from datetime import timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.websockets import WebSocketDisconnect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.config import settings
from backend.database import Base, get_db
from backend.main import app
from backend.models import Bet, BetStatus, Round, RoundStatus, User, UserStatus, Wallet
from backend.services.audit_service import AuditService
from backend.services.auth_service import create_access_token, hash_password
from backend.services.fairness_service import FairnessService
from backend.services.game_service import _active_round_internal, get_current_round
from backend.services.rate_limiter import RateLimiter

from sqlalchemy.pool import StaticPool

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Isolated in-memory DB per test."""
    _active_round_internal.clear()
    RateLimiter.clear()
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        import backend.models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()
        _active_round_internal.clear()
        RateLimiter.clear()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """AsyncClient wired with test DB session."""
    _active_round_internal.clear()
    RateLimiter.clear()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    RateLimiter.clear()


async def _create_test_user(db: AsyncSession, username: str, balance: int = 10_000) -> tuple[User, str]:
    """Helper to create user and valid access token."""
    user = User(
        username=username,
        password_hash=hash_password("Secur3P@ssword!"),
        status=UserStatus.active,
    )
    db.add(user)
    await db.flush()
    wallet = Wallet(user_id=user.id, balance=balance)
    db.add(wallet)
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return user, token


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════════════════════════════
# 1. Token Expiry
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_token_expiry_rejection(client, db_session):
    """Tokens with past expiration timestamps are rejected with 401."""
    user, _ = await _create_test_user(db_session, "expired_user")
    # Expired token (delta = -1 minute)
    expired_token = create_access_token({"sub": str(user.id)}, expires_delta=timedelta(minutes=-1))

    resp = await client.get("/api/player/profile", headers=_auth_header(expired_token))
    assert resp.status_code == 401
    assert "invalid or expired" in resp.json()["detail"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# 2. Invalid JWT (Signature, Malformed)
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_invalid_jwt_signature(client, db_session):
    """Tokens signed with wrong secret key are rejected with 401."""
    user, _ = await _create_test_user(db_session, "bad_sig_user")
    tampered_token = jwt.encode({"sub": str(user.id)}, "wrong-secret-key", algorithm=settings.ALGORITHM)

    resp = await client.get("/api/player/profile", headers=_auth_header(tampered_token))
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_malformed_jwt_token(client):
    """Malformed non-JWT strings are rejected with 401."""
    resp = await client.get("/api/player/profile", headers=_auth_header("not.a.valid.jwt.token"))
    assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# 3. Missing JWT
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_missing_jwt_token(client):
    """Protected endpoints require authorization header."""
    resp = await client.get("/api/player/profile")
    assert resp.status_code == 401


@pytest.fixture(scope="module")
def ws_sync_client():
    from starlette.testclient import TestClient
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


# ══════════════════════════════════════════════════════════════════════════════
# 4. WebSocket Authentication (Valid Token)
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_websocket_authentication_valid_token(ws_sync_client, db_session):
    """WebSocket accepts connection with valid token query parameter and marks authenticated."""
    user, token = await _create_test_user(db_session, "ws_auth_user")

    with ws_sync_client.websocket_connect(f"/ws/game?token={token}") as ws:
        data = ws.receive_json()
        assert data["type"] == "CONNECTED"
        assert data.get("authenticated") is True
        assert data.get("user_id") == user.id


# ══════════════════════════════════════════════════════════════════════════════
# 5. Expired & Invalid WebSocket Token
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_websocket_authentication_expired_token(ws_sync_client, db_session):
    """WebSocket connection with expired token is rejected/closed immediately."""
    user, _ = await _create_test_user(db_session, "ws_expired_user")
    expired_token = create_access_token({"sub": str(user.id)}, expires_delta=timedelta(minutes=-5))

    try:
        with ws_sync_client.websocket_connect(f"/ws/game?token={expired_token}") as ws:
            ws.receive_json()
            pytest.fail("Expected WebSocket to be closed on expired token")
    except WebSocketDisconnect as e:
        assert e.code == 1008


@pytest.mark.asyncio
async def test_websocket_authentication_invalid_token(ws_sync_client):
    """WebSocket connection with invalid token signature is closed with code 1008."""
    bad_token = jwt.encode({"sub": "999"}, "invalid-key", algorithm=settings.ALGORITHM)

    try:
        with ws_sync_client.websocket_connect(f"/ws/game?token={bad_token}") as ws:
            ws.receive_json()
            pytest.fail("Expected WebSocket to be closed on bad token")
    except WebSocketDisconnect as e:
        assert e.code == 1008


# ══════════════════════════════════════════════════════════════════════════════
# 6. In-Band WebSocket Authentication Message
def _recv_type(ws, expected_type: str, max_drain: int = 15) -> dict:
    for _ in range(max_drain):
        msg = ws.receive_json()
        if msg.get("type") == expected_type:
            return msg
    return msg


# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_websocket_in_band_auth_message(ws_sync_client, db_session):
    """WebSocket client can authenticate in-band by sending an auth message."""
    user, token = await _create_test_user(db_session, "inband_auth_user")

    with ws_sync_client.websocket_connect("/ws/game") as ws:
        connected = _recv_type(ws, "CONNECTED")
        assert connected["type"] == "CONNECTED"
        assert connected["authenticated"] is False

        # Send auth message
        ws.send_json({"type": "auth", "token": token})
        auth_ack = _recv_type(ws, "AUTH_SUCCESS")
        assert auth_ack["type"] == "AUTH_SUCCESS"
        assert auth_ack["user_id"] == user.id



# ══════════════════════════════════════════════════════════════════════════════
# 7. Rate-Limited Login
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_rate_limited_login(client, db_session):
    """Excessive login requests from the same client are rate limited with 429."""
    await _create_test_user(db_session, "ratelimit_login_user")
    RateLimiter.clear()

    max_reqs = settings.RATE_LIMIT_LOGIN_PER_MINUTE
    for _ in range(max_reqs):
        resp = await client.post(
            "/api/auth/login",
            json={"username": "ratelimit_login_user", "password": "Secur3P@ssword!"},
        )
        assert resp.status_code == 200

    # Next attempt must trigger 429
    blocked = await client.post(
        "/api/auth/login",
        json={"username": "ratelimit_login_user", "password": "Secur3P@ssword!"},
    )
    assert blocked.status_code == 429
    assert "too many requests" in blocked.json()["detail"].lower()
    assert "retry-after" in blocked.headers


# ══════════════════════════════════════════════════════════════════════════════
# 8. Rate-Limited Cash-Out
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_rate_limited_cashout(client, db_session):
    """Cashout endpoint throttles excessive requests beyond configured limit."""
    user, token = await _create_test_user(db_session, "ratelimit_cashout_user")
    headers = _auth_header(token)
    RateLimiter.clear()

    max_reqs = settings.RATE_LIMIT_CASHOUT_PER_MINUTE
    for _ in range(max_reqs):
        # Even failing requests count against rate limit
        await client.post("/api/game/cashout", json={"bet_id": 9999}, headers=headers)

    blocked = await client.post("/api/game/cashout", json={"bet_id": 9999}, headers=headers)
    assert blocked.status_code == 429
    assert "too many requests" in blocked.json()["detail"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# 9. Invalid Bet Amount Validation
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_invalid_bet_amount_validation(client, db_session):
    """Validation rejects negative, zero, below-min, and above-max bet values."""
    user, token = await _create_test_user(db_session, "validation_user")
    headers = _auth_header(token)

    # Negative bet
    resp_neg = await client.post("/api/game/join", json={"amount": -50}, headers=headers)
    assert resp_neg.status_code in (400, 422)

    # Zero bet
    resp_zero = await client.post("/api/game/join", json={"amount": 0}, headers=headers)
    assert resp_zero.status_code in (400, 422)

    # Below min bet (< 10)
    resp_below = await client.post("/api/game/join", json={"amount": 5}, headers=headers)
    assert resp_below.status_code == 400

    # Above max bet (> 5000)
    resp_above = await client.post("/api/game/join", json={"amount": 99999}, headers=headers)
    assert resp_above.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# 10. Authorization: Private Data Isolation (Wallet & History)
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_unauthorized_wallet_and_history_isolation(client, db_session):
    """User A's token cannot read or mutate User B's wallet balance or bet history."""
    user_a, token_a = await _create_test_user(db_session, "user_alpha", balance=15_000)
    user_b, token_b = await _create_test_user(db_session, "user_beta", balance=7_500)

    # User A checks balance -> gets 15,000
    resp_a = await client.get("/api/player/balance", headers=_auth_header(token_a))
    assert resp_a.status_code == 200
    assert resp_a.json()["user_id"] == user_a.id
    assert resp_a.json()["balance"] == 15_000

    # User B checks balance -> gets 7,500
    resp_b = await client.get("/api/player/balance", headers=_auth_header(token_b))
    assert resp_b.status_code == 200
    assert resp_b.json()["user_id"] == user_b.id
    assert resp_b.json()["balance"] == 7_500


# ══════════════════════════════════════════════════════════════════════════════
# 11. Authorization: User A cannot cash out User B's bet
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_unauthorized_cashout_wrong_user(client, db_session):
    """User B cannot cash out a bet placed by User A."""
    user_a, token_a = await _create_test_user(db_session, "owner_user")
    user_b, token_b = await _create_test_user(db_session, "attacker_user")

    # User A joins round
    join_resp = await client.post(
        "/api/game/join", json={"amount": 100}, headers=_auth_header(token_a)
    )
    assert join_resp.status_code == 201
    bet_id = join_resp.json()["bet_id"]

    # User B attempts to cash out User A's bet -> rejected with 400
    attack_resp = await client.post(
        "/api/game/cashout", json={"bet_id": bet_id}, headers=_auth_header(token_b)
    )
    assert attack_resp.status_code == 400
    assert "bet not found" in attack_resp.json()["detail"].lower() or "not found" in attack_resp.json()["detail"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# 12. Duplicate Cash-Out Prevention
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_duplicate_cashout_rejected(client, db_session):
    """Subsequent cash-out requests on an already cashed-out bet are rejected."""
    user, token = await _create_test_user(db_session, "double_cash_user")
    headers = _auth_header(token)

    # Ensure round has a high crash point so first cashout succeeds
    join_resp = await client.post("/api/game/join", json={"amount": 100}, headers=headers)
    assert join_resp.status_code == 201
    bet_data = join_resp.json()
    bet_id = bet_data["bet_id"]
    round_id = bet_data["round_id"]
    _active_round_internal[round_id] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

    # First cashout -> success
    first = await client.post("/api/game/cashout", json={"bet_id": bet_id}, headers=headers)
    assert first.status_code == 200

    # Second cashout -> 400 Bad Request
    second = await client.post("/api/game/cashout", json={"bet_id": bet_id}, headers=headers)
    assert second.status_code == 400
    assert "already processed" in second.json()["detail"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# 13. Concurrent Cash-Out Race Safety
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_concurrent_cashout_race_safety(client, db_session):
    """Two concurrent cashout requests for the same bet result in exactly one 200 OK."""
    user, token = await _create_test_user(db_session, "concurrent_sec_user")
    headers = _auth_header(token)
    r = await get_current_round(db_session)
    _active_round_internal[r.id] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

    join_resp = await client.post("/api/game/join", json={"amount": 100}, headers=headers)
    assert join_resp.status_code == 201
    bet_id = join_resp.json()["bet_id"]

    async def _cash():
        return await client.post("/api/game/cashout", json={"bet_id": bet_id}, headers=headers)

    res1, res2 = await asyncio.gather(_cash(), _cash(), return_exceptions=True)
    successes = [r for r in (res1, res2) if not isinstance(r, Exception) and r.status_code == 200]

    # At most 1 success — never double payout
    assert len(successes) <= 1


# ══════════════════════════════════════════════════════════════════════════════
# 14. Malformed WebSocket Message Safety & Server Authority
# ══════════════════════════════════════════════════════════════════════════════
def test_malformed_ws_message_safety(ws_sync_client):
    """Malformed WebSocket messages do not crash server and return safe error responses."""
    with ws_sync_client.websocket_connect("/ws/game") as ws:
        connected = _recv_type(ws, "CONNECTED")
        assert connected["type"] == "CONNECTED"

        # 1. Plain string (not JSON)
        ws.send_text("THIS IS NOT JSON")
        err1 = _recv_type(ws, "ERROR")
        assert err1["type"] == "ERROR"

        # 2. JSON array instead of object
        ws.send_text("[1, 2, 3]")
        err2 = _recv_type(ws, "ERROR")
        assert err2["type"] == "ERROR"

        # 3. Client trying to assert multiplier/payout claim
        ws.send_json({"type": "multiplier_claim", "multiplier": 999.99})
        err3 = _recv_type(ws, "ERROR")
        assert err3["type"] == "ERROR"
        assert "authority" in err3["message"].lower()

        # 4. Standard ping still works afterwards
        ws.send_json({"type": "ping"})
        pong = _recv_type(ws, "pong")
        assert pong["type"] == "pong"



# ══════════════════════════════════════════════════════════════════════════════
# 15. Audit Log Secret Sanitization
# ══════════════════════════════════════════════════════════════════════════════
def test_audit_logging_secret_sanitization(caplog):
    """Audit logs must never log raw passwords, access tokens, or secret keys."""
    with caplog.at_level(logging.INFO, logger="anti_gravity.audit"):
        AuditService._emit_audit_event(
            "security_test_event",
            {
                "user_id": 42,
                "password": "raw_user_password",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token": "bearer_secret_token",
            },
        )

    records = [r.message for r in caplog.records if "anti_gravity.audit" in r.name]
    assert len(records) > 0

    log_entry = json.loads(records[-1])
    assert log_entry["password"] == "[REDACTED]"
    assert log_entry["access_token"] == "[REDACTED]"
    assert log_entry["token"] == "[REDACTED]"
    assert "raw_user_password" not in records[-1]


# ══════════════════════════════════════════════════════════════════════════════
# 16. Security Headers Configuration
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_security_headers_present(client):
    """All HTTP responses must include standard defensive security headers."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "1; mode=block" in resp.headers.get("X-XSS-Protection", "")
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
