#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${1:-pinky}"
RELEASE="${2:-pinky}"
TIMEOUT="${3:-300}"

pass() { echo "  [OK] $1"; }
fail() { echo "  [FAIL] $1"; }
warn() { echo "  [WARN] $1"; }

echo "==> Verifying Pinky deployment in namespace ${NAMESPACE}"
echo ""

# 1. Wait for pods to be ready
echo "--- Waiting for pods (timeout: ${TIMEOUT}s)"
WAITED=0
while [[ ${WAITED} -lt ${TIMEOUT} ]]; do
  NOT_READY=$(kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${RELEASE}" --no-headers 2>/dev/null | grep -v "Running\|Completed" | grep -v "^$" || true)
  if [[ -z "${NOT_READY}" ]]; then
    break
  fi
  sleep 10
  WAITED=$((WAITED + 10))
  echo "  ... waiting (${WAITED}s) — $(echo "${NOT_READY}" | wc -l | tr -d ' ') pods not ready"
done

echo ""
echo "--- Pod status"
kubectl get pods -n "${NAMESPACE}" --no-headers 2>/dev/null | while read -r line; do
  POD=$(echo "${line}" | awk '{print $1}')
  STATUS=$(echo "${line}" | awk '{print $3}')
  if [[ "${STATUS}" == "Running" || "${STATUS}" == "Completed" ]]; then
    pass "${POD}: ${STATUS}"
  elif [[ "${STATUS}" == "CrashLoopBackOff" || "${STATUS}" == "ImagePullBackOff" || "${STATUS}" == "Error" ]]; then
    fail "${POD}: ${STATUS}"
  else
    warn "${POD}: ${STATUS}"
  fi
done

# 2. Database
echo ""
echo "--- PostgreSQL"
PG_POD=$(kubectl get pods -n "${NAMESPACE}" -l app.kubernetes.io/name=pinky-postgresql -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [[ -n "${PG_POD}" ]]; then
  if kubectl exec -n "${NAMESPACE}" "${PG_POD}" -- pg_isready -U pinky &>/dev/null; then
    pass "PostgreSQL is ready"
  else
    fail "PostgreSQL not responding"
  fi
else
  fail "PostgreSQL pod not found"
fi

# 3. Redis
echo "--- Redis"
REDIS_POD=$(kubectl get pods -n "${NAMESPACE}" -l app.kubernetes.io/name=pinky-redis -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [[ -n "${REDIS_POD}" ]]; then
  if kubectl exec -n "${NAMESPACE}" "${REDIS_POD}" -- redis-cli ping 2>/dev/null | grep -q PONG; then
    pass "Redis is ready"
  else
    fail "Redis not responding"
  fi
else
  fail "Redis pod not found"
fi

# 4. API health
echo "--- API"
API_POD=$(kubectl get pods -n "${NAMESPACE}" -l app.kubernetes.io/name=pinky-api -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [[ -n "${API_POD}" ]]; then
  HEALTH=$(kubectl exec -n "${NAMESPACE}" "${API_POD}" -- wget -qO- http://localhost:8000/api/v1/healthz 2>/dev/null || echo "")
  if echo "${HEALTH}" | grep -q '"ok"'; then
    pass "API healthz responding"
  else
    warn "API healthz not responding (may still be starting)"
  fi
else
  fail "API pod not found"
fi

# 5. Migration job
echo "--- Migration"
MIGRATE_STATUS=$(kubectl get jobs -n "${NAMESPACE}" -l app.kubernetes.io/name=pinky-migrate -o jsonpath='{.items[0].status.conditions[0].type}' 2>/dev/null || echo "")
if [[ "${MIGRATE_STATUS}" == "Complete" ]]; then
  pass "Migration job completed"
elif [[ -n "${MIGRATE_STATUS}" ]]; then
  warn "Migration job status: ${MIGRATE_STATUS}"
else
  warn "Migration job not found (may not have run yet)"
fi

# 6. Routes (OpenShift)
echo "--- Routes"
if kubectl api-resources 2>/dev/null | grep -q route.openshift.io; then
  kubectl get routes -n "${NAMESPACE}" --no-headers 2>/dev/null | while read -r line; do
    ROUTE=$(echo "${line}" | awk '{print $1}')
    HOST=$(echo "${line}" | awk '{print $2}')
    pass "Route ${ROUTE}: https://${HOST}"
  done
else
  warn "Not an OpenShift cluster — no routes"
fi

# 7. Services
echo "--- Services"
kubectl get svc -n "${NAMESPACE}" --no-headers 2>/dev/null | while read -r line; do
  SVC=$(echo "${line}" | awk '{print $1}')
  TYPE=$(echo "${line}" | awk '{print $2}')
  PORTS=$(echo "${line}" | awk '{print $5}')
  pass "${SVC} (${TYPE}): ${PORTS}"
done

echo ""
echo "==> Verification complete"
