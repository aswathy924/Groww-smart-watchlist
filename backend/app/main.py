from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import AsyncSessionLocal, init_db
from app.feed.injector import FeedInjector
from app.routers import test as test_router
from app.routers import watchlist as watchlist_router
from app.routers import system as system_router

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feed factory
# ---------------------------------------------------------------------------

def _create_feed():
    """
    Instantiate the correct feed based on the FEED_MODE environment variable.

    """
    feed_mode = os.environ.get("FEED_MODE", "hybrid").lower()

    if feed_mode == "live":
        from app.feed.live_feed import LiveFeed
        logger.info("Feed mode: LIVE (yfinance polling)")
        return LiveFeed()
    else:
        from app.feed.hybrid_feed import HybridFeed
        logger.info("Feed mode: HYBRID (GBM simulation, 24/7)")
        return HybridFeed()


# ---------------------------------------------------------------------------
# Lifespan context manager
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manages the full startup and shutdown lifecycle of the application.
    """
    # STARTUP 
    logger.info("=== Smart Market Watchlist — Starting up ===")

    # 1. Initialise database tables
    logger.info("Initialising database (SQLite WAL mode)...")
    await init_db()
    logger.info("Database tables ready.")

    # 2. Start market feed
    feed = _create_feed()
    await feed.start()
    app.state.feed = feed
    logger.info("Market feed started.")

    # 3. Seed database (baselines, demo watchlists, initial checkpoints)
    logger.info("Running database seed...")
    async with AsyncSessionLocal() as db:
        from app.seed import run_all_seeds
        await run_all_seeds(db, feed)
    logger.info("Database seed complete.")

    # 4. Wire up the injector
    injector = FeedInjector(feed)
    app.state.injector = injector
    logger.info("FeedInjector wired to active feed.")

    logger.info("=== Startup complete. API ready. ===")

    # HAND CONTROL TO APPLICATION 
    yield

    # SHUTDOWN 
    logger.info("=== Smart Market Watchlist — Shutting down ===")
    await feed.stop()
    logger.info("Market feed stopped. Goodbye.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Smart Market Watchlist API",
    description=(
        "End-to-end resilient market watchlist engine that answers: "
        "'What has meaningfully changed since the user last checked?'\n\n"
        "Features statistically-grounded Z-score delta detection, volume surge "
        "alerts, structural break identification, and a 24/7 GBM-simulated feed."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow the Vite dev server and any configured production origins
# ---------------------------------------------------------------------------
_raw_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
)
CORS_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Feed-Status", "X-Feed-Lag-Ms"],  # For Phase 2 freshness headers
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(watchlist_router.router)   # Phase 2: /api/watchlist/*
app.include_router(system_router.router)      # Phase 2: /api/system/*
app.include_router(test_router.router)        # Phase 1: /api/test/*


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def health_check():
    """
    Basic liveness probe.
    Returns feed mode and whether the tick worker is running.
    """
    feed = getattr(app.state, "feed", None)
    return {
        "status": "ok",
        "service": "watchlist-engine",
        "feed_running": feed.is_running if feed else False,
        "feed_mode": os.environ.get("FEED_MODE", "hybrid"),
        "tracked_symbols": feed.list_symbols() if feed else [],
    }