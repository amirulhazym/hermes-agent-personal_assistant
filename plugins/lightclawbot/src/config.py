"""
LightClaw adapter — constants and utility functions.
Mirrors: src/config.ts
"""

import os
import time
import uuid

# ---------------------------------------------------------------------------
# Channel key
# ---------------------------------------------------------------------------

CHANNEL_KEY = "lightclawbot"

# ---------------------------------------------------------------------------
# Event names
# ---------------------------------------------------------------------------

EVENT_MESSAGE_PRIVATE   = "message:private"
EVENT_MESSAGE_ACK       = "message:ack"
EVENT_HANDSHAKE         = "__handshake__"
EVENT_HISTORY_REQUEST   = "message:history:request"
EVENT_HISTORY_RESPONSE  = "message:history:response"
EVENT_SESSIONS_REQUEST  = "sessions:request"
EVENT_SESSIONS_RESPONSE = "sessions:response"

# ---------------------------------------------------------------------------
# Server URLs / paths
# ---------------------------------------------------------------------------

DEFAULT_WS_BASE_URL  = "wss://lightai.cloud.tencent.com"
DEFAULT_API_BASE_URL = "https://lightai.cloud.tencent.com"
SOCKET_PATH          = "/ws/agent"
API_PATH_TICKET      = "/cgi/ticket"

# ---------------------------------------------------------------------------
# Protocol limits
# ---------------------------------------------------------------------------

MAX_MESSAGE_LENGTH = 4096

# Default agentId (mirrors DEFAULT_AGENT_ID in config.ts)
DEFAULT_AGENT_ID = "main"

# ---------------------------------------------------------------------------
# Reconnect strategy (mirrors NativeSocketClient)
# ---------------------------------------------------------------------------

RECONNECT_DELAY_BASE = 1.0   # seconds
RECONNECT_DELAY_MAX  = 30.0  # seconds

# ---------------------------------------------------------------------------
# ReliableEmitter config (mirrors reliable-emitter.ts)
# ---------------------------------------------------------------------------

EMIT_ACK_TIMEOUT      = 5.0   # seconds
EMIT_MAX_RETRIES      = 3
EMIT_RETRY_BASE_DELAY = 2.0   # seconds
EMIT_RETRY_MAX_DELAY  = 15.0  # seconds
EMIT_PENDING_MAX      = 500

# ---------------------------------------------------------------------------
# Media / file storage (mirrors src/config.ts media section)
# ---------------------------------------------------------------------------

# Remote file storage service base URL
SERVER_UPLOAD_BASE_URL = "https://lightai.cloud.tencent.com"
API_PATH_UPLOAD        = "/drive/save"       # POST multipart/form-data
API_PATH_DOWNLOAD      = "/drive/preview"    # GET ?filePath=...

# Single-file hard limit: 100 MB (mirrors MEDIA_MAX_BYTES)
MEDIA_MAX_BYTES = 100 * 1024 * 1024
# Upload/download timeout in seconds (mirrors UPLOAD_TIMEOUT=120_000ms)
UPLOAD_TIMEOUT   = 120.0
DOWNLOAD_TIMEOUT = 60.0

# URI scheme for local-file references embedded in AI replies.
# Front-end recognises this prefix and issues a file:download signal to
# trigger on-demand upload + download.
LOCALFILE_SCHEME = "localfile://"

# Auth header `x-product` value (mirrors TS X_PRODUCT)
X_PRODUCT = "channel"

# ---------------------------------------------------------------------------
# file:download signalling (kind field value + status enum)
# ---------------------------------------------------------------------------

KIND_FILE_DOWNLOAD = "file:download"

# ---------------------------------------------------------------------------
# Token usage frame (kind field value)
# ---------------------------------------------------------------------------
# Per-turn token consumption carried under ``extra.usage`` (UnifiedUsage):
#   { kind: 'usage', extra: { chatId: '', usage: { inputTokens, outputTokens, totalTokens } } }
KIND_USAGE = "usage"


class FileDownloadStatus:
    """Lifecycle statuses carried inside `extra.transferData.status`.

    Mirrors TS FILE_DOWNLOAD_STATUS enum.
    """
    REQ   = "download_req"    # client → bot
    READY = "download_ready"  # bot → client (file confirmed, upload starting)
    URL   = "download_url"    # bot → client (upload done, public URL ready)
    ERROR = "download_error"  # bot → client (any failure)


# ---------------------------------------------------------------------------
# MIME type lookup (aligned 1:1 with TS guessMimeByExt)
# ---------------------------------------------------------------------------

_MIME_MAP = {
    # image
    ".png":  "image/png",
    ".jpg":  "image/jpeg", ".jpeg": "image/jpeg",
    ".gif":  "image/gif",
    ".webp": "image/webp",
    ".svg":  "image/svg+xml",
    # audio
    ".mp3":  "audio/mpeg",
    ".wav":  "audio/wav",
    ".ogg":  "audio/ogg",
    # video
    ".mp4":  "video/mp4",
    ".webm": "video/webm",
    # documents
    ".pdf":  "application/pdf",
    ".txt":  "text/plain",
}


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def generate_msg_id() -> str:
    """Generate a unique message ID."""
    return f"hermes_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"


def guess_mime(filename: str) -> str:
    """Guess MIME type from file extension."""
    ext = os.path.splitext(filename)[1].lower()
    return _MIME_MAP.get(ext, "application/octet-stream")


def check_lightclaw_requirements() -> bool:
    """Check if aiohttp is available (python-socketio no longer needed)."""
    try:
        import aiohttp  # noqa: F401
        return True
    except ImportError:
        return False
