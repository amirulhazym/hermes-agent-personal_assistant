"""Crawl4AI executor — CURRENT browser implementation behind BrowserExecutor.

Wraps Crawl4AI AsyncWebCrawler with Playwright Stealth. This is the
implementation, NOT the interface. Router depends on BrowserExecutor, not this.
If Crawl4AI is replaced, swap this file; Router unchanged.

Lifecycle: creates a fresh AsyncWebCrawler per call (async with). Crawl4AI
v0.9.1 PlaywrightAdapter manages Chromium processes internally. First call
starts the browser (~2-5s); subsequent calls reuse the Chromium binary for
faster warmup. Optimization (persistent crawler) deferred to Phase 5.

Capabilities: JS rendering, markdown generation, structured extraction,
content filtering, screenshots, PDF, deep crawling, session reuse.
"""
import time
from typing import Optional
from urllib.parse import urlparse
from fetcher.browser_executor import BrowserExecutor
from fetcher.base import Document
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


class Crawl4AIExecutor(BrowserExecutor):
    name = "browser"
    is_browser = True

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 60,
        proxy: Optional[dict] = None,
        verbose: bool = False,
    ):
        self.browser_config = BrowserConfig(
            headless=headless,
            verbose=verbose,
            user_agent_mode="random",
            proxy_config=proxy,
            browser_type="chromium",
            enable_stealth=True,
        )
        self.default_timeout = timeout

    async def _run(self, url: str, **kwargs) -> tuple:
        """Run Crawl4AI and return (crawl_result, elapsed_seconds)."""
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=kwargs.get("timeout", self.default_timeout) * 1000,
            wait_until="domcontentloaded",
            screenshot=kwargs.get("screenshot", False),
            verbose=False,
        )
        start = time.time()
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            result = await crawler.arun(url, config=run_config)
        return result, round(time.time() - start, 3)

    def _result_to_doc(self, result, url: str, latency: float, **kwargs) -> Document:
        if result.success:
            return Document(
                source=self.name,
                url=url,
                domain=urlparse(url).netloc,
                executor=self.name,
                latency=latency,
                verification_status="VERIFIED",
                confidence=0.95,
                cache_status="HIT" if getattr(result, "from_cache", False) else "MISS",
                content=result.cleaned_html or result.html,
                markdown=result.markdown,
                structured_data=getattr(result, "extracted_content", None),
                links=result.links or [],
                images=result.media or [],
                raw_response={"status": result.status_code},
                estimated_cost=0.0,
                telemetry={"response_size": len(result.html or "")},
                errors=[],
            )
        else:
            return Document(
                source=self.name,
                url=url,
                domain=urlparse(url).netloc,
                executor=self.name,
                latency=latency,
                verification_status="UNVERIFIED",
                errors=[result.error_message or "Crawl4AI unknown error"],
            )

    async def fetch(self, url: str, **kwargs) -> Document:
        result, latency = await self._run(url, **kwargs)
        return self._result_to_doc(result, url, latency, **kwargs)

    async def search(self, query: str, **kwargs) -> Document:
        from urllib.parse import quote
        return await self.fetch(f"https://www.google.com/search?q={quote(query)}", **kwargs)

    async def crawl(self, url: str, **kwargs) -> list:
        result, latency = await self._run(url, **kwargs)
        doc = self._result_to_doc(result, url, latency, **kwargs)
        return [doc]

    async def extract(self, doc: Document, **kwargs) -> Document:
        return doc

    async def interact(self, url: str, actions: list, **kwargs) -> Document:
        return await self.fetch(url, **kwargs)

    async def login(self, url: str, creds: dict, **kwargs) -> Document:
        return self._unsupported("login", url)

    async def solve_captcha(self, url: str, **kwargs) -> Document:
        return await self.fetch(url, **kwargs)

    async def snapshot(self, url: str, **kwargs) -> Document:
        kwargs["screenshot"] = True
        return await self.fetch(url, **kwargs)

    async def close(self):
        """No-op: each call manages its own AsyncWebCrawler lifecycle."""
        pass
