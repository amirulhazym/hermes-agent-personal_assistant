"""Exact R6-B3 guardrail middleware plugin for Gemini 3.8 Flash on Antigravity.

This plugin registers a single `llm_request` middleware callback that injects
the exact R6-B3 guardrail into provider-facing system context when and only when:
  model == "gemini-3.8-flash" AND provider == "antigravity"

Hardened in Round 7B.1:
1. Exact provider equality `provider == "antigravity"`. Removed broader alias.
2. Privileged-context idempotency: checks ONLY system and developer messages
   for existing treatment, preventing user-message quotes from suppressing guardrail.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

EXPECTED_GUARDRAIL_SHA256 = (
    "950601ceebecdee13b94c9791cd0f212d03ab260cda7bdc9ba1970ecd47edbed"
)
GUARDRAIL_FILENAME = "r6-b3-guardrail.txt"

TARGET_MODEL = "gemini-3.8-flash"
TARGET_PROVIDER = "antigravity"

_CACHED_GUARDRAIL_TEXT: Optional[str] = None


def load_and_verify_guardrail() -> Optional[str]:
    """Load and hash-verify the packaged R6-B3 guardrail file."""
    global _CACHED_GUARDRAIL_TEXT
    if _CACHED_GUARDRAIL_TEXT is not None:
        return _CACHED_GUARDRAIL_TEXT

    guardrail_path = Path(__file__).resolve().parent / GUARDRAIL_FILENAME
    if not guardrail_path.exists():
        logger.error("R6-B3 guardrail file missing at %s", guardrail_path)
        return None

    try:
        raw_bytes = guardrail_path.read_bytes()
    except Exception as exc:
        logger.error("Failed to read R6-B3 guardrail file: %s", exc)
        return None

    calculated_sha = hashlib.sha256(raw_bytes).hexdigest()
    if calculated_sha != EXPECTED_GUARDRAIL_SHA256:
        logger.error(
            "R6-B3 guardrail SHA-256 mismatch! expected=%s got=%s",
            EXPECTED_GUARDRAIL_SHA256,
            calculated_sha,
        )
        return None

    try:
        text = raw_bytes.decode("utf-8")
    except Exception as exc:
        logger.error("Failed to decode R6-B3 guardrail bytes as utf-8: %s", exc)
        return None

    _CACHED_GUARDRAIL_TEXT = text
    return _CACHED_GUARDRAIL_TEXT


def is_target_request(
    model: Optional[str],
    provider: Optional[str],
    request: Dict[str, Any],
) -> bool:
    """Return True if and only if request targets gemini-3.8-flash on antigravity."""
    eff_model = (model or "").strip()
    if not eff_model:
        req_model = request.get("model")
        if isinstance(req_model, str):
            eff_model = req_model.strip()

    # Strip optional provider prefix like 'antigravity/' if present
    if eff_model.startswith("antigravity/"):
        eff_model = eff_model[len("antigravity/"):]

    eff_provider = (provider or "").strip().lower()

    return eff_model == TARGET_MODEL and eff_provider == TARGET_PROVIDER


def _contains_guardrail(text: str, guardrail: str) -> bool:
    return guardrail in text


def _privileged_context_contains_guardrail(
    messages: List[Dict[str, Any]],
    guardrail: str,
) -> bool:
    """Check ONLY privileged prompt-bearing messages (system / developer).
    
    User, assistant, and tool messages are strictly ignored so user content
    cannot suppress guardrail injection.
    """
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        if role not in {"system", "developer"}:
            continue
        content = msg.get("content")
        if isinstance(content, str) and _contains_guardrail(content, guardrail):
            return True
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text", "")
                    if isinstance(text, str) and _contains_guardrail(text, guardrail):
                        return True
                elif isinstance(part, str) and _contains_guardrail(part, guardrail):
                    return True
    return False


def _inject_into_system_message(
    msg: Dict[str, Any],
    guardrail: str,
) -> bool:
    """Inject guardrail into an existing system/developer message.
    
    Returns True if injected, False if already present or unsupported format.
    """
    content = msg.get("content")
    if isinstance(content, str):
        if _contains_guardrail(content, guardrail):
            return False
        # Append with double newline separator
        msg["content"] = f"{content}\n\n{guardrail}" if content.strip() else guardrail
        return True
    elif isinstance(content, list):
        # Structured content parts: list of dicts or strings
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                part_text = part.get("text", "")
                if isinstance(part_text, str) and _contains_guardrail(part_text, guardrail):
                    return False
            elif isinstance(part, str) and _contains_guardrail(part, guardrail):
                return False

        # Add guardrail text part. If last part had cache_control, we preserve its position.
        # We append a new text part without disturbing existing cache_control markers.
        content.append({"type": "text", "text": f"\n\n{guardrail}"})
        return True
    return False


def apply_guardrail_to_request(
    request: Dict[str, Any],
    guardrail: str,
) -> Dict[str, Any]:
    """Pure function injecting guardrail into request copy, preserving cache markers and fail-open."""
    if not isinstance(request, dict):
        return request

    messages = request.get("messages")
    if not isinstance(messages, list):
        # Unsupported request shape (e.g. non-chat / raw prompt). Fail open.
        return request

    # If already present in privileged context (system/developer), do nothing (idempotent)
    if _privileged_context_contains_guardrail(messages, guardrail):
        return request

    # Find the first system or developer message
    system_msg_idx: Optional[int] = None
    for idx, msg in enumerate(messages):
        if isinstance(msg, dict) and msg.get("role") in {"system", "developer"}:
            system_msg_idx = idx
            break

    if system_msg_idx is not None:
        sys_msg = messages[system_msg_idx]
        if not isinstance(sys_msg, dict):
            return request
        _inject_into_system_message(sys_msg, guardrail)
    else:
        # No system message present — insert a new system message at index 0
        new_sys_msg = {
            "role": "system",
            "content": guardrail,
        }
        messages.insert(0, new_sys_msg)

    return request


def on_llm_request(**kwargs: Any) -> Optional[Dict[str, Any]]:
    """Middleware callback for llm_request."""
    request = kwargs.get("request")
    if not isinstance(request, dict):
        return None

    model = kwargs.get("model")
    provider = kwargs.get("provider")

    if not is_target_request(model, provider, request):
        # Non-target: leave completely unchanged
        return None

    guardrail = load_and_verify_guardrail()
    if not guardrail:
        # Hash mismatch or unreadable file: fail open without modifying request
        return None

    # Apply to request (the middleware harness in Hermes already passes deep-copied request)
    modified_request = apply_guardrail_to_request(request, guardrail)
    return {
        "request": modified_request,
        "source": "gemini-r6b3-guardrail",
        "reason": "injected_r6b3_system_guardrail",
    }


def register(ctx: Any) -> None:
    """Register the plugin middleware with Hermes PluginContext."""
    # Eager verification of the packaged guardrail artifact
    guardrail = load_and_verify_guardrail()
    if not guardrail:
        logger.error(
            "gemini-r6b3-guardrail: Guardrail verification failed at registration! Middleware will fail-open."
        )

    ctx.register_middleware("llm_request", on_llm_request)
    logger.info("gemini-r6b3-guardrail: registered llm_request middleware.")
