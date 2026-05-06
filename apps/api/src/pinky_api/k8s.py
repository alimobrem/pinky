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
