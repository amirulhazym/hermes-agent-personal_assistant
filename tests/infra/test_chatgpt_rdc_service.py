"""Source-side contract for the live-verified dedicated RDC service."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNIT = ROOT / "ops/systemd/user/chatgpt-rdc.service"
PKG = ROOT / "ops/rdc/package.json"
LOCK = ROOT / "ops/rdc/package-lock.json"
BOOTSTRAP = ROOT / "ops/rdc/bootstrap.sh"


def test_rdc_unit_matches_live_approved_service_contract():
    unit = UNIT.read_text(encoding="utf-8")
    required = (
        "[Unit]", "[Service]", "[Install]", "Type=simple",
        "StartLimitIntervalSec=0",
        "WorkingDirectory=/home/ubuntu",
        "Environment=HOME=/home/ubuntu",
        "Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "ExecStartPre=/usr/bin/curl --fail --silent --show-error --output /dev/null "
        "--connect-timeout 3 --max-time 8 https://mcp.desktopcommander.app/api/mcp-info",
        "ExecStart=/usr/bin/node /home/ubuntu/.local/share/chatgpt-rdc/0.2.51/"
        "node_modules/@wonderwhy-er/desktop-commander/dist/index.js remote",
        "Restart=always", "RestartSec=8s", "TimeoutStartSec=15s",
        "KillMode=control-group", "KillSignal=SIGTERM", "TimeoutStopSec=20s",
        "StandardOutput=journal", "StandardError=journal",
        "WantedBy=default.target",
    )
    missing = [part for part in required if part not in unit]
    assert not missing, f"missing approved live directives: {missing}"
    forbidden = ("npx", "tmux", "hermes-gateway.service",
                 "TimeoutStartSec=infinity", "ACCESS_TOKEN",
                 "REFRESH_TOKEN", "API_KEY", "PASSWORD")
    assert not [part for part in forbidden if part.lower() in unit.lower()]


def test_rdc_dependency_manifest_is_version_locked():
    manifest = json.loads(PKG.read_text(encoding="utf-8"))
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    key = "@wonderwhy-er/desktop-commander"
    assert manifest["private"] is True
    assert manifest["dependencies"] == {key: "0.2.51"}
    assert lock["lockfileVersion"] == 3
    assert lock["packages"][""]["dependencies"][key] == "0.2.51"
    assert lock["packages"]["node_modules/" + key]["version"] == "0.2.51"
    urls = [p["resolved"] for p in lock["packages"].values() if "resolved" in p]
    assert urls and all(url.startswith("https://registry.npmjs.org/") for url in urls)


def test_bootstrap_install_requires_explicit_action_and_inactive_rdc():
    script = BOOTSTRAP.read_text(encoding="utf-8")
    assert "npm ci --prefix" in script
    assert "--check" in script and "--install" in script
    assert "systemctl --user is-active --quiet chatgpt-rdc.service" in script
    assert "Refusing to overwrite an existing RDC runtime" in script
    assert "systemctl --user restart" not in script
    assert "systemctl --user enable" not in script
    assert "systemctl reboot" not in script
