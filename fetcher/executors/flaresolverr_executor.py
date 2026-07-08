"""FlareSolverr executor — solves Cloudflare Managed Challenge via REST API.

Deployed as Docker container on :8191. Returns clean HTML + cf_clearance cookie
which we persist to CookieStore for reuse. This is the layer curl_cffi and
cloudscraper cannot bypass (verified live earlier: Fragrantica/Parfumo blocked).
"""
import asyncio
import time
from typing import Optional
from urllib.parse import urlparse
import requests
from fetcher.base import Executor, Document
from fetcher.cookie_store import CookieStore


class FlareSolverrExecutor(Executor):
    name = "flaresolverr"
    BASE = "http://localhost:8191/v1"

    def __init__(self, base: Optional[str] = None, cookie_store: Optional[CookieStore] = None):
        self.base = base or self.BASE
        self.cookies = cookie_store or CookieStore()

    async def fetch(self, url: str, **kwargs) -> Document:
        start = time.time()
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": kwargs.get("timeout", 60000),
            "cookies": kwargs.get("cookies", []),
        }
        try:
            resp = await asyncio.to_thread(
                requests.post, self.base, json=payload, timeout=kwargs.get("timeout", 60) + 5
            )
            data = resp.json()
            if data.get("status") != "ok":
                return Document(
                    source=self.name, url=url, domain=urlparse(url).netloc,
                    executor=self.name, latency=round(time.time() - start, 3),
                    verification_status="UNVERIFIED", errors=[data.get("message", "flaresolverr error")],
                )
            sol = data["solution"]
            domain = urlparse(url).netloc
            # Persist cookies (cf_clearance etc.) for reuse
            cookies = sol.get("cookies", [])
            if cookies:
                self.cookies.save(domain, cookies)
            return Document(
                source=self.name, url=url, domain=domain, executor=self.name,
                latency=round(time.time() - start, 3),
                verification_status="VERIFIED", confidence=0.95,
                content=sol.get("response"),
                raw_response={"status": sol.get("status"), "headers": sol.get("headers", {}),
                              "url": sol.get("url"), "userAgent": sol.get("userAgent")},
                cookies_used=bool(cookies),
                estimated_cost=0.0,
                telemetry={"response_size": len(sol.get("response") or ""),
                           "cookies_saved": len(cookies)},
            )
        except Exception as e:
            return Document(
                source=self.name, url=url, domain=urlparse(url).netloc,
                executor=self.name, latency=round(time.time() - start, 3),
                verification_status="UNVERIFIED", errors=[str(e)],
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
        # FlareSolverr solves CF challenges; treat as captcha solve
        return await self.fetch(url, **kwargs)

    async def snapshot(self, url: str, **kwargs) -> Document:
        return self._unsupported("snapshot", url)
