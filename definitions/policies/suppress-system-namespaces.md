---
name: suppress-system-namespaces
kind: policy
version: 1.0.0
priority: 10
conditions:
  resource_namespace_regex: "^(openshift-|kube-|default$|redhat-|multicluster-engine|open-cluster-management|hive|assisted-installer|hypershift)"
action:
  type: suppress
  suppress_duration_minutes: 1440
---
# Suppress System Namespace Noise

Observations from OpenShift platform namespaces, Kubernetes system
namespaces, and ACM/MCE operator namespaces are suppressed for 24 hours.

These pods are managed by the platform — resource limits, requests,
and restart behavior are controlled by the operator, not by the user.
Investigating them creates noise without actionable outcomes.
