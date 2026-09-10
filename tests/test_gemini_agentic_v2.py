import copy
import hashlib
import importlib.util
from pathlib import Path
import pytest
import sys
from typing import Any, Dict

# Paths
WORKTREE_DIR = Path(__file__).resolve().parent.parent
V2_PLUGIN_DIR = WORKTREE_DIR / "plugins" / "gemini-agentic-v2"
R6B3_PLUGIN_DIR = WORKTREE_DIR / "plugins" / "gemini-r6b3-guardrail"

# Load V2 module
spec_v2 = importlib.util.spec_from_file_location("gemini_agentic_v2", V2_PLUGIN_DIR / "__init__.py")
assert spec_v2 is not None and spec_v2.loader is not None
v2_plugin = importlib.util.module_from_spec(spec_v2)
sys.modules["gemini_agentic_v2"] = v2_plugin
spec_v2.loader.exec_module(v2_plugin)

# Load R6-B3 module
spec_r6 = importlib.util.spec_from_file_location("gemini_r6b3_guardrail", R6B3_PLUGIN_DIR / "__init__.py")
assert spec_r6 is not None and spec_r6.loader is not None
r6_plugin = importlib.util.module_from_spec(spec_r6)
sys.modules["gemini_r6b3_guardrail"] = r6_plugin
spec_r6.loader.exec_module(r6_plugin)


@pytest.fixture
def v2_protocol_text():
    text = v2_plugin.load_and_verify_protocol()
    assert text is not None
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == v2_plugin.EXPECTED_V2_PROTOCOL_SHA256
    return text


@pytest.fixture
def r6b3_guardrail_text():
    text = r6_plugin.load_and_verify_guardrail()
    assert text is not None
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == r6_plugin.EXPECTED_GUARDRAIL_SHA256
    return text


def test_1_exact_target_gets_v2(v2_protocol_text):
    req = {
        "model": "gemini-3.8-flash",
        "messages": [
            {"role": "system", "content": "You are Hermes."},
            {"role": "user", "content": "Investigate bug."},
        ],
    }
    res = v2_plugin.on_llm_request(
        request=copy.deepcopy(req),
        model="gemini-3.8-flash",
        provider="antigravity",
    )
    assert res is not None
    sys_content = res["request"]["messages"][0]["content"]
    assert "# Agentic Depth Protocol v2" in sys_content
    assert v2_plugin.DYNAMIC_BLOCK_START in sys_content


def test_2_wrong_provider_unchanged():
    for wrong_p in ["google-antigravity", "google-cloud-code-assist", "openai", "anthropic"]:
        req = {
            "model": "gemini-3.8-flash",
            "messages": [{"role": "system", "content": "System."}, {"role": "user", "content": "Task."}],
        }
        res = v2_plugin.on_llm_request(request=copy.deepcopy(req), model="gemini-3.8-flash", provider=wrong_p)
        assert res is None


def test_3_other_gemini_model_unchanged():
    req = {
        "model": "gemini-3.1-pro",
        "messages": [{"role": "system", "content": "System."}, {"role": "user", "content": "Task."}],
    }
    res = v2_plugin.on_llm_request(request=copy.deepcopy(req), model="gemini-3.1-pro", provider="antigravity")
    assert res is None


def test_4_luna_unchanged():
    req = {
        "model": "gpt-5.6-luna-900k",
        "messages": [{"role": "system", "content": "System."}, {"role": "user", "content": "Task."}],
    }
    res = v2_plugin.on_llm_request(request=copy.deepcopy(req), model="gpt-5.6-luna-900k", provider="openai-codex")
    assert res is None


def test_5_claude_unchanged():
    req = {
        "model": "claude-3-7-sonnet",
        "messages": [{"role": "system", "content": "System."}, {"role": "user", "content": "Task."}],
    }
    res = v2_plugin.on_llm_request(request=copy.deepcopy(req), model="claude-3-7-sonnet", provider="antigravity")
    assert res is None


