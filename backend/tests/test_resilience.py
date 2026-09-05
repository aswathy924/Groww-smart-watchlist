import asyncio
from datetime import datetime, timezone, timedelta
import numpy as np
import pytest

from app.engine.delta import compute_delta
from app.feed.base import MarketState
from app.feed.hybrid_feed import HybridFeed
from app.models import MarketBaseline, UserCheckpoint

def create_mock_baseline(symbol="RELIANCE", base_price=3000.0) -> MarketBaseline:
    return MarketBaseline(
        symbol=symbol,
        name="Reliance Industries Ltd",
        sector="Energy",
        base_price=base_price,
        sigma_price=0.22,
        avg_volume=8_500_000,
        day_open=base_price,
        day_high=base_price,
        day_low=base_price,
        week52_low=2200.0,
        week52_high=3200.0,
    )

def test_out_of_order_tick_rejected():
    """Test that ticks with timestamp <= last_tick_time are rejected without mutating state."""
    feed = HybridFeed()
    feed._seed_initial_state()
    state = feed.get_latest_tick("RELIANCE")
    assert state is not None

    initial_price = state.price
    now = datetime.now(timezone.utc)
    state.last_tick_time = now

    # Attempt to process a stale tick with timestamp 5 seconds in the past
    stale_time = now - timedelta(seconds=5)
    rng = np.random.default_rng()
    feed._process_tick("RELIANCE", state, stale_time, rng)

    # State should remain unchanged
    assert state.price == initial_price
    assert state.last_tick_time == now

def test_bad_tick_tagged_and_suppressed():
    """Test that a +20% bad tick without depth is tagged UNVERIFIED_DATA and suppressed from alerts."""
    baseline = create_mock_baseline()
    checkpoint = UserCheckpoint(
        user_id="u1",
        symbol="RELIANCE",
        seen_price=3000.0,
        seen_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    # Corrupt tick
    state = MarketState(
        symbol="RELIANCE",
        price=3600.0, # +20% jump
        last_valid_price=3000.0,
        tick_quality="UNVERIFIED_DATA",
    )

    result = compute_delta(state, checkpoint, baseline)
    assert result.attention_tier == "NORMAL"
    assert "UNVERIFIED_DATA" in result.signals_fired
    assert "suppressed" in result.rationale.lower()

def test_bad_tick_self_healing_restoration():
    """Test that subsequent valid tick restores price to last_valid_price and resets quality to VALID."""
    feed = HybridFeed()
    feed._seed_initial_state()
    state = feed.get_latest_tick("RELIANCE")
    assert state is not None

    true_price = state.price
    feed.inject_bad_tick("RELIANCE")

    # Tick 1: Bad tick applied
    t1 = datetime.now(timezone.utc) + timedelta(seconds=1)
    rng = np.random.default_rng()
    feed._process_tick("RELIANCE", state, t1, rng)

    assert state.tick_quality == "UNVERIFIED_DATA"
    assert state.price > true_price * 1.15
    assert state.last_valid_price == true_price

    # Tick 2: Next tick should self-heal and restore true price
    t2 = t1 + timedelta(seconds=1)
    feed._process_tick("RELIANCE", state, t2, rng)

    assert state.tick_quality == "VALID"
    assert abs(state.price - true_price) < 5.0 # Restored close to true price

def test_trading_halt_suppresses_alerts():
    """Test that trading halt pauses price moves and classifies tier as NORMAL with HALTED signal."""
    baseline = create_mock_baseline()
    checkpoint = UserCheckpoint(
        user_id="u1",
        symbol="RELIANCE",
        seen_price=3000.0,
        seen_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    state = MarketState(
        symbol="RELIANCE",
        price=3180.0,
        is_halted=True,
    )

    result = compute_delta(state, checkpoint, baseline)
    assert result.attention_tier == "NORMAL"
    assert "HALTED" in result.signals_fired
    assert "halted" in result.rationale.lower()
