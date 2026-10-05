"""
Anti-Gravity Backend — Auth Router
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout  (client-side token discard — stateless)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.schemas import RegisterRequest, LoginRequest, TokenResponse
from backend.services.auth_service import (
    register_user, authenticate_user, create_access_token
)
from backend.services.rate_limiter import RateLimiter
from backend.services.wallet_service import get_balance

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new player with rate limiting. Automatically creates a wallet with starting credits.
    Returns a JWT access token.
    """
    RateLimiter.check_http_rate_limit(
        request,
        action="register",
        max_requests=settings.RATE_LIMIT_REGISTER_PER_MINUTE,
    )
    try:
        user = await register_user(db, body.username, body.password, body.email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    token = create_access_token({"sub": str(user.id)})
    balance = await get_balance(db, user.id)
    return TokenResponse(access_token=token, username=user.username, balance=balance)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate with username + password with rate limiting. Returns a JWT access token.
    """
    RateLimiter.check_http_rate_limit(
        request,
        action="login",
        max_requests=settings.RATE_LIMIT_LOGIN_PER_MINUTE,
    )
    user = await authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token({"sub": str(user.id)})
    balance = await get_balance(db, user.id)
    return TokenResponse(access_token=token, username=user.username, balance=balance)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """
    Logout is handled client-side by discarding the JWT token.
    (Stateless JWT — no server-side session to invalidate in this sprint.)
    """
    return
