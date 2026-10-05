"""
Anti-Gravity Backend — Fairness Router (Sprint 5)
GET /api/fairness/stats
GET /api/fairness/{round_id}
GET /api/fairness/{round_id}/verify
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.database import get_db
from backend.models import User
from backend.schemas import (
    FairnessInfo,
    FairnessStatsResponse,
    FairnessVerifyResponse,
)
from backend.services.fairness_service import FairnessService

router = APIRouter(prefix="/api/fairness", tags=["fairness"])


@router.get("/stats", response_model=FairnessStatsResponse)
async def fairness_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return aggregate statistical metrics on completed virtual rounds.
    Includes count, min, max, average, median, and distribution buckets.
    Historical statistics are purely observational and do not influence future outcomes.
    """
    return await FairnessService.get_fairness_statistics(db)


@router.get("/{round_id}", response_model=FairnessInfo)
async def fairness_info(
    round_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return fairness data for a specific round.
    - Before/during the round: only the server_seed_hash is shown.
    - After the round crashes: the full server_seed and crash_multiplier are revealed,
      so anyone can independently verify the result.
    """
    try:
        return await FairnessService.get_round_fairness_info(db, round_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{round_id}/verify", response_model=FairnessVerifyResponse)
async def verify_round(
    round_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cryptographically verify that the revealed server_seed matches the committed hash
    and that the crash_multiplier was derived from it correctly.
    Only available after the round has crashed (seed revealed).
    """
    try:
        return await FairnessService.verify_round_by_id(db, round_id)
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        elif "not crashed" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err_msg)