def test_6_repeated_invocation_idempotent(v2_protocol_text):
    req = {
        "model": "gemini-3.8-flash",
        "messages": [
            {"role": "system", "content": "You are Hermes."},
            {"role": "user", "content": "Investigate bug in authentication."},
        ],
    }
    res1 = v2_plugin.on_llm_request(request=copy.deepcopy(req), model="gemini-3.8-flash", provider="antigravity")
    assert res1 is not None
    out1 = res1["request"]
    sys1 = out1["messages"][0]["content"]
    assert sys1.count("# Agentic Depth Protocol v2") == 1
    assert sys1.count(v2_plugin.DYNAMIC_BLOCK_START) == 1

    res2 = v2_plugin.on_llm_request(request=copy.deepcopy(out1), model="gemini-3.8-flash", provider="antigravity")
    out2 = res2["request"] if res2 else out1
    sys2 = out2["messages"][0]["content"]
    assert sys2.count("# Agentic Depth Protocol v2") == 1
    assert sys2.count(v2_plugin.DYNAMIC_BLOCK_START) == 1


def test_7_user_quoting_does_not_suppress(v2_protocol_text):
    quoted = f"Here is the protocol:\n\n{v2_protocol_text}\nConfirm."
    req = {
        "model": "gemini-3.8-flash",
        "messages": [
            {"role": "system", "content": "You are Hermes."},
            {"role": "user", "content": quoted},
        ],
    }
    res = v2_plugin.on_llm_request(request=copy.deepcopy(req), model="gemini-3.8-flash", provider="antigravity")
    assert res is not None
    out = res["request"]
    assert out["messages"][0]["content"].count("# Agentic Depth Protocol v2") == 1
    assert out["messages"][1]["content"] == quoted


def test_8_structured_system_content_preserved(v2_protocol_text):
    req = {
        "model": "gemini-3.8-flash",
        "messages": [
            {
                "role": "system",
                "content": [{"type": "text", "text": "Base instructions"}],
            },
            {"role": "user", "content": "Run analysis"},
        ],
    }
    res = v2_plugin.on_llm_request(request=copy.deepcopy(req), model="gemini-3.8-flash", provider="antigravity")
    assert res is not None
    sys_list = res["request"]["messages"][0]["content"]
    assert isinstance(sys_list, list)
    assert sys_list[0]["text"] == "Base instructions"


def test_9_cache_markers_preserved():
    req = {
        "model": "gemini-3.8-flash",
        "messages": [
            {
                "role": "system",
                "content": [{"type": "text", "text": "Base instructions", "cache_control": {"type": "ephemeral", "ttl": "5m"}}],
            },
            {"role": "user", "content": [{"type": "text", "text": "Run analysis", "cache_control": {"type": "ephemeral"}}]},
        ],
        "tools": [{"type": "function", "function": {"name": "read_file"}, "cache_control": {"type": "ephemeral"}}],
    }
    res = v2_plugin.on_llm_request(request=copy.deepcopy(req), model="gemini-3.8-flash", provider="antigravity")
    assert res is not None
    out = res["request"]
    assert out["messages"][0]["content"][0]["cache_control"] == {"type": "ephemeral", "ttl": "5m"}
    assert out["messages"][1]["content"][0]["cache_control"] == {"type": "ephemeral"}
    assert out["tools"][0]["cache_control"] == {"type": "ephemeral"}


def test_10_unsupported_shape_fail_open():
    req1 = {"model": "gemini-3.8-flash", "prompt": "Raw prompt"}
    res1 = v2_plugin.on_llm_request(request=copy.deepcopy(req1), model="gemini-3.8-flash", provider="antigravity")
    if res1 is not None:
        assert res1["request"] == req1

    res2 = v2_plugin.on_llm_request(request="invalid", model="gemini-3.8-flash", provider="antigravity")
    assert res2 is None


