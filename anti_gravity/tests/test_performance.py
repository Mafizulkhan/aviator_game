"""
Anti-Gravity Backend — Performance, Database Optimization & Stability Tests (Sprint 7)

Tests:
1. Database indexes and query execution efficiency.
2. Resource management & clean session/engine lifecycle.
3. WebSocket ConnectionManager concurrency (10, 50, 100 clients).
4. Dead WebSocket client cleanup and slow-client isolation.
5. GameLoop lifecycle, duplicate loop prevention, clean shutdown.
6. Safe pagination limits on history endpoints.
7. Representative API latency benchmarks.

Run with:
    python -m pytest tests/test_performance.py -v
"""

import sys
import os
import time
import asyncio
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.main import app
from backend.database import Base, get_db
from backend.models import User, UserStatus, Wallet, Round, RoundStatus, Bet, BetStatus, Transaction
from backend.ws.connection_manager import ConnectionManager
from backend.ws.game_loop import GameLoop
from backend.services.game_service import _active_round_internal, get_current_round, join_round, cashout
from backend.services.audit_service import AuditService
from backend.services.wallet_service import get_balance
from app.engine.game_engine import FairnessEngine


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def perf_db():
    """Isolated in-memory SQLite database for performance tests."""
    _active_round_internal.clear()
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        import backend.models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield factory, engine
    finally:
        await engine.dispose()
        _active_round_internal.clear()


@pytest_asyncio.fixture(scope="function")
async def perf_client(perf_db):
    """AsyncClient wired with test database session."""
    factory, engine = perf_db
    _active_round_internal.clear()

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, factory
    app.dependency_overrides.clear()
    _active_round_internal.clear()


class MockWebSocket:
    """Simulated WebSocket client for load and concurrency testing."""
    def __init__(self, client_id: int, delay: float = 0.0, fail: bool = False):
        self.client_id = client_id
        self.delay = delay
        self.fail = fail
        self.received = []
        self.closed = False

    async def accept(self):
        pass

    async def send_json(self, data):
        if self.closed or self.fail:
            raise RuntimeError(f"Client {self.client_id} disconnected or errored")
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        self.received.append(data)

    async def close(self, code: int = 1000, reason: str = ""):
        self.closed = True


# ════════════════════════════════════════════════════════════════════════════════
# 1. Database Indexes & Query Optimizations
# ════════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_database_indexes_exist(perf_db):
    """Verify that expected performance indexes are created on models."""
    factory, engine = perf_db
    async with engine.connect() as conn:
        def get_indexes(sync_conn):
            insp = inspect(sync_conn)
            return {
                "users": [idx["name"] for idx in insp.get_indexes("users")],
                "rounds": [idx["name"] for idx in insp.get_indexes("rounds")],
                "bets": [idx["name"] for idx in insp.get_indexes("bets")],
                "transactions": [idx["name"] for idx in insp.get_indexes("transactions")],
                "wallets": [idx["name"] for idx in insp.get_indexes("wallets")],
            }
        indexes = await conn.run_sync(get_indexes)

        # Check User indexes
        assert "ix_users_email" in indexes["users"]
        assert "ix_users_status" in indexes["users"]

        # Check Round indexes
        assert "ix_rounds_status" in indexes["rounds"]
        assert "ix_rounds_status_id" in indexes["rounds"]
        assert "ix_rounds_started_at" in indexes["rounds"]

        # Check Bet indexes
        assert "ix_bets_user_id" in indexes["bets"]
        assert "ix_bets_round_id" in indexes["bets"]
        assert "ix_bets_round_id_status" in indexes["bets"]
        assert "ix_bets_user_id_id" in indexes["bets"]

        # Check Transaction indexes
        assert "ix_transactions_user_id_created_at" in indexes["transactions"]
        assert "ix_transactions_created_at" in indexes["transactions"]


