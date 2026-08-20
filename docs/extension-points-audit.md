# Extension-Points Audit — Hermes Gate 2 Patches

> **Scope:** Gate 2 provenance remediation finalized in `8f4620e4` (`chore(reconciliation): finalize gate 2 provenance remediation`). This audit examines the three ordered Hermes runtime patches declared in `docs/reconciliation/hermes-runtime-source-lock.json` and classifies each hunk by whether it overrides upstream internals directly vs. whether it could move to a hook/plugin/extension point.
>
> **Authoritative base:** `NousResearch/Hermes-Agent@a31be48030` + ordered `patch_series` → `scripts/reconstruct_hermes_runtime.py` → `docs/reconciliation/hermes-runtime-tree-manifest.json` → manifest-driven deploy. See `docs/reconciliation/hermes-runtime-source-authority.md`.

- **Official base:** `a31be48030f60383bf4c1d96ba46bd4b48430218`
- **Lock file:** `docs/reconciliation/hermes-runtime-source-lock.json` (schema v1, 3 entries)
- **Patch directory:** `patches/upstream-hermes/`
- **Historical overlays (not in lock):** `2026-08-06_p1c-selected-model-contract.patch`, `2026-08-06_vps-runtime-overlays.patch`, `2026-08-11_a4-model-purge-and-test-stability.patch` — source evidence only; see `patches/upstream-hermes/README.md`.
- **Date:** 2026-08-20

---

## 1. Patch Inventory

| # | Patch file | Lock ID | SHA-256 (prefix) | Origin | Files touched |
|---|------------|---------|-----------------|--------|---------------|
| 1 | `2026-08-19_pr85505-reset-boundary.patch` | `official-pr-85505-reset-boundary` | `734a18…` | Official upstream **PR #85505** | `gateway/session.py`, `hermes_cli/cli_agent_setup_mixin.py`, `hermes_state.py`, `hermes_state_common.py`, `hermes_state_schema.py`, + tests |
| 2 | `2026-08-19_c3-unbounded-cycle-safe-lineage.patch` | `custom-c3-unbounded-cycle-safe-lineage` | `a3ce5e…` | **Custom** (fix for fixed-depth walk bug) | `hermes_state.py`, `tests/test_hermes_state.py` |
| 3 | `2026-08-19_c4-shared-session-identity.patch` | `custom-c4-shared-session-identity` | `f7ecbb…` | **Custom** (shared identity / search dedup) | `gateway/slash_commands.py`, `hermes_cli/session_listing.py`, `hermes_state.py`, `tools/session_search_tool.py`, + tests |

> **Naming note:** The task prompt labels these "C2, C3, C4". The lock and Git history use `PR #85505` / `C3` / `C4`. `PR #85505` is the `C2`-equivalent reset-boundary patch (commit `9b21cb41e`, message "adopt reset-boundary continuation semantics"). There is no separate `patches/upstream-hermes/*c2*.patch` file — the C2 work is PR #85505.

---

## 2. What Each Patch Does (Behavior Summary)

### 2.1 PR #85505 — Reset-Boundary Continuation Semantics (`C2`)

**Problem:** Resuming, listing, counting, and gateway peer recovery could not distinguish a *reset continuation* (user ran `/reset` or session switch/idle/daily/suspended/expired) from ordinary child sessions (subagent runs, compression continuations). Resuming a parent could silently follow into the post-reset conversation the user explicitly abandoned. `list_sessions_rich` and counts also misclassified reset children. Legacy DBs had no stable `_reset_from` marker.

**Fix (9 hunks across 5 source files):**

- **`hermes_state_common.py`** — New shared vocabulary:
  - `_RESET_END_REASONS` / `_RESET_END_REASONS_SQL` — canonical reset-end set.
  - `_legacy_reset_child_sql(alias, reasons_sql)` — pre-marker heuristic: child shares parent's exact non-empty `session_key` and parent ended with a reset reason.
  - `_RESET_CHILD_SQL` — stable `json_extract(…'$._reset_from')` **OR** legacy heuristic.
  - `_LISTABLE_CHILD_SQL` rewritten to `roots OR branch OR reset`; `_ephemeral_child_sql` excludes reset as well.
