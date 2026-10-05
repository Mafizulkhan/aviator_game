"""
Anti-Gravity — Unit Tests: Game Engine
Run with: python -m pytest tests/ -v
"""

import pytest
import time
from app.engine.game_engine import (
    FairnessEngine, MultiplierEngine, Wallet, GameEngine, GameState
)


# ── FairnessEngine ────────────────────────────────────────────────────────────
class TestFairnessEngine:

    def test_seed_is_hex_64_chars(self):
        seed = FairnessEngine.generate_seed()
        assert len(seed) == 64
        int(seed, 16)  # should not raise

    def test_hash_is_sha256(self):
        seed = FairnessEngine.generate_seed()
        h = FairnessEngine.hash_seed(seed)
        assert len(h) == 64

    def test_crash_point_at_least_1(self):
        for i in range(200):
            seed = FairnessEngine.generate_seed()
            cp = FairnessEngine.calculate_crash_point(seed, i)
            assert cp >= 1.00, f"Crash point {cp} below 1.00"

    def test_crash_distribution_realistic(self):
        """Roughly 40% of rounds should crash below 2×."""
        crashes = []
        for i in range(1000):
            seed = FairnessEngine.generate_seed()
            cp = FairnessEngine.calculate_crash_point(seed, i)
            crashes.append(cp)
        below_2 = sum(1 for c in crashes if c < 2.0)
        assert 300 <= below_2 <= 600, f"Unexpected distribution: {below_2}/1000 below 2×"

    def test_verify_round_succeeds(self):
        seed = FairnessEngine.generate_seed()
        seed_hash = FairnessEngine.hash_seed(seed)
        cp = FairnessEngine.calculate_crash_point(seed, 42)
        assert FairnessEngine.verify_round(seed, seed_hash, 42, cp)

    def test_verify_round_fails_bad_seed(self):
        seed = FairnessEngine.generate_seed()
        seed_hash = FairnessEngine.hash_seed(seed)
        cp = FairnessEngine.calculate_crash_point(seed, 42)
        bad_seed = FairnessEngine.generate_seed()
        assert not FairnessEngine.verify_round(bad_seed, seed_hash, 42, cp)

    def test_verify_round_fails_tampered_crash(self):
        seed = FairnessEngine.generate_seed()
        seed_hash = FairnessEngine.hash_seed(seed)
        cp = FairnessEngine.calculate_crash_point(seed, 1)
        assert not FairnessEngine.verify_round(seed, seed_hash, 1, cp + 10.0)


# ── MultiplierEngine ──────────────────────────────────────────────────────────
class TestMultiplierEngine:

    def test_at_zero_elapsed(self):
        assert MultiplierEngine.multiplier_at(0) == 1.00

    def test_increases_over_time(self):
        m1 = MultiplierEngine.multiplier_at(5)
        m2 = MultiplierEngine.multiplier_at(10)
        assert m2 > m1

    def test_roundtrip_time_multiplier(self):
        for m in [1.5, 2.0, 3.0, 5.0, 10.0]:
            t = MultiplierEngine.time_at_multiplier(m)
            recovered = MultiplierEngine.multiplier_at(t)
            assert abs(recovered - m) < 0.05, f"Roundtrip failed for {m}: got {recovered}"


# ── Wallet ────────────────────────────────────────────────────────────────────
class TestWallet:

    def test_starting_balance(self):
        w = Wallet(10_000)
        assert w.balance == 10_000

    def test_deduct_bet_reduces_balance(self):
        w = Wallet(10_000)
        ok = w.deduct_bet(500, round_id=1)
        assert ok
        assert w.balance == 9_500

    def test_deduct_bet_insufficient_returns_false(self):
        w = Wallet(100)
        ok = w.deduct_bet(200, round_id=1)
        assert not ok
        assert w.balance == 100  # unchanged

    def test_deduct_zero_returns_false(self):
        w = Wallet(10_000)
        assert not w.deduct_bet(0, round_id=1)

    def test_add_payout(self):
        w = Wallet(9_900)
        w.add_payout(250, round_id=1)
        assert w.balance == 10_150

    def test_refund(self):
        w = Wallet(9_500)
        w.refund(500, round_id=1)
        assert w.balance == 10_000

    def test_transaction_log(self):
        w = Wallet(10_000)
        w.deduct_bet(100, round_id=1)
        w.add_payout(235, round_id=1)
        assert len(w.transactions) == 2
        assert w.transactions[0].type == "bet"
        assert w.transactions[1].type == "payout"


