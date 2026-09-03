"""curl_cffi executor — static HTML with TLS fingerprint spoofing.

Fastest, cheapest (free), no browser. First tier for static sites.
"""
import asyncio
import time
from urllib.parse import urlparse
from curl_cffi import requests as cffi
from fetcher.base import Executor, Document


class CurlCffiExecutor(Executor):
    name = "curl_cffi"

    async def fetch(self, url: str, **kwargs) -> Document:
        start = time.time()
        try:
            resp = await asyncio.to_thread(
                cffi.get,
                url,
                impersonate="chrome120",
                timeout=kwargs.get("timeout", 15),
                headers=kwargs.get("headers"),
                proxies=kwargs.get("proxies"),
            )
            return Document(
                source=self.name,
                url=url,
                domain=urlparse(url).netloc,
                executor=self.name,
                latency=round(time.time() - start, 3),
                verification_status="VERIFIED",
                confidence=0.9,
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
        # curl_cffi has no search API; delegate to fetch on a search URL
        from urllib.parse import quote
        return await self.fetch(f"https://www.google.com/search?q={quote(query)}", **kwargs)

    async def crawl(self, url: str, **kwargs) -> list:
        return [await self.fetch(url, **kwargs)]

    async def extract(self, doc: Document, **kwargs) -> Document:
        return doc  # no transformation; adapter does extraction

    async def interact(self, url: str, actions: list, **kwargs) -> Document:
        return self._unsupported("interact", url)

    async def login(self, url: str, creds: dict, **kwargs) -> Document:
        return self._unsupported("login", url)

    async def solve_captcha(self, url: str, **kwargs) -> Document:
        return self._unsupported("solve_captcha", url)

    async def snapshot(self, url: str, **kwargs) -> Document:
        return self._unsupported("snapshot", url)
