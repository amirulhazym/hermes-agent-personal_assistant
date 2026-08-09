"""P4/F1/F4/F5 tests: billing metadata follows runtime provider (last-write-wins
with NULL guard), canonical_model persistence, pre-migration graceful
degradation, canonical reset on model switch."""

import sqlite3

from hermes_state import SessionDB


def _make_db(tmp_path):
    return SessionDB(tmp_path / "state.db")


def test_billing_provider_follows_latest_runtime_provider(tmp_path):
    """P4: a mid-session provider switch must update billing metadata."""
    db = _make_db(tmp_path)
    sid = "sess-billing-lww"
    db.update_token_counts(
        sid, input_tokens=100, model="deepseek-v4-flash-free",
        billing_provider="opencode-zen", billing_base_url="https://opencode.ai/zen/v1",
    )
    db.update_token_counts(
        sid, input_tokens=50, model="deepseek-v4-flash",
        billing_provider="deepseek", billing_base_url="https://api.deepseek.com/v1",
    )
    row = db.get_session(sid)
    assert row["billing_provider"] == "deepseek"
    assert row["billing_base_url"] == "https://api.deepseek.com/v1"


def test_null_billing_call_does_not_wipe_existing(tmp_path):
    """F4: call sites that omit billing fields (e.g. codex_runtime) must not
    NULL out the current provider."""
    db = _make_db(tmp_path)
    sid = "sess-billing-nullguard"
    db.update_token_counts(
        sid, input_tokens=100, model="deepseek-v4-flash-free",
        billing_provider="opencode-zen", billing_base_url="https://opencode.ai/zen/v1",
    )
    # No billing args (codex_runtime shape)
    db.update_token_counts(sid, input_tokens=10, model="gpt-5.4", api_call_count=1)
    row = db.get_session(sid)
    assert row["billing_provider"] == "opencode-zen"
    assert row["billing_base_url"] == "https://opencode.ai/zen/v1"


def test_canonical_model_persisted_last_write_wins(tmp_path):
    """P3/F5: response_model (canonical serving model) persists; last non-empty
    value wins."""
    db = _make_db(tmp_path)
    sid = "sess-canonical"
    db.update_token_counts(
        sid, input_tokens=100, model="deepseek-v4-flash",
        response_model="deepseek-v4-flash",
        billing_provider="deepseek", billing_base_url="https://api.deepseek.com/v1",
    )
    db.update_token_counts(
        sid, input_tokens=50, model="gpt-5.4",
        response_model="gpt-5.4-sol",
        billing_provider="openai-api", billing_base_url="https://api.openai.com/v1",
    )
    row = db.get_session(sid)
    assert row["canonical_model"] == "gpt-5.4-sol"


def test_model_switch_resets_canonical(tmp_path):
    """F5/F7: switching model invalidates previous canonical until next call."""
    db = _make_db(tmp_path)
    sid = "sess-canonical-reset"
    db.update_token_counts(
        sid, input_tokens=100, model="deepseek-v4-flash",
        response_model="deepseek-v4-flash",
    )
    db.update_session_model(sid, "gpt-5.4")
    row = db.get_session(sid)
    assert row["model"] == "gpt-5.4"
    assert row["canonical_model"] is None


def test_pre_migration_schema_auto_reconciles_canonical_column(tmp_path):
    """F1: a DB that predates the canonical_model column gets it added by the
    declarative column reconciliation (_reconcile_columns) on init — additive,
    idempotent, no manual migration step."""
    path = tmp_path / "pre-migration.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            user_id TEXT,
            model TEXT,
            model_config TEXT,
            system_prompt TEXT,
            parent_session_id TEXT,
            started_at REAL NOT NULL,
            ended_at REAL,
            end_reason TEXT,
            message_count INTEGER DEFAULT 0,
            tool_call_count INTEGER DEFAULT 0,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cache_read_tokens INTEGER DEFAULT 0,
            cache_write_tokens INTEGER DEFAULT 0,
            reasoning_tokens INTEGER DEFAULT 0,
            cwd TEXT,
            billing_provider TEXT,
            billing_base_url TEXT,
            billing_mode TEXT,
            estimated_cost_usd REAL,
            actual_cost_usd REAL,
            cost_status TEXT,
            cost_source TEXT,
            pricing_version TEXT,
            title TEXT,
            api_call_count INTEGER DEFAULT 0,
            handoff_state TEXT,
            handoff_platform TEXT,
            handoff_error TEXT,
            rewind_count INTEGER NOT NULL DEFAULT 0,
            archived INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (parent_session_id) REFERENCES sessions(id)
        );
        CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);"""
    )
    conn.commit()
    conn.close()

    db = SessionDB(path)
    # Reconciliation added the column (feature-detect confirms).
    assert db._has_canonical_model is True

    # Both SQL variants work and persist tokens + canonical.
    db.update_token_counts(
        "sess-pre-mig", input_tokens=100, output_tokens=10, model="deepseek-v4-flash",
        response_model="deepseek-v4-flash",
        billing_provider="deepseek", billing_base_url="https://api.deepseek.com/v1",
    )
    db.update_token_counts(
        "sess-pre-mig", input_tokens=20, output_tokens=15, model="deepseek-v4-flash",
        billing_provider="deepseek", billing_base_url="https://api.deepseek.com/v1",
        absolute=True, api_call_count=2,
    )
    row = db.get_session("sess-pre-mig")
    assert row is not None
    assert row["input_tokens"] == 20      # absolute overwrote
    assert row["output_tokens"] == 15
    assert row["billing_provider"] == "deepseek"
    assert row["canonical_model"] == "deepseek-v4-flash"

    # Model switch on reconciled schema resets canonical.
    db.update_session_model("sess-pre-mig", "gpt-5.4")
    assert db.get_session("sess-pre-mig")["canonical_model"] is None


def test_feature_detect_off_still_persists_tokens(tmp_path, monkeypatch):
    """F1 safety: if the canonical column were unavailable (e.g. reconciliation
    blocked), token persistence must not crash — SQL variant drops the column."""
    db = _make_db(tmp_path)
    sid = "sess-fd-off"
    # Simulate a session DB that cannot see the column.
    monkeypatch.setattr(db, "_has_canonical_model", False)
    db.update_token_counts(
        sid, input_tokens=100, output_tokens=10, model="deepseek-v4-flash",
        response_model="deepseek-v4-flash",
        billing_provider="deepseek", billing_base_url="https://api.deepseek.com/v1",
    )
    db.update_token_counts(
        sid, input_tokens=20, model="deepseek-v4-flash",
        billing_provider="deepseek", billing_base_url="https://api.deepseek.com/v1",
        absolute=True, api_call_count=2,
    )
    row = db.get_session(sid)
    assert row is not None
    assert row["input_tokens"] == 20
    assert row["billing_provider"] == "deepseek"
    # Column untouched (writes never referenced it).
    assert row["canonical_model"] is None
