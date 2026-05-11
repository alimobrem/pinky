"""Generic scanner executor — runs declarative check definitions against resources.

Replaces hardcoded scanner runner functions with a data-driven engine.
Scanner definitions declare checks in YAML frontmatter; this module
evaluates those checks against K8s resource dicts and produces
RawObservations.
"""

from __future__ import annotations

import base64
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from pinky_worker.definitions.loader import Definition
from pinky_worker.issues.correlator import RawObservation
from pinky_worker.observation.fingerprint import (
    compute_correlation_key,
    compute_observation_fingerprint,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Operator-managed detection & age filtering
# ---------------------------------------------------------------------------

_OLM_OWNER_KINDS = {"ClusterServiceVersion", "OperatorGroup", "Subscription"}
_OLM_LABEL_PREFIX = "operators.coreos.com/"
MIN_RESOURCE_AGE_SECONDS = int(os.environ.get("PINKY_MIN_RESOURCE_AGE_SECONDS", "300"))


def is_operator_managed(resource: dict) -> bool:
    metadata = resource.get("metadata", {})
    labels = metadata.get("labels", {})
    owner_refs = metadata.get("owner_references", [])
    if any(k.startswith(_OLM_LABEL_PREFIX) for k in labels):
        return True
    if labels.get("app.kubernetes.io/managed-by", "").lower() == "operator-lifecycle-manager":
        return True
    return any(ref.get("kind") in _OLM_OWNER_KINDS for ref in owner_refs)


def has_scan_override(resource: dict, scanner_name: str) -> bool:
    metadata = resource.get("metadata", {})
    labels = metadata.get("labels", {})
    override = labels.get("pinky.io/scan-override", "")
    if not override:
        return False
    return override == "all" or scanner_name in override.split(",")


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_WILDCARD_RE = re.compile(r"^([^\[]+)\[\*\]$")
_FILTER_RE = re.compile(r"^([^\[]+)\[([^=]+)=([^\]]+)\]$")


def resolve_path(resource: dict[str, Any], path: str) -> Any:
    """Walk a dot-separated path through a dict.

    Special syntax:
      containers[*].state.reason  → list of values from each element
      conditions[type=Ready].status → filter list element then access field
      spec.replicas → plain nested access
    """
    try:
        return _resolve_path_inner(resource, path.split("."), 0)
    except Exception:
        return None


def _resolve_path_inner(current: Any, segments: list[str], idx: int) -> Any:
    if idx >= len(segments):
        return current
    if current is None:
        return None

    segment = segments[idx]

    # [*] wildcard — iterate list
    wm = _WILDCARD_RE.match(segment)
    if wm:
        key = wm.group(1)
        lst = current.get(key) if isinstance(current, dict) else None
        if not isinstance(lst, list):
            return None
        remaining = segments[idx + 1 :]
        results = []
        for item in lst:
            val = _resolve_path_inner(item, remaining, 0) if remaining else item
            results.append(val)
        return results

    # [key=value] filter
    fm = _FILTER_RE.match(segment)
    if fm:
        key = fm.group(1)
        filter_key = fm.group(2)
        filter_val = fm.group(3)
        lst = current.get(key) if isinstance(current, dict) else None
        if not isinstance(lst, list):
            return None
        for item in lst:
            if isinstance(item, dict) and str(item.get(filter_key, "")) == filter_val:
                return _resolve_path_inner(item, segments, idx + 1)
        return None

    # Plain dict access
    if isinstance(current, dict):
        return _resolve_path_inner(current.get(segment), segments, idx + 1)

    return None


# ---------------------------------------------------------------------------
# Duration / quantity parsing
# ---------------------------------------------------------------------------

_DURATION_RE = re.compile(r"^(\d+(?:\.\d+)?)(s|m|h|d)$")


def parse_duration(s: str) -> timedelta:
    """Parse simple duration strings: 30s, 5m, 1h, 7d."""
    m = _DURATION_RE.match(s.strip())
    if not m:
        raise ValueError(f"Invalid duration: {s!r}")
    val = float(m.group(1))
    unit = m.group(2)
    if unit == "s":
        return timedelta(seconds=val)
    if unit == "m":
        return timedelta(minutes=val)
    if unit == "h":
        return timedelta(hours=val)
    if unit == "d":
        return timedelta(days=val)
    raise ValueError(f"Unknown duration unit: {unit}")


_QUANTITY_SUFFIXES: list[tuple[str, float]] = [
    ("Ki", 1024.0),
    ("Mi", 1024.0**2),
    ("Gi", 1024.0**3),
    ("Ti", 1024.0**4),
    ("m", 0.001),
    ("k", 1000.0),
    ("M", 1_000_000.0),
    ("G", 1_000_000_000.0),
]


def parse_k8s_quantity(s: str) -> float:
    """Parse K8s resource quantity strings to float."""
    s = str(s).strip()
    # Longest suffix first (Ki before k, Mi before M, etc.)
    for suffix, multiplier in _QUANTITY_SUFFIXES:
        if s.endswith(suffix):
            return float(s[: -len(suffix)]) * multiplier
    return float(s)


# ---------------------------------------------------------------------------
# x509 cert parsing
# ---------------------------------------------------------------------------


def parse_x509_not_after(cert_b64: str) -> datetime | None:
    """Decode base64 PEM cert and return notAfter as datetime."""
    try:
        pem_data = base64.b64decode(cert_b64)
    except Exception:
        logger.warning("failed to base64-decode cert data")
        return None

    # Try cryptography lib first
    try:
        from cryptography.x509 import load_pem_x509_certificate

        cert = load_pem_x509_certificate(pem_data)
        return cert.not_valid_after_utc
    except ImportError:
        pass
    except Exception:
        logger.warning("failed to parse x509 cert", exc_info=True)

    return None


# ---------------------------------------------------------------------------
# Operator evaluation
# ---------------------------------------------------------------------------


def _to_float(v: Any) -> float:
    return float(v)


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {} or value == 0


async def evaluate_op(
    value: Any,
    op: str,
    condition: dict[str, Any],
    now: datetime,
    resource: dict[str, Any],
    prom_client: Any = None,
) -> bool:
    """Apply an operator to a resolved value. List values use any() semantics."""
    try:
        # Unwrap list values — any() semantics
        if isinstance(value, list) and op not in ("condition_status",):
            for v in value:
                if await evaluate_op(v, op, condition, now, resource, prom_client):
                    return True
            return False

        cmp_value = condition.get("value")
        if "value_from" in condition:
            cmp_value = resolve_path(resource, condition["value_from"])
            if cmp_value is None:
                return False

        if op == "eq":
            return value == cmp_value
        if op == "neq":
            return value != cmp_value
        if op == "gt":
            return _to_float(value) > _to_float(cmp_value)
        if op == "gte":
            return _to_float(value) >= _to_float(cmp_value)
        if op == "lt":
            return _to_float(value) < _to_float(cmp_value)
        if op == "lte":
            return _to_float(value) <= _to_float(cmp_value)
        if op == "in":
            return cmp_value is not None and value in cmp_value
        if op == "is_empty":
            return _is_empty(value)
        if op == "is_set":
            return value is not None and value != "" and value != [] and value != {}
        if op == "is_true":
            return value is True or value == "True"
        if op == "is_false":
            return value is not True and value != "True"
        if op == "contains":
            return str(condition["value"]) in str(value)
        if op == "condition_status":
            return _eval_condition_status(value, condition)
        if op == "age_gt":
            return _eval_age_gt(value, condition, now)
        if op == "cert_expires_within":
            return _eval_cert_expires_within(value, condition, now)
        if op == "cert_expired":
            return _eval_cert_expired(value, now)
        if op == "quantity_gte":
            return _eval_quantity_gte(condition, resource)
        if op == "quantity_gte_pct":
            return _eval_quantity_gte_pct(condition, resource)
        if op in ("promql_gt", "promql_lt", "promql_eq"):
            return await _eval_promql_compare(op, condition, resource, prom_client)
        if op == "promql_absent":
            return await _eval_promql_absent(condition, resource, prom_client)

        logger.warning("unknown operator", op=op)
        return False
    except Exception:
        logger.warning("evaluate_op failed", op=op, exc_info=True)
        return False


def _eval_condition_status(value: Any, condition: dict[str, Any]) -> bool:
    """Value is a list of K8s condition dicts. Find matching type, check status."""
    if not isinstance(value, list):
        return False
    target_type = condition.get("type", "")
    target_status = condition.get("status", "")
    for cond in value:
        if isinstance(cond, dict) and cond.get("type") == target_type:
            return cond.get("status") == target_status
    return False


def _eval_age_gt(value: Any, condition: dict[str, Any], now: datetime) -> bool:
    if value is None:
        return False
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        threshold = parse_duration(condition["value"])
        return (now - dt) > threshold
    except Exception:
        logger.warning("age_gt parse failed", value=value)
        return False


def _eval_cert_expires_within(value: Any, condition: dict[str, Any], now: datetime) -> bool:
    not_after = parse_x509_not_after(str(value)) if value else None
    if not_after is None:
        return False
    try:
        window = parse_duration(condition["value"])
        return not_after < (now + window)
    except Exception:
        return False


def _eval_cert_expired(value: Any, now: datetime) -> bool:
    not_after = parse_x509_not_after(str(value)) if value else None
    if not_after is None:
        return False
    return not_after < now


def _eval_quantity_gte(condition: dict[str, Any], resource: dict[str, Any]) -> bool:
    used_raw = resolve_path(resource, condition["used_path"])
    hard_raw = resolve_path(resource, condition["hard_path"])
    if used_raw is None or hard_raw is None:
        return False
    try:
        used = parse_k8s_quantity(str(used_raw))
        hard = parse_k8s_quantity(str(hard_raw))
        return used >= hard
    except (ValueError, TypeError):
        return False


def _eval_quantity_gte_pct(condition: dict[str, Any], resource: dict[str, Any]) -> bool:
    used_raw = resolve_path(resource, condition["used_path"])
    hard_raw = resolve_path(resource, condition["hard_path"])
    if used_raw is None or hard_raw is None:
        return False
    try:
        used = parse_k8s_quantity(str(used_raw))
        hard = parse_k8s_quantity(str(hard_raw))
        if hard <= 0:
            return False
        pct = condition.get("pct", 100)
        return (used / hard) >= (pct / 100)
    except (ValueError, TypeError):
        return False


def _interpolate_promql(query: str, resource: dict[str, Any]) -> str:
    ns = resource.get("namespace", "")
    name = resource.get("name", "")
    return query.replace("{namespace}", ns).replace("{name}", name)


async def _eval_promql_compare(
    op: str,
    condition: dict[str, Any],
    resource: dict[str, Any],
    prom_client: Any,
) -> bool:
    if prom_client is None:
        return False
    try:
        query = _interpolate_promql(condition["query"], resource)
        result = await prom_client.query_value(query)
        if result is None:
            return False
        result_f = float(result)
        cmp_val = float(condition["value"])
        if op == "promql_gt":
            return result_f > cmp_val
        if op == "promql_lt":
            return result_f < cmp_val
        if op == "promql_eq":
            return result_f == cmp_val
    except Exception:
        logger.warning("promql compare failed", op=op, exc_info=True)
    return False


async def _eval_promql_absent(
    condition: dict[str, Any],
    resource: dict[str, Any],
    prom_client: Any,
) -> bool:
    if prom_client is None:
        return False
    try:
        query = _interpolate_promql(condition["query"], resource)
        result = await prom_client.query_value(query)
        return result is None
    except Exception:
        logger.warning("promql_absent failed", exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Condition evaluation (composite + single)
# ---------------------------------------------------------------------------


async def evaluate_condition(
    resource: dict[str, Any],
    condition: dict[str, Any],
    now: datetime,
    prom_client: Any = None,
) -> bool:
    """Evaluate a condition tree against a resource.

    Three forms:
      {"all": [...]}  → all sub-conditions must match
      {"any": [...]}  → any sub-condition must match
      {"path": ..., "op": ..., ...} → single leaf condition
    """
    try:
        if "all" in condition:
            for c in condition["all"]:
                if not await evaluate_condition(resource, c, now, prom_client):
                    return False
            return True
        if "any" in condition:
            for c in condition["any"]:
                if await evaluate_condition(resource, c, now, prom_client):
                    return True
            return False
        # Leaf condition
        path = condition.get("path", "")
        op = condition.get("op", "")
        if not op:
            logger.warning("condition missing 'op'", condition=condition)
            return False
        value = resolve_path(resource, path) if path else None
        return await evaluate_op(value, op, condition, now, resource, prom_client)
    except Exception:
        logger.warning("evaluate_condition failed", exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def run_generic_checks(
    resources: list[dict[str, Any]],
    cluster_id: str,
    scanner_def: Definition,
    prom_client: Any = None,
) -> list[RawObservation]:
    """Run all checks from a scanner definition against a list of resources."""
    checks = scanner_def.frontmatter.get("checks", [])
    if not checks:
        return []

    observations: list[RawObservation] = []
    now = datetime.now(UTC)
    scanner_name = scanner_def.name
    default_kind = scanner_def.frontmatter.get("resource_kinds", ["Unknown"])[0]

    for resource in resources:
        for check in checks:
            try:
                await _run_single_check(
                    resource=resource,
                    check=check,
                    cluster_id=cluster_id,
                    scanner_name=scanner_name,
                    scanner_def=scanner_def,
                    default_kind=default_kind,
                    now=now,
                    prom_client=prom_client,
                    observations=observations,
                )
            except Exception:
                logger.warning(
                    "check evaluation failed",
                    scanner=scanner_name,
                    check_id=check.get("id", "?"),
                    resource=f"{resource.get('namespace', '')}/{resource.get('name', '')}",
                    exc_info=True,
                )

    return observations


async def _run_single_check(
    resource: dict[str, Any],
    check: dict[str, Any],
    cluster_id: str,
    scanner_name: str,
    scanner_def: Definition,
    default_kind: str,
    now: datetime,
    prom_client: Any,
    observations: list[RawObservation],
) -> None:
    check_id: str = check.get("id", "unknown")
    severity: str = check.get("severity", "medium")
    resource_kind: str = check.get("resource_kind") or resource.get("kind") or default_kind
    condition = check.get("condition", {})
    iterate_path: str | None = check.get("iterate")

    ns = resource.get("namespace", "")
    name = resource.get("name", "")

    # --- Pre-emission filters ---
    # Skip resources younger than minimum age threshold
    created_at_str = resource.get("created_at") or resource.get("metadata", {}).get("created_at")
    if created_at_str:
        try:
            created_dt = datetime.fromisoformat(str(created_at_str).replace("Z", "+00:00"))
            age = (now - created_dt).total_seconds()
            if age < MIN_RESOURCE_AGE_SECONDS:
                return
        except (ValueError, TypeError):
            pass

    # Skip completed (Succeeded) pods for pod-health scanner
    if scanner_name == "pod-health" and resource.get("phase") == "Succeeded":
        return

    # Detect operator-managed status
    op_managed = is_operator_managed(resource)
    scan_override = has_scan_override(resource, scanner_name)

    if iterate_path:
        elements = resolve_path(resource, iterate_path)
        if not isinstance(elements, list):
            return
        for element in elements:
            if not isinstance(element, dict):
                continue
            if await evaluate_condition(element, condition, now, prom_client):
                _emit_observation(
                    resource=resource,
                    element=element,
                    check=check,
                    check_id=check_id,
                    severity=severity,
                    resource_kind=resource_kind,
                    cluster_id=cluster_id,
                    scanner_name=scanner_name,
                    scanner_def=scanner_def,
                    ns=ns,
                    name=name,
                    now=now,
                    observations=observations,
                    operator_managed=op_managed and not scan_override,
                )
    else:
        if await evaluate_condition(resource, condition, now, prom_client):
            _emit_observation(
                resource=resource,
                element=None,
                check=check,
                check_id=check_id,
                severity=severity,
                resource_kind=resource_kind,
                cluster_id=cluster_id,
                scanner_name=scanner_name,
                scanner_def=scanner_def,
                ns=ns,
                name=name,
                now=now,
                observations=observations,
                operator_managed=op_managed and not scan_override,
            )


def _emit_observation(
    resource: dict[str, Any],
    element: dict[str, Any] | None,
    check: dict[str, Any],
    check_id: str,
    severity: str,
    resource_kind: str,
    cluster_id: str,
    scanner_name: str,
    scanner_def: Definition,
    ns: str,
    name: str,
    now: datetime,
    observations: list[RawObservation],
    operator_managed: bool = False,
) -> None:
    # Build title
    title_template = check.get("title_template", "")
    title = _format_title(title_template, resource, element, check_id, ns, name)

    # Build payload
    payload = _build_payload(check.get("payload_fields", []), resource, element)
    if operator_managed:
        payload["operator_managed"] = True

    # Resource metadata for blast radius / managed-by display
    metadata = resource.get("metadata", {})
    payload["managed_by"] = metadata.get("labels", {}).get("app.kubernetes.io/managed-by", "")
    payload["owner_references"] = metadata.get("owner_references", [])
    payload["replica_count"] = resource.get("desired_replicas") or resource.get("replicas")
    payload["ready_replicas"] = resource.get("ready_replicas")

    fp = compute_observation_fingerprint(
        cluster_id, scanner_name, check_id, resource_kind, ns, name,
    )
    ck = compute_correlation_key(
        cluster_id, resource_kind, ns, name, scanner_name, check_id,
    )

    observations.append(
        RawObservation(
            cluster_id=cluster_id,
            scanner=scanner_name,
            scanner_version=scanner_def.version,
            check_id=check_id,
            severity=severity,
            resource_kind=resource_kind,
            resource_namespace=ns,
            resource_name=name,
            title=title,
            payload=payload,
            observed_at=now,
            fingerprint=fp,
            correlation_key=ck,
        )
    )


def _format_title(
    template: str,
    resource: dict[str, Any],
    element: dict[str, Any] | None,
    check_id: str,
    ns: str,
    name: str,
) -> str:
    if not template:
        if ns:
            return f"{check_id}: {ns}/{name}"
        return f"{check_id}: {name}"
    try:
        fmt_vars: dict[str, Any] = {**resource}
        if element is not None:
            fmt_vars["element"] = element
        else:
            fmt_vars.setdefault("element", {})
        return template.format(**fmt_vars)
    except Exception:
        logger.warning("title_template format failed", template=template)
        if ns:
            return f"{check_id}: {ns}/{name}"
        return f"{check_id}: {name}"


def _build_payload(
    payload_fields: list[str],
    resource: dict[str, Any],
    element: dict[str, Any] | None,
) -> dict[str, Any]:
    if not payload_fields:
        return {}
    payload: dict[str, Any] = {}
    target = element if element is not None else resource
    for field_path in payload_fields:
        try:
            key = field_path.rsplit(".", 1)[-1]
            value = resolve_path(target, field_path)
            if value is None:
                # Fall back to resource-level if element didn't have it
                value = resolve_path(resource, field_path)
            payload[key] = value
        except Exception:
            payload[field_path] = None
    return payload
