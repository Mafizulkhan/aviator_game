"""
Anti-Gravity — Sprint 5 Tests: Fairness, Verification, Statistics & Audit API
=============================================================================

Covers:
1. Server seed generation (256-bit cryptographically secure)
2. Cryptographic commitment generation (SHA-256)
3. HMAC determinism
4. Different round IDs producing independent results
5. Verification of valid round
6. Detection of modified seed
7. Detection of modified round ID
8. Detection of modified crash result
9. Secret visibility before / after round completion
10. Fairness statistics endpoint (summary + distribution buckets)
11. Audit endpoint (round inspection, bet summaries, verification status)
12. Audit record immutability & structured non-sensitive event logging

Run with:
    python -m pytest tests/test_fairness_audit.py -v
"""

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.engine.game_engine import FairnessEngine
from backend.database import Base, get_db
from backend.main import app
from backend.models import Bet, BetStatus, Round, RoundStatus, User, UserStatus, Wallet
from backend.services.audit_service import AuditService, audit_logger
from backend.services.fairness_service import FairnessService
from backend.services.game_service import _active_round_internal

from sqlalchemy.pool import StaticPool

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Isolated in-memory DB per test."""
    _active_round_internal.clear()
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


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """AsyncClient wired with test DB session."""
    _active_round_internal.clear()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _register_auth_user(client: AsyncClient, username: str = "fair_user") -> dict:
    resp = await client.post(
        "/api/auth/register",
        json={"username": username, "password": "FairPassword123!"},
    )
    if resp.status_code == 409:
        resp = await client.post(
            "/api/auth/login",
            json={"username": username, "password": "FairPassword123!"},
        )
    return resp.json()


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════════════════════════════
# 1. Server Seed Generation
# ══════════════════════════════════════════════════════════════════════════════
def test_server_seed_generation():
    """Verify server seeds are 256-bit (64 hex characters) and high entropy."""
    seeds = {FairnessService.generate_seed() for _ in range(100)}
    assert len(seeds) == 100, "Duplicate seed generated in 100 iterations"
    for s in seeds:
        assert len(s) == 64
        int(s, 16)  # must be valid hex string


# ══════════════════════════════════════════════════════════════════════════════
# 2. Commitment Generation
# ══════════════════════════════════════════════════════════════════════════════
def test_commitment_generation():
    """Verify SHA-256 commitment generation matches cryptographic standard."""
    seed = FairnessService.generate_seed()
    commitment = FairnessService.hash_seed(seed)
    expected = hashlib.sha256(seed.encode()).hexdigest()
    assert commitment == expected
    assert len(commitment) == 64


# ══════════════════════════════════════════════════════════════════════════════
# 3. HMAC / Derivation Determinism
# ══════════════════════════════════════════════════════════════════════════════
def test_hmac_determinism():
    """Given identical seed and round identifier, output must be perfectly deterministic."""
    seed = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
    round_id = 42

    result1 = FairnessService.calculate_crash_point(seed, round_id)
    result2 = FairnessService.calculate_crash_point(seed, round_id)
    result3 = FairnessService.calculate_crash_point(seed, round_id)

    assert result1 == result2 == result3
    assert result1 >= 1.00


# ══════════════════════════════════════════════════════════════════════════════
# 4. Different Round IDs Produce Independent Results
# ══════════════════════════════════════════════════════════════════════════════
def test_different_round_ids_produce_independent_results():
    """Using the same seed across different round numbers produces varied results."""
    seed = FairnessService.generate_seed()
    results = [FairnessService.calculate_crash_point(seed, round_num) for round_num in range(1, 50)]
    assert len(set(results)) > 1, "All round IDs produced identical crash points"


# ══════════════════════════════════════════════════════════════════════════════
# 5. Verification of Valid Round
# ══════════════════════════════════════════════════════════════════════════════
def test_verification_of_valid_round():
    """Valid completed round with authentic seed and crash point passes verification."""
    seed = FairnessService.generate_seed()
    seed_hash = FairnessService.hash_seed(seed)
    round_num = 101
    crash_mult = FairnessService.calculate_crash_point(seed, round_num)

    assert FairnessService.verify_round(seed, seed_hash, round_num, crash_mult) is True


# ══════════════════════════════════════════════════════════════════════════════
# 6. Detection of Modified Seed
# ══════════════════════════════════════════════════════════════════════════════
def test_detection_of_modified_seed():
    """Tampering with even 1 character in the revealed seed fails verification."""
    seed = FairnessService.generate_seed()
    seed_hash = FairnessService.hash_seed(seed)
    round_num = 102
    crash_mult = FairnessService.calculate_crash_point(seed, round_num)

    # Flip the first hex char
    tampered_char = "0" if seed[0] != "0" else "1"
    tampered_seed = tampered_char + seed[1:]

    assert FairnessService.verify_round(tampered_seed, seed_hash, round_num, crash_mult) is False


# ══════════════════════════════════════════════════════════════════════════════
# 7. Detection of Modified Round ID
# ══════════════════════════════════════════════════════════════════════════════
def test_detection_of_modified_round_id():
    """Changing the round number fails verification."""
    seed = FairnessService.generate_seed()
    seed_hash = FairnessService.hash_seed(seed)
    round_num = 103
    crash_mult = FairnessService.calculate_crash_point(seed, round_num)

    tampered_round = round_num + 1
    while FairnessService.calculate_crash_point(seed, tampered_round) == crash_mult:
        tampered_round += 1

    assert FairnessService.verify_round(seed, seed_hash, tampered_round, crash_mult) is False


# ══════════════════════════════════════════════════════════════════════════════
# 8. Detection of Modified Crash Result
# ══════════════════════════════════════════════════════════════════════════════
def test_detection_of_modified_crash_result():
    """Tampering with the authoritative crash multiplier fails verification."""
    seed = FairnessService.generate_seed()
    seed_hash = FairnessService.hash_seed(seed)
    round_num = 104
    crash_mult = FairnessService.calculate_crash_point(seed, round_num)

    assert FairnessService.verify_round(seed, seed_hash, round_num, crash_mult + 0.50) is False
    assert FairnessService.verify_round(seed, seed_hash, round_num, 1.00 if crash_mult != 1.00 else 2.00) is False


# ══════════════════════════════════════════════════════════════════════════════
# 9. Secret Visibility Before & After Round Completion
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_secret_visibility_lifecycle(client, db_session):
    """
    Secrets (server_seed, crash_multiplier) MUST NOT be exposed while round is active.
    Once crashed, secrets are revealed and verify endpoint returns 200 with verified=True.
    """
    user_data = await _register_auth_user(client, "visibility_user")
    token = user_data["access_token"]
    headers = _auth_header(token)

    # 1. Create a pending round
    seed = FairnessService.generate_seed()
    seed_hash = FairnessService.hash_seed(seed)
    round_row = Round(
        round_number=501,
        server_seed_hash=seed_hash,
        server_seed=None,
        crash_multiplier=None,
        status=RoundStatus.pending,
    )
    db_session.add(round_row)
    await db_session.commit()
    await db_session.refresh(round_row)
    round_id = round_row.id

    # Check fairness info while pending
    resp = await client.get(f"/api/fairness/{round_id}", headers=headers)
    assert resp.status_code == 200
    info = resp.json()
    assert info["server_seed"] is None
    assert info["crash_multiplier"] is None
    assert info["server_seed_hash"] == seed_hash
    assert info["status"] == "pending"

    # Verify attempt while pending must fail
    v_resp = await client.get(f"/api/fairness/{round_id}/verify", headers=headers)
    assert v_resp.status_code == 400
    assert "not crashed" in v_resp.json()["detail"].lower()

    # 2. Transition to running
    round_row.status = RoundStatus.running
    round_row.started_at = datetime.now(timezone.utc)
    await db_session.commit()

    resp = await client.get(f"/api/fairness/{round_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["server_seed"] is None
    assert resp.json()["crash_multiplier"] is None

    v_resp = await client.get(f"/api/fairness/{round_id}/verify", headers=headers)
    assert v_resp.status_code == 400

    # 3. Transition to crashed (reveal secrets)
    crash_mult = FairnessService.calculate_crash_point(seed, round_row.round_number)
    round_row.status = RoundStatus.crashed
    round_row.server_seed = seed
    round_row.crash_multiplier = crash_mult
    round_row.ended_at = datetime.now(timezone.utc)
    await db_session.commit()

    # Now fairness info exposes revealed seed and crash multiplier
    resp = await client.get(f"/api/fairness/{round_id}", headers=headers)
    assert resp.status_code == 200
    crashed_info = resp.json()
    assert crashed_info["server_seed"] == seed
    assert crashed_info["crash_multiplier"] == crash_mult
    assert crashed_info["status"] == "crashed"

    # Now verify endpoint succeeds
    v_resp = await client.get(f"/api/fairness/{round_id}/verify", headers=headers)
    assert v_resp.status_code == 200
    v_data = v_resp.json()
    assert v_data["verified"] is True
    assert v_data["server_seed"] == seed
    assert v_data["server_seed_hash"] == seed_hash
    assert v_data["crash_multiplier"] == crash_mult


# ══════════════════════════════════════════════════════════════════════════════
# 10. Fairness Statistics API
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_fairness_statistics_empty(client):
    """Stats endpoint handles empty database gracefully."""
    user_data = await _register_auth_user(client, "stats_user_1")
    token = user_data["access_token"]
    resp = await client.get("/api/fairness/stats", headers=_auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_completed_rounds"] == 0
    assert data["min_crash_multiplier"] is None
    assert data["max_crash_multiplier"] is None
    assert data["average_crash_multiplier"] is None
    assert data["median_crash_multiplier"] is None
    assert len(data["distribution_buckets"]) == 6


@pytest.mark.asyncio
async def test_fairness_statistics_populated(client, db_session):
    """Stats endpoint computes exact min, max, avg, median, and bucket distribution."""
    user_data = await _register_auth_user(client, "stats_user_2")
    token = user_data["access_token"]

    multipliers = [1.10, 1.30, 1.75, 2.50, 7.50, 15.00]
    for idx, mult in enumerate(multipliers, start=1):
        seed = FairnessService.generate_seed()
        seed_hash = FairnessService.hash_seed(seed)
        r = Round(
            round_number=idx,
            server_seed_hash=seed_hash,
            server_seed=seed,
            crash_multiplier=mult,
            status=RoundStatus.crashed,
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
        )
        db_session.add(r)
    await db_session.commit()

    resp = await client.get("/api/fairness/stats", headers=_auth_header(token))
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_completed_rounds"] == 6
    assert data["min_crash_multiplier"] == 1.10
    assert data["max_crash_multiplier"] == 15.00
    # Average: (1.10 + 1.30 + 1.75 + 2.50 + 7.50 + 15.00) / 6 = 29.15 / 6 = 4.86
    assert data["average_crash_multiplier"] == 4.86
    # Median: (1.75 + 2.50) / 2 = 2.125 -> 2.12
    assert data["median_crash_multiplier"] == 2.12

    buckets = {b["bucket"]: b for b in data["distribution_buckets"]}
    assert buckets["< 1.20x"]["count"] == 1
    assert buckets["1.20x–1.49x"]["count"] == 1
    assert buckets["1.50x–1.99x"]["count"] == 1
    assert buckets["2.00x–4.99x"]["count"] == 1
    assert buckets["5.00x–9.99x"]["count"] == 1
    assert buckets["10.00x+"]["count"] == 1


# ══════════════════════════════════════════════════════════════════════════════
# 11. Audit Endpoint
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_audit_round_endpoint(client, db_session):
    """GET /api/audit/round/{round_id} returns accurate, non-sensitive audit metrics."""
    user_data = await _register_auth_user(client, "audit_user")
    token = user_data["access_token"]
    user_id = user_data["user_id"] if "user_id" in user_data else 1
    headers = _auth_header(token)

    seed = FairnessService.generate_seed()
    seed_hash = FairnessService.hash_seed(seed)
    round_num = 801
    crash_mult = FairnessService.calculate_crash_point(seed, round_num)

    r = Round(
        round_number=round_num,
        server_seed_hash=seed_hash,
        server_seed=seed,
        crash_multiplier=crash_mult,
        status=RoundStatus.crashed,
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
    )
    db_session.add(r)
    await db_session.flush()

    # Create second user for the second bet
    user2 = User(
        username="audit_user_2",
        password_hash="hash2",
        status=UserStatus.active,
    )
    db_session.add(user2)
    await db_session.flush()

    # Add 2 bets: 1 cashed out (user 1), 1 lost (user 2)
    b1 = Bet(
        round_id=r.id,
        user_id=user_id,
        amount=100,
        cashout_multiplier=1.50,
        payout=150,
        status=BetStatus.cashed_out,
    )
    b2 = Bet(
        round_id=r.id,
        user_id=user2.id,
        amount=200,
        cashout_multiplier=None,
        payout=0,
        status=BetStatus.lost,
    )
    db_session.add_all([b1, b2])
    await db_session.commit()

    resp = await client.get(f"/api/audit/round/{r.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["round_id"] == r.id
    assert data["round_number"] == round_num
    assert data["status"] == "crashed"
    assert data["server_seed_hash"] == seed_hash
    assert data["server_seed"] == seed
    assert data["crash_multiplier"] == crash_mult
    assert data["verified"] is True
    assert data["total_bets"] == 2
    assert data["total_wagered"] == 300
    assert data["total_payout"] == 150
    assert data["cashed_out_count"] == 1
    assert data["lost_count"] == 1

    # 404 for nonexistent round
    not_found = await client.get("/api/audit/round/99999", headers=headers)
    assert not_found.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# 12. Audit Record Immutability & Structured Event Logging
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_audit_record_immutability(client, db_session):
    """Historical audit records cannot be mutated by subsequent requests or queries."""
    user_data = await _register_auth_user(client, "immutable_user")
    token = user_data["access_token"]
    headers = _auth_header(token)

    seed = FairnessService.generate_seed()
    seed_hash = FairnessService.hash_seed(seed)
    r = Round(
        round_number=901,
        server_seed_hash=seed_hash,
        server_seed=seed,
        crash_multiplier=2.50,
        status=RoundStatus.crashed,
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
    )
    db_session.add(r)
    await db_session.commit()

    resp1 = await client.get(f"/api/audit/round/{r.id}", headers=headers)
    assert resp1.status_code == 200
    record1 = resp1.json()

    # Subsequent queries return identical immutable historical data
    resp2 = await client.get(f"/api/audit/round/{r.id}", headers=headers)
    assert resp2.status_code == 200
    record2 = resp2.json()

    assert record1 == record2
    assert record1["server_seed_hash"] == seed_hash
    assert record1["crash_multiplier"] == 2.50


def test_structured_audit_logging_sanitization(caplog):
    """Verify structured audit logs do not leak passwords or authentication tokens."""
    with caplog.at_level(logging.INFO, logger="anti_gravity.audit"):
        AuditService.log_round_created(round_id=1, round_number=1, server_seed_hash="hash123")
        AuditService.log_round_started(round_id=1, round_number=1)
        AuditService.log_round_crashed(round_id=1, round_number=1, crash_multiplier=2.0)
        AuditService.log_round_ended(round_id=1, round_number=1)
        AuditService.log_cashout_accepted(
            round_id=1, user_id=10, bet_id=5, multiplier=1.5, payout=150, balance_after=10050
        )
        AuditService.log_cashout_rejected(round_id=1, user_id=10, bet_id=6, reason="Round crashed")

        # Test sensitive field redaction
        AuditService._emit_audit_event("custom_test", {"password": "secret", "token": "jwt_token"})

    logs = [rec.message for rec in caplog.records if "anti_gravity.audit" in rec.name]
    assert len(logs) >= 7

    for log_str in logs:
        # Must be valid JSON
        data = json.loads(log_str.strip())
        assert "audit_event" in data
        assert "timestamp" in data
        # Ensure no plaintext passwords or tokens
        if "password" in data:
            assert data["password"] == "[REDACTED]"
        if "token" in data:
            assert data["token"] == "[REDACTED]"
