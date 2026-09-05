from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.feed.base import MarketState
from app.models import MarketBaseline, UserCheckpoint


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
Z_HIGH: float = 2.0
Z_MODERATE: float = 1.0
VR_HIGH: float = 2.5        # Volume Ratio threshold for HIGH
VR_MODERATE: float = 1.5    # Volume Ratio threshold for MODERATE

# Minimum time window for σ scaling: 0.25 trading days (~1.6 hours)
# Prevents microsecond Brownian drift from triggering spurious breakouts
MIN_PERIOD_DAYS: float = 0.25

# Trading seconds per day (6.5 hours = 23,400s)
TRADING_SECONDS: int = 23_400


# ---------------------------------------------------------------------------
# DeltaResult
# ---------------------------------------------------------------------------

@dataclass
class DeltaResult:
    symbol: str
    name: str = ""
    sector: str = ""

    # Prices
    current_price: float = 0.0
    checkpoint_price: float = 0.0
    delta_price: float = 0.0        # Absolute ΔP
    delta_pct: float = 0.0          # % change since checkpoint

    # Day context
    day_open: float = 0.0
    day_high: float = 0.0
    day_low: float = 0.0
    change_pct_day: float = 0.0     # % change from open today

    # Statistical signals
    z_score: float = 0.0
    sigma_period: float = 0.0       # σ used in computation
    volume_ratio: float = 0.0

    # Structural breaks since checkpoint
    broke_day_high: bool = False
    broke_day_low: bool = False
    broke_52w_high: bool = False
    broke_52w_low: bool = False

    # Feed metadata
    feed_status: str = "LIVE"
    feed_lag_ms: float = 0.0
    tick_quality: str = "VALID"
    is_halted: bool = False
    last_tick_time: Optional[datetime] = None

    # Checkpoint metadata
    seen_at: Optional[datetime] = None

    # Output
    attention_tier: str = "NORMAL"
    rationale: str = ""

    # Signals that fired
    signals_fired: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_delta(
    state: MarketState,
    checkpoint: Optional[UserCheckpoint],
    baseline: MarketBaseline,
) -> DeltaResult:

    result = DeltaResult(
        symbol=state.symbol,
        name=baseline.name,
        sector=baseline.sector or "",
        current_price=state.price,
        day_open=state.day_open,
        day_high=state.day_high,
        day_low=state.day_low,
        change_pct_day=state.change_pct_day,
        feed_status=state.feed_status,
        feed_lag_ms=state.feed_lag_ms,
        tick_quality=state.tick_quality,
        is_halted=state.is_halted,
        last_tick_time=state.last_tick_time,
    )

    # No checkpoint yet — bootstrap state
    if checkpoint is None or checkpoint.seen_price <= 0:
        result.attention_tier = "NORMAL"
        result.rationale = "No previous checkpoint — monitoring started."
        return result

    result.checkpoint_price = checkpoint.seen_price
    result.seen_at = checkpoint.seen_at

    # Halted symbols
    if state.is_halted:
        result.attention_tier = "NORMAL"
        result.rationale = "Symbol is currently halted / in circuit-breaker state."
        result.signals_fired = ["HALTED"]
        return result

    # SUSPECT_TICK / UNVERIFIED_DATA — suppress all alerts
    if state.tick_quality in ("SUSPECT_TICK", "UNVERIFIED_DATA"):
        result.attention_tier = "NORMAL"
        result.rationale = (
            "Most recent tick was classified as UNVERIFIED_DATA / SUSPECT_TICK "
            "(instantaneous spike >15% without depth). "
            "Alert suppressed pending valid tick."
        )
        result.signals_fired = [state.tick_quality]
        return result

    # ──────────────────────────────────────────────────────────────────────
    # Signal 1: Price delta and Z-score
    # ──────────────────────────────────────────────────────────────────────
    delta_price = state.price - checkpoint.seen_price
    delta_pct = (
        (delta_price / checkpoint.seen_price * 100.0)
        if checkpoint.seen_price != 0
        else 0.0
    )
    result.delta_price = delta_price
    result.delta_pct = delta_pct

    # If price delta is negligible (<0.50%), classify as NORMAL immediately
    if abs(delta_pct) < 0.50:
        result.z_score = 0.0
        result.volume_ratio = 1.0
        result.attention_tier = "NORMAL"
        result.rationale = "Price is within normal variance and unchanged since your last check."
        return result

    # Time since checkpoint (in trading days)
    now = datetime.now(timezone.utc)
    seen_at = checkpoint.seen_at
    if seen_at.tzinfo is None:
        seen_at = seen_at.replace(tzinfo=timezone.utc)
    elapsed_seconds = max((now - seen_at).total_seconds(), 0.0)
    elapsed_days = max(elapsed_seconds / 86_400.0, MIN_PERIOD_DAYS)

    # σ scaled to elapsed time
    sigma_annual = baseline.sigma_price
    sigma_daily = baseline.base_price * sigma_annual / math.sqrt(252.0)
    sigma_period = sigma_daily * math.sqrt(elapsed_days)
    result.sigma_period = round(sigma_period, 4)

    z_score = abs(delta_price) / sigma_period if sigma_period > 0 else 0.0
    result.z_score = round(z_score, 3)

    # ──────────────────────────────────────────────────────────────────────
    # Signal 2: Volume Ratio
    # ──────────────────────────────────────────────────────────────────────
    session_fraction = min(elapsed_seconds / TRADING_SECONDS, 1.0) if elapsed_seconds < TRADING_SECONDS else 0.5
    session_fraction = max(session_fraction, 0.08)
    expected_vol = baseline.avg_volume * session_fraction
    volume_ratio = (state.volume / expected_vol) if expected_vol > 0 else 0.0
    result.volume_ratio = round(volume_ratio, 3)

    # ──────────────────────────────────────────────────────────────────────
    # Signal 3: Structural Breaks SINCE checkpoint
    # ──────────────────────────────────────────────────────────────────────
    DAY_BREAK_BUFFER = 0.001
    # Day High touch occurred since checkpoint
    if (
        state.day_high > 0 
        and state.price >= state.day_high * (1 - DAY_BREAK_BUFFER)
        and checkpoint.seen_price < state.day_high * (1 - DAY_BREAK_BUFFER)
        and delta_pct >= 0.75
    ):
        result.broke_day_high = True

    # Day Low touch occurred since checkpoint
    if (
        state.day_low > 0 
        and state.price <= state.day_low * (1 + DAY_BREAK_BUFFER)
        and checkpoint.seen_price > state.day_low * (1 + DAY_BREAK_BUFFER)
        and delta_pct <= -0.75
    ):
        result.broke_day_low = True

    # 52-week structural breakout occurred since checkpoint
    if (
        baseline.week52_high > 0 
        and state.price >= baseline.week52_high * 0.99
        and checkpoint.seen_price < baseline.week52_high * 0.99
        and delta_pct >= 0.75
    ):
        result.broke_52w_high = True

    if (
        baseline.week52_low > 0 
        and state.price <= baseline.week52_low * 1.01
        and checkpoint.seen_price > baseline.week52_low * 1.01
        and delta_pct <= -0.75
    ):
        result.broke_52w_low = True

    # ──────────────────────────────────────────────────────────────────────
    # Tier classification
    # ──────────────────────────────────────────────────────────────────────
    signals: list[str] = []

    if z_score >= Z_HIGH and abs(delta_pct) >= 1.25:
        signals.append(f"PRICE_BREAKOUT_Z{z_score:.1f}")
    elif z_score >= Z_MODERATE and abs(delta_pct) >= 0.75:
        signals.append(f"PRICE_MOVE_Z{z_score:.1f}")

    if volume_ratio >= VR_HIGH and abs(delta_pct) >= 0.60:
        signals.append(f"VOLUME_SURGE_{volume_ratio:.1f}x")
    elif volume_ratio >= VR_MODERATE and abs(delta_pct) >= 0.50:
        signals.append(f"VOLUME_ELEVATED_{volume_ratio:.1f}x")

    if result.broke_52w_high:
        signals.append("52W_HIGH_BREACH")
    if result.broke_52w_low:
        signals.append("52W_LOW_BREACH")
    if result.broke_day_high:
        signals.append("DAY_HIGH_TOUCH")
    if result.broke_day_low:
        signals.append("DAY_LOW_TOUCH")

    result.signals_fired = signals

    # HIGH conditions
    if (
        (z_score >= Z_HIGH and abs(delta_pct) >= 1.25)
        or (volume_ratio >= VR_HIGH and abs(delta_pct) >= 0.60)
        or result.broke_52w_high
        or result.broke_52w_low
    ):
        result.attention_tier = "HIGH"

    # MODERATE conditions
    elif (
        (z_score >= Z_MODERATE and abs(delta_pct) >= 0.75)
        or (volume_ratio >= VR_MODERATE and abs(delta_pct) >= 0.50)
        or result.broke_day_high
        or result.broke_day_low
    ):
        result.attention_tier = "MODERATE"

    else:
        result.attention_tier = "NORMAL"

    return result
