"""Web extract provider using trafilatura (free, open-source, no API key)."""

import logging
from typing import Any, Dict, List

import httpx
import trafilatura

from agent.web_search_provider import WebSearchProvider

logger = logging.getLogger(__name__)


class TrafilaturaWebSearchProvider(WebSearchProvider):

    @property
    def name(self) -> str:
        return "trafilatura"

    @property
    def display_name(self) -> str:
        return "Trafilatura (free)"

    def is_available(self) -> bool:
        try:
            import trafilatura
            return True
        except ImportError:
            return False

    def supports_search(self) -> bool:
        return False

    def supports_extract(self) -> bool:
        return True

    def extract(self, urls: List[str], **kwargs) -> List[Dict[str, Any]]:
        results = []
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            for url in urls:
                results.append(self._extract_single(url, client))
        return results

    def _extract_single(self, url: str, client) -> Dict[str, Any]:
        entry = {"url": url, "title": "", "content": "",
                 "raw_content": "", "metadata": {}, "error": ""}
        try:
            resp = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()

            result = trafilatura.extract(
                resp.text,
                include_formatting=True,
                include_links=True,
                output_format="markdown",
                with_metadata=True,
            )
            if result is None:
                entry["error"] = "trafilatura could not extract content"
            elif isinstance(result, dict):
                entry["title"] = result.get("title", "")
                entry["content"] = result.get("text", "")
                entry["raw_content"] = entry["content"]
                entry["metadata"] = {
                    k: v for k, v in result.items()
                    if k in ("author", "date", "url", "hostname", "description", "sitename")
                }
            else:
                entry["content"] = str(result)
                entry["raw_content"] = entry["content"]
        except Exception as e:
            entry["error"] = str(e)
            logger.warning("Extract failed for %s: %s", url, e)
        return entry

    def get_setup_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {},
            "description": "No config needed. Trafilatura is free and open-source.",
        }
