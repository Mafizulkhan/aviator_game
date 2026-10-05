"""
Anti-Gravity Backend — Player Router
GET /api/player/profile
GET /api/player/balance
GET /api/player/history
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import User, Wallet, Bet, BetStatus
from backend.schemas import PlayerProfile, BalanceResponse, BetHistoryItem
from backend.api.deps import get_current_user
from backend.services.game_service import get_player_bet_history

router = APIRouter(prefix="/api/player", tags=["player"])


@router.get("/profile", response_model=PlayerProfile)
async def profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the authenticated player's profile with computed stats.
    Uses SQL aggregates instead of loading all rows into Python memory.
    """
    # Single SQL query for all stats
    stats_result = await db.execute(
        select(
            func.count(Bet.id).label("games_played"),
            func.sum(case((Bet.status == BetStatus.cashed_out, 1), else_=0)).label("wins"),
            func.sum(case((Bet.status == BetStatus.lost, 1), else_=0)).label("losses"),
            func.max(Bet.cashout_multiplier).label("best_cashout"),
        ).where(Bet.user_id == current_user.id)
    )
    row = stats_result.one()

    return PlayerProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        status=current_user.status.value,
        created_at=current_user.created_at,
        games_played=row.games_played or 0,
        wins=row.wins or 0,
        losses=row.losses or 0,
        best_cashout=row.best_cashout,
    )


@router.get("/balance", response_model=BalanceResponse)
async def balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated player's current virtual-credit balance."""
    # Only fetch the balance column — no need to load the full Wallet ORM object
    result = await db.execute(
        select(Wallet.balance).where(Wallet.user_id == current_user.id)
    )
    bal = result.scalar_one_or_none() or 0
    return BalanceResponse(user_id=current_user.id, username=current_user.username, balance=bal)


@router.get("/history", response_model=list[BetHistoryItem])
async def history(
    limit: int = Query(50, ge=1, le=200, description="Max records to return (1–200)"),
    offset: int = Query(0, ge=0, description="Pagination offset — number of records to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated player's bet history (most recent first) with pagination."""
    rows = await get_player_bet_history(db, current_user.id, limit=limit, offset=offset)
    items = []
    for bet, round_row in rows:
        items.append(BetHistoryItem(
            bet_id=bet.id,
            round_number=round_row.round_number,
            amount=bet.amount,
            cashout_multiplier=bet.cashout_multiplier,
            crash_multiplier=round_row.crash_multiplier,
            payout=bet.payout,
            status=bet.status.value,
            created_at=bet.created_at,
        ))
    return items

