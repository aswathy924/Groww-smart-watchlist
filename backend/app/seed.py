from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MarketBaseline, UserCheckpoint, Watchlist

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Baseline data (mirrors INSTRUMENT_CATALOG in hybrid_feed.py)
# ---------------------------------------------------------------------------
# Each entry: symbol → {field: value}
BASELINE_DATA: list[dict] = [
    {
        "symbol": "RELIANCE",
        "name": "Reliance Industries Ltd",
        "sector": "Energy",
        "base_price": 2950.0,
        "sigma_price": 0.22,
        "avg_volume": 8_500_000.0,
        "day_open": 2950.0,
        "day_high": 2950.0,
        "day_low": 2950.0,
        "week52_high": 3220.0,
        "week52_low": 2220.0,
    },
    {
        "symbol": "TCS",
        "name": "Tata Consultancy Services",
        "sector": "IT",
        "base_price": 3880.0,
        "sigma_price": 0.19,
        "avg_volume": 3_200_000.0,
        "day_open": 3880.0,
        "day_high": 3880.0,
        "day_low": 3880.0,
        "week52_high": 4592.0,
        "week52_low": 3056.0,
    },
    {
        "symbol": "INFY",
        "name": "Infosys Ltd",
        "sector": "IT",
        "base_price": 1850.0,
        "sigma_price": 0.23,
        "avg_volume": 5_100_000.0,
        "day_open": 1850.0,
        "day_high": 1850.0,
        "day_low": 1850.0,
        "week52_high": 2015.0,
        "week52_low": 1358.0,
    },
    {
        "symbol": "HDFCBANK",
        "name": "HDFC Bank Ltd",
        "sector": "Banking",
        "base_price": 1720.0,
        "sigma_price": 0.20,
        "avg_volume": 10_400_000.0,
        "day_open": 1720.0,
        "day_high": 1720.0,
        "day_low": 1720.0,
        "week52_high": 1880.0,
        "week52_low": 1363.0,
    },
    {
        "symbol": "ICICIBANK",
        "name": "ICICI Bank Ltd",
        "sector": "Banking",
        "base_price": 1280.0,
        "sigma_price": 0.21,
        "avg_volume": 9_800_000.0,
        "day_open": 1280.0,
        "day_high": 1280.0,
        "day_low": 1280.0,
        "week52_high": 1392.0,
        "week52_low": 989.0,
    },
    {
        "symbol": "TATAMOTORS",
        "name": "Tata Motors Ltd",
        "sector": "Auto",
        "base_price": 860.0,
        "sigma_price": 0.32,
        "avg_volume": 14_600_000.0,
        "day_open": 860.0,
        "day_high": 860.0,
        "day_low": 860.0,
        "week52_high": 1179.0,
        "week52_low": 647.0,
    },
    {
        "symbol": "BAJFINANCE",
        "name": "Bajaj Finance Ltd",
        "sector": "NBFC",
        "base_price": 7120.0,
        "sigma_price": 0.28,
        "avg_volume": 2_100_000.0,
        "day_open": 7120.0,
        "day_high": 7120.0,
        "day_low": 7120.0,
        "week52_high": 8190.0,
        "week52_low": 6188.0,
    },
    {
        "symbol": "WIPRO",
        "name": "Wipro Ltd",
        "sector": "IT",
        "base_price": 480.0,
        "sigma_price": 0.24,
        "avg_volume": 7_900_000.0,
        "day_open": 480.0,
        "day_high": 480.0,
        "day_low": 480.0,
        "week52_high": 582.0,
        "week52_low": 387.0,
    },
    {
        "symbol": "MARUTI",
        "name": "Maruti Suzuki India",
        "sector": "Auto",
        "base_price": 12400.0,
        "sigma_price": 0.20,
        "avg_volume": 820_000.0,
        "day_open": 12400.0,
        "day_high": 12400.0,
        "day_low": 12400.0,
        "week52_high": 13680.0,
        "week52_low": 10238.0,
    },
    {
        "symbol": "LTIM",
        "name": "LTIMindtree Ltd",
        "sector": "IT",
        "base_price": 5600.0,
        "sigma_price": 0.25,
        "avg_volume": 1_250_000.0,
        "day_open": 5600.0,
        "day_high": 5600.0,
        "day_low": 5600.0,
        "week52_high": 6767.0,
        "week52_low": 4350.0,
    },
    {
        "symbol": "AXISBANK",
        "name": "Axis Bank Ltd",
        "sector": "Banking",
        "base_price": 1180.0,
        "sigma_price": 0.22,
        "avg_volume": 11_200_000.0,
        "day_open": 1180.0,
        "day_high": 1180.0,
        "day_low": 1180.0,
        "week52_high": 1340.0,
        "week52_low": 966.0,
    },
    {
        "symbol": "SBIN",
        "name": "State Bank of India",
        "sector": "Banking",
        "base_price": 820.0,
        "sigma_price": 0.24,
        "avg_volume": 22_000_000.0,
        "day_open": 820.0,
        "day_high": 820.0,
        "day_low": 820.0,
        "week52_high": 912.0,
        "week52_low": 680.0,
    },
    {
        "symbol": "NESTLEIND",
        "name": "Nestle India Ltd",
        "sector": "FMCG",
        "base_price": 2280.0,
        "sigma_price": 0.16,
        "avg_volume": 680_000.0,
        "day_open": 2280.0,
        "day_high": 2280.0,
        "day_low": 2280.0,
        "week52_high": 2778.0,
        "week52_low": 2010.0,
    },
    {
        "symbol": "ASIANPAINT",
        "name": "Asian Paints Ltd",
        "sector": "FMCG",
        "base_price": 2580.0,
        "sigma_price": 0.18,
        "avg_volume": 1_450_000.0,
        "day_open": 2580.0,
        "day_high": 2580.0,
        "day_low": 2580.0,
        "week52_high": 3394.0,
        "week52_low": 2235.0,
    },
    {
        "symbol": "ONGC",
        "name": "Oil & Natural Gas Corp",
        "sector": "Energy",
        "base_price": 295.0,
        "sigma_price": 0.26,
        "avg_volume": 28_000_000.0,
        "day_open": 295.0,
        "day_high": 295.0,
        "day_low": 295.0,
        "week52_high": 345.0,
        "week52_low": 226.0,
    },
]

