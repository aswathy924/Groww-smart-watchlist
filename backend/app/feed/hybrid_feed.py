from __future__ import annotations

import asyncio
import logging
import math
import random
from datetime import datetime, timezone
from typing import Dict, Optional

import numpy as np

from app.feed.base import BaseMarketFeed, MarketState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Instrument definitions
# ---------------------------------------------------------------------------
INSTRUMENT_CATALOG: Dict[str, tuple] = {
    "RELIANCE": (
        "Reliance Industries Ltd", "Energy",
        2950.0, 0.22, 8_500_000, 2_220.0, 3_220.0,
    ),
    "TCS": (
        "Tata Consultancy Services", "IT",
        3880.0, 0.19, 3_200_000, 3_056.0, 4_592.0,
    ),
    "INFY": (
        "Infosys Ltd", "IT",
        1850.0, 0.23, 5_100_000, 1_358.0, 2_015.0,
    ),
    "HDFCBANK": (
        "HDFC Bank Ltd", "Banking",
        1720.0, 0.20, 10_400_000, 1_363.0, 1_880.0,
    ),
    "ICICIBANK": (
        "ICICI Bank Ltd", "Banking",
        1280.0, 0.21, 9_800_000, 989.0, 1_392.0,
    ),
    "TATAMOTORS": (
        "Tata Motors Ltd", "Auto",
        860.0, 0.32, 14_600_000, 647.0, 1_179.0,
    ),
    "BAJFINANCE": (
        "Bajaj Finance Ltd", "NBFC",
        7120.0, 0.28, 2_100_000, 6_188.0, 8_190.0,
    ),
    "WIPRO": (
        "Wipro Ltd", "IT",
        480.0, 0.24, 7_900_000, 387.0, 582.0,
    ),
    "MARUTI": (
        "Maruti Suzuki India", "Auto",
        12400.0, 0.20, 820_000, 10_238.0, 13_680.0,
    ),
    "LTIM": (
        "LTIMindtree Ltd", "IT",
        5600.0, 0.25, 1_250_000, 4_350.0, 6_767.0,
    ),
    "AXISBANK": (
        "Axis Bank Ltd", "Banking",
        1180.0, 0.22, 11_200_000, 966.0, 1_340.0,
    ),
    "SBIN": (
        "State Bank of India", "Banking",
        820.0, 0.24, 22_000_000, 680.0, 912.0,
    ),
    "NESTLEIND": (
        "Nestle India Ltd", "FMCG",
        2280.0, 0.16, 680_000, 2_010.0, 2_778.0,
    ),
    "ASIANPAINT": (
        "Asian Paints Ltd", "FMCG",
        2580.0, 0.18, 1_450_000, 2_235.0, 3_394.0,
    ),
    "ONGC": (
        "Oil & Natural Gas Corp", "Energy",
        295.0, 0.26, 28_000_000, 226.0, 345.0,
    ),
}

# Tick interval in seconds (1 tick per second for responsiveness)
TICK_INTERVAL_SEC: float = 1.0

# Jump diffusion parameters
JUMP_PROBABILITY_PER_DAY: float = 2.0        # Expected jumps per trading day
JUMP_MU: float = 0.0                          # Mean of log-jump
JUMP_SIGMA: float = 0.015                     # Std dev of log-jump (~1.5%)

# Seconds in a trading day (used for σ scaling)
TRADING_SECONDS_PER_DAY: int = 23_400         # 6.5 hours


