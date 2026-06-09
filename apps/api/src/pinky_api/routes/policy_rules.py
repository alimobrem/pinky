"""Policy rule routes — declarative triage rule management."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import require_admin
from pinky_api.db.deps import get_db
from pinky_api.policy import PolicyInput, evaluate, rules_from_db_rows
from pinky_api.repositories.policy_rules_repo import PolicyRuleRepository

router = APIRouter(prefix="/api/v1/policy-rules", tags=["policy-rules"])


class PolicyRuleCreateRequest(BaseModel):
    name: str
    description: str = ""
    priority: int = 100
    conditions: dict
    action: dict


class PolicyRuleUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    priority: int | None = None
    enabled: bool | None = None
    conditions: dict | None = None
    action: dict | None = None


class PolicyRuleEvalRequest(BaseModel):
    scanner: str = ""
    check_id: str = ""
    severity: str = "medium"
    resource_kind: str = ""
    resource_namespace: str = ""
    cluster_id: str = ""
    labels: dict[str, str] = {}
    recurrence_count: int = 1


def _serialize(r: Any) -> dict:
    return {
        "id": str(r.id),
        "name": r.name,
        "description": r.description,
        "priority": r.priority,
        "enabled": r.enabled,
        "conditions": r.conditions,
        "action": r.action,
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }


@router.get("")
async def list_policy_rules(db: AsyncSession = Depends(get_db)) -> dict:
    repo = PolicyRuleRepository(db)
    result = await repo.list()
    return {
        "items": [_serialize(r) for r in result["items"]],
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
    }


@router.post("", status_code=201)
async def create_policy_rule(
    req: PolicyRuleCreateRequest, db: AsyncSession = Depends(get_db), _admin: dict = Depends(require_admin),
) -> dict:
    repo = PolicyRuleRepository(db)
    rule = await repo.create(
        name=req.name, description=req.description, priority=req.priority,
        conditions=req.conditions, action=req.action,
    )
    await db.commit()
    return _serialize(rule)


@router.put("/{rule_id}")
async def update_policy_rule(
    rule_id: str, req: PolicyRuleUpdateRequest,
    db: AsyncSession = Depends(get_db), _admin: dict = Depends(require_admin),
) -> dict:
    repo = PolicyRuleRepository(db)
    rule = await repo.get(UUID(rule_id))
    if rule is None:
        raise HTTPException(status_code=404, detail="Policy rule not found")
    updates = req.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(rule, field, value)
    await db.flush()
    await db.commit()
    return _serialize(rule)


@router.delete("/{rule_id}", status_code=204)
async def delete_policy_rule(
    rule_id: str, db: AsyncSession = Depends(get_db), _admin: dict = Depends(require_admin),
) -> None:
    repo = PolicyRuleRepository(db)
    deleted = await repo.delete(UUID(rule_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Policy rule not found")
    await db.commit()


@router.post("/evaluate")
async def evaluate_policy_rule(
    req: PolicyRuleEvalRequest,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
) -> dict:
    repo = PolicyRuleRepository(db)
    db_rules = await repo.list_enabled()
    eval_rules = rules_from_db_rows(db_rules)
    inp = PolicyInput(
        scanner=req.scanner,
        check_id=req.check_id,
        severity=req.severity,
        resource_kind=req.resource_kind,
        resource_namespace=req.resource_namespace,
        cluster_id=req.cluster_id,
        labels=req.labels,
        recurrence_count=req.recurrence_count,
    )
    return evaluate(eval_rules, inp)
