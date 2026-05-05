"""Observer tests — mock K8s client and correlator, test orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from pinky_worker.definitions.loader import Definition, DefinitionRegistry
from pinky_worker.observation.observer import SCANNER_FETCHERS, observe_cluster


def _mock_registry() -> DefinitionRegistry:
    registry = DefinitionRegistry()
    scanner = Definition(
        kind="scanner", name="pod-health", version="1.0.0",
        frontmatter={"kind": "scanner"}, body="", source="test",
    )
    policy = Definition(
        kind="policy", name="default", version="1.0.0",
        frontmatter={"kind": "policy", "priority": 100, "conditions": {}, "action": {"action_type": "observe"}},
        body="", source="test",
    )
    registry._definitions = {
        ("scanner", "pod-health"): scanner,
        ("policy", "default"): policy,
    }
    return registry


HEALTHY_PODS = [
    {
        "name": "web-abc",
        "namespace": "default",
        "containers": [
            {"name": "web", "state": {"type": "running"}, "last_state": None, "restart_count": 0},
        ],
    },
]

UNHEALTHY_PODS = [
    {
        "name": "crash-pod",
        "namespace": "production",
        "containers": [
            {
                "name": "app",
                "state": {"type": "waiting", "reason": "CrashLoopBackOff"},
                "last_state": {"type": "terminated", "reason": "Error", "exit_code": 1},
                "restart_count": 8,
            },
        ],
    },
]


async def test_observer_clean_scan() -> None:
    mock_client = AsyncMock()
    mock_correlator = AsyncMock()

    async def mock_list_pods(*args, **kwargs):
        return HEALTHY_PODS

    with (
        patch("pinky_worker.observation.observer.create_client", return_value=mock_client),
        patch.dict(SCANNER_FETCHERS, {"pod-health": mock_list_pods}),
    ):
        await observe_cluster(
            cluster_id="cluster-1",
            registry=_mock_registry(),
            correlator=mock_correlator,
            scan_interval=1,
            max_cycles=1,
        )

    mock_correlator.correlate.assert_not_called()
    mock_client.close.assert_called_once()


async def test_observer_detects_crash_loop() -> None:
    mock_client = AsyncMock()
    mock_correlator = AsyncMock()
    mock_correlator.correlate.return_value = MagicMock(action="created", issue_id="issue-1")

    async def mock_list_pods(*args, **kwargs):
        return UNHEALTHY_PODS

    with (
        patch("pinky_worker.observation.observer.create_client", return_value=mock_client),
        patch.dict(SCANNER_FETCHERS, {"pod-health": mock_list_pods}),
    ):
        await observe_cluster(
            cluster_id="cluster-1",
            registry=_mock_registry(),
            correlator=mock_correlator,
            scan_interval=1,
            max_cycles=1,
        )

    assert mock_correlator.correlate.call_count >= 1
    check_ids = {call[0][0].check_id for call in mock_correlator.correlate.call_args_list}
    assert "crash-loop-backoff" in check_ids
    assert "excessive-restarts" in check_ids


async def test_observer_closes_client_on_error() -> None:
    mock_client = AsyncMock()

    async def mock_list_pods_error(*args, **kwargs):
        raise RuntimeError("K8s down")

    with (
        patch("pinky_worker.observation.observer.create_client", return_value=mock_client),
        patch.dict(SCANNER_FETCHERS, {"pod-health": mock_list_pods_error}),
    ):
        await observe_cluster(
            cluster_id="cluster-1",
            registry=_mock_registry(),
            correlator=AsyncMock(),
            scan_interval=1,
            max_cycles=1,
        )

    mock_client.close.assert_called_once()


async def test_observer_runs_multiple_cycles() -> None:
    mock_client = AsyncMock()
    mock_correlator = AsyncMock()
    call_count = 0

    async def mock_list_pods(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return HEALTHY_PODS

    with (
        patch("pinky_worker.observation.observer.create_client", return_value=mock_client),
        patch.dict(SCANNER_FETCHERS, {"pod-health": mock_list_pods}),
    ):
        await observe_cluster(
            cluster_id="cluster-1",
            registry=_mock_registry(),
            correlator=mock_correlator,
            scan_interval=0,
            max_cycles=3,
        )

    assert call_count == 3
