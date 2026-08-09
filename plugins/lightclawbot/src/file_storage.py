"""
LightClaw — remote file storage client.
Mirrors: src/file-storage.ts

All binary transfer with ai-server happens here.  HTTP contract
(reverse-engineered from the TS client):

    Upload   : POST   /drive/save
               Content-Type: multipart/form-data
               Fields  : file (binary) + filePath (string)
               Auth    : Bearer <apiKey>, x-product: channel
               Success : { code: 0, data: { uploaded: true, ... } }

    Download : GET    /drive/preview?filePath=<filePath>
               Auth    : Bearer <apiKey>, x-product: channel
               Success : HTTP 200, body = raw file bytes

The server-side ``filePath`` is constructed client-side as
``${Date.now()}/${fileName}`` so that concurrent uploads of the same
name never collide.  The returned public URL is constructed locally as
``${SERVER_UPLOAD_BASE_URL}${API_PATH_DOWNLOAD}?filePath=<filePath>``
rather than trusting the server response — matches TS behaviour and
means the public URL is deterministic given a known ``filePath``.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Optional, Tuple
from urllib.parse import quote

from .config import (
    API_PATH_DOWNLOAD,
    API_PATH_UPLOAD,
    DOWNLOAD_TIMEOUT,
    SERVER_UPLOAD_BASE_URL,
    UPLOAD_TIMEOUT,
)
from .media import guess_mime_by_ext
from .tenancy import build_auth_headers

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_file_download_url(file_path: str) -> str:
    """Build a public ``/drive/preview`` URL for *file_path*.

    Does not perform any network IO.  Mirrors TS ``getFileDownloadUrl``.
    """
    if not file_path:
        return ""
    # Full http(s) URL passthrough — sometimes the caller already has one.
    if file_path.startswith(("http://", "https://")):
        return file_path
    return f"{SERVER_UPLOAD_BASE_URL}{API_PATH_DOWNLOAD}?filePath={quote(file_path, safe='')}"


def _make_server_file_path(file_name: str) -> str:
    """Generate the remote ``filePath`` (millisecond timestamp dir + name)."""
    return f"{int(time.time() * 1000)}/{file_name}"


async def _do_upload(
    *,
    data: bytes,
    file_name: str,
    mime: str,
    api_key: str,
    session,
) -> Tuple[str, str]:
    """Internal: POST /drive/save and return ``(file_path, public_url)``.

    Raises ``RuntimeError`` on any failure (HTTP error, timeout, server
    rejection).  The caller decides whether to fall back gracefully.
    """
    import aiohttp

    file_path = _make_server_file_path(file_name)

    form = aiohttp.FormData()
    form.add_field("file", data, filename=file_name, content_type=mime)
    form.add_field("filePath", file_path)

    url = f"{SERVER_UPLOAD_BASE_URL}{API_PATH_UPLOAD}"
    headers = build_auth_headers(api_key)

    try:
        async with session.post(
            url,
            data=form,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=UPLOAD_TIMEOUT),
        ) as resp:
            if resp.status != 200:
                body = (await resp.text())[:200]
                raise RuntimeError(f"Upload HTTP {resp.status}: {body}")
            result = await resp.json(content_type=None)
    except asyncio.TimeoutError as exc:
        raise RuntimeError(f"Upload timeout after {UPLOAD_TIMEOUT}s") from exc

    if not isinstance(result, dict):
        raise RuntimeError(f"Upload rejected: non-JSON response {result!r}")

    data_field = result.get("data") or {}
    if result.get("code") == 0 and data_field.get("uploaded") is True:
        return file_path, get_file_download_url(file_path)

    raise RuntimeError(f"Upload rejected: {result}")


# ---------------------------------------------------------------------------
# Public upload API
# ---------------------------------------------------------------------------

async def upload_file_to_server(
    local_path: str,
    *,
    api_key: str,
    session,
    custom_file_name: Optional[str] = None,
) -> Tuple[str, str]:
    """Upload a local file to ai-server.

    Returns ``(server_file_path, public_url)``.

    :param local_path:        absolute path of the file to upload.
    :param api_key:           tenant API key (Bearer auth).
    :param session:           an ``aiohttp.ClientSession``.
    :param custom_file_name:  override the remote file name.
    :raises FileNotFoundError: when *local_path* does not exist or is
        not a regular file.
    :raises RuntimeError:      for any network / server rejection.
    """
    if not local_path or not os.path.exists(local_path):
        raise FileNotFoundError(f"File not found: {local_path}")
    if not os.path.isfile(local_path):
        raise RuntimeError(f"Not a regular file: {local_path}")

    file_name = custom_file_name or os.path.basename(local_path)
    mime = guess_mime_by_ext(file_name)

    with open(local_path, "rb") as fp:
        payload = fp.read()

    file_path, public_url = await _do_upload(
        data=payload, file_name=file_name, mime=mime,
        api_key=api_key, session=session,
    )
    logger.info("[lightclaw] uploaded %s → %s", local_path, public_url)
    return file_path, public_url


async def upload_buffer_to_server(
    buffer: bytes,
    file_name: str,
    mime: str,
    *,
    api_key: str,
    session,
) -> Tuple[str, str]:
    """Upload an in-memory buffer. Same contract as :func:`upload_file_to_server`."""
    if buffer is None:
        raise RuntimeError("buffer must not be None")
    file_path, public_url = await _do_upload(
        data=buffer, file_name=file_name or "file",
        mime=mime or "application/octet-stream",
        api_key=api_key, session=session,
    )
    logger.info("[lightclaw] uploaded buffer (%d bytes) → %s", len(buffer), public_url)
    return file_path, public_url


async def upload_and_get_public_url(
    local_path: str,
    *,
    api_key: str,
    session,
) -> str:
    """Convenience wrapper: upload and return only the public URL."""
    _, url = await upload_file_to_server(
        local_path, api_key=api_key, session=session,
    )
    return url


# ---------------------------------------------------------------------------
# Public download API
# ---------------------------------------------------------------------------

async def download_file_from_server(
    file_path_or_url: str,
    *,
    api_key: str,
    session,
) -> Tuple[bytes, str, str]:
    """GET ``/drive/preview`` for *file_path_or_url*.

    Returns ``(buffer, file_name, content_type)``.  If a full http(s) URL
    is passed, it's used directly — otherwise it's treated as a remote
    ``filePath`` and wrapped with :func:`get_file_download_url`.
    """
    import aiohttp

    if not file_path_or_url:
        raise RuntimeError("file_path_or_url is required")

    url = (file_path_or_url
           if file_path_or_url.startswith(("http://", "https://"))
           else get_file_download_url(file_path_or_url))
    headers = build_auth_headers(api_key)

    try:
        async with session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT),
        ) as resp:
            if resp.status != 200:
                body = (await resp.text())[:200]
                raise RuntimeError(f"Download HTTP {resp.status}: {body}")
            buf = await resp.read()
            content_type = resp.headers.get("content-type", "application/octet-stream")
    except asyncio.TimeoutError as exc:
        raise RuntimeError(f"Download timeout after {DOWNLOAD_TIMEOUT}s") from exc

    # Derive filename: strip query string + take last path segment.
    tail = file_path_or_url.split("?", 1)[0]
    file_name = tail.rsplit("/", 1)[-1] or "file"
    return buf, file_name, content_type
