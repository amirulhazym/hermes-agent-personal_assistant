"""
Hybrid-Web Plugin - Intelligent extraction routing.

Routes between Trafilatura (static HTML) and Crawl4AI (JS-heavy SPAs)
based on page characteristics.

Inherits from agent.web_search_provider.WebSearchProvider so it integrates
with Hermes' standard web search/extract plugin registry.
"""
from __future__ import annotations

import logging
import os
import re
import signal
import time
from typing import Any, Dict, List, Optional, Tuple

from agent.web_search_provider import WebSearchProvider

logger = logging.getLogger(__name__)

TRAFILATURA_TIMEOUT = 10
CRAWL4AI_TIMEOUT = 45

# Playwright ships no bundled Chromium on this host (`~/.cache/ms-playwright`
# is empty), so `chromium.launch()` with no channel raises
# "Executable doesn't exist ... chrome-headless-shell".  Prefer the
# system-installed Chrome and fall back to the bundled build for hosts that
# do have it.  `None` = let Playwright use its default resolution.
CHROME_CHANNEL_CANDIDATES: Tuple[Optional[str], ...] = ("chrome", None)

# Marker for the Playwright node driver that every Playwright client spawns as
# a direct child process.
_PLAYWRIGHT_DRIVER_MARKER = "playwright/driver/package/cli.js"

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

            from crawl4ai import AsyncWebCrawler, BrowserConfig
        except Exception as exc:
            logger.warning("Crawl4AI unavailable for %s: %s", url, exc)
            return None

        async def _run(channel: Optional[str]):
            kwargs: Dict[str, Any] = {"headless": True}
            if channel:
                kwargs["chrome_channel"] = channel
            try:
                config = BrowserConfig(**kwargs)
            except TypeError:
                # Older crawl4ai without `chrome_channel`.
                config = BrowserConfig(headless=True)
            drivers_before = set(_child_playwright_drivers())
            reaped_here: List[int] = []
            try:
                async with AsyncWebCrawler(config=config) as crawler:
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
            except BaseException:
                # crawl4ai leaks its Playwright node driver (a direct child of
                # this process, ~135 MB RSS) whenever the launch raises — the
                # client is never stopped.  Reap inside the running loop so the
                # child watcher sees the exit cleanly, and only the drivers this
                # attempt created.
                reaped_here.extend(_reap_new_drivers(drivers_before))
                reaped_by_attempt.append(len(reaped_here))
                raise

        reaped_by_attempt: List[int] = []
        for channel in CHROME_CHANNEL_CANDIDATES:
            drivers_before = set(_child_playwright_drivers())
            try:
                try:
                    return asyncio.run(_run(channel))
                except RuntimeError:
                    # A loop is already running in this thread (gateway).
                    loop = asyncio.new_event_loop()
                    try:
                        return loop.run_until_complete(_run(channel))
                    finally:
                        loop.close()
            except Exception as exc:
                # crawl4ai leaks its Playwright node driver (a direct child of
                # this process, ~135 MB RSS) whenever the launch raises — the
                # client is never stopped.  Reap only the drivers this attempt
                # created, so a concurrent healthy extraction is untouched.
                leaked = _reap_new_drivers(drivers_before)
                logger.warning(
                    "Crawl4AI failed for %s via %s: %s (reaped %d leaked driver(s))",
                    url,
                    channel or "bundled-chromium",
                    exc,
                    len(leaked) + (reaped_by_attempt[-1] if reaped_by_attempt else 0),
                )
            finally:
                # Belt and braces: even on a "clean" return crawl4ai can leave
                # a driver behind after a mid-crawl crash.
                # Cheap single scan on the happy path; no polling latency.
                _reap_new_drivers(drivers_before, grace_s=0.0)
        return None

    def _extract_with_playwright(self, url: str) -> Optional[str]:
        try:
            from playwright.sync_api import sync_playwright

            last_exc: Optional[Exception] = None
            for channel in CHROME_CHANNEL_CANDIDATES:
                launch_kwargs: Dict[str, Any] = {"headless": True}
                if channel:
                    launch_kwargs["channel"] = channel
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch(**launch_kwargs)
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
                except Exception as exc:  # channel missing -> try next
                    last_exc = exc
                    continue
            if last_exc is not None:
                raise last_exc
        except Exception as exc:
            logger.warning("Playwright fallback failed for %s: %s", url, exc)
        return None


def _child_playwright_drivers(proc_root: str = "/proc") -> List[int]:
    """PIDs of Playwright node drivers whose parent is this process.

    Reads ``/proc`` directly: no subprocess, safe to call inside the gateway
    on every extraction.
    """
    me = os.getpid()
    found: List[int] = []
    try:
        entries = os.listdir(proc_root)
    except OSError:
        return found
    for entry in entries:
        if not entry.isdigit():
            continue
        pid = int(entry)
        try:
            with open(os.path.join(proc_root, entry, "stat"), "r") as fh:
                stat = fh.read()
            # Format: pid (comm) state ppid ...  -> comm may contain spaces
            fields = stat.rsplit(")", 1)[1].split()
            if len(fields) < 2 or int(fields[1]) != me:
                continue
            with open(os.path.join(proc_root, entry, "cmdline"), "rb") as fh:
                cmdline = fh.read().replace(b"\x00", b" ").decode(
                    "utf-8", "replace"
                )
        except OSError:
            continue
        if _PLAYWRIGHT_DRIVER_MARKER in cmdline:
            found.append(pid)
    return found


def _reap_drivers(pids: "set[int]") -> List[int]:
    """SIGTERM leaked Playwright drivers; SIGKILL only stragglers."""
    reaped: List[int] = []
    for pid in sorted(pids):
        try:
            os.kill(pid, signal.SIGTERM)
            reaped.append(pid)
        except OSError:
            continue
    for pid in reaped:
        for _ in range(20):  # up to ~2s
            try:
                os.kill(pid, 0)
            except OSError:
                break
            time.sleep(0.1)
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    return reaped


def _pids_with_children(proc_root: str = "/proc") -> "set[int]":
    """Every PID that currently has at least one child (cheap /proc scan)."""
    parents: "set[int]" = set()
    try:
        entries = os.listdir(proc_root)
    except OSError:
        return parents
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open(os.path.join(proc_root, entry, "stat"), "r") as fh:
                fields = fh.read().rsplit(")", 1)[1].split()
            parents.add(int(fields[1]))
        except (OSError, IndexError, ValueError):
            continue
    return parents


def _reap_new_drivers(before: "set[int]", grace_s: float = 1.5) -> List[int]:
    """Reap drivers that appeared after ``before`` was snapshotted.

    The leaked driver can register slightly after the launch exception
    surfaces, so poll for a short grace window instead of scanning once.
    Only childless drivers are reaped — a driver that still owns a browser
    process belongs to an extraction that is genuinely running.
    """
    reaped: List[int] = []
    deadline = time.monotonic() + grace_s
    while True:
        parents = _pids_with_children()
        fresh = {
            pid
            for pid in set(_child_playwright_drivers()) - before - set(reaped)
            if pid not in parents
        }
        if fresh:
            reaped.extend(_reap_drivers(fresh))
        if time.monotonic() >= deadline:
            break
        time.sleep(0.1)
    return reaped
