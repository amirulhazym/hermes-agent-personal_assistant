---
name: hermes-session-diagnostics
description: Diagnose empty /sessions and /resume for gateway chats.
version: 1.1.0
author: Hermes curator
license: MIT
tags: [hermes, sessions, state-db, sqlite, diagnostics, gateway]
---

# Hermes Session Diagnostics

## When to use
- User runs `/sessions` or `/resume` in a gateway chat and gets "No sessions found" / empty list, despite having real prior conversations.
- User asks why past sessions don't appear, or `/resume <id>` fails to bind.
- User sees a non-empty list that is unchanged/stale, or `/resume <number>` enters an older branch instead of the latest continuation.
- Symptom is chat-specific (one DM shows nothing; another works).

**Triage first:** an empty list and an old-but-valid list are different failure classes. The NULL routing-column procedure below addresses the former; use `references/stale-lineage-tip-20260815.md` for the latter.

## Mental model: how listing/resume scopes rows
The canonical session store is `~/.hermes/state.db` (SQLite). `~/.hermes/sessions/sessions.json` is a **legacy mirror** of the gateway routing index — use it only to compare routing layers; never treat it as the session list or as the sole authority for current in-memory routing.

`/sessions` resolves to `hermes_cli.session_listing.query_session_listing` → `SessionDB.list_sessions_rich(source, session_key, …)` (`hermes_state.py`). The filter requires **every candidate row to carry the caller's `session_key`** (e.g. `agent:main:telegram:dm:679729206`).

`/resume` adds a **fail-closed ownership check** (`_resume_target_allowed` in `gateway/slash_commands.py`): a row is resumable only if its `source` + `user_id` + `chat_id` match the caller. Legacy rows with NULL `user_id`/`chat_id` fail closed (cannot prove ownership) → not resumable.

## Root-cause class: orphaned ancestors in a long continuation chain
Hermes chains sessions via `parent_session_id` across:
- **compression** continuations (`end_reason='compression'`),
- **session_reset** / **session_switch** continuations.

A busy chat can accumulate **hundreds of chained rows**. The chain root (and many ancestors) may have been written **before routing columns were populated**, leaving them with `session_key = NULL`, `user_id = NULL`, `chat_id = NULL`, `display_name = NULL`. Because listing is scoped by `session_key` and resume by ownership, those orphaned rows are **filtered out entirely** — the chat appears empty even though the data exists.

