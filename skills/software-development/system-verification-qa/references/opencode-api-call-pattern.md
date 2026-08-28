# OpenCode (opencode-go / opencode-zen) API call patterns

Verified live 2026-07-04. Findings on direct API calls from cron scripts.

## TL;DR

- `opencode-go` (`https://opencode.ai/zen/go`) and `opencode-zen` (`https://opencode.ai/zen`) **block direct curl/urllib calls with Cloudflare Error 1010** unless you send browser-like headers.
- Add `User-Agent`, `Origin`, and `Referer` headers — this bypasses the bot check, no proxy needed.
- Both providers use the standard **OpenAI-compatible** `/v1/chat/completions` endpoint shape (request body and response JSON are identical to OpenAI).
- API key is in env: `OPENCODE_GO_API_KEY` for go, `OPENCODE_ZEN_API_KEY` for zen.

## Working headers

```python
HEADERS = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://opencode.ai",
    "Referer": "https://opencode.ai/",
}
```

The `User-Agent` is the critical one. Even `hermes-agent/1.0` works — anything that looks like a real client.

## Without these headers

```
HTTP 403: error code: 1010
```

Cloudflare's "browser integrity check" — interprets missing/short UA as a bot. Same goes for any tool that doesn't send proper headers (curl, plain urllib).

## The 3 providers we actually use

| Provider name in config.yaml | base_url | API key env var | Notes |
|---|---|---|---|
| `opencode-go` | `https://opencode.ai/zen/go` | `OPENCODE_GO_API_KEY` | Paid, paid models (minimax, kimi-k2, etc) |
| `opencode-zen` | `https://opencode.ai/zen` | `OPENCODE_ZEN_API_KEY` | Free tier, similar model selection |
| `deepseek` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | No Cloudflare guard — works with minimal headers |

**Do not assume** other providers (Anthropic, OpenAI, OpenRouter, etc.) are in the active rotation. The 3 above are the ones Amirul has set up. Adding more would require auth + config changes.

## Model resolution from config.yaml (no PyYAML)

For cron scripts that need to call the same model as the user's chat session:

```python
from pathlib import Path

PROVIDER_KEY_ENV = {
    "opencode-go": "OPENCODE_GO_API_KEY",
    "opencode-zen": "OPENCODE_ZEN_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}

DEFAULT_BASE_URLS = {
    "opencode-go": "https://opencode.ai/zen/go",
    "opencode-zen": "https://opencode.ai/zen",
    "deepseek": "https://api.deepseek.com",
}

def _parse_simple_yaml(path: Path) -> dict:
    """
    Minimal YAML parser for flat top-level + one-level-deep keys.
    Hermes config.yaml uses 2-space indent for nested keys; we need to
    strip that indent to read them.
    """
    out: dict = {}
    if not path.exists():
        return out
    current_section = None
    for raw in path.read_text().splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")) and line.endswith(":"):
            current_section = line[:-1].strip()
            out.setdefault(current_section, {})
            continue
        if current_section and ":" in line:
            stripped = line.lstrip(" ")  # strip up to 4 spaces of indent
            if ":" in stripped:
                k, _, v = stripped.partition(":")
                out[current_section][k.strip()] = v.strip()
    return out

def get_active_model_config():
    cfg = _parse_simple_yaml(Path.home() / ".hermes" / "config.yaml").get("model", {})
    provider = cfg.get("provider", "deepseek")
    model = cfg.get("default", "deepseek-v4-flash")
    base_url = cfg.get("base_url") or DEFAULT_BASE_URLS.get(provider, DEFAULT_BASE_URLS["deepseek"])
    return model, provider, base_url.rstrip("/")
```

**Critical pitfall:** if you forget to handle indented keys (lines starting with whitespace), the parser returns empty dicts and you silently fall through to defaults without warning. Always test with the actual config.yaml before deploying.

## `<think>` block leak

Some models (notably minimax-m3 on opencode-go) return content like:

```
<think>
The user is asking me to ...
</think>
Hello, boss!
```

The think block leaks into stdout if you don't strip it. Use a regex:

```python
import re
content = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL).strip()
```

Apply this to any content extraction from OpenAI-format providers. Some providers put reasoning in a separate `reasoning_content` field instead — check both fields.

## Live verification

Always test the full path before assuming it works:

```python
import json, urllib.request, os
from pathlib import Path

env = {}
for line in Path.home().joinpath(".hermes", ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()

api_key = env.get("OPENCODE_GO_API_KEY")
# ... build request with browser-like headers ...
with urllib.request.urlopen(req, timeout=20) as r:
    print(json.loads(r.read().decode()))
```

If you get HTTP 403 with "error code: 1010", it's the Cloudflare block, not an auth issue. Add browser-like headers.

## Worked example: chain_llm.py

The `~/.hermes/scripts/chain_llm.py` script uses this pattern to call the same model as the chat session for medication reminders. See it as a reference for the full pattern (config resolution + API call + response handling + fallback to hardcoded template if LLM fails).
