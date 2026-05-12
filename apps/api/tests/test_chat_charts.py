"""Integration tests for chat endpoint chart generation."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic.types import TextBlock, ToolUseBlock
from starlette.testclient import TestClient

ROUTE = "pinky_api.routes.work_items"
K8S = "pinky_api.k8s"

WORK_ITEM_ID = str(uuid.uuid4())
CLUSTER_ID = uuid.uuid4()


def _mock_work_item():
    wi = MagicMock()
    wi.cluster_id = CLUSTER_ID
    wi.title = "CrashLoopBackOff on web-pod"
    wi.why_now = "3 restarts in 5 minutes"
    return wi


def _make_text_block(text: str):
    block = MagicMock(spec=TextBlock)
    block.text = text
    block.type = "text"
    return block


def _make_tool_use_block(name: str, input_data: dict, block_id: str = "tool_1"):
    block = MagicMock(spec=ToolUseBlock)
    block.name = name
    block.input = input_data
    block.id = block_id
    block.type = "tool_use"
    return block


def _mock_anthropic_two_turns(tool_name: str, tool_input: dict):
    """Mock Anthropic client: first response calls a tool, second returns text."""
    client = MagicMock()
    create = AsyncMock()

    tool_response = MagicMock()
    tool_response.stop_reason = "tool_use"
    tool_response.content = [_make_tool_use_block(tool_name, tool_input)]

    text_response = MagicMock()
    text_response.stop_reason = "end_turn"
    text_response.content = [_make_text_block("Here are the metrics.")]

    create.side_effect = [tool_response, text_response]
    client.messages = MagicMock()
    client.messages.create = create
    return client


@pytest.fixture
def _chat_mocks():
    wi_repo = MagicMock()
    wi_repo.return_value.get = AsyncMock(return_value=_mock_work_item())

    exec_repo = MagicMock()
    exec_repo.return_value.get_investigation_for_work_item = AsyncMock(return_value=None)

    cluster_repo = MagicMock()
    cluster = MagicMock()
    cluster.api_endpoint = "https://api.test:6443"
    cluster_repo.return_value.get = AsyncMock(return_value=cluster)

    binding = MagicMock()
    binding.encrypted_token = b"encrypted"
    binding.expires_at = None
    binding.id = uuid.uuid4()

    with (
        patch(f"{ROUTE}.WorkItemRepository", wi_repo),
        patch("pinky_api.repositories.executions.ExecutionRepository", exec_repo),
        patch(f"{ROUTE}.require_cluster_read_access", AsyncMock()),
        patch(f"{ROUTE}.get_cluster_binding_for_principal", AsyncMock(return_value=binding)),
        patch("pinky_api.repositories.clusters.ClusterRepository", cluster_repo),
        patch("pinky_api.security.crypto.decrypt", return_value=b"test-token"),
    ):
        yield


class TestChatReturnsCharts:
    def test_top_pods_produces_bar_chart(
        self, authed_client: TestClient, _chat_mocks: None,
    ) -> None:
        pod_data = {
            "items": [
                {"name": "web-1", "namespace": "default", "cpu_nanocores": 200_000_000, "cpu": "200m", "memory_ki": 51200, "memory": "50Mi"},
                {"name": "web-2", "namespace": "default", "cpu_nanocores": 100_000_000, "cpu": "100m", "memory_ki": 25600, "memory": "25Mi"},
            ]
        }
        anthropic_client = _mock_anthropic_two_turns("get_top_pods", {"namespace": "default"})

        with (
            patch("anthropic.lib.vertex.AsyncAnthropicVertex", return_value=anthropic_client),
            patch(f"{K8S}.get_top_pods", AsyncMock(return_value=pod_data)),
        ):
            resp = authed_client.post(
                f"/api/v1/work-items/{WORK_ITEM_ID}/chat",
                json={"message": "show me top pods"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "charts" in data
        assert len(data["charts"]) == 1
        chart = data["charts"][0]
        assert chart["type"] == "bar"
        assert chart["xKey"] == "name"
        assert len(chart["data"]) == 2
        assert chart["data"][0]["name"] == "web-1"

    def test_top_nodes_produces_bar_chart(
        self, authed_client: TestClient, _chat_mocks: None,
    ) -> None:
        node_data = {
            "items": [
                {"name": "node-1", "cpu_nanocores": 1_000_000_000, "cpu": "1000m", "memory_ki": 4_194_304, "memory": "4096Mi"},
            ]
        }
        anthropic_client = _mock_anthropic_two_turns("get_top_nodes", {})

        with (
            patch("anthropic.lib.vertex.AsyncAnthropicVertex", return_value=anthropic_client),
            patch(f"{K8S}.get_top_nodes", AsyncMock(return_value=node_data)),
        ):
            resp = authed_client.post(
                f"/api/v1/work-items/{WORK_ITEM_ID}/chat",
                json={"message": "show me node usage"},
            )

        assert resp.status_code == 200
        charts = resp.json()["charts"]
        assert len(charts) == 1
        assert charts[0]["type"] == "bar"
        assert "Node" in charts[0]["title"]

    def test_prometheus_instant_produces_bar_chart(
        self, authed_client: TestClient, _chat_mocks: None,
    ) -> None:
        prom_data = {
            "items": [
                {"metric": {"__name__": "up", "job": "kubelet"}, "value": "1"},
            ]
        }
        anthropic_client = _mock_anthropic_two_turns("query_prometheus", {"query": "up"})

        with (
            patch("anthropic.lib.vertex.AsyncAnthropicVertex", return_value=anthropic_client),
            patch(f"{K8S}.query_prometheus", AsyncMock(return_value=prom_data)),
        ):
            resp = authed_client.post(
                f"/api/v1/work-items/{WORK_ITEM_ID}/chat",
                json={"message": "is everything up?"},
            )

        assert resp.status_code == 200
        charts = resp.json()["charts"]
        assert len(charts) == 1
        assert charts[0]["type"] == "bar"

    def test_prometheus_range_produces_line_chart(
        self, authed_client: TestClient, _chat_mocks: None,
    ) -> None:
        range_data = {
            "series": [
                {
                    "metric": {"__name__": "cpu_usage"},
                    "values": [[1700000000, "0.5"], [1700000060, "0.7"]],
                }
            ]
        }
        anthropic_client = _mock_anthropic_two_turns(
            "query_prometheus_range",
            {"query": "cpu_usage", "start": "1700000000", "end": "1700000120", "step": "60s"},
        )

        with (
            patch("anthropic.lib.vertex.AsyncAnthropicVertex", return_value=anthropic_client),
            patch(f"{K8S}.query_prometheus_range", AsyncMock(return_value=range_data)),
        ):
            resp = authed_client.post(
                f"/api/v1/work-items/{WORK_ITEM_ID}/chat",
                json={"message": "show me CPU over last hour"},
            )

        assert resp.status_code == 200
        charts = resp.json()["charts"]
        assert len(charts) == 1
        chart = charts[0]
        assert chart["type"] == "line"
        assert chart["xKey"] == "time"
        assert len(chart["data"]) == 2
        assert len(chart["series"]) == 1

    def test_no_tool_calls_returns_empty_charts(
        self, authed_client: TestClient, _chat_mocks: None,
    ) -> None:
        client = MagicMock()
        text_response = MagicMock()
        text_response.stop_reason = "end_turn"
        text_response.content = [_make_text_block("No metrics available.")]
        client.messages = MagicMock()
        client.messages.create = AsyncMock(return_value=text_response)

        with patch("anthropic.lib.vertex.AsyncAnthropicVertex", return_value=client):
            resp = authed_client.post(
                f"/api/v1/work-items/{WORK_ITEM_ID}/chat",
                json={"message": "hello"},
            )

        assert resp.status_code == 200
        assert resp.json()["charts"] == []

    def test_tool_error_not_charted(
        self, authed_client: TestClient, _chat_mocks: None,
    ) -> None:
        error_data = {"error": "forbidden", "status": 403}
        anthropic_client = _mock_anthropic_two_turns("get_top_pods", {})

        with (
            patch("anthropic.lib.vertex.AsyncAnthropicVertex", return_value=anthropic_client),
            patch(f"{K8S}.get_top_pods", AsyncMock(return_value=error_data)),
        ):
            resp = authed_client.post(
                f"/api/v1/work-items/{WORK_ITEM_ID}/chat",
                json={"message": "top pods"},
            )

        assert resp.status_code == 200
        assert resp.json()["charts"] == []

    def test_non_chartable_tool_not_captured(
        self, authed_client: TestClient, _chat_mocks: None,
    ) -> None:
        anthropic_client = _mock_anthropic_two_turns("get_nodes", {})

        with (
            patch("anthropic.lib.vertex.AsyncAnthropicVertex", return_value=anthropic_client),
            patch(f"{K8S}.get_nodes", AsyncMock(return_value={"items": []})),
        ):
            resp = authed_client.post(
                f"/api/v1/work-items/{WORK_ITEM_ID}/chat",
                json={"message": "show nodes"},
            )

        assert resp.status_code == 200
        assert resp.json()["charts"] == []
