import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
FULL = REPO / "docs/reconciliation/hermes-runtime-tree-manifest.json"
SELECTIVE = REPO / "docs/reconciliation/hermes-runtime-opencode-free-compression-recovery-deploy-manifest.json"

EXPECTED = [
    "agent/auxiliary_client.py",
    "hermes_cli/model_switch.py",
]


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def test_selective_manifest_is_exactly_the_incident_runtime_surface():
    manifest = json.loads(SELECTIVE.read_text(encoding="utf-8"))
    full = json.loads(FULL.read_text(encoding="utf-8"))

    assert [entry["source"] for entry in manifest["entries"]] == EXPECTED
    assert manifest["base_sha"] == full["base_sha"]
    assert manifest["patch_series_digest"] == full["patch_series_digest"]

    full_rows = {entry["source"]: entry for entry in full["entries"]}
    assert manifest["entries"] == [full_rows[source] for source in EXPECTED]
    assert manifest["tree_sha256"] == hashlib.sha256(
        _canonical(manifest["entries"])
    ).hexdigest()
