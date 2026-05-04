#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <git command string>" >&2
  exit 2
fi

COMMAND_STRING="$1"
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_SCRIPT="${REPO_ROOT}/.cursor/hooks/block-secret-checkin.sh"

if [[ ! -f "${HOOK_SCRIPT}" ]]; then
  echo "Secret guard hook script not found at ${HOOK_SCRIPT}" >&2
  exit 2
fi

RESULT="$(printf '%s' "{\"command\":$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "${COMMAND_STRING}")}" | bash "${HOOK_SCRIPT}")"

if [[ "${SECRET_GUARD_DEBUG:-false}" == "true" ]]; then
  echo "${RESULT}"
fi

python3 - <<'PY' "${RESULT}"
import json
import sys

payload = json.loads(sys.argv[1])
if payload.get("permission") == "allow":
    raise SystemExit(0)

message = payload.get("user_message") or payload.get("agent_message") or "Blocked by secret guard."
print(message, file=sys.stderr)
raise SystemExit(1)
PY
