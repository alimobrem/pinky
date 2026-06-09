"""Prometheus client -- queries Thanos Querier on OpenShift clusters.

Uses the observer SA credentials via the K8s API client. Connects to
thanos-querier.openshift-monitoring.svc:9091 by default (OpenShift CMO).
"""

from __future__ import annotations

import logging
import ssl
from urllib.parse import quote

import aiohttp
from kubernetes_asyncio.client import ApiClient

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://thanos-querier.openshift-monitoring.svc:9091"


class PromClient:
    """Thin async wrapper around the Prometheus HTTP API."""

    def __init__(self, api_client: ApiClient, base_url: str = _DEFAULT_BASE_URL) -> None:
        self._api_client = api_client
        self._base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        token = self._api_client.configuration.api_key.get("authorization", "")
        if not token:
            token = self._api_client.configuration.api_key.get("BearerToken", "")
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def _ssl_context(self) -> ssl.SSLContext | bool:
        ca = self._api_client.configuration.ssl_ca_cert
        if ca:
            return ssl.create_default_context(cafile=ca)
        return False

    async def _get(self, path: str) -> dict:
        url = f"{self._base_url}{path}"
        ssl_ctx = self._ssl_context()
        async with (
            aiohttp.ClientSession(
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as session,
            session.get(url, ssl=ssl_ctx) as resp,
        ):
            resp.raise_for_status()
            return await resp.json()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def instant_query(self, query: str) -> list[dict]:
        """Execute a PromQL instant query. Returns ``data.result`` list."""
        try:
            body = await self._get(f"/api/v1/query?query={quote(query)}")
            return body.get("data", {}).get("result", [])
        except Exception:
            logger.warning("prometheus instant query failed", extra={"query": query})
            return []

    async def query_value(self, query: str) -> float | None:
        """Return a single scalar from an instant query, or *None*."""
        results = await self.instant_query(query)
        if not results:
            return None
        if len(results) == 1:
            result_type = results[0].get("value")
            if result_type and len(result_type) >= 2:
                return float(result_type[1])
        return None

    async def query_range(
        self, query: str, start: str, end: str, step: str = "60s",
    ) -> list[dict]:
        """Execute a PromQL range query. Returns ``data.result`` list."""
        try:
            path = (
                f"/api/v1/query_range?query={quote(query)}"
                f"&start={quote(start)}&end={quote(end)}&step={quote(step)}"
            )
            body = await self._get(path)
            return body.get("data", {}).get("result", [])
        except Exception:
            logger.warning("prometheus range query failed", extra={"query": query})
            return []
