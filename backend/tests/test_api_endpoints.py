import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_watchlist_endpoint(async_client: AsyncClient):
    """Test full watchlist analysis response and fresh headers."""
    response = await async_client.get("/api/watchlist?user_id=test_user")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test_user"
    assert "items" in data
    assert len(data["items"]) >= 1
    assert "X-Feed-Status" in response.headers
    assert "X-Feed-Lag-Ms" in response.headers

@pytest.mark.asyncio
async def test_get_catch_up_endpoint(async_client: AsyncClient):
    """Test smart catch-up response returns structured priority tiers."""
    response = await async_client.get("/api/watchlist/catch-up?user_id=test_user")
    assert response.status_code == 200
    data = response.json()
    assert "high_attention" in data
    assert "moderate_attention" in data
    assert "total_flagged" in data

@pytest.mark.asyncio
async def test_post_checkpoint_endpoint(async_client: AsyncClient):
    """Test atomic checkpoint write resets deltas."""
    response = await async_client.post(
        "/api/watchlist/checkpoint?user_id=test_user",
        json={"symbols": ["RELIANCE"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "RELIANCE" in data["symbols_updated"]

@pytest.mark.asyncio
async def test_add_and_remove_watchlist_item(async_client: AsyncClient):
    """Test adding and removing a symbol from the watchlist."""
    # Add TCS
    add_resp = await async_client.post(
        "/api/watchlist/items?user_id=test_user",
        json={"symbol": "TCS"}
    )
    assert add_resp.status_code == 201
    assert add_resp.json()["symbol"] == "TCS"

    # Remove TCS
    del_resp = await async_client.delete("/api/watchlist/items/TCS?user_id=test_user")
    assert del_resp.status_code == 204

@pytest.mark.asyncio
async def test_feed_health_endpoint(async_client: AsyncClient):
    """Test system feed health metrics endpoint."""
    response = await async_client.get("/api/system/feed-health")
    assert response.status_code == 200
    data = response.json()
    assert data["feed_status"] in ("LIVE", "DELAYED", "STALE")
    assert data["active_symbols"] > 0
    assert "feed_lag_ms" in data

@pytest.mark.asyncio
async def test_inject_anomaly_endpoint(async_client: AsyncClient):
    """Test injecting price surge via test API."""
    response = await async_client.post(
        "/api/test/inject-anomaly",
        json={"symbol": "RELIANCE", "anomaly_type": "price_surge"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Price surge" in data["message"]

@pytest.mark.asyncio
async def test_simulate_inactivity_endpoint(async_client: AsyncClient):
    """Test simulating time fast-forward / user inactivity."""
    response = await async_client.post(
        "/api/test/simulate-inactivity",
        json={"user_id": "test_user", "minutes_ago": 120}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "simulated"
    assert data["minutes_ago"] == 120
    assert "symbols_updated" in data

