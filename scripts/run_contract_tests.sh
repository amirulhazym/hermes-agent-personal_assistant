#!/usr/bin/env bash
# run_contract_tests.sh — fast contract subset for Gate 2 lineage/session/resume
# Full suite: ~100 min. This subset: ~30 sec, covers contract-critical paths.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

echo "=== contract tests: reconciliation + guard ==="
# Reconciliation: runtime reconstruction + C2/C3/C4 lineage
# Guard: PII/secret/manifest — the CI gate
python3 -m pytest \
  tests/reconciliation/ \
  tests/guard/ \
  -v --tb=short

echo "=== contract suite complete ==="
