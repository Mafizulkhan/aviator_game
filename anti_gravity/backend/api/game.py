"""
Anti-Gravity Backend — Game Router
GET  /api/game/current
POST /api/game/join
POST /api/game/cashout
GET  /api/game/history
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models import User
from backend.schemas import (
    CurrentRoundResponse, JoinRoundRequest, JoinRoundResponse,
    CashoutRequest, CashoutResponse, GameHistoryItem,
)
from backend.api.deps import get_current_user
from backend.services.game_service import (
    get_current_round, join_round, cashout,
    compute_current_multiplier, get_game_history,
    resolve_round_if_crashed, start_round,
)
from backend.services.rate_limiter import RateLimiter
from backend.models import RoundStatus

router = APIRouter(prefix="/api/game", tags=["game"])


@router.get("/current", response_model=CurrentRoundResponse)
async def current_round(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current active (or pending) round info including live multiplier."""
    round_row = await get_current_round(db)

    # Auto-start if pending
    if round_row.status == RoundStatus.pending:
        round_row = await start_round(db, round_row)

    # Check crash
    await resolve_round_if_crashed(db, round_row)
    await db.refresh(round_row)

    mult = compute_current_multiplier(round_row) if round_row.status == RoundStatus.running else None

    return CurrentRoundResponse(
        round_id=round_row.id,
        round_number=round_row.round_number,
        status=round_row.status.value,
        server_seed_hash=round_row.server_seed_hash,
        started_at=round_row.started_at,
        current_multiplier=mult,
    )


@router.post("/join", response_model=JoinRoundResponse, status_code=status.HTTP_201_CREATED)
async def join(
    body: JoinRoundRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Place a bet on the current active round.
    The server validates and deducts from the wallet — never trust client balance.
    """
    try:
        bet, round_row, new_balance = await join_round(db, current_user.id, body.amount)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return JoinRoundResponse(
        bet_id=bet.id,
        round_id=round_row.id,
        round_number=round_row.round_number,
        amount=bet.amount,
        balance_after=new_balance,
        server_seed_hash=round_row.server_seed_hash,
        status=bet.status.value,
    )


@router.post("/cashout", response_model=CashoutResponse)
async def request_cashout(
    body: CashoutRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cash out on a running round with rate limiting.
    The server determines the multiplier from its own clock — client multiplier is ignored.
    """
    RateLimiter.check_http_rate_limit(
        request,
        action="cashout",
        max_requests=settings.RATE_LIMIT_CASHOUT_PER_MINUTE,
    )
    try:
        bet, round_row, new_balance = await cashout(db, current_user.id, body.bet_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return CashoutResponse(
        bet_id=bet.id,
        round_number=round_row.round_number,
        cashout_multiplier=bet.cashout_multiplier,
        payout=bet.payout,
        balance_after=new_balance,
    )


@router.get("/history", response_model=list[GameHistoryItem])
async def game_history(
    limit: int = Query(20, ge=1, le=100, description="Number of historical rounds to return"),
    offset: int = Query(0, ge=0, description="Pagination offset — number of records to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return recent completed (crashed) rounds with pagination bounds."""
    rounds = await get_game_history(db, limit=limit, offset=offset)
    return [
        GameHistoryItem(
            round_number=r.round_number,
            crash_multiplier=r.crash_multiplier,
            status=r.status.value,
            started_at=r.started_at,
            ended_at=r.ended_at,
        )
        for r in rounds
    ]
