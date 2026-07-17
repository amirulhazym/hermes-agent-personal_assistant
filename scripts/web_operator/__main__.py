from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

from .adapters.http import HttpExecutor
from .adapters.native_browser import NativeBrowserExecutor
from .adapters.research import ResearchExecutor
from .approvals import ApprovalStore
from .config import load_config
from .contracts import ExecutionLevel, SensitivityMode, TaskRequest
from .coordinator import WebOperator
from .network import DestinationGuard
from .policy import PolicyEngine
from .storage import StateStore


def _build_operator(config_path: Path, *, allow_fixture: bool) -> WebOperator:
    config = load_config(config_path, allow_fixture=allow_fixture)
    state_dir = Path(config.state_dir).expanduser()
    store = StateStore(state_dir / "state.db")
    policy = PolicyEngine()
    approvals = ApprovalStore(store, policy)
    guard = DestinationGuard(
        allowed_schemes=config.allowed_schemes,
        deny_private=config.deny_private_destinations,
        fixture_mode=config.fixture_mode,
        max_redirects=config.max_redirects,
    )
    executors = {
        ExecutionLevel.L1: HttpExecutor(guard, max_bytes=config.max_response_bytes),
        ExecutionLevel.L2: ResearchExecutor(),
        ExecutionLevel.L3: NativeBrowserExecutor(guard),
    }
    return WebOperator(
        config=config,
        store=store,
        policy=policy,
        approvals=approvals,
        guard=guard,
        executors=executors,
        artifact_root=state_dir / "artifacts",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scripts.web_operator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_status = sub.add_parser("status")
    p_status.add_argument("--config", required=True)
    p_status.add_argument("--task-id", required=True)

    p_cancel = sub.add_parser("cancel")
    p_cancel.add_argument("--config", required=True)
    p_cancel.add_argument("--task-id", required=True)

    p_purge = sub.add_parser("purge-expired")
    p_purge.add_argument("--config", required=True)

    p_run = sub.add_parser("run")
    p_run.add_argument("--config", required=True)
    p_run.add_argument("--request", required=True, help="path to TaskRequest JSON")

    args = parser.parse_args(argv)
    config_path = Path(args.config)

    if args.cmd == "run":
        # fixture-only path: production config validation rejects fixture_mode
        op = _build_operator(config_path, allow_fixture=True)
        if not op.config.fixture_mode:
            print("run requires fixture_mode config", file=sys.stderr)
            return 2
        payload = json.loads(Path(args.request).read_text(encoding="utf-8"))
        req = TaskRequest(
            task_id=payload.get("task_id", ""),
            owner_id=payload.get("owner_id", "owner"),
            channel=payload.get("channel", "cli"),
            text=payload.get("text", ""),
            sensitivity=SensitivityMode(payload.get("sensitivity", "ordinary")),
        )
        result = asyncio.run(op.submit(req))
        print(json.dumps(result, indent=2))
        return 0

    op = _build_operator(config_path, allow_fixture=False)
    if args.cmd == "status":
        result = asyncio.run(op.status(args.task_id))
        print(json.dumps(result, indent=2))
        return 0
    if args.cmd == "cancel":
        result = asyncio.run(op.cancel(args.task_id))
        print(json.dumps(result, indent=2))
        return 0
    if args.cmd == "purge-expired":
        from .artifacts import ArtifactSink

        sink = ArtifactSink(Path(op.config.state_dir).expanduser() / "artifacts" / "_keeper")
        print(json.dumps(sink.purge_expired(), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
