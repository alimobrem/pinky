"""Tests for Prometheus metrics endpoint."""

import pytest


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_format(authed_client):
    response = authed_client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "pinky_http_requests_total" in body
    assert "pinky_build_info" in body


@pytest.mark.asyncio
async def test_metrics_endpoint_is_unprotected(unauthed_client):
    """Metrics should be accessible without authentication."""
    # unauthed_client has no session cookie
    response = unauthed_client.get("/metrics")
    assert response.status_code == 200
