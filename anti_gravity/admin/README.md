# Anti-Gravity — Admin Operations & Audit Panel

> **Document:** Admin Panel Documentation & Architecture  
> **Status:** Active  
> **Owner:** Mafizul Khan  
> **Environment:** Antigravity IDE · Windows · Python  

---

## 1. Overview

The Admin Panel is a **first-class product component** of the Anti-Gravity system. It is a separate authenticated web application communicating strictly via protected `/api/admin/*` FastAPI endpoints.

### Key Boundaries & Invariants
- **Virtual Credits Only:** The admin panel never provides real-money deposits, withdrawals, payment gateways, or cash transactions.
- **Outcome Immutability:** **No mechanism exists** (API endpoint, button, database flag, or secret command) to manually alter or manipulate authoritative game crash multipliers, round results, or player cash-out states.
- **Append-Only Audit Trails:** Every administrative modification (settings change, account ban/unban, virtual-credit adjustment) generates an immutable, timestamped audit log.

---

## 2. Admin Roles & Permissions (RBAC)

| Role | Description | Allowed Actions |
|---|---|---|
| `SUPER_ADMIN` | Root Administrator | Full operational access + House Edge changes + User Role adjustments |
| `ADMIN` | Senior Operator | Operational control, wallet adjustments, account ban/unban, configuration |
| `OPERATOR` | Game Operator | Live round monitoring, user view, maintenance mode toggling |
| `AUDITOR` | Compliance / Audit | Read-only access to audit logs, financial transactions, and fairness verification |
| `SUPPORT` | Customer Support | Read-only access to user profiles and round history |

---

## 3. Web Console Architecture & Access

- **URL:** `http://localhost:8000/admin` (or `https://your-domain.com/admin`)
- **API Base:** `/api/admin/*`
- **UI Stack:** Vanilla HTML5, Futuristic Cyber CSS (Design tokens matching Anti-Gravity spec), JavaScript ES6 SPA
- **Real-Time Telemetry:** Polling and WebSocket live stream at `/ws/game`

---

## 4. Protected Endpoints Summary

```
POST   /api/admin/auth/login               # Authenticate admin user (JWT)
POST   /api/admin/auth/logout              # Audit administrative logout
GET    /api/admin/dashboard                # Live system & round telemetry
GET    /api/admin/users                    # Search and list user accounts
GET    /api/admin/users/{id}               # Detailed profile & wagering summary
PATCH  /api/admin/users/{id}/status        # Ban / Unban user with reason
PATCH  /api/admin/users/{id}/role          # Modify user role (Super Admin only)
GET    /api/admin/users/{id}/history       # Bet history
GET    /api/admin/users/{id}/transactions  # Transaction history
POST   /api/admin/wallet-adjustments       # Manual virtual credit adjustment
GET    /api/admin/transactions             # Full financial audit ledger
GET    /api/admin/rounds                   # Round monitoring & wager aggregations
GET    /api/admin/rounds/{id}              # Round detail with player bet breakdown
GET    /api/admin/settings                 # Read game configuration
PATCH  /api/admin/settings                 # Update min/max bet, window, maintenance mode
GET    /api/admin/fairness/{id}            # View commitment hash & revealed seed
POST   /api/admin/fairness/{id}/verify     # Cryptographic fairness verification
GET    /api/admin/audit-logs               # Read append-only audit trail
GET    /api/admin/system/health            # Backend, DB, WS diagnostic health
GET    /api/admin/system/metrics           # System metrics
```