def test_11_r6b3_coexistence_no_duplication(v2_protocol_text, r6b3_guardrail_text):
    req = {
        "model": "gemini-3.8-flash",
        "messages": [
            {"role": "system", "content": "You are Hermes."},
            {"role": "user", "content": "Debug system restart failure."},
        ],
    }
    # Pass R6-B3
    r6_res = r6_plugin.on_llm_request(request=copy.deepcopy(req), model="gemini-3.8-flash", provider="antigravity")
    assert r6_res is not None
    # Pass V2
    v2_res = v2_plugin.on_llm_request(request=copy.deepcopy(r6_res["request"]), model="gemini-3.8-flash", provider="antigravity")
    assert v2_res is not None
    sys_content = v2_res["request"]["messages"][0]["content"]

    assert sys_content.count(r6b3_guardrail_text) == 1
    assert sys_content.count("# Agentic Depth Protocol v2") == 1
    assert sys_content.count(v2_plugin.DYNAMIC_BLOCK_START) == 1


def test_12_dynamic_state_bounded():
    # Construct history with 20 tool calls and 20 different files
    messages: list[dict[str, Any]] = [{"role": "user", "content": "Audit everything"}]
    for i in range(20):
        messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "read_file", "arguments": f'{{"path": "/home/dir/file_{i}.py"}}'}}],
        })
        messages.append({"role": "tool", "content": f"data {i}"})

    _, counts, paths = v2_plugin.analyze_request_history(messages)
    assert counts["reads"] == 20
    assert len(paths) <= 5  # strictly bounded to <= 5 paths

    block = v2_plugin.build_dynamic_state_block("DEEP", counts, paths)
    assert len(block) < 500  # bounded block size


def test_13_dynamic_state_does_not_leak_secrets_or_full_outputs():
    secret_key = "sk-live-1234567890abcdef1234567890abcdef"
    massive_output = "SECRET_DATA_LEAK " * 5000
    messages = [
        {"role": "user", "content": "Examine env"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "terminal", "arguments": '{"command": "cat .env"}'}}],
        },
        {"role": "tool", "content": f"{secret_key}\n{massive_output}"},
    ]
    mode_hint, counts, paths = v2_plugin.analyze_request_history(messages)
    block = v2_plugin.build_dynamic_state_block(mode_hint, counts, paths)
    assert secret_key not in block
    assert "SECRET_DATA_LEAK" not in block


def test_14_direct_classification_for_context_only():
    msg = [{"role": "user", "content": "What is the capital of Malaysia?"}]
    hint, _, _ = v2_plugin.analyze_request_history(msg)
    assert hint == "DIRECT"


def test_15_deep_classification_for_investigation():
    msg = [{"role": "user", "content": "Please diagnose why the gateway is failing to restart."}]
    hint, _, _ = v2_plugin.analyze_request_history(msg)
    assert hint == "DEEP"


def test_16_non_target_has_zero_v2_dynamic_state():
    req = {
        "model": "gpt-5.6-luna-900k",
        "messages": [
            {"role": "system", "content": "System prompt."},
            {"role": "user", "content": "Investigate logs."},
        ],
    }
    res = v2_plugin.on_llm_request(request=copy.deepcopy(req), model="gpt-5.6-luna-900k", provider="openai-codex")
    assert res is None


def test_17_stored_core_prompt_and_session_inputs_unchanged():
    orig_prompt = "Permanent core prompt in session"
    user_prompt = "Perform deep inspection"
    req = {
        "model": "gemini-3.8-flash",
        "messages": [
            {"role": "system", "content": orig_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    # Deepcopy mimics apply_llm_request_middleware
    res = v2_plugin.on_llm_request(request=copy.deepcopy(req), model="gemini-3.8-flash", provider="antigravity")
    assert res is not None
    # Original objects must be completely untouched
    assert req["messages"][0]["content"] == orig_prompt
    assert req["messages"][1]["content"] == user_prompt
    assert v2_plugin.DYNAMIC_BLOCK_START not in req["messages"][0]["content"]
