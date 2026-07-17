from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, MutableMapping


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class OperatorConfig:
    schema: str = "web-operator/v1"
    state_dir: str = "~/.hermes/web-operator"
    max_l3_actions: int = 30
    max_l3_active_seconds: int = 600
    operation_timeout_seconds: int = 180
    approval_ttl_seconds: int = 900
    production_l3_concurrency: int = 1
    deny_private_destinations: bool = True
    allowed_schemes: tuple[str, ...] = ("https", "http")
    max_redirects: int = 5
    max_response_bytes: int = 2_000_000
    fixture_mode: bool = False
    artifacts_enabled: bool = True
    retention_days: int = 14
    raw_frame_retention_seconds: int = 0
    financial_persistence: bool = False
    medical_audit_retention_days: int = 14
    medical_ordinary_artifacts: bool = False
    pc_worker_enabled: bool = False
    pc_device_id: str = ""
    pc_transport: str = ""


def _as_bool(value: Any, key: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ConfigError(f"{key} must be boolean")


def _as_int(value: Any, key: str) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise ConfigError(f"{key} must be integer")


def validate_config(config: OperatorConfig, *, allow_fixture: bool = False) -> None:
    if config.max_l3_actions <= 0:
        raise ConfigError("max_l3_actions must be > 0")
    if config.max_l3_active_seconds <= 0:
        raise ConfigError("max_l3_active_seconds must be > 0")
    if config.operation_timeout_seconds <= 0:
        raise ConfigError("operation_timeout_seconds must be > 0")
    if config.approval_ttl_seconds <= 0:
        raise ConfigError("approval_ttl_seconds must be > 0")
    if config.production_l3_concurrency not in (1, 2, 3):
        raise ConfigError("production_l3_concurrency must be 1, 2, or 3")
    if config.fixture_mode and not allow_fixture:
        raise ConfigError("fixture_mode is forbidden in production config")
    if config.raw_frame_retention_seconds != 0:
        raise ConfigError("raw_frame_retention_seconds must be 0")


def _load_mapping(path: Path) -> Mapping[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ConfigError("PyYAML required for YAML config") from exc
        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)
    if not isinstance(data, MutableMapping):
        raise ConfigError("config root must be a mapping")
    return data


def load_config(path: Path, *, allow_fixture: bool = False) -> OperatorConfig:
    data = _load_mapping(path)
    unknown = set(data) - {
        "schema",
        "runtime",
        "network",
        "artifacts",
        "sessions",
        "medical",
        "pc_worker",
    }
    if unknown:
        raise ConfigError(f"unknown top-level keys: {sorted(unknown)}")

    runtime = data.get("runtime", {}) or {}
    network = data.get("network", {}) or {}
    artifacts = data.get("artifacts", {}) or {}
    sessions = data.get("sessions", {}) or {}
    medical = data.get("medical", {}) or {}
    pc_worker = data.get("pc_worker", {}) or {}

    schemes = network.get("allowed_schemes", ["https", "http"])
    if not isinstance(schemes, list) or not all(isinstance(s, str) for s in schemes):
        raise ConfigError("network.allowed_schemes must be a list of strings")

    config = OperatorConfig(
        schema=str(data.get("schema", "web-operator/v1")),
        state_dir=str(runtime.get("state_dir", "~/.hermes/web-operator")),
        max_l3_actions=_as_int(runtime.get("max_l3_actions", 30), "max_l3_actions"),
        max_l3_active_seconds=_as_int(
            runtime.get("max_l3_active_seconds", 600), "max_l3_active_seconds"
        ),
        operation_timeout_seconds=_as_int(
            runtime.get("operation_timeout_seconds", 180), "operation_timeout_seconds"
        ),
        approval_ttl_seconds=_as_int(
            runtime.get("approval_ttl_seconds", 900), "approval_ttl_seconds"
        ),
        production_l3_concurrency=_as_int(
            runtime.get("production_l3_concurrency", 1), "production_l3_concurrency"
        ),
        deny_private_destinations=_as_bool(
            network.get("deny_private_destinations", True), "deny_private_destinations"
        ),
        allowed_schemes=tuple(schemes),
        max_redirects=_as_int(network.get("max_redirects", 5), "max_redirects"),
        max_response_bytes=_as_int(
            network.get("max_response_bytes", 2_000_000), "max_response_bytes"
        ),
        fixture_mode=_as_bool(network.get("fixture_mode", False), "fixture_mode"),
        artifacts_enabled=_as_bool(artifacts.get("enabled", True), "artifacts.enabled"),
        retention_days=_as_int(artifacts.get("retention_days", 14), "retention_days"),
        raw_frame_retention_seconds=_as_int(
            artifacts.get("raw_frame_retention_seconds", 0),
            "raw_frame_retention_seconds",
        ),
        financial_persistence=_as_bool(
            sessions.get("financial_persistence", False), "financial_persistence"
        ),
        medical_audit_retention_days=_as_int(
            medical.get("audit_retention_days", 14), "medical.audit_retention_days"
        ),
        medical_ordinary_artifacts=_as_bool(
            medical.get("ordinary_artifacts", False), "medical.ordinary_artifacts"
        ),
        pc_worker_enabled=_as_bool(pc_worker.get("enabled", False), "pc_worker.enabled"),
        pc_device_id=str(pc_worker.get("device_id", "")),
        pc_transport=str(pc_worker.get("transport", "")),
    )
    validate_config(config, allow_fixture=allow_fixture)
    return config


def default_config_dict() -> dict[str, Any]:
    return {
        "schema": "web-operator/v1",
        "runtime": {
            "state_dir": "~/.hermes/web-operator",
            "max_l3_actions": 30,
            "max_l3_active_seconds": 600,
            "operation_timeout_seconds": 180,
            "approval_ttl_seconds": 900,
            "production_l3_concurrency": 1,
        },
        "network": {
            "allowed_schemes": ["https", "http"],
            "deny_private_destinations": True,
            "max_redirects": 5,
            "max_response_bytes": 2000000,
            "fixture_mode": False,
        },
        "artifacts": {
            "enabled": True,
            "retention_days": 14,
            "raw_frame_retention_seconds": 0,
        },
        "sessions": {"financial_persistence": False},
        "medical": {"audit_retention_days": 14, "ordinary_artifacts": False},
        "pc_worker": {"enabled": False, "device_id": "", "transport": ""},
    }
