#!/usr/bin/env bash
set -euo pipefail

VALUES_FILE="${1:-infra/helm/values-dev.yaml}"
REGISTRY="${PINKY_REGISTRY:-quay.io/amobrem}"
TAG="${PINKY_TAG:-latest}"
KUBE="${PINKY_KUBE_CLI:-$(command -v oc 2>/dev/null || command -v kubectl 2>/dev/null || echo kubectl)}"
ERRORS=0

pass() { echo "  [OK] $1"; }
fail() { echo "  [FAIL] $1"; ERRORS=$((ERRORS + 1)); }
warn() { echo "  [WARN] $1"; }

echo "==> Pinky deploy preflight check"
echo ""

# 1. Cluster connection
echo "--- Cluster"
if ${KUBE} cluster-info &>/dev/null; then
  SERVER=$(${KUBE} config current-context 2>/dev/null || echo "unknown")
  pass "Connected to cluster: ${SERVER}"
elif command -v oc &>/dev/null && oc whoami &>/dev/null; then
  pass "Connected via oc: $(oc whoami)"
else
  fail "Not connected to a Kubernetes cluster"
fi

if command -v oc &>/dev/null && oc whoami &>/dev/null; then
  pass "OpenShift user: $(oc whoami)"
fi

# 2. Helm
echo "--- Helm"
if command -v helm &>/dev/null; then
  pass "helm $(helm version --short 2>/dev/null)"
else
  fail "helm not found"
fi

# 3. Values file
echo "--- Values"
if [[ -f "$VALUES_FILE" ]]; then
  pass "Values file exists: ${VALUES_FILE}"
else
  fail "Values file not found: ${VALUES_FILE}"
fi

# 4. Helm lint
echo "--- Chart validation"
if helm lint infra/helm/pinky -f "${VALUES_FILE}" &>/dev/null; then
  pass "helm lint passed"
else
  fail "helm lint failed"
fi

if helm template pinky infra/helm/pinky -f "${VALUES_FILE}" &>/dev/null; then
  RESOURCE_COUNT=$(helm template pinky infra/helm/pinky -f "${VALUES_FILE}" 2>/dev/null | grep -c "^kind:")
  pass "helm template renders ${RESOURCE_COUNT} resources"
else
  fail "helm template failed"
fi

# 5. Images
echo "--- Images"
ENGINE="${CONTAINER_ENGINE:-$(command -v podman 2>/dev/null || command -v docker 2>/dev/null || echo podman)}"
for IMG in pinky-api pinky-worker pinky-web; do
  FULL="${REGISTRY}/${IMG}:${TAG}"
  if ${ENGINE} inspect "${FULL}" &>/dev/null 2>&1; then
    ARCH=$(${ENGINE} inspect "${FULL}" --format '{{.Architecture}}' 2>/dev/null)
    if [[ "${ARCH}" == "amd64" ]]; then
      pass "${IMG}: ${ARCH}"
    else
      fail "${IMG}: architecture is ${ARCH}, expected amd64"
    fi
  else
    warn "${IMG}: image not found locally (may already be in registry)"
  fi
done

# 6. Container engine
echo "--- Container engine"
if command -v "${ENGINE}" &>/dev/null; then
  pass "${ENGINE} available"
else
  warn "No container engine found (not needed if images are in registry)"
fi

echo ""
if [[ ${ERRORS} -gt 0 ]]; then
  echo "==> PREFLIGHT FAILED: ${ERRORS} error(s)"
  exit 1
else
  echo "==> PREFLIGHT PASSED"
fi
