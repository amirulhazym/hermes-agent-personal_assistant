from hashlib import sha256

from scripts.verify_hermes_runtime_selection import compare_live_hashes


def _entry(source: str, destination, expected_bytes: bytes):
    return {
        "source": source,
        "destination": str(destination),
        "sha256": sha256(expected_bytes).hexdigest(),
        "mode": "0644",
    }


def test_managed_live_hash_mismatch_reports_exact_source(tmp_path):
    destination = tmp_path / "runtime" / "agent" / "auxiliary_client.py"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"drifted-live-bytes\n")

    entries = [_entry("agent/auxiliary_client.py", destination, b"approved-candidate\n")]

    assert compare_live_hashes(entries) == ("agent/auxiliary_client.py",)


def test_missing_managed_destination_reports_exact_source(tmp_path):
    destination = tmp_path / "runtime" / "hermes_cli" / "model_switch.py"
    entries = [_entry("hermes_cli/model_switch.py", destination, b"approved-candidate\n")]

    assert compare_live_hashes(entries) == ("hermes_cli/model_switch.py",)


def test_unmanaged_live_drift_is_ignored(tmp_path):
    selected = tmp_path / "runtime" / "agent" / "auxiliary_client.py"
    selected.parent.mkdir(parents=True)
    selected.write_bytes(b"approved-candidate\n")
    unmanaged = tmp_path / "runtime" / "other.py"
    unmanaged.write_bytes(b"unrelated-drift\n")

    entries = [_entry("agent/auxiliary_client.py", selected, b"approved-candidate\n")]

    assert compare_live_hashes(entries) == ()
