#!/usr/bin/env bash
# Deterministic secret scan. Matching secret bytes are never printed.
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || { echo 'SECRET-SCAN ERROR: not a Git worktree' >&2; exit 2; }
cd "$ROOT"
case "${1:-}" in
  --tree) exec python3 scripts/guard/secret_scan.py tree ;;
  --staged) exec python3 scripts/guard/secret_scan.py staged ;;
  --diff)
    [ "$#" -eq 3 ] || { echo 'SECRET-SCAN ERROR: usage --diff BASE HEAD' >&2; exit 2; }
    exec python3 scripts/guard/secret_scan.py diff "$2..$3" ;;
  *) echo 'SECRET-SCAN ERROR: usage --tree | --staged | --diff BASE HEAD' >&2; exit 2 ;;
esac
