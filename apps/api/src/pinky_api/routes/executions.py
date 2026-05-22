"""Execution routes — Brain workflows and approval management."""

import json
import logging
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select as sa_select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import (
    principal_uuid,
    require_authenticated,
    require_cluster_read_access,
    require_cluster_write_access,
)
from pinky_api.db.deps import get_db
from pinky_api.events import emit
from pinky_api.models.work_item import WorkItem
from pinky_api.repositories.bindings import BindingRepository
from pinky_api.repositories.executions import ExecutionRepository
from pinky_api.routes._helpers import resolve_cluster_names

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


class ApproveRequest(BaseModel):
    changeset_digest: str = Field(min_length=1)


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1)


async def _update_approval_status(
    db: AsyncSession, execution_id: UUID, status: str, approver_id: UUID,
) -> None:
    from pinky_api.models.execution import Approval
    await db.execute(
        sa_update(Approval)
        .where(Approval.execution_id == execution_id, Approval.status == "pending")
        .values(status=status, approver_id=approver_id)
    )


def _build_oc_command(action: str, kind: str, name: str, namespace: str, params: dict) -> str:
    if action == "scale":
        return f"oc scale {kind} {name} -n {namespace} --replicas={params.get('replicas', 1)}"
    if action == "patch":
        patch = json.dumps(params.get("patch", {}))
        return f"oc patch {kind} {name} -n {namespace} -p '{patch}'"
    if action == "delete_pod":
        return f"oc delete pod {name} -n {namespace}"
    if action == "rollback":
        return f"oc rollout undo {kind}/{name} -n {namespace}"
    return f"oc {action} {kind}/{name} -n {namespace}"


def _parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"{field_name} not found") from exc


def _serialize(ex: Any) -> dict:
    return {
        "id": str(ex.id),
        "work_item_id": str(ex.work_item_id) if ex.work_item_id else None,
        "cluster_id": str(ex.cluster_id),
        "execution_type": ex.execution_type,
        "status": ex.status,
        "started_at": ex.started_at.isoformat() if ex.started_at else None,
        "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
        "created_at": ex.created_at.isoformat() if ex.created_at else "",
    }


async def _resolve_issue_ids(items: list[dict], db: AsyncSession) -> None:
    wi_ids = [UUID(e["work_item_id"]) for e in items if e.get("work_item_id")]
    if not wi_ids:
        return
    result = await db.execute(
        sa_select(WorkItem.id, WorkItem.issue_id).where(WorkItem.id.in_(wi_ids))
    )
    wi_to_issue = {str(row[0]): str(row[1]) if row[1] else None for row in result.all()}
    for item in items:
        item["issue_id"] = wi_to_issue.get(item.get("work_item_id") or "") if item.get("work_item_id") else None


