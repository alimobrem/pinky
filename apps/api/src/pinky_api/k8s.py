"""Lightweight K8s client for API — uses user's cluster binding token."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_QUANTITY_RE = re.compile(r"^(\d+)(n|u|m|Ki|Mi|Gi|Ti)?$")
_QUANTITY_MULTIPLIERS = {
    "n": 1, "u": 1_000, "m": 1_000_000, "": 1_000_000_000,
    "Ki": 1, "Mi": 1024, "Gi": 1024 * 1024, "Ti": 1024 * 1024 * 1024,
}
_THANOS_BASE = "https://thanos-querier.openshift-monitoring.svc:9091"

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


def _parse_k8s_quantity(val: str) -> int:
    """Parse K8s resource quantity string to base units (nanocores for CPU, KiB for memory)."""
    m = _QUANTITY_RE.match(val)
    if not m:
        return 0
    num = int(m.group(1))
    suffix = m.group(2) or ""
    return num * _QUANTITY_MULTIPLIERS.get(suffix, 1)


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
            cpu_raw = usage.get("cpu", "0")
            mem_raw = usage.get("memory", "0Ki")
            total_cpu = _parse_k8s_quantity(cpu_raw)
            total_mem = _parse_k8s_quantity(mem_raw)
            nodes.append({
                "name": item.get("metadata", {}).get("name"),
                "cpu_nanocores": total_cpu,
                "cpu": f"{total_cpu / 1_000_000:.1f}m",
                "memory_ki": total_mem,
                "memory": f"{total_mem // 1024}Mi",
            })
        return {"items": nodes}


async def _query_prometheus_raw(
    api_endpoint: str, token: str, path: str, params: dict[str, str],
) -> dict[str, Any] | None:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    for base in [_THANOS_BASE, api_endpoint]:
        try:
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.get(f"{base}{path}", headers=headers, params=params, timeout=30)
                if resp.status_code == 403:
                    continue
                if resp.status_code != 200:
                    continue
                data = resp.json()
                if data.get("status") == "success":
                    return data
        except Exception:
            logger.debug("prometheus query failed at %s", base)
    return None


async def query_prometheus(
    api_endpoint: str, token: str, query: str,
) -> dict[str, Any]:
    data = await _query_prometheus_raw(api_endpoint, token, "/api/v1/query", {"query": query})
    if data is None:
        return {"error": "prometheus_unavailable", "message": "Could not reach Prometheus/Thanos"}
    results = data.get("data", {}).get("result", [])
    return {"items": [
        {"metric": r.get("metric", {}), "value": r.get("value", [None, None])[1]}
        for r in results
    ]}


async def query_prometheus_range(
    api_endpoint: str, token: str, query: str,
    start: str, end: str, step: str = "60s",
) -> dict[str, Any]:
    params = {"query": query, "start": start, "end": end, "step": step}
    data = await _query_prometheus_raw(api_endpoint, token, "/api/v1/query_range", params)
    if data is None:
        return {"error": "prometheus_unavailable", "message": "Could not reach Prometheus/Thanos"}
    results = data.get("data", {}).get("result", [])
    return {"series": [
        {"metric": r.get("metric", {}), "values": r.get("values", [])}
        for r in results
    ]}


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
