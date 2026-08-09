"""
LightClaw — multi-tenant API key routing.
Mirrors: src/config.ts (L67-169) — resolveEffectiveApiKey, setApiKeyMap,
setSessionApiKey, extractUinFromSessionKey, buildAuthHeaders.

Routing model
-------------
Two lookup tables are maintained at module scope:

    _global_api_key_map : { uin: apiKey }
        Built once at adapter startup from the configured API keys + the
        uin(s) returned by POST /cgi/ticket. Used by inbound handlers
        (which know the sender's uin directly).

    _session_key_to_api_key : { sessionKey.lower(): apiKey }
        Populated by the inbound handler when it starts processing a
        message. AI tool handlers (which only know ``ctx.sessionKey``)
        use this table to resolve the tenant's key without having to
        re-extract the uin.

Resolution priority (mirrors TS):
    1. sessionKey direct hit
    2. senderId direct hit
    3. uin extracted from sessionKey → global map
    4. _global_default_api_key
"""

from __future__ import annotations

import threading
from typing import Dict, Optional

from .config import CHANNEL_KEY, X_PRODUCT

# ---------------------------------------------------------------------------
# Module state (guarded by _lock)
# ---------------------------------------------------------------------------

_lock = threading.RLock()
_global_api_key_map: Dict[str, str] = {}
_global_default_api_key: str = ""
_session_key_to_api_key: Dict[str, str] = {}


# ---------------------------------------------------------------------------
# Registration helpers
# ---------------------------------------------------------------------------

def set_api_key_map(mapping: Dict[str, str], default_api_key: str) -> None:
    """Replace the uin→apiKey map and the default key.

    Called once by ``LightClawAdapter.connect()`` after identity
    resolution. *mapping* may be empty — in that case every lookup falls
    through to *default_api_key*.
    """
    global _global_default_api_key
    with _lock:
        _global_api_key_map.clear()
        if mapping:
            _global_api_key_map.update(mapping)
        _global_default_api_key = default_api_key or ""


def set_session_api_key(session_key: str, api_key: str) -> None:
    """Record a ``sessionKey → apiKey`` association.

    Called by the inbound handler right before dispatching a message to
    the agent so that tools executing within that session can look up
    the tenant's API key via the same session key.
    """
    if not session_key or not api_key:
        return
    with _lock:
        _session_key_to_api_key[session_key.lower()] = api_key


def clear_session_api_key(session_key: str) -> None:
    """Best-effort cleanup; safe to call even if the key was never set."""
    if not session_key:
        return
    with _lock:
        _session_key_to_api_key.pop(session_key.lower(), None)


# ---------------------------------------------------------------------------
# sessionKey → uin extraction (mirrors TS extractUinFromSessionKey)
# ---------------------------------------------------------------------------

def extract_uin_from_session_key(session_key: str) -> Optional[str]:
    """Extract the peer uin embedded in a session key.

    Supported shapes (lowercased for matching, returned case-preserving):
        * ``agent:<agentId>:<channel>:direct:<peerId>[...]``
        * ``agent:<agentId>:<channel>:dm:<peerId>[...]``
        * legacy ``<channel>:dm:<peerId>``

    Returns ``None`` when no uin segment can be located (e.g. the main
    session key ``agent:main:main``).
    """
    if not session_key:
        return None

    lower = session_key.lower()

    for marker in (":direct:", ":dm:"):
        idx = lower.find(marker)
        if idx >= 0:
            tail = session_key[idx + len(marker):]
            peer = tail.split(":", 1)[0]
            return peer or None

    # Legacy pattern: "<channel>:dm:<peerId>"
    legacy_prefix = f"{CHANNEL_KEY}:dm:"
    if lower.startswith(legacy_prefix.lower()):
        remainder = session_key[len(legacy_prefix):]
        return remainder or None

    return None


# ---------------------------------------------------------------------------
# Unified resolution entry point
# ---------------------------------------------------------------------------

def resolve_effective_api_key(
    *,
    session_key: Optional[str] = None,
    sender_id: Optional[str] = None,
) -> str:
    """Resolve the tenant's apiKey for a given context.

    Returns the default key (possibly empty string) when no specific
    match is found.  Callers should generally have at least one of
    *session_key* or *sender_id* populated.
    """
    with _lock:
        # 1. sessionKey → direct lookup
        if session_key:
            hit = _session_key_to_api_key.get(session_key.lower())
            if hit:
                return hit

        # 2. senderId (uin) → direct lookup
        if sender_id:
            hit = _global_api_key_map.get(sender_id)
            if hit:
                return hit

        # 3. Extract uin from sessionKey, look up again
        if session_key:
            uin = extract_uin_from_session_key(session_key)
            if uin:
                hit = _global_api_key_map.get(uin)
                if hit:
                    return hit

        # 4. Fallback
        return _global_default_api_key


# ---------------------------------------------------------------------------
# Auth header builder (mirrors TS utils/common.ts buildAuthHeaders)
# ---------------------------------------------------------------------------

def build_auth_headers(api_key: str) -> Dict[str, str]:
    """Build the standard auth headers used by /cgi/* and /drive/* endpoints."""
    return {
        "authorization": f"Bearer {api_key or ''}",
        "x-product": X_PRODUCT,
    }
