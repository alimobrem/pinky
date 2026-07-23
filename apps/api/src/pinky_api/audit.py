"""Application audit logging for privileged actions and data access."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

_log = logging.getLogger("audit")


def audit_log(
    action: str,
    *,
    actor: str,
    resource: str,
    outcome: str = "success",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Emit a structured audit event (stdout → platform log pipeline)."""
    record = {
        "ts": datetime.now(UTC).isoformat(),
        "type": "audit",
        "action": action,
        "actor": actor,
        "resource": resource,
        "outcome": outcome,
    }
    if metadata:
        record["metadata"] = metadata
    _log.info("%s", json.dumps(record, default=str))
