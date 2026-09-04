from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict

from app.feed.base import BaseMarketFeed, MarketState

logger = logging.getLogger(__name__)

# Polling interval in seconds (respect Yahoo rate limits)
POLL_INTERVAL_SEC: float = 15.0

# NSE symbols → Yahoo Finance symbols (add .NS suffix)
NSE_TO_YAHOO: Dict[str, str] = {
    "RELIANCE":   "RELIANCE.NS",
    "TCS":        "TCS.NS",
    "INFY":       "INFY.NS",
    "HDFCBANK":   "HDFCBANK.NS",
    "ICICIBANK":  "ICICIBANK.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "WIPRO":      "WIPRO.NS",
    "MARUTI":     "MARUTI.NS",
    "LTIM":       "LTIM.NS",
    "AXISBANK":   "AXISBANK.NS",
    "SBIN":       "SBIN.NS",
    "NESTLEIND":  "NESTLEIND.NS",
    "ASIANPAINT": "ASIANPAINT.NS",
    "ONGC":       "ONGC.NS",
}


class LiveFeed(BaseMarketFeed):
    """
    yfinance-backed live market feed.
    """

    def __init__(self) -> None:
        super().__init__()
        self._poll_interval = POLL_INTERVAL_SEC

    async def start(self) -> None:
        """Seed state from an initial poll and start the polling loop."""
        try:
            import yfinance as yf
        except ImportError:
            raise RuntimeError(
                "yfinance is required for FEED_MODE=live. "
                "Install it with: pip install yfinance"
            )

        # Initialise state containers
        for symbol in NSE_TO_YAHOO:
            self._state[symbol] = MarketState(symbol=symbol)

        # Perform the first synchronous fetch to populate initial prices
        await self._poll_all_symbols()

        self._running = True
        self._task = asyncio.create_task(self._poll_loop(), name="live-feed-worker")
        logger.info("LiveFeed started: polling %d symbols every %.0fs",
                    len(self._state), self._poll_interval)

    async def stop(self) -> None:
        """Terminate the polling loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("LiveFeed stopped.")

    async def _poll_loop(self) -> None:
        """Main polling loop — runs every POLL_INTERVAL_SEC seconds."""
        while self._running:
            await asyncio.sleep(self._poll_interval)
            try:
                await self._poll_all_symbols()
            except Exception as exc:
                logger.error("LiveFeed poll error: %s", exc, exc_info=True)

    async def _poll_all_symbols(self) -> None:
        """
        Fetch the latest quotes for all symbols in one batched yfinance call.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._fetch_and_update)

    def _fetch_and_update(self) -> None:
        """
        Synchronous yfinance fetch (runs in thread pool).
        """
        try:
            import yfinance as yf
        except ImportError:
            logger.error("yfinance not installed. Cannot poll live data.")
            return

        yahoo_symbols = list(NSE_TO_YAHOO.values())
        now = datetime.now(timezone.utc)

        try:
            tickers = yf.Tickers(" ".join(yahoo_symbols))
        except Exception as exc:
            logger.error("yfinance Tickers init failed: %s", exc)
            return

        for nse_symbol, yahoo_symbol in NSE_TO_YAHOO.items():
            try:
                ticker = tickers.tickers.get(yahoo_symbol)
                if ticker is None:
                    continue

                info = ticker.fast_info

                price = float(info.last_price or 0)
                if price <= 0:
                    logger.debug("No price data for %s (%s)", nse_symbol, yahoo_symbol)
                    continue

                state = self._state.get(nse_symbol)
                if state is None:
                    state = MarketState(symbol=nse_symbol)
                    self._state[nse_symbol] = state

                # Initialise day_open on first successful fetch
                if state.day_open == 0:
                    state.day_open = float(getattr(info, "open", price) or price)
                    state.day_high = float(getattr(info, "day_high", price) or price)
                    state.day_low = float(getattr(info, "day_low", price) or price)

                # Out-of-order shield: only update if this fetch is newer
                if now <= state.last_tick_time:
                    continue

                prev_price = state.price
                state.price = round(price, 2)
                state.day_high = max(state.day_high, price)
                state.day_low = min(state.day_low, price)
                state.volume = float(getattr(info, "three_month_average_volume", 0) or 0)
                state.last_tick_time = now
                state.tick_quality = "VALID"

                # Detect stale data: if price unchanged for > 5 polls, flag as halted
                if prev_price == state.price and state.volume == 0:
                    state.is_halted = True
                else:
                    state.is_halted = False

                logger.debug(
                    "LiveFeed updated %s: price=%.2f vol=%.0f",
                    nse_symbol, state.price, state.volume,
                )

            except Exception as exc:
                logger.warning("Failed to update %s: %s", nse_symbol, exc)
