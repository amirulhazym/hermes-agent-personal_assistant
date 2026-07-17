#!/usr/bin/env bash
set -euo pipefail

# Dry-run by default. Requires explicit --apply and human approval outside this script.
APPLY=0
HOST=""
USER_NAME=""
SRC=""
DST=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --host) HOST="$2"; shift 2 ;;
    --user) USER_NAME="$2"; shift 2 ;;
    --src) SRC="$2"; shift 2 ;;
    --dst) DST="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$HOST" || -z "$USER_NAME" || -z "$SRC" || -z "$DST" ]]; then
  echo "usage: $0 --host <host> --user <user> --src <repo> --dst <remote-dir> [--apply]" >&2
  exit 2
fi

RSYNC=(rsync -avzn --delete
  --exclude '.env'
  --exclude '.env.*'
  --exclude 'auth.json'
  --exclude 'web-operator/state/'
  --exclude 'web-operator/profiles/'
  --exclude 'web-operator/quarantine/'
  --exclude 'web-operator/artifacts/'
  --exclude 'web-operator/takeover/'
  --exclude 'web-operator/medical-audit/'
  --exclude 'web-operator/keys/'
  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude '.git/'
  --exclude 'logs/'
  --exclude 'session/'
  --exclude 'platforms/'
)

if [[ "$APPLY" -eq 1 ]]; then
  RSYNC=(rsync -avz --delete "${RSYNC[@]:2}")
  echo "APPLY mode: will copy source only. No gateway restart is performed."
else
  echo "DRY-RUN mode (pass --apply after explicit human approval)"
fi

"${RSYNC[@]}" \
  -e "ssh -o BatchMode=yes" \
  "$SRC/scripts/web_operator/" "$USER_NAME@$HOST:$DST/scripts/web_operator/"

"${RSYNC[@]}" \
  -e "ssh -o BatchMode=yes" \
  "$SRC/skills/experts/web-operator/" "$USER_NAME@$HOST:$DST/skills/experts/web-operator/"

echo "Done. Restart gateway only with separate explicit approval."
