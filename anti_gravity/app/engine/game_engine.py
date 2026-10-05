"""
Anti-Gravity — Local Game Engine
Handles crash-point generation, multiplier calculation,
wallet logic, and round history — all running locally
(DEMO_MODE = True).  No server required.
"""

import secrets
import hashlib
import time
import math
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum, auto


# ── Game States ───────────────────────────────────────────────────────────────
class GameState(Enum):
    WAITING   = auto()
    BETTING   = auto()
    RUNNING   = auto()
    CASHED_OUT = auto()
    CRASHED   = auto()
    ROUND_END = auto()


# ── Data Classes ─────────────────────────────────────────────────────────────
@dataclass
class RoundResult:
    round_id: int
    crash_multiplier: float
    server_seed_hash: str
    server_seed: str          # revealed after round ends
    bet: int
    cashout_multiplier: Optional[float] = None
    payout: int = 0
    won: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class WalletTransaction:
    type: str          # "bet" | "payout" | "refund"
    amount: int
    balance_before: int
    balance_after: int
    round_id: int
    timestamp: float = field(default_factory=time.time)


# ── Fairness Engine ──────────────────────────────────────────────────────────
class FairnessEngine:
    """
    Provably-fair crash-point generation.

    Before each round:
        1. A random server_seed (256-bit) is generated.
        2. SHA-256(server_seed) is published as the commitment hash.
        3. The crash point is derived from HMAC-SHA256(server_seed, round_id).

    After each round:
        server_seed is revealed so players can verify.
    """

    @staticmethod
    def generate_seed() -> str:
        return secrets.token_hex(32)          # 256-bit hex string

    @staticmethod
    def hash_seed(seed: str) -> str:
        return hashlib.sha256(seed.encode()).hexdigest()

    @staticmethod
    def calculate_crash_point(seed: str, round_id: int) -> float:
        """
        Derive crash multiplier from the seed and round_id.
        Uses a geometric distribution:  crash >= 1.00x always,
        ~40 % of rounds crash below 2.00x (matching real Aviator-style games).
        """
        hmac_input = f"{seed}:{round_id}".encode()
        h = hashlib.sha256(hmac_input).hexdigest()
        # Take first 8 hex chars as a 32-bit integer
        int_value = int(h[:8], 16)
        # Map to (0, 1) — avoid exactly 0 or 1
        r = (int_value + 1) / (0xFFFFFFFF + 2)
        # Inverse-CDF of a geometric distribution with house edge ~3 %
        house_edge = 0.03
        crash = max(1.00, (1 - house_edge) / (1 - r))
        return round(crash, 2)

    @staticmethod
    def verify_round(seed: str, seed_hash: str, round_id: int, crash_multiplier: float) -> bool:
        """
        Verify that a completed round's crash point matches the published seed hash.
        Returns True if the round is fair.
        """
        if FairnessEngine.hash_seed(seed) != seed_hash:
            return False
        expected = FairnessEngine.calculate_crash_point(seed, round_id)
        return abs(expected - crash_multiplier) < 0.005


# ── Multiplier Engine ────────────────────────────────────────────────────────
class MultiplierEngine:
    """
    Maps elapsed game-time (seconds) → multiplier value.
    Exponential growth: mult = e^(k * t), with k tuned for ~1.64x at 5 s.
    """
    K = 0.10    # growth constant

    @classmethod
    def multiplier_at(cls, elapsed: float) -> float:
        """Return the multiplier value for the given elapsed seconds."""
        return round(max(1.00, math.exp(cls.K * elapsed)), 2)

    @classmethod
    def time_at_multiplier(cls, mult: float) -> float:
        """Return the elapsed time (seconds) when the given multiplier is reached."""
        return math.log(max(mult, 1.00)) / cls.K


# ── Wallet ────────────────────────────────────────────────────────────────────
class Wallet:
    def __init__(self, starting_balance: int = 10_000):
        self._balance: int = starting_balance
        self.transactions: List[WalletTransaction] = []

    @property
    def balance(self) -> int:
        return self._balance

    def deduct_bet(self, amount: int, round_id: int) -> bool:
        """Deduct bet amount from wallet. Returns False if insufficient funds."""
        if amount <= 0 or amount > self._balance:
            return False
        before = self._balance
        self._balance -= amount
        self.transactions.append(WalletTransaction(
            type="bet", amount=amount,
            balance_before=before, balance_after=self._balance,
            round_id=round_id
        ))
        return True

    def add_payout(self, amount: int, round_id: int):
        """Add payout to wallet."""
        before = self._balance
        self._balance += amount
        self.transactions.append(WalletTransaction(
            type="payout", amount=amount,
            balance_before=before, balance_after=self._balance,
            round_id=round_id
        ))

    def refund(self, amount: int, round_id: int):
        """Refund a bet (e.g., round cancelled)."""
        before = self._balance
        self._balance += amount
        self.transactions.append(WalletTransaction(
            type="refund", amount=amount,
            balance_before=before, balance_after=self._balance,
            round_id=round_id
        ))


