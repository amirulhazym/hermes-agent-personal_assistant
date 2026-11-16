#!/bin/bash
# Huawei Health puller wrapper (Hermes no_agent cron).
#
# Semantics: STDOUT IS THE MESSAGE. Empty stdout = silent delivery (normal path).
# Speaks only on: auth EXPIRED (exit 2) or is_stale == true.
#
# Test hooks (do not set in production):
#   HUAWEI_SKIP_SYNC=1     skip running sync_huawei.py
#   HUAWEI_STATUS_FILE=... override status.json path
set -uo pipefail

SYNC="${HUAWEI_SYNC_PY:-/home/ubuntu/hermes-huawei-sync/sync_huawei.py}"
LOG=/home/ubuntu/hermes-huawei-sync/logs/cron.log
STATUS_FILE="${HUAWEI_STATUS_FILE:-/home/ubuntu/hermes-huawei-sync/data/status.json}"

RC=0
if [ "${HUAWEI_SKIP_SYNC:-0}" != "1" ]; then
    # 09:30 MYT run: finalize yesterday first so activity after the 22:30 cron is captured.
    # Silent on success (stdout = message); failures are logged and surfaced by the main run.
    if [ "$(date +%H)" = "09" ]; then
        FIN=$(python3 "$SYNC" --finalize-yesterday 2>&1)
        FRC=$?
        printf '%s\n' "$FIN" >> "$LOG"
        if [ "$FRC" -ne 0 ]; then
            echo "⚠️ Huawei finalize-yesterday gagal (exit $FRC) — fail semalam mungkin stale."
        fi
    fi
    OUT=$(python3 "$SYNC" --sync-diet-log 2>&1)
    RC=$?
    printf '%s\n' "$OUT" >> "$LOG"
fi

AUTH=$(python3 -c "import json;print(json.load(open('$STATUS_FILE')).get('auth_state',''))" 2>/dev/null || echo "")
STALE=$(python3 -c "import json;print(json.load(open('$STATUS_FILE')).get('is_stale',''))" 2>/dev/null || echo "")
STALEMIN=$(python3 -c "import json;print(json.load(open('$STATUS_FILE')).get('staleness_minutes',''))" 2>/dev/null || echo "")
RSS_LIMIT_KB=40000
RSS=$(printf '%s\n' "${OUT:-}" | grep -o 'RSS_KB=[0-9]*' | tail -1 | cut -d= -f2)

# 1) Auth gone -> needs a human re-login. Always speak.
if [ "$RC" -eq 2 ] || [ "$AUTH" = "EXPIRED" ]; then
    echo "🔴 Huawei Health token EXPIRED — data watch dah berhenti masuk."
    echo "Perlu re-login (60 saat): bagitahu aku, aku generate auth URL baru."
    exit 0
fi

# 2) Sync failed for another reason. Speak, but do not pretend it is auth.
if [ "$RC" -ne 0 ]; then
    echo "⚠️ Huawei Health sync gagal (exit $RC)."
    echo "Detail: $LOG (baris terakhir). Aku akan trace bila kau balas."
    exit 0
fi

# 3) Memory gate (owner-raised threshold 40 MB).
if [ -n "${RSS:-}" ] && [ "$RSS" -gt "$RSS_LIMIT_KB" ]; then
    echo "⚠️ Huawei sync RSS ${RSS} KB melebihi gate ${RSS_LIMIT_KB} KB."
    echo "Semak logs/cron.log — kalau berulang, trim payload."
    exit 0
fi

# 4) Stale data -> phone has not pushed to cloud. Speak.
if [ "$STALE" = "True" ]; then
    echo "⚠️ Huawei Health data stale (${STALEMIN} minit)."
    echo "Buka Huawei Health kat Honor 600 Pro, tarik skrin ke bawah untuk flush sync."
    exit 0
fi

# Normal path: silence.
exit 0
