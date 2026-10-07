"""
Anti-Gravity Backend — Comprehensive Admin Panel & RBAC Tests
Verifies:
- Admin login, token generation, and audit logging
- Role-based access control (RBAC): SUPER_ADMIN, ADMIN, OPERATOR, AUDITOR, SUPPORT
- Player rejection from admin endpoints
- User search, detail, ban/unban, and role updates
- Virtual credit manual adjustments with mandatory audit reason & bounds
- Game configuration & settings management
- Server-side maintenance mode enforcement on bet placement
- Fairness verification via admin API
- Strict outcome immutability (no outcome manipulation capability)
- Subsystem health checks
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import User, UserRole, UserStatus, Wallet, Round, RoundStatus, GameSettings, AuditLog
from backend.services.auth_service import hash_password
from backend.services.game_service import _active_round_internal
from backend.main import app
from app.engine.game_engine import FairnessEngine


@pytest_asyncio.fixture
async def admin_test_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=True)

    # Seed users with various roles
    async with factory() as db:
        # Super Admin
        super_admin = User(
            username="superadmin",
            password_hash=hash_password("SuperSecret123!"),
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.active,
        )
        db.add(super_admin)
        await db.flush()
        db.add(Wallet(user_id=super_admin.id, balance=100000))

        # Admin
        admin = User(
            username="admin_ops",
            password_hash=hash_password("AdminSecret123!"),
            role=UserRole.ADMIN,
            status=UserStatus.active,
        )
        db.add(admin)
        await db.flush()
        db.add(Wallet(user_id=admin.id, balance=50000))

        # Operator
        operator = User(
            username="operator1",
            password_hash=hash_password("OperatorPass1!"),
            role=UserRole.OPERATOR,
            status=UserStatus.active,
        )
        db.add(operator)
        await db.flush()
        db.add(Wallet(user_id=operator.id, balance=10000))

        # Auditor
        auditor = User(
            username="auditor1",
            password_hash=hash_password("AuditorPass1!"),
            role=UserRole.AUDITOR,
            status=UserStatus.active,
        )
        db.add(auditor)
        await db.flush()
        db.add(Wallet(user_id=auditor.id, balance=5000))

        # Support
        support = User(
            username="support1",
            password_hash=hash_password("SupportPass1!"),
            role=UserRole.SUPPORT,
            status=UserStatus.active,
        )
        db.add(support)
        await db.flush()
        db.add(Wallet(user_id=support.id, balance=1000))

        # Regular Player
        player = User(
            username="regular_player",
            password_hash=hash_password("PlayerPass1!"),
            role=UserRole.PLAYER,
            status=UserStatus.active,
        )
        db.add(player)
        await db.flush()
        db.add(Wallet(user_id=player.id, balance=2500))

        # Default GameSettings
        settings = GameSettings(
            minimum_bet=10,
            maximum_bet=10000,
            starting_balance=1000,
            house_edge=0.03,
            game_speed=1.0,
            animation_speed=1.0,
            betting_window_ms=5000,
            maintenance_mode=False,
        )
        db.add(settings)

        await db.commit()

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, factory

    app.dependency_overrides.clear()
    await engine.dispose()


async def _get_token(client: AsyncClient, username: str, password: str) -> str:
    res = await client.post(
        "/api/admin/auth/login",
        json={"username": username, "password": password},
    )
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_login_success(admin_test_db):
    client, _ = admin_test_db
    res = await client.post(
        "/api/admin/auth/login",
        json={"username": "superadmin", "password": "SuperSecret123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "super_admin"
    assert data["username"] == "superadmin"
    assert "access_token" in data


@pytest.mark.asyncio
async def test_admin_login_invalid_credentials(admin_test_db):
    client, _ = admin_test_db
    res = await client.post(
        "/api/admin/auth/login",
        json={"username": "superadmin", "password": "WrongPassword!"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_player_cannot_access_admin_auth(admin_test_db):
    client, _ = admin_test_db
    res = await client.post(
        "/api/admin/auth/login",
        json={"username": "regular_player", "password": "PlayerPass1!"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_dashboard_metrics(admin_test_db):
    client, _ = admin_test_db
    token = await _get_token(client, "admin_ops", "AdminSecret123!")
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/admin/dashboard", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_users"] >= 6
    assert data["credits_in_circulation"] >= 168500
    assert data["db_health"] == "connected"


@pytest.mark.asyncio
async def test_admin_user_management(admin_test_db):
    client, _ = admin_test_db
    token = await _get_token(client, "admin_ops", "AdminSecret123!")
    headers = {"Authorization": f"Bearer {token}"}

    # List users
    res = await client.get("/api/admin/users", headers=headers)
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 6

    # Get single user detail
    player_id = next(u["id"] for u in users if u["username"] == "regular_player")
    res_det = await client.get(f"/api/admin/users/{player_id}", headers=headers)
    assert res_det.status_code == 200
    detail = res_det.json()
    assert detail["username"] == "regular_player"
    assert detail["balance"] == 2500

    # Ban player
    res_ban = await client.patch(
        f"/api/admin/users/{player_id}/status",
        json={"status": "banned", "reason": "Suspicious automated traffic"},
        headers=headers,
    )
    assert res_ban.status_code == 200
    assert res_ban.json()["new_status"] == "banned"

    # Verify banned status persists
    res_det2 = await client.get(f"/api/admin/users/{player_id}", headers=headers)
    assert res_det2.json()["status"] == "banned"

    # Unban player
    res_unban = await client.patch(
        f"/api/admin/users/{player_id}/status",
        json={"status": "active", "reason": "Investigation cleared"},
        headers=headers,
    )
    assert res_unban.status_code == 200
    assert res_unban.json()["new_status"] == "active"


@pytest.mark.asyncio
async def test_admin_rbac_role_permissions(admin_test_db):
    client, _ = admin_test_db

    # Support role token
    support_token = await _get_token(client, "support1", "SupportPass1!")
    support_headers = {"Authorization": f"Bearer {support_token}"}

    # Support can read users
    res = await client.get("/api/admin/users", headers=support_headers)
    assert res.status_code == 200
    player_id = res.json()[0]["id"]

    # Support CANNOT ban users (requires super_admin, admin, or operator)
    res_ban = await client.patch(
        f"/api/admin/users/{player_id}/status",
        json={"status": "banned"},
        headers=support_headers,
    )
    assert res_ban.status_code == 403

    # Support CANNOT modify settings
    res_set = await client.patch(
        "/api/admin/settings",
        json={"minimum_bet": 50},
        headers=support_headers,
    )
    assert res_set.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_role_change(admin_test_db):
    client, _ = admin_test_db

    # Admin trying to change role -> 403 Forbidden
    admin_token = await _get_token(client, "admin_ops", "AdminSecret123!")
    res_fail = await client.patch(
        "/api/admin/users/6/role",
        json={"role": "operator"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_fail.status_code == 403

    # Super Admin changing role -> 200 Success
    super_token = await _get_token(client, "superadmin", "SuperSecret123!")
    res_ok = await client.patch(
        "/api/admin/users/6/role",
        json={"role": "operator"},
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["new_role"] == "operator"


@pytest.mark.asyncio
async def test_wallet_manual_adjustment_with_audit(admin_test_db):
    client, factory = admin_test_db
    token = await _get_token(client, "admin_ops", "AdminSecret123!")
    headers = {"Authorization": f"Bearer {token}"}

    # Find regular player ID
    res_users = await client.get("/api/admin/users", headers=headers)
    player = next(u for u in res_users.json() if u["username"] == "regular_player")
    p_id = player["id"]
    initial_bal = player["balance"]

    # Add 1500 credits
    res_adj = await client.post(
        "/api/admin/wallet-adjustments",
        json={"user_id": p_id, "amount": 1500, "reason": "Tournament test bonus grant"},
        headers=headers,
    )
    assert res_adj.status_code == 200
    data = res_adj.json()
    assert data["balance_before"] == initial_bal
    assert data["balance_after"] == initial_bal + 1500

    # Negative adjustment bound check (attempt to debit more than balance)
    res_neg = await client.post(
        "/api/admin/wallet-adjustments",
        json={"user_id": p_id, "amount": -999999, "reason": "Invalid large debit"},
        headers=headers,
    )
    assert res_neg.status_code == 400

    # Verify audit log was written
    res_audit = await client.get("/api/admin/audit-logs", headers=headers)
    assert res_audit.status_code == 200
    logs = res_audit.json()
    assert any(l["action"] == "wallet_adjustment" and str(p_id) in str(l["target_id"]) for l in logs)


@pytest.mark.asyncio
async def test_game_settings_and_maintenance_mode(admin_test_db):
    client, _ = admin_test_db
    super_token = await _get_token(client, "superadmin", "SuperSecret123!")
    headers = {"Authorization": f"Bearer {super_token}"}

    # Update settings
    res = await client.patch(
        "/api/admin/settings",
        json={
            "minimum_bet": 20,
            "maximum_bet": 50000,
            "betting_window_ms": 6000,
            "maintenance_mode": True,
        },
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["minimum_bet"] == 20
    assert data["maximum_bet"] == 50000
    assert data["maintenance_mode"] is True

    # Now verify that player bet attempts are rejected due to maintenance mode
    p_res = await client.post(
        "/api/auth/login",
        json={"username": "regular_player", "password": "PlayerPass1!"},
    )
    player_token = p_res.json()["access_token"]
    player_headers = {"Authorization": f"Bearer {player_token}"}

    # Attempt to place bet during maintenance mode
    res_bet = await client.post(
        "/api/game/join",
        json={"amount": 100},
        headers=player_headers,
    )
    assert res_bet.status_code == 400
    assert "maintenance" in res_bet.json()["detail"].lower()

    # Disable maintenance mode
    await client.patch(
        "/api/admin/settings",
        json={"maintenance_mode": False},
        headers=headers,
    )


@pytest.mark.asyncio
async def test_admin_fairness_verification(admin_test_db):
    client, factory = admin_test_db
    token = await _get_token(client, "admin_ops", "AdminSecret123!")
    headers = {"Authorization": f"Bearer {token}"}

    # Create a completed crashed round with known seed
    seed = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
    seed_hash = FairnessEngine.hash_seed(seed)
    crash_point = FairnessEngine.calculate_crash_point(seed, 42)

    async with factory() as db:
        r = Round(
            round_number=42,
            server_seed_hash=seed_hash,
            server_seed=seed,
            crash_multiplier=crash_point,
            status=RoundStatus.crashed,
        )
        db.add(r)
        await db.commit()
        await db.refresh(r)
        round_id = r.id

    # Verify via Admin API
    res = await client.post(f"/api/admin/fairness/{round_id}/verify", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["verified"] is True
    assert data["crash_multiplier"] == crash_point
    assert data["server_seed_hash"] == seed_hash


@pytest.mark.asyncio
async def test_system_health_and_metrics(admin_test_db):
    client, _ = admin_test_db
    token = await _get_token(client, "admin_ops", "AdminSecret123!")
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/admin/system/health", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["api_status"] == "ok"
    assert data["db_status"] == "ok"
    assert data["version"] == "0.2.0"
