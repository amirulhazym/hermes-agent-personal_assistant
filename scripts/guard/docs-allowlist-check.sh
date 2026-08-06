#!/bin/bash
# docs-allowlist-check.sh — verify a changed path set is docs-only per AGENTS.md.
# Usage: scripts/guard/docs-allowlist-check.sh <changed-path>...
set -euo pipefail

GOVERNANCE='^docs/reconciliation/|^AGENTS\.md$|^skills/|^\.github/|^config/|^scripts/|^hooks/|^patches/|^sync/|^windows/|^tests/|^operations/|^persona/'

ALLOWED=0
for p in "$@"; do
  case "$p" in
    docs/*)
      if echo "$p" | grep -qE "$GOVERNANCE"; then
        echo "PROTECTED: $p"; exit 1
      fi
      ALLOWED=1 ;;
    README.md|PROGRESS.md|DECISIONS.md|RUNBOOK.md|CHANGELOG*|*.md)
      if echo "$p" | grep -qE "$GOVERNANCE"; then
        echo "PROTECTED: $p"; exit 1
      fi
      ALLOWED=1 ;;
    *)
      echo "NOT-DOCS: $p"; exit 1 ;;
  esac
done
[ "$ALLOWED" = "1" ] && echo "DOCS-ALLOWLIST PASS" || { echo "DOCS-ALLOWLIST FAIL (empty set)"; exit 1; }
