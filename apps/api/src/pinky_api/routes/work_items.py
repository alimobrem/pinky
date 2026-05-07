"""Work item routes — the core task-first API."""

import logging
import re
from typing import Any
from uuid import UUID

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import (
    get_cluster_binding_for_principal,
    principal_uuid,
    require_authenticated,
    require_cluster_read_access,
    require_cluster_write_access,
)
from pinky_api.db.deps import get_db
from pinky_api.events import emit
from pinky_api.repositories.bindings import BindingRepository
from pinky_api.repositories.work_items import WorkItemRepository

logger = logging.getLogger(__name__)


class CreateWorkItemRequest(BaseModel):
    cluster_id: str
    title: str
    why_now: str | None = None
    recommended_next_step: str | None = None
    priority: str = "medium"
    runbook_url: str | None = None
    labels: dict = {}


class BlockRequest(BaseModel):
    reason: str

router = APIRouter(prefix="/api/v1/work-items", tags=["work-items"])


def _serialize(item: Any) -> dict:
    return {
        "id": str(item.id),
        "issue_id": str(item.issue_id) if item.issue_id else None,
        "cluster_id": str(item.cluster_id),
        "title": item.title,
        "why_now": item.why_now,
        "recommended_next_step": item.recommended_next_step,
        "status": item.status,
        "owner_id": str(item.owner_id) if item.owner_id else None,
        "owner_display_name": item.owner.display_name if item.owner else None,
        "confidence": item.confidence,
        "priority": item.priority,
        "labels": item.labels or {},
        "annotations": item.annotations or {},
        "runbook_url": item.runbook_url,
        "artifact_refs": item.artifact_refs or {},
        "blocked_reason": item.blocked_reason,
        "created_at": item.created_at.isoformat() if item.created_at else "",
        "updated_at": item.updated_at.isoformat() if item.updated_at else "",
    }


