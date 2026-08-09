"""P2/F6/F7: /status canonical-model display.

The provider may serve a different canonical model than the requested alias
(e.g. requested deepseek-v4-flash, served deepseek-v4-flash-20260423). /status must render the canonical
only when it is known, differs from the requested model, and is not stale
under a session override.
"""

import threading
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.platforms.base import MessageEvent
from gateway.session import SessionSource, build_session_key


def _make_source() -> SessionSource:
    # Synthetic identifiers only; never use owner/contact data in fixtures.
    return SessionSource(
        platform=Platform.TELEGRAM,
        user_id="synthetic-user-001",
        chat_id="synthetic-chat-001",
        user_name="synthetic-test-user",
        chat_type="dm",
    )


def _make_event(text: str) -> MessageEvent:
    return MessageEvent(
        text=text,
        source=_make_source(),
        message_id="synthetic-message-001",
    )


def _make_runner(**overrides):
    from gateway.run import GatewayRunner

    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig(
        platforms={
            Platform.TELEGRAM: PlatformConfig(
                enabled=True, token="synthetic-token-placeholder"
            )
        }
    )
    adapter = MagicMock()
    adapter.send = AsyncMock()
    runner.adapters = {Platform.TELEGRAM: adapter}
    runner._voice_mode = {}
    runner.hooks = SimpleNamespace(
        emit=AsyncMock(),
        emit_collect=AsyncMock(return_value=[]),
        loaded_hooks=False,
    )
    runner.session_store = MagicMock()
    runner.session_store.get_or_create_session.return_value = SimpleNamespace(
        session_key=build_session_key(_make_source()),
        session_id="synthetic-session-canonical",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        last_prompt_tokens=1000,
    )
    runner.session_store.load_transcript.return_value = []
    runner.session_store.has_any_sessions.return_value = True
    runner.session_store.append_to_transcript = MagicMock()
    runner.session_store.rewrite_transcript = MagicMock()
    runner.session_store.update_session = MagicMock()
    runner._running_agents = {}
    runner._pending_messages = {}
    runner._pending_approvals = {}
    runner._session_db = None
    runner._reasoning_config = None
    runner._provider_routing = {}
    runner._fallback_model = None
    runner._show_reasoning = False
    runner._is_user_authorized = lambda _source: True
    runner._set_session_env = lambda _context: None
    runner._should_send_voice_reply = lambda *_a, **_k: False
    runner._send_voice_reply = AsyncMock()
    runner._capture_gateway_honcho_if_configured = lambda *a, **k: None
    runner._emit_gateway_run_progress = AsyncMock()
    runner._agent_cache = {}
    runner._agent_cache_lock = threading.Lock()
    for k, v in overrides.items():
        setattr(runner, k, v)
    return runner


def _agent_with(model="deepseek-v4-flash", response_model="deepseek-v4-flash-20260423"):
    return SimpleNamespace(
        model=model,
        provider="deepseek",
        base_url="https://api.deepseek.com/v1",
        response_model=response_model,
        context_compressor=SimpleNamespace(
            last_prompt_tokens=1000, context_length=1_000_000
        ),
    )


@pytest.mark.asyncio
async def test_status_renders_requested_to_canonical_arrow():
    """P2: requested alias → canonical serving model is shown."""
    runner = _make_runner()
    key = build_session_key(_make_source())
    runner._agent_cache[key] = (_agent_with(), object())

    result = await runner._handle_status_command(_make_event("/status"))

    assert result is not None
    assert "deepseek-v4-flash" in result
    assert "deepseek-v4-flash-20260423" in result
    assert "→" in result


@pytest.mark.asyncio
async def test_status_plain_when_canonical_identical():
    """No arrow when requested == canonical (current format preserved)."""
    runner = _make_runner()
    key = build_session_key(_make_source())
    runner._agent_cache[key] = (
        _agent_with(model="deepseek-v4-flash", response_model="deepseek-v4-flash"),
        object(),
    )

    result = await runner._handle_status_command(_make_event("/status"))

    assert result is not None
    assert "→" not in result
    assert "deepseek-v4-flash" in result


@pytest.mark.asyncio
async def test_status_ignores_canonical_under_session_override():
    """F7: a session override (fresh switch) must not render the cached
    agent's stale canonical from the pre-switch route."""
    runner = _make_runner()
    key = build_session_key(_make_source())
    runner._agent_cache[key] = (
        _agent_with(model="deepseek-v4-flash", response_model="deepseek-v4-flash-20260423"),
        object(),
    )
    runner._session_model_overrides = {
        key: {
            "model": "gpt-5.4",
            "provider": "openai-api",
            "base_url": "https://api.openai.com/v1",
        }
    }

    result = await runner._handle_status_command(_make_event("/status"))

    assert result is not None
    assert "deepseek-v4-flash" not in result
    assert "gpt-5.4" in result
