# Anti-Gravity — Complete Admin Panel Development Plan

> **Document:** Admin Panel + Admin Backend API Source of Truth  
> **Version:** 3.0  
> **Status:** Active  
> **Owner:** Mafizul Khan  
> **Development Environment:** Antigravity IDE · Windows · Python  
> **Admin Platform:** Authenticated Web Application  
> **Backend:** Python + FastAPI  
> **Database:** PostgreSQL in production

## 0. Purpose

The Admin Panel is a **first-class product component** for operating, monitoring, securing and auditing Anti-Gravity.

It is a separate authenticated web application.

It is NOT the Android player application.

It must provide authorized operational control over:

- Users.
- Virtual credits.
- Transactions.
- Round monitoring.
- Game configuration.
- Maintenance mode.
- Fairness verification.
- Audit logs.
- System health.
- Metrics.
- Security events.
- Administrator accounts and roles.

### Absolute boundary

The Admin Panel must NEVER provide any mechanism, visible or hidden, that manually changes an individual authoritative game outcome.

The server game engine and fairness system remain authoritative.

## 0.1 Architecture

```text
Admin Browser
    |
 HTTPS
    |
 WAF / Rate Limiting
    |
 Protected FastAPI Admin APIs
    |
 +---------------------------+
 |                           |
 PostgreSQL             Audit System
```

The Admin Browser must never connect directly to PostgreSQL.

## 0.2 Production Online Security

The Admin Panel is an Internet-facing privileged system.

No security design can honestly guarantee that it is "unhackable."

Use defense in depth so that compromising one layer does not compromise:

- Game outcomes.
- Player wallets.
- Authentication.
- Database.
- Admin roles.
- Fairness.
- Audit records.

## 0.3 Product Boundary

Anti-Gravity remains virtual-credit-only.

The Admin Panel must never add:

- Real-money deposits.
- Withdrawals.
- Cash prizes.
- Cryptocurrency wagering.
- Payment-based betting.
- Real-money wallet functionality.

## 30. Admin Panel

The Admin Panel is a **first-class part of the Anti-Gravity product**.

It is a separate authenticated web dashboard connected to protected Python/FastAPI admin APIs. It is **not** the player Android application.

### Admin Architecture

```
Admin Browser (Chrome / Firefox)
      |
    HTTPS
      |
Protected FastAPI Admin APIs  (/api/admin/*)
      |
+-----+------------------------+
|                              |
Database (PostgreSQL)      Audit System (audit_logs table)
```

### Admin Authentication and RBAC

Implement:

- Admin login with rate limiting and failed-login lockout
- Secure Argon2id password hashing
- JWT/session authentication with expiry
- Token refresh and revocation
- Role-based access control (RBAC)
- Permission checks on every sensitive endpoint
- Audit logging of all admin actions
- Secret sanitization (never expose server seeds, JWT keys, DB credentials)

**Roles:**

| Role | Description |
|---|---|
| `SUPER_ADMIN` | Full access + role management |
| `ADMIN` | Full operational access |
| `OPERATOR` | Game + user management, no RBAC |
| `AUDITOR` | Read-only audit + fairness access |
| `SUPPORT` | Read-only user view |

> [!CAUTION]
> Never put admin credentials, JWT signing secrets, database credentials, or server seeds inside the Android APK.

### Admin Dashboard

Live metrics:

```
Total Users          Active Users      Online Users
Current Round #      Multiplier        Players in Round
Games Today          Credits in Circ.  Cash-out Rate
API Health           WS Connections    DB Health
Recent Security Events
```

### User Management

Authorized administrators can:

- Search and filter users
- View full profile
- View account status and history
- Enable / disable / ban accounts
- Review login and session activity
- View virtual-credit balance
- View game and transaction history
- Review security events associated with account

### Virtual-Credit Management

Provide:

- View current wallet balance
- View full transaction history
- Add virtual test/demo credits (with mandatory reason)
- Remove virtual credits where authorized (with mandatory reason)
- Before/after balance recorded on every adjustment
- Immutable audit record generated automatically

> [!WARNING]
> Never add real-money deposits, withdrawals, payments, cryptocurrency wagering, or cash prizes.

