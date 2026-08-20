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
  -v --tb=short \
  2>&1 | tail -30

# Also check: these are the contract tests that would fail on Gate 2 regression
echo "=== contract suite complete ==="
echo "To catch Gate 2 regressions, these 14 tests must all pass."
echo "Expected: 14 passed in ~10s"
