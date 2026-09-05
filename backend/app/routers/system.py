from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.schemas import FeedHealthResponse, FeedStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get(
    "/feed-health",
    response_model=FeedHealthResponse,
    summary="Report overall feed health and latency",
    description=(
        "Aggregates per-symbol feed metadata into a single system-level "
        "health snapshot. The response `feed_status` reflects the worst "
        "case across all tracked symbols:\n\n"
        "- **LIVE**: all symbols updated within the last 2 seconds\n"
        "- **DELAYED**: at least one symbol lagging 2–15 seconds\n"
        "- **STALE**: at least one symbol lagging > 15 seconds\n\n"
        "Also reports which symbols are halted or had suspect ticks."
    ),
)
async def get_feed_health(request: Request) -> FeedHealthResponse:
    """
    Aggregate feed health across all tracked symbols.

    Iterates all live ticks, computes per-symbol lag, and rolls up
    to a single worst-case status + lag value for the dashboard pill.
    """
    feed = getattr(request.app.state, "feed", None)
    if feed is None:
        raise HTTPException(status_code=503, detail="Market feed not running.")

    all_ticks = feed.get_all_ticks()   # Also refreshes lag on each state

    if not all_ticks:
        return FeedHealthResponse(
            feed_status=FeedStatus.STALE,
            feed_lag_ms=999_999.0,
            active_symbols=0,
            halted_symbols=[],
            suspect_tick_symbols=[],
            last_updated=datetime.now(timezone.utc),
        )

    worst_lag_ms = 0.0
    worst_status = "LIVE"
    halted: list[str] = []
    suspect: list[str] = []

    STATUS_RANK = {"LIVE": 0, "DELAYED": 1, "STALE": 2}

    for symbol, state in all_ticks.items():
        # Accumulate worst lag
        if state.feed_lag_ms > worst_lag_ms:
            worst_lag_ms = state.feed_lag_ms

        # Accumulate worst status
        if STATUS_RANK.get(state.feed_status, 0) > STATUS_RANK.get(worst_status, 0):
            worst_status = state.feed_status

        # Collect flagged symbols
        if state.is_halted:
            halted.append(symbol)
        if state.tick_quality == "SUSPECT_TICK":
            suspect.append(symbol)

    return FeedHealthResponse(
        feed_status=FeedStatus(worst_status),
        feed_lag_ms=round(worst_lag_ms, 1),
        active_symbols=len(all_ticks),
        halted_symbols=sorted(halted),
        suspect_tick_symbols=sorted(suspect),
        last_updated=datetime.now(timezone.utc),
    )