Contrast: a chat whose chain **root has `session_key` populated** lists normally (this is why WhatsApp DM worked but Telegram DM didn't in the 2026-08-13 case).

## Root-cause class: non-empty but stale lineage projection
A non-empty `/sessions` result does **not** prove that the latest conversation is surfaced. `query_session_listing()` calls `list_sessions_rich()` with compression-tip projection enabled by default. Diagnose this class when the output is valid-looking but frozen at an old title/ID, or `/resume <number>` loads an older response.

Use the live code path and compare identities separately:

1. Read the caller's `gateway_routing.entry_json.session_id`, the current open `sessions` row, and the requested/listed row.
2. Run `query_session_listing()` with the exact `source`, `session_key`, and `current_session_id`; capture returned IDs, not just the count.
3. Walk `parent_session_id` from the root to the current open row. Record total edges, each `end_reason`, and the listed row's position in that chain.
4. Call `SessionDB.get_compression_tip(root)` and `resolve_resume_session_id(listed_id)` directly. Do not infer effective resume state from the displayed title.
5. Inspect the resolver for fixed hop caps, which `end_reason` values it follows, and child ordering. A closed compression child may win over a newer live sibling; a `session_reset` boundary may also stop compression-only traversal.
6. Inspect the transcript loader separately: it may call the tip resolver again after `/resume` chose a target, so `requested ID`, `resolved ID`, `routing ID`, and `loaded transcript ID` can differ.

Acceptance is **latest-tip correctness**, not merely "rows returned": assert the expected current ID and a known latest message/content marker. See `references/stale-lineage-tip-20260815.md` for the reproducible probe and fork/cap failure pattern.

## Reconciliation protocol: stale/non-empty sessions and resume surfaces

Use this protocol when `/sessions` returns plausible named rows but the list is frozen, `/resume <number>` selects the wrong conversation, or an exact-ID `/resume` succeeds while later routing becomes stale. Do not collapse these into one "resume is broken" verdict.

### Keep the surfaces separate

Test each contract independently:

1. **`/sessions` projection** — `query_session_listing()` → `list_sessions_rich()` → compression-tip projection → current-session exclusion → origin visibility.
2. **`/resume` numeric selection** — `_list_titled_sessions()` calls `list_sessions_rich(limit=10)` directly, then filters titled rows. It is not guaranteed to use the same rows or numbering as `/sessions`.
3. **`/resume` title resolution** — title lookup first returns a session ID; `resolve_resume_session_id()` may then redirect it.
4. **`/resume` exact-ID resolution** — direct ID lookup, continuation resolution, ownership, switch, and transcript load are separate stages.
5. **Routing persistence** — in-memory `SessionStore`, durable `gateway_routing`, legacy `sessions.json`, and the DB `sessions` row are separate evidence layers.
6. **`/status` metadata** — verify the field source; do not infer it from the timestamp encoded in the session ID.

For `/sessions` vs `/resume` numbering, print `index | id | title` for both lists and compare IDs position-by-position. If the first mismatch is at N, report the exact functions responsible rather than calling the resolver stale by assumption.

### Read-only live probe discipline

Use a read-only SQLite URI (`file:...?...mode=ro`) and `SessionDB(read_only=True)`. Assert that a fresh probe has an empty token-delta queue before calling `list_sessions_rich()`, because that method drains queued token counts before querying. Never call live mutating handlers or methods during this audit: `_handle_sessions_command`, `_handle_resume_command`, `get_or_create_session()`, `switch_session()`, `reset_session()`, and `/status` can change routing or session state.

Capture one timestamped snapshot containing:

- DB and `sessions.json` size/mtime;
- durable `gateway_routing` entry;
- `sessions.json` mirror entry;
- latest open DB row for the exact `session_key`;
- resolver outputs and listing IDs.

A live gateway can persist the current turn/tool results while the probe runs. If DB size/mtime advances, label the result a moving snapshot and do not claim the audit itself was mutation-free without stating this concurrent writer.

### Prove a resolver stop, do not narrate it

For a stale displayed row:

1. Walk `parent_session_id` from the actual root and report edge number.
2. Run the exact live `get_compression_tip(root)` path.
3. Record the iteration count, returned ID, and whether an eligible child still exists after the returned ID.
4. Test fork selection, reset-boundary stopping, and sorting separately. A fork can determine the path without being the stop condition; sorting can determine list order without determining the projected ID.
5. If useful, run the same child SQL without the defensive hop cap on a read-only snapshot to locate the first reset boundary. Do not present that later boundary as the cause of an earlier capped return.

For a target at edge 100 with a non-null eligible child after it, the immediate verdict is the fixed hop cap. If an uncapped walk later stops at `session_reset`, record that as a separate boundary finding.

### Exact-ID provenance chain

For an exact target, print every ID produced by:

```text
explicit target
→ resolve_resume_session_id()
→ routing switch target
→ transcript-load input
→ get_compression_tip()
→ loaded transcript session
```

Do not execute the switch during a read-only audit. Use a persisted historical routing/log/DB observation if available, and label it historical. The target is proven stable only when every stage has the intended ID; later stale routing is a separate persistence failure.

`session_reset` is not automatically a compression continuation. `get_compression_tip()` requires a compression-ended parent, but `resolve_resume_session_id()` may then run a second generic `parent_session_id` child walk. **Do not stop reading after `get_compression_tip()`**: inspect the complete resolver, including the later child SQL, its branch/delegate/source exclusions, and whether it filters `end_reason`. If it does not, a reset/session-switch child with messages can become the effective resume target even though the requested ancestor is not reopened. Reproduce the full identity chain (`requested → resolved → routing → transcript-load`) against live rows. The gateway `Already on ...` response may interpolate the original command argument rather than the resolved target; never treat that acknowledgement as route proof. If a reset/switch child has no messages, the result may still remain on the target; that is evidence for that data shape only, not proof that all reset boundaries are safe.

### Routing and `/status` provenance

Never equate the legacy mirror with in-memory state. Report all layers explicitly and mark in-memory as `UNVERIFIED` when there is no safe read API. If `gateway_routing`/`sessions.json` points to an ended row while a newer open row exists for the same key, that is durable routing staleness even if the live process may still hold a newer in-memory entry.

For `/status`, trace the source field. `SessionStore.SessionEntry.created_at` can be reset when `switch_session()` rebinds an old target ID, so `/status Created` may show the switch/entry-creation time rather than `sessions.started_at`. Call this a metadata semantic defect if the UI labels it as session creation time.

### References

- `references/session-reconciliation-20260816.md` — exact read-only reconciliation recipe and evidence map for projection, numeric/title/exact resume, 100-hop stopping, reset boundaries, routing layers, `/status`, and transcript persistence.
- `references/exact-vs-effective-resume-20260817.md` — verified incident pattern where `/resume` resolves an ancestor to a message-bearing reset child and the acknowledgement echoes the original ID; includes the read-only identity chain and fix boundary.

## Diagnostic procedure (verify on a COPY — never prod first)
1. **Locate the live store**: `~/.hermes/state.db`.
2. **Find the caller's session_key**: read `~/.hermes/sessions/sessions.json` (legacy mirror) or the `gateway_routing` table; format is `agent:main:<platform>:<dm|group>:<chat_id>`.
3. **Count rows per session_key** and flag how many in the target chat have `session_key IS NULL`:
   ```sql
   SELECT session_key, COUNT(*) FROM sessions GROUP BY session_key;
   ```
4. **Walk the parent chain** from the current session id up to root; collect ancestors whose `session_key`/`user_id`/`chat_id` are NULL.
5. **Verify the hypothesis on a copy** (do NOT touch prod yet):
   ```bash
   cp ~/.hermes/state.db /tmp/state_test.db
   cd ~/.hermes/hermes-agent
   venv/bin/python - <<'PY'
   import sys, pathlib
   sys.path.insert(0, '.')
   from hermes_state import SessionDB
   from hermes_cli.session_listing import query_session_listing
   db = SessionDB(db_path=pathlib.Path('/tmp/state_test.db'), read_only=False)
   rows = query_session_listing(db, source='telegram', session_key='agent:main:telegram:dm:679729206',
       current_session_id='<CURRENT_SID>', include_unnamed=False, exclude_sources=['tool'], limit=10)
   print('RETURNED', len(rows))
   for r in rows: print(r.get('id'), r.get('title'))
   PY
   ```
   If this returns 0 rows on the copy, the orphaned-`session_key` hypothesis is confirmed.
6. **Confirm the fix on the copy**: backfill `session_key`/`user_id`/`chat_id`/`display_name` on the orphaned ancestors (matching the live chat identity), re-run step 5. If it now returns rows, the diagnosis + fix are proven on the copy.

## Pitfalls
- **Never edit prod `state.db` without a backup + copy-first verification.** The backfill is a data repair, not a code change; apply only after the copy proves it.
- **`state.db` is large (1.8+ GB at 95k messages).** PRAGMA/page-scan queries can time out; run them with a generous timeout or on the copy. `VACUUM` may reclaim ~0 MB if the data is genuine (freelist small) — that means growth is real conversation volume, not free space.
- **Distinguish diagnosis (proven) from prod fix (unapplied).** At the 2026-08-13 session end the backfill was verified on a copy but NOT yet applied to prod (user had not approved the prod write). Label prod-state claims PARTIAL/T stamped until the live write is done.
- **`sessions.json` is incomplete and stale-prone, not useless.** Use it as a legacy routing-mirror comparison layer; never treat it as the full session list or authoritative in-memory state.

## References
- `references/session-listing-empty-20260813.md` — full evidence from the 2026-08-13 Telegram DM case: 217-row chain, 180 orphaned NULL ancestors, copy-verified backfill, code pointers.
- Code: `gateway/slash_commands.py:_handle_sessions_command`, `hermes_cli/session_listing.py:query_session_listing`, `hermes_state.py:list_sessions_rich`, `hermes_state_common.py:_LISTABLE_CHILD_SQL`.