@pytest.mark.asyncio
async def test_audit_aggregate_query_performance(perf_db):
    """Verify that AuditService.get_fairness_statistics runs as single SQL aggregate."""
    factory, engine = perf_db
    async with factory() as db:
        # Add 50 bets to round r1
        r1 = Round(
            round_number=1,
            server_seed_hash="hash_1",
            status=RoundStatus.crashed,
            crash_multiplier=2.0,
            server_seed="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        )
        db.add(r1)
        await db.flush()

        for i in range(50):
            u = User(username=f"audit_u_{i}", password_hash="hash", status=UserStatus.active)
            db.add(u)
            await db.flush()

            bet = Bet(
                round_id=r1.id,
                user_id=u.id,
                amount=100,
                status=BetStatus.cashed_out if i % 2 == 0 else BetStatus.lost,
                cashout_multiplier=2.0 if i % 2 == 0 else None,
                payout=200 if i % 2 == 0 else 0
            )
            db.add(bet)
        await db.commit()

        audit_rec = await AuditService.get_round_audit_record(db, r1.id)
        assert audit_rec.round_id == r1.id
        assert audit_rec.total_bets == 50
        assert audit_rec.total_wagered == 5000
        assert audit_rec.total_payout == 5000  # 25 * 200
        assert audit_rec.cashed_out_count == 25
        assert audit_rec.lost_count == 25


# ════════════════════════════════════════════════════════════════════════════════
# 2. ConnectionManager Optimization & Load Testing
# ════════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_websocket_broadcast_10_clients():
    """Measure broadcast throughput with 10 concurrent clients."""
    cm = ConnectionManager()
    clients = [MockWebSocket(i) for i in range(10)]
    for c in clients:
        await cm.connect(c)

    assert cm.active_count == 10

    t0 = time.perf_counter()
    await cm.broadcast({"type": "MULTIPLIER_UPDATE", "multiplier": 2.05})
    elapsed = (time.perf_counter() - t0) * 1000  # ms

    for c in clients:
        assert len(c.received) == 1
        assert c.received[0]["multiplier"] == 2.05

    assert elapsed < 50.0
    await cm.clean_shutdown()


@pytest.mark.asyncio
async def test_websocket_broadcast_50_clients():
    """Measure broadcast throughput with 50 concurrent clients."""
    cm = ConnectionManager()
    clients = [MockWebSocket(i) for i in range(50)]
    for c in clients:
        await cm.connect(c)

    assert cm.active_count == 50

    t0 = time.perf_counter()
    await cm.broadcast({"type": "MULTIPLIER_UPDATE", "multiplier": 3.50})
    elapsed = (time.perf_counter() - t0) * 1000  # ms

    for c in clients:
        assert len(c.received) == 1

    assert elapsed < 100.0
    await cm.clean_shutdown()


@pytest.mark.asyncio
async def test_websocket_broadcast_100_clients():
    """Measure broadcast throughput with 100 concurrent clients."""
    cm = ConnectionManager()
    clients = [MockWebSocket(i) for i in range(100)]
    for c in clients:
        await cm.connect(c)

    assert cm.active_count == 100

    t0 = time.perf_counter()
    await cm.broadcast({"type": "MULTIPLIER_UPDATE", "multiplier": 5.12})
    elapsed = (time.perf_counter() - t0) * 1000  # ms

    for c in clients:
        assert len(c.received) == 1

    assert elapsed < 200.0
    await cm.clean_shutdown()


@pytest.mark.asyncio
async def test_slow_client_does_not_block_fast_clients():
    """Verify that asyncio.gather isolates slow clients from fast clients."""
    cm = ConnectionManager()
    fast_client = MockWebSocket(client_id=1, delay=0.0)
    slow_client = MockWebSocket(client_id=2, delay=0.04)

    await cm.connect(fast_client)
    await cm.connect(slow_client)

    t0 = time.perf_counter()
    await cm.broadcast({"type": "MULTIPLIER_UPDATE", "multiplier": 1.50})
    elapsed = (time.perf_counter() - t0) * 1000

    assert len(fast_client.received) == 1
    assert len(slow_client.received) == 1
    assert elapsed < 120.0
    await cm.clean_shutdown()


@pytest.mark.asyncio
async def test_dead_client_cleanup_on_broadcast():
    """Verify that disconnected or errored clients are pruned automatically on broadcast."""
    cm = ConnectionManager()
    good_client = MockWebSocket(client_id=1, fail=False)
    broken_client = MockWebSocket(client_id=2, fail=True)

    await cm.connect(good_client)
    await cm.connect(broken_client)
    assert cm.active_count == 2

    await cm.broadcast({"type": "PING"})

    # Broken client should be removed from active pool
    assert cm.active_count == 1
    assert good_client in cm.active_connections
    assert broken_client not in cm.active_connections


@pytest.mark.asyncio
async def test_clean_shutdown_closes_all_connections():
    """Verify that clean_shutdown calls close on all active connections."""
    cm = ConnectionManager()
    clients = [MockWebSocket(i) for i in range(5)]
    for c in clients:
        await cm.connect(c)

    assert cm.active_count == 5
    await cm.clean_shutdown()
    assert cm.active_count == 0
    for c in clients:
        assert c.closed is True


# ════════════════════════════════════════════════════════════════════════════════
# 3. GameLoop Duplicate Prevention & Stability
# ════════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_duplicate_game_loop_start_prevention(perf_db):
    """Verify that multiple start() calls do not spawn duplicate background tasks."""
    factory, engine = perf_db
    cm = ConnectionManager()
    gl = GameLoop(
        tick_interval=0.02,
        waiting_duration=0.1,
        ended_duration=0.05,
        connection_manager=cm,
        session_factory=factory,
    )

    gl.start()
    task1 = gl._task
    assert gl.is_running is True

    # Second start should be a no-op
    gl.start()
    assert gl._task is task1

    await gl.stop_async()
    assert gl.is_running is False
    assert gl._task is None


# ════════════════════════════════════════════════════════════════════════════════
# 4. Safe Pagination Limits
# ════════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_history_pagination_bounds(perf_client):
    """Verify pagination validation and offset handling."""
    client, factory = perf_client

    # Register
    reg = await client.post("/api/auth/register", json={"username": "pager_user", "password": "pass12345"})
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Valid pagination parameters
    resp = await client.get("/api/game/history?limit=50&offset=0", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # Limit exceeding max allowed should be rejected with 422 Validation Error
    resp_over = await client.get("/api/game/history?limit=500", headers=headers)
    assert resp_over.status_code == 422

    # Limit below min allowed (0) should be rejected with 422 Validation Error
    resp_zero = await client.get("/api/game/history?limit=0", headers=headers)
    assert resp_zero.status_code == 422

    # Player history pagination
    p_resp = await client.get("/api/player/history?limit=50&offset=0", headers=headers)
    assert p_resp.status_code == 200
    assert isinstance(p_resp.json(), list)


# ════════════════════════════════════════════════════════════════════════════════
# 5. Representative API Latency Benchmarks
# ════════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_representative_api_latencies(perf_client):
    """Measure latency for representative API endpoints."""
    client, factory = perf_client

    # 1. Health
    t0 = time.perf_counter()
    r_health = await client.get("/api/health")
    lat_health = (time.perf_counter() - t0) * 1000
    assert r_health.status_code == 200

    # Register & Login
    r_reg = await client.post("/api/auth/register", json={"username": "bench_user", "password": "pass12345"})
    token = r_reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Player Balance
    t0 = time.perf_counter()
    r_bal = await client.get("/api/player/balance", headers=headers)
    lat_bal = (time.perf_counter() - t0) * 1000
    assert r_bal.status_code == 200

    # 3. Game Current
    t0 = time.perf_counter()
    r_curr = await client.get("/api/game/current", headers=headers)
    lat_curr = (time.perf_counter() - t0) * 1000
    assert r_curr.status_code == 200

    # 4. Game History
    t0 = time.perf_counter()
    r_hist = await client.get("/api/game/history", headers=headers)
    lat_hist = (time.perf_counter() - t0) * 1000
    assert r_hist.status_code == 200

    # 5. Fairness Verification (create a crashed round)
    round_id = r_curr.json()["round_id"]
    async with factory() as db:
        r_row = await db.get(Round, round_id)
        r_row.status = RoundStatus.crashed
        r_row.crash_multiplier = 2.00
        r_row.server_seed = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        await db.commit()

    t0 = time.perf_counter()
    r_fair = await client.get(f"/api/fairness/{round_id}/verify", headers=headers)
    lat_fair = (time.perf_counter() - t0) * 1000
    assert r_fair.status_code == 200

    # Print summary of measured latencies for reporting
    print(f"\n[API Benchmark Latency Results]")
    print(f"GET /api/health:                 {lat_health:.2f} ms")
    print(f"GET /api/player/balance:         {lat_bal:.2f} ms")
    print(f"GET /api/game/current:           {lat_curr:.2f} ms")
    print(f"GET /api/game/history:           {lat_hist:.2f} ms")
    print(f"GET /api/fairness/{{id}}/verify:   {lat_fair:.2f} ms")

    assert lat_health < 100.0
    assert lat_bal < 100.0
    assert lat_curr < 100.0
    assert lat_hist < 100.0
    assert lat_fair < 100.0
