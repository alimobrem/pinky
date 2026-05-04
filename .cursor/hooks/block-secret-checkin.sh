#!/usr/bin/env bash
set -euo pipefail

HOOK_INPUT="$(cat)"
export HOOK_INPUT

python3 - <<'PY'
import json
import os
import re
import subprocess
import sys

PATH_PATTERN = re.compile(
    r"(^|/)(\.env($|\.)|oauth-client-secret$|vertex-credentials[^/]*\.json$|"
    r"service-account[^/]*\.json$|gcp[^/]*credentials[^/]*\.json$|"
    r"google[^/]*credentials[^/]*\.json$|id_rsa$|id_ed25519$|.*\.pem$)",
    re.IGNORECASE,
)

CONTENT_PATTERNS = [
    (re.compile(r"-----BEGIN (?:[A-Z ]+)?PRIVATE KEY-----"), "private key material"),
    (re.compile(r'"type"\s*:\s*"service_account"'), "a Google service account credential"),
    (re.compile(r'"private_key_id"\s*:'), "a Google service account private key id"),
    (re.compile(r'"private_key"\s*:\s*"-----BEGIN PRIVATE KEY-----'), "a Google service account private key"),
    (re.compile(r"AIza[0-9A-Za-z\-_]{20,}"), "a Google-style API key"),
    (re.compile(r"ya29\.[0-9A-Za-z\-_]+"), "an OAuth access token"),
]

CONTENT_SCAN_IGNORE_PATHS = {
    ".cursor/hooks/block-secret-checkin.sh",
}


def run_git(*args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout


def deny(reason: str) -> None:
    response = {
        "permission": "deny",
        "user_message": reason,
        "agent_message": reason,
    }
    print(json.dumps(response))
    raise SystemExit(0)


def allow() -> None:
    print(json.dumps({"permission": "allow"}))
    raise SystemExit(0)


try:
    payload = json.loads(os.environ.get("HOOK_INPUT", ""))
except Exception:
    allow()

command = str(payload.get("command", "")).strip()
if not command:
    allow()

if PATH_PATTERN.search(command):
    deny("Blocked: command references a secret-like file path.")


def has_sensitive_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if PATH_PATTERN.search(path)]


def split_lines(output: str) -> list[str]:
    return [line.strip() for line in output.splitlines() if line.strip()]


if command.startswith("git add"):
    code, status_output = run_git("status", "--porcelain")
    if code == 0:
        working_paths = []
        for line in split_lines(status_output):
            if len(line) >= 4:
                working_paths.append(line[3:])
        offenders = has_sensitive_paths(working_paths)
        if offenders and (" -A" in f" {command}" or " --all" in f" {command}" or command.endswith(" .") or " -f " in f" {command}" or " --force " in f" {command}"):
            deny(
                "Blocked: broad git add would include secret-like files: "
                + ", ".join(sorted(set(offenders)))
            )

        if " -f " in f" {command}" or " --force " in f" {command}":
            code, ignored_output = run_git("status", "--ignored", "--porcelain")
            if code == 0:
                ignored_paths = []
                for line in split_lines(ignored_output):
                    if line.startswith("!! ") and len(line) >= 4:
                        ignored_paths.append(line[3:])
                offenders = has_sensitive_paths(ignored_paths)
                if offenders:
                    deny(
                        "Blocked: force-adding ignored secret-like files is not allowed: "
                        + ", ".join(sorted(set(offenders)))
                    )

code, staged_output = run_git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
staged_paths: list[str] = []
if code == 0:
    staged_paths = split_lines(staged_output)
    offenders = has_sensitive_paths(staged_paths)
    if offenders:
        deny(
            "Blocked: staged secret-like files detected: "
            + ", ".join(sorted(set(offenders)))
        )

content_scan_paths = [
    path for path in staged_paths if path not in CONTENT_SCAN_IGNORE_PATHS
]
if content_scan_paths:
    code, staged_diff = run_git(
        "diff",
        "--cached",
        "--no-ext-diff",
        "--unified=0",
        "--",
        *content_scan_paths,
    )
else:
    code, staged_diff = 0, ""

if code == 0 and staged_diff:
    for pattern, description in CONTENT_PATTERNS:
        if pattern.search(staged_diff):
            deny(f"Blocked: staged changes contain {description}.")

if command.startswith("git push"):
    range_expr = ""
    if subprocess.run(["git", "rev-parse", "--verify", "@{u}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode == 0:
        range_expr = "@{u}..HEAD"
    else:
        for base in ("main", "master"):
            if subprocess.run(["git", "rev-parse", "--verify", base], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode == 0:
                code, merge_base = run_git("merge-base", "HEAD", base)
                if code == 0 and merge_base.strip():
                    range_expr = f"{merge_base.strip()}..HEAD"
                    break

    if range_expr:
        code, pushed_paths_output = run_git("diff", "--name-only", range_expr)
        if code == 0:
            pushed_paths = split_lines(pushed_paths_output)
            offenders = has_sensitive_paths(pushed_paths)
            if offenders:
                deny(
                    "Blocked: commits being pushed include secret-like files: "
                    + ", ".join(sorted(set(offenders)))
                )

        pushed_content_scan_paths = [
            path for path in pushed_paths if path not in CONTENT_SCAN_IGNORE_PATHS
        ]
        if pushed_content_scan_paths:
            code, pushed_diff = run_git(
                "diff",
                range_expr,
                "--no-ext-diff",
                "--unified=0",
                "--",
                *pushed_content_scan_paths,
            )
        else:
            code, pushed_diff = 0, ""
        if code == 0 and pushed_diff:
            for pattern, description in CONTENT_PATTERNS:
                if pattern.search(pushed_diff):
                    deny(f"Blocked: commits being pushed contain {description}.")

allow()
PY
