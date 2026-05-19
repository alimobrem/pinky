#!/usr/bin/env bash
set -euo pipefail

VALUES_FILE="${1:-infra/helm/values-dev.yaml}"
REGISTRY="${PINKY_REGISTRY:-quay.io/pinky-project}"
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

# 4b. Secret sources
echo "--- Secret sources"
if grep -Eq 'clientSecret:\s*".+"' "${VALUES_FILE}" || grep -Eq 'clientSecret:\s*[^"[:space:]][^[:space:]]*' "${VALUES_FILE}"; then
  fail "Inline clientSecret found in values file — move it to env or secrets/ instead of checking it into YAML"
fi

if grep -q "clientId:" "${VALUES_FILE}" && ! grep -Eq 'clientId:\s*""' "${VALUES_FILE}"; then
  if [[ -n "${PINKY_OAUTH_CLIENT_SECRET:-}" || -f "secrets/oauth-client-secret" ]]; then
    pass "OAuth client secret source available"
  else
    fail "OAuth client secret missing (set PINKY_OAUTH_CLIENT_SECRET or secrets/oauth-client-secret)"
  fi
fi

if grep -q "url:" "${VALUES_FILE}" && ! grep -Eq 'url:\s*""' "${VALUES_FILE}"; then
  if grep -q "existingSecret:" "${VALUES_FILE}" && ! grep -Eq 'existingSecret:\s*""' "${VALUES_FILE}"; then
    pass "External Redis secret source configured"
  else
    warn "External Redis URL appears inline in values; prefer redis.external.existingSecret to avoid leaking credentials in rendered manifests"
  fi
fi

if grep -Eq 'provider:\s*vertex' "${VALUES_FILE}"; then
  VERTEX_CREDS="${PINKY_VERTEX_CREDENTIALS:-secrets/vertex-credentials.json}"
  if [[ -f "${VERTEX_CREDS}" ]]; then
    VERTEX_CRED_TYPE="$(python3 - "${VERTEX_CREDS}" <<'PY'
import json
import sys

with open(sys.argv[1]) as handle:
    print(json.load(handle).get("type", "unknown"))
PY
)"
    if [[ "${VERTEX_CRED_TYPE}" == "service_account" ]]; then
      pass "Vertex service account credential source available"
    else
      fail "Vertex credential type '${VERTEX_CRED_TYPE}' is not allowed for cluster deploy; use a service account key"
    fi
  else
    warn "Vertex credentials not found — LLM features may be disabled"
  fi
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
