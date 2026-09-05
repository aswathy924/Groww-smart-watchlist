from __future__ import annotations

from app.engine.delta import DeltaResult


def generate_rationale(result: DeltaResult) -> str:
    """
    Produce a human-readable explanation of why a symbol received its
    attention tier, based on the signals in DeltaResult.
    """

    # Special states — short-circuit 
    if result.is_halted:
        return "Trading is halted on this symbol (circuit breaker or exchange action)."

    if result.tick_quality == "SUSPECT_TICK":
        return (
            "The most recent price tick was flagged as SUSPECT_TICK — "
            "an instantaneous spike of >15% with no supporting volume depth. "
            "This alert has been suppressed. Waiting for a clean tick."
        )

    if not result.signals_fired or result.attention_tier == "NORMAL":
        if result.checkpoint_price == 0:
            return "Monitoring started — no previous checkpoint to compare against."
        return (
            f"Price is ₹{result.delta_pct:+.2f}% from your last checkpoint "
            f"(₹{result.checkpoint_price:,.2f} → ₹{result.current_price:,.2f}). "
            f"Z-score: {result.z_score:.2f}σ. All signals within normal range."
        )

    parts: list[str] = []

    # Price / Z-score sentence 
    if result.z_score >= 2.0:
        parts.append(
            f"Price has moved {result.delta_pct:+.2f}% "
            f"(₹{result.checkpoint_price:,.2f} → ₹{result.current_price:,.2f}), "
            f"which is {result.z_score:.1f}σ outside the expected range "
            f"— a statistically significant breakout."
        )
    elif result.z_score >= 1.0:
        parts.append(
            f"Price has moved {result.delta_pct:+.2f}% "
            f"(₹{result.checkpoint_price:,.2f} → ₹{result.current_price:,.2f}), "
            f"a notable {result.z_score:.1f}σ deviation from your checkpoint."
        )
    elif result.delta_pct != 0:
        parts.append(
            f"Price has moved {result.delta_pct:+.2f}% "
            f"from your last checkpoint (₹{result.checkpoint_price:,.2f})."
        )

    # Volume sentence 
    if result.volume_ratio >= 2.5:
        parts.append(
            f"Volume is {result.volume_ratio:.1f}x the session baseline — "
            f"an abnormal surge indicating strong institutional interest."
        )
    elif result.volume_ratio >= 1.5:
        parts.append(
            f"Volume is {result.volume_ratio:.1f}x the session baseline — "
            f"elevated but not yet at surge levels."
        )

    # Structural break sentences 
    if result.broke_52w_high:
        parts.append(
            f"Price is testing the 52-week high — "
            f"a major structural resistance breakout."
        )
    if result.broke_52w_low:
        parts.append(
            f"Price is testing the 52-week low — "
            f"a critical support level breach."
        )
    if result.broke_day_high and not result.broke_52w_high:
        parts.append(
            f"Price has touched the intraday session high (₹{result.day_high:,.2f})."
        )
    if result.broke_day_low and not result.broke_52w_low:
        parts.append(
            f"Price has touched the intraday session low (₹{result.day_low:,.2f})."
        )

    # Time context (append to last sentence) 
    if result.seen_at:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        seen_at = result.seen_at
        if seen_at.tzinfo is None:
            seen_at = seen_at.replace(tzinfo=timezone.utc)
        elapsed_seconds = (now - seen_at).total_seconds()
        if elapsed_seconds < 120:
            time_str = f"{int(elapsed_seconds)}s ago"
        elif elapsed_seconds < 3600:
            time_str = f"{int(elapsed_seconds / 60)}m ago"
        else:
            time_str = f"{elapsed_seconds / 3600:.1f}h ago"
        parts.append(f"Last checked {time_str}.")

    return " ".join(parts) if parts else "Attention signal detected."
