#!/bin/bash
# manifest-validate.sh — validate a deployment manifest as data (no deploy).
# Usage: scripts/guard/manifest-validate.sh <manifest> <release-sha>
set -euo pipefail

MANIFEST="${1:?manifest path}"; SHA="${2:?release sha}"
[ -f "$MANIFEST" ] || { echo "FATAL: manifest missing"; exit 1; }
git cat-file -e "$SHA^{commit}" 2>/dev/null || { echo "FATAL: $SHA not a commit"; exit 1; }

echo "=== validating $MANIFEST at $SHA ==="
awk -F'|' '/^\| (scripts|skills|patches)/ {gsub(/^ +| +$/,"",$2); gsub(/^ +| +$/,"",$3); gsub(/^ +| +$/,"",$4); print $2 "|" $3 "|" $4}' "$MANIFEST" | while IFS='|' read -r src manifest_sha dest; do
  [ -n "$src" ] || continue
  # source exists at SHA
  git cat-file -e "$SHA:$src" 2>/dev/null || { echo "FAIL: source missing $src"; exit 1; }
  # source hash equals manifest
  h=$(git show "$SHA:$src" | sha256sum | cut -d' ' -f1)
  [ "$h" = "$manifest_sha" ] || { echo "FAIL: hash mismatch $src ($h vs $manifest_sha)"; exit 1; }
  # destination inside /home/ubuntu/.hermes
  case "$dest" in
    /home/ubuntu/.hermes/*) ;;
    *) echo "FAIL: destination outside .hermes: $dest"; exit 1 ;;
  esac
  echo "OK $src"
done
echo "MANIFEST-VALIDATE PASS"
