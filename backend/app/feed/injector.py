from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.feed.base import BaseMarketFeed
from app.schemas import AnomalyType

logger = logging.getLogger(__name__)


class FeedInjector:
    """
    Routes anomaly injection commands to the active feed instance.

    """

    def __init__(self, feed: BaseMarketFeed) -> None:
        self._feed = feed

    async def inject(
        self,
        symbol: str,
        anomaly_type: AnomalyType,
        duration_seconds: Optional[int] = None,
    ) -> str:
        """
        Route an injection request to the appropriate handler.

        """
        sym = symbol.upper()

        if anomaly_type == AnomalyType.PRICE_SURGE:
            return self._inject_price_surge(sym)

        elif anomaly_type == AnomalyType.VOLUME_EXPLOSION:
            return self._inject_volume_explosion(sym)

        elif anomaly_type == AnomalyType.BAD_TICK:
            return self._inject_bad_tick(sym)

        elif anomaly_type == AnomalyType.FEED_DELAY:
            duration = duration_seconds or 10
            return await self._inject_feed_delay(duration)

        elif anomaly_type == AnomalyType.TRADING_HALT:
            return self._inject_trading_halt(sym)

        elif anomaly_type == AnomalyType.RESUME_TRADING:
            return self._inject_resume_trading(sym)

        else:
            raise ValueError(f"Unknown anomaly_type: {anomaly_type!r}")

    # ------------------------------------------------------------------
    # Individual injection handlers
    # ------------------------------------------------------------------

    def _inject_price_surge(self, symbol: str) -> str:
        """
        Apply a +6% immediate price move.

        """
        from app.feed.hybrid_feed import HybridFeed
        if isinstance(self._feed, HybridFeed):
            self._feed.inject_price_surge(symbol)
        else:
            # Best-effort for LiveFeed: directly mutate state
            state = self._feed.get_latest_tick(symbol)
            if state is None:
                raise ValueError(f"Symbol {symbol!r} not tracked by active feed")
            state.price = round(state.price * 1.06, 2)
            state.day_high = max(state.day_high, state.price)

        msg = (
            f"Price surge injected for {symbol}: +6% immediate move. "
            f"Expect HIGH attention alert if Z-score > 2.0σ."
        )
        logger.info(msg)
        return msg

    def _inject_volume_explosion(self, symbol: str, multiplier: float = 4.0) -> str:
        """
        Queue a 4x volume multiplier on the next tick.

        """
        from app.feed.hybrid_feed import HybridFeed
        if isinstance(self._feed, HybridFeed):
            self._feed.inject_volume_explosion(symbol, multiplier)
        else:
            state = self._feed.get_latest_tick(symbol)
            if state is None:
                raise ValueError(f"Symbol {symbol!r} not tracked by active feed")
            # For LiveFeed, inject a volume spike directly
            state.volume *= multiplier

        msg = (
            f"Volume explosion queued for {symbol}: {multiplier:.1f}x multiplier "
            f"on next tick. Volume Ratio will exceed 2.5x threshold."
        )
        logger.info(msg)
        return msg

    def _inject_bad_tick(self, symbol: str) -> str:
        """
        Queue a +20% SUSPECT_TICK spike on the next tick.

        """
        from app.feed.hybrid_feed import HybridFeed
        if isinstance(self._feed, HybridFeed):
            self._feed.inject_bad_tick(symbol)
        else:
            state = self._feed.get_latest_tick(symbol)
            if state is None:
                raise ValueError(f"Symbol {symbol!r} not tracked by active feed")
            # Apply directly for LiveFeed
            state.price = round(state.price * 1.20, 2)
            state.tick_quality = "SUSPECT_TICK"

        msg = (
            f"Bad tick queued for {symbol}: +20% spike will be tagged SUSPECT_TICK "
            f"and suppressed from user alerts."
        )
        logger.info(msg)
        return msg

    async def _inject_feed_delay(self, duration_seconds: int) -> str:
        """
        Pause the tick feed for N seconds across ALL symbols.

        """
        from app.feed.hybrid_feed import HybridFeed
        if isinstance(self._feed, HybridFeed):
            # Spawn as a background task — don't await it here
            asyncio.create_task(
                self._feed.inject_feed_delay(duration_seconds),
                name=f"feed-delay-{duration_seconds}s",
            )
        else:
            logger.warning(
                "feed_delay injection not fully supported by LiveFeed; "
                "marking all symbols STALE for %ds", duration_seconds
            )
            # Best-effort: mark all symbols as stale directly
            from datetime import timedelta
            from datetime import timezone
            from datetime import datetime
            stale_time = datetime.now(timezone.utc) - timedelta(seconds=duration_seconds + 5)
            for state in self._feed.get_all_ticks().values():
                state.last_tick_time = stale_time
                state.update_lag()

        msg = (
            f"Feed delay injected: all tick emission paused for {duration_seconds}s. "
            f"Feed will transition LIVE → DELAYED → STALE during the pause."
        )
        logger.info(msg)
        return msg

    def _inject_trading_halt(self, symbol: str) -> str:
        """Halt trading for the target symbol."""
        from app.feed.hybrid_feed import HybridFeed
        if isinstance(self._feed, HybridFeed):
            self._feed.inject_trading_halt(symbol, duration_seconds=30)
        else:
            state = self._feed.get_latest_tick(symbol)
            if state:
                state.is_halted = True
        msg = f"Circuit breaker triggered for {symbol}. Price updates paused for 30s cooling window (auto-resumes)."
        logger.info(msg)
        return msg

    def _inject_resume_trading(self, symbol: str) -> str:
        """Resume trading for the target symbol."""
        from app.feed.hybrid_feed import HybridFeed
        if isinstance(self._feed, HybridFeed):
            self._feed.inject_resume_trading(symbol)
        else:
            state = self._feed.get_latest_tick(symbol)
            if state:
                state.is_halted = False
        msg = f"Trading resumed for {symbol}. Normal tick flow restored."
        logger.info(msg)
        return msg
