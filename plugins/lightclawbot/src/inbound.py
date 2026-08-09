"""
LightClaw inbound message handler — processes incoming message:private events,
downloads/decodes file attachments, and dispatches MessageEvents.

Mirrors: src/inbound.ts + src/media.ts (processFiles inline in inbound.ts).

Attachment pipeline (aligned 1:1 with TS inbound.ts L106-172):

    for each file:
      ① source detection
         - file.bytes is a data URL  → parse_data_url → (buf, mime)
         - file.uri  is a cloud URI  → download_file_from_server(buf, ctype)
         - neither                   → skip with warn

      ② save to local media dir (size/format check)

      ③ warm upload to /drive/save:
         - data-URL source: POST /drive/save (server-side content review),
           failures are logged and ignored
         - uri source: skip upload (already on server)

         ★ The resulting public URL is ONLY logged — the URL pushed into
           `public_urls` is ALWAYS `localfile://<saved_path>`.  This is
           intentional and mirrors TS behaviour precisely.  The real
           delivery path back to the client is the on-demand file:download
           signal handshake (see download_handler.py), not the inbound
           public URL.

      ④ record `{name, mimeType, url: localfile://...}` into
         adapter._inbound_attachments[chat_id] for history persistence.
"""

import base64  # noqa: F401  (kept for backwards-compat external imports)
import logging
import os
import uuid
from typing import List, Optional, Tuple

from gateway.platforms.base import MessageEvent, MessageType, get_image_cache_dir

from .config import (
    CHANNEL_KEY,
    DEFAULT_AGENT_ID,
    EVENT_MESSAGE_PRIVATE,
    LOCALFILE_SCHEME,
    MEDIA_MAX_BYTES,
)
from .file_storage import (
    download_file_from_server,
    get_file_download_url,
    upload_file_to_server,
)
from .media import format_file_size, guess_mime_by_ext, parse_data_url
from .tenancy import resolve_effective_api_key, set_session_api_key

logger = logging.getLogger(__name__)


