"""Lightweight K8s client for API — uses user's cluster binding token."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_KIND_TO_API: dict[str, tuple[str, str]] = {
    "pod": ("api/v1", "pods"),
    "service": ("api/v1", "services"),
    "configmap": ("api/v1", "configmaps"),
    "secret": ("api/v1", "secrets"),
    "persistentvolumeclaim": ("api/v1", "persistentvolumeclaims"),
    "deployment": ("apis/apps/v1", "deployments"),
    "statefulset": ("apis/apps/v1", "statefulsets"),
    "daemonset": ("apis/apps/v1", "daemonsets"),
    "replicaset": ("apis/apps/v1", "replicasets"),
    "job": ("apis/batch/v1", "jobs"),
    "cronjob": ("apis/batch/v1", "cronjobs"),
    "ingress": ("apis/networking.k8s.io/v1", "ingresses"),
    "namespace": ("api/v1", "namespaces"),
}


def _api_path(kind: str, namespace: str, name: str) -> str:
    kind_lower = kind.lower()
    api_prefix, plural = _KIND_TO_API.get(kind_lower, ("api/v1", f"{kind_lower}s"))
    return f"{api_prefix}/namespaces/{namespace}/{plural}/{name}"


async def get_resource(
    api_endpoint: str, token: str, namespace: str, kind: str, name: str,
) -> dict[str, Any]:
    url = f"{api_endpoint}/{_api_path(kind, namespace, name)}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, headers=headers, timeout=30)
        if resp.status_code == 404:
            return {"error": "not_found", "status": 404}
        if resp.status_code == 403:
            return {"error": "forbidden", "status": 403}
        resp.raise_for_status()
        return resp.json()


async def list_resources(
    api_endpoint: str, token: str, namespace: str, kind: str,
) -> dict[str, Any]:
    kind_lower = kind.lower()
    api_prefix, plural = _KIND_TO_API.get(kind_lower, ("api/v1", f"{kind_lower}s"))
    if namespace:
        url = f"{api_endpoint}/{api_prefix}/namespaces/{namespace}/{plural}"
    else:
        url = f"{api_endpoint}/{api_prefix}/{plural}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, headers=headers, timeout=30)
        if resp.status_code == 403:
            return {"error": "forbidden", "status": 403}
        resp.raise_for_status()
        return resp.json()


async def get_nodes(
    api_endpoint: str, token: str,
) -> dict[str, Any]:
    url = f"{api_endpoint}/api/v1/nodes"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, headers=headers, timeout=30)
        if resp.status_code == 403:
            return {"error": "forbidden", "status": 403}
        resp.raise_for_status()
        return resp.json()


async def get_events(
    api_endpoint: str, token: str, namespace: str,
) -> dict[str, Any]:
    url = f"{api_endpoint}/api/v1/namespaces/{namespace}/events" if namespace else f"{api_endpoint}/api/v1/events"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])[-20:]
        return {"items": items}


async def get_top_pods(
    api_endpoint: str, token: str, namespace: str = "",
) -> dict[str, Any]:
    if namespace:
        url = f"{api_endpoint}/apis/metrics.k8s.io/v1beta1/namespaces/{namespace}/pods"
    else:
        url = f"{api_endpoint}/apis/metrics.k8s.io/v1beta1/pods"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, headers=headers, timeout=30)
        if resp.status_code == 403:
            return {"error": "forbidden", "status": 403}
        if resp.status_code == 404:
            return {"error": "metrics_unavailable", "message": "metrics-server not installed"}
        resp.raise_for_status()
        data = resp.json()
        pods = []
        for item in data.get("items", []):
            meta = item.get("metadata", {})
            containers = item.get("containers", [])
            total_cpu = sum(int(c["usage"].get("cpu", "0").rstrip("n")) for c in containers if "usage" in c)
            total_mem = sum(int(c["usage"].get("memory", "0").rstrip("Ki")) for c in containers if "usage" in c)
            pods.append({
                "name": meta.get("name"),
                "namespace": meta.get("namespace", ""),
                "cpu_nanocores": total_cpu,
                "cpu": f"{total_cpu / 1_000_000:.1f}m",
                "memory_ki": total_mem,
                "memory": f"{total_mem // 1024}Mi",
            })
        return {"items": pods}


async def get_top_nodes(
    api_endpoint: str, token: str,
) -> dict[str, Any]:
    url = f"{api_endpoint}/apis/metrics.k8s.io/v1beta1/nodes"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, headers=headers, timeout=30)
        if resp.status_code == 403:
            return {"error": "forbidden", "status": 403}
        if resp.status_code == 404:
            return {"error": "metrics_unavailable", "message": "metrics-server not installed"}
        resp.raise_for_status()
        data = resp.json()
        nodes = []
        for item in data.get("items", []):
            usage = item.get("usage", {})
            nodes.append({
                "name": item.get("metadata", {}).get("name"),
                "cpu": usage.get("cpu", ""),
                "memory": usage.get("memory", ""),
            })
        return {"items": nodes}


async def query_prometheus(
    api_endpoint: str, token: str, query: str,
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    params = {"query": query}
    thanos_base = "https://thanos-querier.openshift-monitoring.svc:9091"

    for base in [thanos_base, api_endpoint]:
        try:
            prom_url = f"{base}/api/v1/query"
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.get(prom_url, headers=headers, params=params, timeout=30)
                if resp.status_code == 403:
                    continue
                if resp.status_code != 200:
                    continue
                data = resp.json()
                if data.get("status") == "success":
                    results = data.get("data", {}).get("result", [])
                    return {"items": [
                        {"metric": r.get("metric", {}), "value": r.get("value", [None, None])[1]}
                        for r in results
                    ]}
        except Exception:
            logger.debug("prometheus query failed at %s", base)
    return {"error": "prometheus_unavailable", "message": "Could not reach Prometheus/Thanos"}


async def apply_resource(
    api_endpoint: str, token: str, namespace: str, kind: str, name: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    url = f"{api_endpoint}/{_api_path(kind, namespace, name)}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/strategic-merge-patch+json",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.patch(url, headers=headers, content=json.dumps(manifest), timeout=30)
        if resp.status_code == 403:
            return {"error": "forbidden", "status": 403}
        if resp.status_code == 422:
            body = resp.json()
            return {"error": "invalid", "status": 422, "message": body.get("message", "")}
        resp.raise_for_status()
        return resp.json()
