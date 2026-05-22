"""Tests for scanner quality endpoint."""
import pytest


@pytest.mark.asyncio
async def test_scanner_quality_returns_extended_fields(authed_client):
    response = authed_client.get("/api/v1/analytics/scanners")
    assert response.status_code == 200
    data = response.json()
    assert "scanners" in data
    for scanner in data["scanners"]:
        assert "scanner" in scanner
        assert "signal_total" in scanner
        assert "signal_suppressed" in scanner
        assert "false_positive_rate" in scanner
        assert "noise_ratio" in scanner
