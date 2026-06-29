# Integrations

> Third-party tools integrated into Hermes for extended capabilities.  
> Each folder contains: README.md (what + why), setup.md (step-by-step install), and usage/ (practical examples).
>
> This document is for **AI coding agents** updating this repo.  
> **Human source of truth:** This is documentation derived from the live system.  
> **Maintenance:** Verify everything here against the actual running environment before pushing edits.

---

## Priority Order — Do Not Change Order Without Human Approval

| Order | Tool | Status | Integration Path | Notes |
|:---:|---|:---:|---|---|
| **1** | **Crawl4AI** | `installed ✅` | Hermes venv `~/.hermes/hermes-agent/venv/` | Trafilatura remains. Crawl4AI is supplemental JS-rendering backend. v0.9.0 |
| **2** | **MarkItDown** | `installed ✅` | Hermes venv `~/.hermes/hermes-agent/venv/` | v0.1.6. Converts docs to markdown for RAG/vault. |
| **3** | **Browser-Use** | `installed ✅` | Hermes venv `~/.hermes/hermes-agent/venv/` | v0.13.1. Playwright-based web automation (different from cua-driver). |
| **4** | **Hybrid-Web** | `installed ✅` | `~/.hermes/plugins/hybrid-web/` | Custom plugin. Routes extraction to Trafilatura (static) or Crawl4AI (JS-heavy) automatically. |
| **5** | **Scrapling** | `standby` | Python package. Has MCP server support. | Anti-bot adaptive scraping. Queue after #3. |
| **6** | **curl-impersonate** | `standby` | System binary. Light dependency. | TLS fingerprint bypass. Minimal setup needed. |

## Removed (Explicitly Excluded)

| Tool | Reason |
|---|--------|
| ~~AutoScraper~~ | Python learning-based scraper. Limited dynamic site support. Not competitive with Crawl4AI. |
| ~~Crawlee~~ | Node.js/TypeScript only. Wrong stack for Hermes (Python-native). |
| ~~Firecrawl~~ | AGPL-3.0 license (self-host risk). Cloud version costs money. Crawl4AI is free (Apache-2.0) and does same thing. |

## Installation Summary (2026-06-28)

All packages installed in **Hermes agent venv** at `~/.hermes/hermes-agent/venv/` (Python 3.11).

### Pre-requisites

```bash
# Activate Hermes venv
source ~/.hermes/hermes-agent/venv/bin/activate

# Playwright system deps (only needed once for both Crawl4AI + Browser-Use)
playwright install-deps chromium
playwright install chromium
```

### Package versions

| Package | Version | Install cmd |
|---------|---------|-------------|
| crawl4ai | 0.9.0 | `pip install crawl4ai` |
| markitdown | 0.1.6 | `pip install markitdown` |
| browser-use | 0.13.1 | `pip install browser-use` |

## Original 10 (Reference Only)

1. Firecrawl ⭐140K — REMOVED
2. Crawl4AI ⭐70K — **INSTALLED ✅**
3. Browser-Use ⭐101K — **INSTALLED ✅**
4. Crawlee ⭐24K — REMOVED
5. Scrapy ⭐63K — Not priority (too heavy for personal use)
6. MarkItDown ⭐160K — **INSTALLED ✅**
7. Scrapling ⭐67K — Standby (#4)
8. scrcpy ⭐144K — Out of scope (Android mirroring)
9. AutoScraper ⭐7.3K — REMOVED
10. curl-impersonate ⭐6.2K — Standby (#5)
