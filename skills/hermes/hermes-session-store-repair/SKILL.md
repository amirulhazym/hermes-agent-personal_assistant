---
name: hermes-session-store-repair
description: "Empty /sessions or /resume? Use repair-routing first."
version: 1.0.0
author: curator (derived from 2026-08-13 session with amirulhazym)
license: MIT
platforms: [linux, macos, windows]
---

# Hermes Session Store Repair

## When to use
- User reports `/sessions` or `/resume` returns "No sessions found" or near-empty, yet they know they have chat history.
- `/sessions search <keyword>` STILL finds chats by title — search uses FTS on title/id, NOT `session_key`, so this confirms history exists but rows are "untagged".
- Symptom: `hermes sessions stats` shows a large total (e.g. 1139 sessions) but the gateway listing shows ~0.

## Root cause (verified 2026-08-13)
Every session row carries a `session_key` column — the "routing identity" that says which chat lane a row belongs to (telegram DM, whatsapp DM, group, etc.). `/sessions` and `/resume` filter by `session_key = <current chat's key>`. Historical rows written during a period when the gateway write path dropped routing columns have `session_key = NULL`. They are NOT lost — just untagged, so the listing filter excludes them.

Reference session: 870 of 1139 rows had NULL session_key (Jul 1 – Aug 10); only ~37 recent rows (post Aug 12) were tagged. Hence /sessions appeared empty.

## Workflow (DO THIS ORDER)

### 0. Consult official tools / docs FIRST — DO NOT hand-roll SQL yet
**Pitfall (user correction 2026-08-13):** The user explicitly wanted official documentation/tools checked before a custom solution was built. Run `hermes sessions --help` and read the subcommands before writing any UPDATE statement. A purpose-built repair tool very likely already exists.

### 1. Diagnose (read-only)
Run `scripts/diagnose_null_keys.py <path-to-state.db> [cutoff-date]`. It reports:
- totals (sessions, messages, db size) — `hermes sessions stats` also gives this
- count of NULL session_key rows by source and by date (pre/post a cutoff)
- per proven chat-lane: orphaned ancestor count

Proven chat-lane keys come from TWO external sources (cross-check both):
- `~/.hermes/sessions/sessions.json` (gateway routing mirror; `display_name` proves ownership)
- `gateway_routing` table in state.db

### 2. Try the official tool (safe, fail-closed)
```
hermes sessions repair-routing          # report-only (dry run) — ALWAYS run first
hermes sessions repair-routing --apply  # perform, only unambiguous rows
```
Re-stamps orphaned rows from their keyed predecessor, but ONLY when the predecessor is unambiguous. In the reference session it confidently fixed only 2 of 926 orphans ("parent session carries no gateway identity" for the rest). That is correct conservative behavior, NOT a bug — see `references/repair-routing-findings.md`.

Other official subcommands (all safe to explore):
- `hermes sessions optimize` — merge FTS5 + VACUUM, no data change (reclaims only free pages; live message data is NOT reclaimable this way)
- `hermes sessions prune` — delete old sessions by filter
- `hermes sessions repair` — fix malformed schema
- `hermes sessions recover` — offline non-destructive rebuild into a separate DB
- `hermes sessions stats` — store statistics

### 3. Manual backfill for the rest (chain-proven)
The official tool only does 1-hop parent adoption. Long chains where MANY ancestors are NULL need manual backfill. Safe only when identity is PROVEN:

- Walk the ancestor chain from the CURRENT keyed session (the one /sessions already scopes to). Every ancestor in that contiguous chain is provably the same conversation.
- For telegram DM: if `sessions.json` shows only ONE `agent:main:telegram:dm:*` key for the user, ALL telegram NULL rows in that chain are the user's DM — safe to tag.
- For whatsapp: prefer per-row — if a row has a keyed descendant, inherit that descendant's exact key (group vs DM stays accurate). Only default to the DM key for rows with NO keyed descendant (user approved this for solo operation — see Pitfalls).

Backfill SQL (inside one transaction):
```sql
UPDATE sessions
SET session_key='<proven key>', user_id='<uid>', chat_id='<cid>', display_name='<name>'
WHERE id IN (<orphan ids>) AND session_key IS NULL;
```

