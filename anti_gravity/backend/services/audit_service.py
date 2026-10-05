"""
Anti-Gravity Backend — Audit Service (Sprint 5)
Provides structured, non-sensitive audit logging and round audit record inspection.
Immutable historical records ensure game integrity and transparency.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.game_engine import FairnessEngine
from backend.models import Bet, BetStatus, Round, RoundStatus
from backend.schemas import AuditRoundResponse

# Dedicated audit logger
audit_logger = logging.getLogger("anti_gravity.audit")
if not audit_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[AUDIT %(asctime)s] %(message)s")
    handler.setFormatter(formatter)
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)


class AuditService:
    """Service layer for audit event logging and round inspection."""

    # ── Structured Audit Logging ───────────────────────────────────────────────
    @staticmethod
    def _emit_audit_event(event_type: str, data: Dict[str, Any]) -> None:
        """
        Emit a structured JSON audit event log.
        Sanitizes data to ensure no passwords, tokens, or secret unrevealed seeds are logged.
        """
        payload = {
            "audit_event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        # Redact sensitive fields if present
        for sensitive_key in ("password", "password_hash", "access_token", "token"):
            if sensitive_key in payload:
                payload[sensitive_key] = "[REDACTED]"

        audit_logger.info(json.dumps(payload, default=str))

    @classmethod
    def log_round_created(cls, round_id: int, round_number: int, server_seed_hash: str) -> None:
        cls._emit_audit_event(
            "round_created",
            {
                "round_id": round_id,
                "round_number": round_number,
                "server_seed_hash": server_seed_hash,
            },
        )

    @classmethod
    def log_round_started(cls, round_id: int, round_number: int, started_at: Optional[datetime] = None) -> None:
        cls._emit_audit_event(
            "round_started",
            {
                "round_id": round_id,
                "round_number": round_number,
                "started_at": (started_at or datetime.now(timezone.utc)).isoformat(),
            },
        )

    @classmethod
    def log_round_crashed(
        cls,
        round_id: int,
        round_number: int,
        crash_multiplier: float,
        ended_at: Optional[datetime] = None,
    ) -> None:
        cls._emit_audit_event(
            "round_crashed",
            {
                "round_id": round_id,
                "round_number": round_number,
                "crash_multiplier": crash_multiplier,
                "ended_at": (ended_at or datetime.now(timezone.utc)).isoformat(),
            },
        )

    @classmethod
    def log_round_ended(cls, round_id: int, round_number: int) -> None:
        cls._emit_audit_event(
            "round_ended",
            {
                "round_id": round_id,
                "round_number": round_number,
            },
        )

    @classmethod
    def log_cashout_accepted(
        cls,
        round_id: int,
        user_id: int,
        bet_id: int,
        multiplier: float,
        payout: int,
        balance_after: int,
    ) -> None:
        cls._emit_audit_event(
            "cashout_accepted",
            {
                "round_id": round_id,
                "user_id": user_id,
                "bet_id": bet_id,
                "multiplier": multiplier,
                "payout": payout,
                "balance_after": balance_after,
            },
        )

    @classmethod
    def log_cashout_rejected(
        cls,
        round_id: int,
        user_id: int,
        bet_id: int,
        reason: str,
    ) -> None:
        cls._emit_audit_event(
            "cashout_rejected",
            {
                "round_id": round_id,
                "user_id": user_id,
                "bet_id": bet_id,
                "reason": reason,
            },
        )

    # ── Audit Query ────────────────────────────────────────────────────────────
    @classmethod
    async def get_round_audit_record(
        cls,
        db: AsyncSession,
        round_id: int,
    ) -> AuditRoundResponse:
        """
        Fetch a comprehensive audit record for a round.
        Includes round lifecycle timestamps, fairness parameters, and bet summary statistics.
        """
        result = await db.execute(select(Round).where(Round.id == round_id))
        round_row = result.scalar_one_or_none()
        if round_row is None:
            raise ValueError(f"Round {round_id} not found")

        # Fetch aggregated bet stats for this round in a single SQL query
        stats_res = await db.execute(
            select(
                func.count(Bet.id).label("total_bets"),
                func.coalesce(func.sum(Bet.amount), 0).label("total_wagered"),
                func.coalesce(func.sum(Bet.payout), 0).label("total_payout"),
                func.coalesce(func.sum(case((Bet.status == BetStatus.cashed_out, 1), else_=0)), 0).label("cashed_out_count"),
                func.coalesce(func.sum(case((Bet.status == BetStatus.lost, 1), else_=0)), 0).label("lost_count"),
            ).where(Bet.round_id == round_id)
        )
        stats_row = stats_res.one()

        total_bets = stats_row.total_bets or 0
        total_wagered = int(stats_row.total_wagered or 0)
        total_payout = int(stats_row.total_payout or 0)
        cashed_out_count = int(stats_row.cashed_out_count or 0)
        lost_count = int(stats_row.lost_count or 0)

        # Verification status if round is finished
        verified: Optional[bool] = None
        is_revealed = round_row.status == RoundStatus.crashed
        if is_revealed and round_row.server_seed and round_row.crash_multiplier is not None:
            verified = FairnessEngine.verify_round(
                round_row.server_seed,
                round_row.server_seed_hash,
                round_row.round_number,
                round_row.crash_multiplier,
            )

        return AuditRoundResponse(
            round_id=round_row.id,
            round_number=round_row.round_number,
            status=round_row.status.value,
            created_at=round_row.created_at,
            started_at=round_row.started_at,
            ended_at=round_row.ended_at,
            server_seed_hash=round_row.server_seed_hash,
            server_seed=round_row.server_seed if is_revealed else None,
            crash_multiplier=round_row.crash_multiplier if is_revealed else None,
            verified=verified,
            total_bets=total_bets,
            total_wagered=total_wagered,
            total_payout=total_payout,
            cashed_out_count=cashed_out_count,
            lost_count=lost_count,
        )
