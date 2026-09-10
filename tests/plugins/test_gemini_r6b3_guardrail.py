from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
from typing import Any, Dict
import pytest

# Target plugin path inside repository SSOT
REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "plugins" / "gemini-r6b3-guardrail"
INIT_FILE = PLUGIN_DIR / "__init__.py"

spec = importlib.util.spec_from_file_location("gemini_r6b3_guardrail_repo_v1", INIT_FILE)
assert spec is not None and spec.loader is not None
plugin = importlib.util.module_from_spec(spec)
sys.modules["gemini_r6b3_guardrail_repo_v1"] = plugin
spec.loader.exec_module(plugin)

EXPECTED_GUARDRAIL_SHA256 = (
    "950601ceebecdee13b94c9791cd0f212d03ab260cda7bdc9ba1970ecd47edbed"
)


def count_r6b3_occurrences_by_role(request: Dict[str, Any], guardrail_text: str) -> Dict[str, int]:
    """Count exact occurrences of guardrail_text in request separated by role."""
    counts = {"privileged": 0, "user": 0, "assistant": 0, "tool": 0, "other": 0}
    if not isinstance(request, dict):
        return counts
    messages = request.get("messages")
    if not isinstance(messages, list):
        return counts

    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        category = "privileged" if role in {"system", "developer"} else (role if role in counts else "other")
        content = msg.get("content")
        occ = 0
        if isinstance(content, str):
            occ = content.count(guardrail_text)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    occ += str(part.get("text", "")).count(guardrail_text)
                elif isinstance(part, str):
                    occ += part.count(guardrail_text)
        counts[category] += occ
    return counts


@pytest.fixture
def guardrail_text():
    text = plugin.load_and_verify_guardrail()
    assert text is not None
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == EXPECTED_GUARDRAIL_SHA256
    return text


def test_guardrail_hash_and_load(guardrail_text):
    assert len(guardrail_text) > 0
    assert hashlib.sha256(guardrail_text.encode("utf-8")).hexdigest() == EXPECTED_GUARDRAIL_SHA256


def test_target_predicate_exact_provider_and_model():
    # 1. exact gemini-3.8-flash + antigravity target gets treatment
    assert plugin.is_target_request("gemini-3.8-flash", "antigravity", {}) is True
    assert plugin.is_target_request("antigravity/gemini-3.8-flash", "antigravity", {}) is True
    assert plugin.is_target_request(None, "antigravity", {"model": "gemini-3.8-flash"}) is True

    # 2. google-antigravity is NOT accepted
    assert plugin.is_target_request("gemini-3.8-flash", "google-antigravity", {}) is False

    # 3. wrong providers unchanged
    assert plugin.is_target_request("gemini-3.8-flash", "google-cloud-code-assist", {}) is False
    assert plugin.is_target_request("gemini-3.8-flash", "openai", {}) is False
    assert plugin.is_target_request("gemini-3.8-flash", "anthropic", {}) is False
    assert plugin.is_target_request("gemini-3.8-flash", "openrouter", {}) is False

    # 4. other Gemini models unchanged
    assert plugin.is_target_request("gemini-3.1-pro", "antigravity", {}) is False
    assert plugin.is_target_request("gemini-3.5-flash", "antigravity", {}) is False
    assert plugin.is_target_request("gemini-2.5-flash", "antigravity", {}) is False

    # 5. Luna unchanged
    assert plugin.is_target_request("gpt-5.6-luna-900k", "openai-codex", {}) is False
    assert plugin.is_target_request("gpt-5.6-luna-900k", "antigravity", {}) is False

    # 6. Claude unchanged
    assert plugin.is_target_request("claude-3-7-sonnet", "anthropic", {}) is False
    assert plugin.is_target_request("claude-3-7-sonnet", "antigravity", {}) is False


def test_target_injection_single(guardrail_text):
    # 7. exactly-once privileged injection
    req = {
        "model": "gemini-3.8-flash",
        "messages": [
            {"role": "system", "content": "You are Hermes."},
            {"role": "user", "content": "Hello"},
        ],
    }
    res = plugin.on_llm_request(
        request=copy.deepcopy(req),
        model="gemini-3.8-flash",
        provider="antigravity",
    )
    assert res is not None
    out_req = res["request"]
    counts = count_r6b3_occurrences_by_role(out_req, guardrail_text)
    assert counts["privileged"] == 1
    assert counts["user"] == 0
    assert out_req["messages"][0]["content"].startswith("You are Hermes.\n\n")
    assert out_req["messages"][1] == {"role": "user", "content": "Hello"}


def test_target_injection_idempotent(guardrail_text):
    # 8. second invocation remains idempotent
    req = {
        "model": "gemini-3.8-flash",
        "messages": [
            {"role": "system", "content": "You are Hermes."},
            {"role": "user", "content": "Hello"},
        ],
    }
    res1 = plugin.on_llm_request(
        request=copy.deepcopy(req),
        model="gemini-3.8-flash",
        provider="antigravity",
    )
    assert res1 is not None
    treated_req = res1["request"]
    counts1 = count_r6b3_occurrences_by_role(treated_req, guardrail_text)
    assert counts1["privileged"] == 1

    # Second invocation on treated request
    res2 = plugin.on_llm_request(
        request=copy.deepcopy(treated_req),
        model="gemini-3.8-flash",
        provider="antigravity",
    )
    out_req2 = res2["request"] if res2 else treated_req
    counts2 = count_r6b3_occurrences_by_role(out_req2, guardrail_text)
    assert counts2["privileged"] == 1
    assert out_req2 == treated_req


