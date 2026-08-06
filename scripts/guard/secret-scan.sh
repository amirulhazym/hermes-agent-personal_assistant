#!/bin/bash
# secret-scan.sh — deterministic secret scan for staged/tracked content.
# Usage: scripts/guard/secret-scan.sh [--diff <base>..<head> | --staged | --tree]
set -euo pipefail

PATTERN='sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY|ghp_[A-Za-z0-9]{20,}|bot[0-9]{8,}:[A-Za-z0-9_-]{20,}|xox[bap]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{20,}'

MODE="${1:---staged}"
case "$MODE" in
  --diff)
    BASE="${2:?need base}"; HEAD="${3:?need head}"
    git diff "$BASE..$HEAD" | grep -aE '^\+' | grep -aiE "$PATTERN" && { echo "SECRET-SCAN FAIL"; exit 1; } || echo "SECRET-SCAN PASS ($BASE..$HEAD)"
    ;;
  --staged)
    git diff --cached | grep -aE '^\+' | grep -aiE "$PATTERN" && { echo "SECRET-SCAN FAIL"; exit 1; } || echo "SECRET-SCAN PASS (staged)"
    ;;
  --tree)
    git ls-files -z | xargs -0 grep -laiE "$PATTERN" 2>/dev/null && { echo "SECRET-SCAN FAIL (tracked)"; exit 1; } || echo "SECRET-SCAN PASS (tree)"
    ;;
  *) echo "unknown mode: $MODE" >&2; exit 2 ;;
esac
