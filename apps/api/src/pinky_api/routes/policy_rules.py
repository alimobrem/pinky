"""Policy rule routes — declarative triage rule management."""

from fastapi import APIRouter
from pydantic import BaseModel

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
    # TODO: query policy_rules table + merge definition-based policies
    return {"items": [], "next_cursor": None, "has_more": False}


@router.post("", status_code=201)
async def create_policy_rule(req: PolicyRuleCreateRequest) -> dict:
    # TODO: check_product_authz(principal, Role.ADMIN)
    # TODO: insert into policy_rules
    return {"message": "Policy rule creation not yet implemented"}


@router.put("/{rule_id}")
async def update_policy_rule(rule_id: str, req: PolicyRuleCreateRequest) -> dict:
    # TODO: check_product_authz(principal, Role.ADMIN)
    return {"message": "Policy rule update not yet implemented"}


@router.delete("/{rule_id}", status_code=204)
async def delete_policy_rule(rule_id: str) -> None:
    # TODO: check_product_authz(principal, Role.ADMIN)
    pass


@router.post("/evaluate")
async def evaluate_policy_rule(req: PolicyRuleEvalRequest) -> dict:
    # TODO: check_product_authz(principal, Role.ADMIN)
    # TODO: run policy engine evaluate() against current rules
    # TODO: return which rule matched and what action would be taken
    return {"message": "Dry-run evaluation not yet implemented"}
