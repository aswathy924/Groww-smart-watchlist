import asyncio
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.feed.base import MarketState
from app.feed.hybrid_feed import HybridFeed
from app.main import app
from app.models import MarketBaseline, UserCheckpoint, Watchlist

# In-memory test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(test_engine):
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Seed test baseline
        baseline = MarketBaseline(
            symbol="RELIANCE",
            name="Reliance Industries Ltd",
            sector="Energy",
            base_price=3000.0,
            sigma_price=0.22,
            avg_volume=8_500_000,
            day_open=3000.0,
            day_high=3000.0,
            day_low=3000.0,
            week52_low=2200.0,
            week52_high=3200.0,
        )
        session.add(baseline)

        # Seed test watchlist
        w_item = Watchlist(user_id="test_user", symbol="RELIANCE")
        session.add(w_item)

        # Seed test checkpoint
        cp = UserCheckpoint(
            user_id="test_user",
            symbol="RELIANCE",
            seen_price=3000.0,
            seen_at=datetime.now(timezone.utc),
        )
        session.add(cp)
        await session.commit()
        yield session

@pytest_asyncio.fixture
async def async_client(test_engine, db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Ensure feed and injector exist on app.state
    feed = HybridFeed()
    feed._seed_initial_state()
    app.state.feed = feed
    from app.feed.injector import FeedInjector
    app.state.injector = FeedInjector(feed)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
