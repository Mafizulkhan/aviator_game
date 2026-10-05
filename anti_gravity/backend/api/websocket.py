"""
Anti-Gravity Backend — WebSocket Endpoint
Route: /ws/game

Supports real-time game stream broadcasting, token-based authentication,
message validation, and connection/message rate limiting.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.config import settings
from backend.services.auth_service import decode_access_token
from backend.services.rate_limiter import RateLimiter
from backend.ws.connection_manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/game")
async def websocket_game_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for real-time game synchronisation.

    Authentication:
    - If `token` query param is supplied, it is cryptographically verified.
      Invalid or expired tokens result in closure with code=1008 (Policy Violation).
    - If no token is provided, connects in public spectator mode (backward compatible).
    - Clients can also send an `authenticate` message with `{"type": "auth", "token": "..."}`.

    Rate Limiting:
    - Protects against connection flooding and message spam.
    """
    client_ip = websocket.client.host if websocket.client else "127.0.0.1"

    # ── 1. Connection Rate Limiting ───────────────────────────────────────────
    if not RateLimiter.check_ws_rate_limit(
        client_ip, "ws_connect", settings.RATE_LIMIT_WS_CONNECT_PER_MINUTE
    ):
        await websocket.close(code=1008, reason="Rate limit exceeded")
        return

    # ── 2. Initial Token Validation (if provided in Query) ───────────────────
    authenticated_user_id: Optional[int] = None
    if token is not None:
        payload = decode_access_token(token)
        if payload is None or "sub" not in payload:
            await websocket.close(code=1008, reason="Invalid or expired token")
            return
        try:
            authenticated_user_id = int(payload["sub"])
        except (ValueError, TypeError):
            await websocket.close(code=1008, reason="Malformed token subject")
            return

    await manager.connect(websocket)
    try:
        # ── 3. Connection confirmation ─────────────────────────────────────────
        connected_msg = {
            "type": "CONNECTED",
            "message": "Connected to Anti-Gravity game stream",
            "authenticated": authenticated_user_id is not None,
            "server_time": datetime.now(timezone.utc).isoformat(),
        }
        if authenticated_user_id is not None:
            connected_msg["user_id"] = authenticated_user_id

        await websocket.send_json(connected_msg)

        # ── 4. Message receive loop ────────────────────────────────────────────
        while True:
            data = await websocket.receive_text()

            # Message flood rate limiting
            if not RateLimiter.check_ws_rate_limit(
                client_ip, "ws_message", settings.RATE_LIMIT_WS_MESSAGES_PER_MINUTE
            ):
                await websocket.send_json({
                    "type": "ERROR",
                    "message": "Message rate limit exceeded",
                    "server_time": datetime.now(timezone.utc).isoformat(),
                })
                continue

            try:
                payload = json.loads(data)
                if not isinstance(payload, dict):
                    await websocket.send_json({
                        "type": "ERROR",
                        "message": "Invalid message structure: expected JSON object",
                        "server_time": datetime.now(timezone.utc).isoformat(),
                    })
                    continue

                msg_type = payload.get("type")

                # Handle ping
                if msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "server_time": datetime.now(timezone.utc).isoformat(),
                    })

                # Handle in-band authentication
                elif msg_type in ("auth", "authenticate"):
                    msg_token = payload.get("token")
                    if not msg_token or not isinstance(msg_token, str):
                        await websocket.send_json({
                            "type": "AUTH_ERROR",
                            "message": "Missing token in auth payload",
                            "server_time": datetime.now(timezone.utc).isoformat(),
                        })
                        continue

                    token_payload = decode_access_token(msg_token)
                    if token_payload is None or "sub" not in token_payload:
                        await websocket.send_json({
                            "type": "AUTH_ERROR",
                            "message": "Invalid or expired token",
                            "server_time": datetime.now(timezone.utc).isoformat(),
                        })
                    else:
                        try:
                            authenticated_user_id = int(token_payload["sub"])
                            await websocket.send_json({
                                "type": "AUTH_SUCCESS",
                                "user_id": authenticated_user_id,
                                "server_time": datetime.now(timezone.utc).isoformat(),
                            })
                        except (ValueError, TypeError):
                            await websocket.send_json({
                                "type": "AUTH_ERROR",
                                "message": "Malformed token subject",
                                "server_time": datetime.now(timezone.utc).isoformat(),
                            })

                # Reject any client-supplied game authority assertions safely
                elif msg_type in ("cashout_claim", "multiplier_claim", "crash_claim"):
                    await websocket.send_json({
                        "type": "ERROR",
                        "message": "Game authority resides exclusively on server",
                        "server_time": datetime.now(timezone.utc).isoformat(),
                    })

                # Unrecognized message types
                else:
                    pass  # Ignored safely without crashing

            except (json.JSONDecodeError, UnicodeDecodeError):
                await websocket.send_json({
                    "type": "ERROR",
                    "message": "Invalid message format",
                    "server_time": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                await websocket.send_json({
                    "type": "ERROR",
                    "message": "Internal error processing message",
                    "server_time": datetime.now(timezone.utc).isoformat(),
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
