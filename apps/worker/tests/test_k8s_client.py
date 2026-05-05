"""K8s client tests — mock kubernetes-asyncio SDK, test summarization logic."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pinky_worker.observation.k8s_client import (
    _container_state,
    _event_summary,
    _node_summary,
    _pod_summary,
    delete_pod,
    list_events,
    list_pods,
    patch_resource,
    scale_deployment,
)


def _make_container_status(
    name: str = "web",
    ready: bool = True,
    restart_count: int = 0,
    state: SimpleNamespace | None = None,
    last_state: SimpleNamespace | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name, ready=ready, restart_count=restart_count,
        state=state or SimpleNamespace(running=True, waiting=None, terminated=None),
        last_state=last_state,
    )


def _make_pod(
    name: str = "web-abc",
    namespace: str = "default",
    phase: str = "Running",
    containers: list | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        metadata=SimpleNamespace(name=name, namespace=namespace),
        status=SimpleNamespace(
            phase=phase,
            container_statuses=containers or [_make_container_status()],
        ),
    )


def test_container_state_running() -> None:
    state = SimpleNamespace(running=True, waiting=None, terminated=None)
    assert _container_state(state) == {"type": "running"}


def test_container_state_waiting() -> None:
    state = SimpleNamespace(
        running=None,
        waiting=SimpleNamespace(reason="CrashLoopBackOff"),
        terminated=None,
    )
    result = _container_state(state)
    assert result == {"type": "waiting", "reason": "CrashLoopBackOff"}


def test_container_state_terminated() -> None:
    state = SimpleNamespace(
        running=None, waiting=None,
        terminated=SimpleNamespace(reason="OOMKilled", exit_code=137),
    )
    result = _container_state(state)
    assert result == {"type": "terminated", "reason": "OOMKilled", "exit_code": 137}


def test_container_state_none() -> None:
    assert _container_state(None) is None


def test_pod_summary_basic() -> None:
    pod = _make_pod()
    summary = _pod_summary(pod)
    assert summary["name"] == "web-abc"
    assert summary["namespace"] == "default"
    assert summary["phase"] == "Running"
    assert len(summary["containers"]) == 1
    assert summary["containers"][0]["name"] == "web"


def test_pod_summary_no_status() -> None:
    pod = SimpleNamespace(
        metadata=SimpleNamespace(name="broken", namespace="test"),
        status=None,
    )
    summary = _pod_summary(pod)
    assert summary["phase"] == "Unknown"
    assert summary["containers"] == []


def test_pod_summary_restart_count() -> None:
    containers = [
        _make_container_status(name="a", restart_count=3),
        _make_container_status(name="b", restart_count=7),
    ]
    pod = _make_pod(containers=containers)
    summary = _pod_summary(pod)
    assert summary["restart_count"] == 10


def test_event_summary() -> None:
    event = SimpleNamespace(
        type="Warning",
        reason="BackOff",
        message="Back-off restarting",
        source=SimpleNamespace(component="kubelet"),
        first_timestamp=None,
        last_timestamp=None,
        count=5,
        involved_object=SimpleNamespace(kind="Pod", name="web", namespace="default"),
    )
    summary = _event_summary(event)
    assert summary["type"] == "Warning"
    assert summary["reason"] == "BackOff"
    assert summary["count"] == 5
    assert summary["involved_object"]["kind"] == "Pod"


def test_node_summary() -> None:
    node = SimpleNamespace(
        metadata=SimpleNamespace(name="node-1"),
        status=SimpleNamespace(
            conditions=[
                SimpleNamespace(type="Ready", status="True", reason="KubeletReady"),
            ]
        ),
    )
    summary = _node_summary(node)
    assert summary["name"] == "node-1"
    assert summary["conditions"][0]["type"] == "Ready"


async def test_list_pods_all_namespaces() -> None:
    mock_client = MagicMock()
    mock_v1 = AsyncMock()
    mock_v1.list_pod_for_all_namespaces.return_value = SimpleNamespace(
        items=[_make_pod()],
    )
    with patch("pinky_worker.observation.k8s_client.client.CoreV1Api", return_value=mock_v1):
        pods = await list_pods(mock_client)

    assert len(pods) == 1
    assert pods[0]["name"] == "web-abc"
    mock_v1.list_pod_for_all_namespaces.assert_called_once()


async def test_list_pods_namespaced() -> None:
    mock_client = MagicMock()
    mock_v1 = AsyncMock()
    mock_v1.list_namespaced_pod.return_value = SimpleNamespace(items=[_make_pod()])
    with patch("pinky_worker.observation.k8s_client.client.CoreV1Api", return_value=mock_v1):
        await list_pods(mock_client, namespace="production")

    mock_v1.list_namespaced_pod.assert_called_once_with("production")


async def test_list_events_all_namespaces() -> None:
    mock_client = MagicMock()
    mock_v1 = AsyncMock()
    mock_v1.list_event_for_all_namespaces.return_value = SimpleNamespace(items=[])
    with patch("pinky_worker.observation.k8s_client.client.CoreV1Api", return_value=mock_v1):
        events = await list_events(mock_client)

    assert events == []


async def test_scale_deployment() -> None:
    mock_client = MagicMock()
    mock_apps = AsyncMock()
    with patch("pinky_worker.observation.k8s_client.client.AppsV1Api", return_value=mock_apps):
        result = await scale_deployment(mock_client, "default", "web", 3)

    assert result["replicas"] == 3
    assert result["status"] == "scaled"
    mock_apps.patch_namespaced_deployment_scale.assert_called_once()


async def test_delete_pod_call() -> None:
    mock_client = MagicMock()
    mock_v1 = AsyncMock()
    with patch("pinky_worker.observation.k8s_client.client.CoreV1Api", return_value=mock_v1):
        result = await delete_pod(mock_client, "default", "web-abc")

    assert result["status"] == "deleted"
    mock_v1.delete_namespaced_pod.assert_called_once_with("web-abc", "default")


async def test_patch_deployment() -> None:
    mock_client = MagicMock()
    mock_apps = AsyncMock()
    with patch("pinky_worker.observation.k8s_client.client.AppsV1Api", return_value=mock_apps):
        result = await patch_resource(mock_client, "default", "deployment", "web", {"spec": {}})

    assert result["status"] == "patched"


async def test_patch_unsupported_kind() -> None:
    mock_client = MagicMock()
    with pytest.raises(ValueError, match="Unsupported"):
        await patch_resource(mock_client, "default", "configmap", "test", {})
