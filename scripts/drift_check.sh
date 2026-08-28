#!/usr/bin/env bash
# drift_check.sh — worktree/live drift alarm (Phase 3.1)
# Compares live ~/.hermes/hermes-agent file hashes against manifest at
# deployed_runtime reference. Warns if live bytes changed outside deploy.
# Separate from post_push_smoke (which checks remote/main vs deployed).
# Scheduled every 6h; alert path is Telegram via gateway (read-only check).
set -eu
REPO=/home/ubuntu/hermes-agent-personal_assistant-work
RUNTIME=/home/ubuntu/.hermes/hermes-agent
RECEIPT=/home/ubuntu/.hermes/logs/drift-check.last.json
NOW=$(TZ=Asia/Kuala_Lumpur date +%Y-%m-%dT%H:%M:%S%z)
DEPLOYED_SHA=$(python3 -c 'import json;print(json.load(open("/home/ubuntu/.hermes/logs/deployed-runtime-reference.json"))["deployed_runtime_sha"])')

# Compare live runtime hashes vs manifest at deployed ref
python3 - "$DEPLOYED_SHA" "$REPO" "$RUNTIME" "$NOW" "$RECEIPT" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
deployed, repo, runtime, now, receipt = sys.argv[1:6]
manifest = json.loads(subprocess.check_output(["git","show",f"{deployed}:docs/reconciliation/v3-source-coverage-manifest.json"], cwd=repo, text=True))
drift = []
for e in manifest["entries"]:
    if e["kind"] != "runtime-deploy":
        continue
    dst = Path(e["destination"])
    actual = hashlib.sha256(dst.read_bytes()).hexdigest() if dst.exists() else "MISSING"
    if actual != e["source_sha256"]:
        drift.append({"source": e["source"], "expected": e["source_sha256"][:12], "actual": actual[:12] if actual!="MISSING" else "MISSING"})
# Known acceptable drift: documented Gate 2 baseline (9 files)
known = {"hooks/med-auto-confirm/test_hook_chain.py","scripts/test_chain_adapter.py","skills/devops/whatsapp-bridge-maintenance/SKILL.md","skills/med-tracker/references/live-confirmation-pitfalls.md","skills/operator/hermes-live-audit/SKILL.md","skills/operator/hermes-release-deploy/SKILL.md","skills/operator/hermes-source-change/SKILL.md","skills/productivity/documentation-workflow/SKILL.md","skills/research/medication-safety-research/SKILL.md"}  # Gate 2
new_drift = [d for d in drift if d["source"] not in known]
result = {"timestamp":now,"deployed_ref":deployed,"drift_total":len(drift),"new_drift":len(new_drift),"known_drift":drift,"new":new_drift,"status":"WARN" if len(new_drift)==0 and drift else ("FAIL" if new_drift else "PASS")}
Path(receipt).write_text(json.dumps(result,indent=2)+"\n")
# Route alert only if new (unexpected) drift
if new_drift:
    print(f"DRIFT ALERT: {len(new_drift)} unexpected drift(s): {[d['source'] for d in new_drift]}")
    sys.exit(1)
print(f"drift_check: {result['status']} drift={len(drift)} new={len(new_drift)}")
PY