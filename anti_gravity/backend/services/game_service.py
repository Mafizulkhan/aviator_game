"""
Anti-Gravity Backend — Game Service
Manages round lifecycle, join (bet), and cash-out.

Architecture principle: the server controls the game. The client only displays state.
- Crash point is generated server-side before round starts.
- Cash-out validity is determined by the server's authoritative clock.
- Client-supplied multiplier/balance/payout values are NEVER trusted.
"""

from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import Round, Bet, BetStatus, RoundStatus
from backend.services.wallet_service import deduct_bet, add_payout
from backend.services.audit_service import AuditService
from app.engine.game_engine import FairnessEngine, MultiplierEngine


# ── Current active round (in-memory for Sprint 3 / DEMO_MODE) ─────────────────
# In Sprint 4 this will be replaced by a persistent server-side ticker via WebSocket.
# For now the server creates one round at a time; the round is "running" and the
# multiplier is computed from (now - started_at) on every request.
_active_round_internal: dict = {}   # {round_id: server_seed} — holds pre-generated secret seeds


def _get_elapsed(round_row: Round) -> float:
    """Seconds elapsed since the round started."""
    if round_row.started_at is None:
        return 0.0
    now = datetime.now(timezone.utc)
    return (now - round_row.started_at.replace(tzinfo=timezone.utc)).total_seconds()


def compute_current_multiplier(round_row: Round) -> float:
    """Compute the live multiplier from elapsed time. Never trust the client."""
    if round_row.status != RoundStatus.running:
        return 1.00
    elapsed = _get_elapsed(round_row)
    return MultiplierEngine.multiplier_at(elapsed)


def _crash_time_elapsed(crash_multiplier: float) -> float:
    """How many seconds after start the crash happens."""
    return MultiplierEngine.time_at_multiplier(crash_multiplier)


