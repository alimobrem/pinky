#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${PINKY_NAMESPACE:-pinky}"
RELEASE="${PINKY_RELEASE:-pinky}"
VALUES_FILE="${1:-infra/helm/values-dev.yaml}"

echo "==> Deploying Pinky to namespace ${NAMESPACE}"
echo "    Release: ${RELEASE}"
echo "    Values:  ${VALUES_FILE}"

kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

if [[ "${PINKY_BUILD:-false}" == "true" ]]; then
  echo "==> Building images..."
  make docker-build
  echo "==> Pushing images..."
  make docker-push
fi

echo "==> Running helm upgrade --install..."
helm upgrade --install "${RELEASE}" infra/helm/pinky \
  --namespace "${NAMESPACE}" \
  --values "${VALUES_FILE}" \
  --wait --timeout 10m

echo "==> Deployment complete"
kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${RELEASE}"
echo ""
echo "==> Services"
kubectl get svc -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${RELEASE}"
echo ""

if kubectl api-resources | grep -q route.openshift.io; then
  echo "==> Routes"
  kubectl get routes -n "${NAMESPACE}" 2>/dev/null || true
fi
