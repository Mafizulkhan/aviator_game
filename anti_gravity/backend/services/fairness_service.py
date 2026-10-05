"""
Anti-Gravity Backend — Fairness Service (Sprint 5)
Handles provably-fair seed commitment, verification, and statistics.
Uses the authoritative FairnessEngine algorithms — never trusts client input.
"""

from __future__ import annotations

import statistics
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.game_engine import FairnessEngine
from backend.models import Round, RoundStatus
from backend.schemas import (
    DistributionBucket,
    FairnessInfo,
    FairnessStatsResponse,
    FairnessVerifyResponse,
)


class FairnessService:
    """Service layer for provably-fair game verification and aggregate statistics."""

    @staticmethod
    def generate_seed() -> str:
        """Generate a cryptographically secure 256-bit server seed."""
        return FairnessEngine.generate_seed()

    @staticmethod
    def hash_seed(seed: str) -> str:
        """Compute the SHA-256 commitment hash of a server seed."""
        return FairnessEngine.hash_seed(seed)

    @staticmethod
    def calculate_crash_point(seed: str, round_number: int) -> float:
        """Deterministically derive the crash multiplier from seed and round identifier."""
        return FairnessEngine.calculate_crash_point(seed, round_number)

    @staticmethod
    def verify_round(
        seed: str,
        seed_hash: str,
        round_number: int,
        crash_multiplier: float,
    ) -> bool:
        """Verify that the revealed seed and crash multiplier match the commitment."""
        return FairnessEngine.verify_round(seed, seed_hash, round_number, crash_multiplier)

    @classmethod
    async def get_round_fairness_info(
        cls,
        db: AsyncSession,
        round_id: int,
    ) -> FairnessInfo:
        """
        Return public fairness details for a round.
        - While active (pending/running): server_seed and crash_multiplier remain hidden (None).
        - Once crashed: reveals seed and crash multiplier for independent verification.
        """
        result = await db.execute(select(Round).where(Round.id == round_id))
        round_row = result.scalar_one_or_none()
        if round_row is None:
            raise ValueError(f"Round {round_id} not found")

        # Only reveal secret seed and final crash multiplier after round crashes
        is_revealed = round_row.status == RoundStatus.crashed
        return FairnessInfo(
            round_id=round_row.id,
            round_number=round_row.round_number,
            server_seed_hash=round_row.server_seed_hash,
            server_seed=round_row.server_seed if is_revealed else None,
            crash_multiplier=round_row.crash_multiplier if is_revealed else None,
            status=round_row.status.value,
        )

    @classmethod
    async def verify_round_by_id(
        cls,
        db: AsyncSession,
        round_id: int,
    ) -> FairnessVerifyResponse:
        """
        Cryptographically verify the result of a completed round.
        Raises ValueError if round is not found, not completed, or data is missing.
        """
        result = await db.execute(select(Round).where(Round.id == round_id))
        round_row = result.scalar_one_or_none()
        if round_row is None:
            raise ValueError(f"Round {round_id} not found")

        if round_row.status != RoundStatus.crashed:
            raise ValueError("Round has not crashed yet — seed not yet revealed")

        if round_row.server_seed is None or round_row.crash_multiplier is None:
            raise ValueError("Round data incomplete — missing revealed seed or crash multiplier")

        verified = cls.verify_round(
            round_row.server_seed,
            round_row.server_seed_hash,
            round_row.round_number,
            round_row.crash_multiplier,
        )

        return FairnessVerifyResponse(
            round_id=round_row.id,
            round_number=round_row.round_number,
            server_seed=round_row.server_seed,
            server_seed_hash=round_row.server_seed_hash,
            crash_multiplier=round_row.crash_multiplier,
            verified=verified,
            message="Round result verified ✓" if verified else "Verification FAILED — possible tampering",
        )

    @classmethod
    async def get_fairness_statistics(
        cls,
        db: AsyncSession,
    ) -> FairnessStatsResponse:
        """
        Compute aggregate fairness statistics from all completed (crashed) rounds.
        Historical statistics are strictly observational and do NOT influence future outcomes.
        """
        result = await db.execute(
            select(Round.crash_multiplier)
            .where(
                Round.status == RoundStatus.crashed,
                Round.crash_multiplier.isnot(None),
            )
            .order_by(Round.id.asc())
        )
        crashes = [float(c) for c in result.scalars().all() if c is not None]

        total = len(crashes)
        if total == 0:
            buckets = [
                DistributionBucket(bucket="< 1.20x", count=0, percentage=0.0),
                DistributionBucket(bucket="1.20x–1.49x", count=0, percentage=0.0),
                DistributionBucket(bucket="1.50x–1.99x", count=0, percentage=0.0),
                DistributionBucket(bucket="2.00x–4.99x", count=0, percentage=0.0),
                DistributionBucket(bucket="5.00x–9.99x", count=0, percentage=0.0),
                DistributionBucket(bucket="10.00x+", count=0, percentage=0.0),
            ]
            return FairnessStatsResponse(
                total_completed_rounds=0,
                min_crash_multiplier=None,
                max_crash_multiplier=None,
                average_crash_multiplier=None,
                median_crash_multiplier=None,
                distribution_buckets=buckets,
            )

        min_val = min(crashes)
        max_val = max(crashes)
        avg_val = round(sum(crashes) / total, 2)
        med_val = round(float(statistics.median(crashes)), 2)

        # Count distribution buckets
        b1 = sum(1 for c in crashes if c < 1.20)
        b2 = sum(1 for c in crashes if 1.20 <= c < 1.50)
        b3 = sum(1 for c in crashes if 1.50 <= c < 2.00)
        b4 = sum(1 for c in crashes if 2.00 <= c < 5.00)
        b5 = sum(1 for c in crashes if 5.00 <= c < 10.00)
        b6 = sum(1 for c in crashes if c >= 10.00)

        buckets = [
            DistributionBucket(bucket="< 1.20x", count=b1, percentage=round((b1 / total) * 100, 2)),
            DistributionBucket(bucket="1.20x–1.49x", count=b2, percentage=round((b2 / total) * 100, 2)),
            DistributionBucket(bucket="1.50x–1.99x", count=b3, percentage=round((b3 / total) * 100, 2)),
            DistributionBucket(bucket="2.00x–4.99x", count=b4, percentage=round((b4 / total) * 100, 2)),
            DistributionBucket(bucket="5.00x–9.99x", count=b5, percentage=round((b5 / total) * 100, 2)),
            DistributionBucket(bucket="10.00x+", count=b6, percentage=round((b6 / total) * 100, 2)),
        ]

        return FairnessStatsResponse(
            total_completed_rounds=total,
            min_crash_multiplier=min_val,
            max_crash_multiplier=max_val,
            average_crash_multiplier=avg_val,
            median_crash_multiplier=med_val,
            distribution_buckets=buckets,
        )
