"""Unit tests for the Prometheus client wrapper.

Mocks aiohttp.ClientSession to test PromClient without a real Prometheus.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pinky_worker.observation.prom_client import PromClient


def _make_api_client() -> MagicMock:
    """Build a mock kubernetes_asyncio ApiClient with minimal config."""
    api_client = MagicMock()
    api_client.configuration.api_key = {"authorization": "test-token"}
    api_client.configuration.ssl_ca_cert = None
    return api_client


def _mock_session(response_json: dict | None = None, *, raise_exc: Exception | None = None):
    """Create a patched aiohttp.ClientSession context manager.

    Returns a patcher that replaces aiohttp.ClientSession with a mock
    whose .get() returns the given JSON or raises the given exception.
    """
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    if response_json is not None:
        mock_resp.json = AsyncMock(return_value=response_json)

    mock_get = AsyncMock()
    if raise_exc:
        mock_get.__aenter__ = AsyncMock(side_effect=raise_exc)
    else:
        mock_get.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_get.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_get)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    return patch("pinky_worker.observation.prom_client.aiohttp.ClientSession", return_value=mock_session)


# ---------------------------------------------------------------------------
# query_value tests
# ---------------------------------------------------------------------------


class TestPromClientQueryValue:
    @pytest.mark.asyncio
    async def test_vector_single_result(self) -> None:
        body = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [{"metric": {}, "value": [1234567890, "0.85"]}],
            },
        }
        with _mock_session(body):
            client = PromClient(_make_api_client())
            result = await client.query_value("up")
        assert result == pytest.approx(0.85)

    @pytest.mark.asyncio
    async def test_scalar_result(self) -> None:
        body = {
            "status": "success",
            "data": {
                "resultType": "scalar",
                "result": [{"metric": {}, "value": [1234567890, "42"]}],
            },
        }
        with _mock_session(body):
            client = PromClient(_make_api_client())
            result = await client.query_value("scalar(up)")
        assert result == pytest.approx(42.0)

    @pytest.mark.asyncio
    async def test_empty_result_returns_none(self) -> None:
        body = {
            "status": "success",
            "data": {"resultType": "vector", "result": []},
        }
        with _mock_session(body):
            client = PromClient(_make_api_client())
            result = await client.query_value("absent(up)")
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_results_returns_none(self) -> None:
        body = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {"metric": {"instance": "a"}, "value": [1234, "0.5"]},
                    {"metric": {"instance": "b"}, "value": [1234, "0.7"]},
                ],
            },
        }
        with _mock_session(body):
            client = PromClient(_make_api_client())
            result = await client.query_value("up")
        assert result is None


# ---------------------------------------------------------------------------
# instant_query tests
# ---------------------------------------------------------------------------


class TestPromClientInstantQuery:
    @pytest.mark.asyncio
    async def test_connection_error_returns_empty_list(self) -> None:
        import aiohttp

        with _mock_session(raise_exc=aiohttp.ClientError("connection refused")):
            client = PromClient(_make_api_client())
            result = await client.instant_query("up")
        assert result == []

    @pytest.mark.asyncio
    async def test_timeout_returns_empty_list(self) -> None:
        import asyncio

        with _mock_session(raise_exc=asyncio.TimeoutError()):
            client = PromClient(_make_api_client())
            result = await client.instant_query("up")
        assert result == []


# ---------------------------------------------------------------------------
# query_value with errors
# ---------------------------------------------------------------------------


class TestPromClientQueryValueErrors:
    @pytest.mark.asyncio
    async def test_timeout_returns_none(self) -> None:
        import asyncio

        with _mock_session(raise_exc=asyncio.TimeoutError()):
            client = PromClient(_make_api_client())
            result = await client.query_value("rate(http_requests[5m])")
        assert result is None

    @pytest.mark.asyncio
    async def test_connection_error_returns_none(self) -> None:
        import aiohttp

        with _mock_session(raise_exc=aiohttp.ClientError("refused")):
            client = PromClient(_make_api_client())
            result = await client.query_value("up")
        assert result is None


# ---------------------------------------------------------------------------
# Headers / auth
# ---------------------------------------------------------------------------


class TestPromClientAuth:
    @pytest.mark.asyncio
    async def test_bearer_token_header(self) -> None:
        api_client = _make_api_client()
        api_client.configuration.api_key = {"authorization": "my-sa-token"}
        client = PromClient(api_client)
        headers = client._headers()
        assert headers == {"Authorization": "Bearer my-sa-token"}

    @pytest.mark.asyncio
    async def test_no_token_empty_headers(self) -> None:
        api_client = _make_api_client()
        api_client.configuration.api_key = {}
        client = PromClient(api_client)
        headers = client._headers()
        assert headers == {}

    @pytest.mark.asyncio
    async def test_bearer_token_fallback_key(self) -> None:
        api_client = _make_api_client()
        api_client.configuration.api_key = {"BearerToken": "fallback-token"}
        client = PromClient(api_client)
        headers = client._headers()
        assert headers == {"Authorization": "Bearer fallback-token"}
