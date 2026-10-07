"""
Anti-Gravity Backend — Server-Authoritative Game Loop Tests (Sprint 4B)
Validates all 14 required server-authoritative live game loop capabilities:
1. Round creation
2. ROUND_STARTED broadcast
3. MULTIPLIER_UPDATE broadcast
4. Crash detection
5. ROUND_CRASHED broadcast
6. ROUND_ENDED broadcast
7. Multiple clients receiving identical events
8. Current-state synchronization
9. Cash-out during active round
10. Cash-out after crash
11. No new round per client
12. Game loop startup
13. Game loop shutdown
14. No duplicate active rounds
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from backend.database import Base
from backend.models import Round, RoundStatus, User, UserStatus, Wallet, Bet, BetStatus
from backend.services.game_service import (
    _active_round_internal, get_current_round, start_round,
    resolve_round_if_crashed, join_round, cashout, _create_new_round
)
from backend.ws.connection_manager import ConnectionManager
from backend.ws.game_loop import GameLoop
from app.engine.game_engine import FairnessEngine, MultiplierEngine


class MockWebSocket:
    """Mock WebSocket client to capture messages sent via ConnectionManager."""
    def __init__(self):
        self.messages = []
        self.closed = False

    async def accept(self):
        pass

    async def send_json(self, data):
        if self.closed:
            raise RuntimeError("WebSocket is closed")
        self.messages.append(data)

    async def close(self):
        self.closed = True


from sqlalchemy.pool import StaticPool


@pytest_asyncio.fixture(scope="function")
async def loop_db():
    """Isolated in-memory DB session factory for game loop tests."""
    _active_round_internal.clear()
    test_db_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        import backend.models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()
        _active_round_internal.clear()


@pytest_asyncio.fixture(scope="function")
async def seed_user(loop_db):
    """Seed a test user with wallet balance for bet/cashout tests."""
    async with loop_db() as db:
        user = User(
            username="pilot_test",
            password_hash="fake_hash",
            status=UserStatus.active
        )
        db.add(user)
        await db.flush()

        wallet = Wallet(
            user_id=user.id,
            balance=10000
        )
        db.add(wallet)
        await db.commit()
        await db.refresh(user)
        return user.id


# ── 1. Round Creation ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_round_creation(loop_db):
    """Test that a newly created round has valid id, pending status, and fairness pre-commitment."""
    async with loop_db() as db:
        round_row = await get_current_round(db)
        assert round_row.id is not None
        assert round_row.round_number >= 1
        assert round_row.status == RoundStatus.pending
        assert round_row.server_seed_hash is not None
        assert len(round_row.server_seed_hash) == 64
        # Seed is stored in internal cache, not revealed in DB yet
        assert round_row.server_seed is None
        assert round_row.id in _active_round_internal


# ── 2. ROUND_STARTED Broadcast ────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_round_started_broadcast(loop_db):
    """Test that transitioning a round to running broadcasts ROUND_STARTED."""
    cm = ConnectionManager()
    ws = MockWebSocket()
    await cm.connect(ws)

    gl = GameLoop(
        tick_interval=0.01,
        waiting_duration=0.02,
        ended_duration=0.02,
        connection_manager=cm,
        session_factory=loop_db,
    )

    gl.start()
    for _ in range(25):
        if any(m["type"] == "ROUND_STARTED" for m in ws.messages):
            break
        await asyncio.sleep(0.01)
    await gl.stop_async()

    types = [m["type"] for m in ws.messages]
    assert "ROUND_WAITING" in types
    assert "ROUND_STARTED" in types

    started_msg = next(m for m in ws.messages if m["type"] == "ROUND_STARTED")
    assert "round_id" in started_msg
    assert "round_number" in started_msg
    assert started_msg["status"] == "running"
    assert "server_time" in started_msg


# ── 3. MULTIPLIER_UPDATE Broadcast ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_multiplier_update_broadcast(loop_db):
    """Test that running rounds periodically broadcast increasing MULTIPLIER_UPDATE events."""
    cm = ConnectionManager()
    ws = MockWebSocket()
    await cm.connect(ws)

    # Pre-create a round with a guaranteed high crash multiplier (e.g. 10.0x) so it ticks
    async with loop_db() as db:
        round_row = await get_current_round(db)
        _active_round_internal[round_row.id] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

    gl = GameLoop(
        tick_interval=0.02,
        waiting_duration=0.02,
        ended_duration=0.05,
        connection_manager=cm,
        session_factory=loop_db,
    )

    gl.start()
    for _ in range(25):
        if len([m for m in ws.messages if m["type"] == "MULTIPLIER_UPDATE"]) >= 2:
            break
        await asyncio.sleep(0.01)
    await gl.stop_async()

    mult_messages = [m for m in ws.messages if m["type"] == "MULTIPLIER_UPDATE"]
    assert len(mult_messages) >= 2, f"Expected multiplier ticks, got {ws.messages}"
    for msg in mult_messages:
        assert msg["multiplier"] >= 1.00
        assert "round_id" in msg
        assert "server_time" in msg


# ── 4. Crash Detection ────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_crash_detection(loop_db):
    """Test that the server detects round crash authoritatively when elapsed >= crash_time."""
    async with loop_db() as db:
        round_row = await get_current_round(db)
        round_row = await start_round(db, round_row)
        # Force a seed with 1.00x crash
        seed = "0000000000000000000000000000000000000000000000000000000000000000"
        _active_round_internal[round_row.id] = seed

        # Immediate resolve check
        crashed = await resolve_round_if_crashed(db, round_row)
        assert crashed is True
        assert round_row.status == RoundStatus.crashed
        assert round_row.server_seed == seed
        assert round_row.crash_multiplier is not None


# ── 5. ROUND_CRASHED Broadcast ────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_round_crashed_broadcast(loop_db):
    """Test that when a round crashes, ROUND_CRASHED is broadcast with crash multiplier."""
    cm = ConnectionManager()
    ws = MockWebSocket()
    await cm.connect(ws)

    # Pre-set fast crash seed (1.00x)
    async with loop_db() as db:
        round_row = await get_current_round(db)
        _active_round_internal[round_row.id] = "0000000000000000000000000000000000000000000000000000000000000000"

    gl = GameLoop(
        tick_interval=0.01,
        waiting_duration=0.01,
        ended_duration=0.02,
        connection_manager=cm,
        session_factory=loop_db,
    )

    gl.start()
    for _ in range(25):
        if any(m["type"] == "ROUND_CRASHED" for m in ws.messages):
            break
        await asyncio.sleep(0.01)
    await gl.stop_async()

    types = [m["type"] for m in ws.messages]
    assert "ROUND_CRASHED" in types, f"Expected ROUND_CRASHED, got {types}"

    crashed_msg = next(m for m in ws.messages if m["type"] == "ROUND_CRASHED")
    assert "round_id" in crashed_msg
    assert "crash_multiplier" in crashed_msg
    assert crashed_msg["crash_multiplier"] >= 1.00
    assert "server_time" in crashed_msg


# ── 6. ROUND_ENDED Broadcast ──────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_round_ended_broadcast(loop_db):
    """Test that ROUND_ENDED is broadcast following crash before the next round begins."""
    cm = ConnectionManager()
    ws = MockWebSocket()
    await cm.connect(ws)

    # Pre-set fast crash seed (1.00x)
    async with loop_db() as db:
        round_row = await get_current_round(db)
        _active_round_internal[round_row.id] = "0000000000000000000000000000000000000000000000000000000000000000"

    gl = GameLoop(
        tick_interval=0.01,
        waiting_duration=0.01,
        ended_duration=0.02,
        connection_manager=cm,
        session_factory=loop_db,
    )

    gl.start()
    for _ in range(25):
        if any(m["type"] == "ROUND_ENDED" for m in ws.messages):
            break
        await asyncio.sleep(0.01)
    await gl.stop_async()

    types = [m["type"] for m in ws.messages]
    assert "ROUND_ENDED" in types, f"Expected ROUND_ENDED, got {types}"

    ended_msg = next(m for m in ws.messages if m["type"] == "ROUND_ENDED")
    assert "round_id" in ended_msg
    assert "server_time" in ended_msg


# ── 7. Multiple Clients Receive Identical Events ──────────────────────────────
@pytest.mark.asyncio
async def test_multiple_clients_receive_identical_events(loop_db):
    """Test that all connected clients receive identical broadcast events in the same order."""
    cm = ConnectionManager()
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()
    await cm.connect(ws1)
    await cm.connect(ws2)
    await cm.connect(ws3)

    gl = GameLoop(
        tick_interval=0.01,
        waiting_duration=0.02,
        ended_duration=0.02,
        connection_manager=cm,
        session_factory=loop_db,
    )

    gl.start()
    await asyncio.sleep(0.25)
    await gl.stop_async()

    assert len(ws1.messages) > 0
    assert len(ws1.messages) == len(ws2.messages) == len(ws3.messages)

    for m1, m2, m3 in zip(ws1.messages, ws2.messages, ws3.messages):
        assert m1 == m2 == m3


# ── 8. Current-State Synchronization ──────────────────────────────────────────
@pytest.mark.asyncio
async def test_current_state_synchronization(loop_db):
    """Test that get_initial_client_message accurately synchronizes client with current state."""
    cm = ConnectionManager()
    gl = GameLoop(
        tick_interval=0.02,
        waiting_duration=0.1,
        ended_duration=0.05,
        connection_manager=cm,
        session_factory=loop_db,
    )

    # 1. Waiting state sync
    async with loop_db() as db:
        await get_current_round(db)
        state_msg = await gl.get_initial_client_message(db_session=db)
        assert state_msg["status"] == "waiting"
        assert state_msg["type"] == "ROUND_WAITING"

    # 2. Running state sync
    async with loop_db() as db:
        round_row = await get_current_round(db)
        await start_round(db, round_row)
        state_msg2 = await gl.get_initial_client_message(db_session=db)
        assert state_msg2["status"] == "running"
        assert state_msg2["type"] == "MULTIPLIER_UPDATE"
        assert state_msg2["multiplier"] >= 1.00


# ── 9. Cash-Out During Active Round ───────────────────────────────────────────
@pytest.mark.asyncio
async def test_cashout_during_active_round(loop_db, seed_user):
    """Test server-authoritative cash-out while a round is running."""
    async with loop_db() as db:
        bet, round_row, _ = await join_round(db, seed_user, 100)
        assert bet.status == BetStatus.active

        # Guarantee high crash multiplier so it's safely running
        _active_round_internal[round_row.id] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

        bet_cashed, _, balance_after = await cashout(db, seed_user, bet.id)
        assert bet_cashed.status == BetStatus.cashed_out
        assert bet_cashed.cashout_multiplier >= 1.00
        assert bet_cashed.payout >= 100
        assert balance_after == 10000 - 100 + bet_cashed.payout


# ── 10. Cash-Out After Crash ──────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_cashout_after_crash(loop_db, seed_user):
    """Test that cashout requested after crash is rejected and bet is marked lost."""
    async with loop_db() as db:
        # Guarantee round is running initially
        _active_round_internal.clear()
        round_row = await get_current_round(db)
        _active_round_internal[round_row.id] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

        bet, round_row, _ = await join_round(db, seed_user, 100)

        # Force crash with seed that produces 1.00x crash point
        _active_round_internal[round_row.id] = "0000000000000000000000000000000000000000000000000000000000000000"
        await resolve_round_if_crashed(db, round_row)

        with pytest.raises(ValueError, match="Cash-out already processed for this bet|Round crashed before your cash-out arrived|Round is not running"):
            await cashout(db, seed_user, bet.id)

        # Check bet marked lost
        updated_bet = await db.get(Bet, bet.id)
        assert updated_bet.status == BetStatus.lost


# ── 11. No New Round Per Client ───────────────────────────────────────────────
@pytest.mark.asyncio
async def test_no_new_round_per_client(loop_db):
    """Test that multiple clients querying current round all receive the same round."""
    async with loop_db() as db:
        r1 = await get_current_round(db)
        r2 = await get_current_round(db)
        r3 = await get_current_round(db)

    assert r1.id == r2.id == r3.id
    assert r1.round_number == r2.round_number == r3.round_number


# ── 12. Game Loop Startup ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_game_loop_startup(loop_db):
    """Test that starting the game loop initializes background task and is_running flag."""
    cm = ConnectionManager()
    gl = GameLoop(
        tick_interval=0.01,
        waiting_duration=0.05,
        ended_duration=0.05,
        connection_manager=cm,
        session_factory=loop_db,
    )

    assert gl.is_running is False
    assert gl._task is None

    gl.start()
    assert gl.is_running is True
    assert gl._task is not None
    assert not gl._task.done()

    await gl.stop_async()


# ── 13. Game Loop Shutdown ────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_game_loop_shutdown(loop_db):
    """Test that game loop stops cleanly on shutdown without hanging or unhandled errors."""
    cm = ConnectionManager()
    gl = GameLoop(
        tick_interval=0.01,
        waiting_duration=0.05,
        ended_duration=0.05,
        connection_manager=cm,
        session_factory=loop_db,
    )

    gl.start()
    await asyncio.sleep(0.02)
    await gl.stop_async()

    assert gl.is_running is False
    assert gl._task is None


# ── 14. No Duplicate Active Rounds ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_no_duplicate_active_rounds(loop_db):
    """Test that the database maintains strictly one active (pending/running) round at a time."""
    async with loop_db() as db:
        # Create initial round
        r1 = await get_current_round(db)
        r2 = await get_current_round(db)
        assert r1.id == r2.id

        # Query all active rounds in database
        result = await db.execute(
            select(Round).where(Round.status.in_([RoundStatus.pending, RoundStatus.running]))
        )
        active_rounds = result.scalars().all()
        assert len(active_rounds) == 1
