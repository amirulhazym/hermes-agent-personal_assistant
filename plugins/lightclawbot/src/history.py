"""
LightClaw history — read session transcripts and return history messages.
Mirrors: src/history/ (session-store.ts, message-parser.ts, session-reader.ts,
text-processing.ts).

Storage note: since Hermes "spec 002" the message transcript lives in SQLite
(``~/.hermes/state.db`` → table ``messages``), not in per-session ``.jsonl``
files.  ``sessions.json`` survives in both eras as a ``session_key →
session_id`` index.

To stay compatible with BOTH the new and the legacy builds we read in two
tiers (see ``read_session_history``):
  1. SQLite via :class:`hermes_state.SessionDB` (new builds).
  2. Per-session ``<session_id>.jsonl`` transcript files (legacy builds, or
     when SessionDB is unavailable / returns nothing).
"""

import hashlib
import json
import logging
import mimetypes
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from .config import LOCALFILE_SCHEME

logger = logging.getLogger(__name__)

# Types that are NOT chat messages — skip when parsing legacy JSONL lines.
_SKIP_LINE_TYPES = frozenset({
    "session", "model_change", "thinking_level_change", "custom",
})


# ---------------------------------------------------------------------------
# File attachment extraction (mirrors history/text-processing.ts)
# ---------------------------------------------------------------------------

# "用户发送了文件: filename (size)"
_USER_FILE_DESC_RE = re.compile(
    r"用户发送了文件:\s*(?P<name>.+?)\s*\((?P<size>[^)]+)\)"
)

# "[media attached: <path> (<mime>) | <uri>]"
# Path may contain spaces (CJK filenames) so we use [^\]]+ for the URI part.
_MEDIA_ATTACH_RE = re.compile(
    r"\[media attached:\s*(?P<path>\S+)\s*"
    r"\((?P<mime>[^)]+)\)\s*"
    r"\|\s*(?P<uri>[^\]]+?)\s*\]"
)

_TRAILING_HASH_RE = re.compile(r"---[0-9a-f-]+\.")


def extract_file_attachments(text: str) -> List[Dict[str, str]]:
    """Recover file attachment info from a previously-rendered message body.

    Returns a list of ``{name, mimeType?, size?, uri?}`` dicts, ordered as
    in TS ``extractFileAttachments``: first pass extracts entries from
    ``"用户发送了文件: ..."`` descriptions, then a second pass enriches
    them (in order) with the ``[media attached: ...]`` markers' MIME/URI
    fields, finally appending unmatched markers as standalone entries.
    """
    if not text:
        return []

    files: List[Dict[str, str]] = []

    for m in _USER_FILE_DESC_RE.finditer(text):
        files.append({"name": m.group("name").strip(),
                      "size": m.group("size").strip()})

    media_idx = 0
    for m in _MEDIA_ATTACH_RE.finditer(text):
        mime = m.group("mime").strip()
        uri  = m.group("uri").strip()
        if media_idx < len(files):
            files[media_idx]["mimeType"] = mime
            files[media_idx]["uri"] = uri
        else:
            base = uri.rsplit("/", 1)[-1] if "/" in uri else uri
            base = _TRAILING_HASH_RE.sub(".", base) or "file"
            files.append({"name": base, "mimeType": mime, "uri": uri})
        media_idx += 1

    return files


