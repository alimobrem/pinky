"""Tests for K8s resource kind mapping and LLM output correction."""

import pytest
from pinky_worker.execution.activities import _KIND_TO_API, _api_path, _normalize_step


class TestKindToApiMapping:
    def test_core_resources_mapped(self):
        assert _KIND_TO_API["pod"] == ("api/v1", "pods")
        assert _KIND_TO_API["service"] == ("api/v1", "services")
        assert _KIND_TO_API["configmap"] == ("api/v1", "configmaps")

    def test_apps_resources_mapped(self):
        assert _KIND_TO_API["deployment"] == ("apis/apps/v1", "deployments")
        assert _KIND_TO_API["statefulset"] == ("apis/apps/v1", "statefulsets")
        assert _KIND_TO_API["daemonset"] == ("apis/apps/v1", "daemonsets")

    def test_crd_resources_mapped(self):
        assert _KIND_TO_API["rollout"] == ("apis/argoproj.io/v1alpha1", "rollouts")
        assert _KIND_TO_API["route"] == ("apis/route.openshift.io/v1", "routes")
        assert _KIND_TO_API["hpa"] == ("apis/autoscaling/v2", "horizontalpodautoscalers")

    def test_api_path_core_resource(self):
        path = _api_path("pod", "default", "nginx-abc123")
        assert path == "api/v1/namespaces/default/pods/nginx-abc123"

    def test_api_path_deployment(self):
        path = _api_path("deployment", "prod", "web")
        assert path == "apis/apps/v1/namespaces/prod/deployments/web"

    def test_api_path_rollout(self):
        path = _api_path("rollout", "guestbook", "demo-rollout")
        assert path == "apis/argoproj.io/v1alpha1/namespaces/guestbook/rollouts/demo-rollout"

    def test_api_path_unknown_kind_fallback(self):
        path = _api_path("widget", "default", "my-widget")
        assert path == "api/v1/namespaces/default/widgets/my-widget"

    def test_all_mapped_kinds_produce_valid_paths(self):
        for kind in _KIND_TO_API:
            path = _api_path(kind, "test-ns", "test-name")
            assert "/namespaces/test-ns/" in path
            assert "test-name" in path


class TestNormalizeStepKindCorrection:
    def test_no_correction_when_kind_matches(self):
        step = {"resource_kind": "rollout", "resource_name": "demo", "action": "patch"}
        result = _normalize_step(step, actual_kind="rollout")
        assert result["resource_kind"] == "rollout"

    def test_corrects_deployment_to_rollout(self):
        step = {"resource_kind": "deployment", "resource_name": "demo", "action": "patch"}
        result = _normalize_step(step, actual_kind="rollout")
        assert result["resource_kind"] == "rollout"

    def test_corrects_pod_to_statefulset(self):
        step = {"resource_kind": "pod", "resource_name": "db-0", "action": "delete_pod"}
        result = _normalize_step(step, actual_kind="statefulset")
        assert result["resource_kind"] == "statefulset"

    def test_no_correction_without_actual_kind(self):
        step = {"resource_kind": "deployment", "resource_name": "web", "action": "patch"}
        result = _normalize_step(step)
        assert result["resource_kind"] == "deployment"

    def test_no_correction_when_actual_kind_not_in_mapping(self):
        step = {"resource_kind": "deployment", "resource_name": "web", "action": "patch"}
        result = _normalize_step(step, actual_kind="customwidget")
        assert result["resource_kind"] == "deployment"

    def test_slash_resource_format_extracts_kind(self):
        step = {"resource": "rollout/demo-app", "action": "patch"}
        result = _normalize_step(step)
        assert result["resource_kind"] == "rollout"
        assert result["resource_name"] == "demo-app"

    def test_defaults_to_deployment_when_kind_empty(self):
        step = {"resource_name": "web", "action": "patch"}
        result = _normalize_step(step)
        assert result["resource_kind"] == "deployment"
