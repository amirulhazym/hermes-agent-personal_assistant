#!/usr/bin/env bash
# Read-only VPS smoke check. Cron is the sole post-push trigger.
set -eu
RUNTIME=/home/ubuntu/.hermes/hermes-agent
MANIFEST_REPO=/home/ubuntu/hermes-agent-personal_assistant-work
LOG_DIR=/home/ubuntu/.hermes/logs
RECEIPT="$LOG_DIR/post-push-smoke.last.json"
SUMMARY="$LOG_DIR/post-push-smoke.last.md"
TMP_THRESHOLD_GB="${TMP_THRESHOLD_GB:-10}"
NOW=$(TZ=Asia/Kuala_Lumpur date +%Y-%m-%dT%H:%M:%S%z)
REMOTE_SHA=$(git -C "$MANIFEST_REPO" ls-remote origin refs/heads/main | cut -f1)
DEPLOYED_SHA=$(python3 -c 'import json; print(json.load(open("/home/ubuntu/.hermes/logs/deployed-runtime-reference.json"))["deployed_runtime_sha"])')
GATEWAY_ACTIVE=$(systemctl --user is-active hermes-gateway.service || true)
BRIDGE_LISTEN=$(ss -ltnH 'sport = :3000' | head -1 || true)
GATEWAY_PID=$(systemctl --user show hermes-gateway.service -p MainPID --value)
TMP_USED_BYTES=$(du -B1 -s /tmp 2>/dev/null | cut -f1 || echo 0)
TMP_THRESHOLD_BYTES=$(awk -v g="$TMP_THRESHOLD_GB" 'BEGIN{printf "%d", g*1024*1024*1024}')
TMP_ALERT=false
[ "$TMP_USED_BYTES" -gt "$TMP_THRESHOLD_BYTES" ] && TMP_ALERT=true || true

python3 - "$REMOTE_SHA" "$DEPLOYED_SHA" "$GATEWAY_ACTIVE" "$BRIDGE_LISTEN" "$GATEWAY_PID" "$MANIFEST_REPO" "$RUNTIME" "$NOW" "$RECEIPT" "$SUMMARY" "$TMP_USED_BYTES" "$TMP_ALERT" "$TMP_THRESHOLD_GB" <<'PY'
import hashlib, json, sqlite3, subprocess, sys
from pathlib import Path
remote_sha, deployed_sha, gateway_active, bridge_listener, gateway_pid, repo, runtime, now, receipt_p, summary_p, tmp_used_bytes, tmp_alert, tmp_threshold_gb = sys.argv[1:14]
required_tg = "agent:main:telegram:dm:679729206"
required_wa = "agent:main:whatsapp:group:120363428305511789@g.us"
source_manifest = Path(repo) / "docs/reconciliation/v3-source-coverage-manifest.json"
manifest_data = json.loads(subprocess.check_output(["git", "show", f"{deployed_sha}:docs/reconciliation/v3-source-coverage-manifest.json"], cwd=repo, text=True))
routing = {required_tg: False, required_wa: False}
try:
    con = sqlite3.connect("file:/home/ubuntu/.hermes/state.db?mode=ro", uri=True)
    cur = con.cursor()
    routing[required_tg] = bool(cur.execute("SELECT 1 FROM gateway_routing WHERE session_key = ? LIMIT 1", (required_tg,)).fetchone())
    routing[required_wa] = bool(cur.execute("SELECT 1 FROM gateway_routing WHERE session_key LIKE ? LIMIT 1", (required_wa + "%",)).fetchone())
    con.close()
except Exception as exc:
    routing["error"] = str(exc)
checks = []
for entry in manifest_data["entries"]:
    if entry["kind"] != "runtime-deploy":
        continue
    dst = Path(entry["destination"])
    actual = hashlib.sha256(dst.read_bytes()).hexdigest() if dst.exists() else None
    checks.append({"source": entry["source"], "destination": str(dst), "match": actual == entry["source_sha256"], "expected_sha256": entry["source_sha256"], "actual_sha256": actual})
# Baseline is informational only; deployed-reference mismatch is the actual signal.
known_drift = [c["source"] for c in checks if not c["match"]]
new_drift = []
service_ok = gateway_active == "active" and bool(bridge_listener) and routing[required_tg] and routing[required_wa]
remote_read_ok = bool(remote_sha and len(remote_sha) == 40)
tmp_ok = tmp_alert == "false"
if not remote_read_ok or not service_ok or not tmp_ok:
    status = "FAIL"
elif not known_drift and remote_sha == deployed_sha:
    status = "NOOP"
elif known_drift:
    status = "WARN"
else:
    status = "NOOP"
receipt = {"status": status, "timestamp_my": now, "remote_main_sha": remote_sha, "deployed_runtime_sha": deployed_sha, "gateway_active": gateway_active, "gateway_pid": gateway_pid, "bridge_listener": bridge_listener, "routing": routing, "file_checks": checks, "drift": {"known_drift": known_drift, "new_drift": new_drift}, "thresholds": {"tmp_used_bytes": int(tmp_used_bytes), "tmp_used_gb": round(int(tmp_used_bytes)/(1024**3),2), "tmp_alert": tmp_alert, "tmp_threshold_gb": int(tmp_threshold_gb)}}
Path(receipt_p).write_text(json.dumps(receipt, indent=2) + "\n")
lines = [f"# post-push smoke ({now})", "", f"- status: **{status}**", f"- remote_main_sha: `{remote_sha}`", f"- deployed_runtime_sha: `{deployed_sha}`", f"- gateway: `{gateway_active}` (pid={gateway_pid})", f"- bridge listener: `{bridge_listener or 'NONE'}`", f"- routing telegram_dm: {routing[required_tg]}", f"- routing whatsapp_group: {routing[required_wa]}", f"- runtime drift vs deployed reference: {len(known_drift)} path(s)", f"- /tmp usage: {receipt['thresholds']['tmp_used_gb']} GB (threshold: {tmp_threshold_gb} GB)"]
if known_drift: lines.append("- known runtime drift: " + ", ".join(f"`{p}`" for p in known_drift))
if tmp_alert == "true": lines.append(f"- /tmp ALERT: above {tmp_threshold_gb} GB")
Path(summary_p).write_text("\n".join(lines) + "\n")
sys.exit(1 if status == "FAIL" else 0)
PY