### Game / Round Management

Display:

- Current round ID, status, multiplier, crash multiplier
- Start/end timestamps
- Number of bets placed / cashed out
- Virtual credits wagered / paid out
- Historical round list with filters

> [!IMPORTANT]
> **Critical rule:** The Admin Panel must **NOT** contain any mechanism — hidden or otherwise — for manually changing an individual round's authoritative crash result. Outcomes remain controlled exclusively by the server game engine and fairness system.

### Game Configuration

Authorized admins can manage:

```
Minimum virtual bet
Maximum virtual bet
Starting virtual-credit balance for new players
Round betting window duration
House edge (SUPER_ADMIN only)
Maintenance mode (ON / OFF)
```

Every change must be: permission-checked → validated → saved → audited.

### Fairness Verification

Display, where authorized:

```
Round ID
Commitment hash (published pre-round)
Server seed (revealed post-round)
Crash result
Verification status (PASS / FAIL)
Audit metadata
```

Unrevealed server seeds for active/future rounds must remain protected.

### Audit Logs

Record:

```
Admin login / logout
Failed admin login attempts
User status changes
Virtual-credit adjustments
Configuration changes
Maintenance mode changes
Security events
All administrative API actions
Fairness verification actions
```

Audit records are **append-only / immutable** — no delete or update from the UI.

### System Health

Display:

```
API health (response time, error rate)
Database health (connection count, latency)
WebSocket connections (active count)
Game-loop status (running / stopped)
Background task status
Recent exceptions log
```

### Maintenance Mode

When enabled:

1. New bets are blocked.
2. Any active round is allowed to finish naturally.
3. Players see a maintenance notice.
4. Admins retain full panel access.

### Complete Admin API Reference

```http
POST   /api/admin/auth/login
POST   /api/admin/auth/logout

GET    /api/admin/dashboard

GET    /api/admin/users
GET    /api/admin/users/{user_id}
PATCH  /api/admin/users/{user_id}/status
GET    /api/admin/users/{user_id}/history
GET    /api/admin/users/{user_id}/transactions

GET    /api/admin/rounds
GET    /api/admin/rounds/{round_id}

GET    /api/admin/transactions
POST   /api/admin/wallet-adjustments

GET    /api/admin/audit-logs

GET    /api/admin/fairness/{round_id}
POST   /api/admin/fairness/{round_id}/verify

GET    /api/admin/system/health
GET    /api/admin/system/metrics

GET    /api/admin/settings
PATCH  /api/admin/settings
```

### Admin Testing Checklist

- [ ] Admin authentication (valid / invalid credentials)
- [ ] RBAC — role permissions enforced
- [ ] Unauthorized access returns 403
- [ ] User isolation (admin can't access other admin's session)
- [ ] Wallet-adjustment authorization (correct role required)
- [ ] Audit record created for every sensitive action
- [ ] Audit records cannot be deleted via UI
- [ ] Configuration validation rejects bad values
- [ ] Maintenance mode blocks new bets
- [ ] Fairness verification returns correct PASS / FAIL
- [ ] Server seeds protected for active rounds
- [ ] Rate limiting on admin login endpoint
- [ ] Expired / invalid admin tokens rejected

---

## 31. Admin UI / Screen Specification

The Admin Panel must contain the following production-style screens.

### 31.1 Login

Components:

- Username/email field.
- Password field.
- MFA field/challenge.
- Show/hide password.
- Login button.
- Forgot password.
- Security/error messages.
- Rate-limit/lockout messaging.
- Session/security notice.

Rules:

- Do not reveal whether a username exists.
- Rate-limit attempts.
- Lock out or temporarily delay repeated failures.
- Do not expose stack traces.
- Do not store passwords in browser storage.

### 31.2 Dashboard

Display live:

- Total users.
- Active users.
- Online users.
- Current round.
- Current multiplier.
- Players in current round.
- Games today.
- Virtual credits in circulation.
- Cash-out rate.
- API health.
- WebSocket connections.
- Database health.
- Recent security events.
- Recent admin activity.

### 31.3 Live Game Monitor

Display:

