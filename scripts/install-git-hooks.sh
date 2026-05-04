#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$(git rev-parse --git-path hooks)"

mkdir -p "${HOOKS_DIR}"

cat > "${HOOKS_DIR}/pre-commit" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
exec "${REPO_ROOT}/scripts/git-hooks/run-secret-guard.sh" "git commit"
EOF

cat > "${HOOKS_DIR}/pre-push" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
exec "${REPO_ROOT}/scripts/git-hooks/run-secret-guard.sh" "git push"
EOF

chmod +x "${HOOKS_DIR}/pre-commit" "${HOOKS_DIR}/pre-push"

echo "Installed local git hooks:"
echo "  - ${HOOKS_DIR}/pre-commit"
echo "  - ${HOOKS_DIR}/pre-push"
