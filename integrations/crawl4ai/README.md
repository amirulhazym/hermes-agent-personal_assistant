# Crawl4AI Integration

> Priority #1 — Python-native web crawler for LLM consumption.  
> Adds JavaScript rendering capability beyond trafilatura's static HTML extraction.

## What It Is

**Crawl4AI** ([unclecode/crawl4ai](https://github.com/unclecode/crawl4ai)) is an open-source Python web crawling and scraping library designed for LLM-friendly output. Renders JavaScript, outputs clean Markdown/JSON.

- **License**: Apache-2.0 ✅ Free
- **Version**: 0.9.0 (installed)
- **Stars**: ~70K
- **Stack**: Python (async) + Playwright
- **Why:** Trafilatura (our current web extract backend) only handles static HTML. Crawl4AI adds JavaScript rendering for modern SPAs (React, Vue, etc.).

## System Impact

| Area | Effect |
|------|--------|
| **Web extraction** | +JS-rendered sites. Trafilatura stays as primary for static sites (faster, no overhead). |
| **RAG pipeline** | More sources now readable (SPAs, dashboards, JS-heavy docs). |
| **Addons** | Unattended. Trafilatura remains default in `config.yaml`. |
| **Cost** | $0 — runs locally. No API key. |

## Install Steps

```bash
# Ensure in the active Hermes venv
source ~/.hermes/hermes-agent/venv/bin/activate  # Hermes agent venv

# Install crawl4ai
pip install crawl4ai

# Install Playwright browser (required by crawl4ai)
playwright install-deps chromium
playwright install chromium

# Verify install
python -c "from crawl4ai import AsyncWebCrawler; print('OK')"
```

> **Note:** Crawl4AI auto-manages Playwright. First run will take extra time (>10s) as Chrome launches. Subsequent calls are faster.

## Usage

### Python — Quick Example

```python
import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://example.com")
        if result.success:
            print(result.markdown)   # Clean markdown
            print(result.metadata)   # Page metadata (title, description, etc.)
            print(result.links)      # Extracted links

asyncio.run(main())
```

### With Custom Configuration

```python
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

async def main():
    browser_config = BrowserConfig(headless=True)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://example.com",
            config=CrawlerRunConfig(
                extraction_strategy=JsonCssExtractionStrategy(...),
                word_count_threshold=10,
                exclude_external_links=True
            )
        )
        print(result.markdown)

asyncio.run(main())
```

### Hermes Skill / Cron Job Example

```python
# ~/.hermes/scripts/crawl4ai-extract.py
# Usage: python crawl4ai-extract.py <url>

import sys, json, asyncio
from crawl4ai import AsyncWebCrawler

async def extract(url):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        if not result.success:
            return {"error": f"Status {result.status_code}"}
        return {
            "url": url,
            "success": result.success,
            "status_code": result.status_code,
            "markdown": result.markdown,
            "metadata": result.metadata,
            "links": result.links
        }

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    output = asyncio.run(extract(url))
    print(json.dumps(output, indent=2, default=str))
```

### Integration with Hermes

Two paths:

1. **`execute_code`** (recommended): Call async Python scripts via Hermes' `execute_code` tool. Output captured as JSON.
2. **`terminal`**: Run the script via terminal tool. Simpler but blocking.

### Obsidian / RAG Pipeline

```python
import asyncio
from crawl4ai import AsyncWebCrawler
import os

OUTPUT_DIR = "/mnt/f/obsidian-vault/2-areas/Personal/reading/"

async def extract_and_save(url):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        if not result.success:
            return
        
        slug = result.metadata.get("title", "extracted")
        with open(os.path.join(OUTPUT_DIR, f"{slug}.md"), "w") as f:
            f.write(f"# {slug}\n\nSource: {url}\n\n{result.markdown}\n")
        print(f"Saved: {slug}.md")

asyncio.run(extract_and_save("https://some-site.com/article"))
```

## Configuration

No config changes needed in `config.yaml`. Trafilatura remains the default `web.extract_backend`.

Optional fallback logic:

```python
# In Hermes plugin/custom tool
if url_needs_js(url):
    result = await crawl4ai_extract(url)
else:
    result = trafilatura_extract(url)  # faster for static
```

## Maintenance Checklist

- [ ] `pip list | grep crawl4ai` → version ≥0.9.0
- [ ] Run test: `timeout 30 python3 -c "import asyncio; from crawl4ai import AsyncWebCrawler; asyncio.run(AsyncWebCrawler().arun(url='https://example.com'))"`
- [ ] Check for updates: `pip install --upgrade crawl4ai`

## Links

- GitHub: https://github.com/unclecode/crawl4ai
- Docs: https://docs.crawl4ai.com/
- PyPI: https://pypi.org/project/crawl4ai/

---

**Installation history:** 2026-06-28 — installed v0.9.0 in hermes-agent venv (Python 3.11). First crawl verified working.