- Current round ID.
- Round status.
- Live multiplier.
- Round start time.
- Elapsed time.
- Player count.
- Bet count.
- Virtual credits wagered.
- Cash-outs.
- Server health.
- WebSocket health.

The monitor is read-only with respect to authoritative outcome.

### 31.4 Users

Features:

- Search.
- Filter.
- Sort.
- Pagination.
- User status.
- Registration date.
- Last login.
- Balance.
- Role.
- Security status.

Authorized administrators may:

- View profile.
- Suspend account.
- Enable account.
- Ban account where permitted.
- Review sessions.
- Review login activity.
- Review security events.
- View game history.
- View transaction history.

Every sensitive action must be authorized server-side and audited.

### 31.5 User Details

Display:

- User ID.
- Username.
- Email where applicable.
- Account status.
- Role.
- Created date.
- Last login.
- Session information.
- Virtual-credit balance.
- Game statistics.
- Round history.
- Transaction history.
- Security events.

Do not display:

- Passwords.
- Password hashes.
- Refresh tokens.
- JWT secrets.
- Server seeds for active/future rounds.

### 31.6 Wallets

Display:

- User.
- Current virtual-credit balance.
- Balance history.
- Transaction count.
- Last transaction.
- Adjustment history.

Authorized adjustment:

- Add virtual test/demo credits.
- Remove virtual credits where permitted.

Every adjustment requires:

- Mandatory reason.
- Actor.
- Timestamp.
- Before balance.
- Adjustment amount.
- After balance.
- Target user.
- Audit record.

### 31.7 Transactions

Display:

- Transaction ID.
- User.
- Type.
- Amount.
- Balance before.
- Balance after.
- Reference ID.
- Timestamp.
- Related round/bet where applicable.

Transactions are server-generated.

### 31.8 Rounds

Display:

- Round ID.
- Round number.
- Status.
- Start timestamp.
- End timestamp.
- Crash multiplier.
- Number of bets.
- Number of cash-outs.
- Virtual credits wagered.
- Virtual credits paid out.
- Commitment hash.
- Fairness status.

Filtering:

- Date.
- Status.
- Round number.
- Result range.

### 31.9 Round Details

Display:

- Round metadata.
- Timeline.
- Commitment hash.
- Post-round server seed where permitted.
- Crash result.
- Bets.
- Cash-outs.
- Settlement information.
- Audit metadata.
- Fairness verification.

Never expose an unrevealed seed for an active/future round.

### 31.10 Fairness

Provide:

- Round ID.
- Commitment hash.
- Server seed after reveal.
- Client seed if used.
- Derived randomness metadata where safe.
- Crash result.
- Verification status.
- Verification timestamp.
- Verification actor.

Actions:

- Verify round.
- View verification result.

Never provide a mechanism to replace the authoritative seed/result.

### 31.11 Audit Logs

Display append-only audit records:

- Admin login/logout.
- Failed admin login.
- MFA events.
- User status changes.
- Wallet adjustments.
- Configuration changes.
- Maintenance changes.
- Security events.
- Admin API actions.
- Fairness verification.
- Role/permission changes.

Filters:

- Admin.
- Action.
- Target.
- Date/time.
- Severity.
- IP/session identifier where appropriate.

No delete/edit operation.

### 31.12 Game Settings

Authorized configuration:

- Minimum virtual bet.
- Maximum virtual bet.
- Starting virtual-credit balance.
- Betting window.
- House edge, SUPER_ADMIN only.
- Game speed where supported.
- Animation settings where applicable.
- Maintenance mode.

Every setting change must:

1. Authenticate.
2. Authorize.
3. Validate.
4. Save transactionally.
5. Record before/after values.
6. Write immutable audit record.

### 31.13 Maintenance

When enabled:

1. New bets are blocked.
2. Active round finishes naturally.
3. Players receive maintenance notice.
4. Admin Panel remains accessible.

Do not terminate an active round solely because maintenance mode was enabled.

### 31.14 System Health

Display:

- API health.
- API latency.
- Error rate.
- Database health.
- DB connection count.
- DB latency.
- WebSocket connection count.
- Game-loop status.
- Background task status.
- Recent exceptions.
- Queue/worker health where applicable.

### 31.15 System Metrics

Display:

