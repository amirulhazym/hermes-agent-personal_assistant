"""
LightClaw outbound message sender — builds and sends messages to the server.
Mirrors: src/outbound.ts

Streaming mode: GatewayStreamConsumer is active (SUPPORTS_MESSAGE_EDITING=True).
Gateway calls send() with the first chunk, then edit_message() with accumulated
full text for subsequent chunks, and finally edit_message(finalize=True).

Round lifecycle:
  The round msgId spans the WHOLE agent turn (one user input → one round),
  so the front-end can aggregate streamed text, tool progress, post-stream
  follow-up text and attachment links into a single bubble.

  Closing the round (typing_stop + state cleanup) is the sole responsibility
  of stop_typing(), which the framework guarantees to invoke at turn end
  (see STREAMING_DESIGN.md §3.1 — at least four call sites).

  - Streaming:  inbound typing_start
                → send(first_chunk)
                → edit_message() × N
                → edit_message(finalize=True)        # only flushes residual delta
                → [optional tool_start / follow-up stream_chunk / attachment link]*
                → stop_typing() → typing_stop        # framework-driven close
  - Commands:   inbound typing_start
                → [tool_start]*
                → send(response)
                → stop_typing() → typing_stop        # framework-driven close
  - Standalone: typing_start → stream_chunk → typing_stop  (self-managed)
"""

import base64
import json
import logging
import os
import re
import time
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

from gateway.platforms.base import SendResult

from .config import (
    CHANNEL_KEY,
    DEFAULT_AGENT_ID,
    EVENT_MESSAGE_PRIVATE,
    KIND_USAGE,
    LOCALFILE_SCHEME,
    MEDIA_MAX_BYTES,
    generate_msg_id,
    guess_mime,
)
from .media import format_file_size

logger = logging.getLogger(__name__)

# Tool progress message pattern: "{emoji} {tool_name}..." or "{emoji} {tool_name}: ..."
_TOOL_PROGRESS_RE = re.compile(
    r'^.{1,2}\s+\w[\w_]*(?:\.\w+)*(?:\.\.\.|:|\()', re.UNICODE
)

# Extract the file path from a write_file tool_start progress message.
# This is our MODEL-INDEPENDENT source of the artifact path: the gateway emits
# the tool call as progress text *before* the model writes its final reply, so
# we capture the path here and deliver it ourselves if the (often weak) model
# never echoes it as a MEDIA: tag or bare path that the framework can detect.
# Handles two gateway formats:
#   compact mode:  '✏️ write_file: "/abs/path/to/file"'
#   verbose mode:  "✏️ write_file([...])\n{\"path\": \"/abs/path\"}"
_WRITE_FILE_PATH_RE = re.compile(
    r'\bwrite_file\b.*?["\'/](/[^"\'<>\s,;}{]+)',
    re.DOTALL,
)
_JSON_PATH_RE = re.compile(r'"path"\s*:\s*"(/[^"]+)"')

# Cursor glyphs used by GatewayStreamConsumer to indicate "still streaming".
# They are visual artifacts and MUST be stripped before any frame leaves the
# adapter, regardless of which send path the content takes.
# Order matters: longer (cursor-with-leading-space) variants first so the
# trailing-space form is removed cleanly.
_STREAM_CURSORS: tuple[str, ...] = (" \u2589", " \u258a", "\u2589", "\u258a")

# 匹配流式模型输出中的 MEDIA: 协议行。
# 框架要求格式：单独一行 "MEDIA:<绝对路径>"。
# 模型有时会将其作为普通文本输出——发送给客户端前必须去除，
# 避免原始路径出现在聊天界面中。
# 实际文件投递由框架的 _deliver_media_from_response / _deliver_pending_files 负责，
# 此处只需将原始标签从视图中隐藏。
_MEDIA_TAG_RE = re.compile(
    r'(?:^|\n)([ \t]*MEDIA:(?:[A-Za-z]:[/\\]|/|~/)\S+)([ \t]*)(?=\n|$)',
    re.MULTILINE,
)


def _strip_stream_cursor(text: str) -> str:
    """Remove a trailing streaming-cursor glyph if present.

    Idempotent and safe to call multiple times.  Returns *text* unchanged
    when no cursor is found.
    """
    if not text:
        return text
    for cursor in _STREAM_CURSORS:
        if text.endswith(cursor):
            return text[: -len(cursor)]
    return text


def _strip_media_tags(text: str) -> str:
    """Remove MEDIA:<path> lines from streamed model output before delivery.

    The framework uses ``MEDIA:<absolute-path>`` as an internal protocol to
    signal that a local file should be attached.  The gateway's post-stream
    handlers (_deliver_media_from_response / _deliver_pending_files) consume
    these tags and convert them to proper attachment links.  However, when the
    model outputs ``MEDIA:/path/to/file`` during streaming, the raw text is
    forwarded to the client verbatim before any post-stream processing runs.

    This function erases those lines so the raw path never appears in the
    chat bubble.  Newlines surrounding the tag are preserved to avoid
    disrupting paragraph layout.
    """
    if "MEDIA:" not in text:
        return text
    # 将每个 MEDIA: 行替换为空字符串。正则已通过换行符锚定行边界，只需丢弃标签内容，保持原有换行结构不变。
    return _MEDIA_TAG_RE.sub(lambda m: m.group(0).replace(m.group(1) + m.group(2), ""), text)


