#!/usr/bin/env python3
"""Phase 1.4 read-only probe: verify MY account data comes back from the pinned ASIA host.

Prints result codes and field summaries only — never token values.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime

VENDOR = os.path.expanduser("~/hermes-huawei-sync/vendor")
sys.path.insert(0, VENDOR)
import client  # noqa: E402

SECRETS = os.path.expanduser("~/secrets/huawei_tokens.json")
MYT = datetime.now().astimezone()


def save(payload: dict) -> None:
    tmp = SECRETS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, SECRETS)


def main() -> int:
    data = json.load(open(SECRETS, encoding="utf-8"))
    print("token keys:", sorted(data.keys()))
    print("session_host:", data.get("session_host"))
    print("access_expires_in_s:", int(float(data.get("expires_at") or 0) - time.time()))

    tokens = client.Tokens(**data, on_change=lambda t: save(t.as_dict))
    cli = client.HuaweiHealthClient(tokens)
    print("client host:", getattr(cli, "host", "<no attr>"))

    today = int(MYT.strftime("%Y%m%d"))
    start = int(MYT.replace(day=1).strftime("%Y%m%d"))

    def show(label, fn):
        try:
            out = fn()
        except client.HuaweiApiError as exc:
            print(f"[{label}] API_ERROR resultCode={exc.code} :: {str(exc)[:200]}")
            return None
        except client.HuaweiError as exc:
            print(f"[{label}] ERROR {type(exc).__name__}: {str(exc)[:200]}")
            return None
        except Exception as exc:  # noqa: BLE001
            print(f"[{label}] EXC {type(exc).__name__}: {str(exc)[:200]}")
            return None
        code = client._result_code(out) if isinstance(out, dict) else "n/a"
        keys = list(out.keys())[:12] if isinstance(out, dict) else f"list[{len(out)}]"
        print(f"[{label}] OK resultCode={code} keys={keys}")
        return out

    show("bind_devices", cli.bind_devices)
    stat = show("sports_stat(today)", lambda: cli.sports_stat(today, today))
    if isinstance(stat, dict):
        body = stat.get("sportBasicInfo") or stat
        print("  sports_stat sample:", json.dumps(
            {k: body.get(k) for k in list(body)[:14] if not isinstance(body.get(k), (dict, list))},
            ensure_ascii=False)[:600])

    hs = show("health_stat(today, 7/9/11/12)", lambda: cli.health_stat(today, today, (7, 9, 11, 12)))
    if isinstance(hs, dict):
        print("  health_stat top keys:", list(hs.keys())[:14])

    show("daily_summary(3)", lambda: cli.daily_summary(3))
    show("health_summary(3)", lambda: cli.health_summary(3))
    show("sessions(7)", lambda: cli.sessions(7))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