- DAU/MAU.
- Games per day.
- Average session duration.
- Average rounds/session.
- Average virtual credits wagered.
- Cash-out distribution.
- Crash distribution.
- Win/loss distribution.
- Client crash rate.
- API p50/p95/p99 latency.
- WebSocket disconnect rate.
- Security event counts.

### 31.16 Security

Display authorized security information:

- Failed login attempts.
- Rate-limit events.
- Suspicious sessions.
- Admin login activity.
- MFA failures.
- Account lockouts.
- Security alerts.
- Recent privileged operations.

Never expose secrets.

### 31.17 Admin Profile

Allow administrators to:

- View own profile.
- Change password.
- Configure MFA.
- Review own active sessions.
- Revoke sessions.
- Log out.

Do not allow ordinary admins to modify their own role.

SUPER_ADMIN role management must still be audited and protected.

### 31.18 Admin Role Management

SUPER_ADMIN only:

- Create admin account.
- Disable admin account.
- Assign allowed role.
- Remove role.
- Force password reset.
- Revoke sessions.
- Require MFA.

Every role change requires an immutable audit entry.

### 31.19 Notifications

Provide an admin notification area for:

- Security alerts.
- System health failures.
- Database issues.
- WebSocket failures.
- Game-loop failures.
- Backup failures.
- High error rates.

Do not turn notifications into a mechanism for changing game outcomes.

### 31.20 Global Search

Search authorized operational data by:

- User ID.
- Username.
- Email where permitted.
- Round ID.
- Transaction ID.
- Audit ID.

Search must be permission-aware.

Never allow search to bypass RBAC.

## 32. Admin Authentication & Security

### 32.1 Authentication

Implement:

- Argon2id password hashing.
- Short-lived admin access tokens.
- Refresh-token rotation.
- Token revocation.
- Session management.
- Failed-login rate limiting.
- Temporary lockout.
- MFA.
- Password reset.
- Secure logout.
- Suspicious-login detection.

### 32.2 MFA

Require MFA for:

```text
SUPER_ADMIN
ADMIN
```

Prefer MFA for all admin roles.

Sensitive operations may require step-up authentication.

### 32.3 Secure Session Handling

- Secure cookies where cookie sessions are used.
- HttpOnly cookies.
- SameSite protection.
- CSRF protection for cookie-based state-changing requests.
- Short session lifetime.
- Explicit session revocation.
- Concurrent-session control.
- No token exposure in URLs.

If bearer tokens are used, keep them short-lived and protect refresh-token storage.

### 32.4 RBAC

Permission checks must occur in FastAPI.

Never rely on frontend route guards alone.

Example:

```text
UI button hidden          = UX
API permission check      = SECURITY
```

The second one is mandatory.

## 33. Admin API Specification

Base path:

```text
/api/admin
```

Authentication:

```text
POST /api/admin/auth/login
POST /api/admin/auth/logout
POST /api/admin/auth/refresh
POST /api/admin/auth/mfa/verify
POST /api/admin/auth/revoke-session
```

Dashboard:

```text
GET /api/admin/dashboard
GET /api/admin/notifications
GET /api/admin/search
```

Users:

```text
GET   /api/admin/users
GET   /api/admin/users/{user_id}
GET   /api/admin/users/{user_id}/history
GET   /api/admin/users/{user_id}/transactions
GET   /api/admin/users/{user_id}/sessions
GET   /api/admin/users/{user_id}/security-events
PATCH /api/admin/users/{user_id}/status
```

Wallet/transactions:

```text
GET  /api/admin/wallets
GET  /api/admin/transactions
POST /api/admin/wallet-adjustments
```

Rounds:

```text
GET /api/admin/rounds
GET /api/admin/rounds/{round_id}
```

Fairness:

```text
GET  /api/admin/fairness/{round_id}
POST /api/admin/fairness/{round_id}/verify
```

Audit:

```text
GET /api/admin/audit-logs
```

Settings:

```text
GET   /api/admin/settings
PATCH /api/admin/settings
```

System:

```text
GET /api/admin/system/health
GET /api/admin/system/metrics
GET /api/admin/system/security
```

Admin management:

