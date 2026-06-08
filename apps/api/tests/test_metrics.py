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
async def test_metrics_api_v1_alias(authed_client):
    """The /api/v1/metrics alias works for route-proxied access."""
    response = authed_client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert "pinky_http_requests_total" in response.text


@pytest.mark.asyncio
async def test_metrics_endpoint_is_unprotected(unauthed_client):
    """Metrics should be accessible without authentication on both paths."""
    response = unauthed_client.get("/metrics")
    assert response.status_code == 200

    response = unauthed_client.get("/api/v1/metrics")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_metrics_middleware_increments_counters(authed_client):
    """Request counter increments after making requests."""
    authed_client.get("/api/v1/healthz")
    authed_client.get("/api/v1/healthz")

    response = authed_client.get("/metrics")
    body = response.text
    assert 'pinky_http_requests_total{' in body
    assert 'endpoint="/api/v1/healthz"' in body


@pytest.mark.asyncio
async def test_metrics_latency_histogram_populated(authed_client):
    """Latency histogram records observations after requests."""
    authed_client.get("/api/v1/readyz")

    response = authed_client.get("/metrics")
    body = response.text
    assert "pinky_http_request_duration_seconds_bucket" in body


@pytest.mark.asyncio
async def test_metrics_normalizes_uuid_paths(authed_client):
    """Dynamic UUID path segments are normalized to :id to prevent cardinality explosion."""
    authed_client.get("/api/v1/work-items/00000000-0000-0000-0000-000000000099")

    response = authed_client.get("/metrics")
    body = response.text
    assert "00000000-0000-0000-0000-000000000099" not in body or ":id" in body
