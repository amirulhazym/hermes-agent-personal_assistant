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

  ``edit_message(finalize=True)`` 只表示当前流分段结束：Hermes 在工具调用前、
  overflow 分段时同样会传入该标记。只有 ``stop_typing()`` 表示整轮结束，
  负责发送 ``typing_stop``，使前端完成并缓存可见回答。

  - Streaming:  inbound typing_start
                → send(first_chunk)
                → edit_message() × N
                → edit_message(finalize=True)          # 当前分段结束
                → [optional tool / follow-up stream_chunk / attachment link]*
                → stop_typing() → typing_stop           # 整轮结束
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
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote, unquote, urlparse

from gateway.platforms.base import SendResult

from .config import (
    BROWSER_TOOLS_WITHOUT_SUMMARY,
    CHANNEL_KEY,
    DEFAULT_AGENT_ID,
    EVENT_MESSAGE_PRIVATE,
    KIND_THINKING_STEP,
    KIND_USAGE,
    LOCALFILE_SCHEME,
    MEDIA_MAX_BYTES,
    classify_tool_type,
    classify_tool_verb,
    generate_msg_id,
    guess_mime,
)
from .media import format_file_size

logger = logging.getLogger(__name__)

# 旧版 Hermes 工具进度格式："{emoji} {tool_name}..." 或
# "{emoji} {tool_name}: ..."。不能使用 ``.{1,2}`` 接受任意字符，否则模型
# 正文中的 "🚀 Running ..." 也会被误判并从主消息流剥离。
_HERMES_TOOL_EMOJI_RE = (
    r"(?:⚙️?|🔧|✏️?|✍️?|🔍|🔎|🌐|📄|📖|💻|🐍|🎨|🎬|🔊|👁️?|📚|🧠|📋|"
    r"⏰|🔀|❓)"
)
_TOOL_PROGRESS_RE = re.compile(
    rf'^{_HERMES_TOOL_EMOJI_RE}\s+\w[\w_]*(?:\.\w+)*(?:\.\.\.|:|\()',
    re.UNICODE,
)

# Hermes v0.19 起，内置 terminal / execute_code 会使用友好文案而非原始
# 工具名，例如：
#   "💻 Running curl -s https://wttr.in/Beijing"
#   "🐍 Running code import json"
#   "🔍 Searching the web for 深圳天气"
#   "📄 Reading https://weather.sz.gov.cn/..."
# 这些格式仍是框架的工具进度，不是模型正文。规则必须保持严格，避免将
# 一般回复中的 "Running ..." 误判后从 stream_chunk 中剥离。
_FRIENDLY_TERMINAL_PROGRESS_RE = re.compile(
    r'^💻\s+Running\s+(?!code(?:\s|$))(?P<summary>\S.*)$', re.UNICODE,
)
_FRIENDLY_EXECUTE_CODE_PROGRESS_RE = re.compile(
    r'^🐍\s+Running code\s+(?P<summary>\S.*)$', re.UNICODE,
)
_FRIENDLY_WEB_SEARCH_PROGRESS_RE = re.compile(
    r'^🔍\s+Searching the web for\s+(?P<summary>\S.*)$', re.UNICODE,
)
_FRIENDLY_WEB_EXTRACT_PROGRESS_RE = re.compile(
    r'^📄\s+Reading\s+(?P<summary>https?://\S+)$', re.UNICODE,
)

_FRIENDLY_TOOL_PROGRESS_PATTERNS = (
    (_FRIENDLY_EXECUTE_CODE_PROGRESS_RE, "execute_code"),
    (_FRIENDLY_TERMINAL_PROGRESS_RE, "terminal"),
    (_FRIENDLY_WEB_SEARCH_PROGRESS_RE, "web_search"),
    (_FRIENDLY_WEB_EXTRACT_PROGRESS_RE, "web_extract"),
)

# AgentChat 的 tool_start 是控制帧：content 只承载与前一段正文的视觉分隔，
# 不能携带 Hermes 原始工具文案。原文已通过 thinking_step 的 detail 字段保留。
_TOOL_START_SEPARATOR = "\n\n"

# Tool name extractor — applied AFTER _TOOL_PROGRESS_RE has already matched.
# Captures the tool identifier following the leading emoji (1-2 chars + space).
# Examples:
#   "🔧 exec: lsof -i :9222"          → "exec"
#   "✏️ write_file([...])\n{...}"     → "write_file"
#   "🔍 web_search..."                → "web_search"
#   "🌐 browser_action(...)"          → "browser_action"
# Returns empty string when the pattern unexpectedly fails to match (defensive).
_TOOL_NAME_RE = re.compile(
    rf'^{_HERMES_TOOL_EMOJI_RE}\s+(\w[\w_]*(?:\.\w+)*)',
    re.UNICODE,
)


def _match_friendly_tool_progress(content: str) -> Optional[tuple[str, re.Match[str]]]:
    """匹配 Hermes 已知的友好工具文案，返回工具名和摘要匹配结果。

    不用宽泛的自然语言规则；只有官方已确认的固定前缀、且带有实际摘要时才
    被视为工具进度。未命中返回 ``None``，由旧格式识别或普通正文路径处理。
    """
    for pattern, tool_name in _FRIENDLY_TOOL_PROGRESS_PATTERNS:
        match = pattern.match(content)
        if match:
            return tool_name, match
    return None


def _extract_tool_name(content: str) -> str:
    """Extract the tool name from a tool_progress text. Returns '' on failure.

    兼容 Hermes 的旧工具名文案，以及 v0.19 起的已知友好工具文案。调用方
    必须先通过 ``_is_tool_progress`` 判断；
    解析失败时返回空串，避免影响正常出站链路。
    """
    if not content:
        return ""
    friendly_match = _match_friendly_tool_progress(content)
    if friendly_match:
        return friendly_match[0]
    m = _TOOL_NAME_RE.match(content)
    return m.group(1) if m else ""


def _is_tool_progress(content: str) -> bool:
    """判断文本是否为 Hermes 框架产生的工具进度，而非模型正文。

    仅接受已知的旧格式和 terminal / execute_code 的两种友好文案。该函数是
    ``send`` 与 ``edit_message`` 共用的判定入口，保证两条出站路径的语义一致。
    """
    if not content:
        return False
    return bool(
        _TOOL_PROGRESS_RE.match(content)
        or _match_friendly_tool_progress(content)
    )


