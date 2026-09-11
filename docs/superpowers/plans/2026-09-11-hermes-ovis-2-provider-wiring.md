# `hermes_ovis_2_bot` Provider Wiring Implementation Plan

> **For agentic workers:** Use strict RED-GREEN-REFACTOR TDD for the framework behavior change. Do not edit the deployment-managed framework checkout directly; represent the final source change as an exact patch overlay in the personal SSOT. Runtime config/process actions require the Phase 3 owner approval.

**Goal:** Make `bot_2` the effective profile for `@hermes_ovis_2_bot`, keep one default multiplex gateway as the token owner, and prevent stale/missing profile identities from falling back to global provider configuration.

**Architecture:** The default gateway remains the single process owner and serves `default` plus the configured `bot_2` profile. A narrow fail-closed guard at the existing profile-home/message-handler seam rejects an explicit profile that is absent or unserved instead of entering global `HERMES_HOME`. Provider verification stays at registration → resolution → picker → zero-token model discovery; inference and channel E2E remain separate gates.

**Tech Stack:** Python 3.11, Hermes `GatewayRunner`, `profiles_to_serve`, `ProfileRouteRejected`/`profile_route_rejected`, pytest, PyYAML/config CLI, existing zero-token provider probe, exact upstream patch overlays, SSOT manifest/contract/security gates.

## Global Constraints

- Canonical profile is exactly `bot_2`; do not create an undocumented `ovis2` alias.
- Topology is exactly one default multiplex gateway; no second gateway may own the same Telegram token.
- Provider verification is zero-token only until separately authorized.
- No `.env`, `auth.json`, state DB, sessions, logs, raw tokens, or private runtime data enter Git/artifacts.
- No direct development edits under `/home/ubuntu/.hermes/hermes-agent`.
- Runtime config changes, gateway stop/start/reload, stale-routing cleanup, deployment, push, and release require the Phase 3/owner gate.
- External provider errors remain classified as external/shared status, not silently patched as part of profile wiring.
- Preserve the current default behavior for genuinely unrouted sources.

---

## Task 1: Fail closed on an explicit missing/unserved profile

**Files in the isolated framework candidate:**
- Modify: `gateway/run.py` — `_resolve_profile_home_for_source`, `_make_profile_message_handler`, and the default-profile handler if required to catch the rejection.
- Modify: `tests/gateway/test_profile_resolution.py` — replace the unsafe fallback expectation and add the handler-level regression.
- Candidate overlay later: `patches/upstream-hermes/2026-09-11_profile-routing-fail-closed.patch`.

**Interface:** `GatewayRunner` must either return an existing effective profile home or reject/drop an explicit profile source. It must not return global/default `HERMES_HOME` for an explicit profile that is absent/unserved.

- [ ] **Step 1 — RED:** Change the test expectation for `source.profile="nonexistent"` from global fallback to a fail-closed `ProfileRouteRejected`/rejection result. Add a test where a secondary profile handler is invoked after its profile directory is absent; assert the agent handler/provider path is not entered.
- [ ] **Step 2 — Verify RED in an isolated candidate.** Run:

```bash
PYTHONPATH=. pytest -q tests/gateway/test_profile_resolution.py
```

Expected: the changed missing-profile assertions fail against the current implementation because it returns global HERMES_HOME.
- [ ] **Step 3 — GREEN:** Implement the smallest guard at the existing seam. For an explicit profile, check `profile_exists()`/served-profile validity; mark the source with the existing strict `profile_route_rejected` marker or raise the existing rejection type; route the event through the existing ingress drop path. Do not add a new provider resolver or a new fallback ladder.
- [ ] **Step 4 — Verify GREEN:** Re-run the focused test. Then run the existing profile-routing suite, including non-Discord/Telegram route and rejected-route tests.
- [ ] **Step 5 — Adversarial regression:** Prove an unrouted source with no explicit profile still uses the default profile, while an explicit stale profile never enters default scope. Preserve secret-free log context only.

**Checkpoint A:** The isolated candidate has a failing test that catches the original bug, a minimal fail-closed implementation, and focused tests green. No live runtime state changed.

---

## Task 2: Prove the canonical `bot_2` served-profile topology

**Files in the isolated candidate:**
- Add/modify a focused profile-enumeration regression test under the framework test tree if existing coverage does not assert the allowlist boundary.
- No secret-bearing runtime file is copied into the SSOT.

**Interfaces:** `profiles_to_serve(multiplex=True, profile_allowlist=["bot_2"])` is the served-profile chokepoint; root runtime config is changed later only through the supported config command.