- **`hermes_state.py`** — Four sites:
  - `create_session()` upsert: `model_config` merge preserves a marker-only `_reset_from` when first-turn CLI config arrives (`CASE … json_set …`).
  - `find_latest_gateway_session_for_peer()` — interpolates `_RESET_END_REASONS_SQL` instead of inline string list (prevents drift).
  - `reopen_session()` — before clearing `ended_at/end_reason`, stamps legacy reset children with `_reset_from = parent_session_id` (same `WHERE` shape as the listing predicate via `_legacy_reset_child_sql`).
  - `list_sessions_rich()`, `resolve_resume_session_id()`, `session_count()`, `session_count_by_source()` — adopt the new predicates/exclusions.
- **`gateway/session.py`** — `reset_session()` and `_get_or_create_session_impl()` write `model_config={"_reset_from": prev_session_id}` on the gateway-created child.
- **`hermes_cli/cli_agent_setup_mixin.py`** — `_init_agent()` and `_preload_resumed_session()` replace raw `UPDATE sessions SET ended_at=NULL …` with `reopen_session()` (so legacy stamping runs).
- **`hermes_state_schema.py`** — schema v16 migration commentary updated.

### 2.2 C3 — Unbounded Cycle-Safe Lineage (`custom-c3`)

**Problem:** `get_compression_tip()` and `_session_lineage_root_to_tip()` used `for _ in range(100)` — silently stopped after 100 hops. Real compression chains can exceed 100. No explicit cycle guard beyond the depth cap.

**Fix:**

- **`hermes_state.py`** — New `_walk_session_ids(start, next_id)` helper: visited-set walk, no depth bound, returns the chain (or stops on cycle). Both resolvers delegate to it via thin `_next_*` closures.
- **Tests** — 218-hop chains + explicit `cycle_a ↔ cycle_b` cycle test.

### 2.3 C4 — Shared Session Identity Projection (`custom-c4`)

**Problem:** Three identity mismatches:
1. `gateway/slash_commands.py` `_list_titled_sessions()` used `list_sessions_rich(limit=10, title-filter)` — different ordering/policy than `hermes_cli/session_listing.query_session_listing`. Numeric `/resume` listing diverged from picker listing.
2. `resolve_empty_head_walk()` in `hermes_state.py` had a bespoke 32-hop message-scan walk distinct from `get_compression_tip()` — the two could disagree on which edge is a compression continuation vs. a branch/delegate/reset/tool child.
3. `tools/session_search_tool.py` `_resolve_to_parent()` / `_resolve_lineage()` walked `parent_session_id` generically via `get_session()`, conflating reset/branch/delegate children with compression continuations for dedup. Title projection used the lineage root row instead of the physical hit row, losing `#NNN` suffixes.

**Fix:**

- **`gateway/slash_commands.py`** — delegates to `query_session_listing(…, order_by_last_active=True, exclude_sources=["tool"])` + widens via `AsyncSessionStore.get_or_create_session` for `current_session_id` scoping. One-line `session_listing.py` change flips `order_by_last_active=bool(search)` → `True` so CLI listing is activity-ordered.
- **`hermes_state.py`** — New `get_compression_parent_id(session_id)` (canonical reverse edge: `child.parent_session_id = parent.id AND parent.end_reason='compression' AND no _branched/_delegate marker AND source!='tool'`). `resolve_empty_head_walk()` collapsed to `get_compression_tip() or session_id`.
- **`tools/session_search_tool.py`** — `_resolve_to_parent()` now calls `get_compression_parent_id` (fail-closed if absent); `_resolve_lineage()` split out as the broader ownership fence (generic `parent_session_id` walk, used for current-session visibility, not dedup). `_title_match_result()` and `search_messages()` preserve physical `hit_sid` row titles instead of lineage-root titles.

---

## 3. Classification: Direct Internal Override vs. Hook/Plugin-Capable

### Rubric

- **Direct internal override** — modifies upstream SQL predicates, storage/migration, or private method contracts that are not yet behind a stable extension point. Requires a patch (or upstream PR) to take effect.
- **Hook/plugin-capable today** — the Hermes runtime already exposes an extension point that could carry the logic without patching internals (verified by inspecting `hooks/` and `plugins/` on this branch).
- **Future hook/plugin after upstream refactor** — no extension point exists today, but a scoped refactor (e.g., introducing a listing/resume/lineage hook or policy interface) would make it pluggable. Listed as *not-pluggable today, pluggable after a small upstream change*.
- **Sugar/inline-constant extraction** — mechanical deduplication of inline constants into a shared symbol; not pluggable, but trivially upstreamable as a literal refactor.

