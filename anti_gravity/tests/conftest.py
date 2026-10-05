"""
conftest.py for backend tests.
Ensures _active_round_internal and RateLimiter are always reset between tests.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.rate_limiter import RateLimiter
from backend.services.game_service import _active_round_internal


@pytest.fixture(autouse=True)
def reset_test_state():
    """Reset rate limiter and round state before each test."""
    RateLimiter.clear()
    _active_round_internal.clear()
    yield
    RateLimiter.clear()
    _active_round_internal.clear()