def deduplicate_files(files: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Merge duplicate file entries by name (mirrors TS deduplicateFiles)."""
    seen: Dict[str, Dict[str, str]] = {}
    for f in files:
        name = f.get("name") or ""
        if name in seen:
            existing = seen[name]
            for k in ("mimeType", "size", "uri"):
                if not existing.get(k) and f.get(k):
                    existing[k] = f[k]
        else:
            seen[name] = dict(f)
    return list(seen.values())


# ---------------------------------------------------------------------------
# Session store (sessions.json index)
# ---------------------------------------------------------------------------

def _default_sessions_dir() -> str:
    """Return the default Hermes sessions directory."""
    hermes_home = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
    return os.path.join(hermes_home, "sessions")


def load_session_store(sessions_dir: Optional[str] = None) -> Dict[str, Any]:
    """Load sessions.json → {session_key: entry}."""
    d = sessions_dir or _default_sessions_dir()
    path = os.path.join(d, "sessions.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.debug("Could not load sessions.json from %s: %s", path, exc)
    return {}


# ---------------------------------------------------------------------------
# session_key → session_id resolution (via sessions.json index)
# ---------------------------------------------------------------------------
#
# Hermes "spec 002" moved message transcripts from per-session ``<id>.jsonl``
# files into a single SQLite database (``~/.hermes/state.db``, table
# ``messages``).  ``sessions.json`` is still written, but only as a
# ``session_key → session_id`` index (see gateway/session.py SessionStore._save:
# "kept for session key -> ID mapping").  So we resolve the session_id here
# and then read the actual messages from SQLite (see ``read_session_history``).

def _lookup_session_entry(
    session_key: str,
    sessions_dir: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Find the sessions.json entry for *session_key* (case-insensitive)."""
    store = load_session_store(sessions_dir)
    entry = store.get(session_key)
    if entry is None:
        lower = session_key.strip().lower()
        for k, v in store.items():
            if k.lower() == lower:
                entry = v
                break
    return entry


def resolve_session_id(
    session_key: str,
    sessions_dir: Optional[str] = None,
) -> Optional[str]:
    """Resolve *session_key* → ``session_id`` using the sessions.json index."""
    entry = _lookup_session_entry(session_key, sessions_dir)
    if not entry:
        logger.debug("No sessions.json entry for key=%s", session_key)
        return None

    # Support both snake_case (lighthouse-hermes) and camelCase (openclaw)
    session_id = entry.get("session_id") or entry.get("sessionId") or ""
    if not session_id:
        logger.debug("Entry for key=%s has no session_id/sessionId", session_key)
        return None
    return session_id


# ---------------------------------------------------------------------------
# SQLite session store accessor (hermes_state.SessionDB)
# ---------------------------------------------------------------------------

# 每个已打开的 state.db 独立缓存一个只读 SessionDB。历史读取始终使用调用方
# 传入的明确文件路径，避免 ContextVar 或不存在路径意外创建数据库。
_session_dbs: Dict[str, Any] = {}
_session_db_failed_paths: set[str] = set()


def _default_state_db_path(sessions_dir: Optional[str] = None) -> str:
    """返回 sessions 目录同级的主 state.db 绝对路径。"""
    directory = os.path.abspath(sessions_dir or _default_sessions_dir())
    return os.path.join(os.path.dirname(directory), "state.db")


def _get_session_db(state_db_path: str):
    """按已存在的 SQLite 文件返回缓存 SessionDB，不创建空库。

    History 是纯读取接口。目标文件不存在时直接返回 None，不能因为用户点击
    会话列表创建新的 SQLite 数据库。
    Hermes 旧版本若不支持 ``read_only`` 参数，会在目标已存在的前提下退回
    兼容构造方式。
    """
    if not state_db_path:
        return None

    path = os.path.realpath(state_db_path)
    if not os.path.isfile(path):
        return None
    if path in _session_dbs:
        return _session_dbs[path]
    if path in _session_db_failed_paths:
        return None

    try:
        from hermes_state import SessionDB

        try:
            db = SessionDB(db_path=Path(path), read_only=True)
        except TypeError:
            # 兼容尚未提供 read_only 参数的 Hermes；已先校验文件存在，避免
            # 该降级路径创建数据库。
            db = SessionDB(db_path=Path(path))
        _session_dbs[path] = db
        return db
    except Exception as exc:  # pragma: no cover - depends on host build
        logger.warning(
            "[lightclaw] SessionDB unavailable for history path=%s: %s",
            path,
            exc,
        )
        _session_db_failed_paths.add(path)
        return None


def _read_db_message_groups(
    session_id: str,
    state_db_paths: List[str],
) -> List[Tuple[List[dict], str]]:
    """读取各候选库中同一 session 的正文，并保留来源路径。

    子角色启用独立 Home 后，升级前的主库和升级后的子库可能各保存同一
    session 的不同时间段。这里不因第一个库命中就停止，而是返回所有非空
    结果，交由调用方按时间合并。历史读取始终只读，不会创建或迁移数据库。
    """
    groups: List[Tuple[List[dict], str]] = []
    seen_paths: set[str] = set()
    for state_db_path in state_db_paths:
        real_path = os.path.realpath(state_db_path)
        if real_path in seen_paths:
            continue
        seen_paths.add(real_path)
        db = _get_session_db(state_db_path)
        if db is None:
            continue
        try:
            raw_messages = db.get_messages_as_conversation(
                session_id, include_ancestors=True,
            )
        except Exception as exc:
            logger.warning(
                "Failed to read messages from SessionDB path=%s session_id=%s: %s",
                os.path.realpath(state_db_path),
                session_id,
                exc,
            )
            continue
        if raw_messages:
            groups.append((raw_messages, real_path))
    return groups


def _history_content_fingerprint(message: dict) -> tuple:
    """返回跨物理数据库识别同一消息副本的保守指纹。

    子角色使用独立 Home 后，同一 session 的旧消息可能在主 state.db，
    新消息位于子 state.db；某些 Core 版本还可能复制已有消息。SQLite 自增
    id 在不同数据库之间不稳定，缺少平台消息 ID 时只能以时间、角色和正文
    哈希识别副本。该指纹只用于不同数据库之间，绝不折叠同一库内模型真实的
    重复输出。
    """
    content = str(message.get("content") or "")
    content_hash = hashlib.sha1(content.encode("utf-8")).hexdigest()[:16]
    return (
        message.get("timestamp"),
        message.get("role", ""),
        content_hash,
    )


def _history_message_identity(message: dict) -> tuple:
    """返回跨库消息身份；优先平台消息 ID，缺失时使用正文弱指纹。"""
    platform_message_id = message.get("platformMessageId")
    if platform_message_id:
        return ("platform", platform_message_id)
    return ("content",) + _history_content_fingerprint(message)


def _attach_usage_from_state_db(
    messages: List[dict],
    session_id: str,
    state_db_path: str,
) -> None:
    """从正文所在 Home 的 usage sidecar 补回该库内各轮 token 用量。"""
    try:
        sessions_dir = os.path.join(os.path.dirname(state_db_path), "sessions")
        usage_entries = _read_usage_log(
            os.path.join(sessions_dir, f"{session_id}.usage.jsonl")
        )
        if usage_entries:
            _attach_usage_to_messages(messages, usage_entries)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(
            "Usage attach failed for session_id=%s state_db=%s: %s",
            session_id,
            state_db_path,
            exc,
        )


def _merge_db_message_groups(
    groups: List[Tuple[List[dict], str]],
    session_id: str,
    *,
    limit: int,
    chat_only: bool,
) -> List[dict]:
    """合并主/子数据库的同一 session，保留库内顺序并仅跨库去重。

    候选顺序由调用方决定，当前为子库优先、主库次之；副本冲突时保留优先
    数据库的消息及其 usage。真实消息只在不同物理数据库身份相同才去重。
    """
    normalized_groups: List[Tuple[List[dict], str]] = []
    preferred_sources: Dict[tuple, str] = {}

    for raw_messages, state_db_path in groups:
        messages = _normalize_db_messages(
            raw_messages, limit=100000, chat_only=chat_only,
        )
        _attach_usage_from_state_db(messages, session_id, state_db_path)
        normalized_groups.append((messages, state_db_path))
        # 候选顺序定义冲突副本优先级，先记录归属，避免时间较早的低优先级
        # 副本抢占子库消息。
        for message in messages:
            identity = _history_message_identity(message)
            preferred_sources.setdefault(identity, state_db_path)

    # 只在不同物理库的当前队首之间比较时间；绝不排序单个库内部消息，避免
    # Hermes 用 SQLite id 保证的 tool call / tool result 相邻关系被打散。
    positions = [0] * len(normalized_groups)
    messages: List[dict] = []
    while True:
        candidates: List[Tuple[float, int]] = []
        for index, (group_messages, _state_db_path) in enumerate(normalized_groups):
            if positions[index] >= len(group_messages):
                continue
            timestamp = group_messages[positions[index]].get("timestamp")
            sort_timestamp = (
                float(timestamp)
                if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool)
                else float("inf")
            )
            candidates.append((sort_timestamp, index))
        if not candidates:
            break

        _, index = min(candidates)
        group_messages, state_db_path = normalized_groups[index]
        message = group_messages[positions[index]]
        positions[index] += 1
        if preferred_sources[_history_message_identity(message)] == state_db_path:
            messages.append(message)

    return messages[-limit:] if len(messages) > limit else messages


