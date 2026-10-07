"""
Anti-Gravity Backend — Admin Service
Business logic for administrator operations, metrics, user management,
virtual-credit adjustments, configuration, audit logging, and health checks.

Critical Rule:
No mechanism exists in this service to modify authoritative round outcomes or crash multipliers.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    User, UserRole, UserStatus, Wallet, Round, Bet, BetStatus,
    Transaction, TransactionType, GameSettings, AuditLog
)
from backend.ws.connection_manager import manager
from backend.ws.game_loop import game_loop


_START_TIME = time.time()


# ── Audit Logging Helper ────────────────────────────────────────────────────────
async def log_audit(
    db: AsyncSession,
    action: str,
    admin_user_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[Dict[str, Any] | str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Create an append-only, immutable audit record."""
    details_str = json.dumps(details) if isinstance(details, dict) else details
    audit_entry = AuditLog(
        admin_user_id=admin_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details_str,
        ip_address=ip_address,
        created_at=datetime.now(timezone.utc),
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(audit_entry)
    return audit_entry


# ── Game Settings (Singleton) ───────────────────────────────────────────────────
async def get_or_create_settings(db: AsyncSession) -> GameSettings:
    """Fetch the singleton GameSettings record, creating default if absent."""
    result = await db.execute(select(GameSettings).limit(1))
    row = result.scalar_one_or_none()
    if row is None:
        row = GameSettings(
            minimum_bet=10,
            maximum_bet=10000,
            starting_balance=1000,
            house_edge=0.03,
            game_speed=1.0,
            animation_speed=1.0,
            betting_window_ms=5000,
            maintenance_mode=False,
            updated_at=datetime.now(timezone.utc),
            updated_by="system",
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


async def update_game_settings(
    db: AsyncSession,
    updates: Dict[str, Any],
    admin_user: User,
    ip_address: Optional[str] = None,
) -> GameSettings:
    """Update configurable game settings with strict validation and audit logging."""
    settings_row = await get_or_create_settings(db)

    # Super Admin check for house edge modification
    if "house_edge" in updates and updates["house_edge"] is not None:
        admin_role = admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role)
        if admin_role != "super_admin":
            raise PermissionError("Only SUPER_ADMIN can modify house_edge")

    changes = {}
    for key, value in updates.items():
        if value is not None and hasattr(settings_row, key):
            old_val = getattr(settings_row, key)
            if old_val != value:
                changes[key] = {"old": old_val, "new": value}
                setattr(settings_row, key, value)

    if changes:
        settings_row.updated_at = datetime.now(timezone.utc)
        settings_row.updated_by = admin_user.username
        await db.commit()
        await db.refresh(settings_row)

        await log_audit(
            db,
            action="update_settings",
            admin_user_id=admin_user.id,
            target_type="game_settings",
            target_id=str(settings_row.id),
            details={"changes": changes},
            ip_address=ip_address,
        )

    return settings_row


# ── Dashboard & System Metrics ─────────────────────────────────────────────────
async def get_dashboard_metrics(db: AsyncSession) -> Dict[str, Any]:
    """Compile real-time operational overview metrics."""
    # Total & active users
    total_users_res = await db.execute(select(func.count(User.id)))
    total_users = total_users_res.scalar() or 0

    active_users_res = await db.execute(
        select(func.count(User.id)).where(User.status == UserStatus.active)
    )
    active_users = active_users_res.scalar() or 0

    # Total credits in circulation
    circ_res = await db.execute(select(func.sum(Wallet.balance)))
    credits_in_circulation = circ_res.scalar() or 0

    # Games today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    games_today_res = await db.execute(
        select(func.count(Round.id)).where(Round.created_at >= today_start)
    )
    games_today = games_today_res.scalar() or 0

    # Cashout rate (cashed out bets vs total bets)
    total_bets_res = await db.execute(select(func.count(Bet.id)))
    total_bets = total_bets_res.scalar() or 0

    cashed_out_res = await db.execute(
        select(func.count(Bet.id)).where(Bet.status == BetStatus.cashed_out)
    )
    cashed_out = cashed_out_res.scalar() or 0
    cashout_rate = round(cashed_out / total_bets, 4) if total_bets > 0 else 0.0

    # Active round telemetry from cache or loop
    cache = game_loop.current_state_cache or {}
    current_round_id = cache.get("round_id")
    current_round_number = cache.get("round_number")
    current_status = cache.get("status", "idle")
    current_multiplier = float(cache.get("multiplier", 1.00))

    # Players in current round
    players_in_round = 0
    if current_round_id:
        p_res = await db.execute(
            select(func.count(Bet.id)).where(Bet.round_id == current_round_id)
        )
        players_in_round = p_res.scalar() or 0

    settings_row = await get_or_create_settings(db)

    return {
        "total_users": total_users,
        "active_users": active_users,
        "online_users": manager.active_count,
        "current_round_id": current_round_id,
        "current_round_number": current_round_number,
        "current_status": current_status,
        "current_multiplier": current_multiplier,
        "players_in_round": players_in_round,
        "games_today": games_today,
        "credits_in_circulation": credits_in_circulation,
        "cashout_rate": cashout_rate,
        "api_health": "healthy",
        "ws_connections": manager.active_count,
        "db_health": "connected",
        "maintenance_mode": settings_row.maintenance_mode,
    }


