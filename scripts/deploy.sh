#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${PINKY_NAMESPACE:-pinky}"
RELEASE="${PINKY_RELEASE:-pinky}"
VALUES_FILE="${1:-infra/helm/values-dev.yaml}"
KUBE="${PINKY_KUBE_CLI:-$(command -v oc 2>/dev/null || command -v kubectl 2>/dev/null || echo kubectl)}"

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

# OAuth client secret
if [[ -n "${PINKY_OAUTH_CLIENT_SECRET:-}" ]]; then
  ${KUBE} create secret generic pinky-auth \
    --namespace "${NAMESPACE}" \
    --from-literal=openshift-client-secret="${PINKY_OAUTH_CLIENT_SECRET}" \
    --dry-run=client -o yaml | ${KUBE} apply -f -
  echo "    OAuth secret: set"
elif [[ -f "secrets/oauth-client-secret" ]]; then
  ${KUBE} create secret generic pinky-auth \
    --namespace "${NAMESPACE}" \
    --from-file=openshift-client-secret=secrets/oauth-client-secret \
    --dry-run=client -o yaml | ${KUBE} apply -f -
  echo "    OAuth secret: set from file"
else
  echo "    OAuth secret: using existing (set PINKY_OAUTH_CLIENT_SECRET or secrets/oauth-client-secret)"
fi

# Vertex AI credentials
VERTEX_CREDS="${PINKY_VERTEX_CREDENTIALS:-secrets/vertex-credentials.json}"
if [[ -f "${VERTEX_CREDS}" ]]; then
  ${KUBE} create secret generic pinky-vertex-credentials \
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
