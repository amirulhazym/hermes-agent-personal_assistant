"""
Per-UIN WebSocket session.

每个 LightClaw 子账号 (UIN) 占用一条独立 WS 连接、独立 ReliableEmitter、
独立 ACK 表。原 :class:`NativeSocketMixin` 的全部状态机都搬到这里，
作为 *实例字段* 而非 mixin 上的属性，从而让一个 ``LightClawAdapter`` 同时
管理 N 条互不干扰的会话。

设计原则：
    - 协议层 *哑* 传输：连接 / 重连 / 心跳 / 收发 / ACK。
    - 收到帧 → 通过 ``on_raw(session, raw)`` 把 *自身 + 原始帧* 同步派发回
      上层 adapter，绝不在 session 内 await 业务。
    - 内置 pending ACK 表 + ReliableEmitter，与其它 session 完全隔离。
    - 单 session 销毁/断开不影响其它 session。

镜像参考：
    - ``socket/native_socket.py``（被取代）
    - OpenClaw ``packages/lightclaw/src/account.ts``
"""

import asyncio
import json
import logging
import random
import urllib.parse
from typing import Awaitable, Callable, Dict, Optional, Tuple

from ..config import (
    API_PATH_TICKET,
    RECONNECT_DELAY_BASE,
    RECONNECT_DELAY_MAX,
    SOCKET_PATH,
)
from .reliable_emitter import ReliableEmitter

logger = logging.getLogger(__name__)


# Type alias: adapter 注册到每个 session 上的回调签名
#   - session: 当前回调来源的 session 实例
#   - raw:     原始 WS 文本帧
RawHandler = Callable[["_PerUinSession", str], Awaitable[None]]


