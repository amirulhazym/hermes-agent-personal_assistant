"""
LightClaw — media utility functions.
Mirrors: src/media.ts

Pure helpers for parsing data URLs, formatting file sizes, guessing MIME
types from file extensions, and converting AI-engine-produced mediaUrl
lists (data:// / http:// / local paths) into the canonical
FileAttachment format (`{name, mimeType, bytes: 'data:<mime>;base64,<...>'}`).
"""

import base64
import binascii
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from .config import _MIME_MAP

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# data URL parsing (mirrors TS parseDataUrl)
# ---------------------------------------------------------------------------

# Pattern: "data:<mime>;base64,<payload>"  (payload may contain anything,
# including newlines, which some producers emit — hence DOTALL).
_DATA_URL_RE = re.compile(r"^data:([^;]+);base64,(.+)$", re.DOTALL)


def parse_data_url(data_url: str) -> Optional[Tuple[bytes, str]]:
    """Parse a base64 data URL → ``(buffer, mime_type)``.

    Returns ``None`` if *data_url* is not a well-formed base64 data URL.
    Mirrors TS ``parseDataUrl`` in ``src/media.ts``.
    """
    if not data_url:
        return None
    m = _DATA_URL_RE.match(data_url)
    if not m:
        return None
    mime = m.group(1).strip()
    payload = m.group(2).strip()
    try:
        buf = base64.b64decode(payload, validate=False)
    except (ValueError, binascii.Error):
        return None
    return buf, mime


# ---------------------------------------------------------------------------
# Human-readable file-size formatting (mirrors TS formatFileSize)
# ---------------------------------------------------------------------------

def format_file_size(n_bytes: int) -> str:
    """Format a byte count as a compact human-readable string.

    Examples::

        0       → "0B"
        512     → "512B"
        2048    → "2.0KB"
        1_500_000 → "1.4MB"
        3_221_225_472 → "3.0GB"
    """
    if n_bytes < 1024:
        return f"{n_bytes}B"
    if n_bytes < 1024 ** 2:
        return f"{n_bytes / 1024:.1f}KB"
    if n_bytes < 1024 ** 3:
        return f"{n_bytes / 1024 ** 2:.1f}MB"
    return f"{n_bytes / 1024 ** 3:.1f}GB"


# ---------------------------------------------------------------------------
# MIME type guessing (mirrors TS guessMimeByExt)
# ---------------------------------------------------------------------------

def guess_mime_by_ext(name_or_ext: str) -> str:
    """Guess MIME type from a filename or a bare extension.

    Accepts both ``".png"`` and ``"picture.png"`` style inputs.  Returns
    ``"application/octet-stream"`` when no mapping matches.
    """
    if not name_or_ext:
        return "application/octet-stream"
    # If the input looks like a bare extension (".png") keep it; otherwise
    # extract the extension from the full filename.
    if name_or_ext.startswith(".") and "/" not in name_or_ext:
        ext = name_or_ext
    else:
        ext = os.path.splitext(name_or_ext)[1]
    ext = ext.lower()
    return _MIME_MAP.get(ext, "application/octet-stream")


# Backwards-compat alias (original helper name in config.py).
guess_mime = guess_mime_by_ext


# ---------------------------------------------------------------------------
# mediaUrlsToFiles — normalise AI-returned media URL list to FileAttachment
# ---------------------------------------------------------------------------

async def media_urls_to_files(
    urls: List[str],
    *,
    session: Any,
) -> List[Dict[str, str]]:
    """Convert a mediaUrl list into ``FileAttachment`` dicts.

    Each returned item has shape::

        {"name": <basename>, "mimeType": <mime>, "bytes": "data:<mime>;base64,<...>"}

    Supported URL forms (mirrors TS mediaUrlsToFiles):
        * ``data:<mime>;base64,<...>``
        * ``http://`` / ``https://``
        * absolute local path (e.g. ``/tmp/foo.png``)
        * ``localfile://<abs>`` — stripped to absolute local path

    *session* must be an ``aiohttp.ClientSession`` (only used for http urls).
    Individual URL failures are logged and skipped; the function never raises.
    """
    import aiohttp  # noqa: F401  (import hint for typing)

    from .config import LOCALFILE_SCHEME

    files: List[Dict[str, str]] = []
    for url in urls or []:
        try:
            buf: Optional[bytes] = None
            mime: str = "application/octet-stream"
            name: str = "file"

            if url.startswith("data:"):
                parsed = parse_data_url(url)
                if not parsed:
                    logger.warning("[media] skip malformed data URL")
                    continue
                buf, mime = parsed

            elif url.startswith(("http://", "https://")):
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning("[media] HTTP %d for %s", resp.status, url[:80])
                        continue
                    buf = await resp.read()
                    mime = resp.headers.get("content-type", mime) or mime
                    name = (url.split("/")[-1].split("?")[0]) or "file"

            else:
                # localfile:// or raw local path
                local_path = url[len(LOCALFILE_SCHEME):] if url.startswith(LOCALFILE_SCHEME) else url
                if not os.path.isfile(local_path):
                    logger.warning("[media] local file missing: %s", local_path)
                    continue
                with open(local_path, "rb") as fp:
                    buf = fp.read()
                mime = guess_mime_by_ext(local_path)
                name = os.path.basename(local_path)

            if buf is None:
                continue

            files.append({
                "name": name,
                "mimeType": mime,
                "bytes": f"data:{mime};base64,{base64.b64encode(buf).decode()}",
            })
        except Exception as exc:
            logger.warning("[media] media_urls_to_files failed for %s: %s", url[:80], exc)

    return files
