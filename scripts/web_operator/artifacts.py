from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from .contracts import ExecutionLevel, OutcomeLabel, TaskState, canonical_json
from .network import DestinationGuard


class SensitiveEvidenceError(RuntimeError):
    pass


_SECRETISH = re.compile(
    r"(password|otp|cookie|authorization|api[_-]?key|card\s*number|cvv)",
    re.I,
)


@dataclass
class ExecutionEvent:
    ts: str
    kind: str
    level: str = ""
    detail: Mapping[str, Any] = field(default_factory=dict)


class ArtifactSink:
    def __init__(
        self,
        root: Path,
        *,
        medical: bool = False,
        guard: Optional[DestinationGuard] = None,
        retention_days: int = 14,
    ) -> None:
        self.root = root
        self.medical = medical
        self.guard = guard or DestinationGuard()
        self.retention_days = retention_days
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_path = self.root / "events.jsonl"
        self.final_path = self.root / "result.json"
        self._events: list[ExecutionEvent] = []

    def record_event(self, event: ExecutionEvent) -> None:
        detail = dict(event.detail)
        text = json.dumps(detail, default=str)
        if _SECRETISH.search(text):
            raise SensitiveEvidenceError("secret-like content blocked from artifacts")
        if "url" in detail and isinstance(detail["url"], str):
            detail["url"] = self.guard.normalize_for_artifact(detail["url"])
        clean = ExecutionEvent(
            ts=event.ts,
            kind=event.kind,
            level=event.level,
            detail=detail,
        )
        self._events.append(clean)
        if self.medical:
            # medical mode: metadata only later; no ordinary event dump of page content
            return
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(canonical_json(asdict(clean)) + "\n")

    def attach_redacted_evidence(self, name: str, content: bytes) -> Path:
        if self.medical:
            raise SensitiveEvidenceError("medical mode forbids ordinary evidence files")
        if b"password" in content.lower() or b"otp" in content.lower():
            raise SensitiveEvidenceError("raw secret content rejected")
        path = self.root / name
        path.write_bytes(content)
        return path

    def finalize(
        self,
        *,
        task_id: str,
        state: TaskState,
        level: ExecutionLevel,
        label: OutcomeLabel,
        summary: str,
        route: list[str],
        error: str = "",
    ) -> Optional[Path]:
        if self.medical:
            meta = {
                "schema": "web-operator/medical-audit/v1",
                "task_id": task_id,
                "outcome": label.value,
                "route": route,
                "event_kinds": [e.kind for e in self._events],
                "summary": "medical-metadata-only",
            }
            path = self.root / "medical-audit.json"
            path.write_text(canonical_json(meta) + "\n", encoding="utf-8")
            return path
        payload = {
            "schema": "web-operator/result/v1",
            "task_id": task_id,
            "state": state.value,
            "level": level.value,
            "label": label.value,
            "summary": summary,
            "route": route,
            "error": error,
            "events": len(self._events),
        }
        self.final_path.write_text(canonical_json(payload) + "\n", encoding="utf-8")
        return self.final_path

    def purge_expired(self, now: Optional[datetime] = None) -> dict[str, int]:
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(days=self.retention_days)
        removed = 0
        for child in self.root.parent.iterdir() if self.root.parent.exists() else []:
            if not child.is_dir():
                continue
            marker = child / "result.json"
            if not marker.exists():
                continue
            mtime = datetime.fromtimestamp(marker.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
        return {"removed": removed}
