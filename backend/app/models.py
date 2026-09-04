from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------
class Watchlist(Base):
    """
    Maps a user to a set of tracked symbols.

    """

    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),
        Index("ix_watchlist_user_symbol", "user_id", "symbol"),
    )

    def __repr__(self) -> str:
        return f"<Watchlist user={self.user_id!r} symbol={self.symbol!r}>"


# ---------------------------------------------------------------------------
# UserCheckpoint
# ---------------------------------------------------------------------------
class UserCheckpoint(Base):
    """
    Persists the last-seen market state for each (user, symbol) pair.

    """

    __tablename__ = "user_checkpoints"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    seen_price: Mapped[float] = mapped_column(Float, nullable=False)
    seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
    )

    __table_args__ = (
        Index("ix_checkpoint_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<UserCheckpoint user={self.user_id!r} symbol={self.symbol!r} "
            f"seen_price={self.seen_price} seen_at={self.seen_at}>"
        )


# ---------------------------------------------------------------------------
# MarketBaseline
# ---------------------------------------------------------------------------
class MarketBaseline(Base):
    """
    Stores historical statistical anchor values for each instrument.
    
    """

    __tablename__ = "market_baselines"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    sector: Mapped[str] = mapped_column(String(64), nullable=True)

    # Pricing anchors
    base_price: Mapped[float] = mapped_column(Float, nullable=False)
    sigma_price: Mapped[float] = mapped_column(
        Float, nullable=False, comment="30-day annualised daily sigma (std dev of returns)"
    )

    # Volume baseline for Volume Ratio computation (V / μ_V)
    avg_volume: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Rolling 30-day average daily volume"
    )

    # Intraday anchors (reset at session open)
    day_open: Mapped[float] = mapped_column(Float, nullable=False)
    day_high: Mapped[float] = mapped_column(Float, nullable=False)
    day_low: Mapped[float] = mapped_column(Float, nullable=False)

    # Structural break levels
    week52_high: Mapped[float] = mapped_column(Float, nullable=False)
    week52_low: Mapped[float] = mapped_column(Float, nullable=False)

    def __repr__(self) -> str:
        return f"<MarketBaseline symbol={self.symbol!r} base_price={self.base_price}>"
