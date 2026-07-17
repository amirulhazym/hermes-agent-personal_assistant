from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
from pathlib import Path

from .bridge import BridgeControlPlane
from .config import default_config_dict, load_config
from .contracts import SensitivityMode, TaskRequest
from .factory import build_operator, live_wire_report
from .pc_worker_runtime import PcWorkerRuntime


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

    p_live = sub.add_parser("run-live")
    p_live.add_argument("--config", required=True)
    p_live.add_argument("--text", required=True)
    p_live.add_argument("--owner-id", default="owner")
    p_live.add_argument("--channel", default="cli")
    p_live.add_argument("--task-id", default="")
    p_live.add_argument("--sensitivity", default="ordinary")

    p_wire = sub.add_parser("wire-status")

    p_write = sub.add_parser("write-default-config")
    p_write.add_argument("--path", required=True)

    p_enroll = sub.add_parser("bridge-enroll")
    p_enroll.add_argument("--config", required=True)
    p_enroll.add_argument("--device-id", required=True)
    p_enroll.add_argument("--public-key-b64", required=True)
    p_enroll.add_argument("--label", default="")

    p_bst = sub.add_parser("bridge-status")
    p_bst.add_argument("--config", required=True)
    p_bst.add_argument("--device-id", default="")

    p_worker = sub.add_parser("worker-loop")
    p_worker.add_argument("--bridge-root", required=True)
    p_worker.add_argument("--device-id", default="")
    p_worker.add_argument("--seconds", type=float, default=0)
    p_worker.add_argument("--poll", type=float, default=1.0)
    p_worker.add_argument(
        "--cua-exe",
        default=r"C:\Users\amiru\AppData\Local\Programs\Cua\cua-driver\bin\cua-driver.exe",
    )

    args = parser.parse_args(argv)

    if args.cmd == "wire-status":
        print(json.dumps(live_wire_report(), indent=2))
        return 0

    if args.cmd == "write-default-config":
        path = Path(args.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = default_config_dict()
        try:
            import yaml  # type: ignore

            path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        except ImportError:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(json.dumps({"written": str(path)}))
        return 0

    if args.cmd == "worker-loop":
        rt = PcWorkerRuntime(
            Path(args.bridge_root),
            device_id=args.device_id,
            cua_exe=args.cua_exe,
        )
        print(json.dumps({"device_id": rt.device_id, "enroll": rt.enroll_payload()}, indent=2))
        rt.run_loop(seconds=args.seconds, poll=args.poll)
        return 0

    config_path = Path(args.config)

    if args.cmd == "bridge-enroll":
        cfg = load_config(config_path, allow_fixture=False)
        plane = BridgeControlPlane(Path(cfg.state_dir))
        pub = base64.b64decode(args.public_key_b64)
        meta = plane.enroll_device(args.device_id, pub, label=args.label)
        print(json.dumps(meta, indent=2))
        return 0

    if args.cmd == "bridge-status":
        cfg = load_config(config_path, allow_fixture=False)
        plane = BridgeControlPlane(Path(cfg.state_dir))
        if args.device_id:
            print(json.dumps(plane.device_status(args.device_id), indent=2))
        else:
            devices = []
            for p in sorted(plane.paths.devices.glob("*.json")):
                if p.name.endswith(".request.json"):
                    continue
                d = json.loads(p.read_text(encoding="utf-8"))
                d["online"] = plane.is_device_online(d.get("device_id", p.stem))
                devices.append(d)
            print(json.dumps({"devices": devices}, indent=2))
        return 0

    if args.cmd == "run":
        op = build_operator(config_path, allow_fixture=True, wire_live=False)
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

    if args.cmd == "run-live":
        op = build_operator(config_path, allow_fixture=False, wire_live=True)
        if op.config.fixture_mode:
            print("run-live forbids fixture_mode", file=sys.stderr)
            return 2
        req = TaskRequest(
            task_id=args.task_id,
            owner_id=args.owner_id,
            channel=args.channel,
            text=args.text,
            sensitivity=SensitivityMode(args.sensitivity),
        )
        result = asyncio.run(op.submit(req))
        result["wire"] = live_wire_report()
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("state") == "completed" else 1

    op = build_operator(config_path, allow_fixture=False, wire_live=True)
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
