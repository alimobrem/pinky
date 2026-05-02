import pytest
from fastapi import HTTPException

from pinky_api.auth.authz import (
    AuthzClass,
    Role,
    check_cluster_authz,
    check_execution_authz,
    check_product_authz,
)


def test_product_authz_rejects_empty_principal() -> None:
    with pytest.raises(HTTPException) as exc:
        check_product_authz({})
    assert exc.value.status_code == 401


def test_product_authz_allows_any_user() -> None:
    check_product_authz({"id": "p1", "groups": []})


def test_product_authz_rejects_non_admin() -> None:
    with pytest.raises(HTTPException) as exc:
        check_product_authz({"id": "p1", "groups": ["users"]}, Role.ADMIN)
    assert exc.value.status_code == 403


def test_product_authz_allows_admin_group() -> None:
    check_product_authz({"id": "p1", "groups": ["pinky-admins"]}, Role.ADMIN)


def test_product_authz_allows_admin_flag() -> None:
    check_product_authz({"id": "p1", "groups": [], "is_admin": True}, Role.ADMIN)


# --- Cluster authz ---

def test_observer_read_requires_healthy_observer() -> None:
    check_cluster_authz(AuthzClass.OBSERVER_READ, None, {"health_state": "healthy"})


def test_observer_read_rejects_unhealthy_observer() -> None:
    with pytest.raises(HTTPException) as exc:
        check_cluster_authz(AuthzClass.OBSERVER_READ, None, {"health_state": "unhealthy"})
    assert exc.value.status_code == 503


def test_observer_read_rejects_missing_observer() -> None:
    with pytest.raises(HTTPException) as exc:
        check_cluster_authz(AuthzClass.OBSERVER_READ, None, None)
    assert exc.value.status_code == 503


def test_sensitive_read_requires_valid_binding() -> None:
    check_cluster_authz(AuthzClass.USER_SENSITIVE_READ, {"status": "valid"})


def test_sensitive_read_allows_expiring_binding() -> None:
    check_cluster_authz(AuthzClass.USER_SENSITIVE_READ, {"status": "expiring"})


def test_sensitive_read_rejects_expired_binding() -> None:
    with pytest.raises(HTTPException) as exc:
        check_cluster_authz(AuthzClass.USER_SENSITIVE_READ, {"status": "expired"})
    assert exc.value.status_code == 401
    assert "reauthentication" in exc.value.detail.lower()


def test_sensitive_read_rejects_missing_binding() -> None:
    with pytest.raises(HTTPException) as exc:
        check_cluster_authz(AuthzClass.USER_SENSITIVE_READ, None)
    assert exc.value.status_code == 401


def test_user_write_rejects_revoked_binding() -> None:
    with pytest.raises(HTTPException) as exc:
        check_cluster_authz(AuthzClass.USER_WRITE, {"status": "revoked"})
    assert exc.value.status_code == 401


# --- Execution authz ---

def test_execution_authz_allows_standard_risk_without_approval() -> None:
    check_execution_authz(AuthzClass.USER_WRITE, risk_class="standard")


def test_execution_authz_requires_approval_for_high_risk() -> None:
    with pytest.raises(HTTPException) as exc:
        check_execution_authz(AuthzClass.USER_WRITE, risk_class="high")
    assert exc.value.status_code == 403
    assert "approval" in exc.value.detail.lower()


def test_execution_authz_allows_approved_high_risk() -> None:
    check_execution_authz(AuthzClass.USER_WRITE, risk_class="high", approval_status="approved")


def test_execution_authz_requires_fresh_reauth_for_very_high_risk_stale_session() -> None:
    with pytest.raises(HTTPException) as exc:
        check_execution_authz(
            AuthzClass.USER_WRITE,
            risk_class="very_high",
            approval_status="approved",
            session_age_minutes=20,
        )
    assert exc.value.status_code == 401
    assert "reauthentication" in exc.value.detail.lower()


def test_execution_authz_allows_very_high_risk_fresh_session() -> None:
    check_execution_authz(
        AuthzClass.USER_WRITE,
        risk_class="very_high",
        approval_status="approved",
        session_age_minutes=5,
    )


def test_execution_authz_skips_non_write() -> None:
    check_execution_authz(AuthzClass.OBSERVER_READ, risk_class="very_high")