# ---------------------------------------------------------------------------
# Tool text summarization (for thinking_step text/detail fields)
# ---------------------------------------------------------------------------
# 与 openclaw thinking-formatter.ts 的 summarizeArgs 等价，但输入不同：
#   - openclaw 拿到的是结构化 args 对象（如 {action:"open",targetUrl:"..."}）
#   - hermes 拿到的是已渲染好的展示文本（如 "🔧 exec: lsof -i :9222" 或
#     "💻 Running curl -s ..."）
# 因此 hermes 这里只能做字符串拆解：去掉前导 emoji + tool_name 之后，
# 再剥离冒号 / 括号 / 省略号等分隔符 → 剩余部分作为 summary。
#
# 输入示例 → summary：
#   "🔧 exec: lsof -i :9222"          → "lsof -i :9222"
#   "✏️ write_file: \"/tmp/a.txt\""   → "/tmp/a.txt"
#   "✏️ write_file([...])\n{...}"     → "[...]\n{...}" 截断到 160 字符
#   "🌐 browser_action(...)"          → "..."
#   "🔍 web_search..."                → "" (省略号本身无信息)
#
# 超长内容会被截断到 160 字符（后接 …），避免占满前端时间线一行。
_SUMMARY_MAX_LEN = 160
# 移除 summary 两侧常见的成对包裹符号（引号 / 括号），让文案更干净。
_QUOTE_PAIRS = (("\"", "\""), ("'", "'"), ("`", "`"))


def _truncate(text: str) -> str:
    if len(text) <= _SUMMARY_MAX_LEN:
        return text
    return f"{text[:_SUMMARY_MAX_LEN]}\u2026"


def _summarize_tool_text(content: str, tool_name: str) -> str:
    """Strip the leading emoji + tool_name + delimiter, return the remainder.

    Used as ``summary`` in running-frame text reformulation:
        "\u6267\u884c\u4e86 ${verb}: ${summary}"
    Returns empty string when there is no informative tail (e.g. "web_search..."
    leaves only an ellipsis).
    """
    if not content or not tool_name:
        return ""

    # Hermes 友好文案中没有原始工具名分隔符，直接取已知格式中的命令 / 代码
    # 摘要。此分支必须早于旧格式的 _TOOL_NAME_RE 解析，否则会把 "Running"
    # 误当作工具名，导致思考卡片丢失命令工具语义。
    friendly_match = _match_friendly_tool_progress(content)
    if friendly_match:
        return _truncate(friendly_match[1].group("summary").strip())

    # 1) Skip past the emoji prefix (matched by _TOOL_NAME_RE: 1-2 chars + space).
    name_match = _TOOL_NAME_RE.match(content)
    if not name_match:
        return ""
    tail = content[name_match.end():]  # tail begins with delimiter or args

    # 2) Strip the leading delimiter that _TOOL_PROGRESS_RE accepted: "..." / ":" / "(".
    tail_stripped = tail.lstrip()
    if tail_stripped.startswith("..."):
        tail_stripped = tail_stripped[3:].lstrip()
    elif tail_stripped.startswith(":"):
        tail_stripped = tail_stripped[1:].lstrip()
    elif tail_stripped.startswith("("):
        # write_file([...])\n{...} \u2014\u2014 keep the parens content as-is for raw view
        tail_stripped = tail_stripped[1:]
        # Drop the matching trailing ")" only when it sits at end of first line.
        line_end = tail_stripped.find("\n")
        head = tail_stripped if line_end == -1 else tail_stripped[:line_end]
        rest = "" if line_end == -1 else tail_stripped[line_end:]
        head = head.rstrip()
        if head.endswith(")"):
            head = head[:-1].rstrip()
        tail_stripped = head + rest

    # 3) Strip surrounding quotes / backticks if any.
    for left, right in _QUOTE_PAIRS:
        if tail_stripped.startswith(left) and tail_stripped.endswith(right) and len(tail_stripped) >= 2:
            tail_stripped = tail_stripped[1:-1]
            break

    return _truncate(tail_stripped.strip())