async def get_system_health(db: AsyncSession) -> Dict[str, Any]:
    """Detailed health check for all subsystems."""
    uptime = time.time() - _START_TIME
    db_ok = False
    try:
        await db.execute(select(func.count(User.id)))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "api_status": "ok",
        "db_status": "ok" if db_ok else "unreachable",
        "ws_status": "ok",
        "game_loop_status": "running" if game_loop.is_running else "stopped",
        "active_connections": manager.active_count,
        "background_tasks_ok": game_loop.is_running,
        "uptime_seconds": round(uptime, 2),
        "version": "0.2.0",
    }


# ── User Management ────────────────────────────────────────────────────────────
async def list_users(
    db: AsyncSession,
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List users with pagination, search by username/email, and role/status filters."""
    query = select(User, Wallet.balance).outerjoin(Wallet, User.id == Wallet.user_id)

    if search:
        query = query.where(
            (User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )
    if role:
        query = query.where(User.role == role)
    if status:
        query = query.where(User.status == status)

    query = query.order_by(User.id.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    output = []
    for u, balance in rows:
        output.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "status": u.status.value if hasattr(u.status, "value") else str(u.status),
            "balance": balance or 0,
            "created_at": u.created_at,
            "last_login_at": u.last_login_at,
        })
    return output


async def get_user_detail(db: AsyncSession, user_id: int) -> Optional[Dict[str, Any]]:
    """Get complete user information with wagering summary."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None

    # Wallet
    w_res = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = w_res.scalar_one_or_none()
    balance = wallet.balance if wallet else 0

    # Stats
    games_res = await db.execute(select(func.count(Bet.id)).where(Bet.user_id == user_id))
    games_played = games_res.scalar() or 0

    wager_res = await db.execute(select(func.sum(Bet.amount)).where(Bet.user_id == user_id))
    total_wagered = wager_res.scalar() or 0

    won_res = await db.execute(select(func.sum(Bet.payout)).where(Bet.user_id == user_id))
    total_won = won_res.scalar() or 0

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "status": user.status.value if hasattr(user.status, "value") else str(user.status),
        "balance": balance,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "games_played": games_played,
        "total_wagered": total_wagered,
        "total_won": total_won,
    }


