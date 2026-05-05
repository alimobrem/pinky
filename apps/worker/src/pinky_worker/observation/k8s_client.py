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


async def scale_deployment(api_client: ApiClient, namespace: str, name: str, replicas: int) -> dict:
    apps_v1 = client.AppsV1Api(api_client)
    body = {"spec": {"replicas": replicas}}
    await apps_v1.patch_namespaced_deployment_scale(name, namespace, body)
    logger.info("scaled deployment %s/%s to %d replicas", namespace, name, replicas)
    return {"name": name, "namespace": namespace, "replicas": replicas, "status": "scaled"}


async def delete_pod(api_client: ApiClient, namespace: str, name: str) -> dict:
    v1 = client.CoreV1Api(api_client)
    await v1.delete_namespaced_pod(name, namespace)
    logger.info("deleted pod %s/%s", namespace, name)
    return {"name": name, "namespace": namespace, "status": "deleted"}


async def patch_resource(api_client: ApiClient, namespace: str, kind: str, name: str, patch: dict) -> dict:
    if kind.lower() in ("deployment", "deployments"):
        apps_v1 = client.AppsV1Api(api_client)
        await apps_v1.patch_namespaced_deployment(name, namespace, patch)
    elif kind.lower() in ("statefulset", "statefulsets"):
        apps_v1 = client.AppsV1Api(api_client)
        await apps_v1.patch_namespaced_stateful_set(name, namespace, patch)
    elif kind.lower() in ("daemonset", "daemonsets"):
        apps_v1 = client.AppsV1Api(api_client)
        await apps_v1.patch_namespaced_daemon_set(name, namespace, patch)
    else:
        raise ValueError(f"Unsupported resource kind for patch: {kind}")
    logger.info("patched %s %s/%s", kind, namespace, name)
    return {"kind": kind, "name": name, "namespace": namespace, "status": "patched"}


async def rollback_deployment(api_client: ApiClient, namespace: str, name: str) -> dict:
    apps_v1 = client.AppsV1Api(api_client)
    dep = await apps_v1.read_namespaced_deployment(name, namespace)
    current_revision = dep.metadata.annotations.get("deployment.kubernetes.io/revision", "0")
    body = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "kubectl.kubernetes.io/restartedAt": (
                            __import__("datetime").datetime.now(
                                __import__("datetime").timezone.utc
                            ).isoformat()
                        )
                    }
                }
            }
        }
    }
    await apps_v1.patch_namespaced_deployment(name, namespace, body)
    logger.info("triggered rollback for deployment %s/%s from revision %s", namespace, name, current_revision)
    return {"name": name, "namespace": namespace, "status": "rollback_triggered", "previous_revision": current_revision}


async def list_nodes(api_client: ApiClient) -> list[dict]:
    v1 = client.CoreV1Api(api_client)
    try:
        result = await v1.list_node()
    except Exception:
        logger.warning("failed to list nodes")
        return []
    return [_node_summary(n) for n in result.items]


async def list_deployments(api_client: ApiClient, namespace: str = "") -> list[dict]:
    apps_v1 = client.AppsV1Api(api_client)
    try:
        if namespace:
            result = await apps_v1.list_namespaced_deployment(namespace)
        else:
            result = await apps_v1.list_deployment_for_all_namespaces()
    except Exception:
        logger.warning("failed to list deployments")
        return []
    return [_deployment_summary(d) for d in result.items]


async def list_tls_secrets(api_client: ApiClient, namespace: str = "") -> list[dict]:
    v1 = client.CoreV1Api(api_client)
    try:
        if namespace:
            result = await v1.list_namespaced_secret(namespace)
        else:
            result = await v1.list_secret_for_all_namespaces()
    except Exception:
        logger.warning("failed to list secrets")
        return []
    return [
        _tls_secret_summary(s)
        for s in result.items
        if s.type == "kubernetes.io/tls"
    ]


