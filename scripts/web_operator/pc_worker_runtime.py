"""PC-side outbound worker.

Polls a local bridge mailbox (synced from VPS via SSH/SCP by the launcher)
or a remote path mounted as local files. Never opens inbound listeners.
Executes only grant-scoped named-app CUA actions via cua-driver.
"""

from __future__ import annotations

import base64
import json
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from .bridge import BridgePaths, GrantConsumer
from .crypto import HostKeyStore
from .grants import GrantError


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class CuaDriver:
    def __init__(self, exe: str) -> None:
        self.exe = exe

    def available(self) -> bool:
        return Path(self.exe).is_file()

    def status_text(self) -> str:
        try:
            r = subprocess.run(
                [self.exe, "status"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            return (r.stdout or r.stderr or "").strip()
        except Exception as exc:
            return f"status_error:{type(exc).__name__}"

    def call(self, tool: str, args: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
        cmd = [self.exe, "call", tool]
        if args:
            cmd.extend(["--args", json.dumps(args)])
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if r.returncode != 0:
            return {"ok": False, "error": err or out or f"exit {r.returncode}", "tool": tool}
        try:
            data = json.loads(out) if out else {}
        except json.JSONDecodeError:
            data = {"raw": out}
        if isinstance(data, dict):
            data.setdefault("ok", True)
            return data
        return {"ok": True, "data": data, "tool": tool}


class PcWorkerRuntime:
    def __init__(
        self,
        bridge_root: Path,
        *,
        device_id: str = "",
        cua_exe: str = r"C:\Users\amiru\AppData\Local\Programs\Cua\cua-driver\bin\cua-driver.exe",
        allowed_apps: Optional[set[str]] = None,
    ) -> None:
        self.paths = BridgePaths(Path(bridge_root))
        self.keys = HostKeyStore(self.paths.keys / "pc")
        self.identity = self.keys.load_or_create_identity()
        self.device_id = device_id or f"pc-{self.identity.fingerprint[:12]}"
        self.cua = CuaDriver(cua_exe)
        self.consumer = GrantConsumer(self.paths.consumed, self.device_id)
        self.allowed_apps = {
            a.lower()
            for a in (
                allowed_apps
                or {
                    "notepad",
                    "notepad.exe",
                    "microsoft.windowsnotepad_8wekyb3d8bbwe!app",
                    "brave",
                    "brave.exe",
                }
            )
        }
        self._stop = False

    def enroll_payload(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "fingerprint": self.identity.fingerprint,
            "public_key_b64": base64.b64encode(self.identity.public_key_bytes).decode("ascii"),
            "label": "windows-pc",
            "created_at": _utc(),
        }

    def write_enrollment_request(self) -> Path:
        path = self.paths.devices / f"{self.device_id}.request.json"
        path.write_text(json.dumps(self.enroll_payload(), indent=2) + "\n", encoding="utf-8")
        return path

    def heartbeat(self, *, online: bool = True, detail: Optional[Mapping[str, Any]] = None) -> Path:
        payload = {
            "device_id": self.device_id,
            "online": online and self.cua.available(),
            "heartbeat_at": _utc(),
            "fingerprint": self.identity.fingerprint,
            "cua_status": self.cua.status_text()[:240],
            "detail": dict(detail or {}),
        }
        path = self.paths.status / f"{self.device_id}.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    def _app_allowed(self, app: str) -> bool:
        a = app.lower().strip()
        if a in self.allowed_apps:
            return True
        # allow basename match
        return any(a.endswith(x) or x in a for x in self.allowed_apps)

    def execute_grant(self, envelope: Mapping[str, Any]) -> dict[str, Any]:
        try:
            grant = self.consumer.verify_and_consume(envelope)
        except GrantError as exc:
            return {
                "ok": False,
                "error": str(exc),
                "fail_closed": True,
                "device_id": self.device_id,
                "at": _utc(),
            }

        app = grant.app
        if not self._app_allowed(app):
            return {
                "ok": False,
                "error": f"app not allowed: {app}",
                "fail_closed": True,
                "nonce": grant.nonce,
                "device_id": self.device_id,
                "at": _utc(),
            }

        action = str(envelope.get("action") or "launch_and_list")
        if not self.cua.available():
            return {
                "ok": False,
                "error": "cua-driver missing",
                "nonce": grant.nonce,
                "device_id": self.device_id,
                "at": _utc(),
            }

        # Privilege / shell denied by design
        if action in {"shell", "elevate", "install", "admin"}:
            return {
                "ok": False,
                "error": f"privilege action denied: {action}",
                "fail_closed": True,
                "nonce": grant.nonce,
                "device_id": self.device_id,
                "at": _utc(),
            }

        launched = self.cua.call("launch_app", {"name": app})
        if not launched.get("ok", True) and launched.get("error"):
            # try alternate name
            alt = app.replace(".exe", "")
            launched = self.cua.call("launch_app", {"name": alt})

        windows = self.cua.call("list_windows")
        apps = self.cua.call("list_apps")
        ok = bool(launched.get("ok", True)) and "error" not in launched
        return {
            "ok": ok,
            "nonce": grant.nonce,
            "task_id": grant.task_id,
            "app": app,
            "action": action,
            "device_id": self.device_id,
            "launched": launched,
            "window_count": len((windows.get("_legacy_windows") or windows.get("windows") or []))
            if isinstance(windows, dict)
            else 0,
            "apps_sample": _sample_app_names(apps),
            "at": _utc(),
        }

    def process_inbox_once(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for path in sorted(self.paths.inbox.glob("*.json")):
            try:
                envelope = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                results.append({"ok": False, "error": f"bad envelope: {exc}", "path": str(path)})
                continue
            grant = envelope.get("grant") or {}
            if str(grant.get("device_id", "")) not in {"", self.device_id}:
                continue
            result = self.execute_grant(envelope)
            nonce = str(grant.get("nonce") or path.stem)
            out = self.paths.outbox / f"{nonce}.json"
            out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            # archive processed grant
            done = self.paths.inbox / f"{path.name}.done"
            try:
                path.replace(done)
            except Exception:
                path.unlink(missing_ok=True)
            results.append(result)
        return results

    def run_loop(self, *, seconds: float = 0, poll: float = 1.0) -> None:
        """Run until stop or seconds elapsed (0 = forever)."""
        self.write_enrollment_request()
        end = time.time() + seconds if seconds > 0 else None
        while not self._stop:
            self.heartbeat(online=True)
            self.process_inbox_once()
            if end is not None and time.time() >= end:
                break
            time.sleep(poll)

    def stop(self) -> None:
        self._stop = True
        self.heartbeat(online=False, detail={"reason": "stopped"})


def _sample_app_names(apps_payload: Mapping[str, Any]) -> list[str]:
    names: list[str] = []
    apps = apps_payload.get("apps") if isinstance(apps_payload, Mapping) else None
    if isinstance(apps, list):
        for item in apps[:12]:
            if isinstance(item, Mapping) and item.get("name"):
                names.append(str(item["name"]))
    return names