```text
GET    /api/admin/admins
POST   /api/admin/admins
GET    /api/admin/admins/{admin_id}
PATCH  /api/admin/admins/{admin_id}
POST   /api/admin/admins/{admin_id}/revoke-sessions
```

No endpoint may exist for manually changing an authoritative individual round result.

## 34. Admin Database Design

Use/extend the core project tables:

### users

```text
id
username
email
password_hash
created_at
last_login_at
status
role
```

### wallets

```text
id
user_id
balance
updated_at
```

### transactions

```text
id
user_id
type
amount
balance_before
balance_after
reference_id
created_at
```

### rounds

```text
id
round_number
server_seed_hash
server_seed
client_seed
crash_multiplier
started_at
ended_at
status
```

### audit_logs

```text
id
admin_user_id
action
target_type
target_id
payload_json
ip_address
created_at
```

Recommended additional admin security tables:

### admin_sessions

```text
id
admin_user_id
session_identifier
created_at
last_seen_at
expires_at
revoked_at
ip_address
user_agent
device_metadata
```

### admin_mfa

```text
id
admin_user_id
method
secret_reference
enabled
created_at
updated_at
```

Never store sensitive MFA secrets in plaintext if the deployment architecture supports protected secret storage.

### security_events

```text
id
event_type
severity
user_id
admin_user_id
ip_address
metadata_json
created_at
```

## 35. Virtual-Credit Administration

Virtual-credit management is operational only.

Allowed:

- Add test/demo credits where authorized.
- Remove virtual credits where authorized.
- Correct an operationally documented virtual-credit error.

Every adjustment requires:

```text
Actor
Target user
Reason
Before balance
Adjustment
After balance
Timestamp
Reference
Audit ID
```

Never implement:

- Cash deposit.
- Cash withdrawal.
- Payment settlement.
- Cryptocurrency transfer.
- Real-money wallet.

## 36. Fairness Administration

The Admin Panel may:

- Inspect commitment hashes.
- Inspect revealed post-round seeds.
- Verify fairness.
- Review verification history.
- Review fairness audit events.

The Admin Panel may NOT:

- Replace a server seed.
- Replace a commitment hash.
- Change a crash multiplier.
- Change a crash timestamp.
- Re-settle a round manually.
- Create a secret outcome override.

## 37. Game Configuration Administration

All configuration must be validated against safe limits.

Examples:

```text
minimum_bet
maximum_bet
starting_balance
betting_window_ms
house_edge
game_speed
animation_speed
maintenance_mode
```

Changes must be:

```text
Authenticate
    ↓
Authorize
    ↓
Validate
    ↓
Save transactionally
    ↓
Audit
    ↓
Return sanitized result
```

SUPER_ADMIN-only controls must be enforced server-side.

## 38. Audit Requirements

Audit logs are append-only.

For each sensitive action record:

```text
Who
What
When
Target
Before
After
Reason
Request ID
IP/session metadata where appropriate
```

Never record:

- Passwords.
- JWT signing secrets.
- Refresh tokens.
- Database credentials.
- Active server seeds.
- Private cryptographic keys.

## 39. Admin API Security

Mandatory:

- HTTPS only.
- TLS.
- HSTS.
- Strict CORS.
- CSP.
- Clickjacking protection.
- CSRF protection where cookie sessions are used.
- Rate limiting.
- Strict input validation.
- Request-size limits.
- Request timeouts.
- Authentication.
- Authorization.
- Audit logging.
- Safe error messages.
- Request IDs.

Never expose:

- Stack traces.
- SQL errors.
- Secrets.
- Environment variables.
- Internal credentials.

## 40. Admin Frontend Security

The web frontend must never contain:

- Database passwords.
- JWT signing secrets.
- Backend private keys.
- Server seeds.
- Internal infrastructure credentials.

Frontend route protection is not sufficient.

Every sensitive operation must be checked again by FastAPI.

Use:

- Secure headers.
- CSP.
- Trusted origins.
- Input escaping.
- Output encoding.
- Safe DOM APIs.
- No dangerous HTML injection.
- Dependency pinning.
- Dependency vulnerability scanning.

## 41. Admin UI Design

Use the Anti-Gravity visual identity:

