"""Hybrid-Web Plugin - Intelligent extraction routing."""
from .provider import HybridWebSearchProvider


def _patch_backend_availability() -> None:
    try:
        import tools.web_tools as wt
    except Exception:
        return

    custom = {"search-cascade", "hybrid-web"}
    orig = getattr(wt, "_is_backend_available", None)
    if orig is None:
        return
    if getattr(orig, "_px1_custom_backends", False):
        return

    def _patched(backend: str) -> bool:
        name = (backend or "").lower().strip()
        if name in custom:
            return True
        return bool(orig(backend))

    _patched._px1_custom_backends = True  # type: ignore[attr-defined]
    wt._is_backend_available = _patched


def register(ctx):
    _patch_backend_availability()
    ctx.register_web_search_provider(HybridWebSearchProvider())
