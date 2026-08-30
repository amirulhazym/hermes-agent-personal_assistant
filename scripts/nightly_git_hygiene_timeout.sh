#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
if [ "$#" -ne 1 ]; then
  printf '%s\n' 'nightly timeout wrapper requires an exact run_id' >&2
  exit 2
fi
exec "$SCRIPT_DIR/nightly_git_hygiene.py" --timeout --run-id "$1" --human-only
