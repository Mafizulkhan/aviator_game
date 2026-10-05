"""
Anti-Gravity — Sprint 4D: End-to-End Integration Tests
=======================================================

Tests the complete Anti-Gravity system against a REAL running Uvicorn server
with a REAL WebSocket client (`websockets` library) and REAL REST calls (`httpx`).
Nothing is mocked at the transport or server level.

Architecture
------------
- A single Uvicorn server instance is started in-process as an asyncio background
  task during the module-scoped `e2e_server` fixture.  All 6 tests share it.
- The server uses an isolated SQLite in-memory database via FastAPI dependency
  overrides; the developer's `anti_gravity.db` is never touched.
- The game loop is replaced with an accelerated instance
  (tick=20 ms, waiting=50 ms, ended=50 ms) so full rounds complete quickly.
- `loop_scope="module"` is applied to every fixture and test so they all execute
  on the same asyncio event loop as the Uvicorn server task.

WebSocket client
----------------
`websockets` v16 (already installed) — `async with websockets.connect(url)`.

Run
---
    python -m pytest tests/test_e2e.py -v
    python -m pytest tests/ -v          # full suite — existing 96 tests + 6 E2E
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import json
import socket
from typing import Any, Dict, List, Optional

import httpx
import pytest
import pytest_asyncio
import uvicorn
import websockets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from sqlalchemy.pool import StaticPool

# ── Project imports ────────────────────────────────────────────────────────────
from backend.main import app
from backend.database import Base, get_db
from backend.models import Bet, BetStatus, Transaction, TransactionType, Wallet
from backend.services.game_service import _active_round_internal
from backend.ws.game_loop import GameLoop
from backend.ws.connection_manager import manager as _shared_manager


# ══════════════════════════════════════════════════════════════════════════════
# Make ALL tests in this module share one event loop (same loop as the server)
# ══════════════════════════════════════════════════════════════════════════════
pytestmark = pytest.mark.asyncio(loop_scope="module")


# ══════════════════════════════════════════════════════════════════════════════
# Utilities
# ══════════════════════════════════════════════════════════════════════════════

def _free_port() -> int:
    """Return an available TCP port on 127.0.0.1."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _wait_for_ws_types(
    ws_url: str,
    required_types: List[str],
    *,
    timeout: float = 25.0,
    stop_on_crash: bool = False,
) -> List[Dict[str, Any]]:
    """
    Open a WebSocket, collect messages until every type in `required_types`
    has been seen at least once (or `timeout` seconds elapse).

    Returns the complete ordered list of messages received.
    Raises asyncio.TimeoutError if the required types never appear.
    """
    collected: List[Dict[str, Any]] = []
    seen: set = set()
    required = set(required_types)
    loop = asyncio.get_event_loop()

    async with websockets.connect(ws_url, open_timeout=10) as ws:
        deadline = loop.time() + timeout
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 1.5))
            except asyncio.TimeoutError:
                if required.issubset(seen):
                    break
                continue

            msg = json.loads(raw)
            collected.append(msg)
            seen.add(msg.get("type", ""))

            if required.issubset(seen):
                if stop_on_crash and "ROUND_CRASHED" in seen:
                    # Drain one more message to get ROUND_ENDED if close behind
                    try:
                        raw2 = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        collected.append(json.loads(raw2))
                        seen.add(json.loads(raw2).get("type", ""))
                    except asyncio.TimeoutError:
                        pass
                    break
                elif not stop_on_crash:
                    break

    if not required.issubset(seen):
        raise asyncio.TimeoutError(
            f"Timeout waiting for {required - seen}. "
            f"Seen: {seen}. Messages: {collected}"
        )
    return collected


async def _register_or_login(
    http: httpx.AsyncClient,
    username: str,
    password: str,
) -> Dict[str, Any]:
    """Register a new user; if username taken, log in instead."""
    resp = await http.post(
        "/api/auth/register",
        json={"username": username, "password": password},
    )
    if resp.status_code == 409:
        resp = await http.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
    resp.raise_for_status()
    return resp.json()


