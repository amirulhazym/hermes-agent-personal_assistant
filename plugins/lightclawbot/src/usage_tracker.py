"""
LightClaw — per-turn token usage tracker.

Hermes stores token counts in its SQLite ``state.db`` ``sessions`` table,
but the columns are session-cumulative. We mirror openclaw's per-turn
``usage`` frame by computing ``current_cumulative − turn_start_baseline``:
the whole-turn total (every LLM call of one question summed).

Note: openclaw reports only the last LLM call's usage; we report the
whole-turn sum. The wire format (openclaw ``UnifiedUsage``, camelCase) is
identical, so front-end / ai-server need zero hermes-specific code.

Baseline 存储维度（方案 A/B/D 重构后）：
  key = (sender_uin, session_id)。session_id 是唯一可靠的隔离维度——
  同一 sender 可能同时活跃多个业务 chat，各映射独立 session_id，累计计数
  绝不能跨 session 混用（否则会得到负 delta → clamp 归零 → 误判为「命令
  回合」，本轮 token 永久丢失）。session_id 缺失时回退 (sender, "")
  作为 legacy key，仅用于「session_id 尚未 materialised」的首轮场景。

  若进程中途重启，内存 baseline 丢失 → classify_turn 返回 ``unknown``
  → 调用方写占位符（``usage: null``），保持 sidecar 与 transcript 的
  1:1 对齐；不会用过时数据虚报本轮 tokens。
"""

import logging
import os
import sqlite3
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Cumulative counter columns read from the ``sessions`` row.
# Keys: openclaw UnifiedUsage names; values: SQLite columns.
# ``totalTokens`` is derived (input + output).
_TOKEN_COLUMNS: Dict[str, str] = {
    "inputTokens":        "input_tokens",
    "outputTokens":       "output_tokens",
    "cachedInputTokens":  "cache_read_tokens",
    "cacheWriteTokens":   "cache_write_tokens",
    "reasoningTokens":    "reasoning_tokens",
}

# Provider tag echoed into every emitted usage object.
_PROVIDER = "hermes"


def _resolve_state_db_path(sessions_dir: Optional[str] = None) -> Optional[str]:
    """Locate the Hermes ``state.db`` — never hardcoding a path or username.

    Resolution order (most authoritative first), kept consistent with the
    rest of the plugin (``adapter._sessions_dir`` /
    ``history._default_sessions_dir``) and the install scripts:

      1. Sibling of *sessions_dir*: ``<HERMES_HOME>/sessions`` →
         ``<HERMES_HOME>/state.db``.  This is the path the adapter already
         resolved at runtime (config ``extra.sessions_dir`` →
         ``LIGHTCLAW_SESSIONS_DIR`` → ``$HERMES_HOME/sessions``), so it
         honours custom install locations automatically.
      2. ``$HERMES_HOME/state.db`` — the canonical env var used by every
         ``hermes_*.sh`` script and by the adapter.
      3. ``~/.hermes/state.db`` for the current user.
      4. Last-resort scan of real home dirs (``/home/*/.hermes`` and
         ``/root/.hermes``), mirroring ``hermes_install.sh``'s own probe —
         covers container setups where the gateway runs under a user that
         differs from ``$HOME``, without ever assuming ``ubuntu``.

    Returns the first existing file, or ``None`` (caller treats that as
    "no usage data available" and skips — never blocks the main path).
    """
    candidates: list[str] = []

    # 1. Derived from the adapter's resolved sessions_dir (state.db is its
    #    sibling: <HERMES_HOME>/sessions/ <-> <HERMES_HOME>/state.db).
    if sessions_dir:
        parent = os.path.dirname(os.path.normpath(sessions_dir))
        if parent:
            candidates.append(os.path.join(parent, "state.db"))

    # 2. Canonical HERMES_HOME env var.
    if hermes_home := os.environ.get("HERMES_HOME"):
        candidates.append(os.path.join(hermes_home, "state.db"))

    # 3. Current user's home.
    candidates.append(os.path.expanduser("~/.hermes/state.db"))

    # 4. Last resort: enumerate real home dirs (no hardcoded username).
    try:
        for entry in sorted(os.listdir("/home")):
            candidates.append(f"/home/{entry}/.hermes/state.db")
    except OSError:
        pass
    candidates.append("/root/.hermes/state.db")

    seen: set = set()
    for path in candidates:
        if path and path not in seen:
            seen.add(path)
            if os.path.isfile(path):
                return path
    return None


