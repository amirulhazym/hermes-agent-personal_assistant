"""
Hybrid-Web Plugin - Intelligent extraction routing.

Routes between Trafilatura (static HTML) and Crawl4AI (JS-heavy SPAs)
based on page characteristics.

Inherits from agent.web_search_provider.WebSearchProvider so it integrates
with Hermes' standard web search/extract plugin registry.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from agent.web_search_provider import WebSearchProvider

logger = logging.getLogger(__name__)

TRAFILATURA_TIMEOUT = 10
CRAWL4AI_TIMEOUT = 45

# Markers that indicate a JS-heavy SPA needs Crawl4AI instead of Trafilatura
SPA_MARKERS = [
    r"__NEXT_DATA__",
    r"__NUXT__",
    r"__VUE__",
    r"react-root",
    r"ng-version",
    r"ember-view",
    r"__REMIX_CONTEXT__",
]


class HybridWebSearchProvider(WebSearchProvider):
    """Routes web extraction to Trafilatura or Crawl4AI based on page type."""

    name = "hybrid-web"
    display_name = "Hybrid Web (Smart Routing)"

    # ---- ABC required methods ----

    def is_available(self) -> bool:
        # Always available — both backends have free/open-source implementations
        return True

    def supports_search(self) -> bool:
        # This provider is extract-only, not a search engine
        return False

    def supports_extract(self) -> bool:
        return True

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        """Extract content from one or more URLs with smart backend routing.

        For each URL:
        1. HEAD request to check content-type
        2. If HTML, GET the page and inspect for SPA markers
        3. Route to Trafilatura (fast, static) or Crawl4AI (headless, JS)
        4. Return list of {url, title, content, raw_content, metadata}

        Returns the format required by Hermes' web_extract tool:
        a list of dicts, one per URL, with consistent shape.
        """
        results: List[Dict[str, Any]] = []
        for url in urls:
            results.append(self._extract_one(url))
        return results

    # ---- internals ----

    def _extract_one(self, url: str) -> Dict[str, Any]:
        """Extract a single URL with smart routing."""
        try:
            import requests
        except ImportError:
            return self._err_result(url, "requests library not available")

        try:
            # Step 1: check content type
            head_resp = requests.head(url, timeout=5, allow_redirects=True)
            content_type = head_resp.headers.get("content-type", "")

            if "text/html" not in content_type:
                return {
                    "url": url,
                    "title": "",
                    "content": f"Non-HTML content: {content_type}",
                    "raw_content": "",
                    "metadata": {"content_type": content_type, "backend": "none"},
                }

            # Step 2: fetch HTML
            resp = requests.get(url, timeout=TRAFILATURA_TIMEOUT)
            html = resp.text
            html_title = self._extract_title(html)

            # Step 3: detect SPA, choose backend
            if self._is_spa(html):
                logger.info("Detected SPA: %s -> using Crawl4AI/Playwright", url)
                content, backend = self._extract_js_heavy(url)
            else:
                logger.info("Detected static: %s -> using Trafilatura", url)
                backend = "trafilatura"
                content = self._extract_with_trafilatura(url)

            if content is None:
                return self._err_result(url, f"{backend} extraction failed", html_title)

            return {
                "url": url,
                "title": html_title or "",
                "content": content,
                "raw_content": content,
                "metadata": {"backend": backend, "content_type": content_type},
            }

        except Exception as exc:
            logger.warning("extract failed for %s: %s", url, exc)
            return self._err_result(url, str(exc))

    def _err_result(self, url: str, error: str, title: str = "") -> Dict[str, Any]:
        return {
            "url": url,
            "title": title,
            "content": f"Error: {error}",
            "raw_content": "",
            "metadata": {"backend": "none", "error": error},
        }

    def _is_spa(self, html: str) -> bool:
        for marker in SPA_MARKERS:
            if re.search(marker, html, re.IGNORECASE):
                return True
        script_count = len(re.findall(r"<script[^>]*>", html, re.IGNORECASE))
        return script_count > 10

    def _extract_title(self, html: str) -> str:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
        return ""

    def _extract_with_trafilatura(self, url: str):
        try:
            import trafilatura
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                return trafilatura.extract(downloaded)
        except Exception as exc:
            logger.warning("Trafilatura failed for %s: %s", url, exc)
        return None

    def _extract_js_heavy(self, url: str) -> Tuple[Optional[str], str]:
        """JS/SPA extract: Crawl4AI API first, Playwright fallback.

        Replaces invalid CLI path (`python3 -m crawl4ai` has no __main__).
        """
        content = self._crawl4ai_async(url)
        if content:
            return content, "crawl4ai"
        content = self._extract_with_playwright(url)
        if content:
            return content, "playwright"
        return None, "crawl4ai"

    def _crawl4ai_async(self, url: str) -> Optional[str]:
        try:
            import asyncio
            from crawl4ai import AsyncWebCrawler

            async def _run():
                async with AsyncWebCrawler() as crawler:
                    result = await crawler.arun(url=url)
                    if result is None:
                        return None
                    if hasattr(result, "success") and result.success is False:
                        return None
                    for attr in ("markdown", "extracted_content", "cleaned_html"):
                        val = getattr(result, attr, None)
                        if val:
                            return str(val)
                    return None

            try:
                return asyncio.run(_run())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(_run())
                finally:
                    loop.close()
        except Exception as exc:
            logger.warning("Crawl4AI API failed for %s: %s", url, exc)
        return None

    def _extract_with_playwright(self, url: str) -> Optional[str]:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=CRAWL4AI_TIMEOUT * 1000,
                    )
                    text = page.inner_text("body")
                finally:
                    browser.close()
            return text or None
        except Exception as exc:
            logger.warning("Playwright fallback failed for %s: %s", url, exc)
        return None
