from __future__ import annotations

import base64
import json
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from .contracts import canonical_json
from .crypto import DeviceKeyPair, HostKeyStore, fingerprint_public_key, sign_payload, verify_payload
from .grants import GrantError, GrantIssuer, GrantRequest, SignedGrant, TaskGrant
from .storage import StateStore


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_ts(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


@dataclass
class BridgePaths:
    root: Path

    def __post_init__(self) -> None:
        for name in ("devices", "inbox", "outbox", "status", "keys", "consumed"):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    @property
    def devices(self) -> Path:
        return self.root / "devices"

    @property
    def inbox(self) -> Path:
        return self.root / "inbox"

    @property
    def outbox(self) -> Path:
        return self.root / "outbox"

    @property
    def status(self) -> Path:
        return self.root / "status"

    @property
    def keys(self) -> Path:
        return self.root / "keys"

    @property
    def consumed(self) -> Path:
        return self.root / "consumed"


class BridgeControlPlane:
    """VPS-side control plane using a filesystem mailbox.

    PC workers connect outbound (e.g. SSH/SCP) and never open inbound ports.
    The VPS never listens for PC CUA ports.
    """

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = Path(state_dir).expanduser()
        self.paths = BridgePaths(self.state_dir / "bridge")
        self.store = StateStore(self.state_dir / "state.db")
        self.host_keys = HostKeyStore(self.paths.keys / "vps")
        self.identity = self.host_keys.load_or_create_identity()
        self.issuer = GrantIssuer(self.store, self.identity)
        # Publish VPS public key for workers
        pub_path = self.paths.keys / "vps_public.json"
        pub_path.write_text(
            json.dumps(
                {
                    "fingerprint": self.identity.fingerprint,
                    "public_key_b64": base64.b64encode(self.identity.public_key_bytes).decode("ascii"),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def enroll_device(
        self,
        device_id: str,
        public_key_bytes: bytes,
        *,
        label: str = "",
    ) -> dict[str, Any]:
        fp = fingerprint_public_key(public_key_bytes)
        with self.store.connect() as conn:
            conn.execute(
                """
                INSERT INTO devices(device_id, public_key, fingerprint, revoked_at)
                VALUES (?,?,?,NULL)
                ON CONFLICT(device_id) DO UPDATE SET
                  public_key=excluded.public_key,
                  fingerprint=excluded.fingerprint,
                  revoked_at=NULL
                """,
                (device_id, public_key_bytes, fp),
            )
        meta = {
            "device_id": device_id,
            "fingerprint": fp,
            "public_key_b64": base64.b64encode(public_key_bytes).decode("ascii"),
            "label": label,
            "enrolled_at": _utc(),
            "revoked": False,
        }
        (self.paths.devices / f"{device_id}.json").write_text(
            json.dumps(meta, indent=2) + "\n", encoding="utf-8"
        )
        return meta

    def revoke_device(self, device_id: str) -> None:
        self.issuer.revoke_device(device_id)
        path = self.paths.devices / f"{device_id}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            data["revoked"] = True
            data["revoked_at"] = _utc()
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def is_device_online(self, device_id: str, *, max_age_seconds: float = 45.0) -> bool:
        path = self.paths.status / f"{device_id}.json"
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return False
        if data.get("revoked"):
            return False
        hb = data.get("heartbeat_at")
        if not hb:
            return False
        age = (datetime.now(timezone.utc) - _parse_ts(str(hb))).total_seconds()
        return age <= max_age_seconds and bool(data.get("online", False))

    def device_status(self, device_id: str) -> dict[str, Any]:
        path = self.paths.status / f"{device_id}.json"
        if not path.exists():
            return {"device_id": device_id, "online": False, "reason": "no_status"}
        data = json.loads(path.read_text(encoding="utf-8"))
        data["online_fresh"] = self.is_device_online(device_id)
        return data

    def post_grant(
        self,
        *,
        task_id: str,
        owner_id: str,
        device_id: str,
        app: str,
        window: str = "",
        action: str = "launch_and_list",
        action_id: str = "",
        parameter_digest: str = "",
        ttl_seconds: int = 900,
    ) -> dict[str, Any]:
        if not self.is_device_online(device_id):
            return {
                "ok": False,
                "error": "pc_offline",
                "postpone": True,
                "device_id": device_id,
            }
        dev_path = self.paths.devices / f"{device_id}.json"
        if not dev_path.exists():
            return {"ok": False, "error": "device_not_enrolled", "device_id": device_id}
        dev = json.loads(dev_path.read_text(encoding="utf-8"))
        if dev.get("revoked"):
            return {"ok": False, "error": "device_revoked", "device_id": device_id}

        req = GrantRequest(
            task_id=task_id,
            action_id=action_id or str(uuid.uuid4()),
            owner_id=owner_id,
            device_id=device_id,
            app=app,
            window=window,
            action_class="cua_run",
            parameter_digest=parameter_digest or f"{action}:{app}:{window}",
            ttl_seconds=ttl_seconds,
        )
        signed = self.issuer.issue(req)
        envelope = {
            "schema": "web-operator/bridge-grant/v1",
            "posted_at": _utc(),
            "action": action,
            "grant": signed.grant.__dict__,
            "signature_b64": base64.b64encode(signed.signature).decode("ascii"),
            "issuer_public_key_b64": base64.b64encode(self.identity.public_key_bytes).decode(
                "ascii"
            ),
            "issuer_fingerprint": self.identity.fingerprint,
        }
        out = self.paths.inbox / f"{signed.grant.nonce}.json"
        out.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
        return {
            "ok": True,
            "nonce": signed.grant.nonce,
            "inbox_path": str(out),
            "app": app,
            "device_id": device_id,
            "expires_at": signed.grant.expires_at,
        }

    def wait_result(
        self,
        nonce: str,
        *,
        timeout_seconds: float = 120.0,
        poll_seconds: float = 0.5,
    ) -> dict[str, Any]:
        path = self.paths.outbox / f"{nonce}.json"
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                return {"ok": True, "result": data, "path": str(path)}
            time.sleep(poll_seconds)
        return {"ok": False, "error": "result_timeout", "nonce": nonce}

    def run_named_app_task(
        self,
        *,
        task_id: str,
        owner_id: str,
        device_id: str,
        app: str,
        window: str = "",
        action: str = "launch_and_list",
        timeout_seconds: float = 120.0,
    ) -> dict[str, Any]:
        posted = self.post_grant(
            task_id=task_id,
            owner_id=owner_id,
            device_id=device_id,
            app=app,
            window=window,
            action=action,
        )
        if not posted.get("ok"):
            return posted
        waited = self.wait_result(str(posted["nonce"]), timeout_seconds=timeout_seconds)
        if not waited.get("ok"):
            return {**posted, **waited, "ok": False}
        result = waited["result"]
        return {
            "ok": bool(result.get("ok")),
            "nonce": posted["nonce"],
            "app": app,
            "device_id": device_id,
            "result": result,
            "postpone": False,
        }


class GrantConsumer:
    """PC-side grant verification with one-time nonce consume."""

    def __init__(self, consumed_dir: Path, device_id: str) -> None:
        self.consumed_dir = Path(consumed_dir)
        self.consumed_dir.mkdir(parents=True, exist_ok=True)
        self.device_id = device_id

    def verify_and_consume(self, envelope: Mapping[str, Any], now: Optional[datetime] = None) -> TaskGrant:
        now = now or datetime.now(timezone.utc)
        grant_raw = envelope.get("grant") or {}
        grant = TaskGrant(**{k: grant_raw[k] for k in TaskGrant.__dataclass_fields__})
        if grant.device_id != self.device_id:
            raise GrantError("device mismatch")
        expires = _parse_ts(grant.expires_at)
        if now >= expires:
            raise GrantError("grant expired")
        sig = base64.b64decode(str(envelope.get("signature_b64", "")))
        pub = base64.b64decode(str(envelope.get("issuer_public_key_b64", "")))
        payload = canonical_json(grant.__dict__).encode("utf-8")
        try:
            verify_payload(payload, sig, pub)
        except Exception as exc:
            raise GrantError("signature invalid") from exc
        marker = self.consumed_dir / f"{grant.nonce}.used"
        if marker.exists():
            raise GrantError("grant replay rejected")
        marker.write_text(_utc() + "\n", encoding="utf-8")
        return grant


def encode_signed_grant(signed: SignedGrant, issuer: DeviceKeyPair, action: str = "launch_and_list") -> dict[str, Any]:
    return {
        "schema": "web-operator/bridge-grant/v1",
        "posted_at": _utc(),
        "action": action,
        "grant": signed.grant.__dict__,
        "signature_b64": base64.b64encode(signed.signature).decode("ascii"),
        "issuer_public_key_b64": base64.b64encode(issuer.public_key_bytes).decode("ascii"),
        "issuer_fingerprint": issuer.fingerprint,
    }
