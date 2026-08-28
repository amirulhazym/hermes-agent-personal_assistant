#!/usr/bin/env bash
# List available rollback artifacts in operator-friendly format.
#
# Reads ~/.hermes/hermes-runtime-rollbacks/ and prints a sorted, timestamped
# list. Used by the post-push smoke script to emit auto-reference lines when
# new drift is detected. Safe to run; read-only.

set -uo pipefail
ROLLBACK_DIR=/home/ubuntu/.hermes/hermes-runtime-rollbacks
KNOWN_GOOD=/home/ubuntu/.hermes/hermes-runtime-rollbacks.last-known-good
[[ -d "$ROLLBACK_DIR" ]] || { echo "no rollback dir at $ROLLBACK_DIR"; exit 0; }

# Use a tmp file to avoid "broken pipe" from large sort output.
TMP=$(mktemp)
trap "rm -f '$TMP'" EXIT

# Each rollback is a directory whose name is the released commit SHA.
# We also store a captured-at timestamp in <rollback>/.captured_at if present.
for d in "$ROLLBACK_DIR"/*/; do
  [[ -d "$d" ]] || continue
  name=$(basename "$d")
  ts=""
  if [[ -f "$d/.captured_at" ]]; then
    ts=$(cat "$d/.captured_at")
  fi
  if [[ -z "$ts" ]]; then
    # Fall back to mtime of the dir.
    ts=$(stat -c %y "$d" 2>/dev/null || stat -f "%Sm" "$d" 2>/dev/null || echo "unknown")
  fi
  is_known_good="NO"
  if [[ -L "$KNOWN_GOOD" ]] || [[ -f "$KNOWN_GOOD" ]]; then
    if [[ -d "$KNOWN_GOOD" ]] && [[ "$(basename "$(readlink -f "$KNOWN_GOOD" 2>/dev/null || echo "$KNOWN_GOOD")")" == "$name" ]]; then
      is_known_good="YES"
    fi
  fi
  file_count=$(find "$d" -type f | wc -l)
  echo -e "$ts\t$name\t$is_known_good\t$file_count\t$d" >> "$TMP"
done

# Print the table (newest first by timestamp column).
{
  echo "Available rollback artifacts (newest first):"
  echo
  printf '%-25s  %-65s  %-15s  %-5s  %s\n' "CAPTURED_AT" "SHA" "LAST_KNOWN_GOOD" "FILES" "PATH"
  echo "----------------------------------------------------------------------------------------------------------------------------------------"
  sort -r "$TMP" | while IFS=$'\t' read -r ts name is_known_good file_count path; do
    printf '%-25s  %-65s  %-15s  %-5s  %s\n' "$ts" "$name" "$is_known_good" "$file_count" "$path"
  done
}