- Dark futuristic/deep-space aesthetic.
- Purple primary accent.
- Cyan highlights.
- White primary text.
- Muted secondary text.
- Green success states.
- Red security/error states.
- Gold important/warning states.
- Orbitron/Inter/Roboto/JetBrains Mono where appropriate.

Layout:

```text
+-------------------------------------------------------------+
| LOGO | Search | Notifications | Admin Profile              |
+-------+-----------------------------------------------------+
|       |                                                     |
| Dash  |                 Main Content                        |
| Live  |                                                     |
| Users |                                                     |
| Wallet|                                                     |
| Txns  |                                                     |
| Rounds|                                                     |
| Fair  |                                                     |
| Audit |                                                     |
| Config|                                                     |
| Maint |                                                     |
| Health|                                                     |
| Metric|                                                     |
| Securi|                                                     |
| Admins|                                                     |
+-------+-----------------------------------------------------+
```

Responsive requirements:

- Desktop.
- Laptop.
- Tablet.
- Mobile browser.

Do not make critical security actions depend only on hover.

## 42. Admin Testing Strategy

### Authentication

- Valid login.
- Invalid login.
- Rate limiting.
- Lockout.
- MFA success.
- MFA failure.
- Expired token.
- Revoked token.
- Refresh-token rotation.
- Refresh-token replay.

### RBAC

Test every role against every sensitive endpoint.

Expected result:

```text
Authorized   -> success
Unauthorized -> 403
Unauthenticated -> 401
```

### User Management

- Search.
- Filter.
- Pagination.
- Status change.
- Unauthorized status change.
- Cross-user access.

### Wallet

- Authorized adjustment.
- Unauthorized adjustment.
- Missing reason.
- Invalid amount.
- Transaction integrity.
- Audit creation.
- Before/after balance accuracy.

### Rounds

- Round listing.
- Round detail.
- Live monitoring.
- Historical filtering.
- No outcome manipulation endpoint.

### Fairness

- Valid verification.
- Invalid verification.
- Tampered seed detection.
- Active seed protection.
- Audit record.

### Audit

- Audit creation.
- Audit immutability.
- No delete.
- No update.
- Permission restrictions.

### Settings

- Valid setting.
- Invalid setting.
- Unauthorized setting.
- SUPER_ADMIN-only setting.
- Audit.

### Security

- SQL injection.
- XSS.
- CSRF where applicable.
- Broken access control.
- IDOR.
- Brute force.
- Rate limit bypass.
- Token replay.
- Session fixation.
- Privilege escalation.
- WebSocket misuse.

## 43. Admin Performance & Reliability

Target:

- Fast dashboard load.
- Paginated tables.
- Indexed searches.
- Efficient API queries.
- WebSocket/live data without excessive polling.
- Proper connection pooling.
- Graceful backend failure.
- Clear degraded-state UI.

Never allow an expensive admin query to overload the game engine or player API.

Admin analytics must not block gameplay-critical database operations.

## 44. Admin Monitoring & Alerts

Monitor:

- Admin login failures.
- Privilege changes.
- Wallet adjustments.
- Configuration changes.
- Maintenance changes.
- API error rate.
- Database latency.
- WebSocket health.
- Game-loop health.
- Backup failures.
- Authentication anomalies.

Alert on:

- Repeated failed admin logins.
- Suspicious privilege changes.
- Unexpected security-event spikes.
- Database failures.
- Game-loop failure.
- Backup failure.
- API outage.

## 45. Backup & Recovery

Production admin operations depend on reliable backups.

Implement:

- Automated PostgreSQL backups.
- Backup retention policy.
- Backup encryption.
- Restore testing.
- Disaster-recovery documentation.
- Recovery-point objectives.
- Recovery-time objectives.

Never claim backup protection without testing a restore.

## 46. Deployment

Recommended production path:

```text
Developer Windows Laptop
        |
        v
     GitHub
        |
        v
CI/CD
        |
        +---- Tests
        +---- Security checks
        +---- Admin frontend build
        +---- Backend deployment
        |
        v
Production Infrastructure
        |
        +---- FastAPI
        +---- PostgreSQL
        +---- TLS
        +---- Monitoring
        +---- Backups
```

The Admin Panel must be deployed over HTTPS.

