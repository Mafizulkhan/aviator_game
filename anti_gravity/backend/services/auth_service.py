"""
Anti-Gravity Backend — Authentication Service
Handles password hashing, JWT creation/validation, and user lookup.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import User, Wallet, Transaction, TransactionType

_pwd_ctx = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a signed JWT with explicit expiration (exp) and issued-at (iat) claims.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "iat": now,
        "exp": expire,
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Validate and decode a JWT.
    Returns payload dict if signature and expiration are valid; None otherwise.
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": True},
        )
    except (ExpiredSignatureError, JWTError):
        return None


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, username: str, password: str, email: Optional[str] = None) -> User:
    """
    Create a new user + wallet + starting-credits transaction.
    Raises ValueError if username already exists.
    """
    existing = await get_user_by_username(db, username)
    if existing:
        raise ValueError("Username already taken")

    user = User(
        username=username,
        password_hash=hash_password(password),
        email=email,
    )
    db.add(user)
    await db.flush()   # get user.id without committing

    # Create wallet with starting balance
    wallet = Wallet(user_id=user.id, balance=settings.STARTING_BALANCE)
    db.add(wallet)
    await db.flush()

    # Record the starting-credits transaction
    tx = Transaction(
        user_id=user.id,
        type=TransactionType.starting_credits,
        amount=settings.STARTING_BALANCE,
        balance_before=0,
        balance_after=settings.STARTING_BALANCE,
        reference_id=None,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
