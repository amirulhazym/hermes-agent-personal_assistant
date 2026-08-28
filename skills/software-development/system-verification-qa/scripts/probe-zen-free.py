#!/usr/bin/env python3
"""Live-probe every FREE model on the opencode-zen provider.

Usage:
    python3 scripts/probe-zen-free.py

Loads OPENCODE_ZEN_API_KEY from ~/.hermes/.env (NOT os.getenv only — the key
lives in .env, not auth.json). Fetches /v1/models, filters *-free, probes each
with max_tokens=100 (small budgets give empty content on reasoning models),
and prints wire-shape details. Use max_tokens>=100 and inspect message keys to
tell reasoning_content vs reasoning vs refusal models apart.
"""
import os, sys, time, json

BASE = "https://opencode.ai/zen/v1"

def load_key():
    env_path = os.path.expanduser("~/.hermes/.env")
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENCODE_ZEN_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return os.getenv("OPENCODE_ZEN_API_KEY", "")

KEY = load_key()
if not KEY:
    print("❌ No OPENCODE_ZEN_API_KEY found (checked ~/.hermes/.env and env)")
    sys.exit(1)

headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

# requests works from this VPS (2026-08-24). If you hit Cloudflare 403,
# fall back to curl_cffi with impersonate="chrome120".
try:
    import requests
    def post(url, body, timeout=60):
        return requests.post(url, headers=headers, json=body, timeout=timeout)
    def get(url, timeout=20):
        return requests.get(url, headers=headers, timeout=timeout)
    MODE = "requests"
except ImportError:
    import curl_cffi.requests as cr
    def post(url, body, timeout=60):
        return cr.post(url, headers=headers, json=body, timeout=timeout, impersonate="chrome120")
    def get(url, timeout=20):
        return cr.get(url, headers=headers, timeout=timeout, impersonate="chrome120")
    MODE = "curl_cffi"

print(f"[http] using {MODE}")

r = get(f"{BASE}/models")
print(f"[models] HTTP {r.status_code}")
if r.status_code != 200:
    print("  body:", r.text[:300])
    sys.exit(1)
data = r.json()
models = data.get("data", data) if isinstance(data, dict) else data
ids = [m["id"] if isinstance(m, dict) else m for m in models]
print(f"[models] total {len(ids)}")

# Free models from live catalog + always-check known curated free ids
free_ids = [i for i in ids if "free" in i.lower() or i.startswith("x-preview")]
for m in [
    "deepseek-v4-flash-free", "mimo-v2.5-free", "nemotron-3-ultra-free",
    "nemotron-3.5-lightning-free", "hy3-free", "north-mini-code-free",
    "muse-spark-1.2-contributor-free", "laguna-s-2.1-free", "x-preview-f-free",
    "minimax-m3-free", "qwen3.6-plus-free",
]:
    if m not in free_ids:
        free_ids.append(m)

print(f"\n[free] {len(free_ids)} to probe: {free_ids}\n")

results = {}
for m in free_ids:
    payload = {
        "model": m,
        "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
        "max_tokens": 100,
    }
    try:
        t0 = time.time()
        resp = post(f"{BASE}/chat/completions", payload)
        dt = time.time() - t0
        if resp.status_code == 200:
            j = resp.json()
            ch = j.get("choices", [{}])[0]
            msg = ch.get("message", {})
            content = (msg.get("content") or "")[:40]
            keys = list(msg.keys())
            fin = ch.get("finish_reason")
            results[m] = ("✅ 200", dt, content, keys, fin)
            print(f"  ✅ {m}: 200 in {dt:.1f}s finish={fin} content={content!r} keys={keys}")
        else:
            err = ""
            try:
                err = resp.json().get("error", {})
                err = err.get("message", "") if isinstance(err, dict) else str(err)
            except Exception:
                err = resp.text[:120]
            results[m] = (f"❌ {resp.status_code}", dt, err, [], None)
            print(f"  ❌ {m}: HTTP {resp.status_code} in {dt:.1f}s -> {err[:120]}")
    except Exception as e:
        results[m] = ("❌ EXC", 0, str(e), [], None)
        print(f"  ❌ {m}: EXCEPTION -> {e}")
    time.sleep(0.5)

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
working = [k for k, v in results.items() if v[0] == "✅ 200"]
dead = [k for k, v in results.items() if v[0] != "✅ 200"]
print(f"Working ({len(working)}): {working}")
print(f"Dead/Errored ({len(dead)}):")
for k in dead:
    st, dt, err, _, _ = results[k]
    print(f"  - {k}: {st} {err[:90]}")
