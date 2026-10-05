"""
Anti-Gravity — HTTP API Client
Manages REST API interactions with the FastAPI backend (/api/*).
Thread-safe execution for Kivy.
"""

import threading
import logging
from typing import Optional, Dict, Any, Callable
import httpx

from app.config import API_BASE_URL

logger = logging.getLogger("anti_gravity.api_client")


class ApiClient:
    """HTTP Client for Anti-Gravity backend REST endpoints."""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.access_token: Optional[str] = None
        self.username: Optional[str] = None
        self.balance: int = 10000

    def set_token(self, token: str, username: Optional[str] = None):
        """Set authentication token."""
        self.access_token = token
        if username:
            self.username = username

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def authenticate_demo_sync(self, username: str = "pilot_kivy", password: str = "pilot_pass123") -> bool:
        """Authenticate or register a demo user synchronously."""
        try:
            with httpx.Client(timeout=5.0) as client:
                # Try login
                login_resp = client.post(
                    f"{self.base_url}/auth/login",
                    json={"username": username, "password": password},
                )
                if login_resp.status_code == 200:
                    data = login_resp.json()
                    self.set_token(data["access_token"], data["username"])
                    self.balance = data.get("balance", 10000)
                    return True

                # If login failed, try register
                reg_resp = client.post(
                    f"{self.base_url}/auth/register",
                    json={"username": username, "password": password},
                )
                if reg_resp.status_code in (200, 201):
                    data = reg_resp.json()
                    self.set_token(data["access_token"], data["username"])
                    self.balance = data.get("balance", 10000)
                    return True
        except Exception as e:
            logger.warning(f"Demo authentication failed: {e}")
        return False

    def ensure_auth(self):
        """Ensure an access token exists, authenticating demo account if necessary."""
        if not self.access_token:
            self.authenticate_demo_sync()

    # ── Game Endpoints ────────────────────────────────────────────────────────
    def get_current_round_sync(self) -> Optional[Dict[str, Any]]:
        """Fetch current round snapshot from GET /api/game/current."""
        self.ensure_auth()
        try:
            with httpx.Client(timeout=4.0) as client:
                resp = client.get(f"{self.base_url}/game/current", headers=self._get_headers())
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"Failed to fetch current round: {e}")
        return None

    def join_round_sync(self, amount: int) -> Optional[Dict[str, Any]]:
        """Join current round via POST /api/game/join."""
        self.ensure_auth()
        try:
            with httpx.Client(timeout=4.0) as client:
                resp = client.post(
                    f"{self.base_url}/game/join",
                    json={"amount": amount},
                    headers=self._get_headers()
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    self.balance = data.get("balance_after", self.balance)
                    return data
                else:
                    logger.warning(f"Join round failed: {resp.status_code} {resp.text}")
                    return None
        except Exception as e:
            logger.warning(f"Join round error: {e}")
            return None

    def cashout_sync(self, bet_id: int) -> Optional[Dict[str, Any]]:
        """Request cashout via POST /api/game/cashout."""
        self.ensure_auth()
        try:
            with httpx.Client(timeout=4.0) as client:
                resp = client.post(
                    f"{self.base_url}/game/cashout",
                    json={"bet_id": bet_id},
                    headers=self._get_headers()
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self.balance = data.get("balance_after", self.balance)
                    return data
                else:
                    logger.warning(f"Cashout failed: {resp.status_code} {resp.text}")
                    return None
        except Exception as e:
            logger.warning(f"Cashout error: {e}")
            return None

    def get_balance_sync(self) -> Optional[int]:
        """Fetch player balance via GET /api/player/balance."""
        self.ensure_auth()
        try:
            with httpx.Client(timeout=4.0) as client:
                resp = client.get(f"{self.base_url}/player/balance", headers=self._get_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    self.balance = data.get("balance", self.balance)
                    return self.balance
        except Exception as e:
            logger.warning(f"Balance fetch error: {e}")
        return None

    # ── Async / Threaded Helpers for Kivy ─────────────────────────────────────
    def cashout_async(self, bet_id: int, on_success: Callable[[Dict[str, Any]], None], on_failure: Callable[[str], None]):
        """Perform cashout on a background thread and dispatch result to callbacks."""
        def worker():
            res = self.cashout_sync(bet_id)
            if res:
                self._dispatch_ui(on_success, res)
            else:
                self._dispatch_ui(on_failure, "Cash-out rejected by server")

        threading.Thread(target=worker, daemon=True).start()

    def join_round_async(self, amount: int, on_success: Callable[[Dict[str, Any]], None], on_failure: Callable[[str], None]):
        """Perform join_round on a background thread and dispatch result to callbacks."""
        def worker():
            res = self.join_round_sync(amount)
            if res:
                self._dispatch_ui(on_success, res)
            else:
                self._dispatch_ui(on_failure, "Failed to place bet")

        threading.Thread(target=worker, daemon=True).start()

    def _dispatch_ui(self, fn: Callable, *args, **kwargs):
        try:
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: fn(*args, **kwargs))
        except Exception:
            fn(*args, **kwargs)


# ── Global Singleton Access ───────────────────────────────────────────────────
_api_client_instance: Optional[ApiClient] = None


def get_api_client() -> ApiClient:
    global _api_client_instance
    if _api_client_instance is None:
        _api_client_instance = ApiClient()
    return _api_client_instance