def _read_session_row(
    chat_id: str,
    sessions_dir: Optional[str] = None,
    *,
    session_id: Optional[str] = None,
    strict: bool = False,
) -> Optional[sqlite3.Row]:
    """Read the matching ``sessions`` row for this turn.

    精确度优先级（``strict=False`` 时）：
      1. ``session_id`` 命中（最精确，跨 chatId 多会话共存时唯一可靠的维度）。
      2. ``WHERE user_id = chat_id`` 取该用户最新一行（``session_id`` 缺失时的兜底，
         例如首轮 Hermes 还没写 sessions.json）。
      3. ``ORDER BY started_at DESC LIMIT 1`` 取全表最新（最弱兜底，仅在前两者都
         不可用时使用——多 UIN 共享 state.db 时可能取到他人数据，但仍优于完全无值）。

    ``strict=True``：仅走优先级 1 —— 找不到就返回 None，绝不降级到 user_id/全表
    兜底。用于 ``classify_turn``：调用方已明确传入本轮的精确 session_id，
    此时若数据库尚未建行（LLM 已跑完但落盘慢半拍），兜底到别的 session 的
    ``current`` 值会与 baseline（属于目标 session）不同源，delta 计算完全错误
    ——不如返回 None，让 classify_turn 归类为 ``unknown`` 写占位符，语义安全。

    Returns ``None`` on any error — usage is best-effort and must never break the
    outbound path.
    """
    db_path = _resolve_state_db_path(sessions_dir)
    if not db_path:
        logger.info("[lightclaw] usage: state.db not found")
        return None

    cols = (
        "input_tokens, output_tokens, "
        "cache_read_tokens, cache_write_tokens, reasoning_tokens, "
        "model"
    )
    try:
        conn = sqlite3.connect(db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            row: Optional[sqlite3.Row] = None
            if session_id:
                # Hermes ``sessions`` 表主键列名是 ``id``（而非 ``session_id``）——
                # 见 hermes_state.py 的 schema 定义。LightClaw 多 chat 场景下，每个
                # 业务 chatId 在 sessions.json 中映射到独立的 ``id``；按 ``id``
                # 精确取行是消除 baseline 串扰（多窗口实时 token 偶尔为 0）的
                # 唯一可靠手段——``user_id`` 兜底必然取到全 UIN 最近活跃那行，
                # 多 chat 共用同一 UIN 时会拿到错误会话的累计值。
                try:
                    cur.execute(
                        f"SELECT {cols} FROM sessions WHERE id = ? LIMIT 1",
                        (str(session_id),),
                    )
                    row = cur.fetchone()
                except sqlite3.Error as exc:
                    # schema 差异等极端兜底——保留兜底链不影响实时帧。
                    logger.info(
                        "[lightclaw] usage: id query failed (%s), "
                        "falling back to user_id",
                        exc,
                    )
                    row = None

            # Strict 模式：不做任何降级兜底。这是 classify_turn 的默认路径——
            # 传入 session_id 的调用方需要保证 baseline / current 同源。
            if strict:
                return row

            if row is None and chat_id:
                cur.execute(
                    f"SELECT {cols} FROM sessions "
                    "WHERE user_id = ? ORDER BY started_at DESC LIMIT 1",
                    (str(chat_id),),
                )
                row = cur.fetchone()

            if row is None:
                cur.execute(
                    f"SELECT {cols} FROM sessions "
                    "ORDER BY started_at DESC LIMIT 1"
                )
                row = cur.fetchone()
            return row
        finally:
            conn.close()
    except sqlite3.Error as exc:
        logger.warning("[lightclaw] usage: sessions query failed: %s", exc)
        return None


def _row_to_counters(row: Optional[sqlite3.Row]) -> Dict[str, int]:
    """Extract cumulative token counters from a row (missing/NULL → 0)."""
    counters: Dict[str, int] = {field: 0 for field in _TOKEN_COLUMNS}
    if row is None:
        return counters
    keys = set(row.keys())
    for field, column in _TOKEN_COLUMNS.items():
        if column in keys:
            value = row[column]
            if isinstance(value, (int, float)):
                counters[field] = int(value)
    return counters


class SessionUsageTracker:
    """Tracks per-turn token deltas against session-cumulative counters.

    Baseline semantics (方案 D 重构后)
    ---------------------------------
    A baseline is the **turn-start snapshot** of the ``state.db`` cumulative
    counters for a specific ``(sender, session_id)`` pair.  It defines the
    *starting point* against which the turn-end ``current`` counters are
    diff'd to obtain this turn's usage.

    * 老会话（Hermes 已建行）→ baseline = 当前累计值（可能 > 0）
    * 新会话首轮（Hermes 尚未建行）→ baseline **必须** 为全零

    The critical invariant is that ``baseline`` and ``current`` MUST come
    from the **same** ``state.db`` row (i.e. the same ``session_id``).
    Cross-session mixing produces a negative delta that gets clamped to 0
    and then mis-classified as a framework command round — the exact bug
    that caused "非默认会话 token 用量不展示".

    To enforce this invariant:

    1. Baselines are keyed by ``(sender, session_id)``.  A missing / empty
       ``session_id`` yields the legacy "sender-only" key, reserved for the
       old single-session (default-chat) code path.

    2. ``mark_new_session_baseline`` explicitly records a zero baseline for
       a newly-created business chat, bypassing any ``state.db`` read that
       would otherwise fall through to another session's row.

    3. ``classify_turn`` only consumes a baseline whose key matches the
       call's ``(sender, session_id)``.  It never falls back to a
       different-session baseline — that yields ``unknown`` (measurable
       failure preserving the sidecar slot) rather than a phantom
       ``no_llm`` verdict that permanently drops the turn's usage.
    """

    def __init__(self, sessions_dir: Optional[str] = None) -> None:
        # Authoritative sessions dir resolved by the adapter; ``state.db``
        # is its sibling.  ``None`` falls back to env / ~/.hermes lookup.
        self._sessions_dir: Optional[str] = sessions_dir
        # Baseline key is ``(sender, session_id_or_empty)``.  session_id
        # is the primary isolation dimension — one UIN can own multiple
        # business chats, each mapped to its own Hermes session_id, and
        # their cumulative counters MUST NOT cross-contaminate.
        self._baselines: Dict[Tuple[str, str], Dict[str, int]] = {}
        self._models: Dict[Tuple[str, str], Optional[str]] = {}

    @staticmethod
    def _baseline_key(chat_id: str, session_id: Optional[str]) -> Tuple[str, str]:
        """Compose the baseline lookup key.

        Empty / ``None`` ``session_id`` maps to the legacy "sender-only"
        namespace, used only when we truly cannot resolve a session_id
        (very first warm-up turn of the very first session).
        """
        return (chat_id, session_id or "")

    @staticmethod
    def _zero_counters() -> Dict[str, int]:
        """Return an all-zero counter dict — the canonical baseline for a
        brand-new session that has no ``state.db`` row yet."""
        return {field: 0 for field in _TOKEN_COLUMNS}

    def mark_new_session_baseline(
        self,
        chat_id: str,
        *,
        session_id: Optional[str] = None,
    ) -> None:
        """Record an **all-zero** baseline for a brand-new session's first turn.

        This is the fix for the "非默认会话 token 用量不展示" bug (方案 A).

        Scenario: inbound has just received the first message of a newly-
        created business chat.  Hermes has not yet allocated a
        ``state.db`` row for this chat's session_id, so any read through
        ``_read_session_row`` would fall through to ``WHERE user_id = ?``
        and return the DEFAULT chat's cumulative counters — poisoning the
        baseline with another session's totals.

        The correct baseline for a brand-new session's first turn is
        trivially zero: nothing has been counted yet.  We record that
        directly, bypassing the DB entirely.

        ``session_id`` may still be ``None`` (Hermes hasn't finalised the
        session at inbound-peek time); the legacy sender-only key is
        used in that case, and the follow-up ``correct_baseline_after_session_id``
        call rewrites it to the correct ``(sender, session_id)`` key
        once the session_id becomes known.
        """
        key = self._baseline_key(chat_id, session_id)
        self._baselines[key] = self._zero_counters()
        self._models[key] = None
        logger.info(
            "[lightclaw][usage] new-session zero baseline: chat_id=%s "
            "session_id=%s key=%s",
            chat_id, session_id, key,
        )

    def correct_baseline_after_session_id(
        self,
        chat_id: str,
        *,
        old_session_id: Optional[str],
        new_session_id: str,
    ) -> None:
        """Rewrite the baseline key from ``(sender, old_sid)`` to
        ``(sender, new_sid)`` **without re-reading state.db**.

        Used by inbound after ``handle_message`` when the framework has
        materialised a fresh ``session_id`` that was unknown at
        ``snapshot_baseline`` time.  We *cannot* re-snapshot at this
        point because ``handle_message`` may already have run the LLM
        call and bumped the counters — a new snapshot would swallow the
        current turn's tokens.  Instead we simply relabel the existing
        baseline (which is either a zero-baseline for a new session, or
        the pre-LLM cumulative for an existing one).

        Model identifier: since baseline datapoints are preserved as-is,
        the model tag associated with the old key (usually ``None`` for a
        zero baseline) may lag behind reality.  We do a *read-only,
        model-column-only* peek at ``state.db`` to enrich the new key's
        model tag when possible.  This never touches the counters and
        cannot poison the baseline value.

        Idempotency: if the new key already has a baseline (already
        relabelled, or ``snapshot_baseline`` had a resolved session_id
        upfront), this call is a no-op — we do NOT overwrite it with the
        old key's data, and we leave the old key intact so a stray double
        call cannot corrupt state.
        """
        old_key = self._baseline_key(chat_id, old_session_id)
        new_key = self._baseline_key(chat_id, new_session_id)
        if old_key == new_key:
            return
        # Idempotency guard: if we've already established a baseline under
        # the target key, don't clobber it or delete the source.
        if new_key in self._baselines:
            logger.debug(
                "[lightclaw][usage] baseline relabel skipped (already at "
                "target): chat_id=%s %s → %s",
                chat_id, old_key, new_key,
            )
            return
        baseline = self._baselines.pop(old_key, None)
        model = self._models.pop(old_key, None)
        if baseline is None:
            # Nothing to relabel — leave the new key untouched so
            # classify_turn can decide whether to treat this as a
            # fresh-zero or an unknown-measure case.
            logger.info(
                "[lightclaw][usage] baseline relabel skipped (no source): "
                "chat_id=%s %s → %s",
                chat_id, old_key, new_key,
            )
            return
        self._baselines[new_key] = baseline
        # Best-effort model enrichment: if the old key had no model recorded
        # (typical for a zero-baseline new session), peek state.db for the
        # model column only.  Safe: we never touch counter columns here.
        if not (isinstance(model, str) and model):
            row = _read_session_row(
                chat_id, self._sessions_dir, session_id=new_session_id,
            )
            if row is not None and "model" in set(row.keys()):
                row_model = row["model"]
                if isinstance(row_model, str) and row_model:
                    model = row_model
        self._models[new_key] = model
        logger.info(
            "[lightclaw][usage] baseline relabelled: chat_id=%s %s → %s "
            "baseline=%s model=%s",
            chat_id, old_key, new_key, baseline, model,
        )

    def handle_session_reset(
        self,
        chat_id: str,
        *,
        new_session_id: str,
    ) -> None:
        """Anchor a zero baseline on the new session_id after a mid-turn
        session reset.

        Trigger: stop_typing has resolved a ``turn_session_id`` that does
        NOT match any existing baseline for this sender/chat.  This is
        Hermes' auto-reset (idle/daily timeout) path — the round started
        under session A, but during ``handle_message`` Hermes swapped in
        session B (via ``get_or_create_session``) and ran the LLM under
        B.  The state.db row for session B was created **inside this
        turn**, so its counters already contain the current turn's
        tokens; the correct baseline for delta = current is therefore
        **zero**, exactly like a brand-new session's first turn.

        Safety: we deliberately do NOT purge other baselines for this
        sender.  The ``chat_id`` parameter here is actually the sender
        UIN (a legacy naming carry-over — see outbound.py); one UIN may
        own multiple concurrent business chats, each with its own
        baseline under a different session_id.  Blindly purging by
        sender risks clobbering another chat's live baseline.  Stale
        baselines are harmless: they simply sit in memory until the
        next ``snapshot_baseline`` / ``mark_new_session_baseline`` /
        ``clear`` covers them.  Memory footprint is bounded by concurrent
        active sessions per sender (small).
        """
        new_key = self._baseline_key(chat_id, new_session_id)
        self._baselines[new_key] = self._zero_counters()
        # Best-effort model enrichment (safe, model column only).
        model: Optional[str] = None
        row = _read_session_row(
            chat_id, self._sessions_dir, session_id=new_session_id,
        )
        if row is not None and "model" in set(row.keys()):
            row_model = row["model"]
            if isinstance(row_model, str) and row_model:
                model = row_model
        self._models[new_key] = model
        logger.info(
            "[lightclaw][usage] session reset handled: chat_id=%s "
            "new_session_id=%s zero-baseline anchored model=%s",
            chat_id, new_session_id, model,
        )

    def has_baseline_for_session(
        self,
        chat_id: str,
        session_id: Optional[str],
    ) -> bool:
        """Return True if a baseline exists for the exact ``(chat_id, session_id)`` key.

        Used by callers (stop_typing) to decide whether a session reset
        handler needs to run before ``classify_turn``.  Only the exact
        key is consulted — legacy sender-only keys count separately as
        ``(chat_id, "")``.
        """
        return self._baseline_key(chat_id, session_id) in self._baselines

    def snapshot_baseline(
        self,
        chat_id: str,
        *,
        session_id: Optional[str] = None,
    ) -> None:
        """Record cumulative counters as the baseline for a new turn.

        Called at inbound.  Requires a resolved ``session_id`` to be safe
        — without it the row resolver falls back to ``WHERE user_id = ?``
        which can return another chat's row when one UIN owns multiple
        chats.  Callers that cannot resolve ``session_id`` should call
        :meth:`mark_new_session_baseline` instead (方案 A).

        Failure modes:
          * DB unreadable → all-zero baseline (matches a brand-new
            session's semantics; safe fallback).
          * Row not found for the given ``session_id`` → all-zero
            baseline (session row not yet created; treat as fresh).
        """
        row = _read_session_row(
            chat_id, self._sessions_dir, session_id=session_id,
        )
        key = self._baseline_key(chat_id, session_id)
        self._baselines[key] = _row_to_counters(row)
        model = None
        if row is not None and "model" in set(row.keys()):
            model = row["model"]
        self._models[key] = model
        logger.info(
            "[lightclaw][usage] snapshot_baseline: chat_id=%s session_id=%s "
            "row_present=%s baseline=%s",
            chat_id, session_id, row is not None, self._baselines[key],
        )

    def classify_turn(
        self,
        chat_id: str,
        *,
        session_id: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, object]], str]:
        """Classify the round that just finished and (when real) return its usage.

        Return: ``(usage, reason)`` where ``reason`` is one of:

          * ``"usage"`` — baseline+current from the same session, delta > 0.
          * ``"no_llm"`` — baseline+current from the same session, delta == 0.
            Framework command round (e.g. ``/new``); no sidecar entry written.
          * ``"unknown"`` — either baseline missing, DB row unreadable, or
            baseline resolvable only through a *different* session_id (which
            would produce a bogus cross-session delta).  Caller writes a
            placeholder to hold this turn's sidecar slot.

        方案 B: this method NO LONGER falls back to a baseline stored under
        a different session_id.  Cross-session baseline reuse was the root
        cause of "非默认会话 token 用量不展示" — a default-session baseline
        (e.g. ``inputTokens=137038``) diffed against a new session's
        ``current=15887`` yields a negative delta that clamps to 0 and gets
        misclassified as ``no_llm``.  Better to surface ``unknown`` and let
        the sidecar placeholder preserve alignment than to silently mint a
        wrong verdict.
        """
        # Baseline lookup: prefer the exact ``(sender, session_id)`` key.
        # Fall back to the legacy sender-only key ONLY when the caller
        # also has no session_id — otherwise we would risk consuming a
        # different session's baseline (the exact bug we're fixing).
        exact_key = self._baseline_key(chat_id, session_id)
        baseline = self._baselines.get(exact_key)
        if baseline is None and not session_id:
            baseline = self._baselines.get(self._baseline_key(chat_id, None))

        if baseline is None:
            logger.info(
                "[lightclaw] usage unknown: no baseline for sender=%s "
                "session_id=%s (no snapshot or mid-turn restart)",
                chat_id, session_id,
            )
            return None, "unknown"

        # Read the current cumulative counters.  Distinguish a genuine
        # read (row present) from a read failure (row None) — the latter
        # cannot be measured and must not be mistaken for a zero-delta
        # command round.
        #
        # ``strict=True``：拒绝 _read_session_row 内部的 user_id/global_latest
        # 兜底。classify_turn 传入的 session_id 必须与 baseline 同源；若目标行
        # 尚未落盘（LLM 已跑完但 state.db 写延迟），宁可返回 unknown 写占位符，
        # 也不要用别的 session 的累计值当 current——那会计算出巨大 delta，
        # 虚报本轮 token 用量。
        row = _read_session_row(
            chat_id, self._sessions_dir,
            session_id=session_id, strict=True,
        )
        if row is None:
            logger.info(
                "[lightclaw] usage unknown: state.db row unreadable for "
                "sender=%s session_id=%s (cannot measure this turn's delta)",
                chat_id, session_id,
            )
            return None, "unknown"

        current = _row_to_counters(row)
        logger.debug(
            "[lightclaw][usage] classify_turn: sender=%s session_id=%s "
            "baseline=%s current=%s",
            chat_id, session_id, baseline, current,
        )

        delta: Dict[str, int] = {}
        for field in _TOKEN_COLUMNS:
            diff = current.get(field, 0) - baseline.get(field, 0)
            # Clamp to 0 to guard against counter resets (new session mid-turn).
            delta[field] = diff if diff > 0 else 0

        input_tokens = delta["inputTokens"]
        output_tokens = delta["outputTokens"]

        # Counters did not move → no LLM call ran → framework command round.
        if input_tokens == 0 and output_tokens == 0:
            return None, "no_llm"

        usage: Dict[str, object] = {
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "totalTokens": input_tokens + output_tokens,
            "provider": _PROVIDER,
        }

        # Extension counters: only attach when positive.
        for field in ("cachedInputTokens", "cacheWriteTokens", "reasoningTokens"):
            if delta[field] > 0:
                usage[field] = delta[field]

        # Optional model identifier — read from the same key we consumed
        # the baseline from (no cross-key fallback for the same reason
        # baseline lookup no longer does it).
        model = self._models.get(exact_key)
        if isinstance(model, str) and model:
            usage["model"] = model

        return usage, "usage"

    def compute_turn_usage(
        self,
        chat_id: str,
        *,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, object]]:
        """Return the per-turn usage object, or ``None`` if not emittable.

        Thin wrapper over :meth:`classify_turn` for callers that only need the
        usage value and not the reason it was (or wasn't) produced.
        """
        return self.classify_turn(chat_id, session_id=session_id)[0]

    def clear(
        self,
        chat_id: str,
        *,
        session_id: Optional[str] = None,
    ) -> None:
        """Drop cached baseline / model for *chat_id* (and the matching
        ``session_id`` if provided).  Without ``session_id`` only the
        sender-only legacy entry is removed.
        """
        key = self._baseline_key(chat_id, session_id)
        self._baselines.pop(key, None)
        self._models.pop(key, None)
