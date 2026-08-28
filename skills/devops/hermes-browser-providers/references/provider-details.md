# Provider Details — Hermes Browser Automation

**Date:** 2026-07-17
**Source files consulted:**
- https://hermes-agent.nousresearch.com/docs/user-guide/features/browser
- https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-gateway
- https://hermes-agent.nousresearch.com/docs/reference/tools-reference (GitHub raw)
- https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/browser.md
- https://docs.browser-use.com/cloud/tutorials/integrations/hermes-agent
- https://hermes-agent.ai/features/browser-automation
- GitHub issues: #374, #6780, #15229, #25214, #15952, #15445, #49385, #59797
- Local: ~/.hermes/config.yaml (v0.17.0), ~/.hermes/hermes-agent/tools/browser_tool.py

---

## Architecture

Hermes has **two browser tool surfaces**:

1. **Core `browser` toolset** — 10 tools always registered:
   `browser_navigate`, `browser_click`, `browser_snapshot`, `browser_type`,
   `browser_vision`, `browser_press`, `browser_scroll`, `browser_back`,
   `browser_console`, `browser_get_images`
2. **CDP-gated tools** — `browser_cdp` + `browser_dialog` — register only when
   a CDP endpoint is reachable at session start

Pages render as **accessibility trees** with ref IDs (`@e1`, `@e2`). Vision via
`browser_vision` screenshot + AI analysis.

---

## Provider Matrix

| Backend | Type | Config | Env Vars | Cost | Stealth |
|---------|------|--------|----------|------|---------|
| Local Playwright Chromium | Local fallback | `engine: auto` (default) | — | $0 | Minimal |
| `/browser connect` CDP | Local CLI-only | Manual Chrome `--remote-debugging-port=9222` | — | $0 | None (your browser) |
| Camofox (Docker) | Self-hosted | `CAMOFOX_URL=http://localhost:9377` | `CAMOFOX_URL` | $0 | Good (FF fork) |
| Browserbase | Cloud | `browser.cloud_provider: browserbase` | `BROWSERBASE_API_KEY` + `BROWSERBASE_PROJECT_ID` | Paid | Best (residential proxies) |
| Browser Use | Cloud | `browser.cloud_provider: browser-use` | `BROWSER_USE_API_KEY` | Paid | Good |
| Firecrawl | Cloud | `browser.cloud_provider: firecrawl` | `FIRECRAWL_API_KEY` | Paid | Moderate |
| Nous Portal Gateway | Cloud (managed) | `browser.use_gateway: true` | Portal OAuth | Paid sub | Good |

**Priority when multiple keys set:** Browserbase > Browser Use > Firecrawl

---

## Hybrid Routing

When a cloud provider is configured AND `browser.auto_local_for_private_urls: true`
(default), private/loopback/LAN URLs automatically route through a **local Chromium
sidecar** — the cloud provider never sees them.

Config:
```yaml
browser:
  cloud_provider: browserbase
  auto_local_for_private_urls: true    # default
  allow_private_urls: false            # reject private URLs if no cloud provider
```

---

## IDE-Only Feature: `/browser connect`

Not available on Telegram/Discord/WebUI — only in CLI TUI.

```bash
# Launch browser separately:
brave-browser --remote-debugging-port=9222 --user-data-dir=$HOME/.hermes/chrome-debug

# In Hermes CLI:
/browser connect                  # auto-detect or connect to 127.0.0.1:9222
/browser connect ws://host:port   # specific endpoint
/browser disconnect
```

---

## Browser Use CLI Alternative

Separate from the cloud backend integration. Hermes drives the browser through
terminal commands via `browser-use` CLI:

```bash
uv tool install browser-use
browser-use skill install
browser-use auth login
```

Then instruct: "Use browser-use to open github.com/trending and summarize."

---

## Known Issues

| Issue | Title | Status | Workaround |
|-------|-------|--------|------------|
| #374 | Local browser via Playwright/CDP | ✅ **CLOSED** (Mar 2026) | Foundational — merged |
| #6780 | Auto-detect local Chrome CDP | ❌ **OPEN** | Manual `/browser connect` |
| #15229 | Camofox missing from `_PROVIDER_REGISTRY` | ❌ **OPEN** | Use raw camofox_* tools |
| #25214 | Plugin migration for browser providers | 🔄 **OPEN** | Architectural — no user impact yet |
| #15952 | `browser_cdp` check_fn requires agent-browser | ❌ **OPEN** | Install agent-browser or configure cdp_url |
| #15445 | Obscura (Rust headless browser) provider | 💡 **FEATURE REQ** | Not merged |
| #49385 | Unauthenticated CDP control plane | 🔴 **OPEN (security)** | Don't share host with untrusted processes |
| #59797 | browser_vision fails on local Brave CDP (Win) | ❌ **OPEN** | Use raw CDP commands |

---

## Key Finding: Local Playwright Works at $0

Playwright headless Chromium is the **default fallback** when no cloud provider
and no `agent-browser` CLI are configured. Works with just:

```bash
pip install playwright
playwright install chromium
```

No API keys, no subscription. This is how the VPS Hermes instance runs browser
tools right now (verified 2026-07-17).
