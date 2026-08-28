# Live-vs-pinned `/resume` differential — 2026-08-19

## Purpose

Session-specific evidence and a reusable reproduction recipe for incidents where a running Hermes gateway, a local candidate commit, a pinned upstream release, and a large SQLite state DB disagree. This is a reference for the class-level `state-transition-lineage-debugging` workflow; it is not a deployment record.

## Evidence captured

| Layer | Artifact | Result |
|---|---|---|
| Runtime source | `/home/ubuntu/.hermes/hermes-agent`, `HEAD=a31be48030`, `v2026.8.3-1142-ga31be48030` | live source was older than the pinned release |
| Local candidate | `/tmp/hermes-candidate-20260812`, commit `123ea417`, parent `a31be48030` | separate branch/worktree; not an ancestor of live HEAD; only `hermes_state.py` and resolver tests changed |
| Pinned upstream | `v2026.8.16`, peeled commit `df4b65147d7ddd74dd449f9067aabbca5aef0ec7` | release tag resolved to the claimed commit |
| Upstream bug | issue `#84284` | open issue title describes `/resume <title>` following `/new`/reset parent chains |
| Upstream fix | PR `#85505` | merged 2026-08-13; its patch has three commits and a broader caller/schema/test surface than local `123ea417` |
| Live config file | `/home/ubuntu/.hermes/config.yaml:778-781` | `session_reset.mode=both`, `idle_minutes=240`, `at_hour=4` |
| Config provenance | dated config backups from 2026-07-17 onward | same reset values recur; exact writer/owner provenance is not present |
| Runtime reload boundary | gateway started 2026-08-16 08:20:35; config mtime 2026-08-17 09:14:51 | current file cannot prove the already-loaded in-memory value |

Official sources:

- https://github.com/NousResearch/hermes-agent/issues/84284
- https://github.com/NousResearch/hermes-agent/pull/85505
- https://github.com/NousResearch/hermes-agent/releases/tag/v2026.8.16
- https://github.com/NousResearch/hermes-agent/tree/v2026.8.16

## SQLite differential recipe

1. Capture the live DB size, mtime, and free space. Do not query a moving DB and call the result a stable behavioral baseline.
2. Create an immutable first copy with SQLite's backup API, e.g. `/tmp/hermes-state-readonly.db`.
3. Run the live source and pinned source against that same read-only copy. Capture exact resolver return IDs and row metadata.
4. If the pinned source fails on a schema difference, preserve the exact error. Do not silently add columns to the baseline copy.
5. Create a second temporary migration copy only if upgrade compatibility is part of the question. Let the pinned source initialize that copy, record schema changes, then rerun the behavior checks. Label results `MIGRATION-COPY`, not `COPY-VERIFIED`.
6. Keep `/tmp` copies separate from live state and delete only when the audit policy permits; never write to `/home/ubuntu/.hermes/state.db` during this investigation.

### Schema-first historical-probe guard

The live `sessions` schema did not contain historical probe fields such as `was_auto_reset` or `auto_reset_reason`. Re-running the query produced `sqlite3.OperationalError: no such column`, so those historical fields were downgraded rather than treated as current evidence. The reset cause was re-derived from present `end_reason`, timestamps, the configured idle threshold, and the live reset log.

Likewise, pinned v0.20.2 listing initially failed against the immutable live-schema copy with `sqlite3.OperationalError: no such column: s.hidden`. The source was then initialized only against a second migration copy. Record `PRAGMA table_info(...)` and the schema delta before using a migration result; never add compatibility columns to the baseline copy just to make a historical probe pass.


## Required behavioral cases

### Real Telegram lineage

For the incident lineage:

```text
20260816_165131_62990a  end_reason=session_reset, message_count=38
  -> 20260817_091858_68a7f428  end_reason=compression, message_count=135
      -> 20260817_094746_60a4fa  live child in the captured copy
```

Observed against the captured DB copy:

```text
live a31be48030:
  resolve_resume_session_id(20260816_165131_62990a) -> 20260817_094746_60a4fa

pinned v2026.8.16:
  resolve_resume_session_id(20260816_165131_62990a) -> 20260816_165131_62990a

local 123ea417:
  resolve_resume_session_id(20260816_165131_62990a) -> 20260816_165131_62990a
```

The local candidate and pinned release both stopped at the reset boundary for this real route. The candidate is not automatically equivalent to upstream: its resolver is 38 lines and delegates directly to `get_compression_tip()`, while the pinned resolver retains a reset-aware 94-line walk and broader filtering.

### Corrected synthetic reset fixture

Legacy reset predicates may use routing identity. A synthetic parent/child fixture that omits `session_key`, `user_id`, `chat_id`, and `chat_type` can produce a false failure in the pinned implementation. Add realistic identity fields, rerun, and only then classify the result.

### Fixed-depth walkers

A 105-node compression chain produced the same stable limitation in current and pinned source:

```text
get_compression_tip(root) -> chain-100
_session_lineage_root_to_tip(chain-104) -> 100 rows, chain-005..chain-104
```

This is independent of the reset-boundary fix. Test every fixed-depth walker, not only `resolve_resume_session_id()`.

### WhatsApp topology evidence

A live DB route with the same boundary class existed at capture time:

```text
source: whatsapp
chat_type: group
chat_id: <GROUP_JID>
session_key: agent:main:whatsapp:group:<GROUP_JID>:601166557800
parent: 20260816_060216_87834d38  end_reason=session_reset
child:  20260816_141545_d480ddac   end_reason=compression
```

This proves shared topology evidence, not that a user reproduced `/resume` on WhatsApp. Keep those claims separate.

## Listing and search contracts

Do not assume `/sessions` and numeric `/resume` share a selector. In the captured source:

- shared `/sessions` path: `hermes_cli/session_listing.py:query_session_listing()`; fetches up to `limit*4`, applies route/current/title policy;
- gateway numeric `/resume`: `gateway/slash_commands.py:_list_titled_sessions()`; fetches `list_sessions_rich(limit=10)`, filters titles, then assigns numbers.

Compare ordered physical IDs. On the captured DB, `same_ids_in_order=false` in both current and migrated pinned probes.

For `session_search`, compare direct `db.search_messages()` with the wrapper using `current_session_id=None` and the active session ID. The wrapper intentionally excludes active current-lineage hits in one path. A direct FTS hit plus wrapper no-result is therefore not enough to call FTS broken; first attribute the difference to the current-lineage guard or lineage projection.

The pinned source initially failed to list the un-migrated live-schema copy with:

```text
sqlite3.OperationalError: no such column: s.hidden
```

A separate migration copy initialized successfully and added the expected column. That proves migration compatibility was exercised on a temporary copy; it does not prove a live upgrade or restart.

## Reporting labels

Use exact labels:

- `LIVE` — directly observed in the running process, live log, routing index, or read-only live DB.
- `COPY-VERIFIED` — behavior run against an immutable SQLite backup using source code under test.
- `MIGRATION-COPY` — behavior run after temporary schema initialization/migration.
- `SOURCE-ONLY` — read from source or upstream metadata but not executed.
- `BLOCKED` — a test could not run; preserve the raw error.
- `UNVERIFIED` — plausible interpretation with no direct evidence.

Never convert a source plan, a candidate commit, a migration copy, or a successful resolver unit into `LIVE` or `DEPLOYED` status.
