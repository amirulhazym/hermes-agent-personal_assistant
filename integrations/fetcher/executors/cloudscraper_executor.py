"""cloudscraper executor — lightweight Cloudflare JS challenge solver (no browser).

Second tier. Handles simple Cloudflare challenges that curl_cffi cannot.
Does NOT solve Managed Challenge (that needs FlareSolverr).
"""
import asyncio
import time
from urllib.parse import urlparse
import cloudscraper
from fetcher.base import Executor, Document


class CloudscraperExecutor(Executor):
    name = "cloudscraper"

    def _session(self):
        return cloudscraper.create_scraper()

    async def fetch(self, url: str, **kwargs) -> Document:
        start = time.time()
        try:
            scraper = await asyncio.to_thread(self._session)
            resp = await asyncio.to_thread(
                scraper.get, url, timeout=kwargs.get("timeout", 20),
                headers=kwargs.get("headers"),
            )
            return Document(
                source=self.name,
                url=url,
                domain=urlparse(url).netloc,
                executor=self.name,
                latency=round(time.time() - start, 3),
                verification_status="VERIFIED",
                confidence=0.85,
                content=resp.text,
                raw_response={"status": resp.status_code, "headers": dict(resp.headers)},
                estimated_cost=0.0,
                headers=kwargs.get("headers", {}),
                telemetry={"response_size": len(resp.text or "")},
            )
        except Exception as e:
            return Document(
                source=self.name,
                url=url,
                domain=urlparse(url).netloc,
                executor=self.name,
                latency=round(time.time() - start, 3),
                verification_status="UNVERIFIED",
                errors=[str(e)],
            )

    async def search(self, query: str, **kwargs) -> Document:
        from urllib.parse import quote
        return await self.fetch(f"https://www.google.com/search?q={quote(query)}", **kwargs)

    async def crawl(self, url: str, **kwargs) -> list:
        return [await self.fetch(url, **kwargs)]

    async def extract(self, doc: Document, **kwargs) -> Document:
        return doc

    async def interact(self, url: str, actions: list, **kwargs) -> Document:
        return self._unsupported("interact", url)

    async def login(self, url: str, creds: dict, **kwargs) -> Document:
        return self._unsupported("login", url)

    async def solve_captcha(self, url: str, **kwargs) -> Document:
        return self._unsupported("solve_captcha", url)

    async def snapshot(self, url: str, **kwargs) -> Document:
        return self._unsupported("snapshot", url)
