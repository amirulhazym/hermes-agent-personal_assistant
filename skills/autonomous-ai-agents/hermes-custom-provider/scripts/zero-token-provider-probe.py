#!/usr/bin/env python3
"""Zero-token provider connectivity probe for Hermes.

For every provider identity that holds a credential, makes exactly ONE
GET {base}/v1/models call (0 tokens burned) and reports HTTP status +
model count + first-3 IDs. Key VALUES are never printed (names/lengths only).

Usage: cd <hermes-agent repo> && python3 <this-file>
(repo root needed so hermes_cli is importable; works with system python3)

Sources covered: config.yaml providers:, auth.json credential_pool,
auth.json providers.* OAuth tokens, .env *API_KEY vars, plugin pool entries.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

# Deterministic env-name fallback for provider slugs the resolver may not
# report envs for (plugin providers, alias-field configs).
KNOWN_ENV = {
    "a6api": "A6API_API_KEY",
    "a6api-gateway": "A6API_API_KEY",
    "ftf": "FTF_API_KEY",
    "openai-api": "OPENAI_API_KEY",
    "opencode-zen": "OPENCODE_ZEN_API_KEY",
    "opencode-go": "OPENCODE_GO_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "apimaster": "APIMASTER_API_KEY",
    "fiq": "FIQ_API_KEY",
}


def load_env():
    env = {}
    p = HERMES_HOME / ".env"
    if p.exists():
        for line in p.read_text(errors="replace").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def load_auth():
    p = HERMES_HOME / "auth.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def pool_active_token(pool, name):
    """Return (token, base_url) of the active pool entry, or (None, None)."""
    lst = pool.get(name)
    if not isinstance(lst, list) or not lst:
        return None, None
    e = next((x for x in lst if x.get("active")), lst[0])
    tok = e.get("access_token") or e.get("token") or e.get("api_key")
    return tok, e.get("base_url")


def probe(name, base, key, label=""):
    req = urllib.request.Request(base.rstrip("/") + "/models", method="GET")
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("User-Agent", UA)
    req.add_header("Accept", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = json.loads(resp.read())
            models = [m.get("id") for m in (body.get("data") or [])] if isinstance(body, dict) else []
            print(f"{name} {label}| HTTP {resp.status} | models {len(models)} | first3 {models[:3]} | {round(time.time()-t0,1)}s")
    except urllib.error.HTTPError as e:
        print(f"{name} {label}| HTTP {e.code} | {e.read().decode('utf-8','replace')[:100]}")
    except Exception as e:
        print(f"{name} {label}| ERR {type(e).__name__} {str(e)[:100]}")


def main():
    import yaml
    from hermes_cli.providers import resolve_provider_full

    env = load_env()
    auth = load_auth()
    pool = auth.get("credential_pool", {})
    cfg_path = HERMES_HOME / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) if cfg_path.exists() else {}

    slugs = sorted(set((cfg.get("providers") or {}).keys()) | set(pool.keys()))
    slugs = sorted(set(slugs) | set(KNOWN_ENV.keys()))

    for s in slugs:
        try:
            r = resolve_provider_full(
                s,
                user_providers=cfg.get("providers", {}),
                custom_providers=cfg.get("custom_providers"),
            )
        except Exception:
            r = None
        base = getattr(r, "base_url", None) if r else None

        if s == "openai-codex":
            tok = (auth.get("providers", {}).get("openai-codex", {}).get("tokens", {}) or {}).get("access_token")
            ptok, pbase = pool_active_token(pool, s)
            tok = tok or ptok
            if tok and (pbase or base):
                probe(s, pbase or base, tok, "(oauth)")  # chatgpt.com edge may 403 from VPS — report, don't fake
            else:
                print(s, "SKIP no_oauth_token")
            continue

        key, src = None, None
        for ev in (getattr(r, "api_key_env_vars", []) or []) if r else []:
            if env.get(ev):
                key, src = env[ev], "env:" + ev
        if not key and s in KNOWN_ENV and env.get(KNOWN_ENV[s]):
            key, src = env[KNOWN_ENV[s]], "env:" + KNOWN_ENV[s]
        if not key:
            tok, pbase = pool_active_token(pool, s)
            if tok:
                key, src, base = tok, "pool:" + s, pbase or base

        if key and base:
            probe(s, base, key, f"({src})")
        else:
            print(s, "SKIP no_key base=", base)


if __name__ == "__main__":
    main()
