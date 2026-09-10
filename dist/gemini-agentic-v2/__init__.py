"""Agentic Depth Protocol v2 Plugin for Gemini 3.8 Flash on Antigravity.

Applies exclusively when:
  model == "gemini-3.8-flash" AND provider == "antigravity"

Injects:
1. Static Agentic Depth Protocol v2 into privileged system/developer context.
2. Bounded dynamic runtime state block (mode_hint, tool_activity, coverage_note).

Preserves:
- Cache markers
- User and assistant messages
- Existing R6-B3 guardrails without conflict or duplication
- Fail-open request shape safety
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

EXPECTED_V2_PROTOCOL_SHA256 = (
    "1392b0ba1e88588fce4e0db1e6d7b45f76a6e7acb6818c7895666ae3836c0357"
)
PROTOCOL_FILENAME = "agentic-depth-v2.txt"

TARGET_MODEL = "gemini-3.8-flash"
TARGET_PROVIDER = "antigravity"

_CACHED_PROTOCOL_TEXT: Optional[str] = None

# Sentinels for idempotency and dynamic block demarcation
V2_HEADER_SENTINEL = "# Agentic Depth Protocol v2"
DYNAMIC_BLOCK_START = "<!-- AGENTIC_V2_STATE_START -->"
DYNAMIC_BLOCK_END = "<!-- AGENTIC_V2_STATE_END -->"

DEEP_KEYWORDS = {
    "investigate", "diagnose", "debug", "audit", "review", "research",
    "verify", "implement", "fix", "refactor", "modify", "inspect",
    "root cause", "missing", "apa lagi", "apa yang terlepas", "semak",
    "cari punca", "betulkan", "check", "analyze", "reconcile",
}


def load_and_verify_protocol() -> Optional[str]:
    """Load and hash-verify the packaged Agentic Depth Protocol v2."""
    global _CACHED_PROTOCOL_TEXT
    if _CACHED_PROTOCOL_TEXT is not None:
        return _CACHED_PROTOCOL_TEXT

    protocol_path = Path(__file__).resolve().parent / PROTOCOL_FILENAME
    if not protocol_path.exists():
        logger.error("V2 protocol file missing at %s", protocol_path)
        return None

    try:
        raw_bytes = protocol_path.read_bytes()
    except Exception as exc:
        logger.error("Failed to read V2 protocol file: %s", exc)
        return None

    calculated_sha = hashlib.sha256(raw_bytes).hexdigest()
    if calculated_sha != EXPECTED_V2_PROTOCOL_SHA256:
        logger.error(
            "V2 protocol SHA-256 mismatch! expected=%s got=%s",
            EXPECTED_V2_PROTOCOL_SHA256,
            calculated_sha,
        )
        return None

    try:
        text = raw_bytes.decode("utf-8")
    except Exception as exc:
        logger.error("Failed to decode V2 protocol bytes as utf-8: %s", exc)
        return None

    _CACHED_PROTOCOL_TEXT = text
    return _CACHED_PROTOCOL_TEXT


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

    if eff_model.startswith("antigravity/"):
        eff_model = eff_model[len("antigravity/"):]

    eff_provider = (provider or "").strip().lower()
    return eff_model == TARGET_MODEL and eff_provider == TARGET_PROVIDER


def analyze_request_history(messages: List[Dict[str, Any]]) -> Tuple[str, Dict[str, int], List[str]]:
    """Derive deterministic mode_hint, tool counts, and unique observed paths."""
    searches = 0
    reads = 0
    writes = 0
    verifications = 0
    paths: Set[str] = set()

    last_user_text = ""

    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        if role == "user":
            content = msg.get("content")
            if isinstance(content, str):
                last_user_text = content.lower()
            elif isinstance(content, list):
                parts = []
                for p in content:
                    if isinstance(p, dict) and p.get("type") == "text":
                        parts.append(str(p.get("text", "")))
                    elif isinstance(p, str):
                        parts.append(p)
                last_user_text = " ".join(parts).lower()
        elif role == "assistant":
            for tc in msg.get("tool_calls") or []:
                if not isinstance(tc, dict):
                    continue
                fn = tc.get("function") or {}
                name = fn.get("name", "") if isinstance(fn, dict) else ""
                args = fn.get("arguments", "") if isinstance(fn, dict) else ""

                if name in {"search_files", "web_search"}:
                    searches += 1
                elif name in {"read_file", "web_extract"}:
                    reads += 1
                elif name in {"write_file", "patch"}:
                    writes += 1
                elif "test" in name or "verify" in name or "doctor" in name:
                    verifications += 1

                # Safely extract bounded path if present in string args
                if isinstance(args, str) and ("path" in args or "file" in args):
                    match = re.search(r'["\'](?:path|file_path)["\']\s*:\s*["\']([^"\']+)["\']', args)
                    if match:
                        clean_path = match.group(1).strip()
                        if clean_path and not clean_path.startswith("http"):
                            paths.add(Path(clean_path).name)

    # Determine mode_hint
    has_tools = (searches + reads + writes + verifications) > 0
    if has_tools:
        mode_hint = "DEEP"
    else:
        has_deep_keyword = any(kw in last_user_text for kw in DEEP_KEYWORDS)
        if has_deep_keyword:
            mode_hint = "DEEP"
        elif len(last_user_text.strip()) > 0 and len(last_user_text.split()) < 12 and not any(k in last_user_text for k in ["how", "why", "what if", "explain", "code", "run"]):
            mode_hint = "DIRECT"
        else:
            mode_hint = "MODEL_DECIDE — choose DEEP if unseen state/dependencies can materially change the answer."

    tool_counts = {
        "searches": searches,
        "reads": reads,
        "writes": writes,
        "verification": verifications,
    }
    bounded_paths = sorted(list(paths))[:5]
    return mode_hint, tool_counts, bounded_paths


def build_dynamic_state_block(mode_hint: str, tool_counts: Dict[str, int], paths: List[str]) -> str:
    """Build bounded dynamic runtime state block."""
    path_str = f" [{', '.join(paths)}]" if paths else ""
    return (
        f"{DYNAMIC_BLOCK_START}\n"
        f"# Agentic V2 Runtime State\n"
        f"mode_hint: {mode_hint}\n"
        f"tool_activity: searches={tool_counts['searches']} reads={tool_counts['reads']} "
        f"writes={tool_counts['writes']} verification={tool_counts['verification']}{path_str}\n"
        f"coverage_note: Do not finalize a DEEP task while a material referenced dependency remains unresolved.\n"
        f"{DYNAMIC_BLOCK_END}"
    )


def _strip_existing_dynamic_block(text: str) -> str:
    """Remove previous dynamic state block cleanly."""
    pattern = re.compile(
        rf"{re.escape(DYNAMIC_BLOCK_START)}.*?{re.escape(DYNAMIC_BLOCK_END)}\n*",
        re.DOTALL,
    )
    return pattern.sub("", text).strip()


def apply_v2_to_system_content(
    content: Any,
    protocol_text: str,
    dynamic_block: str,
) -> Tuple[Any, bool]:
    """Inject or update V2 static protocol and dynamic state block in system message content."""
    changed = False

    if isinstance(content, str):
        # Strip old dynamic block if present
        clean_content = _strip_existing_dynamic_block(content)

        # Check if static protocol is already present
        has_protocol = V2_HEADER_SENTINEL in clean_content

        parts = [clean_content] if clean_content else []
        if not has_protocol:
            parts.append(protocol_text)
            changed = True
        parts.append(dynamic_block)
        changed = True

        return "\n\n".join(parts), changed

    elif isinstance(content, list):
        # Structured content parts
        # 1. Strip dynamic block from existing parts
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                pt = part.get("text", "")
                if DYNAMIC_BLOCK_START in pt:
                    part["text"] = _strip_existing_dynamic_block(pt)
                    changed = True

        # 2. Check if protocol exists in any part
        has_protocol = False
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                if V2_HEADER_SENTINEL in part.get("text", ""):
                    has_protocol = True
                    break
            elif isinstance(part, str) and V2_HEADER_SENTINEL in part:
                has_protocol = True
                break

        if not has_protocol:
            content.append({"type": "text", "text": f"\n\n{protocol_text}"})
            changed = True

        content.append({"type": "text", "text": f"\n\n{dynamic_block}"})
        changed = True
        return content, changed

    return content, False


def apply_v2_to_request(
    request: Dict[str, Any],
    protocol_text: str,
    dynamic_block: str,
) -> Dict[str, Any]:
    """Apply V2 protocol and dynamic block into request copy."""
    if not isinstance(request, dict):
        return request

    messages = request.get("messages")
    if not isinstance(messages, list):
        return request

    # Find the first system or developer message
    system_msg_idx: Optional[int] = None
    for idx, msg in enumerate(messages):
        if isinstance(msg, dict) and msg.get("role") in {"system", "developer"}:
            system_msg_idx = idx
            break

    if system_msg_idx is not None:
        sys_msg = messages[system_msg_idx]
        if isinstance(sys_msg, dict):
            new_content, _ = apply_v2_to_system_content(
                sys_msg.get("content"),
                protocol_text,
                dynamic_block,
            )
            sys_msg["content"] = new_content
    else:
        # No system message present — insert a new system message at index 0
        new_sys_msg = {
            "role": "system",
            "content": f"{protocol_text}\n\n{dynamic_block}",
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
        return None

    protocol_text = load_and_verify_protocol()
    if not protocol_text:
        return None

    messages = request.get("messages")
    if not isinstance(messages, list):
        return None

    mode_hint, tool_counts, paths = analyze_request_history(messages)
    dynamic_block = build_dynamic_state_block(mode_hint, tool_counts, paths)

    modified_request = apply_v2_to_request(request, protocol_text, dynamic_block)
    return {
        "request": modified_request,
        "source": "gemini-agentic-v2",
        "reason": "injected_agentic_depth_v2",
    }


def register(ctx: Any) -> None:
    """Register the plugin middleware with Hermes PluginContext."""
    protocol_text = load_and_verify_protocol()
    if not protocol_text:
        logger.error("gemini-agentic-v2: Protocol verification failed at registration!")

    ctx.register_middleware("llm_request", on_llm_request)
    logger.info("gemini-agentic-v2: registered llm_request middleware.")
