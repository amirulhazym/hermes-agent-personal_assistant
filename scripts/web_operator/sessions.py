from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .contracts import SessionIdentity, canonical_json
from .crypto import EncryptedBlob, HostKeyStore, decrypt_blob, encrypt_blob
from .storage import StateStore


class SessionError(RuntimeError):
    pass


def identity_digest(identity: SessionIdentity) -> str:
    raw = canonical_json(
        {
            "site": identity.site,
            "account": identity.account,
            "profile": identity.profile,
            "execution_device": identity.execution_device,
        }
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass
class SessionRecord:
    identity: SessionIdentity
    mode: str
    expires_at: Optional[datetime]
    revoked: bool = False


@dataclass
class SessionLease:
    identity_digest: str
    locked: bool = True


class SessionStore:
    def __init__(self, store: StateStore, keys: HostKeyStore, profiles_dir: Path) -> None:
        self.store = store
        self.keys = keys
        self.profiles_dir = profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._leases: set[str] = set()

    def enroll(
        self,
        identity: SessionIdentity,
        mode: str = "one_time",
        *,
        profile_bytes: bytes = b"",
        ttl_hours: Optional[int] = None,
        financial: bool = False,
    ) -> SessionRecord:
        if financial:
            raise SessionError("financial sessions must never be persisted")
        if mode not in {"one_time", "persistent"}:
            raise SessionError("mode must be one_time or persistent")
        digest = identity_digest(identity)
        expires = None
        if ttl_hours is not None:
            expires = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        data_key = self.keys.load_or_create_data_key()
        aad = digest.encode("utf-8")
        blob = encrypt_blob(profile_bytes, aad, data_key)
        profile_path = self.profiles_dir / f"{digest}.bin"
        profile_path.write_bytes(blob.nonce + blob.ciphertext)
        meta = {
            "identity": {
                "site": identity.site,
                "account": identity.account,
                "profile": identity.profile,
                "execution_device": identity.execution_device,
            },
            "mode": mode,
            "expires_at": expires.isoformat().replace("+00:00", "Z") if expires else None,
        }
        with self.store.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions(identity_digest, metadata_json, expires_at, revoked_at)
                VALUES (?,?,?,NULL)
                """,
                (
                    digest,
                    json.dumps(meta, sort_keys=True),
                    meta["expires_at"],
                ),
            )
        return SessionRecord(identity=identity, mode=mode, expires_at=expires, revoked=False)

    def acquire(self, identity: SessionIdentity) -> SessionLease:
        digest = identity_digest(identity)
        if digest in self._leases:
            raise SessionError("session already leased")
        with self.store.connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE identity_digest=?",
                (digest,),
            ).fetchone()
            if row is None:
                raise SessionError("session not enrolled")
            if row["revoked_at"]:
                raise SessionError("session revoked")
        self._leases.add(digest)
        return SessionLease(identity_digest=digest, locked=True)

    def release(self, lease: SessionLease) -> None:
        self._leases.discard(lease.identity_digest)

    def revoke(self, identity: SessionIdentity) -> dict[str, str]:
        digest = identity_digest(identity)
        profile_path = self.profiles_dir / f"{digest}.bin"
        if profile_path.exists():
            profile_path.unlink()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self.store.connect() as conn:
            conn.execute(
                "UPDATE sessions SET revoked_at=? WHERE identity_digest=?",
                (now, digest),
            )
        self._leases.discard(digest)
        return {"identity_digest": digest, "revoked_at": now, "profile_deleted": "true"}

    def load_profile(self, identity: SessionIdentity) -> bytes:
        digest = identity_digest(identity)
        path = self.profiles_dir / f"{digest}.bin"
        if not path.exists():
            raise SessionError("profile missing")
        raw = path.read_bytes()
        blob = EncryptedBlob(nonce=raw[:12], ciphertext=raw[12:])
        return decrypt_blob(blob, digest.encode("utf-8"), self.keys.load_or_create_data_key())