class InboundMixin:
    """
    Mixin providing inbound message handling, file processing,
    and history/sessions stub responses.
    Mirrors: inbound.ts (handleIncomingMessage) + media.ts (processFiles)

    Requires (set by LightClawAdapter):
        self._bot_client_id: str
        self._api_keys: list[str]
        self._api_base_url: str
        self._session: aiohttp.ClientSession
        self._inbound_attachments: Dict[str, list]
        self.build_source(...)
        self.handle_message(event)
        self._fire_and_forget(event, data)
        self._generate_msg_id() or generate_msg_id()
    """

    # ------------------------------------------------------------------
    # Incoming message dispatcher
    # ------------------------------------------------------------------

    async def _handle_incoming_message(self, data: dict) -> None:
        """
        Handle a message:private inbound event.
        Mirrors: handleIncomingMessage in inbound.ts
        """
        sender   = data.get("from", "")
        content  = data.get("content", "")
        msg_id   = data.get("msgId", "")
        kind     = data.get("kind", "text")
        files    = data.get("files") or []
        agent_id = data.get("agentId") or DEFAULT_AGENT_ID

        # Echo prevention + control-message filter
        if sender == self._bot_client_id:
            return
        if kind and kind != "text":
            return
        if not (content and content.strip()) and not files:
            return

        logger.info(
            "[lightclaw] Incoming: from=%s msgId=%s kind=%s agentId=%s content='%s' files=%d",
            sender, msg_id, kind, agent_id, (content or "")[:60], len(files),
        )

        # Stash agentId so outbound methods can echo it back.
        # MessageEvent has no metadata field; we use a per-chat dict on the adapter.
        self._incoming_agent_ids[sender] = agent_id

        # Register sessionKey → apiKey so tool executions within this
        # session can resolve the tenant's apiKey via ctx.sessionKey alone.
        # Must run BEFORE any file processing (upload uses the same key).
        # Mirrors TS inbound.ts L89-97.
        if agent_id != DEFAULT_AGENT_ID:
            session_key = f"agent:main:{CHANNEL_KEY}:dm:{sender}:{agent_id}"
        else:
            session_key = f"agent:main:{CHANNEL_KEY}:dm:{sender}"
        effective_key = resolve_effective_api_key(sender_id=sender)
        set_session_api_key(session_key, effective_key)

        # If a previous round is still open (e.g. /new response didn't get a
        # finalize), close it with typing_stop before starting a new round.
        old_round = self._round_ids.get(sender)
        if old_round:
            self._fire_and_forget(
                EVENT_MESSAGE_PRIVATE,
                self._build_message(sender, "", kind="typing_stop",
                                    msg_id=old_round, agent_id=agent_id),
            )

        # Create a fresh round for this new conversation turn.
        self._clear_round_id(sender)
        # Drop any "last closed round" reservation from the previous turn.
        # From now on, output for this chat must use the fresh round msgId.
        self._last_round_id.pop(sender, None)
        # Reset per-turn usage state and snapshot the token baseline so
        # stop_typing can compute this turn's delta.
        self._round_usage_emitted.pop(sender, None)
        # Remember the inbound msgId for the usage frame's replyToMsgId.
        self._round_reply_to[sender] = msg_id
        self._usage_tracker.snapshot_baseline(sender)
        # Clear per-turn file tracking state.
        getattr(self, "_pending_file_paths", {}).pop(sender, None)
        getattr(self, "_delivered_paths", {}).pop(sender, None)
        round_msg_id = self._get_or_create_round_id(sender)
        self._fire_and_forget(
            EVENT_MESSAGE_PRIVATE,
            self._build_message(sender, "", kind="typing_start",
                                msg_id=round_msg_id, agent_id=agent_id),
        )
        logger.info("[lightclaw] typing_start sent: to=%s roundMsgId=%s", sender, round_msg_id)

        source = self.build_source(
            chat_id=sender,
            chat_type="dm",
            user_id=sender,
            user_name=sender,
            # Multi-agent isolation: when agentId differs from the default,
            # encode it as thread_id so build_session_key produces a distinct
            # key per agent (e.g. "agent:main:lightclawbot:dm:<sender>:<agentId>").
            # This keeps different agents' conversation histories separated
            # without modifying the base session key builder.
            thread_id=agent_id if agent_id != DEFAULT_AGENT_ID else None,
        )

        media_urls, media_types, attachment_desc = await self._process_files(
            files, sender, effective_key,
        )

        # Multi-agent system prompt: look up per-agent prompt from config.
        # Configured in config.yaml → platforms.lightclaw.extra.agent_prompts
        agent_prompt = None
        if agent_id:
            agent_prompts = getattr(self, "_agent_prompts", None) or {}
            agent_prompt = agent_prompts.get(agent_id) or None

        event = MessageEvent(
            text=(content or "") + attachment_desc,
            message_type=MessageType.TEXT,
            source=source,
            message_id=msg_id,
            media_urls=media_urls,
            media_types=media_types,
            channel_prompt=agent_prompt,
        )
        await self.handle_message(event)

    # ------------------------------------------------------------------
    # File processing (mirrors TS media.ts + inbound.ts file loop)
    # ------------------------------------------------------------------

    async def _process_files(
        self, files: list, sender: str, api_key: str,
    ) -> Tuple[List[str], List[str], str]:
        """
        Ingest `files[]` from an inbound `message:private` payload.

        Returns (local_paths, mime_types, description_text).

        * local_paths / mime_types: parallel arrays passed to the agent via
          `MessageEvent.media_urls / media_types`.  These point to on-disk
          copies and are what vision/audio tools actually read.

        * description_text: trailing block appended to the user text so
          small models that don't inspect `media_urls` still know files
          were attached (TS `attachmentDescription`).

        Side effects:
          - Warm-uploads data-URL files to /drive/save for server-side
            content review (failures are logged, never fatal).
          - Populates self._inbound_attachments[sender] with
            `{name, mimeType, url=localfile://...}` entries for history.
        """
        local_paths:   List[str] = []
        local_types:   List[str] = []
        ctx_attachments: List[dict] = []
        desc = ""

        for f in files:
            try:
                name = f.get("name") or "file"
                mime = f.get("mimeType") or "application/octet-stream"
                buf: Optional[bytes] = None
                is_uri_source = False

                # ── ① source detection ──────────────────────────────
                if f.get("bytes"):
                    parsed = parse_data_url(f["bytes"])
                    if parsed:
                        buf, parsed_mime = parsed
                        # Prefer the data-URL's MIME over the metadata one
                        mime = parsed_mime or mime
                    else:
                        logger.warning(
                            "[lightclaw] file %s: malformed data URL, skipping", name,
                        )
                        continue
                elif f.get("uri"):
                    is_uri_source = True
                    try:
                        buf, _, ctype = await download_file_from_server(
                            f["uri"], api_key=api_key, session=self._session,
                        )
                        if ctype and ctype != "application/octet-stream":
                            mime = ctype
                    except Exception as exc:
                        logger.warning(
                            "[lightclaw] file %s: download from uri failed: %s",
                            name, exc,
                        )
                        continue
                else:
                    logger.warning(
                        "[lightclaw] file %s has neither bytes nor uri, skipping", name,
                    )
                    continue

                if buf is None:
                    continue
                if len(buf) > MEDIA_MAX_BYTES:
                    logger.warning(
                        "[lightclaw] file %s exceeds %d bytes (got %d), skipping",
                        name, MEDIA_MAX_BYTES, len(buf),
                    )
                    continue

                # ── ② save to local media dir ───────────────────────
                saved_path = self._save_media_buffer(buf, mime, name)
                local_paths.append(saved_path)
                local_types.append(mime)

                # ── ③ warm upload (data-URL source only) ────────────
                # The resulting public URL is purely informational; we
                # always hand `localfile://` back to the agent, matching
                # TS publicMediaUrls behaviour (see docstring).
                if not is_uri_source:
                    try:
                        _, warm_url = await upload_file_to_server(
                            saved_path, api_key=api_key, session=self._session,
                        )
                        logger.info(
                            "[lightclaw] inbound warm upload: %s → %s",
                            saved_path, warm_url,
                        )
                    except Exception as upload_err:
                        logger.warning(
                            "[lightclaw] inbound warm upload failed (ignored): %s",
                            upload_err,
                        )

                local_uri = f"{LOCALFILE_SCHEME}{saved_path}"
                ctx_attachments.append({
                    "name": name, "mimeType": mime, "url": local_uri,
                })

                # Build the description text appended to the user message.
                # For image/audio files the framework enriches the message via
                # media_urls (vision_analyze / STT), so a short note suffices.
                # For all other file types (documents, scripts, archives, etc.)
                # the framework ONLY processes MessageType.DOCUMENT — but we
                # always emit TEXT.  So we must inject the actual local path
                # into the text so the AI knows where to read the file.
                size_str = format_file_size(len(buf))
                if mime.startswith(("image/", "audio/")):
                    desc += f"\n用户发送了文件: {name} ({size_str})"
                else:
                    desc += (
                        f"\n[用户发送了文件: {name} ({size_str})，"
                        f"已保存到: {saved_path}]"
                    )
                # 追加 [media attached: ...] 标记，为了刷新后 history.extract_file_attachments()
                # 从 transcript 中恢复文件的 mimeType 和 localfile:// uri
                # 格式与 history.py 的 _MEDIA_ATTACH_RE 对齐：[media attached: <path> (<mime>) | localfile://<path>]
                desc += f"\n[media attached: {saved_path} ({mime}) | {local_uri}]"
                logger.info(
                    "[lightclaw] file saved: %s (%s, %s)",
                    saved_path, mime, format_file_size(len(buf)),
                )

            except Exception as exc:
                # Per-file error must not break the whole message.
                logger.warning(
                    "[lightclaw] file processing failed for %s: %s",
                    f.get("name"), exc,
                )

        if ctx_attachments:
            # Stash for history persistence / outbound enrichment.
            inbound = getattr(self, "_inbound_attachments", None)
            if isinstance(inbound, dict):
                inbound.setdefault(sender, []).extend(ctx_attachments)

        return local_paths, local_types, desc

    # ------------------------------------------------------------------
    # Local media save (mirrors TS pluginRuntime.channel.media.saveMediaBuffer)
    # ------------------------------------------------------------------

    def _save_media_buffer(
        self, buffer: bytes, mime: str, file_name: str,
    ) -> str:
        """Persist *buffer* to the framework media cache dir.

        The filename is sanitised by keeping the original extension (if
        any, otherwise derived from *mime*) and prefixing with a short
        random token to avoid collisions.  Returns the absolute path.
        """
        # Pick an extension: original → mime-derived → ".bin"
        ext = os.path.splitext(file_name or "")[1].lower()
        if not ext:
            for e, m in _MIME_REVERSE_LOOKUP:
                if m == mime:
                    ext = e
                    break
        if not ext:
            ext = ".bin"

        cache_dir = get_image_cache_dir()
        token = uuid.uuid4().hex[:8]
        path = str(cache_dir / f"lc_{token}{ext}")
        with open(path, "wb") as fp:
            fp.write(buffer)
        return path

    # ------------------------------------------------------------------
    # Legacy _download_file retained for backwards compatibility.
    # New code should use file_storage.download_file_from_server directly.
    # ------------------------------------------------------------------

    async def _download_file(self, uri: str, sender: str) -> Optional[bytes]:
        """Download a file from server URI or HTTP URL.

        Thin wrapper kept for callers that pre-date the file_storage
        module; delegates to :func:`download_file_from_server`.
        """
        api_key = resolve_effective_api_key(sender_id=sender)
        try:
            buf, _, _ = await download_file_from_server(
                uri, api_key=api_key, session=self._session,
            )
            return buf
        except Exception as exc:
            logger.warning("[lightclaw] _download_file fallback failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # History & sessions
    # ------------------------------------------------------------------

    async def _handle_history_request(self, data: dict) -> None:
        """Return real history messages from the SQLite session store.

        Mirrors: handlers.ts → EVENT_HISTORY_REQUEST handler.
        """
        from .config import EVENT_HISTORY_RESPONSE, DEFAULT_AGENT_ID, CHANNEL_KEY, generate_msg_id
        from .history import read_session_history

        user_id = data.get("from", "")
        if not user_id or user_id == self._bot_client_id:
            return

        agent_id = data.get("agentId") or DEFAULT_AGENT_ID
        limit = data.get("limit") or 200
        chat_only = data.get("chatOnly", True)

        # Build session key — must match the format generated by
        # build_session_key(platform=<CHANNEL_KEY>, chat_type=dm, chat_id=user_id,
        #   thread_id=agent_id if non-default).
        # Default agent:  "agent:main:<CHANNEL_KEY>:dm:<user_id>"
        # Other agents:   "agent:main:<CHANNEL_KEY>:dm:<user_id>:<agent_id>"
        if agent_id != DEFAULT_AGENT_ID:
            session_key = f"agent:main:{CHANNEL_KEY}:dm:{user_id}:{agent_id}"
        else:
            session_key = f"agent:main:{CHANNEL_KEY}:dm:{user_id}"

        messages = read_session_history(
            session_key,
            getattr(self, "_sessions_dir", None),
            limit=limit,
            chat_only=chat_only,
        )

        sessions_dir = getattr(self, "_sessions_dir", None)
        logger.info(
            "[lightclaw] History request: userId=%s agentId=%s sessionKey=%s "
            "sessionsDir=%s found=%d",
            user_id, agent_id, session_key, sessions_dir, len(messages),
        )

        msg_id = generate_msg_id()
        self._fire_and_forget(EVENT_HISTORY_RESPONSE, {
            "msgId":      msg_id,
            "from":       self._bot_client_id,
            "to":         user_id,
            "sessionKey": session_key,
            "messages":   messages,
            "agentId":    agent_id,
        })

    async def _handle_sessions_request(self, data: dict) -> None:
        """Return all sessions from sessions.json index.

        Mirrors: handlers.ts → EVENT_SESSIONS_REQUEST handler.

        Multi-tenant safety (D2):
            ``sessions.json`` lives at Hermes-instance level — every tenant
            shares one file.  Without filtering, user A asking for "my
            sessions list" would see user B's sessionKeys (peer_uin leak,
            cross-tenant data exposure).  We pin results to entries whose
            sessionKey carries ``:dm:<from>`` and the LightClaw
            ``channel_key`` prefix.  Falls back to unfiltered behaviour
            only when ``data["from"]`` is empty (legacy / synthetic
            requests).
        """
        from .config import EVENT_SESSIONS_RESPONSE, generate_msg_id
        from .history import list_sessions

        owner_uin = (data.get("from") or "").strip() or None

        sessions = list_sessions(
            getattr(self, "_sessions_dir", None),
            owner_uin=owner_uin,
            channel_key=CHANNEL_KEY,
        )

        msg_id = generate_msg_id()
        self._fire_and_forget(EVENT_SESSIONS_RESPONSE, {
            "requestId": data.get("requestId"),
            "sessions":  sessions,
            "msgId":     msg_id,
            # Echo the requester so the per-uin session router can deliver
            # the response back via the right WS (see adapter._fire_and_forget,
            # which inspects data["to"] / data["from"] for chat routing).
            "from":      self._bot_client_id,
            "to":        owner_uin or "",
        })


# ---------------------------------------------------------------------------
# Reverse MIME → extension lookup (used by _save_media_buffer)
# ---------------------------------------------------------------------------
# Computed once at import time.  Prefers the first extension seen for each
# MIME (so image/jpeg → .jpg rather than .jpeg).

from .config import _MIME_MAP as _FORWARD_MIME_MAP  # noqa: E402

_MIME_REVERSE_LOOKUP = []  # list of (ext, mime) in insertion order
_seen_mimes = set()
for _ext, _m in _FORWARD_MIME_MAP.items():
    if _m not in _seen_mimes:
        _MIME_REVERSE_LOOKUP.append((_ext, _m))
        _seen_mimes.add(_m)
del _seen_mimes
