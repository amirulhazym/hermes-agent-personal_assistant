"""
LightClaw — per-turn token usage tracker.

Hermes stores token counts in its SQLite ``state.db`` ``sessions`` table,
but the columns are session-cumulative. We mirror openclaw's per-turn
``usage`` frame by computing ``current_cumulative − turn_start_baseline``:
the whole-turn total (every LLM call of one question summed).

Note: openclaw reports only the last LLM call's usage; we report the
whole-turn sum. The wire format (openclaw ``UnifiedUsage``, camelCase) is
identical, so front-end / ai-server need zero hermes-specific code.

Baselines live in memory keyed by ``chat_id``. If lost mid-turn (e.g.
process restart), we skip the frame rather than over-report the session total.
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
    chat_id: str, sessions_dir: Optional[str] = None,
) -> Optional[sqlite3.Row]:
    """Read the latest ``sessions`` row for *chat_id* (falling back to the
    absolute-latest row). Returns ``None`` on any error — usage is
    best-effort and must never break the outbound path."""
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
    """Tracks per-turn token deltas against session-cumulative counters."""

    def __init__(self, sessions_dir: Optional[str] = None) -> None:
        # Authoritative sessions dir resolved by the adapter; ``state.db``
        # is its sibling.  ``None`` falls back to env / ~/.hermes lookup.
        self._sessions_dir: Optional[str] = sessions_dir
        # chat_id → baseline counters captured at turn start.
        self._baselines: Dict[str, Dict[str, int]] = {}
        # chat_id → model string captured at baseline time.
        self._models: Dict[str, Optional[str]] = {}

    def snapshot_baseline(self, chat_id: str) -> None:
        """Record cumulative counters as the baseline for a new turn (called
        at inbound). An unreadable DB yields an all-zero baseline, correct
        for a fresh session's first turn."""
        row = _read_session_row(chat_id, self._sessions_dir)
        self._baselines[chat_id] = _row_to_counters(row)
        model = None
        if row is not None and "model" in set(row.keys()):
            model = row["model"]
        self._models[chat_id] = model

    def classify_turn(
        self, chat_id: str
    ) -> Tuple[Optional[Dict[str, object]], str]:
        """Classify the round that just finished and (when real) return its usage.

        The cumulative token counters in Hermes' ``state.db`` are the only
        deterministic signal we have, so the verdict is driven entirely by
        whether — and by how much — they moved against the turn-start
        baseline. The return is ``(usage, reason)`` where ``reason`` is one of:

          * ``"usage"`` — baseline present, DB read OK, **delta > 0**. A real
            conversation turn ran an LLM call; ``usage`` is the openclaw
            ``UnifiedUsage`` object (whole-turn ``current − baseline``).
          * ``"no_llm"`` — baseline present, DB read OK, **delta == 0**. The
            counters did not move, so no LLM call ran. These are framework
            *command* rounds (``/new`` / ``/approve`` / ``/always``) that are
            never stored as transcript turns; the caller MUST NOT write a
            usage sidecar entry — a phantom line shifts the ordinal
            sidecar↔turn join and drops a real turn's usage on history reload.
            ``usage`` is ``None``.
          * ``"unknown"`` — we could **not measure** this turn: the baseline
            was lost (mid-turn restart) or the ``state.db`` row could not be
            read this instant. This is NOT proof the turn was free; it may be
            a real turn we simply failed to measure. The caller should write a
            placeholder to hold this turn's slot rather than silently dropping
            it. ``usage`` is ``None``.

        Crucially this distinguishes *measured zero* (``no_llm``) from
        *could-not-measure* (``unknown``): collapsing them — as a plain
        baseline check would — risks misreading a real turn that hit a
        transient DB read failure as a free command round.
        """
        # No baseline (e.g. restart between inbound and stop_typing) → we
        # can't isolate this turn's delta, so we can't measure it.
        baseline = self._baselines.get(chat_id)
        if baseline is None:
            logger.info(
                "[lightclaw] usage unknown: no baseline for chat_id=%s "
                "(inbound snapshot missing, likely mid-turn restart)",
                chat_id,
            )
            return None, "unknown"

        # Read the current cumulative counters. Distinguish a genuine read
        # (row present) from a read failure (row None) — the latter cannot be
        # measured and must not be mistaken for a zero-delta command round.
        row = _read_session_row(chat_id, self._sessions_dir)
        if row is None:
            logger.info(
                "[lightclaw] usage unknown: state.db row unreadable for "
                "chat_id=%s (cannot measure this turn's delta)",
                chat_id,
            )
            return None, "unknown"

        current = _row_to_counters(row)

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

        # Optional model identifier.
        model = self._models.get(chat_id)
        if isinstance(model, str) and model:
            usage["model"] = model

        return usage, "usage"

    def compute_turn_usage(self, chat_id: str) -> Optional[Dict[str, object]]:
        """Return the per-turn usage object, or ``None`` if not emittable.

        Thin wrapper over :meth:`classify_turn` for callers that only need the
        usage value and not the reason it was (or wasn't) produced.
        """
        return self.classify_turn(chat_id)[0]

    def clear(self, chat_id: str) -> None:
        """Drop any cached baseline / model for *chat_id*."""
        self._baselines.pop(chat_id, None)
        self._models.pop(chat_id, None)
