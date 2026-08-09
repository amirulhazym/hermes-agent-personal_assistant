"""
LightClaw — on-demand file download signal handler.

Mirrors: src/socket/handlers.ts L306-436 (``handleFileDownloadReq``).

Protocol (front-end ↔ adapter)::

    Client → Adapter  (kind=file:download, status=download_req):
        { msgId, from, to, content:"", timestamp, kind:"file:download",
          extra: { transferData: { transferId, status:"download_req",
                                    localPath } } }

    Adapter → Client  (kind=file:download, status=download_ready):
        { ..., extra: { transferData: { transferId, status:"download_ready",
                                         name, size, contentType } } }

    Adapter → Client  (kind=file:download, status=download_url):
        { ..., extra: { transferData: { transferId, status:"download_url",
                                         url, name, size, contentType } } }

    Adapter → Client  (kind=file:download, status=download_error):
        { ..., extra: { transferData: { transferId, status:"download_error",
                                         error } } }

Flow:
    1. Parse transferId / localPath from ``data.extra.transferData``.
    2. Validate: localPath must be absolute, must exist, must be a regular
       file.  On failure → ``download_error`` and stop.
    3. Emit ``download_ready`` with the file metadata (name/size/mime).
    4. Upload the file to ``/drive/save`` (server-side content review).
    5. On success → ``download_url`` with the public URL.
       On failure → ``download_error``.

All four reply frames use the reliable emitter (ACK + auto-retry),
matching TS emitWithAck semantics.
"""

from __future__ import annotations

import asyncio
import logging
import os

from .config import (
    DEFAULT_AGENT_ID,
    EVENT_MESSAGE_PRIVATE,
    FileDownloadStatus,
    KIND_FILE_DOWNLOAD,
)
from .file_storage import upload_file_to_server
from .media import guess_mime_by_ext
from .tenancy import resolve_effective_api_key

logger = logging.getLogger(__name__)


class DownloadHandlerMixin:
    """Mixin providing the ``file:download`` request handler.

    Requires (set by LightClawAdapter):
        self._bot_client_id: str
        self._session: aiohttp.ClientSession
        self._reliable: ReliableEmitter
        self._build_message(...)
        self._emit_reliable(event, data)
    """

    async def _handle_file_download_req(self, data: dict) -> None:
        """Handle one ``file:download`` ``download_req`` frame.

        Fire-and-forget from ``_handle_raw``; never re-raises.  Three
        outcomes: ``download_ready`` + ``download_url`` on success, or
        ``download_error`` on any failure.
        """
        sender   = data.get("from") or ""
        agent_id = data.get("agentId") or DEFAULT_AGENT_ID

        extra = data.get("extra") or {}
        td    = extra.get("transferData") if isinstance(extra, dict) else None
        td    = td or {}

        transfer_id = td.get("transferId")
        local_path  = td.get("localPath") or ""

        logger.info(
            "[lightclaw] file:download(req) received: transferId=%s localPath=%s from=%s",
            transfer_id, local_path, sender,
        )

        async def _reply(status: str, **payload) -> None:
            """Emit one file:download reply frame (reliable)."""
            transfer_payload = {"transferId": transfer_id, "status": status}
            transfer_payload.update(payload)
            msg = self._build_message(
                sender, "",
                kind=KIND_FILE_DOWNLOAD,
                agent_id=agent_id,
                extra={"transferData": transfer_payload},
            )
            try:
                await self._emit_reliable(EVENT_MESSAGE_PRIVATE, msg)
            except Exception as emit_err:
                logger.warning(
                    "[lightclaw] file:download emit(%s) failed for transferId=%s: %s",
                    status, transfer_id, emit_err,
                )

        async def _reply_error(message: str) -> None:
            logger.error(
                "[lightclaw] file:download(error) transferId=%s: %s",
                transfer_id, message,
            )
            await _reply(FileDownloadStatus.ERROR, error=message)

        # ── ① validation ────────────────────────────────────────────
        if not transfer_id or not local_path:
            await _reply_error("Missing transferId or localPath in extra.transferData")
            return
        if not sender:
            logger.warning("[lightclaw] file:download(req) missing sender, ignoring")
            return
        if not os.path.isabs(local_path):
            await _reply_error(f"localPath must be an absolute path: {local_path}")
            return

        resolved = os.path.realpath(local_path)
        if not os.path.exists(resolved):
            await _reply_error(f"File not found: {resolved}")
            return
        if not os.path.isfile(resolved):
            await _reply_error(f"Not a regular file: {resolved}")
            return

        file_name = os.path.basename(resolved)
        size = os.path.getsize(resolved)
        mime = guess_mime_by_ext(file_name) or "application/octet-stream"

        # ── ② ready frame ───────────────────────────────────────────
        await _reply(
            FileDownloadStatus.READY,
            name=file_name, size=size, contentType=mime,
        )
        logger.info(
            "[lightclaw] file:download(ready) sent: transferId=%s name=%s size=%d",
            transfer_id, file_name, size,
        )

        # ── ③ upload + url frame ────────────────────────────────────
        try:
            api_key = resolve_effective_api_key(sender_id=sender)
            _, public_url = await upload_file_to_server(
                resolved, api_key=api_key, session=self._session,
            )
        except asyncio.CancelledError:
            raise
        except Exception as upload_err:
            await _reply_error(str(upload_err))
            return

        await _reply(
            FileDownloadStatus.URL,
            url=public_url, name=file_name, size=size, contentType=mime,
        )
        logger.info(
            "[lightclaw] file:download(url) sent: transferId=%s url=%s",
            transfer_id, public_url,
        )