class HybridFeed(BaseMarketFeed):
    """
    Always-on simulated market feed.

    """

    def __init__(self) -> None:
        super().__init__()
        # Volume multiplier — set by injector for volume_explosion events
        self._volume_multipliers: Dict[str, float] = {}
        # Pause event — cleared by the injector during feed_delay simulation
        self._pause_event: asyncio.Event = asyncio.Event()
        self._pause_event.set()   # Initially not paused (set = "go ahead")
        # Bad-tick pending flags per symbol — set by injector
        self._pending_bad_tick: Dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Seed initial state and launch the async tick loop."""
        self._seed_initial_state()
        self._running = True
        self._task = asyncio.create_task(self._tick_loop(), name="hybrid-feed-worker")
        logger.info("HybridFeed started: tracking %d symbols", len(self._state))

    async def stop(self) -> None:
        """Gracefully terminate the tick loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("HybridFeed stopped.")

    # ------------------------------------------------------------------
    # Seed
    # ------------------------------------------------------------------

    def _seed_initial_state(self) -> None:
        """Initialise MarketState for each instrument from the catalog."""
        for symbol, params in INSTRUMENT_CATALOG.items():
            name, sector, base_price, sigma, avg_vol, w52_low, w52_high = params
            # Add small random jitter so all symbols don't start at identical prices
            jitter = random.gauss(0, base_price * 0.002)
            price = round(base_price + jitter, 2)

            state = MarketState(
                symbol=symbol,
                price=price,
                day_open=price,
                day_high=price,
                day_low=price,
            )
            self._state[symbol] = state

        logger.debug("HybridFeed seeded %d instruments.", len(self._state))

    # ------------------------------------------------------------------
    # Tick loop
    # ------------------------------------------------------------------

    async def _tick_loop(self) -> None:
        """
        Main async loop: emits one tick per TICK_INTERVAL_SEC for every symbol.

        """
        rng = np.random.default_rng()

        while self._running:
            # Honour feed_delay pause — blocks here until event is set
            await self._pause_event.wait()

            tick_time = datetime.now(timezone.utc)

            for symbol, state in self._state.items():
                try:
                    self._process_tick(symbol, state, tick_time, rng)
                except Exception as exc:
                    logger.error("Tick error for %s: %s", symbol, exc, exc_info=True)

            await asyncio.sleep(TICK_INTERVAL_SEC)

    def _process_tick(
        self,
        symbol: str,
        state: MarketState,
        tick_time: datetime,
        rng: np.random.Generator,
    ) -> None:

        # ── Trading Halt check: pause price movements if symbol is halted
        if state.is_halted:
            state.last_tick_time = tick_time
            state.feed_lag_ms = 0.0
            state.feed_status = "LIVE"
            return

        # ── Out-of-order tick shield 
        if tick_time <= state.last_tick_time:
            logger.debug("Rejected out-of-order tick for %s (tick_time=%s ≤ last=%s)",
                         symbol, tick_time, state.last_tick_time)
            return

        # ── Bad-tick injection (from injector)
        if self._pending_bad_tick.get(symbol, False):
            self._apply_bad_tick(symbol, state, tick_time)
            self._pending_bad_tick[symbol] = False
            return

        # ── Self-healing bad-tick filter: restore true price if previous tick was suspect
        if state.tick_quality in ("SUSPECT_TICK", "UNVERIFIED_DATA"):
            if state.last_valid_price > 0:
                state.price = state.last_valid_price
            state.tick_quality = "VALID"
            logger.info("Restored %s price to last valid level: %.2f", symbol, state.price)

        # ── Retrieve instrument parameters for GBM 
        params = INSTRUMENT_CATALOG.get(symbol)
        if params is None:
            return
        _, _, base_price, sigma_annual, avg_vol, _, _ = params

        # ── Realistic trading activity: ~40% chance of an executed trade tick per second per stock
        # In real markets, not every symbol trades every single second
        if rng.random() > 0.45:
            # No price change on this tick, just slight volume accumulation
            per_tick_base_vol = avg_vol / TRADING_SECONDS_PER_DAY
            state.volume += per_tick_base_vol * rng.uniform(0.2, 0.8)
            state.last_tick_time = tick_time
            state.tick_quality = "VALID"
            state.feed_lag_ms = 0.0
            state.feed_status = "LIVE"
            return

        # ── Calibrated realistic micro-tick volatility 
        # Mean-reverting Ornstein-Uhlenbeck drift towards base price (prevents endless 30% drift)
        theta = 0.005  # Mean reversion speed
        ou_drift = -theta * (state.price - base_price) / base_price

        # Realistic tick volatility (~1.5-3 basis points per tick)
        tick_sigma = (sigma_annual / math.sqrt(TRADING_SECONDS_PER_DAY)) * 0.35
        Z = rng.standard_normal()
        log_return = ou_drift + (tick_sigma * Z)

        # Hackathon Pacing: Natural Poisson market events occur ~every 45-75 seconds across the watchlist
        # ~1.2% chance per tick that a stock experiences an organic news/breakout event (±1.5% to ±3.2% jump)
        is_organic_surge = False
        if rng.random() < 0.012:
            is_organic_surge = True
            jump_direction = 1.0 if rng.random() > 0.4 else -1.0
            jump_magnitude = rng.uniform(0.015, 0.032) * jump_direction
            log_return += jump_magnitude

        # Calculate new price with NSE standard 5-paise (₹0.05) tick quantization
        raw_price = state.price * math.exp(log_return)
        new_price = round(round(raw_price / 0.05) * 0.05, 2)
        new_price = max(new_price, 0.05)

        # Volume (amplified during organic surges or manual injections)
        per_tick_base_vol = avg_vol / TRADING_SECONDS_PER_DAY
        vol_noise = rng.lognormal(0.0, 0.3)
        price_vol_amplifier = 2.8 if is_organic_surge else (1.0 + abs(Z) * 0.2)
        vol_multiplier = self._volume_multipliers.pop(symbol, 1.0)
        tick_volume = per_tick_base_vol * vol_noise * price_vol_amplifier * vol_multiplier

        # Apply updates
        state.price = new_price
        state.last_valid_price = new_price
        state.volume += tick_volume
        state.day_high = max(state.day_high, new_price)
        state.day_low = min(state.day_low, new_price)
        state.last_tick_time = tick_time
        state.tick_quality = "VALID"
        state.feed_lag_ms = 0.0
        state.feed_status = "LIVE"

    def _apply_bad_tick(
        self,
        symbol: str,
        state: MarketState,
        tick_time: datetime,
    ) -> None:
        """
        Apply a +20% bad tick tagged as UNVERIFIED_DATA.
        Preserves last_valid_price so subsequent ticks self-heal.
        """
        state.last_valid_price = state.price
        bad_price = round(state.price * 1.20, 2)   # +20% spike
        # NOTE: intentionally tiny volume — no market depth to support this move
        state.price = bad_price
        state.last_tick_time = tick_time
        state.tick_quality = "UNVERIFIED_DATA"
        state.feed_status = "LIVE"
        logger.warning("BAD TICK applied to %s: price=%.2f (UNVERIFIED_DATA, suppressed)", symbol, bad_price)

    # ------------------------------------------------------------------
    # Injector hooks (called by feed/injector.py)
    # ------------------------------------------------------------------

    def inject_price_surge(self, symbol: str) -> None:
        """Immediately apply a +6% price move to symbol's current price."""
        state = self._state.get(symbol.upper())
        if state is None:
            raise ValueError(f"Symbol {symbol!r} not tracked by HybridFeed")
        state.price = round(state.price * 1.06, 2)
        state.day_high = max(state.day_high, state.price)
        state.last_tick_time = datetime.now(timezone.utc)
        logger.info("PRICE_SURGE injected for %s: new price=%.2f", symbol, state.price)

    def inject_volume_explosion(self, symbol: str, multiplier: float = 4.0) -> None:
        """Set a volume multiplier for the symbol — applied on the next tick."""
        sym = symbol.upper()
        if sym not in self._state:
            raise ValueError(f"Symbol {sym!r} not tracked by HybridFeed")
        self._volume_multipliers[sym] = multiplier
        logger.info("VOLUME_EXPLOSION queued for %s: %.1fx multiplier", sym, multiplier)

    def inject_bad_tick(self, symbol: str) -> None:
        """Flag the next tick for symbol as a SUSPECT bad-tick spike."""
        sym = symbol.upper()
        if sym not in self._state:
            raise ValueError(f"Symbol {sym!r} not tracked by HybridFeed")
        self._pending_bad_tick[sym] = True
        logger.info("BAD_TICK queued for %s", sym)

    def inject_trading_halt(self, symbol: str, duration_seconds: int = 45) -> None:
        """Halt trading for the target symbol with automatic cooling window (45s)."""
        sym = symbol.upper()
        if sym not in self._state:
            raise ValueError(f"Symbol {sym!r} not tracked by HybridFeed")
        self._state[sym].is_halted = True
        logger.info("TRADING_HALT injected for %s (auto-resumes in %ds)", sym, duration_seconds)

        # Schedule auto-resume after cooling period
        async def _auto_resume():
            await asyncio.sleep(duration_seconds)
            if sym in self._state and self._state[sym].is_halted:
                self._state[sym].is_halted = False
                logger.info("TRADING_HALT cooled down: trading auto-resumed for %s", sym)

        asyncio.create_task(_auto_resume(), name=f"halt-cooldown-{sym}")

    def inject_resume_trading(self, symbol: str) -> None:
        """Resume trading for the target symbol."""
        sym = symbol.upper()
        if sym not in self._state:
            raise ValueError(f"Symbol {sym!r} not tracked by HybridFeed")
        self._state[sym].is_halted = False
        logger.info("RESUME_TRADING injected for %s", sym)

    async def inject_feed_delay(self, duration_seconds: int) -> None:
        """
        Pause tick emission for all symbols for `duration_seconds`.
        """
        logger.info("FEED_DELAY: pausing feed for %ds", duration_seconds)
        self._pause_event.clear()   # Block the tick loop
        await asyncio.sleep(duration_seconds)
        self._pause_event.set()     # Resume
        logger.info("FEED_DELAY: feed resumed after %ds", duration_seconds)
