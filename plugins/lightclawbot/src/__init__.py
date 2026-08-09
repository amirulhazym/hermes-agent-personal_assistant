"""
LightClaw platform adapter for Hermes Agent.

Connects to a LightClaw-compatible server via native WebSocket,
receiving user messages and sending AI responses back through the same protocol.

Protocol (post socket-rewrite):
- Auth:      POST /cgi/ticket  → { code:0, data:{ client:{ extra:'{"botId":"..."}' }, ticket:"..." } }
- Transport: Native WebSocket  wss://<domain>/ws/agent?ticket=<ticket>&enableMultiLogin=false
- Framing:   Raw JSON  { "event": "<name>", "data": {...} }
- Handshake: server sends { "event": "__handshake__", "data": { "id": "<socket_id>" } }
- ACK:       server sends { "event": "message:ack", "data": { "relatedMsgId": "<msgId>" } }
- Events:    message:private (bidirectional), history/sessions request/response
- Kinds:     text, typing_start, stream_chunk, stream_end, typing_stop

Package layout (mirrors lightclaw/src/):
    config.py                ← constants + utils           (config.ts)
    socket/reliable_emitter.py ← ACK-based send            (socket/reliable-emitter.ts)
    socket/native_socket.py  ← connection loop             (socket/native-socket.ts)
    inbound.py               ← inbound handler + media     (inbound.ts + media.ts)
    outbound.py              ← send API                    (outbound.ts)
    adapter.py               ← LightClawAdapter + singleton (gateway.ts)
"""

# Public API — kept stable so existing callers need no changes:
#   gateway/platforms/__init__.py  → from .lightclaw import LightClawAdapter
#   gateway/run.py                 → from gateway.platforms.lightclaw import LightClawAdapter, check_lightclaw_requirements
#   tools/send_message_tool.py     → from gateway.platforms.lightclaw import get_active_adapter

from .adapter import LightClawAdapter, get_active_adapter
from .config import check_lightclaw_requirements

__all__ = [
    "LightClawAdapter",
    "check_lightclaw_requirements",
    "get_active_adapter",
]
