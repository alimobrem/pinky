"""Async Kubernetes client wrapper for observer loops."""

from __future__ import annotations

import logging
from typing import Any

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client import ApiClient

logger = logging.getLogger(__name__)


async def create_client(kubeconfig: str | None = None, in_cluster: bool = False) -> ApiClient:
    if in_cluster:
        config.load_incluster_config()
    elif kubeconfig:
        await config.load_kube_config(config_file=kubeconfig)
    else:
        await config.load_kube_config()
    return ApiClient()


async def list_pods(api_client: ApiClient, namespace: str = "") -> list[dict]:
    v1 = client.CoreV1Api(api_client)
    if namespace:
        result = await v1.list_namespaced_pod(namespace)
    else:
        result = await v1.list_pod_for_all_namespaces()
    return [_pod_summary(pod) for pod in result.items]


async def list_events(api_client: ApiClient, namespace: str = "", limit: int = 100) -> list[dict]:
    v1 = client.CoreV1Api(api_client)
    if namespace:
        result = await v1.list_namespaced_event(namespace, limit=limit)
    else:
        result = await v1.list_event_for_all_namespaces(limit=limit)
    return [_event_summary(e) for e in result.items]


async def list_nodes(api_client: ApiClient) -> list[dict]:
    v1 = client.CoreV1Api(api_client)
    result = await v1.list_node()
    return [_node_summary(n) for n in result.items]


def _pod_summary(pod: Any) -> dict:
    containers = pod.status.container_statuses or [] if pod.status else []
    return {
        "name": pod.metadata.name,
        "namespace": pod.metadata.namespace,
        "phase": pod.status.phase if pod.status else "Unknown",
        "restart_count": sum(c.restart_count or 0 for c in containers),
        "containers": [
            {
                "name": c.name,
                "ready": c.ready,
                "restart_count": c.restart_count or 0,
                "state": _container_state(c.state),
                "last_state": _container_state(c.last_state) if c.last_state else None,
            }
            for c in containers
        ],
    }


def _container_state(state: Any) -> dict | None:
    if state is None:
        return None
    if state.running:
        return {"type": "running"}
    if state.waiting:
        return {"type": "waiting", "reason": state.waiting.reason or ""}
    if state.terminated:
        return {"type": "terminated", "reason": state.terminated.reason or "", "exit_code": state.terminated.exit_code}
    return None


def _event_summary(event: Any) -> dict:
    return {
        "type": event.type,
        "reason": event.reason,
        "message": event.message,
        "source": event.source.component if event.source else "",
        "first_seen": event.first_timestamp.isoformat() if event.first_timestamp else "",
        "last_seen": event.last_timestamp.isoformat() if event.last_timestamp else "",
        "count": event.count or 1,
        "involved_object": {
            "kind": event.involved_object.kind if event.involved_object else "",
            "name": event.involved_object.name if event.involved_object else "",
            "namespace": event.involved_object.namespace if event.involved_object else "",
        },
    }


def _node_summary(node: Any) -> dict:
    conditions = node.status.conditions or [] if node.status else []
    return {
        "name": node.metadata.name,
        "conditions": [
            {"type": c.type, "status": c.status, "reason": c.reason or ""}
            for c in conditions
        ],
    }