class _PerUinSession:
    """
    一个 UIN ↔ 一条 WS 连接的封装。

    生命周期：
        ``await start()``   建立首次连接（含 fetch ticket）
        ``await stop()``    主动关闭连接、清理 pending、销毁 emitter

    每个 session 对外暴露：
        ``api_key``         : 本 session 绑定的 LightClaw API Key
        ``uin``             : 解析得到的 UIN（首次握手前为空，可后填）
        ``socket_id``       : 服务端握手分配的 socket id
        ``connected``       : 当前是否已连上 WS
        ``reliable``        : 该 session 专属的 :class:`ReliableEmitter`
        ``first_connect_event`` : 首次连上 WS 后被 set，用于 adapter.connect 同步等待
    """

    # ------------------------------------------------------------------
    # 构造 & 生命周期
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        api_key: str,
        uin: str,
        ws_base_url: str,
        api_base_url: str,
        aiohttp_session,                  # aiohttp.ClientSession
        on_raw: RawHandler,
        on_connected: Optional[Callable[["_PerUinSession"], None]] = None,
        on_disconnected: Optional[Callable[["_PerUinSession"], None]] = None,
        log_prefix: Optional[str] = None,
    ) -> None:
        self.api_key = api_key
        self.uin = uin or ""
        self._ws_base_url = ws_base_url
        self._api_base_url = api_base_url
        self._http = aiohttp_session
        self._on_raw = on_raw
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._log_prefix = log_prefix or f"[lightclaw uin={self.uin or '?'}]"

        # 运行时状态
        self.socket_id: str = ""
        self.connected: bool = False
        self._stopped: bool = False
        self._ws = None                                # aiohttp.ClientWebSocketResponse
        self._connection_task: Optional[asyncio.Task] = None
        self.first_connect_event: asyncio.Event = asyncio.Event()

        # Pending ACK 表（msgId → (timer, callback)）
        self._pending_acks: Dict[str, Tuple[asyncio.TimerHandle, Callable]] = {}

        # 每 session 独立的可靠发送器
        self.reliable: ReliableEmitter = ReliableEmitter(
            ws_emit=self._ws_emit,
            ws_emit_with_timeout=self._ws_emit_with_timeout,
            prefix=self._log_prefix,
        )

    async def start(self) -> None:
        """启动后台连接循环。立即返回，首次连接完成由 ``first_connect_event`` 通知。"""
        if self._connection_task is not None:
            return
        self._stopped = False
        self.first_connect_event.clear()
        self._connection_task = asyncio.create_task(self._connection_loop())

    async def stop(self) -> None:
        """主动关闭：取消后台任务、关 ws、销毁 reliable、清 pending。"""
        self._stopped = True
        self._flush_pending_acks(ConnectionError("session stop"))
        try:
            self.reliable.destroy()
        except Exception:
            pass

        if self._connection_task is not None:
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass
            self._connection_task = None

        if self._ws is not None and not getattr(self._ws, "closed", True):
            try:
                await self._ws.close()
            except Exception:
                pass
        self._ws = None
        self.connected = False

    # ------------------------------------------------------------------
    # ACK 表（与 NativeSocketMixin 一一对应）
    # ------------------------------------------------------------------

    def _ws_emit(self, event: str, data: dict) -> None:
        """Fire-and-forget 同步发送。镜像 TS ``socket.emit(event, data)``。"""
        ws = self._ws
        if ws is None or getattr(ws, "closed", True):
            return
        try:
            task = asyncio.ensure_future(ws.send_json({"event": event, "data": data}))
            # 防止 "Task exception was never retrieved" 警告：
            # WS 在发送瞬间关闭时 send_json 会抛出，需要主动消费异常。
            task.add_done_callback(
                lambda t: t.exception() if not t.cancelled() else None
            )
        except Exception as exc:
            logger.debug("%s _ws_emit send failed: %s", self._log_prefix, exc)

    def _ws_emit_with_timeout(
        self,
        event: str,
        data: dict,
        timeout_ms: int,
        callback: Callable[[Optional[Exception]], None],
    ) -> None:
        """同步发送 + 注册 ACK 回调（带超时）。镜像 TS ``socket.timeout(ms).emit(...)``。"""
        ws = self._ws
        if ws is None or getattr(ws, "closed", True):
            callback(ConnectionError("not connected"))
            return

        pending_key = data.get("msgId") or f"_ack_{id(data)}"

        # 同 msgId 重试时取消旧 timer
        existing = self._pending_acks.get(pending_key)
        if existing is not None:
            existing[0].cancel()

        loop = asyncio.get_running_loop()

        def _on_timeout() -> None:
            entry = self._pending_acks.pop(pending_key, None)
            if entry is not None:
                callback(TimeoutError("ACK timeout"))

        timer = loop.call_later(timeout_ms / 1000.0, _on_timeout)
        self._pending_acks[pending_key] = (timer, callback)

        try:
            task = asyncio.ensure_future(ws.send_json({"event": event, "data": data}))
            # 同 _ws_emit：消费 Task 异常，避免 "Task exception was never retrieved" 警告。
            task.add_done_callback(
                lambda t: t.exception() if not t.cancelled() else None
            )
        except Exception as exc:
            timer.cancel()
            self._pending_acks.pop(pending_key, None)
            callback(ConnectionError(f"send failed: {exc}"))

    def on_ws_ack(self, related_msg_id: str) -> None:
        """收到 ``message:ack`` 时由 adapter 派发到对应 session。"""
        entry = self._pending_acks.pop(related_msg_id, None)
        if entry is None:
            logger.debug(
                "%s ACK for unknown msgId=%s (already resolved)",
                self._log_prefix, related_msg_id,
            )
            return
        timer, callback = entry
        timer.cancel()
        callback(None)

    def _flush_pending_acks(self, err: Exception) -> None:
        """断线 / 销毁时一次性 fail 所有挂起回调。"""
        pending = self._pending_acks
        self._pending_acks = {}
        for timer, callback in pending.values():
            timer.cancel()
            try:
                callback(err)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Ticket & WS URL
    # ------------------------------------------------------------------

    async def _fetch_ticket(self) -> str:
        """每次连接前用 *自己* 的 api_key 取 ticket。

        ⚠️ 这里是与原 :class:`NativeSocketMixin` 最关键的差异——
        原实现写死 ``self._api_keys[0]``，导致非首位 UIN 永远拿不到 ticket。
        """
        import aiohttp

        url = f"{self._api_base_url}{API_PATH_TICKET}"
        headers = {"authorization": f"Bearer {self.api_key}", "x-product": "channel"}

        async with self._http.post(
            url, headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"POST /cgi/ticket HTTP {resp.status}")
            data = await resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"POST /cgi/ticket error: {data.get('message')}")
            ticket = data.get("data", {}).get("ticket", "")
            if not ticket:
                logger.warning(
                    "%s /cgi/ticket returned empty ticket, connecting without it",
                    self._log_prefix,
                )
            return ticket

    def _build_ws_url(self, ticket: str) -> str:
        """拼 WS URL —— enableMultiLogin=false 仅约束同一 apiKey 不重复登录，多 UIN 不冲突。"""
        base = self._ws_base_url.rstrip("/")
        path = SOCKET_PATH
        query = (
            f"?ticket={urllib.parse.quote(ticket, safe='')}&enableMultiLogin=false"
            if ticket else ""
        )
        return f"{base}{path}{query}"

    # ------------------------------------------------------------------
    # 连接循环
    # ------------------------------------------------------------------

    async def _connection_loop(self) -> None:
        """指数退避重连循环（镜像原 ``_connection_loop``，但作用域限制在本 session）。

        故障隔离（D3）：单 session 永久无法连接（apiKey 被吊销 / 服务端拒签）
        不应阻塞其它 session，也不应每次失败都打 WARNING 把日志刷穿。
        ``LOG_LOUD_THRESHOLD`` 之内按原级别播报，超出后降级到 DEBUG，
        只在间隔性的 ``HEARTBEAT_EVERY`` 次重试时回到 INFO，让运维仍可
        看到"这条 session 一直在尝试"。
        """
        LOG_LOUD_THRESHOLD = 5    # 前 5 次重试按 INFO/WARN 全量播报
        HEARTBEAT_EVERY   = 30    # 之后每 30 次回到 INFO 留一次心跳日志

        attempts = 0
        while not self._stopped:
            try:
                ticket = await self._fetch_ticket()
                ws_url = self._build_ws_url(ticket)
                if attempts < LOG_LOUD_THRESHOLD:
                    logger.info("%s Connecting to %s", self._log_prefix, ws_url[:80])
                else:
                    logger.debug("%s Connecting to %s", self._log_prefix, ws_url[:80])
                await self._run_once(ws_url)
                attempts = 0   # 成功一次重置计数
            except asyncio.CancelledError:
                return
            except Exception as exc:
                if attempts < LOG_LOUD_THRESHOLD:
                    logger.warning(
                        "%s Connection session ended: %s", self._log_prefix, exc,
                    )
                elif attempts % HEARTBEAT_EVERY == 0:
                    logger.info(
                        "%s Still failing after %d attempts: %s",
                        self._log_prefix, attempts, exc,
                    )
                else:
                    logger.debug(
                        "%s Connection session ended (attempt=%d): %s",
                        self._log_prefix, attempts, exc,
                    )

            if self._stopped:
                return

            attempts += 1
            base_delay = min(RECONNECT_DELAY_BASE * (2 ** (attempts - 1)), RECONNECT_DELAY_MAX)
            delay = base_delay * (0.8 + random.random() * 0.4)
            if attempts <= LOG_LOUD_THRESHOLD:
                logger.info(
                    "%s Reconnecting in %.1fs (attempt %d)",
                    self._log_prefix, delay, attempts,
                )
            else:
                logger.debug(
                    "%s Reconnecting in %.1fs (attempt %d)",
                    self._log_prefix, delay, attempts,
                )
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return

    async def _run_once(self, ws_url: str) -> None:
        """单次 WS 会话：建连 → 接收循环 → 清理。"""
        import aiohttp

        ws = await self._http.ws_connect(
            ws_url,
            heartbeat=30,
            timeout=aiohttp.ClientTimeout(total=None, connect=15),
        )
        self._ws = ws

        try:
            self.socket_id = ""
            self.connected = True
            self.first_connect_event.set()
            if self._on_connected is not None:
                try:
                    self._on_connected(self)
                except Exception as exc:
                    logger.warning("%s on_connected callback error: %s", self._log_prefix, exc)
            self.reliable.resume()

            async for raw_msg in ws:
                if self._stopped:
                    break
                if raw_msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        await self._on_raw(self, raw_msg.data)
                    except Exception as exc:
                        logger.error("%s on_raw error: %s", self._log_prefix, exc)
                elif raw_msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
        finally:
            self._ws = None
            self.connected = False
            # 失败时把 pending 全 fail，让上层 await 立即返回
            self._flush_pending_acks(ConnectionError("disconnect"))
            self.reliable.pause()
            if not ws.closed:
                try:
                    await ws.close()
                except Exception:
                    pass
            if self._on_disconnected is not None:
                try:
                    self._on_disconnected(self)
                except Exception as exc:
                    logger.warning(
                        "%s on_disconnected callback error: %s", self._log_prefix, exc,
                    )
            logger.info(
                "%s Disconnected (socket_id=%s)",
                self._log_prefix, self.socket_id or "?",
            )

    # ------------------------------------------------------------------
    # 便捷封装：让 adapter 不直接碰 reliable
    # ------------------------------------------------------------------

    def emit_fire_and_forget(self, event: str, data: dict) -> None:
        self.reliable.emit_fire_and_forget(event, data)

    async def emit_with_ack(
        self, event: str, data: dict, msg_id: Optional[str] = None,
    ) -> bool:
        return await self.reliable.emit_with_ack(event, data, msg_id)
