#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
exec "$SCRIPT_DIR/nightly_git_hygiene.py" --timeout --human-only