- [ ] **Step 1 — RED:** Add an isolated fixture with `default` and `bot_2` directories, no `ovis2` directory, and allowlist `bot_2`. Assert the served set is exactly `default` + `bot_2`; assert a missing `ovis2` allowlist entry is warned/skipped rather than served.
- [ ] **Step 2 — Verify RED** against the candidate if the exact allowlist/served-set contract is not already covered.
- [ ] **Step 3 — GREEN:** Keep the existing enumerator behavior if it already satisfies the test; only add source changes if the test exposes a real defect. Do not widen the allowlist implicitly or create an alias.
- [ ] **Step 4 — Run focused profile/config tests** and preserve the raw output.

**Operational slice after Phase 3 approval (not executed in this planning phase):**

1. Snapshot root config, root `gateway_state.json`, `bot_2` state, token-lock metadata, and the orphan `gateway_routing` row without printing secrets.
2. Use the supported config command to set the root multiplex allowlist to exactly `[bot_2]`; read the field back.
3. Stop/retire the duplicate standalone `bot_2` process through the supported lifecycle path; do not delete its profile files.
4. Perform the approved clean default-gateway reload/restart in a safe window.
5. Read back `served_profiles`, `bot_2:telegram` state, token-lock ownership, and process/service topology. Do not call this live until all read-backs agree.

**Checkpoint B:** Runtime config and process changes remain on hold until owner approval; the candidate has a deterministic served-profile contract.

---

## Task 3: Zero-token provider boundary verification under `bot_2`

**Files/artifacts:**
- Use existing `skills/autonomous-ai-agents/hermes-custom-provider/scripts/zero-token-provider-probe.py`.
- Preserve raw probe outputs under a bounded evidence directory, not in Git if they contain private runtime metadata.
- No provider adapter code is changed by this task.

- [ ] **Step 1:** In a fresh process with `HERMES_HOME=/home/ubuntu/.hermes/profiles/bot_2`, run the resolver/picker path and capture provider IDs, base URLs, model counts, and source labels with secrets redacted.
- [ ] **Step 2:** Run the zero-token model-list probe for `bot_2`. Do not run a chat completion.
- [ ] **Step 3:** Compare against the already captured `default` control without inferring inference success.
- [ ] **Step 4:** Classify each provider separately as `REGISTRATION`, `RESOLUTION`, `PICKER INVENTORY`, `MODEL DISCOVERY`, `INFERENCE NOT RUN`, `GATEWAY RELOAD`, or `CHANNEL E2E`.
- [ ] **Step 5:** Preserve the known current classifications: Antigravity loopback connection refusal is shared/external; Fiq HTTP 503 is provider maintenance; Codex/Copilot HTTP 400 is unresolved probe/auth-contract status, not a proven adapter defect.

**Checkpoint C:** `bot_2` provider wiring is either proven at zero-token boundaries or has an explicit per-provider data gap. No “all providers fixed” claim is allowed.

---

## Task 4: Capture the intentional framework change as an SSOT overlay

**Files/artifacts:**
- Create/update: `patches/upstream-hermes/2026-09-11_profile-routing-fail-closed.patch`.
- Modify: `docs/reconciliation/hermes-runtime-source-lock.json` only after the candidate patch is tested and its SHA is known.
- Update: `docs/reconciliation/hermes-runtime-tree-manifest.json` if the patch changes the tracked runtime path set.

- [ ] Materialize the pinned upstream/live-aligned candidate in an isolated temporary directory; do not branch/edit the live framework checkout.
- [ ] Apply the TDD-tested fail-closed source change and any test hunk intended for durable source closure.
- [ ] Generate the exact binary/full-index patch and record its base SHA, changed paths, patch SHA-256, and disposition.
- [ ] Run focused profile-routing tests, relevant gateway multiplex tests, and the applicable full regression subset from the candidate interpreter.
- [ ] Run `git diff --check`/candidate path checks, secret scan, PII review, manifest validation, and the repository contract test runner. Preserve raw outputs and exit codes.
- [ ] Stop at the Phase 3/owner release gate. No deployment, config mutation, process reload, push, merge, or release approval is implied by a green candidate.

---

## Dependency Graph

```text
Task 1 (fail-closed source seam)
        ↓
Task 2 (bot_2 served-profile contract + approved operational migration)
        ↓
Task 3 (bot_2 zero-token provider boundary verification)
        ↓
Task 4 (exact SSOT overlay and release gates)
```

## Rollback

Candidate rollback is exact-tree restoration before patch capture. Runtime rollback, if later approved, is an exact pre-change config/process/manifest restoration with token-lock and served-profile read-back. Do not use wildcard deletion, direct SQLite edits, or a second competing gateway as rollback mechanisms.

## Completion Boundary

This plan is complete only when the source candidate, runtime migration, provider boundary evidence, and SSOT overlay each have separate receipts. A passing resolver or model-list probe does not prove gateway reload, inference, or Telegram channel E2E.
