#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${PINKY_NAMESPACE:-pinky}"
RELEASE="${PINKY_RELEASE:-pinky}"
VALUES_FILE="${1:-infra/helm/values-dev.yaml}"
KUBE="${PINKY_KUBE_CLI:-$(command -v oc 2>/dev/null || command -v kubectl 2>/dev/null || echo kubectl)}"
AUTH_SECRET_NAME="${PINKY_AUTH_SECRET_NAME:-${RELEASE}-auth}"
VERTEX_SECRET_NAME="${PINKY_VERTEX_SECRET_NAME:-${RELEASE}-vertex-credentials}"

echo "==> Deploying Pinky to namespace ${NAMESPACE}"
echo "    Release: ${RELEASE}"
echo "    Values:  ${VALUES_FILE}"
echo "    CLI:     ${KUBE}"
echo ""

# Pre-flight
./scripts/preflight.sh "${VALUES_FILE}" || exit 1
echo ""

# Create namespace
${KUBE} create namespace "${NAMESPACE}" --dry-run=client -o yaml | ${KUBE} apply -f -

# Create secrets from local files (never checked into git)
echo "==> Setting up secrets..."

OAUTH_SECRET_VALUE=""

# OAuth client secret
if [[ -n "${PINKY_OAUTH_CLIENT_SECRET:-}" ]]; then
  OAUTH_SECRET_VALUE="${PINKY_OAUTH_CLIENT_SECRET}"
elif [[ -f "secrets/oauth-client-secret" ]]; then
  OAUTH_SECRET_VALUE="$(tr -d '\n' < secrets/oauth-client-secret)"
fi

if [[ -n "${OAUTH_SECRET_VALUE}" ]]; then
  AUTH_SECRET_NAME="${AUTH_SECRET_NAME}" \
  NAMESPACE="${NAMESPACE}" \
  OAUTH_SECRET_VALUE="${OAUTH_SECRET_VALUE}" \
  python3 - <<'PY' | ${KUBE} apply -f -
import json
import os

print(
    f"""apiVersion: v1
kind: Secret
metadata:
  name: {os.environ["AUTH_SECRET_NAME"]}
  namespace: {os.environ["NAMESPACE"]}
type: Opaque
stringData:
  openshift-client-secret: {json.dumps(os.environ["OAUTH_SECRET_VALUE"])}
"""
)
PY
  echo "    OAuth secret: set"

  if ${KUBE} api-resources 2>/dev/null | grep -q "oauthclient"; then
    helm template "${RELEASE}" infra/helm/pinky \
      --namespace "${NAMESPACE}" \
      --values "${VALUES_FILE}" \
      --show-only templates/oauthclient.yaml \
      --set-string auth.openshift.clientSecret="__PINKY_OAUTH_SECRET__" 2>/dev/null | \
      OAUTH_SECRET_VALUE="${OAUTH_SECRET_VALUE}" \
      python3 -c 'import os, sys; sys.stdout.write(sys.stdin.read().replace("__PINKY_OAUTH_SECRET__", os.environ["OAUTH_SECRET_VALUE"]))' | \
      ${KUBE} apply -f -
    echo "    OAuth client: applied"
  fi
else
  echo "    OAuth secret: using existing (set PINKY_OAUTH_CLIENT_SECRET or secrets/oauth-client-secret)"
fi

# Vertex AI credentials
VERTEX_CREDS="${PINKY_VERTEX_CREDENTIALS:-secrets/vertex-credentials.json}"
if [[ -f "${VERTEX_CREDS}" ]]; then
  ${KUBE} create secret generic "${VERTEX_SECRET_NAME}" \
    --namespace "${NAMESPACE}" \
    --from-file=credentials.json="${VERTEX_CREDS}" \
    --dry-run=client -o yaml | ${KUBE} apply -f -
  echo "    Vertex credentials: set"
else
  echo "    Vertex credentials: not found at ${VERTEX_CREDS} — LLM features disabled"
fi

# Build + push (if requested)
if [[ "${PINKY_BUILD:-false}" == "true" ]]; then
  echo "==> Building images..."
  make docker-build REGISTRY="${PINKY_REGISTRY:-quay.io/amobrem}"
  echo "==> Pushing images..."
  make docker-push REGISTRY="${PINKY_REGISTRY:-quay.io/amobrem}"
fi

# Helm install/upgrade
echo "==> Running helm upgrade --install..."
helm upgrade --install "${RELEASE}" infra/helm/pinky \
  --namespace "${NAMESPACE}" \
  --values "${VALUES_FILE}" \
  --timeout 10m

echo ""

# Post-install verify
./scripts/verify.sh "${NAMESPACE}" "${RELEASE}"