async def list_pvcs(api_client: ApiClient, namespace: str = "") -> list[dict]:
    v1 = client.CoreV1Api(api_client)
    try:
        if namespace:
            result = await v1.list_namespaced_persistent_volume_claim(namespace)
        else:
            result = await v1.list_persistent_volume_claim_for_all_namespaces()
    except Exception:
        logger.warning("failed to list PVCs")
        return []
    return [_pvc_summary(p) for p in result.items]


async def list_resource_quotas(api_client: ApiClient, namespace: str = "") -> list[dict]:
    v1 = client.CoreV1Api(api_client)
    try:
        if namespace:
            result = await v1.list_namespaced_resource_quota(namespace)
        else:
            result = await v1.list_resource_quota_for_all_namespaces()
    except Exception:
        logger.warning("failed to list resource quotas")
        return []
    return [_quota_summary(q) for q in result.items]


async def list_ingresses(api_client: ApiClient, namespace: str = "") -> list[dict]:
    networking_v1 = client.NetworkingV1Api(api_client)
    try:
        if namespace:
            result = await networking_v1.list_namespaced_ingress(namespace)
        else:
            result = await networking_v1.list_ingress_for_all_namespaces()
    except Exception:
        logger.warning("failed to list ingresses")
        return []
    return [_ingress_summary(i) for i in result.items]


async def list_statefulsets(api_client: ApiClient, namespace: str = "") -> list[dict]:
    apps_v1 = client.AppsV1Api(api_client)
    try:
        if namespace:
            result = await apps_v1.list_namespaced_stateful_set(namespace)
        else:
            result = await apps_v1.list_stateful_set_for_all_namespaces()
    except Exception:
        logger.warning("failed to list statefulsets")
        return []
    return [_statefulset_summary(s) for s in result.items]


async def list_jobs(api_client: ApiClient, namespace: str = "") -> list[dict]:
    batch_v1 = client.BatchV1Api(api_client)
    try:
        if namespace:
            result = await batch_v1.list_namespaced_job(namespace)
        else:
            result = await batch_v1.list_job_for_all_namespaces()
    except Exception:
        logger.warning("failed to list jobs")
        return []
    return [_job_summary(j) for j in result.items]


async def list_cronjobs(api_client: ApiClient, namespace: str = "") -> list[dict]:
    batch_v1 = client.BatchV1Api(api_client)
    try:
        if namespace:
            result = await batch_v1.list_namespaced_cron_job(namespace)
        else:
            result = await batch_v1.list_cron_job_for_all_namespaces()
    except Exception:
        logger.warning("failed to list cronjobs")
        return []
    return [_cronjob_summary(c) for c in result.items]


async def list_services(api_client: ApiClient, namespace: str = "") -> list[dict]:
    v1 = client.CoreV1Api(api_client)
    try:
        if namespace:
            svc_result = await v1.list_namespaced_service(namespace)
            ep_result = await v1.list_namespaced_endpoints(namespace)
        else:
            svc_result = await v1.list_service_for_all_namespaces()
            ep_result = await v1.list_endpoints_for_all_namespaces()
    except Exception:
        logger.warning("failed to list services")
        return []

    # Index endpoints by namespace/name for lookup
    ep_map: dict[str, Any] = {}
    for ep in ep_result.items:
        key = f"{ep.metadata.namespace or ''}/{ep.metadata.name}"
        ep_map[key] = ep

    return [_service_summary(s, ep_map) for s in svc_result.items]


async def list_daemonsets(api_client: ApiClient, namespace: str = "") -> list[dict]:
    apps_v1 = client.AppsV1Api(api_client)
    try:
        if namespace:
            result = await apps_v1.list_namespaced_daemon_set(namespace)
        else:
            result = await apps_v1.list_daemon_set_for_all_namespaces()
    except Exception:
        logger.warning("failed to list daemonsets")
        return []
    return [_daemonset_summary(d) for d in result.items]


