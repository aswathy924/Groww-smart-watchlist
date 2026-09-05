import math
from datetime import datetime, timezone, timedelta
import pytest

from app.engine.delta import compute_delta, MIN_PERIOD_DAYS
from app.engine.rationale import generate_rationale
from app.feed.base import MarketState
from app.models import MarketBaseline, UserCheckpoint

def create_mock_baseline(
    symbol="RELIANCE",
    base_price=3000.0,
    sigma_price=0.22,
    avg_volume=8_500_000,
    week52_low=2200.0,
    week52_high=3200.0,
) -> MarketBaseline:
    return MarketBaseline(
        symbol=symbol,
        name="Reliance Industries Ltd",
        sector="Energy",
        base_price=base_price,
        sigma_price=sigma_price,
        avg_volume=avg_volume,
        day_open=base_price,
        day_high=base_price,
        day_low=base_price,
        week52_low=week52_low,
        week52_high=week52_high,
    )

def test_delta_normal_price_noise():
    """Test that micro-fluctuations (<0.50%) return NORMAL attention tier with 0 Z-score."""
    baseline = create_mock_baseline()
    checkpoint = UserCheckpoint(
        user_id="u1",
        symbol="RELIANCE",
        seen_price=3000.0,
        seen_at=datetime.now(timezone.utc) - timedelta(minutes=15),
    )
    # Price moved +0.2% (noise)
    state = MarketState(
        symbol="RELIANCE",
        price=3006.0,
        day_open=3000.0,
        day_high=3010.0,
        day_low=2995.0,
        volume=1_000_000,
    )

    result = compute_delta(state, checkpoint, baseline)
    assert result.attention_tier == "NORMAL"
    assert result.z_score == 0.0
    assert abs(result.delta_pct - 0.20) < 0.01
    rationale = generate_rationale(result)
    assert "normal range" in rationale.lower() or "normal variance" in rationale.lower()

def test_delta_statistical_breakout_high_zscore():
    """Test that sudden +5% move triggers HIGH attention tier with Z-score > 2.0."""
    baseline = create_mock_baseline()
    checkpoint = UserCheckpoint(
        user_id="u1",
        symbol="RELIANCE",
        seen_price=3000.0,
        seen_at=datetime.now(timezone.utc) - timedelta(minutes=30),
    )
    # Price moved +5% to 3150.0
    state = MarketState(
        symbol="RELIANCE",
        price=3150.0,
        day_open=3000.0,
        day_high=3150.0,
        day_low=2990.0,
        volume=1_500_000,
    )

    result = compute_delta(state, checkpoint, baseline)
    assert result.attention_tier == "HIGH"
    assert result.z_score >= 2.0
    assert result.delta_pct >= 4.9
    rationale = generate_rationale(result)
    assert "breakout" in rationale.lower() or "z=" in rationale.lower()

def test_delta_volume_surge_elevated_attention():
    """Test that volume ratio > 2.5x with >0.6% price move elevates attention to HIGH."""
    baseline = create_mock_baseline()
    checkpoint = UserCheckpoint(
        user_id="u1",
        symbol="RELIANCE",
        seen_price=3000.0,
        seen_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    # Price moved +0.9% with massive 4x session volume
    state = MarketState(
        symbol="RELIANCE",
        price=3027.0,
        day_open=3000.0,
        day_high=3030.0,
        day_low=2995.0,
        volume=5_500_000, # Large volume
    )

    result = compute_delta(state, checkpoint, baseline)
    assert result.volume_ratio >= 2.5
    assert result.attention_tier == "HIGH"
    rationale = generate_rationale(result)
    assert "volume" in rationale.lower()

def test_delta_52w_high_structural_breakout():
    """Test that crossing 52-week high since checkpoint flags 52W_HIGH_BREACH and HIGH tier."""
    baseline = create_mock_baseline(week52_high=3200.0)
    checkpoint = UserCheckpoint(
        user_id="u1",
        symbol="RELIANCE",
        seen_price=3150.0, # Below 52w high threshold
        seen_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    # Crosses 52w high to 3210.0
    state = MarketState(
        symbol="RELIANCE",
        price=3210.0,
        day_open=3140.0,
        day_high=3210.0,
        day_low=3130.0,
        volume=3_000_000,
    )

    result = compute_delta(state, checkpoint, baseline)
    assert result.broke_52w_high is True
    assert result.attention_tier == "HIGH"
    assert "52W_HIGH_BREACH" in result.signals_fired

def test_delta_bootstrap_for_new_user():
    """Test that missing checkpoint returns clean NORMAL tier state."""
    baseline = create_mock_baseline()
    state = MarketState(symbol="RELIANCE", price=3000.0)

    result = compute_delta(state, None, baseline)
    assert result.attention_tier == "NORMAL"
    assert result.checkpoint_price == 0.0
