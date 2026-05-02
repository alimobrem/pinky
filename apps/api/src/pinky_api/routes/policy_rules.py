"""Policy rule routes — declarative triage rule management."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from pinky_api.auth.deps import require_admin

router = APIRouter(prefix="/api/v1/policy-rules", tags=["policy-rules"])


class PolicyRuleCreateRequest(BaseModel):
    name: str
    description: str = ""
    priority: int = 100
    conditions: dict
    action: dict


class PolicyRuleEvalRequest(BaseModel):
    scanner: str = ""
    check_id: str = ""
    severity: str = "medium"
    resource_kind: str = ""
    resource_namespace: str = ""
    cluster_id: str = ""
    labels: dict[str, str] = {}
    recurrence_count: int = 1


@router.get("")
async def list_policy_rules() -> dict:
    return {"items": [], "next_cursor": None, "has_more": False}


@router.post("", status_code=201)
async def create_policy_rule(req: PolicyRuleCreateRequest, _admin: dict = Depends(require_admin)) -> dict:
    return {"message": "Policy rule creation not yet implemented"}


@router.put("/{rule_id}")
async def update_policy_rule(rule_id: str, req: PolicyRuleCreateRequest, _admin: dict = Depends(require_admin)) -> dict:
    return {"message": "Policy rule update not yet implemented"}


@router.delete("/{rule_id}", status_code=204)
async def delete_policy_rule(rule_id: str, _admin: dict = Depends(require_admin)) -> None:
    pass


@router.post("/evaluate")
async def evaluate_policy_rule(req: PolicyRuleEvalRequest, _admin: dict = Depends(require_admin)) -> dict:
    return {"message": "Dry-run evaluation not yet implemented"}