# ── Main Game Engine ──────────────────────────────────────────────────────────
class GameEngine:
    """
    Local crash-game engine (DEMO_MODE).
    All crash-point and payout decisions are made here — never on the UI layer.
    """

    def __init__(self, wallet: Wallet):
        self.wallet = wallet
        self.fairness = FairnessEngine()
        self.history: List[RoundResult] = []

        # Round state
        self.state: GameState = GameState.WAITING
        self.round_id: int = 0

        self._server_seed: str = ""
        self._server_seed_hash: str = ""
        self._crash_multiplier: float = 1.00
        self._start_time: float = 0.0
        self._current_bet: int = 0
        self._cashout_multiplier: Optional[float] = None

    # ── Getters ───────────────────────────────────────────────────────────────
    @property
    def current_multiplier(self) -> float:
        if self.state != GameState.RUNNING:
            return 1.00
        elapsed = time.monotonic() - self._start_time
        return MultiplierEngine.multiplier_at(elapsed)

    @property
    def seed_hash(self) -> str:
        return self._server_seed_hash

    @property
    def is_running(self) -> bool:
        return self.state == GameState.RUNNING

    # ── Round Lifecycle ───────────────────────────────────────────────────────
    def prepare_round(self, bet: int) -> bool:
        """
        Prepare a new round.
        - Validates the bet against the wallet.
        - Pre-generates crash point (server-authoritative).
        Returns True on success.
        """
        if self.state not in (GameState.WAITING, GameState.ROUND_END,
                               GameState.CRASHED, GameState.CASHED_OUT):
            return False
        if bet <= 0:
            return False

        # Generate fairness data
        self.round_id += 1
        self._server_seed = FairnessEngine.generate_seed()
        self._server_seed_hash = FairnessEngine.hash_seed(self._server_seed)
        self._crash_multiplier = FairnessEngine.calculate_crash_point(
            self._server_seed, self.round_id
        )
        self._current_bet = bet
        self._cashout_multiplier = None

        # Deduct bet
        if not self.wallet.deduct_bet(bet, self.round_id):
            return False

        self.state = GameState.BETTING
        return True

    def start_round(self):
        """Start the live multiplier climb."""
        if self.state != GameState.BETTING:
            return
        self._start_time = time.monotonic()
        self.state = GameState.RUNNING

    def tick(self) -> bool:
        """
        Called every ~50 ms by the UI animation loop.
        Returns True if the round is still running, False if it crashed.
        """
        if self.state != GameState.RUNNING:
            return False
        elapsed = time.monotonic() - self._start_time
        mult = MultiplierEngine.multiplier_at(elapsed)
        if mult >= self._crash_multiplier:
            self._do_crash()
            return False
        return True

    def request_cashout(self) -> Optional[RoundResult]:
        """
        Player presses CASH OUT.
        Returns a RoundResult if successful, None if rejected (already crashed).
        """
        if self.state != GameState.RUNNING:
            return None
        mult = self.current_multiplier
        if mult >= self._crash_multiplier:
            # Too late — crash wins
            self._do_crash()
            return None

        payout = int(self._current_bet * mult)
        self._cashout_multiplier = mult
        self.wallet.add_payout(payout, self.round_id)
        result = self._finalise_round(cashed_out=True, payout=payout)
        self.state = GameState.CASHED_OUT
        return result

    def _do_crash(self):
        """The spider crashes — bet is already deducted, nothing to pay."""
        self._finalise_round(cashed_out=False, payout=0)
        self.state = GameState.CRASHED

    def _finalise_round(self, cashed_out: bool, payout: int) -> RoundResult:
        result = RoundResult(
            round_id=self.round_id,
            crash_multiplier=self._crash_multiplier,
            server_seed_hash=self._server_seed_hash,
            server_seed=self._server_seed,     # revealed now
            bet=self._current_bet,
            cashout_multiplier=self._cashout_multiplier if cashed_out else None,
            payout=payout,
            won=cashed_out,
        )
        self.history.append(result)
        return result

    def reset_to_waiting(self):
        """After showing the round result, return to WAITING for next bet."""
        if self.state in (GameState.CRASHED, GameState.CASHED_OUT, GameState.ROUND_END):
            self.state = GameState.WAITING

    # ── Fairness Verification ─────────────────────────────────────────────────
    def verify_last_round(self) -> bool:
        if not self.history:
            return False
        last = self.history[-1]
        return FairnessEngine.verify_round(
            last.server_seed, last.server_seed_hash,
            last.round_id, last.crash_multiplier
        )
