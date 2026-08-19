#!/usr/bin/env bash
# Exact-manifest Hermes runtime deployment wrapper.
# Default/required caller behavior is dry-run; apply is release-gated by the
# Python tool's full SHA requirement and must be invoked only after Gate 2.
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
exec python3 "$repo_root/scripts/deploy_hermes_runtime.py" \
  --source-tree "${HERMES_SOURCE_TREE:?set HERMES_SOURCE_TREE to a reconstructed tree}" \
  --manifest "$repo_root/docs/reconciliation/hermes-runtime-tree-manifest.json" \
  --lock "$repo_root/docs/reconciliation/hermes-runtime-source-lock.json" \
  "$@"