def _pod_summary(pod: Any) -> dict:
    containers = (pod.status.container_statuses or []) if pod.status else []
    created = pod.metadata.creation_timestamp
    return {
        "name": pod.metadata.name,
        "namespace": pod.metadata.namespace or "",
        "phase": pod.status.phase if pod.status else "Unknown",
        "creation_timestamp": created.isoformat() if created else None,
        "restart_count": sum(c.restart_count or 0 for c in containers),
        "containers": [
            {
                "name": c.name,
                "ready": c.ready or False,
                "restart_count": c.restart_count or 0,
                "state": _container_state(c.state) if c.state else None,
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
        "unschedulable": bool(node.spec.unschedulable) if node.spec else False,
        "conditions": [
            {"type": c.type, "status": c.status, "reason": c.reason or ""}
            for c in conditions
        ],
    }


def _deployment_summary(dep: Any) -> dict:
    spec = dep.spec or type("S", (), {"replicas": 1})()
    status = dep.status or type("S", (), {"ready_replicas": None, "unavailable_replicas": None, "conditions": None})()
    conditions = status.conditions or []
    return {
        "name": dep.metadata.name,
        "namespace": dep.metadata.namespace or "",
        "desired_replicas": spec.replicas or 1,
        "ready_replicas": status.ready_replicas or 0,
        "unavailable_replicas": status.unavailable_replicas or 0,
        "conditions": [
            {"type": c.type, "status": c.status, "reason": c.reason or "", "message": c.message or ""}
            for c in conditions
        ],
    }


def _tls_secret_summary(secret: Any) -> dict:
    data = secret.data or {}
    return {
        "name": secret.metadata.name,
        "namespace": secret.metadata.namespace or "",
        "data_keys": list(data.keys()),
        "tls_crt": data.get("tls.crt", ""),
    }


def _pvc_summary(pvc: Any) -> dict:
    status = pvc.status or type("S", (), {"phase": "Unknown"})()
    return {
        "name": pvc.metadata.name,
        "namespace": pvc.metadata.namespace or "",
        "phase": status.phase or "Unknown",
    }


def _quota_summary(quota: Any) -> dict:
    status = quota.status or type("S", (), {"hard": None, "used": None})()
    hard = status.hard or {}
    used = status.used or {}
    return {
        "name": quota.metadata.name,
        "namespace": quota.metadata.namespace or "",
        "hard": dict(hard),
        "used": dict(used),
    }


def _ingress_summary(ingress: Any) -> dict:
    spec = ingress.spec or type("S", (), {"rules": None})()
    rules = spec.rules or []
    parsed_rules = []
    for rule in rules:
        http = rule.http
        if not http:
            continue
        for path in http.paths or []:
            backend = path.backend
            if not backend:
                continue
            service = backend.service
            parsed_rules.append({
                "host": rule.host or "",
                "path": path.path or "/",
                "service_name": service.name if service else "",
                "service_port": service.port.number if service and service.port else None,
            })
    return {
        "name": ingress.metadata.name,
        "namespace": ingress.metadata.namespace or "",
        "rules": parsed_rules,
    }


def _statefulset_summary(sts: Any) -> dict:
    spec = sts.spec or type("S", (), {"replicas": 1})()
    status = sts.status or type("S", (), {
        "ready_replicas": None, "updated_replicas": None, "replicas": None,
        "current_revision": None, "update_revision": None,
    })()
    return {
        "name": sts.metadata.name,
        "namespace": sts.metadata.namespace or "",
        "replicas": spec.replicas or 1,
        "ready_replicas": status.ready_replicas or 0,
        "updated_replicas": status.updated_replicas or 0,
        "current_replicas": status.replicas or 0,
        "current_revision": getattr(status, "current_revision", None) or "",
        "update_revision": getattr(status, "update_revision", None) or "",
    }


def _job_summary(job: Any) -> dict:
    status = job.status or type("S", (), {
        "succeeded": None, "failed": None, "conditions": None,
    })()
    spec = job.spec or type("S", (), {"backoff_limit": 6})()
    conditions = status.conditions or []
    return {
        "kind": "Job",
        "name": job.metadata.name,
        "namespace": job.metadata.namespace or "",
        "succeeded": status.succeeded or 0,
        "failed": status.failed or 0,
        "backoff_limit": getattr(spec, "backoff_limit", 6) or 6,
        "conditions": [
            {"type": c.type, "status": c.status, "reason": c.reason or ""}
            for c in conditions
        ],
    }


def _cronjob_summary(cj: Any) -> dict:
    status = cj.status or type("S", (), {"last_schedule_time": None})()
    spec = cj.spec or type("S", (), {"schedule": ""})()
    last_schedule = status.last_schedule_time
    return {
        "kind": "CronJob",
        "name": cj.metadata.name,
        "namespace": cj.metadata.namespace or "",
        "schedule": getattr(spec, "schedule", "") or "",
        "last_schedule_time": last_schedule.isoformat() if last_schedule else None,
    }


def _service_summary(svc: Any, ep_map: dict[str, Any]) -> dict:
    spec = svc.spec or type("S", (), {"selector": None, "type": "ClusterIP"})()
    ns = svc.metadata.namespace or ""
    name = svc.metadata.name
    selector = dict(spec.selector) if spec.selector else {}

    ep_key = f"{ns}/{name}"
    ep = ep_map.get(ep_key)
    ready_count = 0
    not_ready_count = 0
    if ep:
        for subset in (ep.subsets or []):
            ready_count += len(subset.addresses or [])
            not_ready_count += len(subset.not_ready_addresses or [])

    return {
        "name": name,
        "namespace": ns,
        "type": getattr(spec, "type", "ClusterIP") or "ClusterIP",
        "selector": selector,
        "ready_endpoints": ready_count,
        "not_ready_endpoints": not_ready_count,
    }


def _daemonset_summary(ds: Any) -> dict:
    status = ds.status or type("S", (), {
        "desired_number_scheduled": 0, "current_number_scheduled": 0,
        "number_ready": 0, "number_unavailable": None,
        "number_misscheduled": 0,
    })()
    return {
        "name": ds.metadata.name,
        "namespace": ds.metadata.namespace or "",
        "desired": status.desired_number_scheduled or 0,
        "current": status.current_number_scheduled or 0,
        "ready": status.number_ready or 0,
        "number_unavailable": getattr(status, "number_unavailable", None) or 0,
        "number_misscheduled": status.number_misscheduled or 0,
    }


# ---------------------------------------------------------------------------
# Skill-aware evidence-gathering helpers
# ---------------------------------------------------------------------------


async def get_pod_logs(
    api_client: ApiClient,
    namespace: str,
    name: str,
    container: str | None = None,
    tail_lines: int = 100,
    previous: bool = False,
) -> str:
    """Fetch pod logs via CoreV1Api.read_namespaced_pod_log."""
    v1 = client.CoreV1Api(api_client)
    try:
        kwargs: dict[str, Any] = {
            "tail_lines": tail_lines,
            "previous": previous,
        }
        if container:
            kwargs["container"] = container
        return await v1.read_namespaced_pod_log(name, namespace, **kwargs)
    except Exception:
        logger.warning("failed to get pod logs for %s/%s (previous=%s)", namespace, name, previous)
        return ""


async def get_top_pods(api_client: ApiClient, namespace: str = "") -> list[dict]:
    """Query metrics.k8s.io/v1beta1 PodMetrics."""
    custom = client.CustomObjectsApi(api_client)
    try:
        if namespace:
            result = await custom.list_namespaced_custom_object(
                group="metrics.k8s.io", version="v1beta1", namespace=namespace, plural="pods",
            )
        else:
            result = await custom.list_cluster_custom_object(
                group="metrics.k8s.io", version="v1beta1", plural="pods",
            )
        return [
            {
                "name": item["metadata"]["name"],
                "namespace": item["metadata"].get("namespace", ""),
                "cpu": item["containers"][0]["usage"]["cpu"] if item.get("containers") else "",
                "memory": item["containers"][0]["usage"]["memory"] if item.get("containers") else "",
            }
            for item in result.get("items", [])
        ]
    except Exception:
        logger.warning("failed to get pod metrics (metrics-server may not be installed)")
        return []


async def get_top_nodes(api_client: ApiClient) -> list[dict]:
    """Query metrics.k8s.io/v1beta1 NodeMetrics."""
    custom = client.CustomObjectsApi(api_client)
    try:
        result = await custom.list_cluster_custom_object(
            group="metrics.k8s.io", version="v1beta1", plural="nodes",
        )
        return [
            {
                "name": item["metadata"]["name"],
                "cpu": item["usage"]["cpu"],
                "memory": item["usage"]["memory"],
            }
            for item in result.get("items", [])
        ]
    except Exception:
        logger.warning("failed to get node metrics (metrics-server may not be installed)")
        return []


async def describe_resource(
    api_client: ApiClient, kind: str, namespace: str, name: str,
) -> dict:
    """Get a resource object and its associated events."""
    v1 = client.CoreV1Api(api_client)
    apps_v1 = client.AppsV1Api(api_client)
    try:
        kind_lower = kind.lower()
        if kind_lower in ("pod", "pods"):
            resource = await v1.read_namespaced_pod(name, namespace)
        elif kind_lower in ("deployment", "deployments"):
            resource = await apps_v1.read_namespaced_deployment(name, namespace)
        elif kind_lower in ("statefulset", "statefulsets"):
            resource = await apps_v1.read_namespaced_stateful_set(name, namespace)
        elif kind_lower in ("daemonset", "daemonsets"):
            resource = await apps_v1.read_namespaced_daemon_set(name, namespace)
        elif kind_lower in ("replicaset", "replicasets"):
            resource = await apps_v1.read_namespaced_replica_set(name, namespace)
        else:
            logger.warning("unsupported resource kind for describe: %s", kind)
            return {}

        events_result = await v1.list_namespaced_event(
            namespace, field_selector=f"involvedObject.name={name}",
        )
        events = [_event_summary(e) for e in events_result.items]

        return {
            "resource": api_client.sanitize_for_serialization(resource),
            "events": events,
        }
    except Exception:
        logger.warning("failed to describe %s %s/%s", kind, namespace, name)
        return {}


async def get_rollout_status(
    api_client: ApiClient, namespace: str, name: str,
) -> dict:
    """Get deployment conditions and replica counts."""
    apps_v1 = client.AppsV1Api(api_client)
    try:
        dep = await apps_v1.read_namespaced_deployment(name, namespace)
        status = dep.status
        conditions = [
            {"type": c.type, "status": c.status, "reason": c.reason or "", "message": c.message or ""}
            for c in (status.conditions or [])
        ] if status else []

        return {
            "conditions": conditions,
            "replicas": status.replicas if status else None,
            "available_replicas": status.available_replicas if status else None,
            "ready_replicas": status.ready_replicas if status else None,
            "updated_replicas": status.updated_replicas if status else None,
        }
    except Exception:
        logger.warning("failed to get rollout status for %s/%s", namespace, name)
        return {}


async def get_helm_releases(
    api_client: ApiClient, namespace: str,
) -> list[dict]:
    """List Helm releases from secrets labelled owner=helm. Does NOT return secret data."""
    v1 = client.CoreV1Api(api_client)
    try:
        result = await v1.list_namespaced_secret(
            namespace, label_selector="owner=helm",
        )
        releases = []
        for secret in result.items:
            labels = secret.metadata.labels or {}
            releases.append({
                "name": labels.get("name", secret.metadata.name),
                "version": labels.get("version", ""),
                "status": labels.get("status", ""),
                "chart": labels.get("chart", ""),
            })
        return releases
    except Exception:
        logger.warning("failed to list helm releases in namespace %s", namespace)
        return []


async def query_prometheus(api_client: ApiClient, query: str) -> list[dict]:
    """Execute a PromQL instant query via Thanos Querier."""
    from pinky_worker.observation.prom_client import PromClient

    prom = PromClient(api_client)
    return await prom.instant_query(query)