### 3.1 PR #85505 — Classification by Hunk

| Area | Files / symbols | Verdict | Rationale |
|------|-----------------|---------|-----------|
| Reset vocabulary | `hermes_state_common._RESET_*`, `_RESET_CHILD_SQL`, `_legacy_reset_child_sql`, `_LISTABLE_CHILD_SQL` | **Direct override — Sugar/Constant extraction** | New shared predicates/constants. Not a hook; correct place is `hermes_state_common.py`. Upstream PR exists. |
| `create_session` upsert merge | `hermes_state.py: create_session … CASE json_set($._reset_from)…` | **Direct override** | Upsert path inside `HermesState`. No plugin hook intercepts `create_session` upserts today (agent storage is internal). |
| Gateway reset marker | `gateway/session.py: reset_session`, `_get_or_create_session_impl` | **Direct override** | Gateway session creation internals. Gateway has no session-creation plugin point; this is the gateway's single place to write the routing key's identity. |
| CLI reopen path | `hermes_cli/cli_agent_setup_mixin.py` → `reopen_session` | **Direct override — Indirect via PR #85505's `reopen_session`** | CLI agent setup is not hook-extensible; the correct fix is exactly the patch's delegation to the DB's stamping method. |
| DB `reopen_session` stamping | `hermes_state.py: reopen_session()` UPDATE with `_legacy_reset_child_sql` | **Direct override** | Schema/DB write path. No safe plugin could run SQL inside the atomic write transaction via an extension point that doesn't exist today. |
| Listing/resume/count predicates | `hermes_state.py: list_sessions_rich / resolve_resume_session_id / session_count*` | **Direct override — Future pluggable via listing/resume policy hook** | Today these are raw SQL methods. Could move to a `SessionListingPolicy` / `ResolveResumePolicy` interface, but none exists. Treat as direct override until upstream introduces one. |
| `find_latest_gateway_session_for_peer` | `hermes_state.py` inline → `_RESET_END_REASONS_SQL` interpolation | **Direct override — Sugar** | Same evidence set, just deduplicated. |
| Schema comment | `hermes_state_schema.py` v16 comment | **Direct override — Comment** | No extension surface. |

**PR #85505 overall: entirely direct internal overrides.** No hunk is hook/plugin-capable today. That is expected — this is the official upstream PR fixing DB identity semantics and the gateway must write/read the same marker.

### 3.2 C3 — Classification by Hunk

| Area | Symbols | Verdict | Rationale |
|------|---------|---------|-----------|
| `_walk_session_ids` helper + two call sites | `hermes_state.py` | **Direct override — Future pluggable via lineage-resolver hook** | Fixes data-dependent traversal inside authenticated DB reads. No hook can intercept `get_compression_tip` / `_session_lineage_root_to_tip` cursor loops today; they are not exposed through `hooks/` or `plugins/`. A future `CompressionLineageResolver` strategy object or DB-level traversal hook could isolate it, but none exists upstream. |

**C3 overall: direct internal override.** The defect is in core storage traversal correctness; a plugin over read-only search could not have fixed it.

### 3.3 C4 — Classification by Hunk