# ── Round helpers ──────────────────────────────────────────────────────────────
async def get_current_round(db: AsyncSession) -> Round:
    """
    Return the most recent non-cancelled round.
    Auto-creates a new pending round if none exists.
    """
    result = await db.execute(
        select(Round)
        .where(Round.status.in_([RoundStatus.pending, RoundStatus.running]))
        .order_by(Round.id.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = await _create_new_round(db)
    return row


async def _create_new_round(db: AsyncSession) -> Round:
    """Create a new pending round with a pre-committed fairness seed."""
    # Get the next round number
    result = await db.execute(select(func.max(Round.round_number)))
    max_num = result.scalar() or 0

    seed = FairnessEngine.generate_seed()
    seed_hash = FairnessEngine.hash_seed(seed)

    # Store the plaintext seed in a module-level dict (keyed by round_number).
    # The DB row keeps only the hash until the round ends.
    round_number = max_num + 1
    round_row = Round(
        round_number=round_number,
        server_seed_hash=seed_hash,
        server_seed=None,           # revealed after round
        crash_multiplier=None,      # revealed after round
        status=RoundStatus.pending,
    )
    db.add(round_row)
    await db.flush()

    # Cache the real seed so we can compute crash point without exposing it
    _active_round_internal[round_row.id] = seed
    await db.commit()
    await db.refresh(round_row)
    AuditService.log_round_created(round_row.id, round_row.round_number, seed_hash)
    return round_row


async def start_round(db: AsyncSession, round_row: Round) -> Round:
    """Transition a pending round to running (sets started_at)."""
    if round_row.status != RoundStatus.pending:
        return round_row
    round_row.status = RoundStatus.running
    round_row.started_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(round_row)
    AuditService.log_round_started(round_row.id, round_row.round_number, round_row.started_at)
    return round_row


async def resolve_round_if_crashed(db: AsyncSession, round_row: Round) -> bool:
    """
    Check whether the round has crashed (server-authoritative).
    If yes, mark it crashed, reveal seed + crash_multiplier, mark all active bets as lost.
    Returns True if the round just crashed.
    """
    if round_row.status != RoundStatus.running:
        return False

    seed = _active_round_internal.get(round_row.id)
    if seed is None:
        return False

    crash_mult = FairnessEngine.calculate_crash_point(seed, round_row.round_number)
    crash_elapsed = _crash_time_elapsed(crash_mult)
    elapsed = _get_elapsed(round_row)

    if elapsed < crash_elapsed:
        return False   # not crashed yet

    # ── Round has crashed ──
    round_row.status = RoundStatus.crashed
    round_row.ended_at = datetime.now(timezone.utc)
    round_row.server_seed = seed           # reveal seed
    round_row.crash_multiplier = crash_mult

    # Mark all active bets as lost
    result = await db.execute(
        select(Bet).where(Bet.round_id == round_row.id, Bet.status == BetStatus.active)
    )
    for bet in result.scalars().all():
        bet.status = BetStatus.lost

    await db.commit()
    await db.refresh(round_row)
    AuditService.log_round_crashed(round_row.id, round_row.round_number, crash_mult, round_row.ended_at)

    # Queue new round for next request
    _active_round_internal.pop(round_row.id, None)
    return True


# ── Player actions ─────────────────────────────────────────────────────────────
async def join_round(
    db: AsyncSession,
    user_id: int,
    amount: int,
) -> Tuple[Bet, Round, int]:
    """
    Place a bet on the current round.
    - Validates bet amount server-side.
    - Deducts from wallet atomically.
    - Returns (bet, round, new_balance).
    Raises ValueError on any validation failure.
    """
    round_row = await get_current_round(db)

    # Auto-start pending rounds
    if round_row.status == RoundStatus.pending:
        round_row = await start_round(db, round_row)

    if round_row.status != RoundStatus.running:
        raise ValueError("No active round to join")

    # Check if the round has already crashed
    crashed = await resolve_round_if_crashed(db, round_row)
    if crashed:
        raise ValueError("Round just ended — please try again")

    # Prevent duplicate bets
    existing = await db.execute(
        select(Bet).where(Bet.round_id == round_row.id, Bet.user_id == user_id)
    )
    if existing.scalar_one_or_none():
        raise ValueError("You already have a bet in this round")

    # Deduct bet from wallet (raises ValueError if insufficient)
    async with db.begin_nested():
        new_balance = await deduct_bet(db, user_id, amount, reference_id=None)

        bet = Bet(
            round_id=round_row.id,
            user_id=user_id,
            amount=amount,
            status=BetStatus.active,
        )
        db.add(bet)
        await db.flush()

    await db.commit()
    await db.refresh(bet)
    await db.refresh(round_row)
    return bet, round_row, new_balance


async def cashout(
    db: AsyncSession,
    user_id: int,
    bet_id: int,
) -> Tuple[Bet, Round, int]:
    """
    Server-authoritative cash-out.
    - Validates round is still running at the moment of the request.
    - Calculates multiplier from server time — NEVER trusts client value.
    - Pays out once only.

    Race-safety
    -----------
    SQLite does NOT honour SELECT ... FOR UPDATE (with_for_update() is silently
    ignored by aiosqlite).  We therefore use an atomic

        UPDATE bets SET status='cashed_out', ... WHERE id=? AND status='active'

    and check the affected rowcount.  Exactly one concurrent request will see
    rowcount=1; all others see rowcount=0 and are rejected immediately, before
    any wallet mutation occurs.  This is the only race-safe approach for SQLite.

    Returns (bet, round, new_balance).
    Raises ValueError on any rejection.
    """
    # ── 0. Verify ownership (no lock needed — just a read) ────────────────────
    check = await db.execute(
        select(Bet).where(Bet.id == bet_id, Bet.user_id == user_id)
    )
    bet = check.scalar_one_or_none()
    if bet is None:
        AuditService.log_cashout_rejected(0, user_id, bet_id, "Bet not found")
        raise ValueError("Bet not found")
    if bet.status != BetStatus.active:
        AuditService.log_cashout_rejected(bet.round_id, user_id, bet_id, "Cash-out already processed")
        raise ValueError("Cash-out already processed for this bet")

    # ── 1. Fetch round (read only — crash check uses server clock) ─────────────
    result2 = await db.execute(
        select(Round).where(Round.id == bet.round_id)
    )
    round_row = result2.scalar_one_or_none()
    if round_row is None:
        AuditService.log_cashout_rejected(bet.round_id, user_id, bet_id, "Round not found")
        raise ValueError("Round not found")

    # ── 2. Check crash FIRST using server clock (never trust client data) ──────
    crashed = await resolve_round_if_crashed(db, round_row)
    if crashed or round_row.status == RoundStatus.crashed:
        # Mark bet lost; the atomic UPDATE below is skipped on raise
        await db.execute(
            update(Bet)
            .where(Bet.id == bet_id, Bet.status == BetStatus.active)
            .values(status=BetStatus.lost)
        )
        await db.commit()
        AuditService.log_cashout_rejected(round_row.id, user_id, bet_id, "Round crashed before cash-out")
        raise ValueError("Round crashed before your cash-out arrived")

    if round_row.status != RoundStatus.running:
        AuditService.log_cashout_rejected(round_row.id, user_id, bet_id, "Round is not running")
        raise ValueError("Round is not running")

    # ── 3. Compute server-authoritative multiplier ─────────────────────────────
    cashout_mult = compute_current_multiplier(round_row)

    seed = _active_round_internal.get(round_row.id)
    if seed:
        crash_mult = FairnessEngine.calculate_crash_point(seed, round_row.round_number)
        if cashout_mult >= crash_mult:
            await resolve_round_if_crashed(db, round_row)
            await db.execute(
                update(Bet)
                .where(Bet.id == bet_id, Bet.status == BetStatus.active)
                .values(status=BetStatus.lost)
            )
            await db.commit()
            AuditService.log_cashout_rejected(round_row.id, user_id, bet_id, "Round crashed before cash-out")
            raise ValueError("Round crashed before your cash-out arrived")

    payout = int(bet.amount * cashout_mult)
    now_ts = datetime.now(timezone.utc)

    # ── 4. ATOMIC status transition — the race gate ───────────────────────────
    # Only one concurrent request can win this UPDATE (rowcount == 1).
    # All others see rowcount == 0 and are rejected before touching the wallet.
    lock_result = await db.execute(
        update(Bet)
        .where(Bet.id == bet_id, Bet.status == BetStatus.active)
        .values(
            status=BetStatus.cashed_out,
            cashout_multiplier=cashout_mult,
            payout=payout,
            cashed_out_at=now_ts,
        )
    )
    if lock_result.rowcount == 0:
        # Another concurrent request already committed — reject this one
        await db.rollback()
        AuditService.log_cashout_rejected(round_row.id, user_id, bet_id, "Cash-out race lost — already processed")
        raise ValueError("Cash-out already processed for this bet")

    # Keep in-memory ORM instance in sync with atomic DB update
    bet.status = BetStatus.cashed_out
    bet.cashout_multiplier = cashout_mult
    bet.payout = payout
    bet.cashed_out_at = now_ts

    # ── 5. Update wallet (only reached by the winning request) ────────────────
    new_balance = await add_payout(db, user_id, payout, reference_id=bet_id)

    await db.commit()
    await db.refresh(round_row)
    AuditService.log_cashout_accepted(round_row.id, user_id, bet_id, cashout_mult, payout, new_balance)
    return bet, round_row, new_balance


# ── History ────────────────────────────────────────────────────────────────────
async def get_game_history(db: AsyncSession, limit: int = 50, offset: int = 0) -> list[Round]:
    result = await db.execute(
        select(Round)
        .where(Round.status == RoundStatus.crashed)
        .order_by(Round.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_player_bet_history(db: AsyncSession, user_id: int, limit: int = 50, offset: int = 0) -> list:
    """Return joined Bet + Round data for the player's history."""
    result = await db.execute(
        select(Bet, Round)
        .join(Round, Bet.round_id == Round.id)
        .where(Bet.user_id == user_id)
        .order_by(Bet.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.all()
