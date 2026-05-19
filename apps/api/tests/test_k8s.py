"""Tests for K8s client — API path construction, response parsing, error handling."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from pinky_api.k8s import (
    _api_path,
    _parse_k8s_quantity,
    apply_resource,
    get_events,
    get_nodes,
    get_resource,
    get_top_nodes,
    get_top_pods,
    list_resources,
    query_prometheus,
    query_prometheus_range,
)

EP = "https://api.test:6443"
TOK = "test-token"


def _mock_response(status: int = 200, body: dict | None = None) -> httpx.Response:
    return httpx.Response(status, json=body or {}, request=httpx.Request("GET", EP))


class TestApiPath:
    def test_deployment(self) -> None:
        assert _api_path("Deployment", "default", "web") == "apis/apps/v1/namespaces/default/deployments/web"

    def test_pod(self) -> None:
        assert _api_path("Pod", "kube-system", "coredns") == "api/v1/namespaces/kube-system/pods/coredns"

    def test_statefulset(self) -> None:
        assert _api_path("StatefulSet", "db", "postgres") == "apis/apps/v1/namespaces/db/statefulsets/postgres"

    def test_unknown_kind_falls_back(self) -> None:
        path = _api_path("CustomThing", "ns", "name")
        assert path == "api/v1/namespaces/ns/customthings/name"

    def test_case_insensitive(self) -> None:
        assert _api_path("deployment", "ns", "x") == _api_path("Deployment", "ns", "x")


class TestParseQuantity:
    def test_nanocores(self) -> None:
        assert _parse_k8s_quantity("250000000n") == 250000000

    def test_millicores(self) -> None:
        assert _parse_k8s_quantity("500m") == 500_000_000

    def test_ki(self) -> None:
        assert _parse_k8s_quantity("1024Ki") == 1024

    def test_mi(self) -> None:
        assert _parse_k8s_quantity("256Mi") == 256 * 1024

    def test_gi(self) -> None:
        assert _parse_k8s_quantity("2Gi") == 2 * 1024 * 1024

    def test_plain_number(self) -> None:
        assert _parse_k8s_quantity("4") == 4_000_000_000

    def test_invalid_returns_zero(self) -> None:
        assert _parse_k8s_quantity("bogus") == 0

    def test_empty_returns_zero(self) -> None:
        assert _parse_k8s_quantity("") == 0


class TestGetResource:
    @pytest.mark.asyncio
    async def test_returns_json_on_success(self) -> None:
        body = {"kind": "Deployment", "metadata": {"name": "web"}}
        mock_resp = _mock_response(200, body)
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_resource(EP, TOK, "default", "Deployment", "web")

        assert result["kind"] == "Deployment"
        call_url = mock_client.get.call_args[0][0]
        assert "apis/apps/v1/namespaces/default/deployments/web" in call_url

    @pytest.mark.asyncio
    async def test_returns_not_found(self) -> None:
        mock_resp = _mock_response(404, {"message": "not found"})
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_resource(EP, TOK, "default", "Pod", "gone")

        assert result == {"error": "not_found", "status": 404}

    @pytest.mark.asyncio
    async def test_returns_forbidden(self) -> None:
        mock_resp = _mock_response(403)
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_resource(EP, TOK, "default", "Secret", "db-creds")

        assert result == {"error": "forbidden", "status": 403}


class TestListResources:
    @pytest.mark.asyncio
    async def test_namespaced_url(self) -> None:
        body = {"items": [{"metadata": {"name": "web"}}]}
        mock_resp = _mock_response(200, body)
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await list_resources(EP, TOK, "default", "Deployment")

        call_url = mock_client.get.call_args[0][0]
        assert "/namespaces/default/deployments" in call_url
        assert result["items"][0]["metadata"]["name"] == "web"

    @pytest.mark.asyncio
    async def test_cluster_scoped_url(self) -> None:
        mock_resp = _mock_response(200, {"items": []})
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await list_resources(EP, TOK, "", "Namespace")

        call_url = mock_client.get.call_args[0][0]
        assert "/namespaces/" not in call_url.split("api/v1/")[-1]

    @pytest.mark.asyncio
    async def test_forbidden(self) -> None:
        mock_resp = _mock_response(403)
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await list_resources(EP, TOK, "default", "Pod")

        assert result["error"] == "forbidden"


class TestGetEvents:
    @pytest.mark.asyncio
    async def test_truncates_to_20(self) -> None:
        items = [{"metadata": {"name": f"evt-{i}"}} for i in range(30)]
        mock_resp = _mock_response(200, {"items": items})
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_events(EP, TOK, "default")

        assert len(result["items"]) == 20


class TestGetTopPods:
    @pytest.mark.asyncio
    async def test_parses_metrics(self) -> None:
        body = {"items": [{
            "metadata": {"name": "web-abc", "namespace": "default"},
            "containers": [{"usage": {"cpu": "100000000n", "memory": "2048Ki"}}],
        }]}
        mock_resp = _mock_response(200, body)
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_top_pods(EP, TOK, "default")

        pod = result["items"][0]
        assert pod["name"] == "web-abc"
        assert pod["cpu_nanocores"] == 100000000
        assert pod["memory_ki"] == 2048
        assert pod["cpu"] == "100.0m"
        assert pod["memory"] == "2Mi"

    @pytest.mark.asyncio
    async def test_metrics_unavailable(self) -> None:
        mock_resp = _mock_response(404)
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_top_pods(EP, TOK)

        assert result["error"] == "metrics_unavailable"


class TestGetTopNodes:
    @pytest.mark.asyncio
    async def test_parses_node_metrics(self) -> None:
        body = {"items": [{
            "metadata": {"name": "node-1"},
            "usage": {"cpu": "2000m", "memory": "4096Mi"},
        }]}
        mock_resp = _mock_response(200, body)
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_top_nodes(EP, TOK)

        node = result["items"][0]
        assert node["name"] == "node-1"
        assert node["cpu"] == "2000.0m"
        assert node["memory"] == "4096Mi"


class TestApplyResource:
    @pytest.mark.asyncio
    async def test_sends_strategic_merge_patch(self) -> None:
        body = {"kind": "Deployment", "metadata": {"name": "web"}}
        mock_resp = _mock_response(200, body)
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.patch.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            manifest = {"spec": {"replicas": 3}}
            result = await apply_resource(EP, TOK, "default", "Deployment", "web", manifest)

        headers = mock_client.patch.call_args[1]["headers"]
        assert headers["Content-Type"] == "application/strategic-merge-patch+json"
        sent_body = mock_client.patch.call_args[1]["content"]
        assert json.loads(sent_body) == {"spec": {"replicas": 3}}
        assert result["kind"] == "Deployment"

    @pytest.mark.asyncio
    async def test_dry_run_appends_query_param(self) -> None:
        mock_resp = _mock_response(200, {"kind": "Deployment"})
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.patch.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await apply_resource(EP, TOK, "default", "Deployment", "web", {}, dry_run=True)

        call_url = mock_client.patch.call_args[0][0]
        assert "?dryRun=All" in call_url

    @pytest.mark.asyncio
    async def test_forbidden(self) -> None:
        mock_resp = _mock_response(403)
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.patch.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await apply_resource(EP, TOK, "default", "Deployment", "web", {})

        assert result == {"error": "forbidden", "status": 403}

    @pytest.mark.asyncio
    async def test_invalid_422(self) -> None:
        mock_resp = _mock_response(422, {"message": "spec.replicas invalid"})
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.patch.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await apply_resource(EP, TOK, "default", "Deployment", "web", {})

        assert result["error"] == "invalid"
        assert result["status"] == 422
        assert "spec.replicas" in result["message"]


class TestQueryPrometheus:
    @pytest.mark.asyncio
    async def test_returns_results(self) -> None:
        prom_resp = {
            "status": "success",
            "data": {"result": [{"metric": {"pod": "web"}, "value": [1, "0.5"]}]},
        }
        mock_resp = _mock_response(200, prom_resp)
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await query_prometheus(EP, TOK, "up")

        assert result["items"][0]["metric"]["pod"] == "web"
        assert result["items"][0]["value"] == "0.5"

    @pytest.mark.asyncio
    async def test_unavailable(self) -> None:
        mock_resp = _mock_response(500)
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await query_prometheus(EP, TOK, "up")

        assert result["error"] == "prometheus_unavailable"


class TestQueryPrometheusRange:
    @pytest.mark.asyncio
    async def test_returns_series(self) -> None:
        prom_resp = {
            "status": "success",
            "data": {"result": [{"metric": {"pod": "web"}, "values": [[1, "0.5"], [2, "0.6"]]}]},
        }
        mock_resp = _mock_response(200, prom_resp)
        with patch("pinky_api.k8s.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await query_prometheus_range(EP, TOK, "up", "0", "100")

        assert len(result["series"][0]["values"]) == 2