class OutboundMixin:
    """
    Mixin providing the full public send API (streaming mode).

    Requires (set by LightClawAdapter):
        self._bot_client_id: str
        self._reliable: ReliableEmitter
        self._round_ids: dict[str, str]
        self._round_has_content: dict[str, bool]
        self._edit_snapshot: dict[str, str]
        self._incoming_agent_ids: dict[str, str]
        self._round_reply_to: dict[str, str]
        self._round_usage_emitted: dict[str, str]
        self._usage_tracker: SessionUsageTracker | None
    """

    # ------------------------------------------------------------------
    # Low-level emit helpers
    # ------------------------------------------------------------------

    def _fire_and_forget(self, event: str, data: dict) -> None:
        """Send frame via WebSocket — no ACK, no retry, no blocking.

        Delegates to ``ReliableEmitter.emit_fire_and_forget`` which injects
        ``idempotencyKey`` and calls the raw socket emit synchronously.
        """
        if not self._reliable:
            return
        msg_id = data.get("msgId")
        kind = data.get("kind", "?")
        to = data.get("to", "?")
        content = data.get("content", "")
        content_preview = content[:40] if content else ""
        logger.info("[lightclaw] fire_and_forget: kind=%s to=%s msgId=%s content='%s'", kind, to, msg_id, content_preview)
        self._reliable.emit_fire_and_forget(event, data)

    async def _emit_reliable(self, event: str, data: dict) -> bool:
        """Send via ReliableEmitter with ACK + auto-retry."""
        if not self._reliable:
            return False
        msg_id = data.get("msgId")
        kind = data.get("kind", "?")
        to = data.get("to", "?")
        logger.info("[lightclaw] emit_reliable: event=%s kind=%s to=%s msgId=%s", event, kind, to, msg_id)
        return await self._reliable.emit_with_ack(event, data, msg_id)

    # ------------------------------------------------------------------
    # Message builder
    # ------------------------------------------------------------------

    def _build_message(
        self,
        to: str,
        content: str,
        kind: str = "text",
        reply_to: Optional[str] = None,
        files: Optional[list] = None,
        msg_id: Optional[str] = None,
        agent_id: str = DEFAULT_AGENT_ID,
        extra: Optional[dict] = None,
        **passthrough,
    ) -> dict:
        """Assemble a message:private frame payload.

        ``extra`` is carried verbatim under the top-level ``extra`` key
        (used by file:download signalling — see PROTOCOL.md).  Any other
        keyword arguments are merged into the top-level message dict for
        fields like ``toolName`` / ``toolPhase`` / ``idempotencyKey``.
        """
        msg: dict = {
            "msgId":     msg_id or generate_msg_id(),
            "from":      self._bot_client_id,
            "to":        to,
            "content":   content,
            "timestamp": int(time.time() * 1000),
            "kind":      kind,
            "agentId":   agent_id,
        }
        if reply_to:
            msg["replyToMsgId"] = reply_to
        if files:
            msg["files"] = files
        if extra is not None:
            msg["extra"] = extra
        if passthrough:
            msg.update(passthrough)
        return msg

    def _get_or_create_round_id(self, chat_id: str) -> str:
        if chat_id not in self._round_ids:
            self._round_ids[chat_id] = generate_msg_id()
        return self._round_ids[chat_id]

    def _clear_round_id(self, chat_id: str) -> None:
        self._round_ids.pop(chat_id, None)
        self._round_has_content.pop(chat_id, None)

    # ------------------------------------------------------------------
    # Per-turn usage sidecar persistence
    # ------------------------------------------------------------------
    #
    # OpenClaw stores per-turn ``usage`` directly on assistant messages
    # in the transcript jsonl, so its history reader picks it up "for
    # free".  Hermes's framework does NOT write usage into the transcript
    # — the sessions table in ``state.db`` only tracks session-cumulative
    # totals.  We can't change framework behaviour, so we persist a
    # *parallel* ``<session_id>.usage.jsonl`` next to each session's
    # transcript and let ``history.py`` re-attach the entries to the
    # matching assistant messages on read.
    #
    # File format (one JSON object per line, append-only):
    #   {
    #     "roundMsgId": "hermes_<ms>_<hex>",
    #     "timestamp":  1780304665270,        # ms-since-epoch, end-of-turn
    #     "usage":      { ...UnifiedUsage }   # camelCase, openclaw shape
    #   }
    #
    # This file lives alongside ``<session_id>.jsonl`` so it follows
    # session deletion / migration automatically.  Errors here MUST NOT
    # break the outbound path — usage persistence is best-effort.

    def _resolve_session_id_for_chat(
        self, chat_id: str, agent_id: str,
    ) -> Optional[str]:
        """Look up the Hermes ``session_id`` for *(chat_id, agent_id)*.

        Mirrors the session_key shape used by inbound (and history's
        history-request handler).  Returns ``None`` when the entry is
        missing — typically the very first turn before the framework
        has flushed sessions.json.
        """
        sessions_dir: Optional[str] = getattr(self, "_sessions_dir", None)

        # session_key format must match inbound._handle_incoming_message.
        if agent_id and agent_id != DEFAULT_AGENT_ID:
            session_key = f"agent:main:{CHANNEL_KEY}:dm:{chat_id}:{agent_id}"
        else:
            session_key = f"agent:main:{CHANNEL_KEY}:dm:{chat_id}"

        try:
            from .history import load_session_store
        except ImportError:
            return None

        store = load_session_store(sessions_dir)
        entry = store.get(session_key)
        if entry is None:
            lower = session_key.strip().lower()
            for k, v in store.items():
                if k.lower() == lower:
                    entry = v
                    break
        if not entry:
            return None
        # Support both snake_case (lighthouse-hermes) and camelCase (openclaw)
        return entry.get("session_id") or entry.get("sessionId") or None

    def _resolve_usage_log_path(
        self, chat_id: str, agent_id: str,
    ) -> Optional[str]:
        """Return absolute path of the usage sidecar jsonl for this chat.

        Returns ``None`` if we can't yet locate the session (best-effort).
        """
        sessions_dir: Optional[str] = getattr(self, "_sessions_dir", None)
        if not sessions_dir:
            return None
        session_id = self._resolve_session_id_for_chat(chat_id, agent_id)
        if not session_id:
            return None
        return os.path.join(sessions_dir, f"{session_id}.usage.jsonl")

    def _persist_turn_usage(
        self,
        chat_id: str,
        agent_id: str,
        round_msg_id: str,
        usage: Optional[Dict[str, Any]],
    ) -> None:
        """Append one usage line to ``<session_id>.usage.jsonl``.

        ``usage`` may be ``None`` — in that case we still write a line
        with ``"usage": null`` to preserve **ordinal alignment** with
        transcript turns: history-side join pairs the i-th sidecar entry
        with the i-th turn-end assistant, so a missing line would shift
        every subsequent turn by one and never self-heal.

        Best-effort: any error is logged at WARNING level and swallowed.
        The realtime usage frame has already been emitted (or skipped)
        by the caller, so a write failure only affects historical
        re-render — never the live UI.
        """
        try:
            log_path = self._resolve_usage_log_path(chat_id, agent_id)
            if not log_path:
                logger.info(
                    "[lightclaw] usage persist skipped (session not yet "
                    "indexed): to=%s msgId=%s",
                    chat_id, round_msg_id,
                )
                return
            entry: Dict[str, Any] = {
                "roundMsgId": round_msg_id,
                "timestamp":  int(time.time() * 1000),
                "usage":      usage,  # may be None — placeholder for alignment
            }
            line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            if usage is None:
                logger.info(
                    "[lightclaw] usage placeholder persisted (no delta): "
                    "path=%s msgId=%s",
                    log_path, round_msg_id,
                )
            else:
                logger.info(
                    "[lightclaw] usage persisted: path=%s msgId=%s "
                    "input=%s output=%s",
                    log_path, round_msg_id,
                    usage.get("inputTokens"), usage.get("outputTokens"),
                )
        except OSError as exc:
            logger.warning(
                "[lightclaw] usage persist failed: chat=%s msgId=%s err=%s",
                chat_id, round_msg_id, exc,
            )

    # ------------------------------------------------------------------
    # Public send API
    # ------------------------------------------------------------------

    async def send(
        self,
        chat_id: str,
        content: str,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> SendResult:
        """Send a message to the user.

        Streaming mode behavior:
        - Round open (inbound already sent typing_start):
          - Tool progress → send as tool_start, keep round open
          - Stream first chunk → send as stream_chunk, record snapshot for
            subsequent edit_message() delta computation, keep round open
        - No round (standalone message, e.g. cron delivery):
          - typing_start → stream_chunk → typing_stop (full lifecycle)
        """
        if not self._reliable:
            return SendResult(success=False, error="Not connected", retryable=True)

        # Strip GatewayStreamConsumer cursor glyphs at the entry point so
        # every downstream branch (round-open / no-round / standalone /
        # tool_start / attachment link) uses sanitized content.
        content = _strip_stream_cursor(content)

        agent_id = self._incoming_agent_ids.get(chat_id) or DEFAULT_AGENT_ID

        # ── Round already open (inbound sent typing_start) ──
        round_msg_id = self._round_ids.get(chat_id)
        if round_msg_id:
            is_tool_progress = bool(
                content and len(content) < 500 and _TOOL_PROGRESS_RE.match(content)
            )
            msg_kind = "tool_start" if is_tool_progress else "stream_chunk"

            # Separate consecutive stream_chunks with \n\n so front-end
            # concatenation produces the same visual breaks as the history
            # view (where each assistant/tool message is a distinct object).
            actual_content = content
            if msg_kind == "stream_chunk":
                if self._round_has_content.get(chat_id):
                    actual_content = "\n\n" + content
                self._round_has_content[chat_id] = True

            logger.info(
                "[lightclaw] send (%s, round open): to=%s msgId=%s content=%d chars",
                msg_kind, chat_id, round_msg_id, len(content),
            )
            self._fire_and_forget(
                EVENT_MESSAGE_PRIVATE,
                self._build_message(
                    chat_id, actual_content, kind=msg_kind,
                    msg_id=round_msg_id, agent_id=agent_id,
                ),
            )

            # Track write_file tool_start paths for the stop_typing() fallback.
            if is_tool_progress:
                self._track_write_file_path(chat_id, content)

            # 记录去除光标和 MEDIA 标签后的快照，供 edit_message() 计算增量。
            # 此处也必须去除 MEDIA 标签——edit_message() 在比较前会先 strip，
            # 若 send() 保存的是含 MEDIA 标签的原始内容，两侧快照不一致，
            # 会触发 delta fallback，将整段可见文本作为增量重复下发。
            if msg_kind == "stream_chunk":
                self._edit_snapshot[chat_id] = _strip_media_tags(content)

            # Never close round here — typing_stop is sent by stop_typing()
            # which is called by the framework when the agent finishes.
            return SendResult(success=True, message_id=round_msg_id)

        # ── No active round, but a previous round is still "claimable" ──
        # The framework may route follow-up output (e.g. attachment links via
        # send_document/send_image) AFTER stop_typing has closed the round.
        # As long as no new inbound has arrived, those frames belong to the
        # same conversation turn — reuse the closed round's msgId so the
        # client aggregates everything into a single bubble.  The reservation
        # lives until inbound clears it on the next turn.
        last_round_id = self._last_round_id.get(chat_id)
        if last_round_id:
            is_tool_progress = bool(
                content and len(content) < 500 and _TOOL_PROGRESS_RE.match(content)
            )
            msg_kind = "tool_start" if is_tool_progress else "stream_chunk"
            # Always prepend "\n\n" for stream_chunks — the previous round
            # already has visible content, so a separator keeps the visual
            # break consistent with round-open follow-ups.
            actual_content = (
                content if msg_kind == "tool_start" else "\n\n" + content
            )
            logger.info(
                "[lightclaw] send (%s, reuse last round): to=%s msgId=%s content=%d chars",
                msg_kind, chat_id, last_round_id, len(content),
            )
            self._fire_and_forget(
                EVENT_MESSAGE_PRIVATE,
                self._build_message(
                    chat_id, actual_content, kind=msg_kind,
                    msg_id=last_round_id, agent_id=agent_id,
                ),
            )
            # Keep the reservation alive — more follow-ups may still arrive
            # before the next inbound (e.g. caption + attachment link).
            return SendResult(success=True, message_id=last_round_id)

        # ── No round open (standalone message) ──
        round_msg_id = self._get_or_create_round_id(chat_id)

        is_tool_progress = bool(
            content and len(content) < 500 and _TOOL_PROGRESS_RE.match(content)
        )

        if is_tool_progress:
            # Tool progress without round: fire-and-forget, no typing lifecycle
            logger.info(
                "[lightclaw] send (tool_start, no round): to=%s msgId=%s content=%d chars",
                chat_id, round_msg_id, len(content),
            )
            self._fire_and_forget(
                EVENT_MESSAGE_PRIVATE,
                self._build_message(
                    chat_id, content, kind="tool_start",
                    msg_id=round_msg_id, agent_id=agent_id,
                ),
            )
            self._clear_round_id(chat_id)
            return SendResult(success=True, message_id=round_msg_id)

        # Standalone message: full lifecycle
        logger.info(
            "[lightclaw] send (standalone): to=%s msgId=%s content=%d chars",
            chat_id, round_msg_id, len(content),
        )
        self._fire_and_forget(
            EVENT_MESSAGE_PRIVATE,
            self._build_message(chat_id, "", kind="typing_start",
                                msg_id=round_msg_id, agent_id=agent_id),
        )
        self._fire_and_forget(
            EVENT_MESSAGE_PRIVATE,
            self._build_message(
                chat_id, content, kind="stream_chunk",
                msg_id=round_msg_id, agent_id=agent_id,
            ),
        )
        self._fire_and_forget(
            EVENT_MESSAGE_PRIVATE,
            self._build_message(chat_id, "", kind="typing_stop",
                                msg_id=round_msg_id, agent_id=agent_id),
        )
        self._clear_round_id(chat_id)
        return SendResult(success=True, message_id=round_msg_id)

    async def send_typing(
        self,
        chat_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Send typing indicator — no-op.

        Inbound already sends typing_start when a message arrives.
        LightClaw's typing_start persists until typing_stop — no refresh needed.
        """
        pass

    async def stop_typing(self, chat_id: str, **kwargs: Any) -> None:
        """Stop typing indicator — sends typing_stop and closes the round.

        Called by the framework (gateway/run.py and base adapter) when:
        1. Agent finishes processing (success or error)
        2. Session processing completes in _process_message_background

        This is where the round gets properly closed with typing_stop.

        We also remember the closed round msgId in ``_last_round_id`` so
        that any output the framework routes AFTER this point (e.g.
        attachment links emitted via ``send_document`` / ``send_image``)
        can reuse the same msgId.  The reservation lives until the next
        inbound message clears it.
        """
        round_msg_id = self._round_ids.get(chat_id)
        if not round_msg_id:
            return
        agent_id = self._incoming_agent_ids.get(chat_id) or DEFAULT_AGENT_ID

        # Fallback: deliver any write_file outputs not covered by model MEDIA:
        # tags / framework path-detection.  Must run BEFORE typing_stop so
        # attachment links land in the same bubble.
        await self._deliver_pending_files(chat_id)

        # Emit one `kind='usage'` frame before typing_stop (same order as
        # openclaw). stop_typing fires multiple times per turn, so we
        # de-duplicate on round_msg_id: only the first emits usage.
        if (
            self._usage_tracker is not None
            and self._round_usage_emitted.get(chat_id) != round_msg_id
        ):
            usage, usage_reason = self._usage_tracker.classify_turn(chat_id)
            if usage is not None:
                logger.info(
                    "[lightclaw] emit usage: to=%s msgId=%s "
                    "input=%s output=%s total=%s",
                    chat_id, round_msg_id,
                    usage.get("inputTokens"),
                    usage.get("outputTokens"),
                    usage.get("totalTokens"),
                )
                self._fire_and_forget(
                    EVENT_MESSAGE_PRIVATE,
                    self._build_message(
                        chat_id, "", kind=KIND_USAGE,
                        msg_id=round_msg_id, agent_id=agent_id,
                        reply_to=self._round_reply_to.get(chat_id),
                        extra={"chatId": "", "usage": usage},
                    ),
                )
                # Real LLM turn → exactly one sidecar entry, aligned 1:1
                # with this turn's transcript turn-end assistant.
                self._persist_turn_usage(
                    chat_id=chat_id,
                    agent_id=agent_id,
                    round_msg_id=round_msg_id,
                    usage=usage,
                )
            elif usage_reason == "unknown":
                # We could NOT measure this turn — the turn-start baseline was
                # lost (mid-turn process restart) or the ``state.db`` row was
                # unreadable.  This is NOT proof the turn was free, so write a
                # placeholder to hold its slot and keep later turns aligned;
                # ``_attach_usage_to_messages`` skips the null payload, so no
                # bogus "0 tokens" is rendered.
                logger.info(
                    "[lightclaw] usage placeholder (unmeasurable turn): "
                    "to=%s msgId=%s",
                    chat_id, round_msg_id,
                )
                self._persist_turn_usage(
                    chat_id=chat_id,
                    agent_id=agent_id,
                    round_msg_id=round_msg_id,
                    usage=None,
                )
            else:
                # usage_reason == "no_llm": baseline present, DB read OK, but
                # the cumulative counters did not move → no LLM call ran.  This
                # is a framework *command* echo (e.g. /new, /approve, /always
                # confirmation), NOT a transcript conversation turn.  Write NO
                # sidecar entry: a line here is a phantom that breaks the
                # "i-th entry ↔ i-th turn-end assistant" join and silently
                # drops a neighbouring real turn's usage when history reloads.
                logger.info(
                    "[lightclaw] usage skipped (no LLM turn, no sidecar "
                    "entry): to=%s msgId=%s",
                    chat_id, round_msg_id,
                )
            # Mark emitted (even if no frame was sent) to skip later
            # stop_typing calls for this round.
            self._round_usage_emitted[chat_id] = round_msg_id

        logger.info("[lightclaw] stop_typing: to=%s msgId=%s", chat_id, round_msg_id)
        self._fire_and_forget(
            EVENT_MESSAGE_PRIVATE,
            self._build_message(
                chat_id, "", kind="typing_stop",
                msg_id=round_msg_id, agent_id=agent_id,
            ),
        )
        # Reserve the msgId for any post-stop_typing follow-up output
        # (typically: attachment markdown links).  Cleared by inbound on
        # the next turn.
        self._last_round_id[chat_id] = round_msg_id
        self._edit_snapshot.pop(chat_id, None)
        # 每轮结束时重置去重表，避免下一轮同名文件被误判为已投递而漏发。
        self._delivered_paths.pop(chat_id, None)
        self._clear_round_id(chat_id)

    async def edit_message(
        self,
        chat_id: str,
        message_id: str,
        content: str,
        *,
        finalize: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> SendResult:
        """Edit message — streaming delta computation and delivery.

        Called by GatewayStreamConsumer with accumulated full text (possibly
        with a cursor suffix like " \u2589").  We strip the cursor, compute the
        delta against the previous snapshot, and emit a stream_chunk frame.

        ``finalize=True`` only marks the end of *one streaming segment*, NOT
        the end of the whole agent turn.  After a streamed answer the agent
        may still emit tool progress, follow-up text, attachment links, etc.,
        and they should all reuse the same round msgId so the front-end can
        aggregate them into a single bubble.

        Therefore round closure (typing_stop + ``_clear_round_id``) is
        delegated entirely to ``stop_typing()``, which the framework
        guarantees to invoke at the end of the turn (see STREAMING_DESIGN.md
        §3.1 — at least four guaranteed call sites).  Here we only flush the
        residual delta and keep the snapshot in sync so any subsequent
        ``edit_message`` calls within the same round still compute correct
        deltas.

        Tool progress edits (message_id != round_msg_id) are ignored.
        """
        # 1. Strip cursor suffix
        content = _strip_stream_cursor(content)

        # 1b. 去除 MEDIA: 协议行——模型可能在流式输出时将其作为普通文本输出；这些是内部投递标记，不应展示给用户。
        #     文件投递由_deliver_media_from_response / _deliver_pending_files 单独处理。
        content = _strip_media_tags(content)

        # 2. Only process edits matching the current round (filter tool progress edits)
        round_msg_id = self._round_ids.get(chat_id)
        if not round_msg_id or round_msg_id != message_id:
            return SendResult(success=True, message_id=message_id)

        # 3. Compute delta
        previous = self._edit_snapshot.get(chat_id, "")
        if content.startswith(previous):
            delta = content[len(previous):]
        else:
            # Full-text fallback (content was truncated/reordered — rare)
            delta = content
            logger.warning(
                "[lightclaw] edit_message delta fallback: to=%s msgId=%s "
                "previous=%d chars, content=%d chars",
                chat_id, round_msg_id, len(previous), len(content),
            )

        # 4. Deliver residual delta (if any) and keep snapshot in sync.
        agent_id = self._incoming_agent_ids.get(chat_id) or DEFAULT_AGENT_ID
        if delta:
            self._fire_and_forget(
                EVENT_MESSAGE_PRIVATE,
                self._build_message(
                    chat_id, delta, kind="stream_chunk",
                    msg_id=round_msg_id, agent_id=agent_id,
                ),
            )
            self._edit_snapshot[chat_id] = content

        if finalize:
            logger.info(
                "[lightclaw] edit_message finalize (round kept open for "
                "post-stream output): to=%s msgId=%s delta=%d chars",
                chat_id, round_msg_id, len(delta),
            )
        else:
            logger.info(
                "[lightclaw] edit_message: to=%s msgId=%s delta=%d chars, content_tail='%s'",
                chat_id, round_msg_id, len(delta), content[-40:] if content else "",
            )

        return SendResult(success=True, message_id=message_id)

    # ------------------------------------------------------------------
    # Media send
    # ------------------------------------------------------------------
    #
    # Design: the channel is STRICTLY PASSIVE about outbound binary data.
    # When the framework (or the AI, via extract_local_files) asks us to
    # deliver a local file, we:
    #
    #   1. Validate the path (exists, regular file, ≤ MEDIA_MAX_BYTES).
    #   2. Emit a ``[name](localfile://<abs>)`` Markdown link through the
    #      normal text pipeline (``self.send``).  No base64 over WS, no
    #      upload to /drive/save.
    #   3. When the user clicks the link, the front-end issues a
    #      ``file:download`` ``download_req`` signal; only then does the
    #      :class:`DownloadHandlerMixin` upload the file on-demand and
    #      reply with a public URL.
    #
    # This matches the constraint "AI must never upload proactively".
    # The only outbound side channel that ever pushes files is:
    #   * /drive/save during inbound warm-upload (content-review hook);
    #   * /drive/save inside _handle_file_download_req (user-initiated).
    # ------------------------------------------------------------------

    async def send_image(
        self,
        chat_id: str,
        image_url: str,
        caption: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        """Send an image reference without proactive upload.

        Three input shapes are handled in-order:
          * ``http(s)://...``    → embed as Markdown image tag (no IO)
          * ``file://...``       → strip scheme, treat as local path
          * absolute local path  → delegate to :meth:`_send_attachment`
                                   which emits a ``localfile://`` link
        """
        if not image_url:
            return SendResult(success=False, error="image_url is required")

        # Already a remote URL → just embed as Markdown, no upload.
        if image_url.startswith(("http://", "https://")):
            text = (caption or "").rstrip()
            md = f"![image]({image_url})"
            payload = f"{text}\n\n{md}".strip() if text else md
            return await self.send(chat_id, payload, reply_to=reply_to, metadata=metadata)

        # file:// → strip the scheme and fall through to the local path branch.
        if image_url.startswith("file://"):
            image_url = image_url[len("file://"):]

        resolved = self._resolve_attachment_path(image_url)
        if resolved:
            return await self._send_attachment(
                chat_id, resolved, caption=caption,
                reply_to=reply_to, metadata=metadata,
            )

        return SendResult(success=False, error=f"Image not found: {image_url}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _file_to_attachment(self, file_path: str) -> Optional[dict]:
        """Read *file_path* and wrap it as a base64 ``FileAttachment`` dict.

        Currently unused — we deliver files via ``localfile://`` Markdown
        links instead of base64 WS payloads.  Kept for potential future
        use (e.g. a small-file fast-path) and for API compatibility with
        the TS ``sendFiles`` emitter.
        """
        if not file_path or not os.path.isfile(file_path):
            return None
        file_name = os.path.basename(file_path)
        mime = guess_mime(file_name)
        with open(file_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return {"name": file_name, "mimeType": mime, "bytes": f"data:{mime};base64,{data}"}

    async def _send_attachment(
        self,
        chat_id: str,
        file_path: str,
        caption: Optional[str] = None,
        file_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        """Deliver a local file by emitting a ``localfile://`` Markdown link.

        Never uploads.  Never embeds base64 binary.  The caller usually
        provides a local path; we normalize that exact path deterministically
        (``file://`` decode, ``~`` / env expansion, relative-path anchoring)
        without probing sibling directories, then emit an inline Markdown link
        through the standard text send path.
        """
        logger.info(
            "[lightclaw] _send_attachment invoked: chat=%s file=%r caption=%r",
            chat_id, file_path, (caption or "")[:60],
        )

        # Resolve the exact path deterministically. We normalize only the
        # caller-provided path string and never guess by basename.
        resolved_path = self._resolve_attachment_path(file_path)
        if not resolved_path:
            # The model may have printed a fabricated path (wrong dir / mangled
            # extension) that diverges from what it actually wrote.  Recover the
            # real path from this turn's tracked write_file calls before giving
            # up — those are model-independent ground truth.
            corrected = self._correct_attachment_path(chat_id, file_path)
            if corrected:
                logger.info(
                    "[lightclaw] attachment path corrected via tracked "
                    "write_file: %r → %r",
                    file_path, corrected,
                )
                resolved_path = corrected
        if not resolved_path:
            logger.warning(
                "[lightclaw] attachment file not found: original=%r "
                "tried=%s — notifying user instead of silent drop",
                file_path, self._attachment_candidates(file_path),
            )
            # Surface the failure to the user so they don't see a
            # successful "saved!" message with no attachment behind it.
            display = os.path.basename(file_path) if file_path else "(unknown)"
            return await self.send(
                chat_id,
                f"⚠️ 文件已生成但读取失败：`{display}`（路径 `{file_path}` 不可访问）",
                reply_to=reply_to, metadata=metadata,
            )
        if resolved_path != file_path:
            logger.info(
                "[lightclaw] attachment path resolved: %r → %r",
                file_path, resolved_path,
            )
        file_path = resolved_path

        try:
            size = os.path.getsize(file_path)
        except OSError as exc:
            logger.warning("[lightclaw] attachment stat failed: %r (%s)", file_path, exc)
            return SendResult(success=False, error=f"Stat failed: {exc}")
        if size > MEDIA_MAX_BYTES:
            # Still advertise the file — on-demand download will also
            # refuse it server-side if necessary — but log so we notice.
            logger.warning(
                "[lightclaw] file %s exceeds %d bytes (got %d); "
                "advertising link anyway, download may be rejected",
                file_path, MEDIA_MAX_BYTES, size,
            )

        abs_path = os.path.abspath(file_path)
        display_name = file_name or os.path.basename(abs_path)

        # 去重：若本轮已通过任意路径（_deliver_pending_files、send_document 或直接调用）
        # 投递过该文件，则直接跳过。stop_typing() 和框架的 _deliver_media_from_response()
        # 可能独立发现同一文件并都走到此处；在发送前检查（而非发送后）可确保第二次调用被静默丢弃。
        delivered = self._delivered_paths.setdefault(chat_id, set())
        if abs_path in delivered:
            logger.info(
                "[lightclaw] _send_attachment dedup (already delivered this turn): "
                "chat=%s path=%r",
                chat_id, abs_path,
            )
            return SendResult(success=True, message_id=None)
        delivered.add(abs_path)

        # Build the Markdown link: "📎 [name](localfile:///abs/path) (size)"
        link = f"📎 [{display_name}]({LOCALFILE_SCHEME}{abs_path})"
        try:
            link = f"{link} ({format_file_size(size)})"
        except Exception:
            pass

        text = (caption or "").rstrip()
        payload = f"{text}\n\n{link}".strip() if text else link

        return await self.send(chat_id, payload, reply_to=reply_to, metadata=metadata)

    # ------------------------------------------------------------------
    # Attachment path resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _attachment_candidates(file_path: str) -> list:
        """Return deterministic path forms for *file_path*.

        Used only for diagnostics.  Every candidate is a direct normalization of
        the original string; no basename-based fallback probing is performed.
        """
        if not file_path:
            return []

        raw = str(file_path).strip()
        if not raw:
            return []

        candidates: list[str] = [raw]

        stripped = raw
        if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in "`\"'":
            stripped = stripped[1:-1].strip()
        stripped = stripped.lstrip("`\"'").rstrip("`\"',.;:)}]")
        if stripped and stripped not in candidates:
            candidates.append(stripped)

        uri_path = stripped
        if uri_path.startswith("file://"):
            try:
                parsed = urlparse(uri_path)
                if parsed.scheme == "file":
                    uri_path = unquote(parsed.path or "")
                    if parsed.netloc and os.name == "nt":
                        uri_path = f"//{parsed.netloc}{uri_path}"
            except Exception:
                uri_path = stripped[len("file://"):]
            if uri_path and uri_path not in candidates:
                candidates.append(uri_path)

        expanded = os.path.expandvars(os.path.expanduser(uri_path))
        if expanded and expanded not in candidates:
            candidates.append(expanded)

        anchored = expanded
        if anchored and not os.path.isabs(anchored):
            base_dir = os.environ.get("TERMINAL_CWD") or os.getcwd()
            anchored = os.path.join(base_dir, anchored)
            if anchored not in candidates:
                candidates.append(anchored)

        if anchored:
            resolved = os.path.realpath(anchored)
            if resolved not in candidates:
                candidates.append(resolved)

        return candidates

    @staticmethod
    def _resolve_attachment_path(file_path: str) -> Optional[str]:
        """Return the exact resolved file path if it exists, else ``None``.

        Compatible with older Hermes versions (including 0.12.0) and avoids
        directory guessing.  Only direct normalizations of the provided path are
        considered.
        """
        candidates = OutboundMixin._attachment_candidates(file_path)
        if not candidates:
            return None

        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        return None

    # ------------------------------------------------------------------
    # Programmatic file delivery fallback
    # ------------------------------------------------------------------
    # The framework only auto-delivers a file when its path appears in the
    # model's final reply (MEDIA: tag or a bare absolute path that
    # extract_local_files() can detect).  write_file is deliberately NOT in
    # the framework's producer-tool auto-append allowlist (only TTS is), so a
    # weak model that forgets the path — or emits a broken markdown link like
    # ``[下载](`` — leaves the user with no download link.  As a model-
    # independent safety net we:
    #   1. Parse every write_file tool_start to extract the file path.
    #   2. In stop_typing(), before emitting typing_stop, deliver any paths
    #      that weren't already covered by the MEDIA: → send_document() path.

    def _correct_attachment_path(
        self, chat_id: str, file_path: str,
    ) -> Optional[str]:
        """Recover the real artifact path when a model-provided one is bogus.

        Weak models sometimes print a *fabricated* path in their final reply
        (wrong directory like ``/home/user/`` instead of the real
        ``/home/ubuntu/``, or a mangled double-extension like ``X.docx.md``).
        The framework's ``extract_local_files`` picks up that bare path and
        routes it here, where ``isfile()`` fails.

        The paths captured from ``write_file`` tool_start this turn
        (``_pending_file_paths``) are MODEL-INDEPENDENT ground truth, so we
        reconcile the failed request against them.  Returns the real path on a
        confident match, else ``None`` (caller then surfaces the error).
        """
        pending = self._pending_file_paths.get(chat_id) or []
        existing = [p for p in pending if p and os.path.isfile(p)]
        if not existing:
            return None

        req_base = os.path.basename(
            (file_path or "").strip().rstrip("`\"',.;:)}]")
        )

        # 1. Exact basename match — same file name, different (real) directory.
        for p in existing:
            if os.path.basename(p) == req_base:
                return p

        # 2. Stem match — handles mangled extensions (``X.docx.md`` vs ``X.md``)
        #    by comparing the name up to the first dot.
        req_stem = req_base.split(".", 1)[0]
        if req_stem:
            for p in existing:
                if os.path.basename(p).split(".", 1)[0] == req_stem:
                    return p

        # 3. Single unambiguous tracked file — only one write_file this turn,
        #    so the failed bare path almost certainly refers to it.
        if len(existing) == 1:
            return existing[0]

        return None

    def _track_write_file_path(self, chat_id: str, content: str) -> None:
        """Extract and stash the file path from a write_file tool_start message."""
        if "write_file" not in content:
            return
        path: Optional[str] = None

        # Try the combined regex first (covers compact and verbose mode).
        m = _WRITE_FILE_PATH_RE.search(content)
        if m:
            path = m.group(1).rstrip("\"',;:.)}]")

        # If the combined regex missed it, try the explicit JSON "path" key
        # (verbose mode when args are printed as JSON).
        if not path and '"path"' in content:
            m2 = _JSON_PATH_RE.search(content)
            if m2:
                path = m2.group(1)

        # Sanity-check: must be an absolute path and not a truncated preview.
        if not path or not path.startswith("/") or path.endswith("..."):
            return

        pending = self._pending_file_paths.setdefault(chat_id, [])
        if path not in pending:
            pending.append(path)
            logger.info(
                "[lightclaw] tracked write_file path: chat=%s path=%r",
                chat_id, path,
            )

    async def _deliver_pending_files(self, chat_id: str) -> None:
        """Auto-deliver write_file results that weren't tagged with MEDIA:.

        Called by stop_typing() BEFORE emitting typing_stop so the attachment
        links land inside the same message bubble as the rest of the response.
        Paths already delivered this turn (via the framework's
        send_document() path) are skipped using ``_delivered_paths``.
        """
        pending = self._pending_file_paths.pop(chat_id, [])
        if not pending:
            return
        # 使用 setdefault 确保与 send_document() 和 _send_attachment() 共享同一个 set 对象。
        # dict.get(key, set()) 返回的是临时 set，.add() 不会写回 _delivered_paths，
        # 导致 _send_attachment 中的去重守卫始终看到空 set，每次调用都会通过。
        delivered = self._delivered_paths.setdefault(chat_id, set())
        for path in pending:
            abs_path = os.path.abspath(path)
            if abs_path in delivered:
                logger.info(
                    "[lightclaw] skip auto-deliver (already delivered): "
                    "chat=%s path=%r",
                    chat_id, path,
                )
                continue
            if not os.path.isfile(path):
                logger.info(
                    "[lightclaw] skip auto-deliver (file not found): chat=%s path=%r",
                    chat_id, path,
                )
                continue
            logger.info(
                "[lightclaw] auto-delivering write_file result (model missed MEDIA:): "
                "chat=%s path=%r",
                chat_id, path,
            )
            # _send_attachment 在发送前会将 abs_path 加入 delivered，
            # 后续对同一路径的并发/重复调用都会被拦截。
            await self._send_attachment(chat_id, path)

    async def send_document(
        self, chat_id: str, file_path: str, caption: Optional[str] = None,
        file_name: Optional[str] = None, reply_to: Optional[str] = None, **kwargs,
    ) -> SendResult:
        # Record the delivered path so the stop_typing() fallback can skip it.
        # The framework's _deliver_media_from_response also routes here for any
        # MEDIA: tag / bare path it detects, so this dedup keeps a file from
        # being delivered twice (framework + fallback).
        if file_path:
            abs_path = os.path.abspath(file_path)
            self._delivered_paths.setdefault(chat_id, set()).add(abs_path)
        return await self._send_attachment(chat_id, file_path, caption, file_name, reply_to,
                                           metadata=kwargs.get("metadata"))

    async def send_voice(
        self, chat_id: str, audio_path: str, caption: Optional[str] = None,
        reply_to: Optional[str] = None, **kwargs,
    ) -> SendResult:
        return await self._send_attachment(chat_id, audio_path, caption, reply_to=reply_to,
                                           metadata=kwargs.get("metadata"))

    async def send_video(
        self, chat_id: str, video_path: str, caption: Optional[str] = None,
        reply_to: Optional[str] = None, **kwargs,
    ) -> SendResult:
        return await self._send_attachment(chat_id, video_path, caption, reply_to=reply_to,
                                           metadata=kwargs.get("metadata"))

    async def send_image_file(
        self, chat_id: str, image_path: str, caption: Optional[str] = None,
        reply_to: Optional[str] = None, **kwargs,
    ) -> SendResult:
        return await self._send_attachment(chat_id, image_path, caption, reply_to=reply_to,
                                           metadata=kwargs.get("metadata"))
