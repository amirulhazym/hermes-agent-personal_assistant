from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class CryptoError(RuntimeError):
    pass


@dataclass(frozen=True)
class EncryptedBlob:
    nonce: bytes
    ciphertext: bytes


@dataclass(frozen=True)
class DeviceKeyPair:
    private_key_bytes: bytes
    public_key_bytes: bytes
    fingerprint: str


def _require_cryptography():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            NoEncryption,
            PrivateFormat,
            PublicFormat,
        )
    except ImportError as exc:
        raise CryptoError(
            "cryptography package required; install only after explicit approval"
        ) from exc
    return Ed25519PrivateKey, Ed25519PublicKey, AESGCM, Encoding, NoEncryption, PrivateFormat, PublicFormat


class HostKeyStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def load_or_create_identity(self) -> DeviceKeyPair:
        Ed25519PrivateKey, _, _, Encoding, NoEncryption, PrivateFormat, PublicFormat = (
            _require_cryptography()
        )
        priv_path = self.root / "device_ed25519.pem"
        if priv_path.exists():
            from cryptography.hazmat.primitives.serialization import load_pem_private_key

            private = load_pem_private_key(priv_path.read_bytes(), password=None)
        else:
            private = Ed25519PrivateKey.generate()
            pem = private.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
            priv_path.write_bytes(pem)
            try:
                os.chmod(priv_path, 0o600)
            except OSError:
                pass
        public = private.public_key()
        pub_bytes = public.public_bytes(Encoding.Raw, PublicFormat.Raw)
        priv_bytes = private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        return DeviceKeyPair(
            private_key_bytes=priv_bytes,
            public_key_bytes=pub_bytes,
            fingerprint=fingerprint_public_key(pub_bytes),
        )

    def load_or_create_data_key(self) -> bytes:
        path = self.root / "data.key"
        if path.exists():
            return path.read_bytes()
        key = os.urandom(32)
        path.write_bytes(key)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return key


def fingerprint_public_key(public_key: bytes) -> str:
    return hashlib.sha256(public_key).hexdigest()[:16]


def sign_payload(payload: bytes, private_key_bytes: bytes) -> bytes:
    Ed25519PrivateKey, *_ = _require_cryptography()
    key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    return key.sign(payload)


def verify_payload(payload: bytes, signature: bytes, public_key_bytes: bytes) -> None:
    _, Ed25519PublicKey, *_ = _require_cryptography()
    key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    key.verify(signature, payload)


def encrypt_blob(plaintext: bytes, aad: bytes, key: bytes) -> EncryptedBlob:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    _require_cryptography()
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext, aad)
    return EncryptedBlob(nonce=nonce, ciphertext=ct)


def decrypt_blob(blob: EncryptedBlob, aad: bytes, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    _require_cryptography()
    return AESGCM(key).decrypt(blob.nonce, blob.ciphertext, aad)
