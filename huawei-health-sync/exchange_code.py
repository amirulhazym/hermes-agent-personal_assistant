#!/usr/bin/env python3
"""Exchange a captured Huawei authorization code for tokens and store them atomically.

Usage:
    python3 exchange_code.py "<pasted redirect line or bare code>"

Writes ~/secrets/huawei_tokens.json (chmod 600) via temp-file + fsync + os.replace.
Never prints token values.
"""
from __future__ import annotations

import json
import os
import sys
import time

VENDOR = os.path.expanduser("~/hermes-huawei-sync/vendor")
sys.path.insert(0, VENDOR)
import client  # noqa: E402  (vendored, stdlib-only)

SECRETS = os.path.expanduser("~/secrets/huawei_tokens.json")


def save_atomic(payload: dict) -> None:
    tmp = SECRETS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, SECRETS)


def main(argv: list[str]) -> int:
    raw = " ".join(argv[1:]).strip()
    if not raw:
        print("USAGE: exchange_code.py \"<redirect line or code>\"")
        return 64

    code = client.authorization_code_from(raw)
    if not code:
        print("NO_CODE_FOUND in pasted text")
        return 65
    print(f"code_len={len(code)}")

    try:
        tokens = client.exchange_authorization_code(code)
    except client.HuaweiApiError as exc:
        print(f"EXCHANGE_FAILED resultCode={exc.code} msg={exc}")
        return 2
    except client.HuaweiError as exc:
        print(f"EXCHANGE_FAILED {type(exc).__name__}: {exc}")
        return 3

    data = tokens.as_dict
    data = dict(data() if callable(data) else data)
    save_atomic(data)

    exp = float(data.get("expires_at") or 0)
    print("SAVED keys=", sorted(data.keys()))
    print("HAS_RT=", bool(data.get("refresh_token")))
    print("uid_present=", bool(data.get("uid")))
    print("session_host=", data.get("session_host"))
    print("access_expires_in_s=", int(exp - time.time()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
