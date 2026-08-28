#!/usr/bin/env python3.12
"""Probe reasoning effort across models and providers.

Live-verifies that reasoning_effort values are accepted by the API and returns
actual reasoning token counts. Uses curl_cffi for TLS fingerprinting (required
to bypass Cloudflare on opencode-* endpoints from VPS IPs).

Usage:
    python3.12 scripts/probe-reasoning-effort.py --provider opencode-go --model deepseek-v4-flash
    python3.12 scripts/probe-reasoning-effort.py --provider opencode-zen --effort xhigh,medium

Without arguments, probes all default models with all default effort levels.

Output: table showing HTTP status, timing, reasoning tokens, and content
for each (model x effort) combination.
"""

import json
import os
import re
import sys
import time

# -- Config ---------------------------------------------------------------
DEFAULT_MODELS = {
    "opencode-go": ["deepseek-v4-flash", "deepseek-v4-pro"],
    "opencode-zen": ["deepseek-v4-flash-free", "mimo-v2.5-free", "nemotron-3-ultra-free", "hy3-free"],
}

DEFAULT_EFFORTS = ["xhigh", "medium", "low", "max", None]  # None = no field

PROVIDER_CONFIG = {
    "opencode-go": {
        "base_url": "https://opencode.ai/zen/go/v1",
        "env_var": "OPENCODE_GO_API_KEY",
    },
    "opencode-zen": {
        "base_url": "https://opencode.ai/zen/v1",
        "env_var": "OPENCODE_ZEN_API_KEY",
    },
}


def load_api_key(env_var: str) -> str:
    env_path = os.path.expanduser("~/.hermes/.env")
    with open(env_path) as f:
        content = f.read()
    m = re.search(rf"{env_var}[=]\s*(\S+)", content)
    if not m:
        raise SystemExit(f"ERROR: {env_var} not found in .env")
    return m.group(1).strip().strip('"').strip("'")


try:
    from curl_cffi import requests
    USE_CFFI = True
except ImportError:
    import requests as _requests_mod
    requests = _requests_mod
    USE_CFFI = False


def probe(base_url: str, api_key: str, model: str, effort: str | None,
           prompt: str = "What is 2+2? Just answer the number.") -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "stream": False,
    }
    if effort:
        body["reasoning_effort"] = effort

    kwargs = {
        "json": body,
        "headers": {"Authorization": f"Bearer {api_key}"},
        "timeout": 60,
    }
    if USE_CFFI:
        kwargs["impersonate"] = "chrome120"

    start = time.time()
    try:
        resp = requests.post(f"{base_url}/chat/completions", **kwargs)
        elapsed = time.time() - start
        result = {
            "status": resp.status_code,
            "time": elapsed,
            "effort": effort or "(none)",
            "model": model,
        }
        if resp.status_code == 200:
            data = resp.json()
            choice = data["choices"][0]
            result["content"] = choice["message"].get("content", "").strip()
            result["reasoning_keys"] = [
                k for k in choice["message"].keys() if "reason" in k.lower()
            ]
            rc = choice["message"].get("reasoning_content", "")
            rt = (
                data.get("usage", {})
                .get("completion_tokens_details", {})
                .get("reasoning_tokens", 0)
            )
            result["reasoning_tokens"] = rt
            result["reasoning_content_len"] = len(rc)
        else:
            result["error"] = resp.text[:300]
        return result
    except Exception as e:
        return {
            "status": 0,
            "time": time.time() - start,
            "effort": effort or "(none)",
            "model": model,
            "error": f"{type(e).__name__}: {e}",
        }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Probe reasoning effort across models")
    p.add_argument("--provider", choices=["opencode-go", "opencode-zen"])
    p.add_argument("--model", action="append", help="Model to test (repeatable)")
    p.add_argument("--effort", help="Comma-separated efforts (default: xhigh,medium,low,max)")
    args = p.parse_args()

    providers = [args.provider] if args.provider else list(DEFAULT_MODELS.keys())
    efforts = args.effort.split(",") if args.effort else DEFAULT_EFFORTS

    print(f"Transport: {'curl_cffi (chrome120)' if USE_CFFI else 'plain requests'}")
    print(f"Efforts: {[e or '(none)' for e in efforts]}")
    print()

    for provider in providers:
        cfg = PROVIDER_CONFIG[provider]
        api_key = load_api_key(cfg["env_var"])
        models = args.model if args.model else DEFAULT_MODELS[provider]

        print(f"{'='*70}")
        print(f"Provider: {provider} | Base: {cfg['base_url']}")
        print(f"API key: {api_key[:8]}...")
        print(f"{'='*70}")

        for model in models:
            print(f"\n  Model: {model}")
            header = f"  {'Effort':12s} {'HTTP':6s} {'Time':8s} {'ReasoningTokens':16s} {'Content'}"
            sep = f"  {'-'*12} {'-'*6} {'-'*8} {'-'*16} {'-'*30}"
            print(header)
            print(sep)

            for effort in efforts:
                r = probe(cfg["base_url"], api_key, model, effort)
                status = r.get("status", "ERR")
                elapsed = f"{r['time']:.2f}s"
                rt = r.get("reasoning_tokens", "-")
                content = r.get("content", r.get("error", ""))[:50]
                print(f"  {r['effort']:12s} {status:>4}   {elapsed:8s} {str(rt):>14}   {content}")
            print()
