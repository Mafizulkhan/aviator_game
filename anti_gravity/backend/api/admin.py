"""
Anti-Gravity Backend — Admin API Router
Endpoints for privileged administrative operations.

Security & Authorization:
- Role-Based Access Control (RBAC): SUPER_ADMIN, ADMIN, OPERATOR, AUDITOR, SUPPORT
- Append-only audit logging for all mutations and sensitive operations
- Strict sanitization: never expose unrevealed active seeds or secret tokens
- Absolute rule: No mechanism exists to alter authoritative round outcomes or multipliers
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import User, UserRole, Round, RoundStatus
from backend.services.auth_service import authenticate_user, create_access_token
from backend.services import admin_service
from backend.services.fairness_service import FairnessService
from backend.api.deps import get_current_user, require_roles
from backend.schemas import (
    AdminLoginRequest,
    AdminTokenResponse,
    AdminUserListItem,
    AdminUserDetail,
    AdminUserStatusUpdate,
    AdminUserRoleUpdate,
    AdminWalletAdjustmentRequest,
    AdminWalletAdjustmentResponse,
    AdminGameSettingsResponse,
    AdminGameSettingsUpdate,
    AdminAuditLogItem,
    AdminDashboardMetrics,
    AdminSystemHealthResponse,
    AdminRoundDetail,
    BetHistoryItem,
    FairnessVerifyResponse,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _client_ip(request: Request) -> str:
    """Extract client IP address for audit logging."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Admin Auth ─────────────────────────────────────────────────────────────────
@router.post("/auth/login", response_model=AdminTokenResponse)
async def admin_login(
    payload: AdminLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate administrator and return JWT token."""
    user = await authenticate_user(db, payload.username, payload.password)
    if not user:
        # Audit failed login attempt
        await admin_service.log_audit(
            db,
            action="admin_login_failed",
            target_type="auth",
            target_id=payload.username,
            details={"reason": "invalid_credentials"},
            ip_address=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role_val == "player":
        await admin_service.log_audit(
            db,
            action="admin_login_rejected_insufficient_role",
            admin_user_id=user.id,
            target_type="auth",
            target_id=user.username,
            ip_address=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Admin credentials required",
        )

    token = create_access_token({"sub": str(user.id), "role": role_val, "username": user.username})

    await admin_service.log_audit(
        db,
        action="admin_login_success",
        admin_user_id=user.id,
        target_type="auth",
        target_id=user.username,
        ip_address=_client_ip(request),
    )

    return AdminTokenResponse(
        access_token=token,
        token_type="bearer",
        role=role_val,
        username=user.username,
    )


@router.post("/auth/logout")
async def admin_logout(
    request: Request,
    admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Log administrative logout event."""
    await admin_service.log_audit(
        db,
        action="admin_logout",
        admin_user_id=admin.id,
        target_type="auth",
        target_id=admin.username,
        ip_address=_client_ip(request),
    )
    return {"status": "ok", "message": "Logged out successfully"}


# ── Dashboard & Health ─────────────────────────────────────────────────────────
@router.get("/dashboard", response_model=AdminDashboardMetrics)
async def get_dashboard(
    admin: User = Depends(require_roles("super_admin", "admin", "operator", "auditor", "support")),
    db: AsyncSession = Depends(get_db),
):
    """Get live dashboard operational metrics."""
    return await admin_service.get_dashboard_metrics(db)


@router.get("/system/health", response_model=AdminSystemHealthResponse)
async def get_system_health(
    admin: User = Depends(require_roles("super_admin", "admin", "operator", "auditor", "support")),
    db: AsyncSession = Depends(get_db),
):
    """Detailed health check of backend subsystems."""
    return await admin_service.get_system_health(db)


@router.get("/system/metrics")
async def get_system_metrics(
    admin: User = Depends(require_roles("super_admin", "admin", "operator", "auditor", "support")),
    db: AsyncSession = Depends(get_db),
):
    """System metrics and telemetry for admin monitoring."""
    return await admin_service.get_dashboard_metrics(db)


# ── User Management ────────────────────────────────────────────────────────────
@router.get("/users", response_model=List[AdminUserListItem])
async def list_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin: User = Depends(require_roles("super_admin", "admin", "operator", "auditor", "support")),
    db: AsyncSession = Depends(get_db),
):
    """Search and list users."""
    return await admin_service.list_users(
        db, search=search, role=role, status=status_filter, limit=limit, offset=offset
    )


