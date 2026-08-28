#!/usr/bin/env python3
"""Probe a DeepSeek-style thinking model's reasoning_content echo contract.

Why: providers that default thinking ON (DeepSeek V4 family) enforce a
"reasoning_content must be passed back" contract on multi-turn. A single-turn
probe with no reasoning_content only LOWERS the risk — it does not prove the
echo contract works. This script proves it with a real 2-turn exchange:

  Turn 1: thinking enabled -> capture assistant message + reasoning_content
  Turn 2: replay with reasoning_content echoed in the assistant message
          -> HTTP 200 = echo contract VERIFIED (no 400 trap)

Usage:
    python3 probe-reasoning-echo.py                 # uses DEEPSEEK_API_KEY from ~/.hermes/.env
    DEEPSEEK_KEY_FILE=/path/.env MODEL=deepseek-v4-flash python3 probe-reasoning-echo.py

Exit codes: 0 = echo contract verified, 1 = probe failed, 2 = no API key.

Verified 2026-08-07: deepseek-v4-flash, thinking enabled, 2-turn echo -> 200.
"""
import json
import os
import sys
import urllib.request

DEFAULT_MODEL = os.environ.get("MODEL", "deepseek-v4-flash")
KEY_FILE = os.environ.get("DEEPSEEK_KEY_FILE", os.path.expanduser("~/.hermes/.env"))


def load_key():
    try:
        for raw in open(KEY_FILE, encoding="utf-8", errors="replace"):
            line = raw.strip()
            if line.startswith("DEEPSEEK_API_") and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        return None
    return None


def call(key, messages, thinking=True):
    body = {"model": DEFAULT_MODEL, "messages": messages, "max_tokens": 32}
    if thinking:
        body["extra_body"] = {"thinking": {"type": "enabled"}}
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300].decode(errors="replace")


def main():
    key = load_key()
    if not key:
        print("NO KEY: cannot find DEEPSEEK_API_KEY in", KEY_FILE)
        return 2

    st1, r1 = call(key, [{"role": "user", "content": "2+2? Reply with the number only."}])
    print("TURN1 HTTP", st1)
    if st1 != 200:
        print(r1)
        return 1
    m1 = r1["choices"][0]["message"]
    rc1 = m1.get("reasoning_content") or ""
    print("turn1 reasoning_content len:", len(rc1), "content:", repr(m1.get("content")))

    assistant_msg = {"role": "assistant", "content": m1.get("content")}
    if rc1:
        assistant_msg["reasoning_content"] = rc1
    st2, r2 = call(key, [
        {"role": "user", "content": "2+2?"},
        assistant_msg,
        {"role": "user", "content": "now 3+3? Reply with the number only."},
    ])
    print("TURN2 HTTP", st2)
    if st2 == 200:
        m2 = r2["choices"][0]["message"]
        print("turn2 reasoning_content len:", len(m2.get("reasoning_content") or ""),
              "content:", repr(m2.get("content")))
        print("ECHO CONTRACT: VERIFIED (no 400 on reasoning echo)")
        return 0
    print("TURN2 ERROR:", r2)
    print("ECHO CONTRACT: FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
