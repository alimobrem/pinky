#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${PINKY_NAMESPACE:-pinky}"

echo "==> Setting up secrets in namespace ${NAMESPACE}"

kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

# Encryption key
if kubectl get secret pinky-encryption-key -n "${NAMESPACE}" &>/dev/null; then
  echo "    Encryption key secret already exists — skipping"
else
  ENC_KEY=$(python3 -c "import os; print(os.urandom(32).hex())")
  kubectl create secret generic pinky-encryption-key \
    --namespace "${NAMESPACE}" \
    --from-literal=key="${ENC_KEY}"
  echo "    Encryption key created"
  echo "    SAVE THIS KEY: ${ENC_KEY}"
fi

# Database credentials (if using external DB)
if [[ -n "${PINKY_DB_URL:-}" ]]; then
  DB_URL_ASYNCPG="${PINKY_DB_URL}"
  DB_URL_PLAIN="${PINKY_DB_URL//postgresql+asyncpg/postgresql}"

  kubectl create secret generic pinky-db-credentials \
    --namespace "${NAMESPACE}" \
    --from-literal=url="${DB_URL_ASYNCPG}" \
    --from-literal=url-plain="${DB_URL_PLAIN}" \
    --from-literal=password="external" \
    --dry-run=client -o yaml | kubectl apply -f -
  echo "    External DB secret created"
fi

echo "==> Done"
