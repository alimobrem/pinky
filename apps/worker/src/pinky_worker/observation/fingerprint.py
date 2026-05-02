"""Stable fingerprinting for observations and correlation keys for issues.

Fingerprints are content-addressable identifiers that do NOT depend on
mutable fields like titles or severity labels.
"""

import hashlib


def compute_observation_fingerprint(
    cluster_id: str,
    scanner: str,
    check_id: str,
    resource_kind: str,
    resource_namespace: str,
    resource_name: str,
) -> str:
    raw = f"{cluster_id}:{scanner}:{check_id}:{resource_kind}:{resource_namespace}:{resource_name}"
    return hashlib.sha256(raw.encode()).hexdigest()


def compute_correlation_key(
    cluster_id: str,
    resource_kind: str,
    resource_namespace: str,
    resource_name: str,
    scanner: str,
    check_id: str,
) -> str:
    raw = f"{cluster_id}:{resource_kind}:{resource_namespace}:{resource_name}:{scanner}:{check_id}"
    return hashlib.sha256(raw.encode()).hexdigest()