@router.get("")
async def list_work_items(
    cluster_id: str | None = None,
    status: str | None = None,
    owner: str | None = None,
    priority: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    binding_repo = BindingRepository(db)
    allowed_clusters = await binding_repo.list_accessible_cluster_ids(principal_uuid(principal))
    if cluster_id:
        await require_cluster_read_access(UUID(cluster_id), principal, db, require_binding=True)
    repo = WorkItemRepository(db)
    result = await repo.list(
        cluster_id=cluster_id, cluster_ids=None if cluster_id else allowed_clusters, status=status, owner_id=owner,
        priority=priority, limit=limit, cursor=cursor,
    )
    return {
        "items": [_serialize(i) for i in result["items"]],
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
        "total_count": result.get("total_count", len(result["items"])),
    }


@router.post("")
async def create_work_item(
    req: CreateWorkItemRequest,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    cluster_uuid = UUID(req.cluster_id)
    await require_cluster_write_access(cluster_uuid, principal, db)
    repo = WorkItemRepository(db)
    item = await repo.create(
        cluster_id=cluster_uuid,
        title=req.title,
        why_now=req.why_now,
        recommended_next_step=req.recommended_next_step,
        status="ready",
        confidence=1.0,
        priority=req.priority,
        runbook_url=req.runbook_url,
        labels=req.labels,
    )
    await emit(db, "work_item.created", "work_item", item.id, {"status": "ready"})
    await db.commit()
    return _serialize(item)


@router.get("/{work_item_id}")
async def get_work_item(
    work_item_id: str, db: AsyncSession = Depends(get_db), principal: dict = Depends(require_authenticated),
) -> dict:
    repo = WorkItemRepository(db)
    item = await repo.get(UUID(work_item_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await require_cluster_read_access(item.cluster_id, principal, db, require_binding=True)
    return _serialize(item)


@router.post("/{work_item_id}/start")
async def start_work_item(
    work_item_id: str, db: AsyncSession = Depends(get_db), _principal: dict = Depends(require_authenticated),
) -> dict:
    repo = WorkItemRepository(db)
    current = await repo.get(UUID(work_item_id))
    if current is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await require_cluster_write_access(current.cluster_id, _principal, db)
    try:
        item = await repo.transition(UUID(work_item_id), "in_progress")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await emit(db, "work_item.started", "work_item", UUID(work_item_id), {"status": "in_progress"})
    await db.commit()
    return _serialize(item)


@router.post("/{work_item_id}/complete")
async def complete_work_item(
    work_item_id: str, db: AsyncSession = Depends(get_db), _principal: dict = Depends(require_authenticated),
) -> dict:
    repo = WorkItemRepository(db)
    current = await repo.get(UUID(work_item_id))
    if current is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await require_cluster_write_access(current.cluster_id, _principal, db)
    try:
        item = await repo.transition(UUID(work_item_id), "done")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await emit(db, "work_item.completed", "work_item", UUID(work_item_id), {"status": "done"})
    await db.commit()
    return _serialize(item)


@router.post("/{work_item_id}/block")
async def block_work_item(
    work_item_id: str,
    req: BlockRequest,
    db: AsyncSession = Depends(get_db),
    _principal: dict = Depends(require_authenticated),
) -> dict:
    repo = WorkItemRepository(db)
    current = await repo.get(UUID(work_item_id))
    if current is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await require_cluster_write_access(current.cluster_id, _principal, db)
    try:
        item = await repo.transition(UUID(work_item_id), "blocked", blocked_reason=req.reason)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await emit(db, "work_item.blocked", "work_item", UUID(work_item_id), {"status": "blocked", "reason": req.reason})
    await db.commit()
    return _serialize(item)


@router.post("/{work_item_id}/reassign")
async def reassign_work_item(
    work_item_id: str,
    assignee_id: str,
    db: AsyncSession = Depends(get_db),
    _principal: dict = Depends(require_authenticated),
) -> dict:
    repo = WorkItemRepository(db)
    current = await repo.get(UUID(work_item_id))
    if current is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await require_cluster_write_access(current.cluster_id, _principal, db)
    item = await repo.reassign(UUID(work_item_id), UUID(assignee_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await db.commit()
    return _serialize(item)


@router.post("/{work_item_id}/take")
async def take_work_item(
    work_item_id: str,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    repo = WorkItemRepository(db)
    current = await repo.get(UUID(work_item_id))
    if current is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await require_cluster_write_access(current.cluster_id, principal, db)
    if current.owner_id is not None and current.owner_id != principal_uuid(principal):
        raise HTTPException(status_code=409, detail="Task already taken")
    await repo.reassign(UUID(work_item_id), principal_uuid(principal))
    if current.status == "ready":
        try:
            item = await repo.transition(UUID(work_item_id), "in_progress")
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from None
    else:
        item = await repo.get(UUID(work_item_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await emit(db, "work_item.taken", "work_item", UUID(work_item_id), {"status": item.status})
    await db.commit()
    return _serialize(item)


@router.post("/{work_item_id}/release")
async def release_work_item(
    work_item_id: str,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    repo = WorkItemRepository(db)
    current = await repo.get(UUID(work_item_id))
    if current is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await require_cluster_write_access(current.cluster_id, principal, db)
    if current.status not in ("in_progress", "blocked"):
        raise HTTPException(status_code=409, detail=f"Cannot release from {current.status}")
    try:
        item = await repo.transition(UUID(work_item_id), "ready")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await repo.unassign(UUID(work_item_id))
    item = await repo.get(UUID(work_item_id))
    await emit(db, "work_item.released", "work_item", UUID(work_item_id), {"status": "ready"})
    await db.commit()
    return _serialize(item)


class BulkActionRequest(BaseModel):
    ids: list[str]
    action: str


@router.post("/bulk")
async def bulk_action(
    req: BulkActionRequest,
    db: AsyncSession = Depends(get_db),
    _principal: dict = Depends(require_authenticated),
) -> dict:
    repo = WorkItemRepository(db)
    results: list[dict] = []
    for item_id in req.ids:
        try:
            item = await repo.transition(UUID(item_id), req.action)
            if item:
                await emit(db, f"work_item.{req.action}", "work_item", UUID(item_id), {"status": req.action})
                results.append({"id": item_id, "status": "ok"})
            else:
                results.append({"id": item_id, "status": "not_found"})
        except ValueError as e:
            results.append({"id": item_id, "status": "error", "detail": str(e)})
    await db.commit()
    return {"results": results}


class AnnotationsUpdateRequest(BaseModel):
    annotations: dict[str, str]


@router.patch("/{work_item_id}/annotations")
async def update_annotations(
    work_item_id: str,
    req: AnnotationsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _principal: dict = Depends(require_authenticated),
) -> dict:
    from sqlalchemy import update as sa_update

    from pinky_api.models.work_item import WorkItem

    repo = WorkItemRepository(db)
    item = await repo.get(UUID(work_item_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")

    merged = {**(item.annotations or {}), **req.annotations}
    await db.execute(sa_update(WorkItem).where(WorkItem.id == UUID(work_item_id)).values(annotations=merged))
    await db.commit()
    db.expire_all()
    updated = await repo.get(UUID(work_item_id))
    return _serialize(updated)


@router.get("/{work_item_id}/events")
async def get_work_item_events(
    work_item_id: str, db: AsyncSession = Depends(get_db), principal: dict = Depends(require_authenticated),
) -> dict:
    work_item_repo = WorkItemRepository(db)
    item = await work_item_repo.get(UUID(work_item_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await require_cluster_read_access(item.cluster_id, principal, db, require_binding=True)
    from pinky_api.repositories.executions import ExecutionRepository
    repo = ExecutionRepository(db)
    events = await repo.get_events_for_work_item(UUID(work_item_id))
    return {
        "items": [
            {
                "id": str(e.id),
                "execution_id": str(e.execution_id),
                "event_type": e.event_type,
                "sequence": e.sequence,
                "payload": e.payload or {},
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else "",
            }
            for e in events
        ],
    }


@router.get("/{work_item_id}/investigation")
async def get_work_item_investigation(
    work_item_id: str, db: AsyncSession = Depends(get_db), principal: dict = Depends(require_authenticated),
) -> dict:
    work_item_repo = WorkItemRepository(db)
    item = await work_item_repo.get(UUID(work_item_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await require_cluster_read_access(item.cluster_id, principal, db, require_binding=True)
    from pinky_api.repositories.executions import ExecutionRepository
    repo = ExecutionRepository(db)
    investigation = await repo.get_investigation_for_work_item(UUID(work_item_id))
    if investigation is None:
        return {"has_investigation": False}
    return {"has_investigation": True, **investigation}


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("/{work_item_id}/chat")
async def chat_with_brain(
    work_item_id: str,
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    work_item_repo = WorkItemRepository(db)
    item = await work_item_repo.get(UUID(work_item_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await require_cluster_read_access(item.cluster_id, principal, db, require_binding=True)

    from pinky_api.repositories.executions import ExecutionRepository
    repo = ExecutionRepository(db)
    investigation = await repo.get_investigation_for_work_item(UUID(work_item_id))

    context_parts = [f"Task: {item.title}"]
    if item.why_now:
        context_parts.append(f"Situation: {item.why_now}")
    if investigation:
        if investigation.get("summary"):
            context_parts.append(f"Investigation summary: {investigation['summary']}")
        if investigation.get("root_cause"):
            context_parts.append(f"Root cause: {investigation['root_cause']}")
        if investigation.get("recommended_action"):
            context_parts.append(f"Recommended action: {investigation['recommended_action']}")
    context = "\n\n".join(context_parts)

    messages = [
        {
            "role": "system",
            "content": (
                "You are The Brain, an SRE agent. The operator is asking about an investigation. "
                "Answer concisely using the context below. If they ask for YAML or commands, "
                "provide them. Include relevant oc/kubectl commands in a 'commands' list in your response.\n\n"
                f"Context:\n{context}"
            ),
        },
    ]
    for msg in req.history[-10:]:
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": req.message})

    from pinky_api.k8s import get_events, get_nodes, get_resource, list_resources
    from pinky_api.repositories.clusters import ClusterRepository

    cluster_repo = ClusterRepository(db)
    cluster = await cluster_repo.get(item.cluster_id)
    api_endpoint = cluster.api_endpoint if cluster else ""

    binding = await get_cluster_binding_for_principal(item.cluster_id, principal, db)
    cluster_token = ""
    if binding and binding.encrypted_token:
        from datetime import UTC, datetime
        if binding.expires_at and binding.expires_at < datetime.now(UTC):
            logger.warning("cluster binding expired for chat, tools disabled")
        else:
            from pinky_api.security.crypto import decrypt
            try:
                cluster_token = decrypt(
                    binding.encrypted_token, aad=f"cluster_identity_bindings:{binding.id}",
                ).decode()
            except Exception:
                logger.exception("token decryption failed for binding %s", binding.id)

    tools: list[anthropic.types.ToolParam] = [
        {
            "name": "get_resource",
            "description": "Get a specific K8s resource as JSON. Use for deployments, pods, statefulsets, etc.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "K8s namespace"},
                    "kind": {"type": "string", "description": "Resource kind (pod, deployment, node, etc.)"},
                    "name": {"type": "string", "description": "Resource name"},
                },
                "required": ["namespace", "kind", "name"],
            },
        },
        {
            "name": "list_resources",
            "description": "List K8s resources of a given kind in a namespace. Use to find pods, deployments, etc.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "K8s namespace (empty for cluster-scoped)"},
                    "kind": {"type": "string", "description": "Resource kind (pod, deployment, node, etc.)"},
                },
                "required": ["kind"],
            },
        },
        {
            "name": "get_nodes",
            "description": "Get all cluster nodes with taints, conditions, capacity, and allocatable resources.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "get_events",
            "description": "Get recent K8s events in a namespace. Shows scheduling failures, warnings, errors.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "K8s namespace (empty for all)"},
                },
            },
        },
    ]

    try:
        from anthropic.lib.vertex import AsyncAnthropicVertex
        from anthropic.types import TextBlock, ToolUseBlock
        client = AsyncAnthropicVertex(region="global")
        api_messages: list[anthropic.types.MessageParam] = [
            {"role": "user" if m["role"] == "user" else "assistant", "content": m["content"]}
            for m in messages if m["role"] != "system"
        ]
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")

        tool_fns = {
            "get_resource": lambda inp: get_resource(
                api_endpoint, cluster_token, inp["namespace"], inp["kind"], inp["name"],
            ),
            "list_resources": lambda inp: list_resources(
                api_endpoint, cluster_token, inp.get("namespace", ""), inp["kind"],
            ),
            "get_nodes": lambda _inp: get_nodes(api_endpoint, cluster_token),
            "get_events": lambda inp: get_events(
                api_endpoint, cluster_token, inp.get("namespace", ""),
            ),
        }

        remaining_rounds = 5
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_msg,
            messages=api_messages,
            tools=tools,
        )

        while response.stop_reason == "tool_use" and remaining_rounds > 0:
            remaining_rounds -= 1
            tool_results = []
            for block in response.content:
                if isinstance(block, ToolUseBlock):
                    fn = tool_fns.get(block.name)
                    if fn and cluster_token:
                        try:
                            result = await fn(block.input)
                            import json as _json
                            result_text = _json.dumps(result, default=str)[:8000]
                        except Exception as exc:
                            logger.exception("tool call failed: %s", block.name)
                            result_text = f"Error: {exc}"
                    else:
                        result_text = "Tool unavailable — no cluster binding"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    })

            api_messages.append({"role": "assistant", "content": response.content})
            api_messages.append({"role": "user", "content": tool_results})
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system_msg,
                messages=api_messages,
                tools=tools,
            )

        text_parts = []
        for block in response.content:
            if isinstance(block, TextBlock):
                text_parts.append(block.text)
        content = "\n".join(text_parts)

        commands: list[str] = []
        for match in re.finditer(r"`(oc\s[^`]+|kubectl\s[^`]+)`", content):
            commands.append(match.group(1))

        return {"reply": content, "commands": commands}
    except Exception:
        logger.exception("chat with brain failed")
        raise HTTPException(status_code=502, detail="Brain unavailable") from None
