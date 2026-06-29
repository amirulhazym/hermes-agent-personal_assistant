# Hybrid-Web Setup Guide

> Step-by-step installation and configuration for the hybrid-web plugin.
>
> **Prerequisites:** Hermes Agent installed with Crawl4AI and Trafilatura.

---

## Quick Install

### 1. Create Plugin Directory

```bash
mkdir -p ~/.hermes/plugins/hybrid-web
```

### 2. Create Plugin Files

Create three files in `~/.hermes/plugins/hybrid-web/`:

#### `plugin.yaml`

```yaml
name: hybrid-web
version: 1.0.0
description: Intelligent web extraction routing between Trafilatura and Crawl4AI
author: Amirul
homepage: https://github.com/amirulhazym/hermes-agent-personal_assistant
```

#### `__init__.py`

```python
"""Hybrid-Web Plugin - Intelligent extraction routing."""

from .provider import HybridWebSearchProvider

def register():
    """Register the hybrid-web provider."""
    return HybridWebSearchProvider()
```

#### `provider.py`

```python
"""Hybrid-Web Provider - Routes extraction to optimal backend."""

import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Timeout for Crawl4AI (JS-heavy pages need more time)
CRAWL4AI_TIMEOUT = 45


class HybridWebSearchProvider:
    """Web search provider that routes extraction based on page type."""

    def __init__(self):
        self.name = "hybrid-web"
        self.display_name = "Hybrid Web"
        self._available = True

    def is_available(self) -> bool:
        """Check if provider is available."""
        return self._available

    def supports_extract(self) -> bool:
        """This provider supports URL extraction."""
        return True

    def extract(self, urls: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Extract content from URLs, routing to optimal backend.

        Args:
            urls: List of URLs to extract
            **kwargs: Additional options (format, etc.)

        Returns:
            List of extraction results
        """
        results = []

        for url in urls:
            try:
                result = self._extract_single(url, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Extraction failed for {url}: {e}")
                results.append({
                    "url": url,
                    "content": None,
                    "error": str(e),
                    "success": False
                })

        return results

    def _extract_single(self, url: str, **kwargs) -> Dict[str, Any]:
        """Extract content from a single URL."""
        # Detect if page is likely JavaScript-heavy
        if self._is_likely_js_heavy(url):
            return self._extract_with_crawl4ai(url, **kwargs)
        else:
            return self._extract_with_trafilatura(url, **kwargs)

    def _is_likely_js_heavy(self, url: str) -> bool:
        """
        Detect if a URL is likely to be JavaScript-heavy.

        Uses heuristics based on URL patterns and known SPA frameworks.
        """
        # Known JS-heavy domains
        js_heavy_domains = [
            "github.com",
            "react.dev",
            "nextjs.org",
            "vuejs.org",
            "angular.io",
            "vercel.app",
            "netlify.app",
        ]

        # Check domain
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        for js_domain in js_heavy_domains:
            if js_domain in domain:
                return True

        # Default to static extraction (Trafilatura)
        return False

    def _extract_with_trafilatura(self, url: str, **kwargs) -> Dict[str, Any]:
        """Extract using Trafilatura (fast, lightweight)."""
        try:
            import trafilatura

            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                content = trafilatura.extract(downloaded, include_links=True)
                return {
                    "url": url,
                    "content": content,
                    "backend": "trafilatura",
                    "success": True
                }
            else:
                return {
                    "url": url,
                    "content": None,
                    "error": "Failed to fetch URL",
                    "backend": "trafilatura",
                    "success": False
                }
        except Exception as e:
            logger.error(f"Trafilatura extraction failed: {e}")
            raise

    def _extract_with_crawl4ai(self, url: str, **kwargs) -> Dict[str, Any]:
        """Extract using Crawl4AI (headless browser for JS-heavy pages)."""
        try:
            import asyncio
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

            async def _crawl():
                browser_config = BrowserConfig(headless=True)
                run_config = CrawlerRunConfig(
                    wait_until="networkidle",
                    page_timeout=CRAWL4AI_TIMEOUT * 1000  # Convert to ms
                )

                async with AsyncWebCrawler(config=browser_config) as crawler:
                    result = await crawler.arun(
                        url=url,
                        config=run_config
                    )
                    return result

            # Run async crawl
            result = asyncio.run(_crawl())

            if result and result.success:
                return {
                    "url": url,
                    "content": result.markdown or result.cleaned_html,
                    "backend": "crawl4ai",
                    "success": True
                }
            else:
                return {
                    "url": url,
                    "content": None,
                    "error": result.error_message if result else "Unknown error",
                    "backend": "crawl4ai",
                    "success": False
                }
        except Exception as e:
            logger.error(f"Crawl4AI extraction failed: {e}")
            raise


# Module-level instance for plugin registration
provider_instance = HybridWebSearchProvider()
```

### 3. Enable Plugin in Config

Edit `~/.hermes/config.yaml`:

```yaml
web:
  extract_backend: hybrid-web    # Add this line

plugins:
  enabled:
    - hybrid-web                 # Add to existing list
```

### 4. Restart Hermes

```bash
hermes gateway restart
```

### 5. Verify Installation

```bash
# Test plugin loads
python3 -c "
import sys
sys.path.insert(0, '/home/amirul/.hermes/plugins/hybrid-web')
from provider import HybridWebSearchProvider
p = HybridWebSearchProvider()
print('Plugin available:', p.is_available())
print('Supports extract:', p.supports_extract())
"

# Test actual extraction
web_extract(urls=["https://example.com"])
```

## Dependencies

The hybrid-web plugin requires:

- **Trafilatura** — Already installed in Hermes venv
- **Crawl4AI** — Already installed in Hermes venv

No additional packages needed.

## Configuration Options

### Timeout Adjustment

To change Crawl4AI timeout, edit `~/.hermes/plugins/hybrid-web/provider.py`:

```python
# Find this line and modify the value
CRAWL4AI_TIMEOUT = 60  # Default: 45 seconds
```

### Custom Domain Detection

To add more JS-heavy domains, edit the `_is_likely_js_heavy` method in `provider.py`:

```python
# Add domains to this list
js_heavy_domains = [
    "github.com",
    "react.dev",
    # Add more here
]
```

## Uninstall

1. Remove plugin directory:
   ```bash
   rm -rf ~/.hermes/plugins/hybrid-web
   ```

2. Remove from config:
   ```yaml
   web:
     extract_backend: ddgs  # Revert to default

   plugins:
     enabled:
       - hybrid-web  # Remove this line
   ```

3. Restart Hermes:
   ```bash
   hermes gateway restart
   ```
