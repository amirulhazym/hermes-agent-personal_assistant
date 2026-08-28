---
name: state-transition-lineage-debugging
description: "Use when debugging parent/child state-transition graphs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, state-machines, lineage, continuations, sessions, tdd]
    related_skills: [systematic-debugging, test-driven-development, codebase-design]
---

# State-Transition and Lineage Debugging

## When to Use

Use when debugging parent/child state-transition graphs, continuation or rotation logic, lineage-aware lookup, session resume behavior, reset boundaries, stale-child recovery, or multiple callers that independently traverse the same state graph.

## Purpose

Use this skill when a stateful system models continuations, rotations, parent/child sessions, recovery, reset boundaries, or lineage-aware lookup. It is especially useful when several callers traverse the same graph and one broad fallback walk can cross a lifecycle boundary.

The central rule is:

> A child edge is a domain transition, not merely a matching `parent_id`.

A graph query that finds a child is not necessarily allowed to follow it. The parent state, child role, lifecycle reason, and race policy must authorize the edge.

## Contract-first vocabulary

Lock these terms before changing code:

- **Requested ID** — the identifier supplied by the caller; it may be an ancestor.
- **Effective ID** — the ID selected after the canonical continuation resolver runs.
- **Continuation edge** — a parent→child edge authorized by the exact lifecycle predicate.
- **Ordinary child** — a parented row that is not authorized as a continuation; it may be a reset artifact, delegate, branch, tool run, or unrelated child.
- **Boundary reason** — an end/transition reason that intentionally terminates a chain. Examples include `session_reset`, `session_switch`, `idle`, `cron_complete`, and intentional user/system boundaries.
- **Canonical predicate** — the one reusable definition of an authorized edge. Every relevant traversal must reuse it or be demonstrably equivalent.

Do not collapse requested, effective, routing, and display identities. A title or UI label is not proof of the stored ID; an ancestor and its compression child are related but remain distinct rows.

## Investigation workflow

### 1. Build a red-capable, narrow feedback loop

Before theorizing, locate or create the smallest test at the real seam. The test must reproduce the user's exact wrong selection, not merely prove that the query runs.

Read-only analysis can still establish the seam by tracing:

1. the public entry point (CLI, slash command, API, or TUI);
2. the resolver it calls;
3. every graph traversal invoked by that resolver;
4. all other callers of the same helper;
5. the persistence path that creates parent/child rows.

Record exact file paths, function names, and existing test names. Label unrun behavior as a hypothesis, not a finding.

### 2. State the transition contract

Write the edge as a predicate before proposing a patch. For a compression-style continuation, the minimum shape is usually:

```text
child.parent_session_id == parent.id
AND parent.end_reason == "compression"
AND child is not a branch/delegate/tool child
```

The exact values are project-specific and must be verified from source. Do not infer them from a title, timestamp, source name, or a generic `parent_id` relationship.

Explicitly decide:

- which parent state authorizes the edge;
- which boundary states prohibit it;
- how branch/delegate/tool roles are marked;
- whether inherited metadata on a legitimate child is legal;
- how cycles and excessive depth fail;
- how multiple candidates are selected or rejected;
- whether the resolver is read-only.

### 3. Inventory duplicate traversals

Search all references to the resolver and to predicate fragments. Classify each caller:

| Caller class | Typical contract | Side effects allowed? |
|---|---|---|
| Resume/session lookup | return the effective continuation ID | no |
| List/sidebar projection | show one logical conversation at the latest valid tip | no |
| Export/history | include only valid lineage segments | no |
| Stale-writer recovery | adopt exactly one valid live child or fail closed | recovery-specific, never guess |
| Routing/ownership | compare caller identity to the effective session | no implicit cross-owner adoption |
| Command handler | switch routing, end old row, reopen target | yes, but outside the resolver |

A primary canonical traversal followed by a second generic child walk is a second state machine. It can undo the contract of the primary traversal and cross `session_reset`, `session_switch`, `idle`, `cron_complete`, or intentional boundaries. Remove it or constrain it to the same canonical predicate.

### 4. Check race assumptions

Do not use `child.started_at >= parent.ended_at` as the semantic definition unless the lifecycle guarantees that ordering. Atomic publication or concurrent writers may make the real continuation visible before the parent's durable end timestamp; stale siblings may satisfy the timestamp test and hijack resolution.

Use timestamps only for deterministic ordering among candidates after eligibility has been established, not to establish eligibility itself.

