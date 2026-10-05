"""
Anti-Gravity Backend — Audit Router (Sprint 5)
GET /api/audit/round/{round_id}
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.database import get_db
from backend.models import User
from backend.schemas import AuditRoundResponse
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/round/{round_id}", response_model=AuditRoundResponse)
async def audit_round(
    round_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return comprehensive, non-sensitive audit records for a given round.
    Provides lifecycle timestamps, seed commitment hashes, revealed secrets (when lifecycle allows),
    verification status, and aggregated wagering/payout metrics.
    """
    try:
        return await AuditService.get_round_audit_record(db, round_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
