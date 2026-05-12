"""Tests for _build_charts and _parse_k8s_quantity — pure function unit tests."""

from __future__ import annotations

import pytest

from pinky_api.k8s import _parse_k8s_quantity
from pinky_api.routes.work_items import _build_charts


class TestParseK8sQuantity:
    def test_nanocores(self) -> None:
        assert _parse_k8s_quantity("500000000n") == 500_000_000

    def test_microcores(self) -> None:
        assert _parse_k8s_quantity("500000u") == 500_000_000

    def test_millicores(self) -> None:
        assert _parse_k8s_quantity("250m") == 250_000_000

    def test_whole_cores(self) -> None:
        assert _parse_k8s_quantity("2") == 2_000_000_000

    def test_kibibytes(self) -> None:
        assert _parse_k8s_quantity("1024Ki") == 1024

    def test_mebibytes(self) -> None:
        assert _parse_k8s_quantity("512Mi") == 512 * 1024

    def test_gibibytes(self) -> None:
        assert _parse_k8s_quantity("4Gi") == 4 * 1024 * 1024

    def test_tebibytes(self) -> None:
        assert _parse_k8s_quantity("1Ti") == 1024 * 1024 * 1024

    def test_zero(self) -> None:
        assert _parse_k8s_quantity("0") == 0

    def test_invalid_returns_zero(self) -> None:
        assert _parse_k8s_quantity("abc") == 0

    def test_empty_returns_zero(self) -> None:
        assert _parse_k8s_quantity("") == 0


class TestBuildChartsTopPods:
    def _pod_result(self, count: int = 3) -> dict:
        return {
            "items": [
                {
                    "name": f"pod-{i}",
                    "namespace": "default",
                    "cpu_nanocores": (count - i) * 100_000_000,
                    "cpu": f"{(count - i) * 100}m",
                    "memory_ki": (count - i) * 10240,
                    "memory": f"{(count - i) * 10}Mi",
                }
                for i in range(count)
            ]
        }

    def test_produces_bar_chart(self) -> None:
        charts = _build_charts([("get_top_pods", {"namespace": "default"}, self._pod_result())])
        assert len(charts) == 1
        chart = charts[0]
        assert chart["type"] == "bar"
        assert "default" in chart["title"]
        assert chart["xKey"] == "name"

    def test_data_sorted_by_cpu_descending(self) -> None:
        charts = _build_charts([("get_top_pods", {}, self._pod_result())])
        data = charts[0]["data"]
        cpus = [d["CPU (millicores)"] for d in data]
        assert cpus == sorted(cpus, reverse=True)

    def test_two_series_cpu_and_memory(self) -> None:
        charts = _build_charts([("get_top_pods", {}, self._pod_result())])
        keys = [s["key"] for s in charts[0]["series"]]
        assert "CPU (millicores)" in keys
        assert "Memory (MiB)" in keys

    def test_caps_at_15_items(self) -> None:
        charts = _build_charts([("get_top_pods", {}, self._pod_result(count=25))])
        assert len(charts[0]["data"]) == 15

    def test_empty_items_skipped(self) -> None:
        charts = _build_charts([("get_top_pods", {}, {"items": []})])
        assert charts == []

    def test_title_without_namespace(self) -> None:
        charts = _build_charts([("get_top_pods", {}, self._pod_result(1))])
        assert "(" not in charts[0]["title"]


class TestBuildChartsTopNodes:
    def test_produces_bar_chart(self) -> None:
        result = {
            "items": [
                {"name": "node-1", "cpu_nanocores": 1_000_000_000, "cpu": "1000.0m", "memory_ki": 4_194_304, "memory": "4096Mi"},
                {"name": "node-2", "cpu_nanocores": 500_000_000, "cpu": "500.0m", "memory_ki": 2_097_152, "memory": "2048Mi"},
            ]
        }
        charts = _build_charts([("get_top_nodes", {}, result)])
        assert len(charts) == 1
        assert charts[0]["type"] == "bar"
        assert "Node" in charts[0]["title"]

    def test_node_data_values(self) -> None:
        result = {
            "items": [{"name": "n1", "cpu_nanocores": 500_000_000, "cpu": "500m", "memory_ki": 1_048_576, "memory": "1024Mi"}]
        }
        charts = _build_charts([("get_top_nodes", {}, result)])
        data = charts[0]["data"][0]
        assert data["CPU (millicores)"] == 500.0
        assert data["Memory (MiB)"] == 1024.0


