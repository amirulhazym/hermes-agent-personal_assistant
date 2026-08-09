"""
LightClaw — 可靠发送器 (ReliableEmitter)
Mirrors: src/socket/reliable-emitter.ts

设计哲学（对齐 TS 版）：
    - emit_fire_and_forget(): 同步发送，不等 ACK，不重试。用于控制帧。
    - emit_with_ack(): 可靠发送 + 自动重试。返回 asyncio.Future<bool>。
    - 所有 ACK 通过 callback 派发，不阻塞任何协程。
    - pause/resume 控制断线期间的重试调度。
    - 每条消息注入 idempotencyKey，服务端/前端据此去重。
"""

import asyncio
import logging
import random
import time
from typing import Callable, Dict, Optional

from ..config import (
    EMIT_ACK_TIMEOUT,
    EMIT_MAX_RETRIES,
    EMIT_PENDING_MAX,
    EMIT_RETRY_BASE_DELAY,
    EMIT_RETRY_MAX_DELAY,
)

logger = logging.getLogger(__name__)


class _PendingMsg:
    """One outbound message waiting for server ACK (reliable path only)."""

    __slots__ = (
        "emit_id", "msg_id", "event", "data", "retry_count",
        "created_at", "retry_timer", "resolve",
    )

    def __init__(
        self,
        emit_id: str,
        msg_id: Optional[str],
        event: str,
        data: dict,
        resolve: Callable[[bool], None],
    ):
        self.emit_id = emit_id
        self.msg_id = msg_id
        self.event = event
        self.data = data
        self.retry_count = 0
        self.created_at = time.monotonic()
        self.retry_timer: Optional[asyncio.TimerHandle] = None
        self.resolve = resolve


