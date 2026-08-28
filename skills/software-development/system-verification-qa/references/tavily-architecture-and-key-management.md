# Tavily Architecture & Key Management — 2026-07-14

## Endpoint entry points

| Endpoint | Code path | Provider |
|----------|-----------|----------|
| web_search | `tools/web_tools.py:web_search_tool()` → `_get_search_backend()` → `TavilyWebSearchProvider.search()` | Plugin |
| web_extract | `tools/web_tools.py:web_extract_tool()` → `_get_extract_backend()` → `TavilyWebSearchProvider.extract()` | Plugin |
| tavily-search | MCP tool → `mcp.tavily.com` (remote) | MCP |
| tavily-extract | MCP tool → `mcp.tavily.com` (remote) | MCP |
| tavily-crawl | MCP tool → `mcp.tavily.com` (remote) | MCP only (NOT in plugin) |
| tavily-map | MCP tool → `mcp.tavily.com` (remote) | MCP only (NOT in plugin) |
| tavily-research | MCP tool → `mcp.tavily.com` (remote) | MCP only (NOT in plugin) |

## search-cascade resolution

`search_backend: search-cascade` is NOT a recognized backend. Resolution chain:

1. `_get_capability_backend("search")` reads `"search-cascade"` from config
2. `_is_backend_available("search-cascade")` → False (not in recognized set)
3. Falls back to `_get_backend()` → reads `web.backend: tavily`
4. Returns `"tavily"` → `TavilyWebSearchProvider` (plugin)

**Result:** search-cascade ALWAYS resolves to the tavily plugin. MCP Tavily is NOT used by search/extract dispatch.

## MCP vs Plugin separation

- Plugin: `plugins/web/tavily/provider.py` — handles search + extract via `_tavily_request()`
- MCP: `config.yaml mcp_servers.tavily` — remote server, exposes crawl/map/research (not in plugin)
- search-cascade uses plugin only, never MCP
- MCP tools (tavily-search, tavily-extract) are SEPARATE tools from plugin tools (web_search, web_extract)

## Key env vars

| Var | Purpose | Where read |
|-----|---------|------------|
| `TAVILY_API_KEY` | Single key (backward-compat) | `provider.py:44` `os.getenv()` |
| `TAVILY_API_KEYS` | Comma-separated pool (NOT YET IN HERMES — needs patch) | Not implemented |
| `TAVILY_BASE_URL` | Override API base | `provider.py:51` `os.getenv()` |

## MCP URL interpolation

`config.yaml`: `url: https://mcp.tavily.com/mcp/?tavilyApiKey=${TAVILY_API_KEY}`
- Uses shell `${}` expansion at startup
- Only sees the FIRST key (TAVILY_API_KEY), not a pool
- MCP server is remote — no local key rotation possible

## Runtime process

- Active source: `/home/ubuntu/.hermes/hermes-agent/` (v0.17.0, Python 3.11)
- Snapshot: `/home/ubuntu/hermes-snapshot-20260709/hermes-agent/` (disconnected reference, NO .git)
- The snapshot is NOT used by any running process
- Provider path at runtime: `/home/ubuntu/.hermes/hermes-agent/plugins/web/tavily/provider.py`

## Key audit findings (2026-07-14)

1. Key A (current TAVILY_API_KEY): VALID — 41 chars, starts `tvly-dev-`, search + extract both return 200
2. Key B (ai-marryjane-03): NOT in .env, user holds the value
3. Tavily free tier: 1,000 credits/month per key (NOT 1,000 searches — credits vary by endpoint)
4. Usage: ~300 requests/day → needs multiple keys for quota distribution
5. Hermes only reads TAVILY_API_KEY (single) — TAVILY_API_KEYS needs code patch

## HTTP 400 diagnostic pattern

When diagnosing Auth0/Cloudflare signup failures:

1. Navigate to signup page (not login — different Turnstile behavior)
2. Enable network monitoring (JS fetch intercept or CDP Network domain)
3. Type email, solve Turnstile (wait for 752-char token)
4. Intercept form submission with `redirect: 'manual'` to capture server response
5. Record: HTTP status, Location header, response body
6. Do NOT click submit multiple times — each click consumes the token

Evidence classification:
- HTTP 400 + token present + email present = server-side rejection (cause unknown without response body)
- HTTP 403 = explicit block (WAF/risk)
- HTTP 401 = auth failure
- Turnstile "couldn't load" on login but loads on signup = page-specific behavior, not IP block

## Plugin patch gaps (prototype only — NOT deployed)

| Gap | Status |
|-----|--------|
| Retry-After header parsing | Not handled (fixed 60s cooldown) |
| Monthly quota vs RPM throttling | Not distinguished |
| Async support | Not supported (sync httpx.post only) |
| Env change detection | Startup only (pool built at import time) |
| HTTP 400 handling | Not handled (falls through to raise_for_status) |
| Process/thread safety | Basic threading.Lock (safe for sync) |