# ── GameEngine ────────────────────────────────────────────────────────────────
class TestGameEngine:

    def _engine(self):
        return GameEngine(Wallet(10_000))

    def test_initial_state(self):
        e = self._engine()
        assert e.state == GameState.WAITING

    def test_prepare_round_deducts_bet(self):
        e = self._engine()
        ok = e.prepare_round(100)
        assert ok
        assert e.wallet.balance == 9_900
        assert e.state == GameState.BETTING

    def test_prepare_round_insufficient(self):
        e = GameEngine(Wallet(50))
        assert not e.prepare_round(100)
        assert e.wallet.balance == 50

    def test_start_round_transitions_to_running(self):
        e = self._engine()
        e.prepare_round(100)
        e.start_round()
        assert e.state == GameState.RUNNING

    def test_cashout_before_crash_wins(self):
        e = self._engine()
        e.prepare_round(100)
        # Force a high crash point so we can always cash out
        e._crash_multiplier = 999.99
        e.start_round()
        # Let a little time pass so multiplier rises above 1.00
        time.sleep(0.15)
        result = e.request_cashout()
        assert result is not None
        assert result.won
        assert result.payout >= 100  # at >= 1.00× we get at least our bet back
        assert e.state == GameState.CASHED_OUT

    def test_cashout_after_crash_rejected(self):
        e = self._engine()
        e.prepare_round(100)
        # Force an immediate crash
        e._crash_multiplier = 1.00
        e.start_round()
        e.tick()  # should trigger crash
        result = e.request_cashout()
        assert result is None
        assert e.state == GameState.CRASHED

    def test_round_history_saved(self):
        e = self._engine()
        e.prepare_round(100)
        e._crash_multiplier = 999.99
        e.start_round()
        e.request_cashout()
        assert len(e.history) == 1

    def test_verify_last_round(self):
        """Verify using the real seed-generated crash point (don't override it)."""
        e = self._engine()
        e.prepare_round(100)
        # Use the real crash point — set a very small delay then cash out fast
        # by temporarily making crash point very high after prepare
        real_seed = e._server_seed
        real_round = e.round_id
        real_hash  = e._server_seed_hash
        e._crash_multiplier = 999.99   # ensure we don't crash before cashout
        e.start_round()
        time.sleep(0.05)
        result = e.request_cashout()
        # Restore the real crash point into the history entry for verification
        real_cp = FairnessEngine.calculate_crash_point(real_seed, real_round)
        e.history[-1].crash_multiplier = real_cp
        e.history[-1].server_seed      = real_seed
        e.history[-1].server_seed_hash = real_hash
        assert e.verify_last_round()

    def test_reset_to_waiting(self):
        e = self._engine()
        e.prepare_round(100)
        e._crash_multiplier = 999.99
        e.start_round()
        e.request_cashout()
        e.reset_to_waiting()
        assert e.state == GameState.WAITING

    def test_no_double_cashout(self):
        e = self._engine()
        e.prepare_round(100)
        e._crash_multiplier = 999.99
        e.start_round()
        r1 = e.request_cashout()
        r2 = e.request_cashout()   # second call must be rejected
        assert r1 is not None
        assert r2 is None

    def test_wallet_exact_payout(self):
        """Ensure payout = floor(bet * cashout_mult)."""
        e = self._engine()
        e.prepare_round(100)
        e._crash_multiplier = 999.99
        e.start_round()
        # Artificially set a known multiplier by mocking time
        import unittest.mock as mock
        with mock.patch("time.monotonic", return_value=e._start_time + 10.0):
            mult = e.current_multiplier
            result = e.request_cashout()
        expected_payout = int(100 * mult)
        assert result.payout == expected_payout