# ---------------------------------------------------------------------------
# Legacy JSONL transcript path resolution (pre-spec-002 builds)
# ---------------------------------------------------------------------------

def resolve_transcript_path(
    session_id: str,
    sessions_dir: Optional[str] = None,
    entry: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Locate the ``<session_id>.jsonl`` transcript file (legacy builds).

    Fallback chain (mirrors session-store.ts):
      1. entry.sessionFile (absolute, or relative to sessions_dir)
      2. <sessions_dir>/<session_id>.jsonl
      3. sessions.json sibling directory (offline / downloaded sessions)
    Returns ``None`` when no transcript file exists (e.g. on new SQLite-only
    builds, which is the expected case there).
    """
    if not session_id:
        return None
    d = sessions_dir or _default_sessions_dir()
    jsonl_name = f"{session_id}.jsonl"

    # Layer 1: explicit sessionFile from the sessions.json entry.
    if entry:
        sf = entry.get("session_file") or entry.get("sessionFile")
        if sf:
            p = sf if os.path.isabs(sf) else os.path.join(d, sf)
            if os.path.isfile(p):
                return p

    # Layer 2: standard sessions directory.
    p2 = os.path.join(d, jsonl_name)
    if os.path.isfile(p2):
        return p2

    # Layer 3: sessions.json sibling directory (offline scenario).
    sessions_json_path = os.path.join(d, "sessions.json")
    sibling_dir = os.path.dirname(sessions_json_path)
    if sibling_dir and sibling_dir != d:
        p3 = os.path.join(sibling_dir, jsonl_name)
        if os.path.isfile(p3):
            return p3

    return None


# ---------------------------------------------------------------------------
# Message normalisation (mirrors message-parser.ts: normalizeMessage)
# ---------------------------------------------------------------------------

def _extract_text(content: Any, role: str = "") -> str:
    """Extract plain text from a message content field."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for entry in content:
        if not isinstance(entry, dict):
            continue
        t = entry.get("type", "")
        if t in ("text", "output_text", "input_text"):
            txt = entry.get("text", "")
            if isinstance(txt, str):
                parts.append(txt)
    return "\n".join(parts)


def _is_system_injected(msg: dict) -> bool:
    """Return True if a user-role message is actually system-injected."""
    if (msg.get("role") or "").lower() != "user":
        return False
    text = _extract_text(msg.get("content", ""))
    return bool(re.match(r"^System:\s*\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}", text.strip()))


# Markdown links pointing at localfile:// — embedded by _send_attachment in outbound.
_LOCALFILE_MD_RE = re.compile(
    r"\[(?P<name>[^\]]+)\]\((?P<uri>localfile://[^)\s]+)\)"
)

# MEDIA:/path tags — stored raw in transcripts, need conversion to localfile://.
# Treat everything after the absolute-path prefix through the line end as the
# path so historical attachments with spaces follow the same rule as live
# delivery. Optional quotes/backticks are tolerated for model variations.
_MEDIA_TAG_RE = re.compile(
    r'^[ \t]*[`"\']?MEDIA:[ \t]*'
    r'(?P<path>(?:[A-Za-z]:[/\\]|/|~/)[^\r\n]*?)[`"\']?[ \t]*(?=\r?$)',
    re.MULTILINE,
)


def _mime_from_filename(name: str) -> Optional[str]:
    """根据文件扩展名推断 MIME 类型，无法识别时返回 None。"""
    mime, _ = mimetypes.guess_type(name)
    return mime or None


def _extract_localfile_links(text: str) -> List[Dict[str, str]]:
    """从助手回复中提取 ``[name](localfile://...)`` 格式的链接。

    每条记录包含 ``name``、``uri``，以及（可推断时）``mimeType``。
    前端 ``file-card.tsx`` 的 ``isImageFile`` 依赖 ``mimeType`` 字段判断图片；
    若缺失，图片附件会被归入 ``otherFiles``，渲染成灰色不可交互的静态卡片。
    """
    if not text or LOCALFILE_SCHEME not in text:
        return []
    result = []
    for m in _LOCALFILE_MD_RE.finditer(text):
        entry: Dict[str, str] = {"name": m.group("name"), "uri": m.group("uri")}
        mime = _mime_from_filename(m.group("name"))
        if mime:
            entry["mimeType"] = mime
        result.append(entry)
    return result


def _convert_media_tags_to_localfile(text: str) -> str:
    """Replace ``MEDIA:/path`` lines with ``localfile://`` Markdown links.

    Transcript JSONL stores the raw AI reply including MEDIA: tags (the
    framework strips them at delivery time via ``extract_media()``).  When
    serving history back to the front-end, we convert them to the same
    ``📎 [name](localfile:///path)`` format used by live delivery so the
    user sees clickable download links.
    """
    if "MEDIA:" not in text:
        return text

    def _replace(m: re.Match) -> str:
        path = m.group("path").strip().rstrip("\"'`,.;:)}]")
        name = os.path.basename(path) or path
        encoded_path = quote(path, safe="/")
        return f"📎 [{name}]({LOCALFILE_SCHEME}{encoded_path})"

    return _MEDIA_TAG_RE.sub(_replace, text)


def normalize_message(msg: dict) -> Optional[dict]:
    """Convert a raw JSONL message object to a HistoryMessage dict.

    Returns None if the message should be skipped.
    """
    role_raw = msg.get("role", "")
    if not role_raw:
        return None

    role_map = {
        "user": "user",
        "assistant": "assistant",
        "system": "system",
        "tool": "tool",
        "toolresult": "tool",
        "tool_result": "tool",
    }
    role = role_map.get(role_raw.lower(), "assistant")

    text = _extract_text(msg.get("content"), role)
    raw_timestamp = msg.get("timestamp")
    timestamp = raw_timestamp if isinstance(raw_timestamp, (int, float)) else None

    # Completely empty messages are useless
    if not text and role not in ("tool",):
        return None

    result: dict = {
        "role": role,
        "content": text,
    }
    if timestamp is not None:
        result["timestamp"] = timestamp

    # 透传消息 ID：跨 Reset 历史合并（read_session_histories_by_ids）需要用
    # 这些 ID 做去重键。缺少它们会退回到「timestamp+role+content_hash」的
    # 弱去重，同一条消息若被父/子 session 各写一次会展示重复。
    message_id = msg.get("message_id") or msg.get("messageId") or msg.get("id")
    if message_id:
        result["messageId"] = message_id
    platform_message_id = msg.get("platform_message_id") or msg.get("platformMessageId")
    if platform_message_id:
        result["platformMessageId"] = platform_message_id

    # File-attachment recovery (mirrors TS history/message-parser.ts):
    # User messages → "用户发送了文件" + [media attached] markers
    # Assistant messages → MEDIA: tags (raw) or localfile:// markdown links
    if role == "user":
        files = extract_file_attachments(text)
        if files:
            result["files"] = deduplicate_files(files)
        # 清除 [media attached: ...] 标记，这是内部历史恢复注解，不应展示给用户或 LLM。
        # 注意：此处使用条件更新（cleaned != text）而非始终覆盖，是因为：
        #   1. 若无标记，cleaned == text，跳过可避免一次不必要的 dict 写入。
        #   2. 若仅有标记而无其他文字，cleaned == ""，条件成立，result["content"] 被置空，
        #      与 assistant 分支「始终覆盖」的语义等价——前端只渲染 files 数组。
        cleaned_user_text = _MEDIA_ATTACH_RE.sub("", text).strip()
        if cleaned_user_text != text:
            result["content"] = cleaned_user_text
    elif role == "assistant":
        # Restore MEDIA: tags to the same localfile:// Markdown representation
        # used by live delivery. Do not also populate files from these
        # derived links: the front-end would otherwise render both the inline
        # blue link/image and a second structured attachment card.
        converted_text = _convert_media_tags_to_localfile(text)
        localfile_links = _extract_localfile_links(converted_text)
        if localfile_links:
            result["content"] = converted_text.strip()

    return result


# ---------------------------------------------------------------------------
# Per-turn usage sidecar (paired writer in outbound._persist_turn_usage)
# ---------------------------------------------------------------------------

def _resolve_usage_log_path(transcript_path: str) -> str:
    """Return the sidecar usage path for a given transcript jsonl path.

    Convention: ``<dir>/<session_id>.jsonl`` → ``<dir>/<session_id>.usage.jsonl``.
    """
    if transcript_path.endswith(".jsonl"):
        return transcript_path[: -len(".jsonl")] + ".usage.jsonl"
    return transcript_path + ".usage.jsonl"


def _read_usage_log(path: str) -> List[Dict[str, Any]]:
    """Parse the usage sidecar jsonl into a list of entries.

    Each entry has shape::

        {"roundMsgId": str, "timestamp": int, "usage": dict | None}

    A ``usage`` of ``None`` denotes a *placeholder* line written by
    ``outbound._persist_turn_usage`` for turns where the tracker had no
    delta to report.  Placeholders are kept in the list to preserve
    ordinal alignment with transcript turn-end assistants — the attach
    step skips them rather than writing ``null`` onto a message.

    Malformed lines are skipped silently.  A missing file returns ``[]``
    — equivalent to "no usage data yet" (e.g. fresh sessions before the
    feature shipped).
    """
    if not os.path.isfile(path):
        return []
    entries: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    obj = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                # ``usage`` may be a dict (real entry) or None (placeholder).
                # Anything else (e.g. malformed value) → skip the line.
                usage = obj.get("usage")
                if usage is not None and not isinstance(usage, dict):
                    continue
                ts = obj.get("timestamp")
                if not isinstance(ts, (int, float)):
                    continue
                entries.append({
                    "roundMsgId": obj.get("roundMsgId"),
                    "timestamp":  int(ts),
                    "usage":      usage,  # dict or None
                })
    except OSError as exc:
        logger.warning("Failed to read usage sidecar %s: %s", path, exc)
        return []
    # Sidecar is append-only and read in write order; do not re-sort by
    # timestamp here because that would also re-order dict-vs-None entries
    # away from the original ordinal positions used for join.
    return entries


def _attach_usage_to_messages(
    messages: List[dict],
    usage_entries: List[Dict[str, Any]],
) -> None:
    """In-place: attach each usage entry to its matching turn-end assistant.

    "Turn-end assistant" = the last ``assistant`` of each turn (a ``user``
    message opens a turn; tool/system rows are transparent), mirroring
    openclaw's "one usage per turn, on the turn's last assistant".

    Matching strategy — **absolute-time anchoring** (preferred):
        Each sidecar entry carries the ``stop_typing`` timestamp of its round;
        each turn-end assistant carries its store timestamp.  We anchor every
        entry to the turn-end assistant *nearest in time* via an order-
        preserving (monotonic) minimum-cost assignment.  Because inter-turn
        gaps (tens of seconds) dwarf the intra-turn writer skew (sub-second),
        each entry lands on its own turn — and, crucially, the pairing stays
        correct when the two sides differ in count (a command round wrote no
        entry, or a real-but-zero-token round was skipped).  That count drift
        is exactly what pure ordinal alignment cannot survive: one missing or
        extra entry shifts every subsequent pairing.

    Fallback — **ordinal tail-alignment**:
        Used when timestamps are unusable on either side, or there are more
        entries than turn-ends (legacy data).  Pairs the i-th entry with the
        i-th turn-end counting from the end, so freshly-added turns at the tail
        line up and pre-feature turns at the head go without usage.

    Placeholder entries (``usage is None``, written when a real turn could not
    be measured) take part in matching so they *claim* their own slot and keep
    neighbours from drifting onto it, but no payload is attached — a null usage
    would mislead the renderer into showing "0 tokens" instead of "unknown".
    """
    if not usage_entries:
        return

    turn_end_assistants = _collect_turn_end_assistants(messages)
    if not turn_end_assistants:
        return

    end_ts = [_usage_ts_ms(messages[i].get("timestamp")) for i in turn_end_assistants]
    entry_ts = [_usage_ts_ms(e.get("timestamp")) for e in usage_entries]

    # Preferred path: absolute-time anchoring.  Requires a usable timestamp on
    # every entry and every turn-end, and no more entries than turn-ends (so a
    # one-to-one, order-preserving assignment of every entry exists).
    if (
        len(usage_entries) <= len(turn_end_assistants)
        and all(t is not None for t in end_ts)
        and all(t is not None for t in entry_ts)
    ):
        assignment = _align_entries_by_time(entry_ts, end_ts)  # entry → end pos
        for entry_pos, end_pos in enumerate(assignment):
            if end_pos is None:
                continue
            usage = usage_entries[entry_pos].get("usage")
            if usage is None:
                continue  # placeholder: claims its slot, carries no payload
            messages[turn_end_assistants[end_pos]]["usage"] = usage
        return

    # Fallback: ordinal tail-alignment.
    _attach_usage_tail_ordinal(messages, turn_end_assistants, usage_entries)


def _collect_turn_end_assistants(messages: List[dict]) -> List[int]:
    """Return indices of each turn's last assistant message, in order.

    A ``user`` message opens a new turn; the last ``assistant`` seen before the
    next ``user`` (or end-of-list) is that turn's end.  ``tool`` / ``system``
    rows are transparent and leave the running pointer untouched.
    """
    turn_end_assistants: List[int] = []
    last_assistant_in_turn: Optional[int] = None
    for i, m in enumerate(messages):
        role = m.get("role")
        if role == "user":
            if last_assistant_in_turn is not None:
                turn_end_assistants.append(last_assistant_in_turn)
                last_assistant_in_turn = None
            continue
        if role == "assistant":
            last_assistant_in_turn = i
        # tool / system rows: leave the running pointer alone.
    if last_assistant_in_turn is not None:
        turn_end_assistants.append(last_assistant_in_turn)
    return turn_end_assistants


def _usage_ts_ms(ts: Any) -> Optional[float]:
    """Normalise a timestamp to epoch milliseconds, or ``None`` if unusable.

    Transcript rows store epoch *seconds* (e.g. ``1780387827.02``) while the
    usage sidecar stores epoch *milliseconds* (``int(time.time() * 1000)``).
    A value below ``1e12`` is therefore treated as seconds and scaled up, so
    both sides become directly comparable without the callsite assuming a unit.
    ``bool`` is rejected explicitly (it is an ``int`` subclass in Python).
    """
    if isinstance(ts, bool) or not isinstance(ts, (int, float)):
        return None
    return float(ts) * 1000.0 if ts < 1e12 else float(ts)


def _align_entries_by_time(
    entry_ts: List[float],
    end_ts: List[float],
) -> List[Optional[int]]:
    """Order-preserving minimum-cost assignment of entries onto turn-ends.

    Returns a list parallel to *entry_ts*: ``result[i]`` is the index into
    *end_ts* that entry ``i`` is anchored to (strictly increasing across i), or
    ``None`` if unassigned.  Cost is absolute time distance; the chosen
    turn-ends form an increasing subsequence — matching the fact that sidecar
    entries and turn-end assistants share one chronological order while the
    head of the transcript may pre-date the sidecar feature.

    Caller guarantees ``len(entry_ts) <= len(end_ts)`` so a full assignment of
    every entry exists.  Complexity ``O(p * q)`` with both small.
    """
    p, q = len(entry_ts), len(end_ts)
    if p == 0:
        return []
    inf = float("inf")
    # dp[i][j]: min total cost assigning the first i entries within the first
    # j turn-ends (entry i-1 placed at some end index < j).
    dp = [[inf] * (q + 1) for _ in range(p + 1)]
    for j in range(q + 1):
        dp[0][j] = 0.0
    for i in range(1, p + 1):
        for j in range(i, q + 1):
            skip = dp[i][j - 1]
            take = dp[i - 1][j - 1] + abs(entry_ts[i - 1] - end_ts[j - 1])
            dp[i][j] = take if take < skip else skip

    assignment: List[Optional[int]] = [None] * p
    i, j = p, q
    while i > 0 and j > 0:
        skip = dp[i][j - 1]
        take = dp[i - 1][j - 1] + abs(entry_ts[i - 1] - end_ts[j - 1])
        if take <= skip:
            assignment[i - 1] = j - 1
            i -= 1
            j -= 1
        else:
            j -= 1
    return assignment


def _attach_usage_tail_ordinal(
    messages: List[dict],
    turn_end_assistants: List[int],
    usage_entries: List[Dict[str, Any]],
) -> None:
    """Fallback pairing: i-th entry ↔ i-th turn-end, counted from the end.

    Placeholder entries (``usage is None``) still occupy a slot to preserve
    ordinal alignment, but carry no payload.
    """
    n = min(len(turn_end_assistants), len(usage_entries))
    if n == 0:
        return
    paired_assistants = turn_end_assistants[-n:]
    paired_entries = usage_entries[-n:]
    for asst_idx, entry in zip(paired_assistants, paired_entries):
        if entry.get("usage") is None:
            continue
        messages[asst_idx]["usage"] = entry["usage"]


# ---------------------------------------------------------------------------
# Core reader (mirrors session-reader.ts: readSessionHistory)
# ---------------------------------------------------------------------------

def read_session_history(
    session_key: str,
    sessions_dir: Optional[str] = None,
    *,
    state_db_paths: Optional[List[str]] = None,
    limit: int = 200,
    chat_only: bool = True,
) -> List[dict]:
    """Read the last *limit* messages for *session_key*.

    Two-tier read for forward/backward compatibility across Hermes builds:
      1. SQLite (``~/.hermes/state.db`` via :class:`hermes_state.SessionDB`)
         — the canonical store since "spec 002".
      2. Legacy per-session ``<session_id>.jsonl`` transcript file — used when
         SessionDB is unavailable (older builds) or yields no rows.
    In both cases the ``session_id`` comes from the surviving ``sessions.json``
    index.
    """
    entry = _lookup_session_entry(session_key, sessions_dir)
    if not entry:
        logger.warning(
            "No sessions.json entry for session_key=%s sessions_dir=%s",
            session_key, sessions_dir or _default_sessions_dir(),
        )
        return []
    session_id = entry.get("session_id") or entry.get("sessionId") or ""
    if not session_id:
        logger.warning("Entry for session_key=%s has no session_id", session_key)
        return []

    # 第一层：SQLite。子角色库与主库均参与合并；旧调用方未显式指定时保持
    # 原先只读主库的行为。
    db_paths = state_db_paths or [_default_state_db_path(sessions_dir)]
    groups = _read_db_message_groups(session_id, db_paths)
    if groups:
        messages = _merge_db_message_groups(
            groups,
            session_id,
            limit=limit,
            chat_only=chat_only,
        )
        return messages
    logger.debug(
        "SessionDB returned no rows for session_id=%s; trying JSONL",
        session_id,
    )

    # Tier 2: legacy JSONL transcript file (pre-spec-002 builds).
    path = resolve_transcript_path(session_id, sessions_dir, entry)
    if not path:
        logger.warning(
            "No history found (SQLite empty/unavailable and no JSONL) for "
            "session_key=%s session_id=%s",
            session_key, session_id,
        )
        return []
    logger.debug("Falling back to legacy JSONL transcript: %s", path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError as exc:
        logger.warning("Failed to read transcript %s: %s", path, exc)
        return []

    messages = _parse_transcript(raw, limit=limit, chat_only=chat_only)

    # Re-attach per-turn usage from the sidecar jsonl so the response
    # shape matches openclaw (assistant.usage on the last assistant of
    # each turn).  Best-effort: any failure here just yields messages
    # without usage, never breaks the history response.
    try:
        usage_entries = _read_usage_log(_resolve_usage_log_path(path))
        if usage_entries:
            _attach_usage_to_messages(messages, usage_entries)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(
            "Usage attach failed for transcript=%s: %s", path, exc,
        )

    return messages


def _parse_transcript(
    raw: str,
    *,
    limit: int = 200,
    chat_only: bool = True,
) -> List[dict]:
    """Parse a legacy JSONL transcript into HistoryMessage dicts.

    JSONL files are written line-by-line as messages arrive, so the line order
    naturally reflects chronological order. No additional sorting is needed.
    """
    messages: list[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Skip non-message metadata lines.
        if parsed.get("type") in _SKIP_LINE_TYPES:
            continue

        # Skip session_meta marker lines.
        if parsed.get("role") == "session_meta":
            continue

        # Standard message lines wrap the payload in a "message" object.
        msg = parsed.get("message") if isinstance(parsed.get("message"), dict) else parsed

        # Skip delivery-mirror messages.
        if msg.get("model") == "delivery-mirror":
            continue

        # Skip system-injected user messages.
        if _is_system_injected(msg):
            continue

        normalized = normalize_message(msg)
        if normalized is None:
            continue

        if chat_only and normalized["role"] not in ("user", "assistant"):
            continue

        messages.append(normalized)

    # Log message order for debugging (only build the order_info string when
    # DEBUG logging is actually enabled; otherwise the per-message preview /
    # join would burn cycles for nothing on every history fetch).
    if messages and logger.isEnabledFor(logging.DEBUG):
        order_info = []
        for i, m in enumerate(messages[:10]):  # First 10 messages
            preview = str(m.get("content", ""))[:30].replace("\n", " ")
            ts = m.get("timestamp", "N/A")
            order_info.append(f"[{i}] {m['role']} (ts={ts}): {preview}...")
        if len(messages) > 10:
            order_info.append(f"... and {len(messages) - 10} more")
        logger.debug(
            "[lightclaw] Parsed %d messages from JSONL transcript (line order): %s",
            len(messages), "; ".join(order_info),
        )

    return messages[-limit:] if len(messages) > limit else messages


def _normalize_db_messages(
    raw_messages: List[dict],
    *,
    limit: int = 200,
    chat_only: bool = True,
) -> List[dict]:
    """Normalise SQLite conversation rows into HistoryMessage dicts.

    ``raw_messages`` come from ``SessionDB.get_messages_as_conversation`` in the
    OpenAI ``{role, content, tool_calls?, ...}`` shape (content already decoded
    and sanitised).  We reuse :func:`normalize_message` for file-attachment /
    ``MEDIA:`` link recovery, and drop delivery-mirror echoes (``observed``)
    plus system-injected user turns to match the previous JSONL behaviour.

    ``SessionDB.get_messages_as_conversation`` 使用 ``ORDER BY id``（自增主键）。
    这个顺序会保持 tool call 与 tool result 的相邻关系，插件不得再按 timestamp
    重排单库消息；跨物理库合并时仅比较各自尚未读取的队首。
    """
    messages: list[dict] = []
    for msg in raw_messages:
        if not isinstance(msg, dict):
            continue

        # Skip delivery-mirror / echo rows so assistant text isn't duplicated.
        if msg.get("observed"):
            continue

        # Skip system-injected user messages (timestamped "System: [..]" turns).
        if _is_system_injected(msg):
            continue

        normalized = normalize_message(msg)
        if normalized is None:
            continue

        if chat_only and normalized["role"] not in ("user", "assistant"):
            continue

        messages.append(normalized)

    # Log message order for debugging (only build the order_info string when
    # DEBUG logging is actually enabled — see _parse_transcript for rationale).
    if messages and logger.isEnabledFor(logging.DEBUG):
        order_info = []
        for i, m in enumerate(messages[:10]):  # First 10 messages
            preview = str(m.get("content", ""))[:30].replace("\n", " ")
            order_info.append(f"[{i}] {m['role']}: {preview}...")
        if len(messages) > 10:
            order_info.append(f"... and {len(messages) - 10} more")
        logger.debug(
            "[lightclaw] Normalized %d messages from SessionDB (ORDER BY id): %s",
            len(messages), "; ".join(order_info),
        )

    return messages[-limit:] if len(messages) > limit else messages


# 跨 Reset 历史合并查询

MAX_MERGE_SESSIONS = 100


def _history_dedup_key(message: dict) -> tuple:
    """构建跨 session 合并时的去重键（与具体 session_id 无关）。

    采用「消息自身身份」而非「迭代到的 session_id」作为去重维度，原因：
    当 ``sessionIdHistory`` 因会话中途压缩同时记录父、子 session 时，配合
    ``include_ancestors=True`` 读取，父 session 的消息会在父、子两次迭代中
    被分别读出。若去重键带 session_id，则同一条消息会被判为不同，导致重复。

    优先用平台消息 ID（全局唯一）；缺失时退回 ``(timestamp, role, content_hash)``。
    """
    platform_message_id = (
        message.get("platformMessageId")
        or message.get("platform_message_id")
        or message.get("messageId")
        or message.get("message_id")
    )
    if platform_message_id:
        return ("pmid", platform_message_id)

    content = str(message.get("content") or "")
    content_hash = hashlib.sha1(content.encode("utf-8")).hexdigest()[:16]
    return (
        "legacy",
        message.get("timestamp"),
        message.get("role", ""),
        content_hash,
    )


def read_session_histories_by_ids(
    session_ids: List[str],
    sessions_dir: Optional[str] = None,
    *,
    state_db_paths: Optional[List[str]] = None,
    limit: int = 200,
    chat_only: bool = True,
) -> List[dict]:
    """按 sessionIdHistory 顺序合并多个 session 的消息并截取最近 limit 条。

    用于跨 Reset 历史完整性：同一 chatId 的 ``sessionIdHistory`` 记录了所有历史
    sessionId，本函数按该顺序逐个查询、合并，返回完整历史流。

    完整性保证：每个 session 使用 ``include_ancestors=True`` 走 parent_session_id
    链，确保会话中途压缩（session_id 轮转 parent→child）之前的消息不丢失，与单
    session 读取行为对齐。
    """
    if not session_ids:
        return []

    deduped_session_ids = [sid for sid in session_ids if sid]
    if len(deduped_session_ids) > MAX_MERGE_SESSIONS:
        logger.warning(
            "[history] session_ids truncated to last %d for performance",
            MAX_MERGE_SESSIONS,
        )
        deduped_session_ids = deduped_session_ids[-MAX_MERGE_SESSIONS:]

    all_messages: List[dict] = []
    seen_keys: set = set()
    db_paths = state_db_paths or [_default_state_db_path(sessions_dir)]

    for sid in deduped_session_ids:
        msgs: List[dict] = []

        # Tier 1: SQLite（include_ancestors=True 保证压缩前历史完整）
        groups = _read_db_message_groups(sid, db_paths)
        if groups:
            msgs = _merge_db_message_groups(
                groups,
                sid,
                limit=100000,
                chat_only=chat_only,
            )

        # Tier 2: JSONL fallback
        if not msgs:
            d = sessions_dir or _default_sessions_dir()
            path = os.path.join(d, f"{sid}.jsonl")
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        raw_text = f.read()
                    msgs = _parse_transcript(raw_text, limit=100000, chat_only=chat_only)
                except OSError as exc:
                    logger.warning(
                        "[history] read_session_histories_by_ids: JSONL read error sid=%s: %s",
                        sid, exc,
                    )

        for message in msgs:
            dedup_key = _history_dedup_key(message)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            all_messages.append(message)

    return all_messages[-limit:] if len(all_messages) > limit else all_messages


# ---------------------------------------------------------------------------
# Session list (mirrors session-reader.ts: listSessions)
# ---------------------------------------------------------------------------

def list_sessions(
    sessions_dir: Optional[str] = None,
    *,
    owner_uin: Optional[str] = None,
    channel_key: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> List[dict]:
    """List sessions from the sessions.json index.

    Multi-tenant filtering (D2):
        ``sessions.json`` is shared by the whole Hermes instance — every
        tenant's conversations live in the same dict.  In LightClaw, sessionKey
        format is ``agent:{agentId}:<channel_key>:dm:<peer_uin>[:<chatId>]``
        where ``agentId`` occupies the namespace segment (defaults to ``"main"``
        via DEFAULT_AGENT_ID) and ``chatId`` is the optional business-session
        suffix appended for physical per-chat isolation (method A).

        When ``owner_uin`` is set, we only return entries whose sessionKey's
        ``peer_uin`` segment matches ``owner_uin`` — i.e. "the sessions
        belonging to user X", filtering out other tenants' sessions.

        ``channel_key`` further narrows results to a specific platform
        prefix (``agent:<agent_id>:<channel_key>:``); set it to LightClaw's
        ``CHANNEL_KEY`` to avoid leaking sessions from other adapters that
        share the same Hermes instance.

        ``agent_id`` scopes results to a specific agent (defaults to
        ``"main"`` when omitted).  Pass the resolved agentId from the
        inbound message for multi-agent isolation.

        With neither set, behaviour matches the pre-D2 build (return all
        entries).  This keeps the function safe to use in single-tenant
        deployments and in hosts that have no concept of "owner".
    """
    from .config import DEFAULT_AGENT_ID as _DEFAULT_AGENT_ID
    effective_agent_id = agent_id or _DEFAULT_AGENT_ID

    store = load_session_store(sessions_dir)
    result: list[dict] = []

    # Pre-compute the prefix we use for filtering once.  sessionKey segments
    # are ":"-delimited and the per-tenant dm chunk we care about always
    # appears at the same depth, so a substring check is sufficient and
    # avoids a full split per row.
    channel_prefix = f"agent:{effective_agent_id}:{channel_key}:" if channel_key else None
    dm_marker = f":dm:{owner_uin}" if owner_uin else None

    for key, entry in store.items():
        if not entry:
            continue

        if channel_prefix and not key.startswith(channel_prefix):
            continue

        if dm_marker:
            # Match `:dm:<owner_uin>` followed by either end-of-string or
            # `:` (so `:dm:1234` does not falsely match `:dm:12345`).
            idx = key.find(dm_marker)
            if idx < 0:
                continue
            tail_pos = idx + len(dm_marker)
            if tail_pos < len(key) and key[tail_pos] != ":":
                continue

        # Support both snake_case and camelCase field names
        sid = entry.get("session_id") or entry.get("sessionId") or ""
        if not sid:
            continue
        updated = entry.get("updated_at") or entry.get("updatedAt")
        display = entry.get("display_name") or entry.get("displayName")
        result.append({
            "sessionKey": key,
            "sessionId": sid,
            "updatedAt": updated,
            "displayName": display,
        })
    # Sort by updated_at descending (most recent first)
    result.sort(key=lambda x: x.get("updatedAt") or "", reverse=True)
    return result
