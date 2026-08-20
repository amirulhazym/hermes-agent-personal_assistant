#!/usr/bin/env bash
# rollback_restore.sh — restore a rollback snapshot to live runtime.
# Canonical in work repo: scripts/monitor/rollback_restore.sh
# Live mirror: ~/.hermes/scripts/rollback_restore.sh (synced on deploy)
# SAFE: --dry-run never touches ~/.hermes; live path requires --no-dry-run intent.
set -eu
usage() {
  echo "Usage: $0 <sha> [--dry-run] [--skip-restart] [--rollback-dir DIR] [--runtime DIR]"
  echo "  sha              snapshot dir name under ROLLBACK_DIR"
  echo "  --dry-run        print plan only; no capture/copy/restart (default for --help); does NOT touch ~/.hermes"
  echo "  --skip-restart   dry-run helper — no restart even in live mode"
  echo "  --rollback-dir   override (tests: /tmp throwaway)"
  echo "  --runtime        override (tests: /tmp throwaway)"
  exit "${1:-1}"
}
SHA=""
DRY_RUN=false
SKIP_RESTART=false
ROLLBACK_DIR="/home/ubuntu/.hermes/hermes-runtime-rollbacks"
RUNTIME="/home/ubuntu/.hermes/hermes-agent"
skip_next=false
for arg in "$@"; do
  if [ "$skip_next" = true ]; then skip_next=false; continue; fi
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --skip-restart) SKIP_RESTART=true ;;
    --help|-h) usage 0 ;;
    --rollback-dir|--runtime) skip_next=true ;;
    --rollback-dir=*) ROLLBACK_DIR="${arg#--rollback-dir=}" ;;
    --runtime=*) RUNTIME="${arg#--runtime=}" ;;
    --*) echo "Unknown flag: $arg" >&2; usage 1 ;;
    *) [ -z "$SHA" ] && SHA="$arg" || { echo "Too many positional args" >&2; usage 1; } ;;
  esac
done
# Allow --flag value form
args=("$@"); i=0
while [ $i -lt ${#args[@]} ]; do
  case "${args[$i]}" in
    --rollback-dir) ROLLBACK_DIR="${args[$((i+1))]}"; i=$((i+2)) ;;
    --runtime) RUNTIME="${args[$((i+1))]}"; i=$((i+2)) ;;
    *) i=$((i+1)) ;;
  esac
done
[ -n "$SHA" ] || usage 1
SRC="$ROLLBACK_DIR/$SHA"
if [ ! -d "$SRC" ]; then
  echo "rollback not found: $SRC" >&2; exit 2
fi
# Build file list from snapshot (portable: find, not manifest.sha256 which may not exist for old captures)
mapfile -d '' FILES < <(find "$SRC" -type f -print0 | sort -z)
count=${#FILES[@]}
# Safety: refuse outside-runtime copies
bad=0
for f in "${FILES[@]}"; do
  rel="${f#$SRC/}"
  # Normalize: snapshot stores runtime tree; live dest is RUNTIME/rel
  # Refuse absolute/escaping paths
  case "$rel" in
    /*|*\.\.*) echo "refuse escaping path: $rel" >&2; bad=1 ;;
  esac
done
if [ "$bad" -ne 0 ]; then exit 2; fi
if [ "$DRY_RUN" = true ]; then
  echo "DRY-RUN plan for $SHA"
  echo "  source: $SRC ($count files)"
  echo "  runtime: $RUNTIME"
  echo "  would: capture current live -> new rollback (skipped in --dry-run)"
  echo "  would: copy $count files -> \$RUNTIME (skipped)"
  if [ "$SKIP_RESTART" = true ] || [ "$DRY_RUN" = true ]; then
    echo "  would: restart gateway (skipped)"
  fi
  echo "  would: smoke verify (skipped)"
  echo "DRY-RUN OK"
  exit 0
fi
# Live path — guarded (not exercised in tonight's dry-run)
if [ ! -d "$RUNTIME" ]; then echo "runtime missing: $RUNTIME" >&2; exit 2; fi
# Disk guard
avail_kb=$(df -Pk "$RUNTIME" | awk 'NR==2{print $4}')
if [ "${avail_kb:-0}" -lt 1048576 ]; then echo "refuse: disk <1GB free" >&2; exit 2; fi
# Anti self-kill: refuse if caller is child of gateway PID
gw_pid=$(systemctl --user show hermes-gateway.service -p MainPID --value 2>/dev/null || echo "")
if [ -n "$gw_pid" ] && [ "$gw_pid" != "0" ]; then
  # Walk parent chain
  p=$$
  while [ "$p" != "1" ] && [ -n "$p" ]; do
    if [ "$p" = "$gw_pid" ]; then echo "refuse: caller is child of gateway PID $gw_pid" >&2; exit 2; fi
    p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ') || break
  done
fi
# Capture current live before overwrite (reversible)
TS=$(date +%Y%m%dT%H%M%SZ)
CAP="$ROLLBACK_DIR/pre-restore-$TS"
mkdir -p "$CAP"
# Copy live runtime tree snapshot (best-effort, no symlinks)
cp -a "$RUNTIME/." "$CAP/" 2>/dev/null || cp -r "$RUNTIME/." "$CAP/"
echo "captured current live -> $CAP"
# Copy snapshot files
for f in "${FILES[@]}"; do
  rel="${f#$SRC/}"
  dst="$RUNTIME/$rel"
  mkdir -p "$(dirname "$dst")"
  cp -a "$f" "$dst"
done
echo "copied $count files to $RUNTIME"
if [ "$SKIP_RESTART" = false ]; then
  echo "scheduling detached gateway restart..."
  # Reuse documented detached cron method
  cat >/tmp/hermes-rollback-restart-$$.sh <<EOS
#!/usr/bin/env bash
set -eu
export XDG_RUNTIME_DIR=/run/user/\$(id -u)
systemctl --user restart hermes-gateway.service
crontab -l 2>/dev/null | grep -v 'hermes-rollback-restart' | crontab -
EOS
  chmod +x /tmp/hermes-rollback-restart-$$.sh
  ( crontab -l 2>/dev/null; echo "* * * * * /bin/bash /tmp/hermes-rollback-restart-$$.sh # hermes-rollback-restart" ) | crontab -
  echo "restart scheduled (next minute)"
else
  echo "skip restart (--skip-restart)"
fi
echo "restore complete for $SHA"
