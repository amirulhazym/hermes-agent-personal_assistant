from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional


@dataclass(frozen=True)
class LiveWireStatus:
    hermes_root: str
    browser: bool
    search: bool
    extract: bool
    detail: Mapping[str, str]


def discover_hermes_root() -> Optional[Path]:
    env = os.environ.get("HERMES_AGENT_ROOT") or os.environ.get("HERMES_HOME")
    if env:
        p = Path(env).expanduser()
        if (p / "tools" / "browser_tool.py").is_file():
            return p
        if (p / "hermes-agent" / "tools" / "browser_tool.py").is_file():
            return p / "hermes-agent"
    for candidate in (
        Path.home() / ".hermes" / "hermes-agent",
        Path("/home/ubuntu/.hermes/hermes-agent"),
    ):
        if (candidate / "tools" / "browser_tool.py").is_file():
            return candidate
    return None


def _ensure_path(root: Path) -> None:
    s = str(root)
    if s not in sys.path:
        sys.path.insert(0, s)


def load_browser_callables(
    hermes_root: Optional[Path] = None,
) -> tuple[dict[str, Callable[..., Any]], LiveWireStatus]:
    root = hermes_root or discover_hermes_root()
    detail: dict[str, str] = {}
    if root is None:
        return {}, LiveWireStatus("", False, False, False, {"error": "hermes root not found"})
    _ensure_path(root)
    try:
        browser_tool = importlib.import_module("tools.browser_tool")
    except Exception as exc:  # pragma: no cover - environment dependent
        return {}, LiveWireStatus(
            str(root), False, False, False, {"browser_import": type(exc).__name__}
        )

    callables: dict[str, Callable[..., Any]] = {}
    for name, attr in (
        ("navigate", "browser_navigate"),
        ("snapshot", "browser_snapshot"),
        ("click", "browser_click"),
        ("type_text", "browser_type"),
        ("cleanup", "cleanup_browser"),
    ):
        fn = getattr(browser_tool, attr, None)
        if callable(fn):
            callables[name] = fn
            detail[attr] = "ok"
        else:
            detail[attr] = "missing"
    status = LiveWireStatus(
        hermes_root=str(root),
        browser=bool(callables.get("navigate") and callables.get("snapshot")),
        search=False,
        extract=False,
        detail=detail,
    )
    return callables, status


def load_research_callables(
    hermes_root: Optional[Path] = None,
) -> tuple[dict[str, Callable[..., Any]], LiveWireStatus]:
    root = hermes_root or discover_hermes_root()
    detail: dict[str, str] = {}
    if root is None:
        return {}, LiveWireStatus("", False, False, False, {"error": "hermes root not found"})
    _ensure_path(root)
    try:
        web_tools = importlib.import_module("tools.web_tools")
    except Exception as exc:  # pragma: no cover
        return {}, LiveWireStatus(
            str(root), False, False, False, {"web_import": type(exc).__name__}
        )

    callables: dict[str, Callable[..., Any]] = {}
    search = getattr(web_tools, "web_search_tool", None)
    extract = getattr(web_tools, "web_extract_tool", None)
    if callable(search):
        callables["search_fn"] = search
        detail["web_search_tool"] = "ok"
    else:
        detail["web_search_tool"] = "missing"
    if callable(extract):
        def _extract(urls: list[str]) -> Any:
            return extract(urls)

        callables["extract_fn"] = _extract
        detail["web_extract_tool"] = "ok"
    else:
        detail["web_extract_tool"] = "missing"
    status = LiveWireStatus(
        hermes_root=str(root),
        browser=False,
        search="search_fn" in callables,
        extract="extract_fn" in callables,
        detail=detail,
    )
    return callables, status


def wire_status() -> dict[str, Any]:
    b_call, b_st = load_browser_callables()
    r_call, r_st = load_research_callables()
    return {
        "hermes_root": b_st.hermes_root or r_st.hermes_root,
        "browser_wired": b_st.browser,
        "search_wired": r_st.search,
        "extract_wired": r_st.extract,
        "browser_detail": dict(b_st.detail),
        "research_detail": dict(r_st.detail),
        "callable_names": sorted(set(b_call) | set(r_call)),
    }
