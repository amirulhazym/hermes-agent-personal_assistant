---
name: hermes-browser-providers
description: "Configure, switch, and troubleshoot Hermes Agent browser automation providers. Covers all seven backends (Local Playwright, CDP, Camofox, Browserbase, Browser Use, Firecrawl, Nous Portal Gateway), config keys, known bugs, and Hybrid Routing."
version: 1.0.0
author: Hermes Agent (via research 2026-07-17)
tags: [hermes, browser, automation, providers, CDP, Playwright, Browserbase, Camoufox, stealth]
trigger: user asks to set up browser tools, switch providers, fix "browser_tool not working", configure CDP, or enable cloud browsing
---

# Hermes Browser Providers

Class-level skill for configuring Hermes Agent browser automation. The bundled `hermes-agent` skill only lists the `browser` toolset — this skill covers **provider-specific** setup, config keys, known bugs, and troubleshooting.

> **Reference file:** `references/provider-details.md` — full research trace with issue numbers, provider matrix, and architecture notes.

---

## Provider Quick-Reference

### Cloud Providers (paid/API-key)

| Provider | `cloud_provider` value | Required env vars | Cost |
|----------|------------------------|-------------------|------|
| **Browserbase** | `browserbase` | `BROWSERBASE_API_KEY`, `BROWSERBASE_PROJECT_ID` | Paid |
| **Browser Use** | `browser-use` | `BROWSER_USE_API_KEY` | Paid |
| **Firecrawl** | `firecrawl` | `FIRECRAWL_API_KEY` | Paid |
| **Nous Portal Gateway** | `browser-use` + `use_gateway: true` | Portal OAuth (`hermes setup --portal`) | Paid sub |

**Priority:** Browserbase > Browser Use > Firecrawl when multiple keys set.

### Self-Hosted / Free Options

| Provider | How to enable | Notes |
|----------|--------------|-------|
| **Local Playwright Chromium** | No config needed (fallback) | Works if `playwright` pip package installed + `playwright install chromium` |
| **CDP connect** | `/browser connect` (CLI slash command) | CLI-only. Not available on Telegram/Discord/WebUI |
| **Camofox** | `CAMOFOX_URL=http://localhost:9377` | Docker-based Firefox fork, stealth fingerprinting |

---

## Config Keys

Key section in `~/.hermes/config.yaml`:

```yaml
browser:
  cloud_provider: browser-use     # 'browserbase', 'browser-use', 'firecrawl', 'camofox'
  engine: auto                    # 'auto', 'playwright', 'agent-browser'
  cdp_url: ''                     # BROWSER_CDP_URL — explicit CDP endpoint
  auto_local_for_private_urls: true  # cloud → local sidecar for private IPs
  allow_private_urls: false       # reject private URLs unless true
  inactivity_timeout: 120
  command_timeout: 30
  camofox:
    managed_persistence: false
    rewrite_loopback_urls: false
    loopback_host_alias: host.docker.internal
```

Set via CLI:
```bash
hermes config set browser.cloud_provider browserbase
export BROWSERBASE_API_KEY=...
export BROWSERBASE_PROJECT_ID=...
```

Or interactive:
```bash
hermes setup tools     # Browser Automation → pick provider
```

---

## Hybrid Routing (Cloud + Local Sidecar)

When a cloud provider is configured AND `auto_local_for_private_urls: true` (default):
- **Public URLs** → route through cloud provider
- **Private/LAN/loopback URLs** → auto-spawn local Chromium sidecar
- **Cloud provider never sees the private URL**

Disable: `browser.auto_local_for_private_urls: false`
With routing disabled, private URLs rejected unless `browser.allow_private_urls: true`.

---

## Ausiliary: Browser Use CLI Option

Browser Use also offers a **standalone CLI** that Hermes drives via `terminal` tool:

```bash
uv tool install browser-use
browser-use skill install
```

Then instruct: "Use browser-use to open <url> and ..." — driven through terminal commands, not the built-in browser toolset.

---

## CDP (/browser connect)

Only works in **CLI TUI mode** — NOT through gateway platforms (Telegram, Discord, etc.).

```bash
# In a separate terminal, launch Chromium-family browser with debug port:
brave-browser --remote-debugging-port=9222 --user-data-dir=$HOME/.hermes/chrome-debug

# Then in Hermes CLI:
/browser connect              # auto-launch or connect to 127.0.0.1:9222
/browser connect ws://host:port  # specific endpoint
/browser status
/browser disconnect
```

**Security warning (#49385):** The CDP endpoint at `127.0.0.1:9222` is **unauthenticated** — any other process on the same host can hijack the browser session via `http://127.0.0.1:9222/json/version`.

---

## Known Bugs & Pitfalls

### Camofox provider registration broken (#15229)
Setting `browser.cloud_provider: camofox` has **no effect** on standard browser tools (`browser_navigate`, etc.) — they fall through to Browserbase/Browser Use. Camofox only works via the separate `camofox_*` tool functions.
**Fix:** None upstream yet (issue open). Use Camofox only via its own raw tools, not as a cloud_provider.

### CDP tool check_fn requires agent-browser CLI (#15952)
`browser_cdp` tool is gated by `check_browser_requirements()` which checks for `agent-browser` CLI — even though the CDP tool is a pure WebSocket client with zero dependency on it.
**Workaround:** Install `agent-browser` (npm), or if using a build with the fix, configure `browser.cdp_url`.

### Auto-detect local Chrome CDP (#6780)
The agent's browser tools do NOT auto-detect a running Chrome on port 9222 — they fall through to launching a separate headless Chromium. The CLI's `/browser connect` does detect it, but the agent tools don't.
**Status:** Open issue. Switch: manually use `/browser connect`.

### Obscura provider (#15445)
Feature request to add Obscura (Rust headless browser with CDP) as a lightweight local provider. Not merged.

### Windows: browser_vision fails on local Brave CDP (#59797)
`Target.attachToTarget: Not allowed` error on Windows with local Brave CDP. Raw CDP commands work fine.

---

## Verification Checklist

After configuring a provider, verify it works:

```bash
hermes status                    # Check tool gateway status
hermes portal info               # Portal + Tool Gateway routing summary (if using gateway)
hermes tools                     # Check browser toolset is enabled
```

Then test in a fresh session (`/reset`):
1. `browser_navigate(url="https://example.com")` — should return snapshot
2. `browser_snapshot()` — should show interactive elements with ref IDs
3. `browser_vision(question="Describe the page")` — screenshot + analysis

---

## Pitfalls

- **Config changes** (cloud_provider, cdp_url) need `/reset` (new session) — tool changes don't apply mid-conversation
- **Local mode** (no cloud keys) → Hermes falls through `agent-browser` CLI → Playwright headless Chromium. If neither works, `browser_*` tools return "Daemon failed to start"
- **playwright not installed** → run `pip install playwright && playwright install chromium`
- **agent-browser not installed** → `npm install -g agent-browser` or rely on Playwright fallback
