#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${1:-pinky}"
RELEASE="${2:-pinky}"
TIMEOUT="${3:-300}"
KUBE="${PINKY_KUBE_CLI:-$(command -v oc 2>/dev/null || command -v kubectl 2>/dev/null || echo kubectl)}"
AUTH_SECRET_NAME="${PINKY_AUTH_SECRET_NAME:-${RELEASE}-auth}"
VERTEX_SECRET_NAME="${PINKY_VERTEX_SECRET_NAME:-${RELEASE}-vertex-credentials}"

pass() { echo "  [OK] $1"; }
fail() { echo "  [FAIL] $1"; }
warn() { echo "  [WARN] $1"; }

echo "==> Verifying Pinky deployment in namespace ${NAMESPACE}"
echo ""

# 1. Wait for pods to be ready
echo "--- Waiting for pods (timeout: ${TIMEOUT}s)"
WAITED=0
while [[ ${WAITED} -lt ${TIMEOUT} ]]; do
  NOT_READY=$(${KUBE} get pods -n "${NAMESPACE}" -l "app.kubernetes.io/instance=${RELEASE}" --no-headers 2>/dev/null | grep -v "Running\|Completed" | grep -v "^$" || true)
  if [[ -z "${NOT_READY}" ]]; then
    break
  fi
  sleep 10
  WAITED=$((WAITED + 10))
  echo "  ... waiting (${WAITED}s) — $(echo "${NOT_READY}" | wc -l | tr -d ' ') pods not ready"
done

echo ""
echo "--- Pod status"
${KUBE} get pods -n "${NAMESPACE}" --no-headers 2>/dev/null | while read -r line; do
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
PG_POD=$(${KUBE} get pods -n "${NAMESPACE}" -l app.kubernetes.io/name=pinky-postgresql -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [[ -n "${PG_POD}" ]]; then
  if ${KUBE} exec -n "${NAMESPACE}" "${PG_POD}" -- pg_isready -U pinky &>/dev/null; then
    pass "PostgreSQL is ready"
  else
    fail "PostgreSQL not responding"
  fi
else
  fail "PostgreSQL pod not found"
fi

# 3. Redis
echo "--- Redis"
REDIS_POD=$(${KUBE} get pods -n "${NAMESPACE}" -l app.kubernetes.io/name=pinky-redis -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [[ -n "${REDIS_POD}" ]]; then
  if ${KUBE} exec -n "${NAMESPACE}" "${REDIS_POD}" -- redis-cli ping 2>/dev/null | grep -q PONG; then
    pass "Redis is ready"
  else
    fail "Redis not responding"
  fi
else
  fail "Redis pod not found"
fi

# 4. API health
echo "--- API"
API_POD=$(${KUBE} get pods -n "${NAMESPACE}" -l app.kubernetes.io/name=pinky-api -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [[ -n "${API_POD}" ]]; then
  HEALTH=$(${KUBE} exec -n "${NAMESPACE}" "${API_POD}" -- python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/v1/healthz').read().decode())" 2>/dev/null || echo "")
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
MIGRATE_STATUS=$(${KUBE} get jobs -n "${NAMESPACE}" -l app.kubernetes.io/name=pinky-migrate -o jsonpath='{.items[0].status.conditions[0].type}' 2>/dev/null || echo "")
if [[ "${MIGRATE_STATUS}" == "Complete" ]]; then
  pass "Migration job completed"
elif [[ -n "${MIGRATE_STATUS}" ]]; then
  warn "Migration job status: ${MIGRATE_STATUS}"
else
  warn "Migration job not found (may not have run yet)"
fi

# 6. Routes (OpenShift)
echo "--- Routes"
if ${KUBE} api-resources 2>/dev/null | grep -q route.openshift.io; then
  ${KUBE} get routes -n "${NAMESPACE}" --no-headers 2>/dev/null | while read -r line; do
    ROUTE=$(echo "${line}" | awk '{print $1}')
    HOST=$(echo "${line}" | awk '{print $2}')
    pass "Route ${ROUTE}: https://${HOST}"
  done
else
  warn "Not an OpenShift cluster — no routes"
fi

# 7. Services
echo "--- Services"
${KUBE} get svc -n "${NAMESPACE}" --no-headers 2>/dev/null | while read -r line; do
  SVC=$(echo "${line}" | awk '{print $1}')
  TYPE=$(echo "${line}" | awk '{print $2}')
  PORTS=$(echo "${line}" | awk '{print $5}')
  pass "${SVC} (${TYPE}): ${PORTS}"
done

echo "--- Secrets"
if ${KUBE} get secret -n "${NAMESPACE}" "${AUTH_SECRET_NAME}" >/dev/null 2>&1; then
  pass "Auth secret present"
else
  warn "Auth secret not found"
fi

if ${KUBE} get secret -n "${NAMESPACE}" "${VERTEX_SECRET_NAME}" >/dev/null 2>&1; then
  pass "Vertex credentials secret present"
else
  warn "Vertex credentials secret not found"
fi

echo "--- Temporal"
TEMPORAL_POD=$(${KUBE} get pods -n "${NAMESPACE}" -l app.kubernetes.io/name=pinky-temporal -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [[ -n "${TEMPORAL_POD}" ]]; then
  pass "Temporal pod present: ${TEMPORAL_POD}"
else
  warn "Temporal pod not found"
fi

echo ""
echo "==> Verification complete"