### 4. Verify (live, not copy)
Re-run the exact listing path the gateway uses:
```python
from hermes_cli.session_listing import query_session_listing
# source='telegram', session_key='agent:main:telegram:dm:<uid>',
# current_session_id=<current>, include_unnamed=False
```
Expect ≥1 named row. Also confirm `/resume <ancestor id>` passes the ownership check. No gateway restart needed (reads at query time).

### 5. Backup before any mutation
```
cp ~/.hermes/state.db ~/.hermes/state.db.bak-sessionsfix-<ts>
```
Verify the copy exists. Rollback = restore the copy.

## Pitfalls
- **Plan ≠ execution (user correction 2026-08-13):** The user said "kena work on it, bukan cakap je." Do not stop at a written plan when the user already approved the action. Execute with backup + verify, then report before/after counts.
- **Don't present a custom SQL fix as the only option when an official tool exists.** Always dry-run `repair-routing` first.
- **Security boundary is real for multi-user**, but the user (solo operator) explicitly waived it for older history. Encode that as: bulk-tag NULL rows only AFTER proving the peer keys are exclusively the user's (via sessions.json + gateway_routing). If multiple distinct peer keys exist for a source, do NOT blindly default them all to one key — that would cross-wire different chats.
- **`/sessions search` works without session_key** — older untagged chats are still findable by title. Tell the user this so they don't think history is lost.
- **VACUUM/optimize reclaims 0 on a healthy store** — if state.db is ~1.8GB with ~95k messages, that's genuine data, not free space. Don't promise disk savings from VACUUM alone.

## Runtime-drift check FIRST (2026-08-24/25 case)

Odd `/sessions`/`/resume` behavior (own live conversation listed, empty "shell" sessions appearing) may NOT be store corruption. Before any DB surgery:

1. `git -C ~/.hermes/hermes-agent status --short && git log --oneline -1` — uncommitted local modifications to session files (`gateway/slash_commands.py`, `hermes_cli/session_listing.py`, `gateway/session.py`) are a proven root cause class. On 2026-08-25, 14 modified files were found; a prior resume-work experiment had injected `get_or_create_session()` into the `_list_titled_sessions()` listing path.
2. Two downstream effects of that drift: (a) calling `get_or_create_session()` inside a LIST path creates an empty sibling row whenever the routing store is cold (32 empty rows accumulated in one Telegram DM lane); (b) `current_session_id` exclusion then bound to that freshly-created empty shell row, so the real titled conversation stayed listed as if it were another chat.
3. Compare against upstream before blaming upstream: diff the live runtime's session files vs its own git HEAD (`git fetch origin`, then `git diff origin/main -- gateway/ hermes_cli/session_listing.py`). Clean upstream `/sessions` calls `list_sessions_rich(...)` directly with NO current-session exclusion and NO session creation in the listing path.
4. Slash commands (`/title`, `/compress`, `/resume`) are user-side — an agent turn cannot execute them. Verify their effects read-only via state.db, and resolve the CURRENT session id from the user's most recent inbound message row (session-scoped), not lane-wide `ORDER BY timestamp DESC` (fresh shell/sibling sessions share the lane key and will hijack the query — caused a wrong "last message" quote on 2026-08-24).
5. Present disposition options, don't self-execute destructive ones: revert working tree (destroys un-promoted work) vs promote via source-clone feat branch + PR per the git flow (constitution: runtime is never edited ad hoc). Full case study: `references/runtime-drift-shell-row-case.md`.

## Communication note (user preference)
When explaining this class of problem to amirulhazym, lead with a plain-language summary (per /non-tech shape: what happened, why it matters, what I'll do) BEFORE any SQL/table dump. He found a raw technical write-up "terlalu berat untuk seorang beginner." Keep the first reply beginner-friendly; put detail after.

## References
- `references/repair-routing-findings.md` — dry-run output and interpretation from the reference session.
- `scripts/diagnose_null_keys.py` — read-only diagnostic (counts NULL keys, walks chains, reports per-lane orphans).
