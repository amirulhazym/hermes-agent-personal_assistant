# Scrapling Integration

> Priority #4 — Standby. Adaptive web scraping with MCP server support and built-in anti-bot.

## What It Is

**Scrapling** ([D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling)) is an adaptive web scraping framework that automatically adjusts when a website changes layout. Includes stealth mode, anti-bot evasion, and MCP (Model Context Protocol) server support.

- **License**: BSD-3-Clause ✅ Free
- **Stars**: ~67K
- **Stack**: Python + Playwright
- **Why:** Adaptive scraping + anti-bot + MCP support makes it a strong secondary scraper.

## Status

`planned` — queued after Browser-Use (#3).

## Use Cases

- Sites that frequently change CSS/structure (adaptive scraping)
- Anti-bot bypass as backup to Crawl4AI
- Integration as Hermes MCP server (native support)

## Install

```bash
pip install scrapling
```

## Quick Example

```python
from scrapling import Fetcher

f = Fetcher()
page = f.fetch("https://example.com")
page.scroll_down()
print(page.text)
```

## Links

- GitHub: https://github.com/D4Vinci/Scrapling
- Docs: https://scrapling.readthedocs.io/