def test_user_message_poisoning_does_not_suppress_injection(guardrail_text):
    # 9. user quoting full R6-B3 text cannot suppress privileged injection
    user_content_with_guardrail = f"Please check this guardrail text:\n\n{guardrail_text}\nIs it correct?"
    req = {
        "model": "gemini-3.8-flash",
        "messages": [
            {"role": "system", "content": "You are Hermes."},
            {"role": "user", "content": user_content_with_guardrail},
        ],
    }

    res1 = plugin.on_llm_request(
        request=copy.deepcopy(req),
        model="gemini-3.8-flash",
        provider="antigravity",
    )
    assert res1 is not None
    out_req1 = res1["request"]

    counts1 = count_r6b3_occurrences_by_role(out_req1, guardrail_text)
    assert counts1["privileged"] == 1
    assert counts1["user"] == 1
    assert out_req1["messages"][1]["content"] == user_content_with_guardrail

    # Second pass stays idempotent
    res2 = plugin.on_llm_request(
        request=copy.deepcopy(out_req1),
        model="gemini-3.8-flash",
        provider="antigravity",
    )
    out_req2 = res2["request"] if res2 else out_req1
    counts2 = count_r6b3_occurrences_by_role(out_req2, guardrail_text)
    assert counts2["privileged"] == 1
    assert counts2["user"] == 1
    assert out_req2 == out_req1


def test_structured_content_parts_and_cache_markers_preserved(guardrail_text):
    # 10. structured system/developer content preserved
    # 11. existing cache_control markers preserved
    req = {
        "model": "gemini-3.8-flash",
        "messages": [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": "Stable Prefix", "cache_control": {"type": "ephemeral", "ttl": "5m"}},
                    {"type": "text", "text": "Volatile suffix"},
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Turn 1", "cache_control": {"type": "ephemeral"}}
                ],
            },
            {
                "role": "assistant",
                "content": "Turn 1 response",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Turn 2", "cache_control": {"type": "ephemeral"}}
                ],
            },
        ],
        "tools": [
            {
                "type": "function",
                "function": {"name": "read_file"},
                "cache_control": {"type": "ephemeral"},
            }
        ],
    }

    res = plugin.on_llm_request(
        request=copy.deepcopy(req),
        model="gemini-3.8-flash",
        provider="antigravity",
    )
    assert res is not None
    out_req = res["request"]

    counts = count_r6b3_occurrences_by_role(out_req, guardrail_text)
    assert counts["privileged"] == 1
    assert counts["user"] == 0

    # User messages and tool cache controls preserved exactly
    assert out_req["messages"][1]["content"][0]["cache_control"] == {"type": "ephemeral"}
    assert out_req["messages"][3]["content"][0]["cache_control"] == {"type": "ephemeral"}
    assert out_req["tools"][0]["cache_control"] == {"type": "ephemeral"}

    # System message cache marker preserved on first part, guardrail appended
    sys_content = out_req["messages"][0]["content"]
    assert isinstance(sys_content, list)
    assert sys_content[0]["cache_control"] == {"type": "ephemeral", "ttl": "5m"}
    assert sys_content[0]["text"] == "Stable Prefix"
    assert sys_content[1]["text"] == "Volatile suffix"
    assert sys_content[-1]["type"] == "text"
    assert guardrail_text in sys_content[-1]["text"]


def test_unsupported_request_shape_fails_open():
    # 12. unsupported request shape fails open
    req1 = {"model": "gemini-3.8-flash", "prompt": "Raw prompt"}
    res1 = plugin.on_llm_request(
        request=copy.deepcopy(req1),
        model="gemini-3.8-flash",
        provider="antigravity",
    )
    if res1 is not None:
        assert res1["request"] == req1

    res2 = plugin.on_llm_request(
        request="invalid",
        model="gemini-3.8-flash",
        provider="antigravity",
    )
    assert res2 is None


def test_stored_prompt_non_mutation(guardrail_text):
    # 13. original request object / stored prompt input remains unchanged when middleware receives a copied request
    original_prompt = "Permanent core prompt in session"
    req = {
        "model": "gemini-3.8-flash",
        "messages": [
            {"role": "system", "content": original_prompt},
            {"role": "user", "content": "Query"},
        ],
    }
    req_copy = copy.deepcopy(req)
    res = plugin.on_llm_request(
        request=req_copy,
        model="gemini-3.8-flash",
        provider="antigravity",
    )
    assert res is not None
    assert original_prompt == "Permanent core prompt in session"
    assert req["messages"][0]["content"] == "Permanent core prompt in session"
    counts_orig = count_r6b3_occurrences_by_role(req, guardrail_text)
    counts_mod = count_r6b3_occurrences_by_role(res["request"], guardrail_text)
    assert counts_orig["privileged"] == 0
    assert counts_mod["privileged"] == 1
