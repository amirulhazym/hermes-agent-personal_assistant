# Provider Endpoint Triage (live API diagnosis)

Pattern for verifying whether a provider's base_url + API key actually work —
by sending real HTTP requests and reading the response, not by reading config.

## Why this exists

When a user says "it works" but you have no live proof, you must reproduce. The
MiniMax session (2026-07-09) showed: config had `api.minimax.com/v1` set,
fallback chain pointed to deepseek, and ALL historical minimax calls in the log
were `APIConnectionError` → deepseek fallback. The user believed minimax-m3 was
working. Live triage proved otherwise.

## Three-way response triage

| Symptom | HTTP | Root cause | Next step |
|---|---|---|---|
| `Name or service not known` / `Errno -2` | 000 | DNS fails — domain doesn't exist or isn't reachable from VPS | Check the domain is spelled right; try alternate host (`api.minimax.io` vs `api.minimaxi.com`) |
| `401 authorized_error` / `login fail` | 401 | Domain reachable, key rejected | Key is for a different endpoint, or key invalid, or auth header malformed |
| `404 page not found` | 404 | Wrong path on a reachable host | Fix the URL path (`/anthropic/messages` -> `/v1/messages` or similar) — NOT an auth problem |

Key insight: **401 != key is wrong for THIS endpoint**. It means the key isn't
accepted at THIS host. A key issued for `api.minimax.io` may be rejected by
`api.minimax.com` (different host = different auth realm).

## Working probe template (Python — avoids shell-quoting + placeholder traps)

NEVER type `***` as a placeholder for a secret in a shell command. Write a
Python script that reads the key from `.env` directly:

```python
import os, json, urllib.request, urllib.error

# Read key from .env (Hermes injects creds internally, NOT into shell env)
with open(os.path.expanduser("/home/ubuntu/.hermes/.env")) as f:
    for line in f:
        if line.startswith("MINIMAX_API_KEY=***            KEY = line.strip().split("=", 1)[1]
            break

def call(url, payload, headers, label):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            print(f"\n=== {label} ===\n[HTTP {r.status}]\n{r.read().decode()[:800]}")
    except urllib.error.HTTPError as e:
        print(f"\n=== {label} ===\n[HTTP {e.code}]\n{e.read().decode()[:800]}")
    except Exception as e:
        print(f"\n=== {label} ===\n[ERROR] {type(e).__name__}: {e}")

H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

# Test each candidate base_url + path
call("https://api.minimax.com/v1/chat/completions",
     {"model":"minimax-m3","messages":[{"role":"user","content":"PONG"}],"max_tokens":20},
     H, "T1: api.minimax.com/v1 (user config)")
call("https://api.minimax.io/v1/chat/completions",
     {"model":"minimax-m3","messages":[{"role":"user","content":"PONG"}],"max_tokens":20},
     H, "T2: api.minimax.io/v1 (plugin route)")
```

## MiniMax-specific findings (2026-07-09)

| Candidate endpoint | Result | Notes |
|---|---|---|
| `api.minimax.com/v1` (user's config.yaml) | DNS FAIL (`Errno -2`) | Domain does not resolve from VPS. User's provider-given URL is wrong/dead. |
| `api.minimax.io/v1` (Hermes plugin OpenAI route) | 401 | Reachable, key `sk-cp-...1s5U` rejected. Key likely issued for a different host/realm. |
| `api.minimax.io/anthropic/messages` (built-in Anthropic route) | 404 | Wrong path — `/anthropic/messages` not found. Route string needs correction. |

**Conclusion for MiniMax:** No endpoint verified working with the stored key.
The user's belief that "it works" was actually the deepseek fallback firing
(`config.yaml` fallback chain: minimax -> deepseek -> opencode-zen -> opencode-go).

**Reasoning-effort caveat:** Hermes' MiniMax plugin only emits M3 `reasoning_split`
controls when `base_url` host == `api.minimax.io` AND path == `/v1`
(`plugins/model-providers/minimax/__init__.py:_is_minimax_global_openai_base_url`).
A custom `api.minimax.com/v1` config gets NO reasoning controls — so even if it
responded, M3's adaptive reasoning would be silently disabled.

## What to tell the user

- Don't claim "it works" without a live 200 from the actual endpoint.
- Distinguish "fallback fired" (deepseek answered) from "provider answered".
- If key is rejected (401) on the host the user configured, ask the provider
  which exact host the key is scoped to — don't guess.

## ADVANCED: custom config.yaml provider vs built-in plugin shadowing (2026-07-09)

When a user has BOTH a built-in plugin provider AND a custom `providers:` block
in config.yaml with the SAME name (e.g. `minimax`), the resolution order matters:

**Resolution chain** (`hermes_cli/runtime_provider.py:resolve_runtime_provider`):
1. `_resolve_named_custom_runtime(requested)` is called FIRST (line 1442).
2. If it returns a dict → used directly, built-in plugin NEVER consulted.
3. If it returns `None` → falls through to `resolve_provider()` (built-in plugin).

**Critical gotcha:** A custom `providers:` block in config.yaml may NOT be read
as a "named custom provider" by `_resolve_named_custom_runtime` if the config
structure doesn't match what `_get_named_custom_provider()` expects. In the
MiniMax case, `_resolve_named_custom_runtime("minimax")` returned `None` —
so the **built-in plugin won the base_url + api_mode** (`api.minimax.io/anthropic`,
`anthropic_messages`), completely ignoring the user's `api.minimax.com/v1` in
config.yaml.

**How to verify which path wins:**
```python
from hermes_cli.runtime_provider import resolve_runtime_provider, _resolve_named_custom_runtime
print("custom_runtime:", _resolve_named_custom_runtime(requested_provider="minimax"))
print("full resolve:", resolve_runtime_provider(requested="minimax", target_model="minimax-m3"))
```
If `custom_runtime` is `None` but `full resolve` shows the plugin's base_url,
the custom block is dead.

**The "/model picker shows two MiniMax" question:**
- "MiniMax" (capital M) = built-in plugin entry (`PROVIDER_GROUPS` in
  `hermes_cli/models.py:1062`, models from `_PROVIDER_MODELS["minimax"]`).
- "minimax" (lowercase) = custom config.yaml `providers:` block.
- NOT a bug — it's a naming collision. The custom one is often dead (see above).
- Both share the same `MINIMAX_API_KEY` env var (confirmed).

**The "it works" misattribution trap:**
- Search gateway logs for `provider=minimax` + SUCCESS → if ZERO matches but the
  user insists minimax-m3 "works", check if the successes are actually
  `provider=opencode-go` (or fallback deepseek) serving the `minimax-m3` MODEL.
- In this session: every successful `minimax-m3` response = `provider=opencode-go`.
  Every `provider=minimax` call = 100% failure (Connection error / 401 / 404).
- Model name ≠ provider. A model can be served by multiple providers; the
  successful ones may not be the provider the user thinks they configured.

**Log search commands that separate signal from noise:**
```
# Successful calls WITH the actual minimax provider (should be 0 if broken):
grep 'provider=minimax' agent.log* | grep -E 'finish_reason=stop|content_delivered=True'
# Successful minimax-m3 regardless of provider (reveals misattribution):
grep 'model=minimax-m3' agent.log* | grep 'provider=opencode-go' | grep 'finish_reason=stop'
# All minimax provider failures:
grep 'provider=minimax' agent.log* | grep -E 'APIConnectionError|401|404'
```
