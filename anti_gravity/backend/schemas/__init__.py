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


# ── Admin ───────────────────────────────────────────────────────────────────────
class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    role:         str
    username:     str


class AdminUserListItem(BaseModel):
    id:            int
    username:      str
    email:         Optional[str]
    role:          str
    status:        str
    balance:       int
    created_at:    datetime
    last_login_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AdminUserDetail(BaseModel):
    id:            int
    username:      str
    email:         Optional[str]
    role:          str
    status:        str
    balance:       int
    created_at:    datetime
    last_login_at: Optional[datetime]
    games_played:  int
    total_wagered: int
    total_won:     int

    model_config = {"from_attributes": True}


class AdminUserStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(active|banned)$")
    reason: Optional[str] = None


class AdminUserRoleUpdate(BaseModel):
    role: str = Field(..., pattern=r"^(super_admin|admin|operator|auditor|support|player)$")


class AdminWalletAdjustmentRequest(BaseModel):
    user_id: int
    amount:  int = Field(..., description="Signed integer amount to adjust (positive to add, negative to remove)")
    reason:  str = Field(..., min_length=3, max_length=255, description="Mandatory reason for audit trail")


class AdminWalletAdjustmentResponse(BaseModel):
    transaction_id: int
    user_id:        int
    amount:         int
    balance_before: int
    balance_after:  int
    reason:         str
    created_at:     datetime


class AdminGameSettingsResponse(BaseModel):
    minimum_bet:       int
    maximum_bet:       int
    starting_balance:  int
    house_edge:        float
    game_speed:        float
    animation_speed:   float
    betting_window_ms: int
    maintenance_mode:  bool
    updated_at:        datetime
    updated_by:        Optional[str]

    model_config = {"from_attributes": True}


class AdminGameSettingsUpdate(BaseModel):
    minimum_bet:       Optional[int] = Field(None, gt=0)
    maximum_bet:       Optional[int] = Field(None, gt=0)
    starting_balance:  Optional[int] = Field(None, ge=0)
    house_edge:        Optional[float] = Field(None, ge=0.0, le=0.20)
    game_speed:        Optional[float] = Field(None, gt=0.1, le=5.0)
    animation_speed:   Optional[float] = Field(None, gt=0.1, le=5.0)
    betting_window_ms: Optional[int] = Field(None, ge=1000, le=30000)
    maintenance_mode:  Optional[bool] = None


class AdminAuditLogItem(BaseModel):
    id:             int
    admin_user_id:  Optional[int]
    admin_username: Optional[str] = None
    action:         str
    target_type:    Optional[str]
    target_id:      Optional[str]
    details:        Optional[str]
    ip_address:     Optional[str]
    created_at:     datetime

    model_config = {"from_attributes": True}


class AdminDashboardMetrics(BaseModel):
    total_users:            int
    active_users:           int
    online_users:           int
    current_round_id:       Optional[int]
    current_round_number:   Optional[int]
    current_status:         str
    current_multiplier:     float
    players_in_round:       int
    games_today:            int
    credits_in_circulation: int
    cashout_rate:           float
    api_health:             str
    ws_connections:         int
    db_health:              str
    maintenance_mode:       bool


class AdminSystemHealthResponse(BaseModel):
    api_status:            str
    db_status:             str
    ws_status:             str
    game_loop_status:      str
    active_connections:    int
    background_tasks_ok:   bool
    uptime_seconds:        float
    version:               str


class AdminRoundBetItem(BaseModel):
    bet_id:             int
    user_id:            int
    username:           str
    amount:             int
    cashout_multiplier: Optional[float]
    payout:             int
    status:             str
    created_at:         datetime

    model_config = {"from_attributes": True}


class AdminRoundDetail(BaseModel):
    id:               int
    round_number:     int
    status:           str
    server_seed_hash: str
    server_seed:      Optional[str]
    crash_multiplier: Optional[float]
    started_at:       Optional[datetime]
    ended_at:         Optional[datetime]
    created_at:       datetime
    total_bets:       int
    total_wagered:    int
    total_payout:     int
    bets:             list[AdminRoundBetItem] = []

    model_config = {"from_attributes": True}
