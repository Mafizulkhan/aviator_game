"""
Anti-Gravity Backend — Server-Authoritative Game Loop
Runs continuous round cycles (WAITING -> ROUND_STARTED -> MULTIPLIER_UPDATE -> ROUND_CRASHED -> ROUND_ENDED -> WAITING)
and broadcasts live WebSocket updates to connected clients.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models import RoundStatus
from backend.services.game_service import (
    get_current_round, start_round, resolve_round_if_crashed,
    _active_round_internal, _create_new_round
)
from backend.services.audit_service import AuditService
from app.engine.game_engine import FairnessEngine, MultiplierEngine
from backend.ws.connection_manager import manager


class GameLoop:
    """
    Server-authoritative real-time game loop.
    Calculates multiplier dynamically from monotonic elapsed time.
    """

    def __init__(
        self,
        tick_interval: float = settings.GAME_LOOP_TICK_INTERVAL,
        waiting_duration: float = settings.GAME_LOOP_WAITING_DURATION,
        ended_duration: float = settings.GAME_LOOP_ENDED_DURATION,
        connection_manager=manager,
        session_factory: Optional[Callable] = None,
    ):
        self.tick_interval = tick_interval
        self.waiting_duration = waiting_duration
        self.ended_duration = ended_duration
        self.connection_manager = connection_manager
        self.session_factory = session_factory or AsyncSessionLocal
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.current_state_cache: Dict[str, Any] = {}

    def start(self):
        """Start the background game loop task if not already running."""
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._run_loop())

    def stop(self):
        """Synchronously stop the background game loop task."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def stop_async(self):
        """Asynchronously stop the background game loop and await cancellation."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            self._task = None

    async def get_initial_client_message(self, db_session=None) -> Dict[str, Any]:
        """
        Return state message for a newly connected WebSocket client or sync call.
        """
        if self.current_state_cache:
            return self.current_state_cache

        close_session = False
        if db_session is None:
            db_session = self.session_factory()
            close_session = True

        try:
            round_row = await get_current_round(db_session)
            now_iso = datetime.now(timezone.utc).isoformat()
            if round_row.status == RoundStatus.running and round_row.started_at:
                elapsed = (datetime.now(timezone.utc) - round_row.started_at.replace(tzinfo=timezone.utc)).total_seconds()
                mult = MultiplierEngine.multiplier_at(elapsed)
                return {
                    "type": "MULTIPLIER_UPDATE",
                    "round_id": round_row.id,
                    "round_number": round_row.round_number,
                    "multiplier": mult,
                    "server_time": now_iso,
                    "status": "running"
                }
            elif round_row.status == RoundStatus.crashed:
                return {
                    "type": "ROUND_CRASHED",
                    "round_id": round_row.id,
                    "round_number": round_row.round_number,
                    "crash_multiplier": round_row.crash_multiplier or 1.0,
                    "server_time": now_iso
                }
            else:
                return {
                    "type": "ROUND_WAITING",
                    "round_id": round_row.id,
                    "round_number": round_row.round_number,
                    "hash": round_row.server_seed_hash,
                    "server_time": now_iso,
                    "status": "waiting",
                    "next_round_in": self.waiting_duration
                }
        finally:
            if close_session:
                await db_session.close()

    async def _run_loop(self):
        """Main loop executing round lifecycles continuously."""
        while self.is_running:
            try:
                await self._run_single_round()
            except asyncio.CancelledError:
                break
            except Exception as e:
                if not self.is_running:
                    break
                print(f"[GameLoop Error] {e}")
                await asyncio.sleep(1.0)

    async def _run_single_round(self):
        """Execute one complete round lifecycle: WAITING -> ROUND_STARTED -> MULTIPLIER_UPDATE -> ROUND_CRASHED -> ROUND_ENDED."""
        # ── 1. Fetch or create pending round ──
        async with self.session_factory() as db:
            round_row = await get_current_round(db)
            if round_row.status == RoundStatus.crashed:
                round_row = await _create_new_round(db)

            round_id = round_row.id
            round_number = round_row.round_number
            seed_hash = round_row.server_seed_hash
            is_pending = (round_row.status == RoundStatus.pending)

        # ── 2. WAITING (ROUND_WAITING) ──
        if is_pending:
            waiting_msg = {
                "type": "ROUND_WAITING",
                "round_id": round_id,
                "round_number": round_number,
                "hash": seed_hash,
                "server_time": datetime.now(timezone.utc).isoformat(),
                "status": "waiting",
                "next_round_in": self.waiting_duration
            }
            self.current_state_cache = waiting_msg
            await self.connection_manager.broadcast(waiting_msg)

            # Sleep in small increments to respond quickly to shutdown (outside DB session)
            sleep_elapsed = 0.0
            while sleep_elapsed < self.waiting_duration and self.is_running:
                step = min(0.05, self.waiting_duration - sleep_elapsed)
                await asyncio.sleep(step)
                sleep_elapsed += step

            if not self.is_running:
                return

            # Transition to running in DB
            async with self.session_factory() as db:
                current_r = await get_current_round(db)
                if current_r.status == RoundStatus.pending:
                    round_row = await start_round(db, current_r)
                    round_id = round_row.id
                    round_number = round_row.round_number
                    started_at = round_row.started_at
                else:
                    started_at = current_r.started_at
        else:
            started_at = None

        # ── 3. ROUND_STARTED ──
        seed = _active_round_internal.get(round_id)
        if not seed:
            seed = FairnessEngine.generate_seed()
            _active_round_internal[round_id] = seed

        crash_mult = FairnessEngine.calculate_crash_point(seed, round_number)
        crash_time = MultiplierEngine.time_at_multiplier(crash_mult)

        started_msg = {
            "type": "ROUND_STARTED",
            "round_id": round_id,
            "round_number": round_number,
            "server_time": datetime.now(timezone.utc).isoformat(),
            "status": "running"
        }
        self.current_state_cache = started_msg
        await self.connection_manager.broadcast(started_msg)

        # Calculate monotonic start time
        if started_at:
            elapsed_past = (datetime.now(timezone.utc) - started_at.replace(tzinfo=timezone.utc)).total_seconds()
            start_mono = time.monotonic() - elapsed_past
        else:
            start_mono = time.monotonic()

        # ── 4. MULTIPLIER_UPDATE Ticks (in-memory, outside DB session) ──
        while self.is_running:
            elapsed = time.monotonic() - start_mono
            if elapsed >= crash_time:
                break

            current_mult = MultiplierEngine.multiplier_at(elapsed)
            mult_msg = {
                "type": "MULTIPLIER_UPDATE",
                "round_id": round_id,
                "round_number": round_number,
                "multiplier": current_mult,
                "server_time": datetime.now(timezone.utc).isoformat()
            }
            self.current_state_cache = mult_msg
            await self.connection_manager.broadcast(mult_msg)
            await asyncio.sleep(self.tick_interval)

        if not self.is_running:
            return

        # ── 5. ROUND_CRASHED (DB update) ──
        async with self.session_factory() as db:
            current_r = await get_current_round(db)
            await resolve_round_if_crashed(db, current_r)

        crashed_msg = {
            "type": "ROUND_CRASHED",
            "round_id": round_id,
            "round_number": round_number,
            "crash_multiplier": crash_mult,
            "server_time": datetime.now(timezone.utc).isoformat()
        }
        self.current_state_cache = crashed_msg
        await self.connection_manager.broadcast(crashed_msg)

        # ── 6. ROUND_ENDED ──
        ended_msg = {
            "type": "ROUND_ENDED",
            "round_id": round_id,
            "round_number": round_number,
            "server_time": datetime.now(timezone.utc).isoformat()
        }
        self.current_state_cache = ended_msg
        await self.connection_manager.broadcast(ended_msg)
        AuditService.log_round_ended(round_id, round_number)

        # Sleep in small increments during ended duration (outside DB session)
        sleep_elapsed = 0.0
        while sleep_elapsed < self.ended_duration and self.is_running:
            step = min(0.05, self.ended_duration - sleep_elapsed)
            await asyncio.sleep(step)
            sleep_elapsed += step

        if not self.is_running:
            return

        # Prepare for next round by creating a new round in DB
        async with self.session_factory() as db:
            await _create_new_round(db)


game_loop = GameLoop()
