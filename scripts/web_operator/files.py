from __future__ import annotations

import hashlib
import mimetypes
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Optional

from .contracts import FileDescriptor


class FileError(RuntimeError):
    pass


SAFE_TYPES = {
    "text/plain",
    "text/csv",
    "application/pdf",
    "application/json",
}


@dataclass
class QuarantinedFile:
    item_id: str
    expected: FileDescriptor
    path: Path


@dataclass
class InspectedFile:
    item_id: str
    expected: FileDescriptor
    actual: FileDescriptor
    path: Path
    safe: bool
    reason: str = ""


class QuarantineStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def receive(self, expected: FileDescriptor, stream: BinaryIO) -> QuarantinedFile:
        item_id = str(uuid.uuid4())
        path = self.root / f"{item_id}.part"
        data = stream.read()
        path.write_bytes(data)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return QuarantinedFile(item_id=item_id, expected=expected, path=path)

    def inspect(self, item: QuarantinedFile) -> InspectedFile:
        data = item.path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        guessed, _ = mimetypes.guess_type(item.expected.filename)
        content_type = guessed or item.expected.content_type or "application/octet-stream"
        actual = FileDescriptor(
            filename=item.expected.filename,
            content_type=content_type,
            size_bytes=len(data),
            sha256=digest,
            source=item.expected.source,
            purpose=item.expected.purpose,
        )
        reason = ""
        safe = True
        if item.expected.sha256 and item.expected.sha256 != digest:
            safe = False
            reason = "sha256 mismatch"
        if item.expected.size_bytes and item.expected.size_bytes != len(data):
            safe = False
            reason = (reason + "; " if reason else "") + "size mismatch"
        if content_type not in SAFE_TYPES and not content_type.startswith("text/"):
            # allow expected type if explicitly declared safe text/pdf/csv/json only
            if item.expected.content_type not in SAFE_TYPES:
                safe = False
                reason = (reason + "; " if reason else "") + "unsafe content type"
        if b"MZ" == data[:2]:
            safe = False
            reason = (reason + "; " if reason else "") + "executable signature"
        return InspectedFile(
            item_id=item.item_id,
            expected=item.expected,
            actual=actual,
            path=item.path,
            safe=safe,
            reason=reason,
        )

    def release(self, item: InspectedFile, *, approved: bool) -> Path:
        if not approved:
            raise FileError("release requires second approval")
        if not item.safe:
            raise FileError(f"unsafe file cannot be released: {item.reason}")
        final = item.path.with_suffix(".bin")
        item.path.replace(final)
        return final


def describe_existing_upload(path: Path, *, source: str = "", purpose: str = "") -> FileDescriptor:
    data = path.read_bytes()
    guessed, _ = mimetypes.guess_type(path.name)
    return FileDescriptor(
        filename=path.name,
        content_type=guessed or "application/octet-stream",
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        source=source,
        purpose=purpose,
    )
