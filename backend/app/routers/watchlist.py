from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.engine.delta import compute_delta
from app.engine.rationale import generate_rationale
from app.models import MarketBaseline, UserCheckpoint, Watchlist
from app.schemas import (
    AttentionTier,
    CatchUpItem,
    CatchUpResponse,
    CheckpointBulkWrite,
    CheckpointWriteResponse,
    FeedStatus,
    SymbolSearchResult,
    TickQuality,
    WatchlistItemAdd,
    WatchlistItemResponse,
    WatchlistResponse,
    WatchlistRow,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_feed(request: Request):
    """Retrieve the active feed from app state or raise 503."""
    feed = getattr(request.app.state, "feed", None)
    if feed is None:
        raise HTTPException(status_code=503, detail="Market feed not available.")
    return feed


def _tier_sort_key(item: CatchUpItem) -> tuple:
    """Sort key: HIGH before MODERATE, then by Z-score descending."""
    tier_rank = {"HIGH": 0, "MODERATE": 1, "NORMAL": 2}
    return (tier_rank.get(item.attention_tier.value, 99), -item.z_score)


async def _get_watchlist_symbols(user_id: str, db: AsyncSession) -> list[str]:
    """Return all symbols on a user's watchlist."""
    result = await db.execute(
        select(Watchlist.symbol).where(Watchlist.user_id == user_id)
    )
    return [row[0] for row in result.fetchall()]


async def _get_checkpoints(
    user_id: str, symbols: list[str], db: AsyncSession
) -> dict[str, UserCheckpoint]:
    """Fetch checkpoints for a set of symbols, keyed by symbol."""
    if not symbols:
        return {}
    result = await db.execute(
        select(UserCheckpoint).where(
            UserCheckpoint.user_id == user_id,
            UserCheckpoint.symbol.in_(symbols),
        )
    )
    return {row.symbol: row for row in result.scalars().all()}


async def _get_baselines(
    symbols: list[str], db: AsyncSession
) -> dict[str, MarketBaseline]:
    """Fetch market baselines for a set of symbols, keyed by symbol."""
    if not symbols:
        return {}
    result = await db.execute(
        select(MarketBaseline).where(MarketBaseline.symbol.in_(symbols))
    )
    return {row.symbol: row for row in result.scalars().all()}


# ---------------------------------------------------------------------------
# GET /api/watchlist
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=WatchlistResponse,
    summary="Get full watchlist with delta analysis",
    description=(
        "Returns all symbols on the user's watchlist with live market data, "
        "delta vs checkpoint, Z-score, volume ratio, and attention tier. "
        "Feed freshness metadata is included in both the response body and "
        "X-Feed-Status / X-Feed-Lag-Ms response headers."
    ),
)
async def get_watchlist(
    request: Request,
    response: Response,
    user_id: str = Query("trader_1", description="User identifier"),
    db: AsyncSession = Depends(get_db),
) -> WatchlistResponse:
    feed = _get_feed(request)

    symbols = await _get_watchlist_symbols(user_id, db)
    checkpoints, baselines = await asyncio.gather(
        _get_checkpoints(user_id, symbols, db),
        _get_baselines(symbols, db),
    )

    # Edge Case Resilience: Auto-bootstrap checkpoints for new users or newly added symbols
    missing_symbols = [s for s in symbols if s not in checkpoints]
    if missing_symbols:
        now = datetime.now(timezone.utc)
        for sym in missing_symbols:
            st = feed.get_latest_tick(sym)
            if st and st.tick_quality not in ("SUSPECT_TICK", "UNVERIFIED_DATA"):
                stmt = sqlite_upsert(UserCheckpoint).values(
                    user_id=user_id, symbol=sym, seen_price=st.price, seen_at=now
                ).on_conflict_do_nothing()
                await db.execute(stmt)
                checkpoints[sym] = UserCheckpoint(
                    user_id=user_id, symbol=sym, seen_price=st.price, seen_at=now
                )
        await db.commit()

    rows: list[WatchlistRow] = []
    worst_lag_ms = 0.0
    worst_feed_status = "LIVE"

    for symbol in symbols:
        state = feed.get_latest_tick(symbol)
        baseline = baselines.get(symbol)

        if state is None or baseline is None:
            # Symbol not in feed or no baseline — skip gracefully
            logger.warning("Skipping %s: state=%s baseline=%s", symbol, state, baseline)
            continue

        checkpoint = checkpoints.get(symbol)
        delta = compute_delta(state, checkpoint, baseline)
        delta.rationale = generate_rationale(delta)

        # Track worst feed health across all symbols
        if state.feed_lag_ms > worst_lag_ms:
            worst_lag_ms = state.feed_lag_ms
        if state.feed_status == "STALE" or worst_feed_status == "STALE":
            worst_feed_status = "STALE"
        elif state.feed_status == "DELAYED" or worst_feed_status == "DELAYED":
            worst_feed_status = "DELAYED"

        rows.append(WatchlistRow(
            symbol=delta.symbol,
            name=delta.name,
            sector=delta.sector,
            current_price=delta.current_price,
            day_open=delta.day_open,
            day_high=delta.day_high,
            day_low=delta.day_low,
            change_pct_day=round(delta.change_pct_day, 3),
            checkpoint_price=delta.checkpoint_price or None,
            seen_at=delta.seen_at,
            delta_price=round(delta.delta_price, 2),
            delta_pct=round(delta.delta_pct, 3),
            z_score=delta.z_score,
            volume_ratio=delta.volume_ratio,
            broke_day_high=delta.broke_day_high,
            broke_day_low=delta.broke_day_low,
            broke_52w_high=delta.broke_52w_high,
            broke_52w_low=delta.broke_52w_low,
            attention_tier=AttentionTier(delta.attention_tier),
            rationale=delta.rationale,
            signals_fired=delta.signals_fired,
            feed_status=FeedStatus(state.feed_status),
            feed_lag_ms=round(state.feed_lag_ms, 1),
            tick_quality=TickQuality(state.tick_quality),
            is_halted=state.is_halted,
            last_tick_time=state.last_tick_time,
        ))

    # Sort: HIGH first, then MODERATE, then NORMAL; within each tier by |delta_pct|
    rows.sort(key=lambda r: (
        {"HIGH": 0, "MODERATE": 1, "NORMAL": 2}.get(r.attention_tier.value, 99),
        -abs(r.delta_pct),
    ))

    high_count = sum(1 for r in rows if r.attention_tier == AttentionTier.HIGH)
    moderate_count = sum(1 for r in rows if r.attention_tier == AttentionTier.MODERATE)

    # Set feed freshness response headers
    response.headers["X-Feed-Status"] = worst_feed_status
    response.headers["X-Feed-Lag-Ms"] = str(round(worst_lag_ms, 1))

    return WatchlistResponse(
        user_id=user_id,
        items=rows,
        feed_status=FeedStatus(worst_feed_status),
        feed_lag_ms=round(worst_lag_ms, 1),
        total_count=len(rows),
        high_attention_count=high_count,
        moderate_attention_count=moderate_count,
        generated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# GET /api/watchlist/catch-up
# ---------------------------------------------------------------------------

@router.get(
    "/catch-up",
    response_model=CatchUpResponse,
    summary="Smart Catch-Up — only meaningful changes since last checkpoint",
    description=(
        "The core differentiator endpoint. Returns ONLY instruments with "
        "statistically significant changes (MODERATE or HIGH attention) since "
        "the user's last saved checkpoint. Items are categorised by priority tier "
        "and sorted by severity. SUSPECT_TICK items are excluded. "
        "An empty response means nothing important has changed."
    ),
)
async def get_catch_up(
    request: Request,
    user_id: str = Query("trader_1", description="User identifier"),
    db: AsyncSession = Depends(get_db),
) -> CatchUpResponse:
    feed = _get_feed(request)

    symbols = await _get_watchlist_symbols(user_id, db)
    checkpoints, baselines = await asyncio.gather(
        _get_checkpoints(user_id, symbols, db),
        _get_baselines(symbols, db),
    )

    # Edge Case Resilience: Auto-bootstrap checkpoints for new users
    missing_symbols = [s for s in symbols if s not in checkpoints]
    if missing_symbols:
        now = datetime.now(timezone.utc)
        for sym in missing_symbols:
            st = feed.get_latest_tick(sym)
            if st and st.tick_quality not in ("SUSPECT_TICK", "UNVERIFIED_DATA"):
                stmt = sqlite_upsert(UserCheckpoint).values(
                    user_id=user_id, symbol=sym, seen_price=st.price, seen_at=now
                ).on_conflict_do_nothing()
                await db.execute(stmt)
                checkpoints[sym] = UserCheckpoint(
                    user_id=user_id, symbol=sym, seen_price=st.price, seen_at=now
                )
        await db.commit()

    high_items: list[CatchUpItem] = []
    moderate_items: list[CatchUpItem] = []
    last_cp_at: Optional[datetime] = None

    for symbol in symbols:
        state = feed.get_latest_tick(symbol)
        baseline = baselines.get(symbol)
        if state is None or baseline is None:
            continue

        checkpoint = checkpoints.get(symbol)
        if checkpoint and (last_cp_at is None or checkpoint.seen_at < last_cp_at):
            last_cp_at = checkpoint.seen_at

        delta = compute_delta(state, checkpoint, baseline)

        # Skip NORMAL-tier items — they don't deserve attention
        if delta.attention_tier == "NORMAL":
            continue

        # Skip SUSPECT_TICK / UNVERIFIED_DATA — bad data shouldn't surface in catch-up
        if state.tick_quality in ("SUSPECT_TICK", "UNVERIFIED_DATA"):
            continue

        delta.rationale = generate_rationale(delta)

        item = CatchUpItem(
            symbol=delta.symbol,
            name=delta.name,
            sector=delta.sector,
            current_price=delta.current_price,
            checkpoint_price=delta.checkpoint_price or state.price,
            delta_pct=round(delta.delta_pct, 3),
            z_score=delta.z_score,
            volume_ratio=delta.volume_ratio,
            attention_tier=AttentionTier(delta.attention_tier),
            rationale=delta.rationale,
            signals_fired=delta.signals_fired,
            broke_52w_high=delta.broke_52w_high,
            broke_52w_low=delta.broke_52w_low,
            feed_status=FeedStatus(state.feed_status),
            tick_quality=TickQuality(state.tick_quality),
            seen_at=delta.seen_at,
        )

        if delta.attention_tier == "HIGH":
            high_items.append(item)
        else:
            moderate_items.append(item)

    # Sort by Z-score descending within each tier
    high_items.sort(key=lambda x: -x.z_score)
    moderate_items.sort(key=lambda x: -x.z_score)

    return CatchUpResponse(
        user_id=user_id,
        high_attention=high_items,
        moderate_attention=moderate_items,
        total_flagged=len(high_items) + len(moderate_items),
        last_checkpoint_at=last_cp_at,
        generated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# POST /api/watchlist/checkpoint
# ---------------------------------------------------------------------------

@router.post(
    "/checkpoint",
    response_model=CheckpointWriteResponse,
    summary="Mark current market state as seen (update checkpoint)",
    description=(
        "Upserts user_checkpoints for all (or specified) watchlist symbols. "
        "After this call, the catch-up panel will show no alerts until "
        "the market moves again. Safe to call from multiple tabs simultaneously "
        "— last writer wins (atomic SQLite UPSERT)."
    ),
)
async def update_checkpoint(
    request: Request,
    body: CheckpointBulkWrite,
    user_id: str = Query("trader_1", description="User identifier"),
    db: AsyncSession = Depends(get_db),
) -> CheckpointWriteResponse:
    feed = _get_feed(request)
    now = datetime.now(timezone.utc)

    # Determine target symbols
    if body.symbols:
        target_symbols = [s.upper() for s in body.symbols]
    else:
        target_symbols = await _get_watchlist_symbols(user_id, db)

    if not target_symbols:
        raise HTTPException(
            status_code=404,
            detail=f"No watchlist symbols found for user {user_id!r}.",
        )

    updated: list[str] = []

    for symbol in target_symbols:
        state = feed.get_latest_tick(symbol)
        if state is None:
            logger.warning("Checkpoint skip — %s not in feed", symbol)
            continue

        # Suppress checkpointing corrupt/suspect prices
        if state.tick_quality in ("SUSPECT_TICK", "UNVERIFIED_DATA"):
            logger.warning(
                "Checkpoint suppressed for %s (%s price=%.2f)",
                symbol, state.tick_quality, state.price,
            )
            continue

        # Atomic UPSERT: if row exists, update; if not, insert
        stmt = sqlite_upsert(UserCheckpoint).values(
            user_id=user_id,
            symbol=symbol,
            seen_price=state.price,
            seen_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "symbol"],
            set_={"seen_price": state.price, "seen_at": now},
        )
        await db.execute(stmt)
        updated.append(symbol)

    await db.commit()
    logger.info("Checkpointed %d symbols for user %r", len(updated), user_id)

    return CheckpointWriteResponse(
        user_id=user_id,
        symbols_updated=updated,
        checkpointed_at=now,
        message=f"Checkpointed {len(updated)} symbol(s) as of {now.isoformat()}.",
    )


# ---------------------------------------------------------------------------
# POST /api/watchlist/items
# ---------------------------------------------------------------------------

@router.post(
    "/items",
    response_model=WatchlistItemResponse,
    status_code=201,
    summary="Add a symbol to the watchlist",
)
async def add_watchlist_item(
    request: Request,
    body: WatchlistItemAdd,
    user_id: str = Query("trader_1", description="User identifier"),
    db: AsyncSession = Depends(get_db),
) -> WatchlistItemResponse:
    feed = _get_feed(request)
    symbol = body.symbol.upper()

    # Validate: symbol must be tracked by the active feed
    if symbol not in feed.list_symbols():
        raise HTTPException(
            status_code=422,
            detail=(
                f"Symbol {symbol!r} is not tracked by the active feed. "
                f"Available: {sorted(feed.list_symbols())}"
            ),
        )

    # Upsert into watchlist (unique constraint on user_id + symbol)
    stmt = sqlite_upsert(Watchlist).values(
        user_id=user_id,
        symbol=symbol,
        created_at=datetime.now(timezone.utc),
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "symbol"])
    await db.execute(stmt)
    await db.commit()

    # Fetch the inserted/existing row
    result = await db.execute(
        select(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.symbol == symbol,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve watchlist item.")

    # Bootstrap checkpoint at current price so user doesn't see stale deltas
    state = feed.get_latest_tick(symbol)
    if state and state.tick_quality == "VALID":
        cp_stmt = sqlite_upsert(UserCheckpoint).values(
            user_id=user_id,
            symbol=symbol,
            seen_price=state.price,
            seen_at=datetime.now(timezone.utc),
        )
        cp_stmt = cp_stmt.on_conflict_do_nothing()
        await db.execute(cp_stmt)
        await db.commit()

    return WatchlistItemResponse(
        id=row.id,
        user_id=row.user_id,
        symbol=row.symbol,
        created_at=row.created_at,
    )


# ---------------------------------------------------------------------------
# DELETE /api/watchlist/items/{symbol}
# ---------------------------------------------------------------------------

@router.delete(
    "/items/{symbol}",
    status_code=204,
    summary="Remove a symbol from the watchlist",
)
async def remove_watchlist_item(
    symbol: str,
    user_id: str = Query("trader_1", description="User identifier"),
    db: AsyncSession = Depends(get_db),
) -> None:
    sym = symbol.upper()

    # Delete watchlist entry
    result = await db.execute(
        delete(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.symbol == sym,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Symbol {sym!r} not found in {user_id!r}'s watchlist.",
        )

    # Also clean up checkpoint for this symbol
    await db.execute(
        delete(UserCheckpoint).where(
            UserCheckpoint.user_id == user_id,
            UserCheckpoint.symbol == sym,
        )
    )
    await db.commit()
    logger.info("Removed %s from watchlist of %r", sym, user_id)


# ---------------------------------------------------------------------------
# GET /api/watchlist/symbols  (search / add modal)
# ---------------------------------------------------------------------------

@router.get(
    "/symbols",
    response_model=list[SymbolSearchResult],
    summary="List all available symbols (for search modal)",
    description="Returns all symbols tracked by the active feed with baseline info.",
)
async def list_available_symbols(
    request: Request,
    user_id: str = Query("trader_1", description="User identifier (to check current watchlist)"),
    db: AsyncSession = Depends(get_db),
) -> list[SymbolSearchResult]:
    feed = _get_feed(request)
    tracked = set(feed.list_symbols())

    # Get user's current watchlist to flag is_tracked
    user_symbols = set(await _get_watchlist_symbols(user_id, db))

    # Fetch baselines for all tracked symbols
    result = await db.execute(
        select(MarketBaseline).where(MarketBaseline.symbol.in_(tracked))
    )
    baselines = result.scalars().all()

    return sorted(
        [
            SymbolSearchResult(
                symbol=b.symbol,
                name=b.name,
                sector=b.sector or "",
                base_price=b.base_price,
                is_tracked=b.symbol in user_symbols,
            )
            for b in baselines
        ],
        key=lambda x: x.symbol,
    )
