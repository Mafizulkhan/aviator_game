"""
Anti-Gravity Backend — FastAPI dependencies
Shared dependencies: current user extraction from JWT, optional user extraction, DB session.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.auth_service import decode_access_token, get_user_by_id
from backend.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: decode the JWT, return the authenticated User.
    Raises 401 if the token is missing, invalid, expired, or user is banned.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        raise credentials_exception

    user = await get_user_by_id(db, uid)
    if user is None or user.status.value == "banned":
        raise credentials_exception
    return user


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Optional user dependency. Returns User if valid token provided; None otherwise.
    """
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    try:
        uid = int(payload["sub"])
        user = await get_user_by_id(db, uid)
        if user and user.status.value != "banned":
            return user
    except Exception:
        return None
    return None


def require_roles(*allowed_roles: str):
    """
    FastAPI dependency factory: verifies that current user has one of the allowed roles
    (or is SUPER_ADMIN).
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        # SUPER_ADMIN always has full access
        if role_val == "super_admin":
            return current_user
        if role_val in allowed_roles:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient administrative privileges",
        )
    return role_checker

