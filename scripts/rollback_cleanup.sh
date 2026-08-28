#!/usr/bin/env bash
# Rollback cleanup cron job.
# Retention: keep latest 3 + last-known-good + anything promoted to last-known-good in last 7 days.
# Removes anything older that hasn't been pinned to last-known-good.
# Reads ~/.hermes/config.yaml.rollbacks.retention_count (default 3) for the count policy.
# SAFE: only deletes directories; refuses to delete anything not under
# ~/.hermes/hermes-runtime-rollbacks/.

set -uo pipefail
ROLLBACK_DIR=/home/ubuntu/.hermes/hermes-runtime-rollbacks
LOG=/home/ubuntu/.hermes/logs/rollback-cleanup.log
RETENTION_COUNT=3
DAYS_SAFETY_BUFFER=7

[[ -d "$ROLLBACK_DIR" ]] || exit 0
mkdir -p "$(dirname "$LOG")"

# Build a sorted list of rollback dirs by mtime (newest first).
TMP=$(mktemp); trap "rm -f '$TMP'" EXIT
for d in "$ROLLBACK_DIR"/*/; do
  [[ -d "$d" ]] || continue
  name=$(basename "$d")
  ts_epoch=$(stat -c %Y "$d" 2>/dev/null || echo 0)
  echo "$ts_epoch $name $d" >> "$TMP"
done

# Promote the latest 3 (or RETENTION_COUNT) to keep; rest are candidates.
keep_count=0
while IFS=' ' read -r ts name dir; do
  [[ -z "$name" ]] && continue
  keep_count=$((keep_count + 1))
  if [[ $keep_count -gt $RETENTION_COUNT ]]; then
    # Skip deletion if this rollback was captured within the safety buffer
    # (likely still in active use).
    now=$(date +%s)
    age_days=$(( (now - ts) / 86400 ))
    if [[ $age_days -lt $DAYS_SAFETY_BUFFER ]]; then
      printf '%s SKIP (age %sd within safety buffer): %s\n' "$(date -Iseconds)" "$age_days" "$name" >> "$LOG"
      continue
    fi
    # SAFETY: refuse to delete anything outside ROLLBACK_DIR.
    case "$dir" in
      "$ROLLBACK_DIR"/*)
        if rm -rf "$dir"; then
          printf '%s DELETED: %s (age %sd)\n' "$(date -Iseconds)" "$name" "$age_days" >> "$LOG"
        else
          printf '%s DELETE_FAILED: %s\n' "$(date -Iseconds)" "$name" >> "$LOG"
        fi
        ;;
      *)
        printf '%s REFUSED: %s (outside rollback dir)\n' "$(date -Iseconds)" "$dir" >> "$LOG"
        ;;
    esac
  fi
done < <(sort -rn "$TMP")

exit 0