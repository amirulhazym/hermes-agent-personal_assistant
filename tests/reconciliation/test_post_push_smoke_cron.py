from __future__ import annotations

import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/monitor/post_push_smoke.sh"


def _export_line(prefix: str) -> str:
    for line in SCRIPT.read_text().splitlines():
        if line.startswith(prefix):
            return line
    raise AssertionError(f"missing {prefix} in {SCRIPT}")


def test_cron_like_environment_can_reach_user_systemd_bus() -> None:
    xdg = _export_line("export XDG_RUNTIME_DIR=")
    dbus = _export_line("export DBUS_SESSION_BUS_ADDRESS=")
    probe = "\n".join([xdg, dbus, "systemctl --user show hermes-gateway.service -p MainPID --value"])
    env = {"HOME": "/home/ubuntu", "USER": "ubuntu", "PATH": "/usr/local/bin:/usr/bin:/bin"}
    result = subprocess.run(["bash", "-c", probe], env=env, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().isdigit(), result.stdout + result.stderr


def test_gateway_pid_probe_is_non_fatal() -> None:
    text = SCRIPT.read_text()
    assert 'GATEWAY_PID=$(systemctl --user show hermes-gateway.service -p MainPID --value || true)' in text