### 5. Handle marker inheritance correctly

A legitimate continuation may inherit a model/config marker from the rotated agent. Therefore, rejecting every child with `_delegate_from` or `_branched_from` merely because the key exists can hide a real continuation.

When the codebase's contract permits inherited metadata, bind marker exclusions to the parent being queried:

```text
marker is disqualifying only when marker == queried_parent_id
```

Verify the actual marker semantics before applying this rule. A child explicitly marked as a branch/delegate of the queried parent must remain excluded; a foreign inherited marker must not be mistaken for that relationship.

## Evidence gates for live-vs-pinned lineage investigations

When the incident involves a live checkout, a moving upstream, and a persisted SQLite graph, do not jump from source reading to a patch recommendation. Keep these evidence layers separate:

1. **Runtime layer** — capture the active PID/start time, source path/HEAD, routing entry, and the exact live log/DB rows. A current file is not proof of what an already-running process loaded: if the config mtime is later than process start, classify the in-memory value as a provenance gap unless a startup/reload record proves it.
2. **Candidate layer** — record the candidate commit, parent, branch/worktree, and ancestry relation to the live HEAD. A local commit that fixes a fixture is not deployed, and a commit that sounds equivalent to an upstream PR is not automatically redundant.
3. **Pinned-upstream layer** — use a tag/peeled commit, not moving `main`. Compare the complete caller/test surface, not only the resolver body. Report the exact upstream version, tag SHA, PR/issue state, and any schema or migration assumptions.
4. **Persistence layer** — use a SQLite backup copy for behavior. Keep the first copy read-only and immutable. If the pinned source requires migrations, make a second `/tmp` copy, allow writes only there, record the schema delta, and never silently convert the baseline copy.

### Schema-first provenance guard

Historical handoffs and derived probes may name fields that are not present in the current database schema (for example, reset metadata columns). Before using such a field as evidence, run `PRAGMA table_info(<table>)` against the current copy. If the field is absent, downgrade the historical claim and re-derive the fact from present schema rows, logs, timestamps, or source. Do not add the missing column to the immutable baseline just to make an old probe run; that belongs in a separately labelled migration copy. A migration/schema error is a boundary finding, not a behavior PASS or FAIL.

The copied-DB differential must include:

- the real incident lineage and route identity;
- a reset parent → ordinary child boundary;
- a compression parent → valid continuation chain;
- a >100-hop chain for every fixed-depth walker;
- the actual source/listing path used by `/sessions` and numeric `/resume`;
- the `session_search` wrapper with and without `current_session_id`.

A synthetic reset fixture is invalid if it omits identity fields used by legacy boundary predicates (for example `session_key`, `user_id`, `chat_id`, and `chat_type`). Correct the fixture and rerun before classifying the implementation. Likewise, a no-result search is not automatically an index bug: inspect the current-lineage exclusion and compare direct FTS results with the wrapper result.

For list/resume parity, compare the ordered physical IDs, not just counts or titles. `/sessions` and numeric `/resume` may use different fetch limits, title filters, current-session exclusion, projection, or route scoping; source inspection alone does not prove parity.

Report each result as **LIVE**, **COPY-VERIFIED**, **MIGRATION-COPY**, **SOURCE-ONLY**, **BLOCKED**, or **UNVERIFIED**. Preserve exact errors such as schema incompatibility (`no such column: ...`) instead of silently changing the test database. A WhatsApp/Telegram shared backend means the resolver code is shared; it does not prove that a user reproduced the command on both platforms. Keep topology evidence and user-level reproduction evidence separate.

## Gate 1.5: source closure, route timing, and search identity

When a session/resume incident also involves an incomplete source manifest, a stale-looking durable route, and a search/title complaint, keep the three gates separate before proposing implementation:

1. **Source closure** — prove every runtime input is either in the approved Git tree, pinned to an exact official base, reconstructed by an ordered hashed patch series, or intentionally excluded. A manifest update alone is not closure when required upstream files are absent.
2. **Route timing** — correlate compression-child publication, `Turn ended`, gateway split detection, route persistence, and the durable route row. An ended-parent route observed while the turn is still running is `EXPECTED-IN-FLIGHT-LAG`, not automatically a routing bug. Only post-completion staleness justifies a routing change.
3. **Search identity** — select a genuinely unique physical content fingerprint, compare raw FTS `message_id/session_id` with the wrapper's `match_message_id/session_id`, then test title projection separately. If physical identities agree, drop a standalone search fix; fold only a proven title/display projection defect into the shared listing/resume identity work.

