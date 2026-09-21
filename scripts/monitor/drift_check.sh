#!/usr/bin/env bash
# drift_check.sh — deployed-manifest/live drift alarm.
# Compares managed live runtime file hashes against the manifest at the
# approved deployed-runtime reference. Any managed mismatch is a failure.
# Separate from post_push_smoke (which checks remote/main vs deployed).
# Scheduled every 6h; alert path is Telegram via gateway (read-only check).
set -eu

REPO="${DRIFT_REPO:-/home/ubuntu/hermes-agent-personal_assistant-work}"
RECEIPT="${DRIFT_RECEIPT:-/home/ubuntu/.hermes/logs/drift-check.last.json}"
DEPLOYED_REFERENCE="${DRIFT_DEPLOYED_REFERENCE:-/home/ubuntu/.hermes/logs/deployed-runtime-reference.json}"
NOW=$(TZ=Asia/Kuala_Lumpur date +%Y-%m-%dT%H:%M:%S%z)
DEPLOYED_SHA=$(python3 - "$DEPLOYED_REFERENCE" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))["deployed_runtime_sha"])
PY
)

python3 - "$DEPLOYED_SHA" "$REPO" "$NOW" "$RECEIPT" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path

deployed, repo, now, receipt = sys.argv[1:5]
manifest = json.loads(
    subprocess.check_output(
        ["git", "show", f"{deployed}:docs/reconciliation/v3-source-coverage-manifest.json"],
        cwd=repo,
        text=True,
    )
)

drift = []
for entry in manifest["entries"]:
    if entry["kind"] != "runtime-deploy":
        continue
    destination = Path(entry["destination"])
    actual = hashlib.sha256(destination.read_bytes()).hexdigest() if destination.exists() else "MISSING"
    if actual != entry["source_sha256"]:
        drift.append(
            {
                "source": entry["source"],
                "expected": entry["source_sha256"][:12],
                "actual": actual[:12] if actual != "MISSING" else "MISSING",
            }
        )

status = "FAIL" if drift else "PASS"
result = {
    "timestamp": now,
    "deployed_ref": deployed,
    "drift_total": len(drift),
    "drift": drift,
    "status": status,
}
Path(receipt).write_text(json.dumps(result, indent=2) + "\n")

if drift:
    print(f"DRIFT ALERT: {len(drift)} managed drift(s): {[item['source'] for item in drift]}")
    sys.exit(1)

print("drift_check: PASS drift=0")
PY
