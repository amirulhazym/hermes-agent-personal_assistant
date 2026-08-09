"""Tavily key-pool search: sticky-until-fail rotate across TAVILY_API_KEYS, DDGS final fallback.

Env: TAVILY_API_KEYS=key1,key2,... (comma-separated, no spaces)
Log: ~/.hermes/logs/tavily_key_usage.jsonl (key_index + fingerprint only, no secret)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agent.web_search_provider import WebSearchProvider

logger = logging.getLogger(__name__)

_LOG_DIR = Path.home() / ".hermes" / "logs"


class SearchCascadeProvider(WebSearchProvider):
    """Search: rotate Tavily keys pool; DDGS if all keys exhausted."""

    name = "search-cascade"
    display_name = "Search Cascade (Tavily pool → DDGS)"

    _cooldown: Dict[str, float] = {}
    _lock = threading.Lock()

    def is_available(self) -> bool:
        return self._tavily_ready() or self._ddgs_ready()

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return False

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        keys = self._load_keys()
        if not keys:
            if self._ddgs_ready():
                logger.warning("No Tavily keys; DDGS fallback")
                return self._search_ddgs(query, limit)
            return {"success": False, "error": "No search backend configured"}

        errors: List[str] = []
        for idx, key in enumerate(keys):
            with self._lock:
                if self._cooldown.get(key, 0) > time.time():
                    logger.info("Tavily key %d in cooldown; trying next", idx)
                    errors.append(f"key_{idx}_cooldown")
                    continue

            result = self._search_tavily_with_key(query, limit, key)
            if self._is_good(result):
                self._tag(result, "tavily", idx)
                self._log_usage(idx, key, True, "ok")
                return result

            err = self._err_of(result, f"tavily_key_{idx}_fail")
            errors.append(err)
            logger.warning("Tavily key %d failed: %s; rotating", idx, err)

            # cooldown if rate-limited
            if self._should_cooldown(result):
                with self._lock:
                    self._cooldown[key] = time.time() + 30  # 30s cooldown
            self._log_usage(idx, key, False, err)

        # DDGS fallback
        if self._ddgs_ready():
            logger.info("All Tavily keys exhausted; DDGS fallback")
            result = self._search_ddgs(query, limit)
            if self._is_good(result):
                result.setdefault("data", {})["fallback_from"] = "tavily_pool_exhausted"
                result.setdefault("data", {})["fallback_reason"] = "; ".join(errors[-3:])
                result.setdefault("data", {})["search_backend"] = "ddgs"
                return result

        return {"success": False, "error": "Search cascade exhausted: " + "; ".join(errors[-5:]) if errors else "No backends"}

    def _load_keys(self) -> List[str]:
        raw = os.getenv("TAVILY_API_KEYS", "")
        keys = [k.strip() for k in raw.split(",") if k.strip() and k.strip().startswith("tvly-")]
        if not keys:
            single = os.getenv("TAVILY_API_KEY", "").strip()
            if single:
                keys = [single]
        return keys

    def _tavily_ready(self) -> bool:
        return len(self._load_keys()) > 0

    def _ddgs_ready(self) -> bool:
        try:
            import ddgs  # noqa
            return True
        except ImportError:
            return False

    def _search_tavily_with_key(self, query: str, limit: int, api_key: str) -> Dict[str, Any]:
        try:
            from plugins.web.tavily.provider import _tavily_request, _normalize_tavily_search_results

            os.environ["TAVILY_API_KEY"] = api_key  # temp override
            raw = _tavily_request("search", {"query": query, "max_results": min(limit, 20), "include_raw_content": False, "include_images": False})
            return _normalize_tavily_search_results(raw)
        except Exception as exc:
            return {"success": False, "error": f"tavily exception: {exc}"}

    def _search_ddgs(self, query: str, limit: int) -> Dict[str, Any]:
        try:
            from plugins.web.ddgs.provider import DDGSWebSearchProvider

            return DDGSWebSearchProvider().search(query, limit)
        except Exception as exc:
            return {"success": False, "error": f"ddgs exception: {exc}"}

    @staticmethod
    def _is_good(result: Optional[Dict[str, Any]]) -> bool:
        if not result or not result.get("success"):
            return False
        web = (result.get("data") or {}).get("web") or []
        return len(web) > 0

    @staticmethod
    def _err_of(result: Optional[Dict[str, Any]], default: str) -> str:
        if not result:
            return default
        return str(result.get("error") or default)

    @staticmethod
    def _tag(result: Dict[str, Any], backend: str, key_index: int = 0) -> None:
        data = result.setdefault("data", {})
        data["search_backend"] = backend
        data["tavily_key_index"] = key_index

    def _should_cooldown(self, result: Optional[Dict[str, Any]]) -> bool:
        if result is None:
            return False
        error = str(result.get("error") or "").lower()
        return any(w in error for w in ("429", "rate", "limit", "quota", "exhausted"))

    def _log_usage(self, idx: int, key: str, success: bool, detail: str) -> None:
        try:
            _LOG_DIR.mkdir(parents=True, exist_ok=True)
            log_path = _LOG_DIR / "tavily_key_usage.jsonl"
            entry = json.dumps(
                {
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "key_index": idx,
                    "key_fingerprint": hashlib.sha256(key.encode()).hexdigest()[:12],
                    "success": success,
                    "detail": detail[:120],
                }
            )
            with log_path.open("a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except Exception:
            pass