Use the detailed read-only sequence and evidence labels in `references/source-closure-routing-search-gates.md`.

## TDD regression matrix

Use vertical RED→GREEN slices. Do not write production code before seeing the first relevant test fail.

1. **Positive multi-hop chain** — parent ended with the authorized reason, child is a valid continuation, child ends with the same reason, and a later tip is returned.
2. **Intermediate continuation** — resolving the root and resolving an intermediate segment both reach the valid latest tip.
3. **Ordinary child after valid tip** — a non-authorized child exists after the tip; resolution stops at the tip and never crosses it.
4. **Boundary matrix** — for every prohibited reason (`session_reset`, `session_switch`, `idle`, `cron_complete`, intentional boundary values), an ordinary child must not be followed.
5. **Role exclusions** — branch, delegate/subagent, and tool children must not hijack the continuation.
6. **Marker inheritance** — a valid continuation carrying a foreign inherited marker remains eligible; a marker pointing to the queried parent remains excluded.
7. **Exact ID entry point** — `/resume <exact-id>` resolves the same effective ID as the title path.
8. **Exact title entry point** — `/resume <exact-title>` resolves the stored exact title, not a generated label or unrelated variant.
9. **Read-only guarantee** — snapshot relevant session rows before and after resolution; assert no `UPDATE`, `INSERT`, `DELETE`, reopen, routing, or other mutation occurred.
10. **Malformed graph** — cycles and depth overflow fail closed and deterministically.

Repair existing fixtures that create ordinary parented children without setting the parent state required by the contract. Such fixtures accidentally bless a generic graph walk and will either fail after the correct fix or conceal the regression.

## Minimal-fix discipline

Prefer the smallest patch that makes the canonical contract true:

1. Add one failing test for the exact wrong edge.
2. Run it and confirm the failure is behavioral, not a fixture/import error.
3. Remove the broad fallback traversal or route it through the canonical predicate.
4. Run the focused resolver tests.
5. Run every direct caller's contract tests: CLI, gateway/slash command, WebUI/TUI, export/list projection, and recovery/ownership tests where the helper is shared.
6. Only then refactor duplicated SQL/Python fragments into a shared predicate if that refactor is necessary to enforce one definition. Keep refactor and behavior change separable where practical.

Do not “fix” a read-only resolver by adding side effects. Session switching, ending the prior session, reopening the target, and updating routing belong to the command handler after resolution.

## Evidence-first reporting

For a code-only investigation, report:

- exact paths and line/function names;
- the canonical predicate and every duplicate traversal;
- tests that already cover the behavior and tests that model it incorrectly;
- hidden callers and side-effect boundaries;
- what was actually run versus only read;
- the smallest TDD-safe patch sequence.

Do not claim tests pass if they were not run. Do not claim the database is unchanged unless a read-only check or source-level side-effect audit supports it.

## Pitfalls

- **Parented means continuation** — false. `parent_session_id` is a relationship, not authorization.
- **Latest child is always correct** — false. A delegate/tool/reset child may be newer.
- **Timestamp ordering proves lifecycle** — false under concurrent publication.
- **Marker presence proves role** — false when legitimate children inherit configuration.
- **One correct helper is enough** — false if a caller performs a second generic walk.
- **Exact title equals effective ID** — false across compression lineage and title projection.
- **A unit test that only calls the helper is enough** — not when the bug is in a CLI/gateway caller's pre/post-resolution flow.
- **Fixture convenience is harmless** — false; unmodeled parent state can encode the wrong contract.

## Supporting reference

- `references/canonical-state-transition-predicates.md` — Hermes `/resume` case study, predicate matrix, call-surface inventory, and a compact read-only/TDD checklist.
- `references/live-vs-pinned-resume-differential.md` — copied-DB differential recipe, runtime/config provenance gates, migration-copy handling, and the tested `/sessions`/`/resume`/`session_search` contracts.
- `references/closure-gate-controls.md` — direct-release pinning, immutable SQLite `Connection.backup()` baselines, search self-contamination controls, durable route integrity, and >100-hop upstream scope checks.
- `references/source-closure-routing-search-gates.md` — reusable Gate 1.5 sequence for source closure, in-flight versus post-completion route staleness, and raw-FTS-versus-wrapper/title-projection testing.
