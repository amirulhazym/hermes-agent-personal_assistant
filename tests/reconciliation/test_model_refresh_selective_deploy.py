from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORE = REPO / "docs/reconciliation/hermes-runtime-model-refresh-deploy-manifest.json"
FULL = REPO / "docs/reconciliation/hermes-runtime-tree-manifest.json"
AGY = REPO / "docs/reconciliation/antigravity-model-refresh-deploy-manifest.json"
MODEL_PATCH = REPO / "patches/upstream-hermes/2026-09-24_model_provider_refresh_v021.patch"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def test_core_model_refresh_deploy_manifest_is_minimal_and_hash_pinned() -> None:
    manifest = json.loads(CORE.read_text())
    full = json.loads(FULL.read_text())
    patch = MODEL_PATCH.read_text()

    touched = [
        match.group(2)
        for match in re.finditer(r"^diff --git a/(.+?) b/(.+?)$", patch, re.MULTILINE)
    ]
    production = [path for path in touched if not path.startswith("tests/")]
    sources = [entry["source"] for entry in manifest["entries"]]

    assert sources == production
    assert len(sources) == 8
    assert manifest["destination_root"] == "/home/ubuntu/.hermes/hermes-agent"
    assert manifest["base_sha"] == full["base_sha"]
    assert manifest["patch_series_digest"] == full["patch_series_digest"]
    assert manifest["tree_sha256"] == hashlib.sha256(_canonical(manifest["entries"])).hexdigest()

    full_by_source = {entry["source"]: entry for entry in full["entries"]}
    assert manifest["entries"] == [full_by_source[source] for source in sources]


def test_antigravity_model_refresh_deploy_manifest_is_one_file_and_chain_pinned() -> None:
    manifest = json.loads(AGY.read_text())

    assert manifest["authority"] == "antigravity-model-refresh-selective-deploy"
    assert manifest["upstream_base_sha"] == "097db5303a610d7e5d75a2fef58d4aefb18436d6"
    assert manifest["destination_root"] == "/home/ubuntu/.hermes/plugins/antigravity-provider"
    assert [entry["source"] for entry in manifest["entries"]] == [
        "src/antigravity_provider/models.py"
    ]

    for patch in manifest["patch_chain"]:
        path = REPO / patch["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == patch["sha256"]

    payload = {
        "patch_chain": manifest["patch_chain"],
        "entries": manifest["entries"],
    }
    assert manifest["payload_sha256"] == hashlib.sha256(_canonical(payload)).hexdigest()
