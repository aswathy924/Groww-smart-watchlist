from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enumerations (shared across multiple schemas)
# ---------------------------------------------------------------------------

class FeedStatus(str, Enum):
    """Upstream data feed freshness classification."""
    LIVE = "LIVE"          # lag < 2 seconds
    DELAYED = "DELAYED"    # lag 2–15 seconds
    STALE = "STALE"        # lag > 15 seconds


class TickQuality(str, Enum):
    """Per-tick data quality assessment."""
    VALID = "VALID"
    SUSPECT_TICK = "SUSPECT_TICK"       # Single-tick spike > 15% without depth
    UNVERIFIED_DATA = "UNVERIFIED_DATA" # Suppressed from alert pipeline


class AttentionTier(str, Enum):
    """Attention classification produced by the Delta Engine."""
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    NORMAL = "NORMAL"


class AnomalyType(str, Enum):
    """Supported injection types for the test/demo endpoint."""
    PRICE_SURGE = "price_surge"
    VOLUME_EXPLOSION = "volume_explosion"
    BAD_TICK = "bad_tick"
    FEED_DELAY = "feed_delay"
    TRADING_HALT = "trading_halt"
    RESUME_TRADING = "resume_trading"


# ---------------------------------------------------------------------------
# Market State (internal → API boundary)
# ---------------------------------------------------------------------------

class MarketStateSchema(BaseModel):
    """
    Snapshot of a single instrument's live state as returned by the feed.
    Maps directly to the MarketState dataclass in feed/base.py.
    """
    model_config = ConfigDict(from_attributes=True)

    symbol: str = Field(..., description="NSE ticker symbol, e.g. RELIANCE")
    price: float = Field(..., description="Latest trade price (LTP)")
    volume: float = Field(..., description="Cumulative intraday volume")
    day_high: float = Field(..., description="Intraday session high")
    day_low: float = Field(..., description="Intraday session low")
    day_open: float = Field(..., description="Session open price")
    last_tick_time: datetime = Field(..., description="UTC timestamp of the last accepted tick")
    feed_status: FeedStatus = Field(..., description="Feed freshness classification")
    feed_lag_ms: float = Field(..., description="Milliseconds since the last tick was received")
    tick_quality: TickQuality = Field(..., description="Quality flag for the most recent tick")
    is_halted: bool = Field(False, description="True if this symbol is circuit-breaker halted")
    change_pct_day: float = Field(0.0, description="% change from day open to current price")


# ---------------------------------------------------------------------------
# Watchlist CRUD
# ---------------------------------------------------------------------------

class WatchlistItemAdd(BaseModel):
    """Request body to add a symbol to the watchlist."""
    symbol: str = Field(..., min_length=1, max_length=32, description="NSE symbol to add")


class WatchlistItemResponse(BaseModel):
    """Single watchlist row returned to the client."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    symbol: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------

class CheckpointRead(BaseModel):
    """A user's stored checkpoint for a single symbol."""
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    symbol: str
    seen_price: float
    seen_at: datetime


class CheckpointBulkWrite(BaseModel):
    """
    Request body for POST /api/watchlist/checkpoint.
    If symbols is empty/None, checkpoints all symbols on the user's watchlist.
    """
    symbols: Optional[list[str]] = Field(
        None, description="Specific symbols to checkpoint; None means all."
    )


# ---------------------------------------------------------------------------
# Feed Health
# ---------------------------------------------------------------------------

class FeedHealthResponse(BaseModel):
    """System-level feed health report returned by GET /api/system/feed-health."""
    feed_status: FeedStatus
    feed_lag_ms: float = Field(..., description="Worst-case lag across all tracked symbols")
    active_symbols: int = Field(..., description="Number of symbols currently being tracked")
    halted_symbols: list[str] = Field(
        default_factory=list, description="Symbols currently in halted/circuit-breaker state"
    )
    suspect_tick_symbols: list[str] = Field(
        default_factory=list, description="Symbols whose last tick was classified SUSPECT_TICK"
    )
    last_updated: datetime = Field(..., description="Timestamp of this health snapshot")


# ---------------------------------------------------------------------------
# Anomaly Injection (test/demo endpoint)
# ---------------------------------------------------------------------------