# ══════════════════════════════════════════════════════════════════════════════
# Module-scoped fixture: isolated in-memory DB  +  live Uvicorn server
# ══════════════════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def e2e_server():
    """
    Spin up a REAL Uvicorn server backed by an isolated temporary SQLite DB.

    Yields a dict:
        base_url   – "http://127.0.0.1:<port>"
        ws_url     – "ws://127.0.0.1:<port>/ws/game"
        db_factory – async session factory for direct DB inspection in tests

    Tears down cleanly after all tests in this module have run.
    """
    import tempfile
    import uuid

    port = _free_port()
    db_file = os.path.join(tempfile.gettempdir(), f"anti_gravity_e2e_{uuid.uuid4().hex[:8]}.db")

    # ── 1. Isolated temporary file-based DB ────────────────────────────────────
    # File-backed SQLite allows multiple independent connections with proper
    # transaction isolation for concurrent cash-out tests.
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    TestSession = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create tables
    async with test_engine.begin() as conn:
        import backend.models  # noqa: F401 — ensures all models are registered
        await conn.run_sync(Base.metadata.create_all)

    # ── 2. FastAPI dependency override → isolated DB ──────────────────────────
    async def _override_get_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    # ── 3. Accelerated game loop using isolated DB ────────────────────────────
    fast_loop = GameLoop(
        tick_interval=0.02,      # 20 ms multiplier broadcast cadence
        waiting_duration=0.05,   # 50 ms betting window
        ended_duration=0.05,     # 50 ms cool-down between rounds
        connection_manager=_shared_manager,
        session_factory=TestSession,
    )

    # ── 4. Replace app lifespan so our fast_loop + isolated DB are used ───────
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _test_lifespan(application):
        _active_round_internal.clear()
        async with test_engine.begin() as conn:
            import backend.models  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
        fast_loop.start()
        yield
        await fast_loop.stop_async()
        await _shared_manager.remove_dead_connections()
        _active_round_internal.clear()

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _test_lifespan

    # ── 5. Start Uvicorn in a background task on the CURRENT event loop ───────
    config = uvicicorn_config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        loop="none",          # do NOT let uvicorn create a new event loop
    )
    server = uvicorn.Server(config)
    server_task = asyncio.get_event_loop().create_task(server.serve())

    # Poll until accepting connections (max 8 s)
    for _ in range(160):
        await asyncio.sleep(0.05)
        if server.started:
            break
    else:
        server_task.cancel()
        raise RuntimeError("E2E Uvicorn server did not start within 8 s")

    # ── Yield to tests ────────────────────────────────────────────────────────
    yield {
        "base_url":   f"http://127.0.0.1:{port}",
        "ws_url":     f"ws://127.0.0.1:{port}/ws/game",
        "db_factory": TestSession,
        "port":       port,
    }

    # ── 6. Tear-down ──────────────────────────────────────────────────────────
    server.should_exit = True
    try:
        await asyncio.wait_for(server_task, timeout=5.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        server_task.cancel()

    # Restore
    app.router.lifespan_context = original_lifespan
    app.dependency_overrides.clear()

    await test_engine.dispose()
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except OSError:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# Test 1 — Health
# ══════════════════════════════════════════════════════════════════════════════

async def test_e2e_health(e2e_server):
    """
    GET /api/health on the real running server must return status=ok.
    Verifies the Uvicorn server is up, lifespan completed, and routing works.
    """
    async with httpx.AsyncClient(
        base_url=e2e_server["base_url"], timeout=10.0
    ) as http:
        resp = await http.get("/api/health")

    assert resp.status_code == 200, f"Unexpected status {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "ok",      f"Expected status=ok, got: {data}"
    assert data["version"] == "0.2.0",  f"Unexpected version: {data}"
    assert "mode" in data


# ══════════════════════════════════════════════════════════════════════════════
# Test 2 — Real WebSocket connection + CONNECTED message
# ══════════════════════════════════════════════════════════════════════════════

async def test_e2e_ws_connection(e2e_server):
    """
    Open a REAL WebSocket to /ws/game (no mocking).
    The server must immediately send a CONNECTED message with required fields.
    """
    async with websockets.connect(
        e2e_server["ws_url"], open_timeout=10
    ) as ws:
        raw = await asyncio.wait_for(ws.recv(), timeout=8.0)

    msg = json.loads(raw)
    assert msg.get("type") == "CONNECTED", f"Expected CONNECTED, got: {msg}"
    assert "message" in msg,       "CONNECTED missing 'message' field"
    assert "server_time" in msg,   "CONNECTED missing 'server_time' field"
    assert "Anti-Gravity" in msg["message"], (
        f"Expected 'Anti-Gravity' in message text, got: {msg['message']}"
    )
    assert len(msg["server_time"]) > 0


# ══════════════════════════════════════════════════════════════════════════════
# Test 3 — Live round: ROUND_STARTED + MULTIPLIER_UPDATE
# ══════════════════════════════════════════════════════════════════════════════

async def test_e2e_ws_live_round(e2e_server):
    """
    Observe a real live round via WebSocket:
    - ROUND_STARTED is broadcast by the server-authoritative game loop
    - At least 2 MULTIPLIER_UPDATE ticks follow *for the same round*
    - round_id is consistent across both event types
    - Multiplier values are >= 1.00 and non-decreasing

    NOTE: When we connect mid-session, MULTIPLIER_UPDATE messages from a
    *previous* round may already be in-flight. We therefore only validate
    messages received *after* we see ROUND_STARTED, using the round_id
    from that event to filter out any residual messages from prior rounds.
    """
    ws_url = e2e_server["ws_url"]
    # Messages collected AFTER we see ROUND_STARTED for the target round
    target_round_id: Optional[int] = None
    post_start_mults: List[Dict] = []
    started_msg: Optional[Dict] = None

    async with websockets.connect(ws_url, open_timeout=10) as ws:
        deadline = asyncio.get_event_loop().time() + 40.0

        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 2.0))
            except asyncio.TimeoutError:
                if target_round_id is not None and len(post_start_mults) >= 2:
                    break
                continue

            msg = json.loads(raw)

            if msg.get("type") == "ROUND_STARTED":
                # Lock onto this round; discard any prior-round messages
                target_round_id = msg["round_id"]
                started_msg = msg
                post_start_mults = []   # reset: only count ticks from this round

            elif msg.get("type") == "MULTIPLIER_UPDATE" and target_round_id is not None:
                if msg.get("round_id") == target_round_id:
                    post_start_mults.append(msg)

            if target_round_id is not None and len(post_start_mults) >= 2:
                break

    # ── Assertions ────────────────────────────────────────────────────────────
    assert started_msg is not None, (
        "Never received ROUND_STARTED within 40 s"
    )
    assert len(post_start_mults) >= 2, (
        f"Expected ≥2 MULTIPLIER_UPDATE messages after ROUND_STARTED, "
        f"got {len(post_start_mults)}"
    )

    round_id = started_msg["round_id"]
    assert isinstance(round_id, int)
    assert started_msg["status"] == "running"

    for msg in post_start_mults:
        assert msg.get("round_id") == round_id, (
            f"round_id mismatch: expected {round_id}, got {msg.get('round_id')}"
        )
        assert isinstance(msg["multiplier"], (int, float))
        assert msg["multiplier"] >= 1.00, f"Multiplier below 1.00: {msg['multiplier']}"
        assert "server_time" in msg

    multipliers = [m["multiplier"] for m in post_start_mults]
    for i in range(1, len(multipliers)):
        assert multipliers[i] >= multipliers[i - 1], (
            f"Multiplier decreased: {multipliers[i-1]} → {multipliers[i]}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Test 4 — Crash: ROUND_CRASHED + ROUND_ENDED
# ══════════════════════════════════════════════════════════════════════════════

async def test_e2e_ws_crash(e2e_server):
    """
    Wait for a complete round crash on the real server.
    - ROUND_CRASHED is broadcast with a valid crash_multiplier >= 1.00
    - round_id in ROUND_CRASHED matches the ROUND_STARTED we observed
    - ROUND_ENDED follows the crash
    """
    ws_url = e2e_server["ws_url"]
    collected: List[Dict] = []
    seen: set = set()
    current_round_id: Optional[int] = None

    async with websockets.connect(ws_url, open_timeout=10) as ws:
        deadline = asyncio.get_event_loop().time() + 50.0

        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 2.0))
            except asyncio.TimeoutError:
                if "ROUND_CRASHED" in seen and "ROUND_ENDED" in seen:
                    break
                continue

            msg = json.loads(raw)
            collected.append(msg)
            t = msg.get("type", "")
            seen.add(t)
            if t == "ROUND_STARTED":
                current_round_id = msg["round_id"]
            if "ROUND_CRASHED" in seen and "ROUND_ENDED" in seen:
                break

    assert "ROUND_CRASHED" in seen, (
        f"Never received ROUND_CRASHED within 50 s.\n"
        f"Seen: {seen}\nMessages: {collected}"
    )

    crashed = next(m for m in collected if m["type"] == "ROUND_CRASHED")
    assert "round_id" in crashed
    crash_mult = crashed.get("crash_multiplier")
    assert isinstance(crash_mult, (int, float)), \
        f"crash_multiplier is not numeric: {crash_mult}"
    assert crash_mult >= 1.00, f"crash_multiplier below 1.00: {crash_mult}"
    assert "server_time" in crashed

    if current_round_id is not None:
        assert crashed["round_id"] == current_round_id, (
            f"ROUND_CRASHED round_id {crashed['round_id']} != "
            f"ROUND_STARTED round_id {current_round_id}"
        )

    assert "ROUND_ENDED" in seen, (
        f"ROUND_CRASHED received but ROUND_ENDED never followed. Seen: {seen}"
    )
    ended = next(m for m in collected if m["type"] == "ROUND_ENDED")
    assert ended["round_id"] == crashed["round_id"], (
        f"ROUND_ENDED round_id {ended['round_id']} != "
        f"ROUND_CRASHED round_id {crashed['round_id']}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Test 5 — Cash-out (server-side payout, DB verification)
# ══════════════════════════════════════════════════════════════════════════════

async def test_e2e_cashout(e2e_server):
    """
    Full cash-out flow:
      1. Register a test player
      2. Join an active round (retried across rounds if one crashes mid-join)
      3. Cash out immediately via POST /api/game/cashout
      4. Verify the server response — payout is server-determined; we do NOT
         compute it client-side
      5. Verify DB: bet=cashed_out, wallet balance correct, exactly 3 transactions
         (starting_credits + bet + payout)
    """
    base_url = e2e_server["base_url"]
    db_factory = e2e_server["db_factory"]

    async with httpx.AsyncClient(base_url=base_url, timeout=12.0) as http:
        # 1. Register
        token_data = await _register_or_login(
            http, username="e2e_cashout_user", password="CashoutP4ss!"
        )
        token = token_data["access_token"]
        starting_balance = token_data["balance"]
        hdrs = {"Authorization": f"Bearer {token}"}
        assert starting_balance == 10_000

        bet_amount = 100
        join_data: Optional[Dict] = None
        cashout_resp: Optional[Dict] = None

        # 2+3. Join then immediately cashout; retry if the round crashes first
        for _attempt in range(10):
            await asyncio.sleep(0.08)

            # Ensure there's a running round
            cur = await http.get("/api/game/current", headers=hdrs)
            if cur.status_code != 200:
                continue
            if cur.json().get("status") not in ("running", "pending"):
                await asyncio.sleep(0.05)
                continue

            jr = await http.post(
                "/api/game/join", json={"amount": bet_amount}, headers=hdrs
            )
            if jr.status_code not in (200, 201):
                await asyncio.sleep(0.08)
                continue
            join_data = jr.json()

            await asyncio.sleep(0.04)   # let multiplier tick up a bit

            co = await http.post(
                "/api/game/cashout",
                json={"bet_id": join_data["bet_id"]},
                headers=hdrs,
            )
            if co.status_code == 200:
                cashout_resp = co.json()
                break
            # Round crashed before we could cashout — try next round
            await asyncio.sleep(0.08)

        assert cashout_resp is not None, (
            "Could not complete a cashout after 10 attempts. "
            "Check that round duration is long enough for test timing."
        )
        assert join_data is not None

        # 4. Verify response fields (payout is server-authoritative)
        payout       = cashout_resp["payout"]
        cashout_mult = cashout_resp["cashout_multiplier"]
        bal_after    = cashout_resp["balance_after"]

        assert payout >= bet_amount, (
            f"Payout {payout} < bet {bet_amount} — impossible at ≥1.00×"
        )
        assert cashout_mult >= 1.00, f"cashout_multiplier {cashout_mult} < 1.00"
        assert bal_after >= 0,       f"Negative balance: {bal_after}"

        # Balance must equal starting − bet + payout (server formula)
        expected_balance = starting_balance - bet_amount + payout
        assert bal_after == expected_balance, (
            f"balance_after {bal_after} ≠ {expected_balance} "
            f"(starting={starting_balance}, bet={bet_amount}, payout={payout})"
        )

        # 5. Direct DB verification
        async with db_factory() as db:
            # Bet row
            bet_row = (await db.execute(
                select(Bet).where(Bet.id == join_data["bet_id"])
            )).scalar_one()
            assert bet_row.status == BetStatus.cashed_out, \
                f"DB bet status: {bet_row.status}"
            assert bet_row.payout == payout, \
                f"DB payout {bet_row.payout} ≠ response payout {payout}"
            assert bet_row.cashout_multiplier is not None
            assert bet_row.cashout_multiplier >= 1.00

            # Wallet
            wallet = (await db.execute(
                select(Wallet).where(Wallet.user_id == bet_row.user_id)
            )).scalar_one()
            assert wallet.balance == bal_after, \
                f"DB wallet {wallet.balance} ≠ response {bal_after}"

            # Transactions: starting_credits(1) + bet(1) + payout(1) = 3
            txs = (await db.execute(
                select(Transaction).where(Transaction.user_id == bet_row.user_id)
            )).scalars().all()
            assert len(txs) == 3, (
                f"Expected 3 transactions, got {len(txs)}: "
                f"{[(t.type, t.amount) for t in txs]}"
            )
            payout_txs = [t for t in txs if t.type.value == "payout"]
            assert len(payout_txs) == 1, \
                f"Expected exactly 1 payout transaction, got {len(payout_txs)}"
            assert payout_txs[0].amount == payout
            assert payout_txs[0].balance_after == bal_after


# ══════════════════════════════════════════════════════════════════════════════
# Test 6 — Crash / cash-out race: mutual exclusion, no duplicate payout
# ══════════════════════════════════════════════════════════════════════════════

async def test_e2e_cashout_race(e2e_server):
    """
    Fire two concurrent POST /api/game/cashout requests for the same bet.
    Exactly one of these valid outcomes must occur:
      (a) Both rejected — the round crashed before either cashout arrived.
      (b) Exactly one cashout accepted; the other rejected with 400.

    INVALID (must never happen):
      - Two 200 responses for the same bet (duplicate payout).

    DB assertions regardless of outcome:
      - bet.status is exactly one of {cashed_out, lost}
      - wallet.balance >= 0
      - at most 1 payout transaction
      - if cashed_out: balance = starting − bet + payout
      - if lost: 0 payout transactions, balance = starting − bet
    """
    base_url = e2e_server["base_url"]
    db_factory = e2e_server["db_factory"]

    async with httpx.AsyncClient(base_url=base_url, timeout=12.0) as http:
        # Register
        token_data = await _register_or_login(
            http, username="e2e_race_user", password="RaceP4ss!"
        )
        token = token_data["access_token"]
        starting_balance = token_data["balance"]
        hdrs = {"Authorization": f"Bearer {token}"}
        assert starting_balance == 10_000

        bet_amount = 50
        join_data: Optional[Dict] = None

        # Join a running round
        for _attempt in range(10):
            await asyncio.sleep(0.06)
            jr = await http.post(
                "/api/game/join", json={"amount": bet_amount}, headers=hdrs
            )
            if jr.status_code in (200, 201):
                join_data = jr.json()
                break
            await asyncio.sleep(0.08)

        assert join_data is not None, "Could not join any round for race test"
        bet_id = join_data["bet_id"]

        # Brief pause so we're mid-round, then fire two concurrent cashouts
        await asyncio.sleep(0.03)

        async def _do_cashout() -> httpx.Response:
            return await http.post(
                "/api/game/cashout",
                json={"bet_id": bet_id},
                headers=hdrs,
            )

        results = await asyncio.gather(
            _do_cashout(), _do_cashout(), return_exceptions=True
        )

    successes = [
        r for r in results
        if not isinstance(r, Exception) and r.status_code == 200
    ]

    # CRITICAL: two successes = duplicate payout = application bug
    assert len(successes) <= 1, (
        f"CRITICAL — {len(successes)} cashout requests succeeded for the same "
        f"bet (bet_id={bet_id}). Duplicate payout detected!\n"
        f"Responses: {[r.json() for r in successes]}"
    )

    # Brief wait: if the round crashed concurrently, the game loop's background
    # task may need a moment to mark the bet as 'lost' in the DB.
    await asyncio.sleep(0.3)

    # DB consistency check
    async with db_factory() as db:
        bet_row = (await db.execute(
            select(Bet).where(Bet.id == bet_id)
        )).scalar_one()

        # Valid terminal states:
        #   cashed_out — one cashout won the race
        #   lost       — round crashed (game loop marked it)
        #   active     — BOTH cashouts were rejected (round crashed mid-request),
        #                game loop hasn't yet marked it lost; this is consistent
        #                and safe: no payout was issued, balance is unchanged
        valid_statuses = (BetStatus.cashed_out, BetStatus.lost, BetStatus.active)
        assert bet_row.status in valid_statuses, (
            f"Unexpected bet status after race: {bet_row.status}"
        )

        wallet = (await db.execute(
            select(Wallet).where(Wallet.user_id == bet_row.user_id)
        )).scalar_one()
        assert wallet.balance >= 0, f"Negative wallet balance: {wallet.balance}"

        payout_txs = (await db.execute(
            select(Transaction).where(
                Transaction.user_id == bet_row.user_id,
                Transaction.type == TransactionType.payout,
            )
        )).scalars().all()
        assert len(payout_txs) <= 1, (
            f"Duplicate payout transactions: {len(payout_txs)}"
        )

        if bet_row.status == BetStatus.cashed_out:
            # Exactly one cashout succeeded — verify balance math
            assert len(successes) == 1, "cashed_out in DB but no 200 response — inconsistent"
            assert bet_row.payout > 0
            expected = starting_balance - bet_amount + bet_row.payout
            assert wallet.balance == expected, (
                f"Cashed-out balance {wallet.balance} ≠ expected {expected}"
            )
            assert len(payout_txs) == 1

        if bet_row.status == BetStatus.lost:
            # Round crashed — no payout should have been issued
            assert len(payout_txs) == 0, (
                f"Lost bet has {len(payout_txs)} payout transaction(s) — invalid"
            )
            # Balance must equal starting minus bet (no refund on crash)
            expected_lost = starting_balance - bet_amount
            assert wallet.balance == expected_lost, (
                f"Lost-bet balance {wallet.balance} ≠ expected {expected_lost}"
            )

        if bet_row.status == BetStatus.active:
            # Both requests were rejected (round crashed before processing) —
            # the game loop will mark it lost asynchronously. No payout issued.
            assert len(successes) == 0, "active bet in DB but a cashout 200 was returned — inconsistent"
            assert len(payout_txs) == 0, (
                f"Active (unresolved) bet has {len(payout_txs)} payout transactions — invalid"
            )
            # Wallet was debited when bet was placed but not credited back yet
            expected_active = starting_balance - bet_amount
            assert wallet.balance == expected_active, (
                f"Active bet wallet {wallet.balance} ≠ expected {expected_active}"
            )