class ReliableEmitter:
    """
    业务可靠性层 — 在 NativeSocketMixin 的 callback 之上加重试逻辑。
    Mirrors: ReliableEmitter in reliable-emitter.ts

    使用方式::

        emitter = ReliableEmitter(
            ws_emit=adapter._ws_emit,
            ws_emit_with_timeout=adapter._ws_emit_with_timeout,
            prefix="[lightclaw]",
        )
        # fire-and-forget (控制帧)
        emitter.emit_fire_and_forget("message:private", data)

        # 可靠发送 (关键帧)
        ok = await emitter.emit_with_ack("message:private", data, msg_id)
    """

    def __init__(
        self,
        ws_emit: Callable[[str, dict], None],
        ws_emit_with_timeout: Callable[
            [str, dict, int, Callable[[Optional[Exception]], None]], None
        ],
        prefix: str = "[lightclaw]",
    ):
        self._ws_emit = ws_emit
        self._ws_emit_with_timeout = ws_emit_with_timeout
        self._prefix = prefix

        self._pending: Dict[str, _PendingMsg] = {}
        self._paused = False
        self._counter = 0

    # ---- public API --------------------------------------------------------

    def emit_fire_and_forget(self, event: str, data: dict) -> None:
        """Send one frame — no ACK, no retry, no blocking.

        Injects ``idempotencyKey`` for client-side dedup/ordering, then
        calls the raw socket emit.  Replaces the old
        ``asyncio.create_task(emit_nowait(...))`` pattern.
        """
        emit_id = self._gen_id()
        enriched = {**data, "idempotencyKey": emit_id}
        self._ws_emit(event, enriched)

    async def emit_with_ack(
        self,
        event: str,
        data: dict,
        msg_id: Optional[str] = None,
    ) -> bool:
        """Reliable send — ACK + auto-retry.  Returns True on ACK, False on give-up.

        Mirrors TS ``emitWithAck``.  Internally bridges the callback-based
        socket layer to an ``asyncio.Future`` so callers can ``await``.
        """
        emit_id = self._gen_id()
        enriched = {**data, "idempotencyKey": emit_id}

        # Capacity protection: evict oldest on overflow
        self._evict_if_needed()

        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()

        def _resolve(ok: bool) -> None:
            if not future.done():
                future.set_result(ok)

        entry = _PendingMsg(emit_id, msg_id, event, enriched, _resolve)
        self._pending[emit_id] = entry

        logger.info(
            "%s emit_with_ack: emitId=%s msgId=%s event=%s",
            self._prefix, emit_id, msg_id, event,
        )

        if not self._paused:
            self._do_emit(entry)

        return await future

    def pause(self) -> None:
        """Call on disconnect: clear all retry timers, keep queue."""
        if self._paused:
            return
        self._paused = True
        for entry in self._pending.values():
            if entry.retry_timer is not None:
                entry.retry_timer.cancel()
                entry.retry_timer = None
        logger.info("%s Paused (%d pending)", self._prefix, len(self._pending))

    def resume(self) -> None:
        """Call on reconnect: re-emit all pending messages."""
        if not self._paused:
            return
        self._paused = False
        logger.info(
            "%s Resumed, re-emitting %d pending message(s)",
            self._prefix, len(self._pending),
        )
        for entry in self._pending.values():
            self._do_emit(entry)

    def destroy(self) -> None:
        """Call on shutdown: cancel all timers, fail all futures."""
        for entry in list(self._pending.values()):
            if entry.retry_timer is not None:
                entry.retry_timer.cancel()
            entry.resolve(False)
        self._pending.clear()
        logger.info("%s Destroyed", self._prefix)

    # ---- internals ---------------------------------------------------------

    def _gen_id(self) -> str:
        self._counter += 1
        return f"_re_{int(time.time() * 1000):016d}_{self._counter:012d}"

    def _do_emit(self, entry: _PendingMsg) -> None:
        """Send one frame via the socket timeout+callback path.

        Mirrors TS ``doEmit``: calls ``socket.timeout(ms).emit(event, data, cb)``.
        The callback resolves the pending entry on ACK or schedules retry on timeout.
        """
        timeout_ms = int(EMIT_ACK_TIMEOUT * 1000)

        def _on_ack_or_timeout(err: Optional[Exception]) -> None:
            # Guard: entry may have been removed by destroy/evict
            if entry.emit_id not in self._pending:
                return
            if err is None:
                # ACK success
                self._confirm(entry.emit_id)
            else:
                # Timeout or error → schedule retry
                logger.warning(
                    "%s ACK error: emitId=%s msgId=%s err=%s retries=%d",
                    self._prefix, entry.emit_id, entry.msg_id, err,
                    entry.retry_count,
                )
                self._schedule_retry(entry)

        self._ws_emit_with_timeout(
            entry.event, entry.data, timeout_ms, _on_ack_or_timeout,
        )

    def _confirm(self, emit_id: str) -> None:
        """ACK received — remove from pending, resolve True."""
        entry = self._pending.pop(emit_id, None)
        if entry is None:
            return
        if entry.retry_timer is not None:
            entry.retry_timer.cancel()
            entry.retry_timer = None
        entry.resolve(True)

    def _schedule_retry(self, entry: _PendingMsg) -> None:
        """Exponential backoff retry. Mirrors TS ``scheduleRetry``."""
        if self._paused:
            return  # resume() will re-emit

        if entry.retry_count >= EMIT_MAX_RETRIES:
            self._pending.pop(entry.emit_id, None)
            logger.error(
                "%s Gave up after %d retries: emitId=%s msgId=%s elapsed=%.1fs",
                self._prefix, entry.retry_count, entry.emit_id, entry.msg_id,
                time.monotonic() - entry.created_at,
            )
            entry.resolve(False)
            return

        entry.retry_count += 1
        delay = self._retry_delay(entry.retry_count)
        logger.info(
            "%s Retry #%d in %.1fs: emitId=%s msgId=%s",
            self._prefix, entry.retry_count, delay, entry.emit_id, entry.msg_id,
        )

        loop = asyncio.get_running_loop()
        entry.retry_timer = loop.call_later(delay, self._on_retry_timer, entry)

    def _on_retry_timer(self, entry: _PendingMsg) -> None:
        """Timer callback: re-emit if still pending and not paused."""
        entry.retry_timer = None
        if entry.emit_id not in self._pending:
            return
        if self._paused:
            return  # resume() will pick it up
        self._do_emit(entry)

    def _retry_delay(self, retry_count: int) -> float:
        base = EMIT_RETRY_BASE_DELAY * (2 ** (retry_count - 1))
        jitter = random.random()
        return min(base + jitter, EMIT_RETRY_MAX_DELAY)

    def _evict_if_needed(self) -> None:
        while len(self._pending) >= EMIT_PENDING_MAX:
            oldest_id = next(iter(self._pending), None)
            if oldest_id is None:
                break
            entry = self._pending.pop(oldest_id)
            if entry.retry_timer is not None:
                entry.retry_timer.cancel()
            logger.warning(
                "%s Evicted oldest: emitId=%s msgId=%s",
                self._prefix, entry.emit_id, entry.msg_id,
            )
            entry.resolve(False)
