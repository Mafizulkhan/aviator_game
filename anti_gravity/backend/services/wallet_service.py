"""
Anti-Gravity Backend — Wallet Service
All balance mutations go through here. Database transactions enforce atomicity.
IMPORTANT: Never trust client-supplied balance, payout, or multiplier values.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import Wallet, Transaction, TransactionType


async def get_wallet(db: AsyncSession, user_id: int) -> Optional[Wallet]:
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == user_id).with_for_update()
    )
    return result.scalar_one_or_none()


async def get_balance(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(select(Wallet.balance).where(Wallet.user_id == user_id))
    bal = result.scalar_one_or_none()
    return bal if bal is not None else 0


async def deduct_bet(
    db: AsyncSession,
    user_id: int,
    amount: int,
    reference_id: Optional[int] = None,
) -> int:
    """
    Deduct `amount` from the user's wallet for a bet.
    Returns the new balance.
    Raises ValueError on validation failure.
    This must be called inside a DB transaction (caller wraps with begin/commit).
    """
    if amount < settings.MIN_BET or amount > settings.MAX_BET:
        raise ValueError(f"Bet must be between {settings.MIN_BET} and {settings.MAX_BET}")

    wallet = await get_wallet(db, user_id)
    if wallet is None:
        raise ValueError("Wallet not found")
    if wallet.balance < amount:
        raise ValueError("Insufficient balance")

    balance_before = wallet.balance
    wallet.balance -= amount
    wallet.updated_at = datetime.now(timezone.utc)

    tx = Transaction(
        user_id=user_id,
        type=TransactionType.bet,
        amount=amount,
        balance_before=balance_before,
        balance_after=wallet.balance,
        reference_id=reference_id,
    )
    db.add(tx)
    return wallet.balance


async def add_payout(
    db: AsyncSession,
    user_id: int,
    amount: int,
    reference_id: Optional[int] = None,
) -> int:
    """
    Add payout `amount` to the user's wallet after a successful cash-out.
    Returns the new balance.
    """
    wallet = await get_wallet(db, user_id)
    if wallet is None:
        raise ValueError("Wallet not found")

    balance_before = wallet.balance
    wallet.balance += amount
    wallet.updated_at = datetime.now(timezone.utc)

    tx = Transaction(
        user_id=user_id,
        type=TransactionType.payout,
        amount=amount,
        balance_before=balance_before,
        balance_after=wallet.balance,
        reference_id=reference_id,
    )
    db.add(tx)
    return wallet.balance


async def add_refund(
    db: AsyncSession,
    user_id: int,
    amount: int,
    reference_id: Optional[int] = None,
) -> int:
    """Refund the bet (e.g. round was cancelled)."""
    wallet = await get_wallet(db, user_id)
    if wallet is None:
        raise ValueError("Wallet not found")

    balance_before = wallet.balance
    wallet.balance += amount
    wallet.updated_at = datetime.now(timezone.utc)

    tx = Transaction(
        user_id=user_id,
        type=TransactionType.refund,
        amount=amount,
        balance_before=balance_before,
        balance_after=wallet.balance,
        reference_id=reference_id,
    )
    db.add(tx)
    return wallet.balance
