"""BrowserAct executor — CAPTCHA solving + human handoff (DEFERRED: payment).

This is a STUB only. BrowserAct is NOT installed, NOT integrated, NOT paid.
Executor interface is maintained so integration is straightforward when the
user approves payment.

Requirements to activate:
  1. uv tool install browser-act-cli  (paid; requires payment approval)
  2. Wire into AdaptiveRouter executors dict
  3. Configure via capability_registry.yaml for captcha-needed domains
"""
from fetcher.browser_executor import BrowserExecutor
from fetcher.base import Document


class BrowserActExecutor(BrowserExecutor):
    name = "browseract"
    is_browser = True

    def __init__(self):
        pass

    async def fetch(self, url: str, **kwargs) -> Document:
        return self._unsupported("fetch", url)

    async def search(self, query: str, **kwargs) -> Document:
        return self._unsupported("search")

    async def crawl(self, url: str, **kwargs) -> list:
        return [self._unsupported("crawl", url)]

    async def extract(self, doc: Document, **kwargs) -> Document:
        return self._unsupported("extract")

    async def interact(self, url: str, actions: list, **kwargs) -> Document:
        return self._unsupported("interact", url)

    async def login(self, url: str, creds: dict, **kwargs) -> Document:
        return self._unsupported("login", url)

    async def solve_captcha(self, url: str, **kwargs) -> Document:
        return self._unsupported("solve_captcha", url)

    async def snapshot(self, url: str, **kwargs) -> Document:
        return self._unsupported("snapshot", url)