class AnomalyInjectionRequest(BaseModel):
    """Request body for POST /api/test/inject-anomaly."""
    symbol: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Target symbol to inject the anomaly into",
    )
    anomaly_type: AnomalyType = Field(
        ...,
        description=(
            "price_surge: +6% price move | "
            "volume_explosion: 4x volume multiplier | "
            "bad_tick: +20% spike tagged SUSPECT_TICK | "
            "feed_delay: pause feed for duration_seconds"
        ),
    )
    duration_seconds: Optional[int] = Field(
        None,
        ge=1,
        le=120,
        description="Only used by feed_delay; how long to pause tick emission (seconds)",
    )


class AnomalyInjectionResponse(BaseModel):
    """Response confirming anomaly injection."""
    status: str = Field("injected", description="Always 'injected' on success")
    symbol: str
    anomaly_type: str
    message: str


class InactivitySimulationRequest(BaseModel):
    """Request body for POST /api/test/simulate-inactivity."""
    user_id: str = Field("trader_1", description="User identifier")
    minutes_ago: int = Field(120, ge=1, le=10080, description="How many minutes ago user last checked")


class InactivitySimulationResponse(BaseModel):
    """Response confirming time rewinding for checkpoint testing."""
    status: str = Field("simulated", description="Always 'simulated' on success")
    user_id: str
    minutes_ago: int
    new_seen_at: datetime
    symbols_updated: list[str]
    message: str


# ---------------------------------------------------------------------------
# Generic API wrapper
# ---------------------------------------------------------------------------

class APIResponse(BaseModel):
    """Generic success/error envelope."""
    success: bool = True
    message: str = "OK"
    data: Optional[Any] = None


# ---------------------------------------------------------------------------
# Phase 2: Watchlist API response models
# ---------------------------------------------------------------------------

class WatchlistRow(BaseModel):
    """
    A single row in the main watchlist table — combines live market data,
    delta engine output, and feed metadata for the frontend table view.
    """
    # Identity
    symbol: str
    name: str
    sector: str = ""

    # Live pricing
    current_price: float
    day_open: float
    day_high: float
    day_low: float
    change_pct_day: float   # % change from open

    # Delta since user's checkpoint
    checkpoint_price: Optional[float] = None
    seen_at: Optional[datetime] = None
    delta_price: float = 0.0
    delta_pct: float = 0.0      # % change since checkpoint

    # Statistical signals
    z_score: float = 0.0
    volume_ratio: float = 0.0

    # Structural breaks
    broke_day_high: bool = False
    broke_day_low: bool = False
    broke_52w_high: bool = False
    broke_52w_low: bool = False

    # Attention
    attention_tier: AttentionTier
    rationale: str
    signals_fired: list[str] = Field(default_factory=list)

    # Feed metadata (per-symbol freshness)
    feed_status: FeedStatus
    feed_lag_ms: float
    tick_quality: TickQuality
    is_halted: bool = False
    last_tick_time: Optional[datetime] = None


class WatchlistResponse(BaseModel):
    """
    Response for GET /api/watchlist.
    Includes per-row data plus global feed metadata headers.
    """
    user_id: str
    items: list[WatchlistRow]
    feed_status: FeedStatus
    feed_lag_ms: float
    total_count: int
    high_attention_count: int
    moderate_attention_count: int
    generated_at: datetime


class CatchUpItem(BaseModel):
    """
    A single item in the catch-up panel — instruments with MODERATE/HIGH
    attention that have meaningfully changed since the user's last checkpoint.
    """
    symbol: str
    name: str
    sector: str = ""
    current_price: float
    checkpoint_price: float
    delta_pct: float
    z_score: float
    volume_ratio: float
    attention_tier: AttentionTier
    rationale: str
    signals_fired: list[str] = Field(default_factory=list)
    broke_52w_high: bool = False
    broke_52w_low: bool = False
    feed_status: FeedStatus
    tick_quality: TickQuality
    seen_at: Optional[datetime] = None


class CatchUpResponse(BaseModel):
    """
    Response for GET /api/watchlist/catch-up — the core differentiator endpoint.
    """
    user_id: str
    high_attention: list[CatchUpItem]
    moderate_attention: list[CatchUpItem]
    total_flagged: int
    last_checkpoint_at: Optional[datetime]
    generated_at: datetime


class CheckpointWriteResponse(BaseModel):
    """Response for POST /api/watchlist/checkpoint."""
    user_id: str
    symbols_updated: list[str]
    checkpointed_at: datetime
    message: str


class SymbolSearchResult(BaseModel):
    """Result for symbol lookup (used in the Add Symbol modal)."""
    symbol: str
    name: str
    sector: str = ""
    base_price: float
    is_tracked: bool = False   # True if symbol is tracked by the active feed
