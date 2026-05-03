#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${PINKY_NAMESPACE:-pinky}"
RELEASE="${PINKY_RELEASE:-pinky}"
VALUES_FILE="${1:-infra/helm/values-dev.yaml}"

echo "==> Deploying Pinky to namespace ${NAMESPACE}"
echo "    Release: ${RELEASE}"
echo "    Values:  ${VALUES_FILE}"
echo ""

# Pre-flight
./scripts/preflight.sh "${VALUES_FILE}" || exit 1
echo ""

# Create namespace
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

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