# Extract the file path from a write_file tool_start progress message.
# This is our MODEL-INDEPENDENT source of the artifact path: the gateway emits
# the tool call as progress text *before* the model writes its final reply, so
# we capture the path here and deliver it ourselves if the (often weak) model
# never echoes it as a MEDIA: tag or bare path that the framework can detect.
# Handles two gateway formats:
#   compact mode:  '✏️ write_file: "/abs/path/to/file"'
#   verbose mode:  "✏️ write_file([...])\n{\"path\": \"/abs/path\"}"
_WRITE_FILE_QUOTED_PATH_RE = re.compile(
    r'\bwrite_file\b.*?["\'`](/[^"\'`\r\n]+)["\'`]',
    re.DOTALL,
)
_WRITE_FILE_PATH_RE = re.compile(
    r'\bwrite_file\b.*?(/[^\r\n,;}{]+)',
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
# 框架要求格式：单独一行 "MEDIA:<绝对路径>"。路径允许包含空格，因此
# 不能再用 ``\S+`` 截取，而应把 MEDIA: 后直到行尾的内容整体视为内部协议。
# 可选的引号 / 反引号用于兼容模型偶尔输出的非标准包裹形式。
#
# 实际文件投递由框架的 _deliver_media_from_response / _deliver_pending_files 负责；
# 此处只负责在任何 stream_chunk 发出前，从用户可见正文中隐藏协议行。
_MEDIA_TAG_RE = re.compile(
    r'^[ \t]*[`"\']?MEDIA:[ \t]*'
    r'(?:[A-Za-z]:[/\\]|/|~/)[^\r\n]*?[`"\']?[ \t]*(?=\r?$)',
    re.MULTILINE,
)

_MEDIA_PREFIX = "MEDIA:"


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


def _normalize_stream_snapshot(text: str, *, finalize: bool = False) -> str:
    """归一化非最终流式帧的 cursor 与 Hermes 临时 Markdown 尾部。

    Hermes v0.20 会先在正文尾部加入 cursor，再为实时预览自动补未闭合的
    代码块 ``\\n``` `` 或 inline-code `` ` ``。这些补齐内容只是当前帧的
    展示辅助，下一帧会被新的正文插到它们之前；若把它们写进本地 snapshot，
    后续累计全文就不再是前缀，追加式协议会永久停止。

    cursor 永远是核心生成的展示字符，最终帧也必须剥离。只有非最终帧才删除
    ``cursor + 临时尾部`` 的组合；最终帧的闭合标记可能是真实结果，必须保留。
    """
    if not text:
        return text

    for cursor in _STREAM_CURSORS:
        if text.endswith(cursor):
            return text[: -len(cursor)]

        if finalize:
            continue

        # ``ensure_closed_code_fences`` 在 cursor 之后追加的临时闭合。代码块
        # 与更早开始的 inline-code 都未闭合时，上游会连续追加两者，因此先
        # 匹配更长的 ``\n`` + 四个反引号组合。
        for transient_tail in ("\n````", "\n```", "`"):
            suffix = f"{cursor}{transient_tail}"
            if text.endswith(suffix):
                return text[: -len(suffix)]
    return text


_FINAL_CODE_FENCE_SUFFIX = "\n```"


def _restore_final_code_fence_blank_lines(content: str, previous: str) -> str:
    """恢复 Hermes 最终自动闭合代码块时压掉的明确尾部空行。

    Hermes v0.20 会以 ``rstrip("\\n") + "\\n```"`` 闭合未结束的代码块。
    单个换行无法区分“被压缩的正文换行”和“模型自行输出闭合 fence 的分隔符”，
    因此只恢复上一帧中至少两个连续换行的情形，避免凭空插入空行。
    """
    if not content.endswith(_FINAL_CODE_FENCE_SUFFIX) or not previous:
        return content

    content_body = content[: -len(_FINAL_CODE_FENCE_SUFFIX)]
    if not previous.startswith(content_body) or content.startswith(previous):
        return content

    compressed_tail = previous[len(content_body) :]
    if len(compressed_tail) < 2 or compressed_tail.strip("\n"):
        return content

    return f"{previous}```"


def _is_partial_media_tag_line(line: str) -> bool:
    """判断流式文本的最后一行是否可能是尚未输出完整的 ``MEDIA:`` 协议行。

    ``GatewayStreamConsumer`` 传入的是不断增长的累计全文，但一次刷新可能恰好
    停在 ``M``、``MEDIA:``、``MEDIA:~`` 或 ``MEDIA:C:``。这些内容如果立即发给
    AgentChat，后面即使完整协议行被过滤，前端也无法撤回已经追加的半截文本。

    返回 ``True`` 表示“先暂存这一行，等待下一份累计全文确认”；返回 ``False``
    表示它不是待确认的协议前缀，可以按普通正文继续处理。若后续内容变成普通文本
    （例如 ``MEDal``），下一次累计快照会把整行正常释放出去。
    """
    # 模型偶尔会先输出缩进或用引号/反引号包住 MEDIA 行。判断协议前缀时先忽略
    # 这些展示字符，但不修改原始 line；确认是普通文本时仍会按原样展示。
    candidate = line.lstrip(" \t")
    if candidate.startswith(("`", '"', "'")):
        candidate = candidate[1:]
    if not candidate:
        return False

    # 注意判断方向：candidate 是完整关键字 "MEDIA:" 的前缀。
    # 因此 M / ME / MED / MEDI / MEDIA / MEDIA: 都需要继续等待。
    if _MEDIA_PREFIX.startswith(candidate):
        return True

    # 连完整的 "MEDIA:" 都不是，例如 "MEDal"，应立即当作普通正文。
    if not candidate.startswith(_MEDIA_PREFIX):
        return False

    # 已经出现 "MEDIA:" 后，只继续暂存“绝对路径起始部分还没写完整”的情况：
    #   MEDIA:      → 还没开始输出路径
    #   MEDIA:~     → 可能继续成为 MEDIA:~/file
    #   MEDIA:C     → 可能继续成为 MEDIA:C:/file 或 MEDIA:C:\\file
    #   MEDIA:C:    → 还在等待 / 或 \\
    # 一旦出现完整的 /、~/、C:/ 或 C:\\ 前缀，就不再属于 partial；完整协议行
    # 会由前面的 _MEDIA_TAG_RE 负责整体删除。
    path_prefix = candidate[len(_MEDIA_PREFIX):].lstrip(" \t")
    if not path_prefix or path_prefix == "~":
        return True
    if len(path_prefix) == 1 and path_prefix.isalpha():
        return True
    return (
        len(path_prefix) == 2
        and path_prefix[0].isalpha()
        and path_prefix[1] == ":"
    )


def _strip_media_tags(text: str, *, finalize: bool = False) -> str:
    """Hide complete and not-yet-complete MEDIA lines before delivery.

    The framework uses ``MEDIA:<absolute-path>`` as an internal protocol to
    signal that a local file should be attached.  The gateway's post-stream
    handlers (_deliver_media_from_response / _deliver_pending_files) consume
    these tags and convert them to proper attachment links.  However, when the
    model outputs ``MEDIA:/path/to/file`` during streaming, the raw text is
    forwarded to the client verbatim before any post-stream processing runs.

    Complete protocol lines are erased while their line endings are preserved.
    A possible protocol prefix at the end of accumulated streaming text is
    withheld until the next snapshot resolves it.  This prevents an early
    ``MEDIA:`` chunk from becoming irreversible in AgentChat's append-only UI.
    """
    if not text:
        return text

    cleaned = _MEDIA_TAG_RE.sub("", text)

    # Only the final unterminated line can still grow in the next accumulated
    # callback.  Keep its preceding newline so paragraph layout remains stable.
    line_start = cleaned.rfind("\n") + 1
    trailing_line = cleaned[line_start:]
    if _is_partial_media_tag_line(trailing_line):
        # At finalization, a bare partial keyword (M / ME / ... / MEDIA)
        # cannot grow into a protocol tag anymore, so release it as ordinary
        # prose.  Keep MEDIA: and incomplete absolute-path prefixes hidden.
        candidate = trailing_line.lstrip(" \t")
        if candidate.startswith(("`", '"', "'")):
            candidate = candidate[1:]
        if (
            finalize
            and candidate != _MEDIA_PREFIX
            and _MEDIA_PREFIX.startswith(candidate)
        ):
            return cleaned
        return cleaned[:line_start]
    return cleaned


class OutboundMixin:
    """
    Mixin providing the full public send API (streaming mode).

    Requires (set by LightClawAdapter):
        self._bot_client_id: str
        self._reliable: ReliableEmitter
        self._round_ids: dict[str, str]
        self._edit_snapshot: dict[str, str]
        self._round_reply_to: dict[str, str]
        self._round_usage_emitted: dict[str, str]
        self._round_terminal_emitted: dict[str, str]
        self._round_chat_ctx: dict[str, tuple[str, str]]
        self._usage_tracker: SessionUsageTracker | None
        self._round_usage_context: dict[str, tuple[SessionUsageTracker, str]]
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

    def _resolve_agent_id(self, chat_id: str) -> str:
        """Resolve current agentId from _round_chat_ctx, with sessions.json fallback."""
        ctx = getattr(self, "_round_chat_ctx", {}).get(chat_id)
        if ctx:
            _, agent_id = ctx
            return agent_id
        try:
            from .history import load_session_store
            store = load_session_store(getattr(self, "_sessions_dir", None))
            if store:
                for sk, entry in store.items():
                    origin = entry.get("origin") if isinstance(entry, dict) else None
                    if not isinstance(origin, dict):
                        continue
                    if str(origin.get("chat_id", "")) != str(chat_id):
                        continue
                    m = re.match(r"^agent:([^:]+):", sk)
                    if m:
                        return m.group(1)
        except Exception:
            pass
        return DEFAULT_AGENT_ID

    def _build_message(
        self,
        to: str,
        content: str,
        kind: str = "text",
        reply_to: Optional[str] = None,
        files: Optional[list] = None,
        msg_id: Optional[str] = None,
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
            "agentId":   self._resolve_agent_id(to),
        }
        if reply_to:
            msg["replyToMsgId"] = reply_to
        if files:
            msg["files"] = files
        # ── 强制注入 extra.chatId ─────────────────────────────
        # 为什么每帧都必须带：前端 use-claw-socket.ts 有个「chatId 闸门」——
        # incomingChatId !== currentChatId → 整条 ws 帧被丢弃。
        # 缺失 extra.chatId 的帧会被判为「另一会话的帧」而全部拦截，
        # 表现是新会话里 stream_chunk / usage 全部不显示。
        #
        # 要传什么值：必须是**业务 chatId**（前端 UUID，如
        # "940a9710-471f-4bb6-a8de-8f60b7f32cba"），不是 UIN。UIN 只是 IM 层
        # 收件人，前端 currentChatId 存的是业务 UUID。默认会话业务 chatId 为
        # 空串，前端 currentChatId 也是空串，自然匹配。
        #
        # 值从哪来：inbound 每轮开始时把 (business_chatId, agentId) 写入
        # _round_chat_ctx[sender]，outbound 这里读出用。ctx 缺失时回退空串
        # （legacy 前端行为），保持向后兼容。
        ctx = self._round_chat_ctx.get(to)
        business_chat_id = ctx[0] if ctx else ""
        merged_extra = {"chatId": business_chat_id}
        if extra is not None:
            merged_extra.update(extra)
        msg["extra"] = merged_extra
        if passthrough:
            msg.update(passthrough)
        return msg

    def _get_or_create_round_id(self, chat_id: str) -> str:
        if chat_id not in self._round_ids:
            self._round_ids[chat_id] = generate_msg_id()
        return self._round_ids[chat_id]

    def _clear_round_id(self, chat_id: str) -> None:
        self._round_ids.pop(chat_id, None)

    async def _emit_typing_stop_once(
        self,
        chat_id: str,
        round_msg_id: str,
        *,
        reason: str,
    ) -> bool:
        """可靠发送一轮的结束帧，保证同一 ``msgId`` 至多发送一次。

        只有 ``stop_typing`` 才会调用本方法。前端收到 ``typing_stop`` 后才会
        将消息从 ``updating`` 收敛到 ``success``，进而允许切换会话时写入
        内存快照；流分段的 ``finalize=True`` 不得提前关闭整轮。
        """
        if self._round_terminal_emitted.get(chat_id) == round_msg_id:
            return True

        payload = self._build_message(
            chat_id,
            "",
            kind="typing_stop",
            msg_id=round_msg_id,
        )
        if not await self._emit_reliable(EVENT_MESSAGE_PRIVATE, payload):
            logger.warning(
                "[lightclaw] typing_stop was not acknowledged: "
                "to=%s msgId=%s reason=%s",
                chat_id,
                round_msg_id,
                reason,
            )
            return False

        self._round_terminal_emitted[chat_id] = round_msg_id
        logger.info(
            "[lightclaw] typing_stop acknowledged: to=%s msgId=%s reason=%s",
            chat_id,
            round_msg_id,
            reason,
        )
        return True

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

    def _usage_context_for_chat(
        self,
        chat_id: str,
    ) -> Tuple[object, Optional[str]]:
        """返回本轮绑定的 token tracker 与 sessions 目录，缺失时兼容主角色。"""
        context = getattr(self, "_round_usage_context", {}).get(chat_id)
        if context:
            return context
        return (
            getattr(self, "_usage_tracker", None),
            getattr(self, "_sessions_dir", None),
        )

    def _resolve_session_id_for_chat(
        self,
        chat_id: str,
        *,
        sessions_dir: Optional[str] = None,
    ) -> Optional[str]:
        """Look up the Hermes ``session_id`` for *chat_id* (the sender UIN).

        必须与 inbound._build_session_key 输出**字节级一致**，否则 sessions.json
        查不到对应 entry，``_persist_turn_usage`` 拿不到 session_id → usage sidecar
        无法落盘 → 历史回放 token 永久丢失。

        inbound 的 sessionKey 格式：
          ``agent:{agent_id}:{CHANNEL_KEY}:dm:{sender}[:{business_chat_id}]``

        本轮的 ``(business_chat_id, agent_id)`` 由 inbound 在每轮开始时写入
        ``_round_chat_ctx[sender]``。该上下文缺失（首轮预热 / 进程重启 /
        framework-routed follow-up）时回退到不带 chatId 后缀的 legacy 形式，
        与历史单 session 路径行为保持一致。
        """
        sessions_dir = sessions_dir or getattr(self, "_sessions_dir", None)
        # 子角色的 state.db 位于子 Home，但 v0.20+ Gateway 启动时创建的
        # SessionStore 仍可能继续把 sessions.json 维护在主 Home。正文/token
        # 读取与 sidecar 写入仍使用传入的子 sessions_dir；这里只为 sessionId
        # 映射准备子→主的只读候选索引目录。
        index_sessions_dirs: list[str] = []
        for directory in (sessions_dir, getattr(self, "_sessions_dir", None)):
            if not directory:
                continue
            canonical_dir = os.path.realpath(directory)
            if canonical_dir not in index_sessions_dirs:
                index_sessions_dirs.append(canonical_dir)

        ctx = getattr(self, "_round_chat_ctx", {}).get(chat_id)
        if ctx:
            business_chat_id, agent_id = ctx
        else:
            business_chat_id, agent_id = "", DEFAULT_AGENT_ID

        # 修复：当 _round_chat_ctx 为空时（进程重启 / 首轮预热），
        # 扫描 sessions.json 按 origin.chat_id 反查 business_chat_id。
        # 此场景下当前调用方的 session_id 为 None，但业务 chatId 可从
        # sessions.json 的条目中推断——遍历所有 entry，找到 origin.chat_id
        # 与当前 chat_id 匹配且 origin.thread_id 非空的条目，取其
        # origin.thread_id 作为 business_chat_id。
        # 这是新建会话场景下唯一可靠的 chatId 来源（首轮预热阶段
        # inbound 尚未执行，_round_chat_ctx 还未被写入）。
        if not ctx and business_chat_id == "":
            try:
                from .history import load_session_store
                for index_sessions_dir in index_sessions_dirs:
                    store = load_session_store(index_sessions_dir)
                    if not store:
                        continue
                    for _sk, _entry in store.items():
                        _origin = _entry.get("origin") if isinstance(_entry, dict) else None
                        if not isinstance(_origin, dict):
                            continue
                        # origin.chat_id 存的是 sender UIN，必须与当前 chat_id 匹配
                        if str(_origin.get("chat_id", "")) != str(chat_id):
                            continue
                        # origin.thread_id 是业务 chatId（chats.json 中的 UUID）
                        # 仅当非空时才有意义——默认会话的 thread_id 为 None/空。
                        _thread_id = _origin.get("thread_id") or ""
                        if _thread_id:
                            business_chat_id = _thread_id
                            # 同时从该条目中恢复 agent_id（如果非默认）
                            _agent_id = _entry.get("session_key", "")
                            # session_key 格式：agent:{agent_id}:{CHANNEL_KEY}:dm:{sender}[:{chatId}]
                            _agent_id_match = re.match(
                                r'^agent:([^:]+):', _agent_id
                            ) if _agent_id else None
                            if _agent_id_match:
                                agent_id = _agent_id_match.group(1)
                            logger.debug(
                                "[lightclaw][usage] _resolve_session_id_for_chat "
                                "fallback from sessions.json: sender=%s "
                                "business_chat_id=%s agent_id=%s index_dir=%s",
                                chat_id, business_chat_id, agent_id, index_sessions_dir,
                            )
                            break
                    if business_chat_id:
                        break
            except Exception as _exc:
                logger.debug(
                    "[lightclaw] sessions.json scan for business_chat_id failed: %s",
                    _exc,
                )

        # 候选 key 顺序：精确匹配优先。非 main agent 的默认会话带
        # __default_{agent_id} 后缀，必须在无后缀的通用 key 之前尝试，
        # 否则会被 agent:main:...dm:chat_id 先匹配到 main 的默认 session。
        candidate_keys = []
        if business_chat_id:
            candidate_keys.append(
                f"agent:{agent_id}:{CHANNEL_KEY}:dm:{chat_id}:{business_chat_id}"
            )
        candidate_keys.append(f"agent:{agent_id}:{CHANNEL_KEY}:dm:{chat_id}")
        if agent_id != DEFAULT_AGENT_ID:
            if business_chat_id:
                candidate_keys.append(
                    f"agent:{DEFAULT_AGENT_ID}:{CHANNEL_KEY}:dm:{chat_id}:{business_chat_id}"
                )
            # 非 main agent 默认会话：精确 key 先于通用 key
            if not business_chat_id:
                candidate_keys.append(
                    f"agent:{DEFAULT_AGENT_ID}:{CHANNEL_KEY}:dm:{chat_id}:__default_{agent_id}"
                )
            candidate_keys.append(
                f"agent:{DEFAULT_AGENT_ID}:{CHANNEL_KEY}:dm:{chat_id}"
            )

        try:
            from .history import load_session_store
        except ImportError:
            return None

        for index_sessions_dir in index_sessions_dirs:
            store = load_session_store(index_sessions_dir)
            if not store:
                continue

            # 大小写不敏感的反查表（每个索引目录构建一次），覆盖
            # sessions.json 中 key 大小写差异的边界场景。
            lower_index: Optional[dict] = None
            for session_key in candidate_keys:
                entry = store.get(session_key)
                if entry is None:
                    if lower_index is None:
                        lower_index = {k.lower(): v for k, v in store.items()}
                    entry = lower_index.get(session_key.lower())
                if not entry:
                    continue
                # Support both snake_case (lighthouse-hermes) and camelCase (openclaw)
                session_id = entry.get("session_id") or entry.get("sessionId") or None
                if session_id:
                    logger.info(
                        "[lightclaw][usage] session index resolved: sender=%s "
                        "session_id=%s index_dir=%s state_sessions_dir=%s",
                        chat_id, session_id, index_sessions_dir, sessions_dir,
                    )
                    return session_id
        return None

    def _resolve_usage_log_path(
        self,
        chat_id: str,
        *,
        session_id: Optional[str] = None,
        sessions_dir: Optional[str] = None,
    ) -> Optional[str]:
        """Return absolute path of the usage sidecar jsonl for this chat.

        Returns ``None`` if we can't yet locate the session (best-effort).

        ``session_id`` 可由调用方预先解析后透传，避免在 stop_typing 路径上
        重复扫描 sessions.json（``classify_turn`` 已经解析过一次）。
        """
        sessions_dir = sessions_dir or getattr(self, "_sessions_dir", None)
        if not sessions_dir:
            return None
        if not session_id:
            session_id = self._resolve_session_id_for_chat(
                chat_id, sessions_dir=sessions_dir,
            )
        if not session_id:
            return None
        return os.path.join(sessions_dir, f"{session_id}.usage.jsonl")

    def _persist_turn_usage(
        self,
        chat_id: str,
        round_msg_id: str,
        usage: Optional[Dict[str, Any]],
        *,
        session_id: Optional[str] = None,
        sessions_dir: Optional[str] = None,
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
            log_path = self._resolve_usage_log_path(
                chat_id, session_id=session_id, sessions_dir=sessions_dir,
            )
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

        # Sanitize at the common entry point so every downstream branch
        # (round-open / reuse-last-round / standalone / attachment link) sees
        # the same user-visible text.  In particular, the first streaming
        # chunk must not bypass the MEDIA filter that edit_message() applies.
        content = _strip_media_tags(_normalize_stream_snapshot(content))

        # ── Round already open (inbound sent typing_start) ──
        round_msg_id = self._round_ids.get(chat_id)
        if round_msg_id:
            is_tool_progress = bool(
                content and len(content) < 500 and _is_tool_progress(content)
            )
            msg_kind = "tool_start" if is_tool_progress else "stream_chunk"

            # 同一轮的 stream_chunk 是累计回复的增量，前端会直接拼接；不能
            # 为后续分片补换行，否则上游若按行调用 send() 会变成每行一个空行。
            should_emit = msg_kind == "tool_start" or bool(content.strip())

            logger.info(
                "[lightclaw] send (%s, round open): to=%s msgId=%s content=%d chars",
                msg_kind, chat_id, round_msg_id, len(content),
            )
            if should_emit:
                self._fire_and_forget(
                    EVENT_MESSAGE_PRIVATE,
                    self._build_message(
                        chat_id,
                        _TOOL_START_SEPARATOR if is_tool_progress else content,
                        kind=msg_kind,
                        msg_id=round_msg_id,
                    ),
                )

            # Track write_file tool_start paths for the stop_typing() fallback.
            if is_tool_progress:
                self._track_write_file_path(chat_id, content)
                # 并发一帧 thinking_step (running)，给前端做行级时间线展示。
                agent_id = self._resolve_agent_id(chat_id)
                self._emit_thinking_step_running(
                    chat_id, round_msg_id, agent_id, content,
                )

            # ``content`` 已在入口统一清洗，直接记录用户可见快照，供
            # edit_message() 对后续累计全文计算增量。
            if msg_kind == "stream_chunk":
                self._edit_snapshot[chat_id] = content

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
                content and len(content) < 500 and _is_tool_progress(content)
            )
            msg_kind = "tool_start" if is_tool_progress else "stream_chunk"
            # 这是已结束轮次后的独立补充（如附件链接），与当前轮的连续流式
            # 分片不同；保留段落分隔，避免链接直接黏连到已经展示的正文末尾。
            should_emit = msg_kind == "tool_start" or bool(content.strip())
            actual_content = (
                _TOOL_START_SEPARATOR if is_tool_progress else "\n\n" + content
            )
            logger.info(
                "[lightclaw] send (%s, reuse last round): to=%s msgId=%s content=%d chars",
                msg_kind, chat_id, last_round_id, len(content),
            )
            if should_emit:
                self._fire_and_forget(
                    EVENT_MESSAGE_PRIVATE,
                    self._build_message(
                        chat_id, actual_content, kind=msg_kind,
                        msg_id=last_round_id,
                    ),
                )
            # 与 round-open 分支一致：并发一帧 thinking_step (running)。
            # 复用 last_round_id 作为 msgId，保证后续附件链接与同一 round 聚合。
            if is_tool_progress:
                agent_id = self._resolve_agent_id(chat_id)
                self._emit_thinking_step_running(
                    chat_id, last_round_id, agent_id, content,
                )
            # Keep the reservation alive — more follow-ups may still arrive
            # before the next inbound (e.g. caption + attachment link).
            return SendResult(success=True, message_id=last_round_id)

        # ── No round open (standalone message) ──
        round_msg_id = self._get_or_create_round_id(chat_id)

        is_tool_progress = bool(
            content and len(content) < 500 and _is_tool_progress(content)
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
                    chat_id, _TOOL_START_SEPARATOR, kind="tool_start",
                    msg_id=round_msg_id,
                ),
            )
            # 同样并发一帧 thinking_step (running)，保持与另两条分支行为一致。
            agent_id = self._resolve_agent_id(chat_id)
            self._emit_thinking_step_running(
                chat_id, round_msg_id, agent_id, content,
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
                                msg_id=round_msg_id),
        )
        if content.strip():
            self._fire_and_forget(
                EVENT_MESSAGE_PRIVATE,
                self._build_message(
                    chat_id, content, kind="stream_chunk",
                    msg_id=round_msg_id,
                ),
            )
        self._fire_and_forget(
            EVENT_MESSAGE_PRIVATE,
            self._build_message(chat_id, "", kind="typing_stop",
                                msg_id=round_msg_id),
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

    def _finalize_round_usage(
        self,
        chat_id: str,
        round_msg_id: str,
        *,
        persist_unknown: bool,
    ) -> bool:
        """在整轮 ``stop_typing`` 回调中结算 token，按 msgId 幂等去重。"""
        usage_tracker, usage_sessions_dir = self._usage_context_for_chat(chat_id)
        if usage_tracker is None:
            return False
        if self._round_usage_emitted.get(chat_id) == round_msg_id:
            return True

        # 先解析一次 session_id：classify_turn 用它从 state.db 精确取行（避免
        # 多 chat 共用 sender 时拿到错行），_persist_turn_usage 用同一个值
        # 拼出 sidecar 路径——两者必须用同一个 session_id 才能保证写下来的
        # sidecar 和历史回放读到的文件一致。
        turn_session_id = self._resolve_session_id_for_chat(
            chat_id, sessions_dir=usage_sessions_dir,
        )
        logger.info(
            "[lightclaw][usage] finalize resolve: sender=%s "
            "round_chat_ctx=%s sessions_dir=%s resolved_session_id=%s",
            chat_id,
            self._round_chat_ctx.get(chat_id),
            usage_sessions_dir,
            turn_session_id,
        )
        # Baseline relabel（方案 A + D 的收尾，含 session reset 兜底）：
        # inbound 阶段调用 mark_new_session_baseline / snapshot_baseline
        # 时，`baseline_session_id` 可能为 None；此处 sessionId 已可稳定解析。
        # 不能重新读 state.db 复位 baseline：LLM 已跑过，累计值已包含本轮输入，
        # 重读会把「起点 + 本轮消耗」当成起点，delta 归零，本轮 token 永久丢失。
        if turn_session_id:
            try:
                # 先尝试常规 legacy→turn_sid relabel（幂等，若已就位或无源都是 no-op）
                usage_tracker.correct_baseline_after_session_id(
                    chat_id,
                    old_session_id=None,
                    new_session_id=turn_session_id,
                )
                # 若 relabel 后 turn_sid 下仍无 baseline，说明既没有 legacy 源
                # 也没有预置 baseline，唯一可能就是 session reset：inbound 时
                # 拿到的 old_sid 与 stop_typing 的 new_sid 不同。此时按 reset
                # 语义处理——落零 baseline + 清 sender/chat 下的过期 baseline。
                if not usage_tracker.has_baseline_for_session(
                    chat_id, turn_session_id,
                ):
                    logger.info(
                        "[lightclaw][usage] session reset detected in "
                        "finalize: chat_id=%s turn_session_id=%s",
                        chat_id, turn_session_id,
                    )
                    usage_tracker.handle_session_reset(
                        chat_id, new_session_id=turn_session_id,
                    )
            except Exception as _exc:
                logger.debug(
                    "[lightclaw] usage baseline reconcile failed: %s", _exc,
                )
        usage, usage_reason = usage_tracker.classify_turn(
            chat_id, session_id=turn_session_id,
        )
        logger.info(
            "[lightclaw][usage] finalize classify: sender=%s "
            "sessions_dir=%s session_id=%s reason=%s",
            chat_id, usage_sessions_dir, turn_session_id, usage_reason,
        )
        if usage is not None:
            logger.info(
                "[lightclaw] emit usage: to=%s msgId=%s input=%s output=%s total=%s",
                chat_id, round_msg_id,
                usage.get("inputTokens"),
                usage.get("outputTokens"),
                usage.get("totalTokens"),
            )
            # extra.chatId 必须等于本轮 inbound 收到的业务 chatId，前端才会
            # 将 usage 帧更新到当前打开的会话。
            ctx_chat = self._round_chat_ctx.get(chat_id)
            business_chat_id = ctx_chat[0] if ctx_chat else ""
            self._fire_and_forget(
                EVENT_MESSAGE_PRIVATE,
                self._build_message(
                    chat_id, "", kind=KIND_USAGE,
                    msg_id=round_msg_id,
                    reply_to=self._round_reply_to.get(chat_id),
                    extra={"chatId": business_chat_id, "usage": usage},
                ),
            )
            self._persist_turn_usage(
                chat_id=chat_id,
                round_msg_id=round_msg_id,
                usage=usage,
                session_id=turn_session_id,
                sessions_dir=usage_sessions_dir,
            )
        elif usage_reason == "unknown":
            if not persist_unknown:
                logger.info(
                    "[lightclaw][usage] finalize deferred: sender=%s msgId=%s",
                    chat_id, round_msg_id,
                )
                return False
            # 无法测量不代表免费；Core 回调作为最终兜底时写空占位，保持
            # 历史 usage sidecar 与回答轮次的序号对齐。
            logger.info(
                "[lightclaw] usage placeholder (unmeasurable turn): to=%s msgId=%s",
                chat_id, round_msg_id,
            )
            self._persist_turn_usage(
                chat_id=chat_id,
                round_msg_id=round_msg_id,
                usage=None,
                session_id=turn_session_id,
                sessions_dir=usage_sessions_dir,
            )
        else:
            # usage_reason == "no_llm"：命令回显而非模型对话，不写 sidecar，
            # 避免产生会挤占后续真实回答的伪 usage 条目。
            logger.info(
                "[lightclaw] usage skipped (no LLM turn, no sidecar entry): "
                "to=%s msgId=%s",
                chat_id, round_msg_id,
            )
        # Mark emitted (even if no frame was sent) to skip later
        # finalize / stop_typing calls for this round.
        self._round_usage_emitted[chat_id] = round_msg_id
        return True

    async def stop_typing(self, chat_id: str, **kwargs: Any) -> None:
        """Stop typing indicator — 处理兜底任务并关闭当前轮次。"""
        round_msg_id = self._round_ids.get(chat_id)
        if not round_msg_id:
            return

        # Fallback: deliver any write_file outputs not covered by model MEDIA:
        # tags / framework path-detection.  Must run BEFORE typing_stop so
        # attachment links land in the same bubble.
        await self._deliver_pending_files(chat_id)

        # ``stop_typing`` 是整轮终态，state.db 已有机会完成落盘；无法测量时
        # 才写 unknown 占位，保持历史 usage 与回答轮次对齐。
        self._finalize_round_usage(
            chat_id, round_msg_id, persist_unknown=True,
        )

        await self._emit_typing_stop_once(
            chat_id,
            round_msg_id,
            reason="core-stop-typing",
        )
        # Reserve the msgId for any post-stop_typing follow-up output
        # (typically: attachment markdown links).  Cleared by inbound on
        # the next turn.
        self._last_round_id[chat_id] = round_msg_id
        self._edit_snapshot.pop(chat_id, None)
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

        ``finalize=True`` 只表示当前流分段结束，不能据此发送 ``typing_stop``
        或结算 usage；Hermes 也会在工具调用前与 overflow 分段使用它。整轮
        终态由 Core 随后的 ``stop_typing`` 统一发送，前端才会缓存消息。

        Tool progress edits (message_id != round_msg_id) are ignored.
        """
        # 1. 归一化非最终帧的 cursor 与 v0.20 临时 Markdown 闭合尾部。
        content = _normalize_stream_snapshot(content, finalize=finalize)

        # 1b. 去除 MEDIA: 协议行——模型可能在流式输出时将其作为普通文本输出；这些是内部投递标记，不应展示给用户。
        #     文件投递由_deliver_media_from_response / _deliver_pending_files 单独处理。
        content = _strip_media_tags(content, finalize=finalize)

        # 2. Only process edits matching the current round (filter tool progress edits)
        round_msg_id = self._round_ids.get(chat_id)
        if not round_msg_id or round_msg_id != message_id:
            return SendResult(success=True, message_id=message_id)

        # 3. Compute delta
        previous = self._edit_snapshot.get(chat_id, "")
        if finalize:
            # 最终帧的自动 fence 闭合会压缩末尾换行；先恢复可确定的空行，
            # 才能继续走追加式 delta，避免前端保留半截代码块。
            content = _restore_final_code_fence_blank_lines(content, previous)
        if content.startswith(previous):
            delta = content[len(previous):]
            # 只有严格前缀扩展才能映射为前端的追加操作；即使本帧无新增文本，
            # 同步 snapshot 也能保持与 Hermes 的累计正文一致。
            should_advance_snapshot = True
        elif previous.startswith(content):
            # 前端只支持追加，无法撤回已经显示的内容；纯收缩时不发送，
            # 并保留旧快照，等后续内容重新覆盖已下发边界后再继续计算增量。
            delta = ""
            should_advance_snapshot = False
            logger.warning(
                "[lightclaw] edit_message snapshot shrank, suppressed: to=%s msgId=%s "
                "previous=%d chars, content=%d chars",
                chat_id, round_msg_id, len(previous), len(content),
            )
        else:
            # 前端不支持替换或撤回已展示正文。重发新全文会与旧内容并列，形成
            # 可见重复；因此本帧不下发也不推进 snapshot，等待上游恢复为前缀扩展。
            delta = ""
            should_advance_snapshot = False
            logger.warning(
                "[lightclaw] edit_message delta mismatch, suppressed: "
                "to=%s msgId=%s previous=%d chars content=%d chars",
                chat_id, round_msg_id, len(previous), len(content),
            )

        # 4. Deliver residual delta (if any) and keep snapshot in sync.
        #
        # 方案 B（剥离）：扫描 delta 中的"工具进度行"，将其从 stream_chunk
        # 文本流中剥离，并旁路并发一帧 thinking_step (running)。这样前端
        # 主气泡的 stream_chunk 不再包含 emoji 工具行噪声，时间线视图
        # （thinking_step）独立承载工具调用展示。
        #
        # snapshot 仍保存"未剥离"的原始累积全文（content），因为下一次
        # hermes 推过来的累积全文也含工具行，必须保持一致才能正确算 delta。
        # 剥离仅作用于"本次实际下发的 delta"，是纯输出层裁剪，不污染状态。
        agent_id = self._resolve_agent_id(chat_id)
        cleaned_delta = delta
        tool_lines_count = 0
        if delta:
            kept_lines: list[str] = []
            for line in delta.split("\n"):
                line_stripped = line.strip()
                if (
                    line_stripped
                    and len(line_stripped) < 500
                    and _is_tool_progress(line_stripped)
                ):
                    # 工具进度行：旁路发 thinking_step (running)，不进 stream_chunk
                    self._emit_thinking_step_running(
                        chat_id, round_msg_id, agent_id, line_stripped,
                    )
                    tool_lines_count += 1
                else:
                    kept_lines.append(line)

            cleaned_delta = "\n".join(kept_lines)
            # 剥离后若仍有非空内容，作为 stream_chunk 下发；
            # 全是工具行（cleaned_delta 仅余空白/空字符串）则不发 stream_chunk。
            # 注：不显式传 agent_id ——_build_message 已硬编码
            # agentId=DEFAULT_AGENT_ID，通过 **passthrough 泄漏会在消息帧顶层
            # 产出前端不识别的 "agent_id" 字段。
            if cleaned_delta.strip():
                payload = self._build_message(
                    chat_id, cleaned_delta, kind="stream_chunk",
                    msg_id=round_msg_id,
                )
                if finalize:
                    # 最后一个正文增量必须等 ACK；失败要返回给 Hermes 触发其
                    # 官方 fallback，而不是让 History 与实时消息继续分叉。
                    if not await self._emit_reliable(EVENT_MESSAGE_PRIVATE, payload):
                        return SendResult(
                            success=False,
                            message_id=message_id,
                            error="final stream_chunk was not acknowledged",
                            retryable=True,
                        )
                else:
                    self._fire_and_forget(EVENT_MESSAGE_PRIVATE, payload)

            # 仅在本帧可安全追加时推进 snapshot。收缩或重写无法在追加协议中
            # 表达，保留旧边界，避免下一帧在错误位置继续追加或整段重复。
            if should_advance_snapshot:
                self._edit_snapshot[chat_id] = content

        if finalize:
            logger.info(
                "[lightclaw] edit_message finalize (segment closed; "
                "round retained for terminal stop_typing): to=%s msgId=%s delta=%d chars "
                "(tool_lines=%d, stream_chunk=%d chars)",
                chat_id, round_msg_id, len(delta),
                tool_lines_count, len(cleaned_delta),
            )
        else:
            logger.info(
                "[lightclaw] edit_message: to=%s msgId=%s delta=%d chars "
                "(tool_lines=%d, stream_chunk=%d chars), content_tail='%s'",
                chat_id, round_msg_id, len(delta),
                tool_lines_count, len(cleaned_delta),
                content[-40:] if content else "",
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

        # Encode the URI path so spaces, CJK, parentheses and literal ``%``
        # remain one Markdown destination.  The download handler decodes it
        # exactly once before touching the filesystem.
        encoded_path = quote(abs_path, safe="/")
        link = f"📎 [{display_name}]({LOCALFILE_SCHEME}{encoded_path})"
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

    # ------------------------------------------------------------------
    # Thinking step (kind='thinking_step') emission helper
    # ------------------------------------------------------------------
    #
    # 与 `tool_start` 帧并发派生一帧 `thinking_step (status=running)`，承载
    # agent "思考过程" 的行级时间线展示。
    #
    # 设计要点：
    #   1. 不替代 tool_start，而是并排发送 \u2014\u2014 旧前端忽略未知 kind 即可平滑兼容。
    #   2. 阶段一只发 running 帧（hermes 框架未暴露工具结束钩子，无法可靠
    #      生成 done 帧）。前端建议持续 spinner，直到下一个 running 出现或
    #      typing_stop 抵达视为整轮结束。
    #   3. type 字段做"是否 browser"二分类（Web 据此决定是否打开浏览器云桌面）。
    #   4. text 字段原样透传 hermes 已渲染好的 progress 文本（含 emoji 与
    #      参数摘要），不做二次解析、避免在插件层重做 args summarization。
    #   5. 复用 round_msg_id：与同轮的 stream_chunk / tool_start 用同一
    #      msgId，保证前端把整轮内容聚合到同一个 bubble。

    def _emit_thinking_step_running(
        self,
        chat_id: str,
        round_msg_id: str,
        agent_id: str,
        content: str,
    ) -> None:
        """Derive and emit one ``thinking_step (running)`` frame from the
        tool progress text already accepted by ``_TOOL_PROGRESS_RE``.

        Caller responsibility: only invoke when ``is_tool_progress`` is True
        and a valid ``round_msg_id`` is in scope.
        """
        # 跨调用路径去重（方案 1 / 去重集）：
        #
        # 同一条工具进度行可能从多条路径到达本函数：
        #   1. send() round-open / reuse-last-round / no-round 三处分支
        #      （hermes 把工具进度作为整条消息推送）；
        #   2. edit_message() 内 delta 行级剥离
        #      （hermes 流式累积全文里夹带工具进度行）。
        # 在多工具串行场景下，send() 触发后 _edit_snapshot 不会被 tool_start
        # 分支更新，下次 edit_message 算 delta 时会把该工具行再次纳入剥离循环
        # → 同一行会被发两次。
        #
        # 此处以"工具行原文"为 key 做幂等：本轮（per-turn）已发过则直接返回，
        # 不消耗 stepId / seq，也不发帧。集合在 inbound 收到新 round 时清空。
        line_key = (content or "").strip()
        if line_key:
            seen = self._emitted_tool_lines.setdefault(chat_id, set())
            if line_key in seen:
                logger.info(
                    "[lightclaw] thinking_step dedup skip: to=%s msgId=%s "
                    "line='%s'",
                    chat_id, round_msg_id,
                    line_key[:60] + ("..." if len(line_key) > 60 else ""),
                )
                return
            seen.add(line_key)

        tool_name = _extract_tool_name(content)
        step_type = classify_tool_type(tool_name)
        verb = classify_tool_verb(tool_name)
        summary = _summarize_tool_text(content, tool_name)

        # 无副词类 browser 工具（截图/滚动/返回/前进/刷新/关闭等）：verb 自身
        # 已说清楚动作语义，SDK 在冒号后给的多为内部句柄（page-5 / frame-7）。
        # 此处强制丢弃 summary，避免出现 "执行了 页面截图: 5" 这类劣化文案。
        # 与 openclaw thinking-formatter.ts BROWSER_ACTION_VERBS 中无 summary
        # 行为的 action 一致。
        if tool_name and tool_name.lower() in BROWSER_TOOLS_WITHOUT_SUMMARY:
            summary = ""

        # 自增计数器（per-chat、per-turn；inbound 在新一轮开始时清零）
        n = self._step_count.get(chat_id, 0) + 1
        seq = self._step_seq.get(chat_id, 0) + 1
        self._step_count[chat_id] = n
        self._step_seq[chat_id] = seq

        step_id = f"step-{n}-{tool_name or 'unknown'}"

        # 文案重组：与 openclaw thinking-formatter.ts buildRunningStep 视觉对齐。
        #   summary 命中 → "执行了 ${verb}: ${summary}"
        #   summary 为空 → 仅 "执行了 ${verb}"（如 "🔍 web_search..." 这类无尾文本）
        # detail 取冒号/括号后的原始片段，给前端折叠展开使用；空则不暴露字段语义。
        text = f"执行了 {verb}: {summary}" if summary else f"执行了 {verb}"

        step = {
            "stepId":   step_id,
            "seq":      seq,
            "type":     step_type,
            "text":     text,
            "status":   "running",
            "toolName": tool_name,
            "detail":   summary,
        }

        # 缓存最近一次 running 帧的元信息，阶段二的 done 帧合并将以此为锚点。
        self._last_tool_step[chat_id] = {
            "stepId":   step_id,
            "seq":      seq,
            "toolName": tool_name,
            "type":     step_type,
        }

        logger.info(
            "[lightclaw] thinking_step (running): to=%s msgId=%s "
            "stepId=%s seq=%d type=%s tool=%s raw=%r",
            chat_id, round_msg_id, step_id, seq, step_type, tool_name,
            content[:200] + ("..." if len(content) > 200 else ""),
        )

        self._fire_and_forget(
            EVENT_MESSAGE_PRIVATE,
            self._build_message(
                chat_id, "",
                kind=KIND_THINKING_STEP,
                msg_id=round_msg_id,
                # agentId 由 _build_message 自动从 _round_chat_ctx 解析
                #
                # 注：extra 里不写 chatId ——
                # _build_message 会自动从 _round_chat_ctx 注入正确的业务 chatId
                # （见 _build_message 的 `merged_extra` 逻辑）。这里显式写空串
                # 会**覆盖**自动注入，让前端 chatId 闸门在新建会话中拦截本帧，
                # thinking_step 与本次修复的 usage 帧犯同样的错。
                extra={"step": step},
            ),
        )

    def _track_write_file_path(self, chat_id: str, content: str) -> None:
        """Extract and stash the file path from a write_file tool_start message."""
        if "write_file" not in content:
            return
        path: Optional[str] = None

        # Prefer the explicit JSON field in verbose mode; unlike the old
        # whitespace-delimited matcher it preserves spaces in file names.
        if '"path"' in content:
            m_json = _JSON_PATH_RE.search(content)
            if m_json:
                path = m_json.group(1)

        # Compact mode normally quotes the path.  Keep an unquoted fallback
        # that treats the rest of that line as the path, matching MEDIA's
        # "whole remaining line" rule.
        if not path:
            m_quoted = _WRITE_FILE_QUOTED_PATH_RE.search(content)
            if m_quoted:
                path = m_quoted.group(1)
        if not path:
            m = _WRITE_FILE_PATH_RE.search(content)
            if m:
                path = m.group(1)
        if path:
            path = path.strip().rstrip("\"',;:.)}]")

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