# ---------------------------------------------------------------------------
# Demo user watchlists
# trader_1 — Diversified large-cap portfolio
# trader_2 — Banking + IT focus (different set to show isolation)
# ---------------------------------------------------------------------------
DEMO_WATCHLISTS: dict[str, list[str]] = {
    "trader_1": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "TATAMOTORS",
                 "BAJFINANCE", "SBIN"],
    "trader_2": ["ICICIBANK", "AXISBANK", "WIPRO", "MARUTI", "ONGC"],
}


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

async def seed_baselines(db: AsyncSession) -> None:
    """
    Upsert all market baseline rows.
    """
    stmt = sqlite_upsert(MarketBaseline).values(BASELINE_DATA)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol"],
        set_={col: stmt.excluded[col] for col in [
            "name", "sector", "base_price", "sigma_price", "avg_volume",
            "day_open", "day_high", "day_low", "week52_high", "week52_low",
        ]},
    )
    await db.execute(stmt)
    await db.commit()
    logger.info("Seeded %d market baselines.", len(BASELINE_DATA))


async def seed_demo_watchlists(db: AsyncSession) -> None:
    """
    Seed default watchlists for demo users if they don't already have entries.

    """
    now = datetime.now(timezone.utc)

    for user_id, symbols in DEMO_WATCHLISTS.items():
        # Check if user already has watchlist entries
        result = await db.execute(
            select(Watchlist.symbol).where(Watchlist.user_id == user_id).limit(1)
        )
        if result.scalar() is not None:
            logger.debug("Watchlist for %r already seeded — skipping.", user_id)
            continue

        rows = [
            {"user_id": user_id, "symbol": sym, "created_at": now}
            for sym in symbols
        ]
        stmt = sqlite_upsert(Watchlist).values(rows)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["user_id", "symbol"]  # uses uq_watchlist_user_symbol
        )
        await db.execute(stmt)
        logger.info("Seeded watchlist for %r: %s", user_id, symbols)

    await db.commit()


async def seed_initial_checkpoints(db: AsyncSession, feed) -> None:
    """
    Bootstrap checkpoints for demo users at their watchlist symbols.

    """
    now = datetime.now(timezone.utc)

    for user_id, symbols in DEMO_WATCHLISTS.items():
        for symbol in symbols:
            # Only create if checkpoint doesn't exist yet
            result = await db.execute(
                select(UserCheckpoint).where(
                    UserCheckpoint.user_id == user_id,
                    UserCheckpoint.symbol == symbol,
                )
            )
            if result.scalar() is not None:
                continue

            tick = feed.get_latest_tick(symbol)
            if tick is None:
                continue

            stmt = sqlite_upsert(UserCheckpoint).values(
                user_id=user_id,
                symbol=symbol,
                seen_price=tick.price,
                seen_at=now,
            )
            stmt = stmt.on_conflict_do_nothing()
            await db.execute(stmt)

    await db.commit()
    logger.info("Bootstrapped initial checkpoints for demo users.")


async def run_all_seeds(db: AsyncSession, feed=None) -> None:
    """
    Entry point called from main.py lifespan.
    Runs all seed operations in dependency order.
    """
    await seed_baselines(db)
    await seed_demo_watchlists(db)
    if feed is not None:
        await seed_initial_checkpoints(db, feed)