class TestBuildChartsPrometheus:
    def test_instant_query_bar_chart(self) -> None:
        result = {
            "items": [
                {"metric": {"__name__": "up", "job": "kubelet"}, "value": "1"},
                {"metric": {"__name__": "up", "job": "apiserver"}, "value": "1"},
            ]
        }
        charts = _build_charts([("query_prometheus", {"query": "up"}, result)])
        assert len(charts) == 1
        assert charts[0]["type"] == "bar"
        assert charts[0]["title"] == "up"
        assert len(charts[0]["data"]) == 2

    def test_instant_query_handles_non_numeric(self) -> None:
        result = {"items": [{"metric": {}, "value": "NaN"}]}
        charts = _build_charts([("query_prometheus", {"query": "test"}, result)])
        assert charts[0]["data"][0]["value"] == 0.0

    def test_instant_query_empty_items(self) -> None:
        charts = _build_charts([("query_prometheus", {"query": "test"}, {"items": []})])
        assert charts == []


class TestBuildChartsPrometheusRange:
    def test_range_query_line_chart(self) -> None:
        result = {
            "series": [
                {
                    "metric": {"__name__": "cpu_usage"},
                    "values": [
                        [1700000000, "0.5"],
                        [1700000060, "0.7"],
                        [1700000120, "0.3"],
                    ],
                }
            ]
        }
        charts = _build_charts([("query_prometheus_range", {"query": "cpu_usage"}, result)])
        assert len(charts) == 1
        chart = charts[0]
        assert chart["type"] == "line"
        assert chart["xKey"] == "time"
        assert len(chart["data"]) == 3
        assert len(chart["series"]) == 1

    def test_range_query_multiple_series(self) -> None:
        result = {
            "series": [
                {"metric": {"instance": "a"}, "values": [[1700000000, "1"]]},
                {"metric": {"instance": "b"}, "values": [[1700000000, "2"]]},
            ]
        }
        charts = _build_charts([("query_prometheus_range", {"query": "test"}, result)])
        assert len(charts[0]["series"]) == 2

    def test_range_query_caps_at_5_series(self) -> None:
        result = {
            "series": [
                {"metric": {"i": str(i)}, "values": [[1700000000, str(i)]]}
                for i in range(8)
            ]
        }
        charts = _build_charts([("query_prometheus_range", {"query": "test"}, result)])
        assert len(charts[0]["series"]) == 5

    def test_range_query_empty_series(self) -> None:
        charts = _build_charts([("query_prometheus_range", {"query": "test"}, {"series": []})])
        assert charts == []

    def test_timestamps_formatted_as_hhmm(self) -> None:
        result = {
            "series": [{"metric": {}, "values": [[1700000000, "1"]]}]
        }
        charts = _build_charts([("query_prometheus_range", {"query": "q"}, result)])
        time_val = charts[0]["data"][0]["time"]
        assert ":" in str(time_val)


class TestBuildChartsMultipleTools:
    def test_multiple_tool_results_produce_multiple_charts(self) -> None:
        pods = {
            "items": [{"name": "p1", "namespace": "ns", "cpu_nanocores": 100_000_000, "cpu": "100m", "memory_ki": 1024, "memory": "1Mi"}]
        }
        prom = {
            "items": [{"metric": {"__name__": "up"}, "value": "1"}]
        }
        charts = _build_charts([
            ("get_top_pods", {}, pods),
            ("query_prometheus", {"query": "up"}, prom),
        ])
        assert len(charts) == 2
        assert charts[0]["type"] == "bar"
        assert charts[1]["type"] == "bar"

    def test_empty_captured_returns_empty(self) -> None:
        assert _build_charts([]) == []
