---
name: hermes-session-troubleshooting
description: "Debug Hermes /sessions and /resume returning empty lists."
version: 1.0.0
author: Hermes curator (derived from live VPS debug, 2026-08-13)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, sessions, troubleshooting, state.db, operator, debugging]
    related_skills: [hermes-agent]
---

# Hermes Session Store Troubleshooting

## When to use
- User reports `/sessions` shows "No sessions found" or "Use `/title My Session`..." for a chat that clearly has history.
- `/resume` (or the numbered resume list) shows nothing, or `Resume session` fails even though sessions exist.
- A chat's history "disappeared" from listings but the rows are still in `state.db`.
- `/sessions` returns plausible named rows but they are frozen at an old ID/title, or `/resume <number>` enters an older continuation.
- You are auditing why a specific `session_key` lane returns fewer sessions than expected.

Do NOT use for:
- CLI `hermes sessions list` showing empty — same data model applies, but confirm which surface (see `references/session-db-schema.md`).
- Live gateway connection / session *establishment* failures — that is session creation, not listing.

**Failure-class split:** empty output usually points to routing/ownership visibility; non-empty but stale output requires lineage-tip and transcript-resolution checks. Do not apply the NULL-backfill conclusion to the second class.

## The one-line root cause class
The listing filter `SessionDB.list_sessions_rich(..., session_key=...)` requires **every candidate row to carry the caller's `session_key`**. Historical sessions created before routing-column capture (or after a reset/compression that dropped them) have `session_key = NULL`, so they are filtered out — even though they belong to the same conversation. The newer rows (post-capture) have it; the old chain root does not. Result: 0 listable rows → "No sessions found". `/resume` shares the same failure via its fail-closed ownership check (`_resume_target_allowed` rejects rows with NULL `user_id`/`chat_id`).

For the **empty-list / NULL-routing** class above, this is a data-integrity problem and the fix is a one-time backfill of routing columns. Do **not** generalize that conclusion to a non-empty but stale list: if valid rows appear but an old continuation/title is surfaced, investigate lineage-tip resolution, hop caps, child forks, `session_reset` boundaries, and transcript loading as a possible code/data-shape failure. See `references/stale-lineage-tip-20260815.md` under the `hermes-session-diagnostics` umbrella.

## Data model (condensed)
- Canonical store: `~/.hermes/state.db` (SQLite + FTS5). Table `sessions`.
- Key columns: `id`, `source` (telegram/whatsapp/cli/cron/subagent/...), `session_key` (e.g. `agent:main:telegram:dm:679729206`), `user_id`, `chat_id`, `thread_id`, `display_name`, `parent_session_id`, `model_config` (JSON, may hold `_branched_from`/`_delegate_from`), `archived`, `title`, `message_count`, `end_reason`.
- Conversations are chains: each new turn window is a new row linked by `parent_session_id` (compression continuation or `session_reset`). A long daily DM can have 200+ rows in one chain.
- Listing visibility policy (`hermes_cli/session_listing.py::query_session_listing` + `hermes_state.py::list_sessions_rich`):
  - `_LISTABLE_CHILD_SQL`: root rows (`parent_session_id IS NULL`) OR branch children (`_branched_from` set). Subagent runs and compression continuations are hidden.
  - `session_key = ?` scope (gateway callers).
  - `exclude_sources=['tool']`, `archived = 0`.
  - Post-fetch: drop the current session id; drop untitled rows unless `include_unnamed`.
- `/resume` ownership: `_resume_target_allowed` fails CLOSED for any row lacking `user_id`/`chat_id`/`source` matching the caller. NULL routing columns → not resumable.

Full schema, exact filter SQL, and the fail-closed function with file:line citations: `references/session-db-schema.md`.

