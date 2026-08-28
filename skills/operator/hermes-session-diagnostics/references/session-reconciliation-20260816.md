# Session reconciliation reference — 2026-08-16

This is a session-specific evidence record for the class-level `hermes-session-diagnostics` workflow. It is not a claim that these IDs remain current; reproduce against a fresh read-only snapshot.

## Snapshot and safety

- Live CLI: `Hermes Agent v0.20.0 (2026.8.3)`.
- Live checkout: `/home/ubuntu/.hermes/hermes-agent`, HEAD `a31be48030f60383bf4c1d96ba46bd4b48430218`, clean `main` worktree.
- SQLite reads used `file:/home/ubuntu/.hermes/state.db?mode=ro` and `SessionDB(read_only=True)`.
- The gateway persisted the ongoing turn concurrently, so DB size/mtime moved during the audit. Treat outputs as timestamped snapshots, not an immutable transaction.
- Do not introspect or mutate live `SessionStore` if no safe read API exists; label in-memory routing `UNVERIFIED`.

## Projection versus numeric resume reproduction

At snapshot `2026-08-16T13:19:01.264671+08:00`:

- Latest open Telegram DB row: `20260816_131321_6c1933`.
- Durable `gateway_routing` and `sessions.json` still pointed to ended `20260816_082228_b6ac0385`.

Pure `/sessions` equivalent, using latest open DB ID as `current_session_id`, returned:

```text
1  20260809_040831_306cb73c  Clarifying Architecture Scope and Drift
2  20260810_144912_43bf68    Hermes Integration Reconciliation Review #108
3  20260808_015351_37b227    git-0806-tele #13
4  20260806_083918_cf1b8d9b  Starting Fresh Session
5  20260801_075248_1a88ad14  Identifying Hermes Agent Go Live Session
6  20260731_173518_ad3344  Hermes Agent Go Live #42
7  20260729_124336_c353d2  Investigate WhatsApp Message Delivery Delays #13
8  20260728_193048_c3a94376  ChatGPT Plus Purchase Check
9  20260729_161739_fe94ba  ChatGPT Plus Provider Setup #27
10 20260726_124754_8923f2  Resuming TB medication logging session #2
```

Pure `/resume` numeric equivalent fetched 10 raw rows, then filtered titled rows. Only three numbered choices were emitted:

```text
1  20260816_131321_6c1933  Find session ID for /resume
2  20260809_040831_306cb73c  Clarifying Architecture Scope and Drift
3  20260810_144912_43bf68  Hermes Integration Reconciliation Review #108
```

First mismatch is position 1. This is a policy/function mismatch, not proof that exact-ID resume is broken:

- `/sessions`: `query_session_listing()` over-fetches, projects tips, and excludes `current_session_id`.
- `/resume`: `_list_titled_sessions()` calls `list_sessions_rich(limit=10)` directly and filters titles; it does not share `/sessions` numbering.

## Stale #108 stop proof

The actual root was `20260808_040236_9eee6992`; `20260810_144912_43bf68` was edge 100. The live capped walk returned:

```text
iterations_taken:          100
returned:                  20260810_144912_43bf68
eligible_child_after_stop: 20260810_145144_c8b8c8
```

Therefore the immediate stop condition was the `for range(100)` exhaustion, not an empty child result.

Independent tests:

- Root-to-target lineage contained forks, but fork selection did not terminate at #108.
- Removing the cap in the same compression-only child SQL reached `20260811_191501_990b01` at edge 186, where `end_reason=session_reset`; that is a later, separate boundary.
- SQL sorting (`started_at`) affects list ordering, not the projected ID.

## Exact-ID resume trace

Target: `20260815_130611_c1bff7`.

```text
explicit target                 20260815_130611_c1bff7
get_compression_tip()           20260815_130611_c1bff7
resolve_resume_session_id()     20260815_130611_c1bff7
historical switch target        20260815_130611_c1bff7
transcript load tip             20260815_130611_c1bff7
active transcript rows          179
last active row IDs             106735..106739
```

Persisted historical diagnostic message `106735` showed the route at the successful event pointing to `c1bff7` and temporary `20260816_082228_b6ac0385` ending with `session_switch`. Do not execute another switch during a read-only reconciliation.

## Reset/session-switch classification

Target ancestry had 219 nodes / 218 edges:

```text
compression:   215
session_reset:   4
```

Reset rows included:

```text
20260811_191501_990b01
20260812_004652_1e77848c
20260813_002900_1a73a4
20260815_130611_c1bff7
```

The target's direct child was a separate `session_switch` row:

```text
20260816_125941_c9e320f6
message_count = 0
```

`get_compression_tip()` excludes reset/switch parents because its SQL requires `parent.end_reason='compression'`. Inspect the later generic child walk in `resolve_resume_session_id()` separately; it is broader and should not be silently treated as compression traversal.

## Routing layers

Telegram key:

```text
agent:main:telegram:dm:679729206
```

- durable route: ended `20260816_082228_b6ac0385` (`compression`)
- latest open DB child: `20260816_131321_6c1933`
- `sessions.json`: still ended parent ID
- in-memory: do not infer without a safe read

WhatsApp key:

```text
agent:main:whatsapp:group:<GROUP_JID>:601166557800
```

- durable route: `20260816_060216_87834d38`
- DB row: ended `session_reset`
- latest open row: none
- `sessions.json`: same ended ID

Same `gateway_routing`/legacy mirror mismatch across both platforms supports a shared backend routing problem, while the exact in-memory entries remain unverified.

## `/status` provenance

`/status` renders `SessionEntry.created_at`, not `sessions.started_at`. `switch_session()` creates a new `SessionEntry` with `created_at=now` while retaining the target ID. Historical target evidence:

```text
ID:             20260815_130611_c1bff7
DB started_at:  2026-08-15 13:06:11
entry created:  2026-08-16 08:26:28
```

So `Created: 2026-08-16 08:26` is the routing-entry creation/switch time, not the DB session start time.

## Transcript persistence proof

Message `105493` remained present:

```text
session_id: c1bff7
role:       assistant
length:     8599
sha256:     e8ea208804a006ae69ed445581a7dce94f985712df70f230963690a64421ac82
active:     0
compacted:  1
```

The raw row is persisted even though default active replay excludes it. Active transcript loading still returned 179 rows through assistant row `106739`. This distinguishes transcript persistence from routing/lineage accessibility.

## Source map

- `hermes_state.py`: `get_compression_tip()` around lines 7004–7062; `list_sessions_rich()` around 7104–7460; `resolve_resume_session_id()` around 8566–8653; active transcript filtering around 8655–8701.
- `hermes_cli/session_listing.py`: `query_session_listing()` around lines 45–88.
- `gateway/slash_commands.py`: `/resume` around 4497–4649; `/sessions` around 4665–4734; `/status` around 540–680; `/new`/`/reset` around 119–217.
- `gateway/session.py`: reset/switch around 3199–3396; routing load/prune around 1334–1510; transcript load around 3791–3829.
