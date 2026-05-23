"""Tests for CSP violation reporting endpoint."""

import pytest


@pytest.mark.asyncio
async def test_csp_report_returns_204(authed_client):
    response = authed_client.post(
        "/api/v1/csp-report",
        json={"csp-report": {"document-uri": "https://pinky.example.com", "violated-directive": "script-src"}},
    )
    assert response.status_code == 204
