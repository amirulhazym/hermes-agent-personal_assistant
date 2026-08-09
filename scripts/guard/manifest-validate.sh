#!/usr/bin/env bash
# Strict source-coverage manifest validation; no deployment.
set -euo pipefail
[ "$#" -eq 2 ] || { echo 'MANIFEST-VALIDATE ERROR: usage <manifest.json> <release-sha>' >&2; exit 2; }
exec python3 scripts/guard/manifest_validate.py "$1" "$2"