async def update_user_status(
    db: AsyncSession,
    user_id: int,
    status: str,
    reason: Optional[str],
    admin_user: User,
    ip_address: Optional[str] = None,
) -> User:
    """Enable / ban user account with mandatory audit record."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError(f"User {user_id} not found")

    old_status = user.status.value if hasattr(user.status, "value") else str(user.status)
    user.status = UserStatus(status)
    await db.commit()
    await db.refresh(user)

    await log_audit(
        db,
        action="update_user_status",
        admin_user_id=admin_user.id,
        target_type="user",
        target_id=str(user.id),
        details={"old_status": old_status, "new_status": status, "reason": reason},
        ip_address=ip_address,
    )
    return user


async def update_user_role(
    db: AsyncSession,
    user_id: int,
    new_role: str,
    admin_user: User,
    ip_address: Optional[str] = None,
) -> User:
    """Super Admin only: Change user role."""
    admin_role = admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role)
    if admin_role != "super_admin":
        raise PermissionError("Only SUPER_ADMIN can modify user roles")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError(f"User {user_id} not found")

    old_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    user.role = UserRole(new_role)
    await db.commit()
    await db.refresh(user)

    await log_audit(
        db,
        action="update_user_role",
        admin_user_id=admin_user.id,
        target_type="user",
        target_id=str(user.id),
        details={"old_role": old_role, "new_role": new_role},
        ip_address=ip_address,
    )
    return user


# ── Virtual Credit Adjustments ─────────────────────────────────────────────────
async def adjust_user_wallet(
    db: AsyncSession,
    user_id: int,
    amount: int,
    reason: str,
    admin_user: User,
    ip_address: Optional[str] = None,
) -> Transaction:
    """
    Safely credit or debit virtual credits from a user's wallet with mandatory audit trail.
    Enforces positive balance constraint.
    """
    if amount == 0:
        raise ValueError("Adjustment amount cannot be zero")

    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise ValueError(f"Wallet for user {user_id} not found")

    balance_before = wallet.balance
    balance_after = balance_before + amount

    if balance_after < 0:
        raise ValueError(f"Adjustment would result in negative balance ({balance_after})")

    wallet.balance = balance_after

    tx = Transaction(
        user_id=user_id,
        type=TransactionType.admin_adjustment,
        amount=amount,
        balance_before=balance_before,
        balance_after=balance_after,
        reference_id=admin_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    await log_audit(
        db,
        action="wallet_adjustment",
        admin_user_id=admin_user.id,
        target_type="user_wallet",
        target_id=str(user_id),
        details={
            "amount": amount,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "reason": reason,
            "transaction_id": tx.id,
        },
        ip_address=ip_address,
    )

    return tx


# ── Round Monitoring & History ─────────────────────────────────────────────────
async def list_rounds(
    db: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List rounds for admin monitoring."""
    query = select(Round)
    if status:
        query = query.where(Round.status == status)
    query = query.order_by(Round.id.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    rounds = result.scalars().all()

    output = []
    for r in rounds:
        # Aggregate bets
        b_res = await db.execute(
            select(
                func.count(Bet.id),
                func.sum(Bet.amount),
                func.sum(Bet.payout),
            ).where(Bet.round_id == r.id)
        )
        total_bets, total_wagered, total_payout = b_res.one()

        # Seed protection: only reveal server_seed if crashed/ended
        revealed_seed = r.server_seed if r.status in [RoundStatus.crashed, RoundStatus.cancelled] else None

        output.append({
            "id": r.id,
            "round_number": r.round_number,
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "server_seed_hash": r.server_seed_hash,
            "server_seed": revealed_seed,
            "crash_multiplier": r.crash_multiplier,
            "started_at": r.started_at,
            "ended_at": r.ended_at,
            "created_at": r.created_at,
            "total_bets": total_bets or 0,
            "total_wagered": total_wagered or 0,
            "total_payout": total_payout or 0,
        })
    return output


async def get_round_detail(db: AsyncSession, round_id: int) -> Optional[Dict[str, Any]]:
    """Get full details of a specific round including all player bets."""
    result = await db.execute(select(Round).where(Round.id == round_id))
    r = result.scalar_one_or_none()
    if not r:
        return None

    bets_res = await db.execute(
        select(Bet, User.username)
        .join(User, Bet.user_id == User.id)
        .where(Bet.round_id == round_id)
        .order_by(Bet.id.asc())
    )
    bet_rows = bets_res.all()

    bet_items = []
    total_wagered = 0
    total_payout = 0
    for bet, uname in bet_rows:
        total_wagered += bet.amount
        total_payout += bet.payout
        bet_items.append({
            "bet_id": bet.id,
            "user_id": bet.user_id,
            "username": uname,
            "amount": bet.amount,
            "cashout_multiplier": bet.cashout_multiplier,
            "payout": bet.payout,
            "status": bet.status.value if hasattr(bet.status, "value") else str(bet.status),
            "created_at": bet.created_at,
        })

    revealed_seed = r.server_seed if r.status in [RoundStatus.crashed, RoundStatus.cancelled] else None

    return {
        "id": r.id,
        "round_number": r.round_number,
        "status": r.status.value if hasattr(r.status, "value") else str(r.status),
        "server_seed_hash": r.server_seed_hash,
        "server_seed": revealed_seed,
        "crash_multiplier": r.crash_multiplier,
        "started_at": r.started_at,
        "ended_at": r.ended_at,
        "created_at": r.created_at,
        "total_bets": len(bet_items),
        "total_wagered": total_wagered,
        "total_payout": total_payout,
        "bets": bet_items,
    }


# ── Transactions & Audit Logs ──────────────────────────────────────────────────
async def list_transactions(
    db: AsyncSession,
    user_id: Optional[int] = None,
    tx_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List financial transactions for auditing."""
    query = select(Transaction, User.username).join(User, Transaction.user_id == User.id)
    if user_id:
        query = query.where(Transaction.user_id == user_id)
    if tx_type:
        query = query.where(Transaction.type == tx_type)
    query = query.order_by(Transaction.id.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    output = []
    for tx, uname in rows:
        output.append({
            "id": tx.id,
            "user_id": tx.user_id,
            "username": uname,
            "type": tx.type.value if hasattr(tx.type, "value") else str(tx.type),
            "amount": tx.amount,
            "balance_before": tx.balance_before,
            "balance_after": tx.balance_after,
            "reference_id": tx.reference_id,
            "created_at": tx.created_at,
        })
    return output


async def list_audit_logs(
    db: AsyncSession,
    action: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List append-only audit log records."""
    query = (
        select(AuditLog, User.username)
        .outerjoin(User, AuditLog.admin_user_id == User.id)
    )
    if action:
        query = query.where(AuditLog.action == action)
    query = query.order_by(AuditLog.id.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    output = []
    for log, uname in rows:
        output.append({
            "id": log.id,
            "admin_user_id": log.admin_user_id,
            "admin_username": uname,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at,
        })
    return output
