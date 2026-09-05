"""Test for /resume listing accuracy and clean mobile formatting."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from types import SimpleNamespace
from gateway.config import Platform
from gateway.platforms.base import MessageEvent
from gateway.session import SessionSource, build_session_key
from hermes_state import SessionDB, AsyncSessionDB


def _make_event(text="/resume", platform=Platform.TELEGRAM, user_id="12345", chat_id="67890"):
    source = SessionSource(
        platform=platform,
        user_id=user_id,
        chat_id=chat_id,
        user_name="testuser",
    )
    return MessageEvent(text=text, source=source)


def _make_runner(session_db, current_session_id="current_active_sess"):
    from gateway.run import GatewayRunner
    runner = object.__new__(GatewayRunner)
    runner.adapters = {}
    runner.config = SimpleNamespace(platforms={})
    runner._voice_mode = {}
    runner._session_db = AsyncSessionDB(session_db)
    runner._running_agents = {}
    runner._is_user_authorized = lambda _source: True
    runner._resume_caller_is_admin = lambda _source: False

    mock_session_entry = MagicMock()
    mock_session_entry.session_id = current_session_id
    mock_store = MagicMock()
    mock_store.get_or_create_session.return_value = mock_session_entry
    mock_store.load_transcript.return_value = []
    mock_store.switch_session.return_value = mock_session_entry
    runner.session_store = mock_store

    mock_async_store = MagicMock()
    mock_async_store.get_or_create_session = AsyncMock(return_value=mock_session_entry)
    mock_async_store._store = mock_store
    runner._async_session_store = mock_async_store

    runner._gateway_session_origin_for_id = lambda _id: None
    runner._same_matrix_room = lambda _src, _orig: True
    runner._resume_row_visible = AsyncMock(return_value=True)
    return runner


@pytest.mark.asyncio
async def test_resume_formatting_and_10_past_titled(tmp_path):
    db = SessionDB(db_path=tmp_path / "state.db")
    event = _make_event(text="/resume")
    lane_key = build_session_key(event.source)

    # Create current active session
    db.create_session("current_active_sess", "telegram", session_key=lane_key, user_id="12345", chat_id="67890")
    db.set_session_title("current_active_sess", "Fix /resume session list")
    db.append_message("current_active_sess", role="user", content="Fix this /resume issue")

    # Create 12 past titled sessions and some untitled sessions interleaved
    for i in range(1, 13):
        sid = f"past_sess_{i:02d}"
        db.create_session(sid, "telegram", session_key=lane_key, user_id="12345", chat_id="67890")
        db.set_session_title(sid, f"Title {i:02d}")
        db.append_message(sid, role="user", content=f"Message {i:02d}")

    # Create 5 untitled sessions
    for i in range(1, 6):
        sid = f"untitled_{i:02d}"
        db.create_session(sid, "telegram", session_key=lane_key, user_id="12345", chat_id="67890")
        db.append_message(sid, role="user", content=f"Untitled msg {i:02d}")

    runner = _make_runner(db, current_session_id="current_active_sess")

    result = await runner._handle_resume_command(event)

    # 1. Total sessions in output: 1 active + 10 past = 11 items
    assert "1. (active) `current_active_sess` [TG]" in result
    assert "🏷️ **Fix /resume session list**" in result
    assert "11. " in result
    assert "12. " not in result

    # 2. Check 3-line format with 💬 and clean italic
    assert "\n   🏷️ " in result
    assert "\n   💬 *" in result

    db.close()