@router.get("/users/{user_id}", response_model=AdminUserDetail)
async def get_user(
    user_id: int,
    admin: User = Depends(require_roles("super_admin", "admin", "operator", "auditor", "support")),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed profile and statistics for a specific user."""
    user = await admin_service.get_user_detail(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdate,
    request: Request,
    admin: User = Depends(require_roles("super_admin", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
):
    """Enable / ban user account."""
    try:
        user = await admin_service.update_user_status(
            db,
            user_id=user_id,
            status=payload.status,
            reason=payload.reason,
            admin_user=admin,
            ip_address=_client_ip(request),
        )
        return {
            "status": "ok",
            "user_id": user.id,
            "new_status": user.status.value if hasattr(user.status, "value") else str(user.status),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    payload: AdminUserRoleUpdate,
    request: Request,
    admin: User = Depends(require_roles("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Super Admin only: update user role (RBAC)."""
    try:
        user = await admin_service.update_user_role(
            db,
            user_id=user_id,
            new_role=payload.role,
            admin_user=admin,
            ip_address=_client_ip(request),
        )
        return {
            "status": "ok",
            "user_id": user.id,
            "new_role": user.role.value if hasattr(user.role, "value") else str(user.role),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/users/{user_id}/history", response_model=List[BetHistoryItem])
async def get_user_game_history(
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    admin: User = Depends(require_roles("super_admin", "admin", "operator", "auditor", "support")),
    db: AsyncSession = Depends(get_db),
):
    """Get bet history for a specific user."""
    from backend.services.player_service import get_bet_history
    return await get_bet_history(db, user_id=user_id, limit=limit, offset=offset)


@router.get("/users/{user_id}/transactions")
async def get_user_transactions(
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    admin: User = Depends(require_roles("super_admin", "admin", "operator", "auditor", "support")),
    db: AsyncSession = Depends(get_db),
):
    """Get transaction history for a specific user."""
    return await admin_service.list_transactions(db, user_id=user_id, limit=limit, offset=offset)


# ── Virtual Credit Adjustments ─────────────────────────────────────────────────
@router.post("/wallet-adjustments", response_model=AdminWalletAdjustmentResponse)
async def adjust_wallet(
    payload: AdminWalletAdjustmentRequest,
    request: Request,
    admin: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Adjust virtual test/demo credits on a user's wallet with mandatory audit reason.
    Virtual credits only — no real money operations.
    """
    try:
        tx = await admin_service.adjust_user_wallet(
            db,
            user_id=payload.user_id,
            amount=payload.amount,
            reason=payload.reason,
            admin_user=admin,
            ip_address=_client_ip(request),
        )
        return AdminWalletAdjustmentResponse(
            transaction_id=tx.id,
            user_id=tx.user_id,
            amount=tx.amount,
            balance_before=tx.balance_before,
            balance_after=tx.balance_after,
            reason=payload.reason,
            created_at=tx.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions")
async def list_all_transactions(
    user_id: Optional[int] = None,
    tx_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin: User = Depends(require_roles("super_admin", "admin", "operator", "auditor")),
    db: AsyncSession = Depends(get_db),
):
    """List financial transactions for auditing."""
    return await admin_service.list_transactions(
        db, user_id=user_id, tx_type=tx_type, limit=limit, offset=offset
    )


# ── Round Monitoring ───────────────────────────────────────────────────────────
@router.get("/rounds")
async def list_rounds(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin: User = Depends(require_roles("super_admin", "admin", "operator", "auditor", "support")),
    db: AsyncSession = Depends(get_db),
):
    """List rounds with wager and payout aggregations."""
    return await admin_service.list_rounds(db, status=status, limit=limit, offset=offset)


@router.get("/rounds/{round_id}", response_model=AdminRoundDetail)
async def get_round_detail(
    round_id: int,
    admin: User = Depends(require_roles("super_admin", "admin", "operator", "auditor", "support")),
    db: AsyncSession = Depends(get_db),
):
    """Get full details of a specific round, including all placed bets and cash-outs."""
    detail = await admin_service.get_round_detail(db, round_id=round_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Round not found")
    return detail


# ── Game Settings ──────────────────────────────────────────────────────────────
@router.get("/settings", response_model=AdminGameSettingsResponse)
async def get_game_settings(
    admin: User = Depends(require_roles("super_admin", "admin", "operator", "auditor", "support")),
    db: AsyncSession = Depends(get_db),
):
    """Fetch current game configuration."""
    return await admin_service.get_or_create_settings(db)


@router.patch("/settings", response_model=AdminGameSettingsResponse)
async def update_game_settings(
    payload: AdminGameSettingsUpdate,
    request: Request,
    admin: User = Depends(require_roles("super_admin", "admin", "operator")),
    db: AsyncSession = Depends(get_db),
):
    """Update game configuration parameters (house_edge requires SUPER_ADMIN)."""
    try:
        updated = await admin_service.update_game_settings(
            db,
            updates=payload.model_dump(exclude_unset=True),
            admin_user=admin,
            ip_address=_client_ip(request),
        )
        return updated
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Fairness Verification ──────────────────────────────────────────────────────
@router.get("/fairness/{round_id}")
async def get_admin_fairness(
    round_id: int,
    admin: User = Depends(require_roles("super_admin", "admin", "operator", "auditor", "support")),
    db: AsyncSession = Depends(get_db),
):
    """Inspect fairness commitment and revealed seed for a round."""
    try:
        return await FairnessService.get_round_fairness_info(db, round_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/fairness/{round_id}/verify", response_model=FairnessVerifyResponse)
async def verify_admin_fairness(
    round_id: int,
    request: Request,
    admin: User = Depends(require_roles("super_admin", "admin", "operator", "auditor")),
    db: AsyncSession = Depends(get_db),
):
    """Execute cryptographic fairness verification against HMAC-SHA256 outcome."""
    try:
        res = await FairnessService.verify_round_by_id(db, round_id)
        await admin_service.log_audit(
            db,
            action="verify_fairness",
            admin_user_id=admin.id,
            target_type="round",
            target_id=str(round_id),
            details={"verified": res.verified, "crash_multiplier": res.crash_multiplier},
            ip_address=_client_ip(request),
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Audit Logs ─────────────────────────────────────────────────────────────────
@router.get("/audit-logs", response_model=List[AdminAuditLogItem])
async def list_audit_logs(
    action: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin: User = Depends(require_roles("super_admin", "admin", "auditor")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve immutable audit logs."""
    return await admin_service.list_audit_logs(db, action=action, limit=limit, offset=offset)