@router.get("")
async def list_executions(
    work_item_id: str | None = None,
    cluster_id: str | None = None,
    status: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    binding_repo = BindingRepository(db)
    allowed_clusters = await binding_repo.list_accessible_cluster_ids(principal_uuid(principal))
    if cluster_id:
        await require_cluster_read_access(_parse_uuid(cluster_id, "Cluster"), principal, db, require_binding=True)
    repo = ExecutionRepository(db)
    result = await repo.list(
        work_item_id=work_item_id, cluster_id=cluster_id, status=status, limit=limit, cursor=cursor,
    )
    items = result["items"]
    if not cluster_id:
        items = [e for e in items if e.cluster_id in allowed_clusters]
    serialized = [_serialize(e) for e in items]
    await _resolve_issue_ids(serialized, db)
    await resolve_cluster_names(serialized, db)
    return {
        "items": serialized,
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
        "total_count": result.get("total_count", len(items)),
    }


@router.get("/{execution_id}")
async def get_execution(
    execution_id: str, db: AsyncSession = Depends(get_db), principal: dict = Depends(require_authenticated),
) -> dict:
    repo = ExecutionRepository(db)
    ex = await repo.get(_parse_uuid(execution_id, "Execution"))
    if ex is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    await require_cluster_read_access(ex.cluster_id, principal, db, require_binding=True)
    serialized = _serialize(ex)
    await resolve_cluster_names([serialized], db)
    if ex.execution_type == "remediation":
        from pinky_api.models.execution import Approval
        approval_result = await db.execute(
            sa_select(Approval).where(Approval.execution_id == ex.id)
            .order_by(Approval.created_at.desc()).limit(1)
        )
        approval = approval_result.scalar_one_or_none()
        if approval:
            serialized["approval_status"] = approval.status
    return serialized


@router.post("")
async def start_execution(
    work_item_id: str | None = None,
    issue_id: str | None = None,
    execution_type: str = "investigation",
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    from pinky_api.temporal_state import get_client

    repo = ExecutionRepository(db)
    plan_steps: list[dict] = []
    binding_id = ""
    approval_id = ""

    from pinky_api.repositories.work_items import WorkItemRepository
    wi_repo = WorkItemRepository(db)

    if work_item_id:
        wi = await wi_repo.get(_parse_uuid(work_item_id, "Work item"))
    elif issue_id:
        result = await db.execute(
            sa_select(WorkItem).where(WorkItem.issue_id == _parse_uuid(issue_id, "Issue"))
        )
        wi = result.scalar_one_or_none()
    else:
        raise HTTPException(status_code=422, detail="work_item_id or issue_id required")

    if wi is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    wi_id = wi.id

    changeset_digest = ""
    target_resources: list[dict] = []

    if execution_type == "remediation":
        await require_cluster_write_access(wi.cluster_id, principal, db)
        refs = wi.artifact_refs if isinstance(wi.artifact_refs, dict) else {}
        raw_plan_steps = refs.get("plan_steps")
        binding_value = refs.get("binding_id")
        approval_value = refs.get("approval_id")
        if not isinstance(raw_plan_steps, list) or not raw_plan_steps:
            raise HTTPException(status_code=409, detail="Remediation plan not available for this task")
        if not isinstance(binding_value, str) or not binding_value:
            raise HTTPException(status_code=409, detail="Cluster binding required before remediation can start")
        if not isinstance(approval_value, str) or not approval_value:
            raise HTTPException(status_code=409, detail="Approval is required before remediation can start")
        plan_steps = cast("list[dict[str, Any]]", raw_plan_steps)
        binding_id = binding_value
        approval_id = approval_value
        changeset_digest = refs.get("changeset_digest", "")
        target_resources = refs.get("target_resources", [])

        from pinky_api.models.execution import Approval
        approval_check = await db.execute(
            sa_select(Approval).where(Approval.id == UUID(approval_id))
        )
        approval_obj = approval_check.scalar_one_or_none()
        if not approval_obj or approval_obj.status not in ("pending", "approved"):
            raise HTTPException(status_code=409, detail="Approval is no longer valid — re-investigate first")
        if approval_obj.expires_at and approval_obj.expires_at < datetime.now(UTC):
            raise HTTPException(status_code=409, detail="Approval has expired — re-investigate first")
    else:
        await require_cluster_read_access(wi.cluster_id, principal, db, require_binding=True)

    existing = await repo.list(
        work_item_id=work_item_id,
        status="pending,running,waiting_for_approval",
        limit=1,
    )
    if existing["items"]:
        same_type = next((e for e in existing["items"] if e.execution_type == execution_type), None)
        if same_type is not None:
            return _serialize(same_type)

    try:
        temporal_client = await get_client()
    except Exception:
        logger.exception("cannot connect to Temporal")
        raise HTTPException(
            status_code=503, detail="Workflow engine unavailable — please try again in a moment",
        ) from None

    ex = await repo.create(work_item_id=wi_id, cluster_id=wi.cluster_id, execution_type=execution_type)
    await emit(db, "execution.started", "execution", ex.id,
               {"type": execution_type, "work_item_id": str(wi.id)},
               cluster_id=wi.cluster_id, principal_id=principal_uuid(principal))
    await db.commit()

    try:
        if execution_type == "remediation":
            await temporal_client.start_workflow(
                "RemediationWorkflow",
                {
                    "execution_id": str(ex.id),
                    "approval_id": approval_id,
                    "cluster_id": str(wi.cluster_id),
                    "binding_id": binding_id,
                    "plan_steps": plan_steps,
                    "changeset_digest": changeset_digest,
                    "target_resources": target_resources,
                },
                id=f"remediation-{ex.id}",
                task_queue="remediation",
            )
        else:
            workflow_input = {
                "issue_id": str(wi.issue_id) if wi.issue_id else str(wi.id),
                "cluster_id": str(wi.cluster_id),
                "correlation_key": str(wi.id),
                "evidence_hash": "",
                "skill_body": "",
                "execution_id": str(ex.id),
            }

            await temporal_client.start_workflow(
                "InvestigationWorkflow",
                workflow_input,
                id=f"investigation-{ex.id}",
                task_queue="investigation",
            )
        logger.info("temporal workflow started for execution %s", str(ex.id))
    except Exception:
        logger.exception("failed to start temporal workflow for execution %s", str(ex.id))
        await repo.update_status(ex.id, "failed")
        await db.commit()
        raise HTTPException(status_code=502, detail="Failed to start investigation workflow") from None

    return _serialize(ex)


@router.get("/{execution_id}/approval")
async def get_execution_approval(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    repo = ExecutionRepository(db)
    ex = await repo.get(_parse_uuid(execution_id, "Execution"))
    if ex is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    await require_cluster_read_access(ex.cluster_id, principal, db, require_binding=True)

    from pinky_api.models.execution import Approval
    result = await db.execute(
        sa_select(Approval).where(Approval.execution_id == ex.id).order_by(Approval.created_at.desc()).limit(1)
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        return {"approval": None}
    return {
        "approval": {
            "id": str(approval.id),
            "status": approval.status,
            "target_resources": approval.target_resources,
            "changeset_digest": approval.changeset_digest,
            "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
        }
    }


@router.get("/{execution_id}/preview")
async def preview_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    from pinky_api.k8s import apply_resource

    repo = ExecutionRepository(db)
    ex = await repo.get(_parse_uuid(execution_id, "Execution"))
    if ex is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    await require_cluster_write_access(ex.cluster_id, principal, db)

    from pinky_api.repositories.work_items import WorkItemRepository
    wi_repo = WorkItemRepository(db)
    wi = await wi_repo.get(ex.work_item_id) if ex.work_item_id else None
    if not wi or not isinstance(wi.artifact_refs, dict):
        raise HTTPException(status_code=409, detail="No remediation plan available")

    plan_steps = wi.artifact_refs.get("plan_steps", [])
    if not plan_steps:
        raise HTTPException(status_code=409, detail="No remediation steps")

    from pinky_api.repositories.clusters import ClusterRepository
    from pinky_api.security.crypto import decrypt

    binding_id = wi.artifact_refs.get("binding_id")
    if not binding_id:
        raise HTTPException(status_code=409, detail="No cluster binding in remediation plan")
    from pinky_api.models.fleet import ClusterIdentityBinding
    binding_result = await db.execute(
        sa_select(ClusterIdentityBinding).where(ClusterIdentityBinding.id == _parse_uuid(binding_id, "Binding"))
    )
    binding = binding_result.scalar_one_or_none()
    if not binding or not binding.encrypted_token:
        raise HTTPException(status_code=409, detail="Stored cluster binding no longer valid")
    cluster_repo = ClusterRepository(db)
    cluster = await cluster_repo.get(ex.cluster_id)
    api_endpoint = cluster.api_endpoint if cluster else ""
    try:
        token = decrypt(
            binding.encrypted_token,
            aad=f"cluster_identity_bindings:{binding.id}",
        ).decode()
    except Exception:
        raise HTTPException(status_code=500, detail="Token decryption failed") from None

    results = []
    for i, step in enumerate(plan_steps):
        kind = step.get("resource_kind", "deployment")
        name = step.get("resource_name", "")
        ns = step.get("namespace", step.get("resource_namespace", "default"))
        action = step.get("action", "patch")
        params = step.get("params", {})

        cmd = _build_oc_command(action, kind, name, ns, params)
        entry: dict[str, object] = {
            "index": i,
            "command": cmd,
            "action": action,
            "resource": f"{kind}/{name}",
            "namespace": ns,
        }

        if action == "patch" and params.get("patch"):
            try:
                result = await apply_resource(
                    api_endpoint, token, ns, kind, name,
                    params["patch"], dry_run=True,
                )
                if "error" in result:
                    entry["status"] = "error"
                    entry["error"] = result.get("message", result.get("error", ""))
                else:
                    entry["status"] = "ok"
            except Exception as e:
                entry["status"] = "error"
                entry["error"] = str(e)
        else:
            entry["status"] = "ok"

        results.append(entry)

    return {"steps": results}


@router.post("/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    from pinky_api.temporal_state import get_client

    repo = ExecutionRepository(db)
    ex = await repo.get(_parse_uuid(execution_id, "Execution"))
    if ex is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    await require_cluster_write_access(ex.cluster_id, principal, db)

    if ex.status not in ("pending", "running", "waiting_for_approval"):
        raise HTTPException(status_code=409, detail=f"Cannot cancel execution in '{ex.status}' state")

    await repo.update_status(ex.id, "cancelled")
    await emit(db, "execution.cancelled", "execution", ex.id, {},
               cluster_id=ex.cluster_id, principal_id=principal_uuid(principal))
    await db.commit()

    workflow_id = f"{ex.execution_type}-{execution_id}"
    try:
        temporal_client = await get_client()
        handle = temporal_client.get_workflow_handle(workflow_id)
        await handle.cancel()
    except Exception:
        logger.warning("could not cancel Temporal workflow %s (may have already finished)", workflow_id)

    return {"status": "cancelled", "execution_id": execution_id}


@router.post("/{execution_id}/approve")
async def approve_execution(
    execution_id: str, req: ApproveRequest,
    db: AsyncSession = Depends(get_db), principal: dict = Depends(require_authenticated),
) -> dict:
    from pinky_api.temporal_state import get_client

    repo = ExecutionRepository(db)
    ex = await repo.get(_parse_uuid(execution_id, "Execution"))
    if ex is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    await require_cluster_write_access(ex.cluster_id, principal, db)
    if ex.execution_type != "remediation":
        raise HTTPException(status_code=409, detail="Only remediation executions require approval")
    if ex.status != "waiting_for_approval":
        raise HTTPException(status_code=409, detail=f"Execution is {ex.status} — approval no longer applicable")

    try:
        temporal_client = await get_client()
    except Exception:
        logger.exception("temporal client unavailable for approval")
        raise HTTPException(status_code=503, detail="Workflow engine unavailable") from None

    await _update_approval_status(db, ex.id, "approved", principal_uuid(principal))
    await emit(
        db, "approval.granted", "execution", ex.id,
        {"changeset_digest": req.changeset_digest},
        cluster_id=ex.cluster_id, principal_id=principal_uuid(principal),
    )
    from pinky_api.repositories.analytics import AnalyticsRepository
    analytics = AnalyticsRepository(db)
    await analytics.record(
        "approval_decided",
        {"decision": "approved", "execution_id": str(ex.id)},
        execution_id=ex.id,
    )
    await db.flush()

    try:
        handle = temporal_client.get_workflow_handle(f"remediation-{execution_id}")
        await handle.signal("approve", {"changeset_digest": req.changeset_digest})
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("failed to signal approval for %s", execution_id)
        raise HTTPException(status_code=503, detail="Failed to deliver approval to workflow engine") from None

    return {"status": "approved", "execution_id": execution_id}


@router.post("/{execution_id}/reject")
async def reject_execution(
    execution_id: str, req: RejectRequest,
    db: AsyncSession = Depends(get_db), principal: dict = Depends(require_authenticated),
) -> dict:
    from pinky_api.temporal_state import get_client

    repo = ExecutionRepository(db)
    ex = await repo.get(_parse_uuid(execution_id, "Execution"))
    if ex is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    await require_cluster_write_access(ex.cluster_id, principal, db)
    if ex.execution_type != "remediation":
        raise HTTPException(status_code=409, detail="Only remediation executions require approval")
    if ex.status != "waiting_for_approval":
        raise HTTPException(status_code=409, detail=f"Execution is {ex.status} — rejection no longer applicable")

    try:
        temporal_client = await get_client()
    except Exception:
        logger.exception("temporal client unavailable for rejection")
        raise HTTPException(status_code=503, detail="Workflow engine unavailable") from None

    await _update_approval_status(db, ex.id, "rejected", principal_uuid(principal))
    await emit(
        db, "approval.rejected", "execution", ex.id,
        {"reason": req.reason},
        cluster_id=ex.cluster_id, principal_id=principal_uuid(principal),
    )
    from pinky_api.repositories.analytics import AnalyticsRepository
    analytics = AnalyticsRepository(db)
    await analytics.record(
        "approval_decided",
        {"decision": "rejected", "execution_id": str(ex.id), "reason": req.reason},
        execution_id=ex.id,
    )
    await db.flush()

    try:
        handle = temporal_client.get_workflow_handle(f"remediation-{execution_id}")
        await handle.signal("reject", {"reason": req.reason})
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("failed to signal rejection for %s", execution_id)
        raise HTTPException(status_code=503, detail="Failed to deliver rejection to workflow engine") from None

    return {"status": "rejected", "execution_id": execution_id}
