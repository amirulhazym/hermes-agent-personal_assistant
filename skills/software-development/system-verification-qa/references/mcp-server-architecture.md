# MCP Server Architecture in Hermes

## How Hermes Connects to MCP Servers

Hermes reads `mcp_servers` from `config.yaml` and connects at startup via `_load_mcp_config()` → `_interpolate_env_vars()` → `_connect_server()` in `tools/mcp_tool.py`.

**Key constraint:** The MCP server URL is resolved ONCE at startup. The `${VAR}` interpolation in the URL template reads from env vars at that moment. There is NO per-call interception point — every tool call goes through the same persistent session with the same URL (and thus the same API key).

### Transport types
- **stdio** (command + args) — spawns a subprocess, communicates via stdin/stdout
- **Streamable HTTP** (url) — connects to remote HTTP endpoint (default for remote servers)
- **SSE** (url + transport: sse) — Server-Sent Events for older MCP servers

### URL interpolation
```yaml
mcp_servers:
  tavily:
    url: https://mcp.tavily.com/mcp/?tavilyApiKey=${TAVILY_API_KEY}
```
`${TAVILY_API_KEY}` is resolved by `_interpolate_env_vars()` which calls `_get_secret()` from `agent/secret_scope.py`. This reads from the active profile's secret scope (or `os.environ` as fallback).

## Why Remote MCP Servers Can't Do Per-Call Key Rotation

1. **Single session:** One connection per server, established at startup
2. **URL = key:** The API key is embedded in the URL query parameter
3. **No hook:** The MCP tool handler (`_make_tool_handler`) calls `server.session.call_tool()` on the existing session — there's no mechanism to change the URL per-call
4. **CredentialPool gap:** Hermes has a `CredentialPool` system (`agent/credential_pool.py`) with round-robin, exhaustion cooldowns, and dead detection — but it's designed for **LLM providers** (OpenRouter, Anthropic, etc.), not MCP server URLs

## Local Proxy Pattern for Key Rotation

When you need multi-key rotation for a remote MCP server, build a **local MCP server** that proxies requests with key rotation.

### Architecture
```
Hermes → stdio → Local Proxy MCP Server → REST API (Tavily, etc.)
                    │
                    ├── Reads TAVILY_API_KEYS from .env
                    ├── Round-robin key selection
                    ├── Cooldown on 429/401
                    └── Redacted logging
```

### Config change
```yaml
mcp_servers:
  tavily:
    command: "/home/ubuntu/.hermes/hermes-agent/venv/bin/python3"
    args: ["/home/ubuntu/.hermes/scripts/tavily-proxy.py"]
    timeout: 120
    connect_timeout: 30
```

### Available tools
FastMCP is available in the Hermes venv:
```bash
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -c "from mcp.server.fastmcp import FastMCP; print('ok')"
```

### REST API endpoints (Tavily example)
- Search: `POST https://api.tavily.com/search` (1-2 credits)
- Extract: `POST https://api.tavily.com/extract` (1-2 credits per 5 URLs)
- Auth: `Authorization: Bearer <key>` header
- All return JSON with `results`, `response_time`, `request_id`

### Key rotation logic
```python
# Pseudocode for round-robin with cooldown
keys = parse_keys(os.environ.get("TAVILY_API_KEYS", ""))
cooldowns = {}  # key_suffix -> expiry_timestamp

def next_key():
    for key in keys:
        if key not in cooldowns or time.time() > cooldowns[key]:
            return key
    raise AllKeysExhausted()

def handle_error(key, status_code, response):
    if status_code == 401:
        disable_key(key)  # permanent
    elif status_code == 429:
        retry_after = parse_retry_after(response)
        cooldowns[key[-4:]] = time.time() + retry_after
    elif status_code >= 500:
        rotate_to_next(key)
```

### Backward compatibility
Always keep `TAVILY_API_KEY` (singular) as fallback:
```python
keys = os.environ.get("TAVILY_API_KEYS", "").split(",")
keys = [k.strip() for k in keys if k.strip()]
if not keys:
    keys = [os.environ.get("TAVILY_API_KEY", "")]
```

## References in Hermes Source

| File | What it does |
|------|-------------|
| `tools/mcp_tool.py` | MCP client: connection, tool registration, dispatch |
| `agent/credential_pool.py` | LLM provider credential rotation (not for MCP) |
| `agent/secret_scope.py` | Secret resolution for `${VAR}` interpolation |
| `hermes_cli/env_loader.py` | `.env` loading at startup (runs ONCE at import time) |
