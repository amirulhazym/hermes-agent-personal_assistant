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

跨 Reset 历史完整性（Cross-Reset History Preservation）：

    超时自动 reset（idle/daily）由 Hermes Core 在 get_or_create_session() 内部
    触发，lightclawbot 通过消息前/后内存快照对比来检测。

    检测逻辑（_handle_incoming_message）：
      ① 消息前：在 session_store._lock 内读取当前 session_id（pre_session_id），无 IO
      ② await handle_message(event)：内部 asyncio.create_task 启动后台任务立即返回
      ③ await asyncio.sleep(0)：让出一次事件循环控制权，使后台任务执行到
         get_or_create_session（纯同步函数，在第一次 yield 前完成）
      ④ 消息后：再读 session_id（post_session_id）
      ⑤ 若不一致，说明发生了超时 reset，将 pre_session_id 追加到
         chats.json.sessionIdHistory（幂等）

    时序保证：
      - get_or_create_session 是纯同步函数（持 threading.Lock，无任何 await）
      - asyncio.sleep(0) 后，后台任务同步段（含 _save()）已执行完毕
      - _save() 采用 tmpfile → os.replace() + fsync 原子写入
"""

import asyncio
import base64  # noqa: F401  (kept for backwards-compat external imports)
import logging
import os
import uuid
from typing import List, Optional, Tuple

from gateway.platforms.base import MessageEvent, MessageType, get_image_cache_dir

from .config import (
    CHANNEL_KEY,
    DEFAULT_AGENT_ID,
    EVENT_CHAT_RESPONSE,
    EVENT_MESSAGE_PRIVATE,
    LOCALFILE_SCHEME,
    MEDIA_MAX_BYTES,
    generate_msg_id,
)
from .file_storage import (
    download_file_from_server,
    get_file_download_url,
    upload_file_to_server,
)
from .media import format_file_size, guess_mime_by_ext, parse_data_url
from .tenancy import resolve_effective_api_key, set_session_api_key
from .language_follow import LANGUAGE_FOLLOW_PROMPT

logger = logging.getLogger(__name__)

# UUID v4 白名单：允许 chatId 为空字符串（legacy）或标准 UUID v4。
# 防止路径穿越和注入（D6）。
import re as _re
_CHAT_ID_RE = _re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    _re.IGNORECASE,
)

# 子角色目录名来自外部 WebSocket 消息。只接受既有 Agent ID 的安全字符集，
# 禁止它影响 state.db 候选路径。
_AGENT_ID_RE = _re.compile(r'^[A-Za-z0-9_-]{1,128}$')


def _sanitize_chat_id(raw: str) -> str:
    """校验并返回清洗后的 chatId。

    - 空字符串 → 允许（legacy 路径）
    - UUID v4 格式 → 允许
    - 其他 → 记录警告并回退空字符串，防止路径穿越/注入（D6）
    """
    if not raw:
        return ""
    if _CHAT_ID_RE.match(raw):
        return raw
    logger.warning("[lightclaw] Invalid chatId rejected: %r", raw[:64])
    return ""


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
        self.ensure_platform_registration_for_current_home()
        self._fire_and_forget(event, data)
        self._generate_msg_id() or generate_msg_id()
    """

    def _history_state_db_paths(
        self,
        agent_id: str,
        sessions_dir: Optional[str],
    ) -> Optional[List[str]]:
        """返回当前角色的历史数据库候选路径，子库优先、主库兼容读取。

        子角色在自己的 ``HERMES_HOME`` 下运行，Core 会将其新消息写入
        ``workspace/{agentId}/state.db``；旧版本或升级前的同一会话可能仍有
        消息在主库。历史请求需同时读取两者并由 history 模块合并；这里仅提供
        路径，history 会先确认文件存在，因此点击历史列表不会创建数据库。
        """
        if not sessions_dir:
            return None

        from .history import _default_state_db_path

        main_state_db = _default_state_db_path(sessions_dir)
        if agent_id == DEFAULT_AGENT_ID:
            return [main_state_db]
        if not _AGENT_ID_RE.fullmatch(agent_id):
            logger.warning("[lightclaw] Invalid agentId for history: %r", agent_id)
            return None

        main_home = os.path.realpath(os.path.dirname(main_state_db))
        workspace_root = os.path.realpath(os.path.join(main_home, "workspace"))
        child_state_db = os.path.realpath(
            os.path.join(workspace_root, agent_id, "state.db")
        )
        try:
            if os.path.commonpath((workspace_root, child_state_db)) != workspace_root:
                logger.warning(
                    "[lightclaw] Agent history path escaped workspace: %r", agent_id,
                )
                return None
        except ValueError:
            logger.warning("[lightclaw] Invalid agent history path: %r", agent_id)
            return None
        return [child_state_db, main_state_db]

    def _agent_home_for_agent(
        self,
        agent_id: str,
        sessions_dir: Optional[str],
    ) -> Optional[str]:
        """根据主 sessions 目录推导子角色 Home，并校验路径未逃出 workspace。"""
        if not sessions_dir:
            return None
        if agent_id == DEFAULT_AGENT_ID:
            return os.path.realpath(os.path.dirname(os.path.abspath(sessions_dir)))
        if not _AGENT_ID_RE.fullmatch(agent_id):
            logger.warning("[lightclaw] Invalid agentId for agent Home: %r", agent_id)
            return None

        main_home = os.path.realpath(os.path.dirname(os.path.abspath(sessions_dir)))
        workspace_root = os.path.realpath(os.path.join(main_home, "workspace"))
        agent_home = os.path.realpath(os.path.join(workspace_root, agent_id))
        try:
            if os.path.commonpath((workspace_root, agent_home)) != workspace_root:
                logger.warning("[lightclaw] Agent Home escaped workspace: %r", agent_id)
                return None
        except ValueError:
            logger.warning("[lightclaw] Invalid agent Home path: %r", agent_id)
            return None
        return agent_home

    def _bind_round_usage_context(
        self,
        sender: str,
        agent_id: str,
    ) -> Tuple[object, Optional[str]]:
        """将本轮 token 统计绑定到当前角色实际写入的 state.db 所在目录。

        Core 在子角色 Home 下会将正文与累计 token 写入子 ``state.db``，故
        tracker 和 usage sidecar 必须绑定子目录。但 v0.20+ 的 SessionStore
        实例仍可能持有主 Home 的 ``sessions.json``；sessionId 映射由
        ``_resolve_usage_session_id`` 单独处理，不能再假设它与 state.db 同目录。
        """
        main_sessions_dir = getattr(self, "_sessions_dir", None)
        agent_home = self._agent_home_for_agent(agent_id, main_sessions_dir)
        sessions_dir = (
            os.path.join(agent_home, "sessions")
            if agent_home else main_sessions_dir
        )
        if not sessions_dir:
            return getattr(self, "_usage_tracker", None), None

        canonical_dir = os.path.realpath(sessions_dir)
        trackers = getattr(self, "_usage_trackers_by_sessions_dir", None)
        if trackers is None:
            trackers = {}
            self._usage_trackers_by_sessions_dir = trackers
        tracker = trackers.get(canonical_dir)
        if tracker is None:
            from .usage_tracker import SessionUsageTracker

            tracker = SessionUsageTracker(sessions_dir=canonical_dir)
            trackers[canonical_dir] = tracker
        self._round_usage_context[sender] = (tracker, canonical_dir)
        logger.info(
            "[lightclaw][usage] bind round context: sender=%s agent_id=%s "
            "sessions_dir=%s",
            sender, agent_id, canonical_dir,
        )
        return tracker, canonical_dir

    def _resolve_usage_session_id(
        self,
        session_key: str,
        state_sessions_dir: Optional[str],
    ) -> Optional[str]:
        """按子 Home 优先、主 Home 回退解析本轮 sessionId。

        子角色 state.db 与主 Home 的 SessionStore 在 v0.20+ 可以同时存在：
        前者保存正文和累计 token，后者仍写 ``sessions/sessions.json`` 映射。
        因此先尝试正文所在 Home；缺少映射文件时，再读取主 Home 的索引。该
        方法只解析 sessionId，不会创建目录或修改任意会话数据。
        """
        from .history import resolve_session_id

        candidate_dirs: List[str] = []
        for directory in (state_sessions_dir, getattr(self, "_sessions_dir", None)):
            if not directory:
                continue
            canonical_dir = os.path.realpath(directory)
            if canonical_dir not in candidate_dirs:
                candidate_dirs.append(canonical_dir)

        for sessions_dir in candidate_dirs:
            session_id = resolve_session_id(session_key, sessions_dir)
            if session_id:
                return session_id
        return None

    # ------------------------------------------------------------------
    # Incoming message dispatcher
    # ------------------------------------------------------------------

    async def _handle_incoming_message(self, data: dict) -> None:
        """
        Handle a message:private inbound event.
        Mirrors: handleIncomingMessage in inbound.ts
        """
        sender  = data.get("from", "")
        content = data.get("content", "")
        msg_id  = data.get("msgId", "")
        kind    = data.get("kind", "text")
        files   = data.get("files") or []

        # Echo prevention + control-message filter
        if sender == self._bot_client_id:
            return
        if kind and kind != "text":
            return
        if not (content and content.strip()) and not files:
            return

        # ── 跨 Reset 检测：消息前快照（同步，读内存，无 IO）────────────────
        # chatId 经白名单校验（D6），防止路径穿越；agentId 缺省回退 main。
        # 前端将 chatId 放在顶层或 extra.chatId，两处均兼容。
        chat_id = _sanitize_chat_id(
            (data.get("chatId") or (data.get("extra") or {}).get("chatId") or "").strip()
        )
        # 从消息体读取 agentId，缺省时回退到 DEFAULT_AGENT_ID（"main"）。
        agent_id = (data.get("agentId") or "").strip() or DEFAULT_AGENT_ID
        if agent_id != DEFAULT_AGENT_ID and not _AGENT_ID_RE.fullmatch(agent_id):
            logger.warning("[lightclaw] Invalid agentId rejected: %r", agent_id)
            return
        # 记录本轮业务会话上下文，供 outbound 还原 inbound 一致的 sessionKey
        # （outbound 的 stop_typing / _persist_turn_usage 只能拿到 sender，
        # 没有这层映射就拼不出带 chatId 后缀的 key，导致 usage sidecar 无法落盘）。
        self._round_chat_ctx[sender] = (chat_id, agent_id)
        source = self._build_session_source(sender, chat_id, agent_id=agent_id)
        # 子角色的 session store 位于其 Home；此时 Core 尚未切换 ContextVar，
        # 读取主 store 会把同名主会话误当成子会话，故只让主角色走内存快照。
        pre_session_id = (
            self._peek_session_id(source)
            if agent_id == DEFAULT_AGENT_ID else None
        )
        usage_tracker, sessions_dir_for_tracker = self._bind_round_usage_context(
            sender, agent_id,
        )

        # Register sessionKey → apiKey so tool executions within this
        # session can resolve the tenant's apiKey via ctx.sessionKey alone.
        # Must run BEFORE any file processing (upload uses the same key).
        # Mirrors TS inbound.ts L89-97.
        session_key = self._build_session_key(sender, chat_id, agent_id=agent_id)
        effective_key = resolve_effective_api_key(sender_id=sender)
        set_session_api_key(session_key, effective_key)

        # If a previous round is still open (e.g. /new response didn't get a
        # finalize), close it with typing_stop before starting a new round.
        old_round = self._round_ids.get(sender)
        if old_round:
            self._fire_and_forget(
                EVENT_MESSAGE_PRIVATE,
                self._build_message(sender, "", kind="typing_stop", msg_id=old_round),
            )

        # Create a fresh round for this new conversation turn.
        self._clear_round_id(sender)
        # Drop any "last closed round" reservation from the previous turn.
        # From now on, output for this chat must use the fresh round msgId.
        self._last_round_id.pop(sender, None)
        # Reset per-turn usage state and snapshot the token baseline so
        # stop_typing can compute this turn's delta.
        self._round_usage_emitted.pop(sender, None)
        # 上一轮可能已由流式 finalize 发送终态；新轮必须移除该标记，
        # 否则恰好复用 msgId 的极端场景会错误跳过新的 typing_stop。
        self._round_terminal_emitted.pop(sender, None)
        # Remember the inbound msgId for the usage frame's replyToMsgId.
        self._round_reply_to[sender] = msg_id

        # ── Baseline 建立（方案 A + D） ─────────────────────────────
        # 目标：baseline 必须与 stop_typing 阶段读到的 state.db 行**同源**。
        # 跨会话取行是「非默认会话 token 用量不展示」bug 的根因——默认会话
        # 累计值（如 137038）当作新会话 baseline，与新会话 current（15887）
        # 相减产生负 delta，被 clamp 到 0 后误判为 no_llm，实时帧不发、
        # sidecar 不写，前端永久看不到这一轮的 token。
        #
        # 分支判定（严格化：仅在能确认是新会话首轮时才走 A 分支）：
        #   ① chat_id != "" 且 resolve_session_id **确定性地** 返回 None
        #      （成功查询，未找到 entry）→ 新建业务 chat 的首轮：Hermes 尚未
        #      在 state.db 建行。显式落零 baseline，绕开 _read_session_row 的
        #      user_id 兜底（否则会取到默认会话的累计值污染 baseline）。
        #   ② chat_id != "" 且能拿到 session_id
        #      → 已有会话继续对话：按精确 session_id 读 state.db 快照。
        #   ③ chat_id == ""
        #      → legacy 默认会话（chatId 为空）：session_id 已能通过
        #        _peek_session_id 稳定拿到，走常规 snapshot 路径。
        #   ④ resolve_session_id 抛异常 → 无法判断是否为新会话，保守走
        #     snapshot_baseline（宽松 fallback 到 user_id）。stop_typing
        #     的 reset 兜底能覆盖后续错乱的场景。
        #
        # ``_peek_session_id`` 走 Hermes Core 的内存 ``session_store._entries`` 路径，
        # 在多 chat / lazy-load / 锁竞争场景下经常返回 ``None``（实测日志确认）。
        # 此时必须用文件路径 ``resolve_session_id``（读 sessions.json）兜底。
        baseline_session_id = pre_session_id
        # resolve_session_id 是否成功执行（即使返回 None 也算成功）：
        # 只有「成功查询且未找到」才是「新会话首轮」的必要条件；抛异常时
        # 我们不能推断这是新会话，必须保守走 snapshot 兜底。
        resolve_ok = True
        if baseline_session_id is None:
            try:
                baseline_session_id = self._resolve_usage_session_id(
                    session_key, sessions_dir_for_tracker,
                )
            except Exception as _exc:
                logger.debug(
                    "[lightclaw] baseline session_id fallback failed: %s", _exc,
                )
                baseline_session_id = None
                resolve_ok = False

        # 关键分支：新会话首轮的判定
        # 1) 业务 chat 首轮：chat_id 非空 + resolve 成功 + resolve 返回 None
        # 2) 非 main agent 默认会话首轮：chat_id 为空但 session 未创建
        is_new_chat_first = (
            bool(chat_id) and resolve_ok and baseline_session_id is None
        )
        is_new_default_agent = (
            not bool(chat_id) and agent_id != DEFAULT_AGENT_ID
            and baseline_session_id is None and resolve_ok
        )
        if is_new_chat_first or is_new_default_agent:
            # 方案 A：显式落零 baseline，绝不读 state.db
            usage_tracker.mark_new_session_baseline(
                sender, session_id=None,
            )
        else:
            usage_tracker.snapshot_baseline(
                sender, session_id=baseline_session_id,
            )

        logger.debug(
            "[lightclaw][usage] inbound enter: sender=%s chat_id=%s "
            "agent_id=%s pre_session_id=%s baseline_session_id=%s "
            "resolve_ok=%s new_chat_first_turn=%s",
            sender, chat_id, agent_id, pre_session_id, baseline_session_id,
            resolve_ok, is_new_chat_first,
        )
        # Clear per-turn file tracking state.
        getattr(self, "_pending_file_paths", {}).pop(sender, None)
        getattr(self, "_delivered_paths", {}).pop(sender, None)
        # Clear per-turn thinking_step counters / last-step cache.
        # 必须在新 round 开始时复位，否则 stepId / seq 会跨轮单调增长，
        # 前端按 stepId 合并行的逻辑会把旧轮 step 映射到本轮的 stepId 上。
        getattr(self, "_step_seq", {}).pop(sender, None)
        getattr(self, "_step_count", {}).pop(sender, None)
        getattr(self, "_last_tool_step", {}).pop(sender, None)
        # 同时清空本轮已发工具行去重集，新一轮工具调用允许重新发 thinking_step。
        getattr(self, "_emitted_tool_lines", {}).pop(sender, None)
        round_msg_id = self._get_or_create_round_id(sender)
        self._fire_and_forget(
            EVENT_MESSAGE_PRIVATE,
            self._build_message(sender, "", kind="typing_start", msg_id=round_msg_id),
        )
        logger.info("[lightclaw] typing_start sent: to=%s roundMsgId=%s", sender, round_msg_id)

        media_urls, media_types, attachment_desc = await self._process_files(
            files, sender, effective_key,
        )

        event = MessageEvent(
            text=(content or "") + attachment_desc,
            message_type=MessageType.TEXT,
            source=source,
            message_id=msg_id,
            media_urls=media_urls,
            media_types=media_types,
            channel_prompt=LANGUAGE_FOLLOW_PROMPT,
        )
        # ── 非 main agent：切换 HERMES_HOME，使 Core 加载子角色专属资源 ──
        # SOUL、skills、memory、cron 和 state.db 都跟随该子 Home；主配置文件
        # 通过软链接共享，工具集和授权元数据则由 adapter 的两个兼容钩子处理。
        # set_hermes_home_override 使用 ContextVar，协程级隔离，并发安全。
        if agent_id != DEFAULT_AGENT_ID:
            try:
                from hermes_constants import (
                    reset_hermes_home_override,
                    set_hermes_home_override,
                )

                main_hermes_home = os.path.realpath(
                    os.path.dirname(os.path.abspath(self._sessions_dir))
                )
                agent_home = self._agent_home_for_agent(agent_id, self._sessions_dir)
                if not agent_home:
                    logger.warning(
                        "[lightclaw] Unable to resolve child Home for agent %s", agent_id,
                    )
                    return
                os.makedirs(agent_home, exist_ok=True)
                # 子 Home 复用主 Home 的推理与认证配置，避免重复维护凭证。
                for shared_file in (".env", "auth.json", "config.yaml"):
                    source_path = os.path.join(main_hermes_home, shared_file)
                    target_path = os.path.join(agent_home, shared_file)
                    if os.path.exists(source_path) and not os.path.exists(target_path):
                        os.symlink(source_path, target_path)

                token = set_hermes_home_override(agent_home)
                try:
                    # v0.20 的平台注册按 Home 隔离；同步主条目后，子角色仍按
                    # 主平台的 allowlist / allow-all 规则接受入站用户。
                    self.ensure_platform_registration_for_current_home()
                    await self.handle_message(event)
                finally:
                    reset_hermes_home_override(token)
            except ImportError:
                # 旧 Hermes 没有 Home override 时保持原先降级行为：能回复，
                # 但不会加载子角色目录的独立资源。
                logger.warning(
                    "[lightclaw] hermes_constants not available, "
                    "skipping HERMES_HOME override for agent %s", agent_id,
                )
                await self.handle_message(event)
        else:
            await self.handle_message(event)

        # ── baseline relabel after session_id materialises（方案 A + D） ─────
        # 新会话首轮 inbound 时，sessions.json 尚未包含此 chat 的条目，
        # `baseline_session_id` 为 None，baseline 以 (sender, "") 维度落库。
        # handle_message 内部框架会为新会话建 state.db 行、写 sessions.json，
        # 到此 baseline 已经能通过 chat_id 反查到真实的 session_id。
        #
        # 关键点：**不能重新 snapshot state.db**——handle_message 里 LLM 已经跑过，
        # 累计值已经吸收了本轮的输入 token。重新读会把「起点 + 本轮消耗」当作
        # 起点，导致 delta 归零、本轮 token 丢失。
        #
        # 正确做法：把已经落库的 baseline（内存里的零基线或旧快照）
        # 从 (sender, old_sid) 键 relabel 到 (sender, new_sid) 键，
        # 数值不变。stop_typing 阶段用 new_sid 就能命中同一份 baseline。
        if usage_tracker is not None and chat_id:
            try:
                post_session_key = self._build_session_key(sender, chat_id, agent_id=agent_id)
                post_session_id = self._resolve_usage_session_id(
                    post_session_key, sessions_dir_for_tracker,
                )
                if post_session_id and post_session_id != baseline_session_id:
                    logger.info(
                        "[lightclaw][usage] baseline session_id resolved "
                        "post-handle_message: sender=%s chat_id=%s "
                        "session_key=%s old_session_id=%s new_session_id=%s",
                        sender, chat_id, post_session_key,
                        baseline_session_id, post_session_id,
                    )
                    # 保留数值，只换 key —— 不重新读 state.db。
                    usage_tracker.correct_baseline_after_session_id(
                        sender,
                        old_session_id=baseline_session_id,
                        new_session_id=post_session_id,
                    )
            except Exception as _exc:
                logger.debug(
                    "[lightclaw] baseline relabel failed: %s", _exc,
                )

        # ── 跨 Reset 检测：消息后检测 ────────────────────────────────────
        # 触发条件：Hermes Core 在 get_or_create_session 内部超时自动 reset
        # （idle/daily），本轮的 session_id 在 handle_message 中被换成新的。
        # 我们需要把旧 sessionId 追加到 chats.json.sessionIdHistory，让后续
        # 的历史请求能通过跨 session 合并读到 reset 前的消息。
        #
        # 为什么用「消息前 vs 消息后」比对：Core 的 reset 是内部行为，没暴露
        # hook；只能通过前后 session_id 快照对比来推断。
        # 为什么用 asyncio.sleep(0) 循环：handle_message 内部 create_task
        # 立即返回，我们需要让出控制权等后台任务的同步段（含 _save()）跑完，
        # 才能读到 reset 后的稳定 session_id。5 次 yield 足够覆盖同步段。
        if pre_session_id:
            try:
                post_session_id = pre_session_id
                for _ in range(5):
                    await asyncio.sleep(0)
                    post_session_id = self._peek_session_id(source)
                    if post_session_id and post_session_id != pre_session_id:
                        break

                if post_session_id and post_session_id != pre_session_id:
                    logger.info(
                        "[lightclaw] Auto-reset detected for sender=%s chatId=%s: "
                        "%s → %s; appending to sessionIdHistory",
                        sender, chat_id or "<legacy>", pre_session_id, post_session_id,
                    )
                    await self._append_session_history_on_reset(
                        sender, chat_id, pre_session_id, agent_id=agent_id,
                    )
            except Exception as _exc:
                # Reset 检测失败不阻塞主流程，仅记录警告
                logger.warning(
                    "[lightclaw] Post-reset detection failed for sender=%s: %s",
                    sender, _exc,
                )

    def _build_session_source(self, user_id: str, chat_id: str = "",
                               agent_id: str = DEFAULT_AGENT_ID):
        """构建 source，供 Core _generate_session_key 反查 sessionId。

        隔离策略：不注入 source.profile（multiplex_profiles=false），核心通过
        thread_id 区分会话。非 main agent 且 chatId 为空时，thread_id 设为
        ``__default_{agent_id}`` 防止 Core session 恢复逻辑合并不同 agent 的
        默认会话（hermes_state fallback 查询不含 profile 字段）。
        """
        import dataclasses
        effective_thread_id = chat_id or None
        if not chat_id and agent_id != DEFAULT_AGENT_ID:
            effective_thread_id = f"__default_{agent_id}"
        return self.build_source(
            chat_id=user_id, chat_type="dm",
            user_id=user_id, user_name=user_id,
            thread_id=effective_thread_id,
        )

    def _build_session_key(self, user_id: str, chat_id: str = "",
                           agent_id: str = DEFAULT_AGENT_ID) -> str:
        """构建 lightclaw 会话键，与 _build_session_source 一一对应。

        namespace 固定 agent:main（不开启 multiplex_profiles），通过 thread_id
        实现不同 agent 的默认会话隔离。
        格式：agent:main:{CHANNEL_KEY}:dm:{user_id}[:{chat_id|__default_{agent_id}}]
        """
        if chat_id:
            return f"agent:main:{CHANNEL_KEY}:dm:{user_id}:{chat_id}"
        if agent_id != DEFAULT_AGENT_ID:
            return f"agent:main:{CHANNEL_KEY}:dm:{user_id}:__default_{agent_id}"
        return f"agent:main:{CHANNEL_KEY}:dm:{user_id}"

    def _peek_session_key(self, source) -> Optional[str]:
        """防御性读取 source 对应 sessionKey。"""
        session_store = getattr(self, "session_store", None)
        if session_store is None:
            return None
        generate_session_key = getattr(session_store, "_generate_session_key", None)
        if not callable(generate_session_key):
            return None
        try:
            return generate_session_key(source)
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("[lightclaw] _peek_session_key failed: %s", exc)
            return None

    def _peek_session_id(self, source) -> Optional[str]:
        """防御性读取 source 对应 sessionId；失败时返回 None。"""
        session_store = getattr(self, "session_store", None)
        if session_store is None:
            return None

        lock = getattr(session_store, "_lock", None)
        entries = getattr(session_store, "_entries", None)
        ensure_loaded = getattr(session_store, "_ensure_loaded_locked", None)
        session_key = self._peek_session_key(source)

        if lock is None or entries is None or not callable(ensure_loaded) or not session_key:
            return None

        try:
            with lock:
                ensure_loaded()
                entry = entries.get(session_key)
            return entry.session_id if entry else None
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("[lightclaw] _peek_session_id failed: %s", exc)
            return None

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

        支持跨 Reset 历史合并：
          - 当请求携带 chatId 时，从 chats.json 读取 sessionIdHistory，
            合并所有历史 sessionId 的消息（ensureSessionInHistory 幂等兜底）。
          - chatId 缺失（旧前端）时退回原逻辑，向前兼容。

        Mirrors: handlers.ts → EVENT_HISTORY_REQUEST handler.
        """
        from .config import EVENT_HISTORY_RESPONSE
        from .history import read_session_history, read_session_histories_by_ids

        user_id = data.get("from", "")
        if not user_id or user_id == self._bot_client_id:
            return

        limit = data.get("limit") or 200
        chat_only = data.get("chatOnly", True)
        # 前端将 chatId 放在顶层或 extra.chatId，两处均兼容。
        chat_id = _sanitize_chat_id(
            (data.get("chatId") or (data.get("extra") or {}).get("chatId") or "").strip()
        )
        agent_id = (data.get("agentId") or "").strip() or DEFAULT_AGENT_ID

        sessions_dir = getattr(self, "_sessions_dir", None)
        session_key = self._build_session_key(user_id, chat_id, agent_id=agent_id)
        history_state_db_paths = self._history_state_db_paths(agent_id, sessions_dir)

        messages: list = []

        from .history import resolve_session_id
        from .chat_manager import ChatManager

        if history_state_db_paths is None:
            logger.warning(
                "[lightclaw] History request rejected invalid Agent: agentId=%s",
                agent_id,
            )
        elif sessions_dir:
            history_ids: list = []
            try:
                chat_mgr = ChatManager(sessions_dir)
                # ensureSessionInHistory：把当前 sessionId 写入 sessionIdHistory（幂等兜底）
                current_session_id = resolve_session_id(session_key, sessions_dir)
                if current_session_id:
                    chat_mgr.append_session_history(
                        agent_id, user_id, chat_id, current_session_id,
                    )
                history_ids = chat_mgr.get_session_id_history(
                    agent_id, user_id, chat_id,
                )
            except Exception as exc:  # pylint: disable=broad-except
                # chats.json 读写异常不得击穿历史请求，降级为单 session 读取
                logger.warning(
                    "[lightclaw] History request: chats.json access failed "
                    "(userId=%s chatId=%s agentId=%s): %s",
                    user_id, chat_id or "<legacy>", agent_id, exc,
                )
                history_ids = []

            if history_ids:
                messages = read_session_histories_by_ids(
                    history_ids,
                    sessions_dir,
                    state_db_paths=history_state_db_paths,
                    limit=limit,
                    chat_only=chat_only,
                )
                logger.info(
                    "[lightclaw] History request (merge): userId=%s chatId=%s agentId=%s "
                    "sessionCount=%d found=%d",
                    user_id, chat_id or "<legacy>", agent_id,
                    len(history_ids), len(messages),
                )

        if not messages and history_state_db_paths is not None:
            messages = read_session_history(
                session_key,
                sessions_dir,
                state_db_paths=history_state_db_paths,
                limit=limit,
                chat_only=chat_only,
            )
            logger.info(
                "[lightclaw] History request (fallback single): userId=%s chatId=%s agentId=%s found=%d",
                user_id, chat_id or "<legacy>", agent_id, len(messages),
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

    async def _append_session_history_on_reset(
        self,
        user_id: str,
        chat_id: str,
        old_session_id: str,
        *,
        agent_id: str = DEFAULT_AGENT_ID,
    ) -> None:
        """将旧 sessionId 追加到 chats.json 的 sessionIdHistory（reset 检测后调用）。

        在 asyncio 执行器外直接调用 ChatManager（同步 IO），适合 I/O 轻量的场景。
        如果 sessions_dir 未配置，静默跳过。
        """
        sessions_dir = getattr(self, "_sessions_dir", None)
        if not sessions_dir:
            logger.debug(
                "[lightclaw] _append_session_history_on_reset: sessions_dir not set, skip"
            )
            return
        try:
            from .chat_manager import ChatManager
            chat_mgr = ChatManager(sessions_dir)
            written = chat_mgr.append_session_history(
                agent_id, user_id, chat_id, old_session_id,
            )
            if not written:
                logger.debug(
                    "[lightclaw] sessionId %s already in history or chatId=%s not found",
                    old_session_id, chat_id,
                )
        except Exception as exc:
            logger.warning(
                "[lightclaw] Failed to append sessionIdHistory for chatId=%s: %s",
                chat_id, exc,
            )

    async def _handle_chat_request(self, data: dict) -> None:
        """处理 chat:request（list/create/update/delete/clearContext）。"""
        from .chat_manager import ChatManager

        req_type = (data.get("type") or "").strip()
        user_id = (data.get("from") or "").strip()
        # 前端将 chatId 放在顶层或 extra.chatId，两处均兼容。
        chat_id = _sanitize_chat_id(
            (data.get("chatId") or (data.get("extra") or {}).get("chatId") or "").strip()
        )
        agent_id = (data.get("agentId") or "").strip() or DEFAULT_AGENT_ID

        if not user_id or user_id == self._bot_client_id:
            return

        sessions_dir = getattr(self, "_sessions_dir", None)
        if not sessions_dir:
            logger.warning("[lightclaw] _handle_chat_request skipped: sessions_dir not set")
            return

        chat_manager = ChatManager(sessions_dir)
        payload = {
            "msgId": generate_msg_id(),
            "type": req_type,
            "from": self._bot_client_id,
            "to": user_id,
            "agentId": agent_id,
        }

        try:
            if req_type == "list":
                chats = chat_manager.list_chats(agent_id, user_id)
                payload["chats"] = [chat.to_dict() for chat in chats]
            elif req_type == "create":
                new_chat = chat_manager.create_chat(agent_id, user_id)
                payload["chats"] = [new_chat.to_dict()]
            elif req_type == "update":
                title = (data.get("title") or "").strip()
                updated = chat_manager.update_chat(agent_id, user_id, chat_id, title)
                payload["chats"] = [updated.to_dict()] if updated else []
            elif req_type == "delete":
                deleted = chat_manager.delete_chat(agent_id, user_id, chat_id)
                payload["chats"] = [deleted.to_dict()] if deleted else []
            elif req_type == "clearContext":
                await self._handle_clear_context(
                    chat_manager=chat_manager,
                    agent_id=agent_id,
                    user_id=user_id,
                    chat_id=chat_id,
                    payload=payload,
                )
                return
            else:
                logger.warning("[lightclaw] unknown chat:request type: %r", req_type)
                return

            self._fire_and_forget(EVENT_CHAT_RESPONSE, payload)
        except Exception:  # pylint: disable=broad-except
            logger.exception("[lightclaw] _handle_chat_request failed type=%s", req_type)

    async def _handle_clear_context(
        self,
        *,
        chat_manager,
        agent_id: str = DEFAULT_AGENT_ID,
        user_id: str,
        chat_id: str,
        payload: dict,
    ) -> None:
        """clearContext：reset 当前 session，并把旧 sessionId 追加到历史路由。"""
        source = self._build_session_source(user_id, chat_id, agent_id=agent_id)
        pre_session_id = self._peek_session_id(source)
        session_key = self._peek_session_key(source)

        if session_key:
            try:
                await self.reset_session(session_key)
            except Exception:  # pylint: disable=broad-except
                logger.exception("[lightclaw] reset_session failed for key=%s", session_key)

        if pre_session_id:
            try:
                chat_manager.append_session_history(
                    agent_id, user_id, chat_id, pre_session_id,
                )
            except Exception:  # pylint: disable=broad-except
                logger.exception(
                    "[lightclaw] clearContext append_session_history failed: "
                    "agentId=%s user=%s chat=%s",
                    agent_id, user_id, chat_id or "<legacy>",
                )

        chat_manager.touch_chat(agent_id, user_id, chat_id)
        payload["chatId"] = chat_id
        payload["chats"] = []
        self._fire_and_forget(EVENT_CHAT_RESPONSE, payload)

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
        req_agent_id = (data.get("agentId") or "").strip() or DEFAULT_AGENT_ID

        sessions = list_sessions(
            getattr(self, "_sessions_dir", None),
            owner_uin=owner_uin,
            channel_key=CHANNEL_KEY,
            agent_id=req_agent_id,
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

    # ==================================================================
    # Agent 列表查询（只读）
    # ==================================================================

    async def _handle_agents_request(self, data: dict) -> None:
        from .config import EVENT_AGENTS_RESPONSE, generate_msg_id
        from .agent_manager import AgentManager

        sessions_dir = getattr(self, "_sessions_dir", None)
        if not sessions_dir:
            return
        try:
            agent_list = AgentManager(sessions_dir).list()
        except Exception:
            agent_list = []
        self._fire_and_forget(EVENT_AGENTS_RESPONSE, {
            "requestId": data.get("requestId"),
            "msgId":     generate_msg_id(),
            "from":      self._bot_client_id,
            "to":        (data.get("from") or "").strip(),
            "agents":    agent_list,
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