| Area | Symbols / files | Verdict | Rationale |
|------|-----------------|---------|-----------|
| `hermes_cli/session_listing.py: order_by_last_active=True` | 1-line flag flip | **Direct override — Sugar/Behavior flag** | Single boolean default change inside the dedicated listing module. No extension point governs it today; a listing-options hook could, but none exists. |
| `gateway/slash_commands.py: _list_titled_sessions → query_session_listing` | gateway slash command | **Direct override — Future pluggable via slash-command listing delegate** | Gateway slash commands have no listing-delegate hook; `search-cascade`/`hybrid-web` plugins live under `plugins/` as providers and cannot intercept gateway command internals. After introducing a `SessionListingProvider` / `SlashCommandListingHook`, this could move. Today: direct override. |
| `hermes_state.py: get_compression_parent_id` + `resolve_empty_head_walk` collapse | new reverse edge + simplification | **Direct override — Future pluggable via resume/lineage hook** | New canonical DB predicate plus consolidation of a redundant walker. No existing extension point can inject the reverse-edge SQL or replace the walker. |
| `tools/session_search_tool.py: _resolve_to_parent` → `get_compression_parent_id` (fail-closed) + `_resolve_lineage` split + title fix | search tool | **Partially hook-adjacent, but Direct override today** | `tools/session_search_tool.py` is itself **tool/provider** surface (closer to plugin than `hermes_state.py`). However the change depends on the new `get_compression_parent_id` DB method and on correct ownership-fence vs. dedup semantics — both internal. A future `SessionSearchIdentityResolver` hook wrapping these two functions could make them swappable; no such hook exists. |

**C4 overall: direct internal overrides** (one gateway, one DB, one CLI listing flag, one tool-adjacent file). The tool file is the only one that *could* have lived closer to plugin surface, but its correctness depends on a new DB primitive introduced by the same patch.

---

## 4. Why None of Gate 2 Moves to Current Hooks/Plugins (Evidence)

- **Current hooks (`hooks/hello-world`, `hooks/med-auto-confirm`, `hooks/skill-trigger`):** hook triggers are `agent:start` / `gateway:startup` / custom skill triggers. No hook intercepts DB reads, listing, resume resolution, or peer recovery. All logic runs via `handler.py` on coarse lifecycle events — not on per-query session resolution.
- **Current plugins (`plugins/search-cascade`, `hybrid-web`, `trafilatura`, `google-workspace-commands`, `lightclawbot`):** plugin YAMLs (`plugin.yaml`) declare `kind: standalone`, providers, and tools. None expose a hook into `hermes_state*.py` or the gateway's `SessionStore`. Providers are additive (search fallbacks, web operators), not overrides of storage/identity predicates.
- **Conclusion:** moving any Gate 2 hunk to the current extension surface would require inventing a *new* extension point first. There is no existing surface to reuse.

---

## 5. PR Candidates for Upstream (`NousResearch/Hermes-Agent`)

### Already upstream

- **PR #85505 — `official-pr-85505-reset-boundary`** — Official Nous pull request. Already the correct upstream vehicle. Keep pinned at the lock's SHA; no separate fork PR needed.

### Recommended new upstream PRs (from the two custom patches)

#### PR-1 — Cycle-safe, unbounded lineage traversal (from `custom-c3`)

- **Source:** `patches/upstream-hermes/2026-08-19_c3-unbounded-cycle-safe-lineage.patch`
- **Title suggestion:** `fix(state): unbounded cycle-safe compression lineage traversal`
- **Scope:** `hermes_state.py: _walk_session_ids` + `get_compression_tip` / `_session_lineage_root_to_tip` call sites
- **Evidence:** `tests/test_hermes_state.py`: `test_compression_tip_follows_more_than_100_continuations`, `test_lineage_root_to_tip_follows_more_than_100_parents`, `test_lineage_walkers_stop_on_cycles` (218-hop + cycle)
- **Upstream value:** Fixes a latent correctness bug (depth cap = silent truncation). Small, isolated, no schema/migration impact. Strong upstream PR candidate.
- **Risk:** Low — visited-set is strictly safer than a fixed bound.

#### PR-2 — Unified compression-continuation identity + search deduplication (from `custom-c4`)

- **Source:** `patches/upstream-hermes/2026-08-19_c4-shared-session-identity.patch`
- **Title suggestion:** `fix(sessions): canonical compression-continuation identity and listing/search alignment`
- **Scope (bundle, or split into 2 PRs):**
  - **2a — DB + gateway/listing alignment:** `hermes_state.py:get_compression_parent_id`, `resolve_empty_head_walk` collapse, `gateway/slash_commands.py:query_session_listing` delegation, `hermes_cli/session_listing.py:order_by_last_active=True`.
  - **2b — Search dedup semantics:** `tools/session_search_tool.py: _resolve_to_parent` (fail-closed on `get_compression_parent_id`), `_resolve_lineage` split, physical-hit title preservation.