## Diagnostic procedure (root-cause-first)
1. **Confirm it's the data problem, not code/config.** Run the live code path on a COPY of `state.db` (never prod) — see Verification protocol. If `query_session_listing` returns 0 for the chat's `session_key`, proceed.
2. **Count the chain and find the NULL gap.** For the current session id, walk `parent_session_id` upward to the root. Tally how many ancestors have `session_key IS NULL` (and `user_id`/`chat_id` NULL). Reproduced case: 217-row chain, 180 ancestors NULL, 37 populated.
3. **Verify the NULL rows are genuinely this chat** (not another user/room) by checking `source`, `display_name`, `user_id`, `chat_id` consistency across the chain before backfilling. If the chain mixes owners, STOP — partial backfill would be wrong.
4. **Contrast with a working chat** (e.g. WhatsApp DM) to confirm the only difference is routing-column population on the root/ancestors.

## Fix procedure (backfill routing columns)
Set `session_key`, `user_id`, `chat_id`, `display_name` on the orphaned ancestors to match the live session's identity. Canonical values come from the live (current) row, which already has them populated.

**Recommended:** use the re-runnable script `scripts/backfill_session_routing.py`. It copies/backs up the DB, walks the chain, derives canonical routing from the starting row, backfills NULL ancestors idempotently, prints before/after listable counts, and supports `--dry-run`. It refuses to write a live `~/.hermes` DB without an explicit flag.

Run it on a COPY first, confirm `/sessions` + `/resume` return the expected rows via the live code path, THEN apply to prod (with its own backup).

Manual equivalent (SQL, on a copy — walk the chain in Python first, then):
```sql
UPDATE sessions SET session_key='agent:main:telegram:dm:679729206',
                    user_id='679729206', chat_id='679729206', display_name='amirulhazym'
WHERE id IN (<ancestor ids with NULL session_key>);
```

## Verification protocol (MANDATORY before touching prod)
Do NOT guess. Reproduce with the real code:
1. `cp ~/.hermes/state.db /tmp/state_test.db`
2. In the `hermes-agent` source venv:
   ```python
   from hermes_state import SessionDB
   from hermes_cli.session_listing import query_session_listing
   db = SessionDB(db_path=Path('/tmp/state_test.db'))
   rows = query_session_listing(db, source='telegram', session_key='agent:main:telegram:dm:679729206',
                                current_session_id='<current>', include_unnamed=False,
                                exclude_sources=['tool'], limit=10)
   print(len(rows))   # 0 before fix
   ```
3. Apply the backfill to the copy, re-run → expect ≥1 named row.
4. Only then run on prod (with backup).

Why copy-first: `state.db` is large and live; a wrong UPDATE is painful. The copy test is cheap and proves the fix end-to-end using the actual filter code, not a re-implemented SQL guess.

## Pitfalls
- **Editing prod `state.db` directly without a backup** — never. Always `.bak` first.
- **Assuming it's a code bug** — for the EMPTY/NULL-routing class, the listing logic and fail-closed ownership scope are intentional and a broad scope loosening would risk IDOR. For a NON-EMPTY but stale result, however, inspect the resolver and data shape; that class can be a genuine lineage-resolution defect.
- **Backfilling the wrong owner** — if a chain's ancestors belong to a different user/room, backfilling your caller's `session_key` would leak/merge. Always verify `source`+`user_id`+`chat_id` consistency across the whole chain first.
- **Forgetting `/resume` shares the cause** — backfilling `session_key` alone is not enough; `/resume` also needs `user_id`/`chat_id` populated to pass the fail-closed check. Backfill all four.
- **`include_unnamed` still returns 0** — confirms the scope filter (`session_key`), not the title filter, is the blocker. Don't be misled into "just add titles."
- **Compression chains are huge** — a daily DM can be 200+ rows. Walking the chain in Python is O(chain) and fine; don't try a single recursive SQL UPDATE without confirming the tree is a simple chain.

## References
- `references/session-db-schema.md` — full table notes, exact `list_sessions_rich`/`query_session_listing` filter SQL, `_resume_target_allowed` fail-closed logic, with file:line citations in the hermes-agent source.
- `hermes-session-diagnostics/references/stale-lineage-tip-20260815.md` — reusable probe for valid-looking but stale listings, fixed hop caps, forked children, reset boundaries, and transcript-tip mismatch.
- `scripts/backfill_session_routing.py` — idempotent, dry-run capable, copy-first backfill.
