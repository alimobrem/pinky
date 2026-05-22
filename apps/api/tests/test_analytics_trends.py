"""Tests for /api/v1/analytics/trends endpoint."""
import pytest


@pytest.mark.asyncio
async def test_trends_endpoint_returns_buckets(authed_client):
    response = authed_client.get("/api/v1/analytics/trends?metric=token_usage&period=7d&bucket=day")
    assert response.status_code == 200
    data = response.json()
    assert data["metric"] == "token_usage"
    assert "buckets" in data


@pytest.mark.asyncio
async def test_trends_invalid_metric(authed_client):
    response = authed_client.get("/api/v1/analytics/trends?metric=invalid")
    assert response.status_code == 400