- **Evidence:** `tests/test_hermes_state.py` lineage tests, `tests/tools/test_session_search.py` dedup/branch/fork tests, `tests/gateway/test_resume_command.py` listing identity tests, `tests/hermes_cli/test_session_listing.py` ordering tests
- **Upstream value:** Resolves user-visible divergence between resume, listing, and search identities. Collapses a redundant walker. Makes search titles faithful to the physical continuation row.
- **Risk:** Medium — identity predicate change. Mitigated by the expanded regression contract explicitly added in this PR (compression chains, generic parent edges, fork ambiguity) and by the `_RESET_*` vocabulary already in PR #85505.

#### Defer / Do Not Propose Separately

- **`hermes_cli/session_listing.py: order_by_last_active` flag flip** — ship inside PR-2a; not a standalone PR.
- **`tools/session_search_tool.py` title fix alone** — ship inside PR-2b; not a standalone PR.

### Non-PR Material (Keep Local)

- Historical overlays `2026-08-06_p1c-selected-model-contract.patch` / `2026-08-06_vps-runtime-overlays.patch` / `2026-08-11_a4-model-purge-and-test-stability.patch` — site-specific VPS overlays (model catalog, runtime resolver, gossip/execution context, goals, bridge controller). Not generic upstream features; keep as local source evidence per `patches/upstream-hermes/README.md`.

---

## 6. What an Extension-Point Refactor Would Look Like (If Pursued)

These are **recommendations for future upstream work**, not today's hook/plugin move.

1. **Listing/resume policy interface** — Extract `SessionListingPolicy` / `ResumePolicy` from `hermes_state.py` into a testable policy object with a plugin hook (`plugins/session-policy`?). PR #85505's SQL predicates and C4's `query_session_listing` delegation would then be policy config, not scattered SQL edits.
2. **Lineage traversal strategy** — Extract `CompressionLineageResolver` (C3's `_walk_session_ids` + C4's `get_compression_parent_id`/`get_compression_tip` family) into a single class with injected `next_parent` / `next_child` strategies. Makes cycle-safety and depth bounds testable in isolation.
3. **Search identity hook** — Split `tools/session_search_tool.py`'s two concerns (`_resolve_to_parent` = dedup identity, `_resolve_lineage` = ownership fence) behind an interface (`SessionSearchIdentityResolver`) so alternative resolvers can be swapped without patching the search tool.

None of these should block the two PRs above — they are follow-on design work once the correctness fixes land.

---

## 7. Checklist for Reviewers

- [ ] Confirm `docs/reconciliation/hermes-runtime-source-lock.json` patch SHAs match on-disk `patches/upstream-hermes/*.patch` (re-run `python3 scripts/reconstruct_hermes_runtime.py --validate` / `scripts/guard/*`).
- [ ] If submitting upstream, open PR-1 (C3) first — it is the smallest/safest and unblocks PR-2's lineage vocabulary.
- [ ] For PR-2, consider splitting 2a/2b to keep review scope narrow; keep the same branch's test suite green end-to-end.
- [ ] After upstream merges PR #85505's successor SHA, update the lock's `official_base_sha` / `patch_series` accordingly (release-gated via `APPROVE RELEASE <sha>` per `AGENTS.md`).

---

## 8. References

- Lock: `docs/reconciliation/hermes-runtime-source-lock.json`
- Authority: `docs/reconciliation/hermes-runtime-source-authority.md`
- Overlays README: `patches/upstream-hermes/README.md`
- PR #85505 patch: `patches/upstream-hermes/2026-08-19_pr85505-reset-boundary.patch` (commit `9b21cb41e`)
- C3 patch: `patches/upstream-hermes/2026-08-19_c3-unbounded-cycle-safe-lineage.patch` (commit `6933cdcc`)
- C4 patch: `patches/upstream-hermes/2026-08-19_c4-shared-session-identity.patch` (commit `8f4620e4` delta; final state `d8da8e18c` listing-identity unification)
- Reconstruction: `scripts/reconstruct_hermes_runtime.py`, `docs/reconciliation/hermes-runtime-tree-manifest.json`
- Historical classification: `docs/reconciliation/gate4-classification-ledger.md`, `docs/reconciliation/post-gate7-audit-debt-classification.md`