## 47. Admin Definition of Done

### Authentication

- [ ] Secure admin login.
- [ ] Argon2id.
- [ ] Short-lived sessions/tokens.
- [ ] Refresh rotation.
- [ ] Revocation.
- [ ] MFA.
- [ ] Lockout.
- [ ] Rate limiting.
- [ ] Secure logout.

### RBAC

- [ ] SUPER_ADMIN.
- [ ] ADMIN.
- [ ] OPERATOR.
- [ ] AUDITOR.
- [ ] SUPPORT.
- [ ] Every sensitive endpoint permission-checked server-side.

### UI

- [ ] Login.
- [ ] Dashboard.
- [ ] Live game monitor.
- [ ] Users.
- [ ] User details.
- [ ] Wallets.
- [ ] Transactions.
- [ ] Rounds.
- [ ] Round details.
- [ ] Fairness.
- [ ] Audit logs.
- [ ] Game settings.
- [ ] Maintenance.
- [ ] System health.
- [ ] System metrics.
- [ ] Security.
- [ ] Admin profile.
- [ ] Admin role management.
- [ ] Notifications.
- [ ] Global search.
- [ ] Responsive design.

### Security

- [ ] HTTPS.
- [ ] HSTS.
- [ ] CSP.
- [ ] CORS.
- [ ] CSRF protection where applicable.
- [ ] Rate limiting.
- [ ] Input validation.
- [ ] Secure session handling.
- [ ] No secrets in frontend.
- [ ] No database credentials in frontend.
- [ ] No active server seeds exposed.
- [ ] No hidden outcome override.

### Operations

- [ ] User management.
- [ ] Virtual-credit management.
- [ ] Transaction inspection.
- [ ] Round monitoring.
- [ ] Game settings.
- [ ] Maintenance mode.
- [ ] Fairness verification.
- [ ] Audit logs.
- [ ] System health.
- [ ] System metrics.
- [ ] Security monitoring.
- [ ] Backups/recovery.

### Critical Acceptance

- [ ] Admin cannot alter authoritative round outcomes.
- [ ] Admin cannot bypass RBAC.
- [ ] Every sensitive action is audited.
- [ ] Audit records cannot be deleted/modified through UI.
- [ ] Active/future seeds remain protected.
- [ ] No real-money functionality exists.

## 48. Admin Development Order

1. Admin project structure.
2. Login UI.
3. Secure authentication.
4. MFA.
5. RBAC middleware.
6. Dashboard.
7. User management.
8. User details.
9. Wallet/transaction views.
10. Round monitoring.
11. Fairness verification.
12. Audit logs.
13. Game settings.
14. Maintenance mode.
15. System health.
16. System metrics.
17. Security monitoring.
18. Admin profile.
19. Admin role management.
20. Notifications.
21. Global search.
22. Security testing.
23. Performance testing.
24. Production deployment.
25. Backup/recovery validation.

## 49. Relationship With Player App

The player app and Admin Panel share the same authoritative FastAPI backend.

```text
                    FASTAPI
                      |
        +-------------+-------------+
        |                           |
  Player API/Admin API          PostgreSQL
        |
   +----+----+
   |         |
Android     Admin
App         Browser
```

The player app must never call admin APIs.

The Admin Panel must never bypass the backend.

Both clients are untrusted from the perspective of the server.

## 50. Final Admin Security Principle

> **The Admin Panel is an operational control center, not a backdoor.**

It can control authorized operational settings and virtual-credit administration, monitor the system, manage users, verify fairness, and review audits.

It cannot rewrite history, bypass RBAC, reveal secrets, or manually determine an individual game's authoritative outcome.

## 51. Current Operating Plan

| Decision | Choice |
|---|---|
| Admin Platform | Separate authenticated web app |
| Backend | Python + FastAPI |
| Database | PostgreSQL production |
| Authentication | Strong admin authentication + MFA |
| Authorization | RBAC |
| Transport | HTTPS |
| Audit | Append-only |
| Game Authority | Server |
| Outcome Override | Prohibited |
| Economy | Virtual credits only |
| Development | Antigravity IDE on Windows |
| Deployment | Production HTTPS infrastructure |

