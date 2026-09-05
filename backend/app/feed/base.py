from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# MarketState — the canonical in-memory tick snapshot
# ---------------------------------------------------------------------------

@dataclass
class MarketState:
    """
    Represents the latest known state of a single instrument.

    """

    symbol: str

    # Pricing
    price: float = 0.0
    last_valid_price: float = 0.0
    day_open: float = 0.0
    day_high: float = 0.0
    day_low: float = float("inf")

    # Volume
    volume: float = 0.0          # Cumulative intraday volume (shares)

    # Feed metadata
    last_tick_time: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    feed_status: str = "LIVE"    # LIVE | DELAYED | STALE
    feed_lag_ms: float = 0.0     # Time since last tick in ms

    # Quality / Resilience flags
    tick_quality: str = "VALID"  # VALID | SUSPECT_TICK
    is_halted: bool = False

    # Derived convenience field
    @property
    def change_pct_day(self) -> float:
        """Percentage change from day open to current price."""
        if self.day_open == 0:
            return 0.0
        return ((self.price - self.day_open) / self.day_open) * 100.0

    def update_lag(self) -> None:
        """Recalculate feed_lag_ms and feed_status from wall-clock time."""
        now = datetime.now(timezone.utc)
        lag = (now - self.last_tick_time).total_seconds() * 1000.0
        self.feed_lag_ms = lag

        if lag < 2_000:
            self.feed_status = "LIVE"
        elif lag < 15_000:
            self.feed_status = "DELAYED"
        else:
            self.feed_status = "STALE"


# ---------------------------------------------------------------------------
# Abstract feed interface
# ---------------------------------------------------------------------------

class BaseMarketFeed(ABC):
    """
    Abstract interface every feed implementation must satisfy.

    """

    def __init__(self) -> None:
        self._state: Dict[str, MarketState] = {}
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    async def start(self) -> None:
        """
        Initialise state and launch the background tick loop.
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """
        Signal the tick loop to stop and await its clean termination.
        """
        ...

    # ------------------------------------------------------------------
    # Read accessors (same for all implementations)
    # ------------------------------------------------------------------

    def get_latest_tick(self, symbol: str) -> Optional[MarketState]:
        """
        Return the latest MarketState for a symbol, updating lag metrics first.
        Returns None if the symbol is not tracked by this feed.
        """
        state = self._state.get(symbol.upper())
        if state is not None:
            state.update_lag()
        return state

    def get_all_ticks(self) -> Dict[str, MarketState]:
        """
        Return a snapshot of all tracked symbols with freshly computed lag.
        """
        for state in self._state.values():
            state.update_lag()
        return dict(self._state)

    def list_symbols(self) -> list[str]:
        """Return all tracked symbol tickers."""
        return list(self._state.keys())

    @property
    def is_running(self) -> bool:
        return self._running
