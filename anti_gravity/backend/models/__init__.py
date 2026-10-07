"""
Anti-Gravity Backend — ORM Models
All five database tables: User, Wallet, Round, Bet, Transaction.

Indexes
-------
Performance indexes are added on columns frequently used in WHERE and ORDER BY clauses:
  - users.email                   → user authentication / uniqueness lookup
  - users.status                  → active / banned user checks
  - wallets.user_id               → user wallet balance lookup
  - rounds.status                 → get_current_round (WHERE status IN ('pending','running'))
  - rounds (status, id)           → composite index for get_game_history (WHERE status='crashed' ORDER BY id DESC)
  - rounds.started_at             → round duration / timestamp filtering
  - rounds.created_at             → timestamp ordering
  - bets.round_id                 → round bet aggregation (WHERE round_id=?)
  - bets (round_id, status)       → resolve active bets on round crash (WHERE round_id=? AND status='active')
  - bets.user_id                  → user bet history lookup
  - bets (user_id, id)            → composite index for player history (WHERE user_id=? ORDER BY id DESC)
  - bets.created_at               → time-based queries
  - transactions (user_id, created_at) → ordered wallet history per player (WHERE user_id=? ORDER BY created_at DESC)
  - transactions.created_at       → global timestamp financial auditing
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum as SAEnum, Float,
    ForeignKey, Index, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Enums ──────────────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN       = "admin"
    OPERATOR    = "operator"
    AUDITOR     = "auditor"
    SUPPORT     = "support"
    PLAYER      = "player"


class UserStatus(str, enum.Enum):
    active   = "active"
    banned   = "banned"


class RoundStatus(str, enum.Enum):
    pending   = "pending"   # seed generated, not started
    running   = "running"
    crashed   = "crashed"
    cancelled = "cancelled"


class BetStatus(str, enum.Enum):
    active     = "active"
    cashed_out = "cashed_out"
    lost       = "lost"


class TransactionType(str, enum.Enum):
    starting_credits = "starting_credits"
    bet              = "bet"
    payout           = "payout"
    refund           = "refund"
    admin_adjustment = "admin_adjustment"


# ── User ───────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_status", "status"),
    )

    id:            Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    username:      Mapped[str]        = mapped_column(String(50), unique=True, nullable=False, index=True)
    email:         Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str]        = mapped_column(String(255), nullable=False)
    role:          Mapped[UserRole]   = mapped_column(SAEnum(UserRole), default=UserRole.PLAYER, nullable=False)
    status:        Mapped[UserStatus] = mapped_column(SAEnum(UserStatus), default=UserStatus.active)
    created_at:    Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=_now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    wallet:       Mapped["Wallet"]            = relationship("Wallet", back_populates="user", uselist=False)
    bets:         Mapped[list["Bet"]]         = relationship("Bet", back_populates="user")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="user")
    audit_logs:   Mapped[list["AuditLog"]]    = relationship("AuditLog", back_populates="admin_user")


# ── Wallet ─────────────────────────────────────────────────────────────────────
class Wallet(Base):
    __tablename__ = "wallets"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:    Mapped[int]      = mapped_column(ForeignKey("users.id"), unique=True, nullable=False, index=True)
    balance:    Mapped[int]      = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped["User"] = relationship("User", back_populates="wallet")


# ── Round ──────────────────────────────────────────────────────────────────────
class Round(Base):
    __tablename__ = "rounds"
    __table_args__ = (
        # Speeds up get_current_round (WHERE status IN ('pending','running'))
        Index("ix_rounds_status", "status"),
        # Composite index: satisfies WHERE status = 'crashed' ORDER BY id DESC directly
        Index("ix_rounds_status_id", "status", "id"),
        # Timestamp filtering for audit and monitoring
        Index("ix_rounds_started_at", "started_at"),
        Index("ix_rounds_created_at", "created_at"),
    )

    id:               Mapped[int]          = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_number:     Mapped[int]          = mapped_column(Integer, unique=True, nullable=False, index=True)
    server_seed_hash: Mapped[str]          = mapped_column(String(64), nullable=False)
    server_seed:      Mapped[str | None]   = mapped_column(String(64), nullable=True)   # revealed after round
    crash_multiplier: Mapped[float | None] = mapped_column(Float, nullable=True)       # revealed after round
    status:           Mapped[RoundStatus]  = mapped_column(SAEnum(RoundStatus), default=RoundStatus.pending)
    started_at:       Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at:         Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:       Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=_now)

    bets: Mapped[list["Bet"]] = relationship("Bet", back_populates="round")


# ── Bet ────────────────────────────────────────────────────────────────────────
class Bet(Base):
    __tablename__ = "bets"
    __table_args__ = (
        # One active bet per user per round
        UniqueConstraint("round_id", "user_id", name="uq_bet_round_user"),
        # Composite index: resolve active bets when a round crashes
        # (WHERE round_id=? AND status='active') — hot path in resolve_round_if_crashed
        Index("ix_bets_round_id_status", "round_id", "status"),
        # Speeds up round audit queries (WHERE round_id=?)
        Index("ix_bets_round_id", "round_id"),
        # Speeds up player bet history (WHERE user_id=? ORDER BY id DESC)
        Index("ix_bets_user_id", "user_id"),
        Index("ix_bets_user_id_id", "user_id", "id"),
        # Timestamp ordering
        Index("ix_bets_created_at", "created_at"),
    )

    id:                 Mapped[int]       = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_id:           Mapped[int]       = mapped_column(ForeignKey("rounds.id"), nullable=False)
    user_id:            Mapped[int]       = mapped_column(ForeignKey("users.id"), nullable=False)
    amount:             Mapped[int]       = mapped_column(Integer, nullable=False)
    cashout_multiplier: Mapped[float | None] = mapped_column(Float, nullable=True)
    payout:             Mapped[int]       = mapped_column(Integer, default=0)
    status:             Mapped[BetStatus] = mapped_column(SAEnum(BetStatus), default=BetStatus.active)
    created_at:         Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=_now)
    cashed_out_at:      Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    round: Mapped["Round"] = relationship("Round", back_populates="bets")
    user:  Mapped["User"]  = relationship("User", back_populates="bets")


# ── Transaction ────────────────────────────────────────────────────────────────
class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # Composite index: ordered wallet history per player
        # (WHERE user_id=? ORDER BY created_at DESC)
        Index("ix_transactions_user_id_created_at", "user_id", "created_at"),
        # Global timestamp index for system financial auditing
        Index("ix_transactions_created_at", "created_at"),
    )

    id:             Mapped[int]             = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:        Mapped[int]             = mapped_column(ForeignKey("users.id"), nullable=False)
    type:           Mapped[TransactionType] = mapped_column(SAEnum(TransactionType), nullable=False)
    amount:         Mapped[int]             = mapped_column(Integer, nullable=False)
    balance_before: Mapped[int]             = mapped_column(Integer, nullable=False)
    balance_after:  Mapped[int]             = mapped_column(Integer, nullable=False)
    reference_id:   Mapped[int | None]      = mapped_column(Integer, nullable=True)   # bet_id or round_id
    created_at:     Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship("User", back_populates="transactions")


# ── Game Settings (Singleton Configuration) ───────────────────────────────────
class GameSettings(Base):
    __tablename__ = "game_settings"

    id:                Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    minimum_bet:       Mapped[int]        = mapped_column(Integer, default=10, nullable=False)
    maximum_bet:       Mapped[int]        = mapped_column(Integer, default=10000, nullable=False)
    starting_balance:  Mapped[int]        = mapped_column(Integer, default=1000, nullable=False)
    house_edge:        Mapped[float]      = mapped_column(Float, default=0.03, nullable=False)
    game_speed:        Mapped[float]      = mapped_column(Float, default=1.0, nullable=False)
    animation_speed:   Mapped[float]      = mapped_column(Float, default=1.0, nullable=False)
    betting_window_ms: Mapped[int]        = mapped_column(Integer, default=5000, nullable=False)
    maintenance_mode:  Mapped[bool]       = mapped_column(Boolean, default=False, nullable=False)
    updated_at:        Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    updated_by:        Mapped[str | None] = mapped_column(String(50), nullable=True)


# ── Audit Log (Append-Only) ────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id:            Mapped[int]             = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_user_id: Mapped[int | None]      = mapped_column(ForeignKey("users.id"), nullable=True)
    action:        Mapped[str]             = mapped_column(String(100), nullable=False)
    target_type:   Mapped[str | None]      = mapped_column(String(50), nullable=True)
    target_id:     Mapped[str | None]      = mapped_column(String(100), nullable=True)
    details:       Mapped[str | None]      = mapped_column(Text, nullable=True)
    ip_address:    Mapped[str | None]      = mapped_column(String(50), nullable=True)
    created_at:    Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=_now)

    admin_user: Mapped["User | None"] = relationship("User", back_populates="audit_logs")
