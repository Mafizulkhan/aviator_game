"""
Anti-Gravity Backend — Pydantic Schemas
Request / response models for all API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Auth ───────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128)
    email:    Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    username:     str
    balance:      int


# ── Player ─────────────────────────────────────────────────────────────────────
class PlayerProfile(BaseModel):
    id:           int
    username:     str
    email:        Optional[str]
    status:       str
    created_at:   datetime
    games_played: int
    wins:         int
    losses:       int
    best_cashout: Optional[float]

    model_config = {"from_attributes": True}


class BalanceResponse(BaseModel):
    user_id:  int
    username: str
    balance:  int


class BetHistoryItem(BaseModel):
    bet_id:             int
    round_number:       int
    amount:             int
    cashout_multiplier: Optional[float]
    crash_multiplier:   Optional[float]
    payout:             int
    status:             str
    created_at:         datetime

    model_config = {"from_attributes": True}


# ── Game ────────────────────────────────────────────────────────────────────────
class CurrentRoundResponse(BaseModel):
    round_id:         int
    round_number:     int
    status:           str
    server_seed_hash: str
    started_at:       Optional[datetime]
    current_multiplier: Optional[float] = None   # computed, not stored

    model_config = {"from_attributes": True}


class JoinRoundRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Bet amount in virtual credits")


class JoinRoundResponse(BaseModel):
    bet_id:           int
    round_id:         int
    round_number:     int
    amount:           int
    balance_after:    int
    server_seed_hash: str
    status:           str


class CashoutRequest(BaseModel):
    bet_id: int


class CashoutResponse(BaseModel):
    bet_id:             int
    round_number:       int
    cashout_multiplier: float
    payout:             int
    balance_after:      int
    status:             str = "cashed_out"


class GameHistoryItem(BaseModel):
    round_number:     int
    crash_multiplier: Optional[float]
    status:           str
    started_at:       Optional[datetime]
    ended_at:         Optional[datetime]

    model_config = {"from_attributes": True}


# ── Fairness ────────────────────────────────────────────────────────────────────
class FairnessInfo(BaseModel):
    round_id:         int
    round_number:     int
    server_seed_hash: str
    server_seed:      Optional[str] = None     # None until round ends
    crash_multiplier: Optional[float] = None   # None until round ends
    status:           str

    model_config = {"from_attributes": True}


class FairnessVerifyResponse(BaseModel):
    round_number:     int
    server_seed:      str
    server_seed_hash: str
    crash_multiplier: float
    verified:         bool
    message:          str
    round_id:         Optional[int] = None


class DistributionBucket(BaseModel):
    bucket:     str
    count:      int
    percentage: float


class FairnessStatsResponse(BaseModel):
    total_completed_rounds:   int
    min_crash_multiplier:     Optional[float] = None
    max_crash_multiplier:     Optional[float] = None
    average_crash_multiplier: Optional[float] = None
    median_crash_multiplier:  Optional[float] = None
    distribution_buckets:     list[DistributionBucket] = []


# ── Audit ───────────────────────────────────────────────────────────────────────
class AuditRoundResponse(BaseModel):
    round_id:         int
    round_number:     int
    status:           str
    created_at:       datetime
    started_at:       Optional[datetime] = None
    ended_at:         Optional[datetime] = None
    server_seed_hash: str
    server_seed:      Optional[str] = None     # revealed when lifecycle permits
    crash_multiplier: Optional[float] = None   # revealed when lifecycle permits
    verified:         Optional[bool] = None    # verified status for completed rounds
    total_bets:       int = 0
    total_wagered:    int = 0
    total_payout:     int = 0
    cashed_out_count: int = 0
    lost_count:       int = 0

    model_config = {"from_attributes": True}


# ── Health ──────────────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status:  str = "ok"
    version: str = "0.2.0"
    mode:    str = "demo"
