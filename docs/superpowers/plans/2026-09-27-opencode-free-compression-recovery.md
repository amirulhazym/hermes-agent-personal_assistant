# Implementation Plan: OpenCode Free 403 & Compression Auxiliary Runtime Drift Recovery

> **Execution contract:** Follow `/xcute`. This document is Phase 2 planning only. Do not modify live config/runtime/session state, restart the gateway, publish, or deploy before the Phase 3 owner approval gate.

- **Date:** 2026-09-27
- **Feature Slug:** `opencode-free-compression-recovery-2026-09-27`
- **Spec:** `.scratch/opencode-free-compression-recovery-2026-09-27/spec.md`
- **Tickets:** 01 fail-close OpenCode Free, 02 restore auxiliary middleware, 03 Codex Luna default, 04 targeted drift/release proof.
- **Current SSOT HEAD:** `50bf2df99cf5d6e0e36ce908502cacb613186ffc`

## Locked Decisions

1. `opencode-free` chat is fail-closed while OpenCode rejects external Hermes use.
2. Global default target is `openai-codex / gpt-6-luna`.
3. Current live Codex discovery contains `gpt-6-luna` but not `gpt-6-luna-900k`; no synthetic 900k alias.
4. Existing Telegram/WhatsApp session overrides are untouched; owner will manually switch/retry.
5. Repair Antigravity auxiliary routing and add targeted live-byte drift detection.
## Task 1 — RED: OpenCode Free must be unavailable to Hermes chat

**Candidate source/tests after reconstruction**
- `hermes_cli/models.py`
- `hermes_cli/model_switch.py`
- `plugins/model-providers/opencode-free/__init__.py` only if provider-profile behavior must change
- `tests/agent/test_opencode_free_provider.py`
- `tests/hermes_cli/test_opencode_free_live_catalog.py`
- relevant shared picker/model-switch tests

- [ ] Reconstruct current authoritative Hermes candidate from source lock + tree manifest.
- [ ] Add failing tests: shared picker excludes `opencode-free`; typed provider aliases `opencode-free` and `free` are rejected; known free model IDs cannot bypass the provider block.
- [ ] Run only the new/affected tests and capture genuine RED failures.
- [ ] Implement the smallest fail-closed policy at the common catalog/selection boundary.
- [ ] Keep `opencode-go` unchanged and retain the existing `opencode-zen` fail-closed contract.
- [ ] Re-run targeted tests to GREEN.
- [ ] Capture the candidate diff for this slice before moving on.
## Task 2 — RED/GREEN: restore auxiliary Antigravity middleware routing

**Candidate source/tests**
- `agent/auxiliary_client.py`
- `tests/agent/test_auxiliary_relay.py`
- affected compression/auxiliary tests
- existing SSOT patches:
  - `patches/upstream-hermes/2026-08-28_live-auxiliary-middleware-route.patch`
  - `patches/upstream-hermes/2026-08-28_harden-auxiliary-middleware-fail-closed.patch`

- [ ] Add a focused failing test proving sync auxiliary calls for `provider=antigravity` pass through `run_llm_execution_middleware`.
- [ ] Add/retain a failing-path assertion that middleware exceptions do not silently fall through to direct HTTP creation.
- [ ] Run the focused test to prove RED against the drifted behavior baseline or an intentionally stripped candidate fixture.
- [ ] Restore the authoritative relay behavior in the reconstructed candidate; do not edit `/home/ubuntu/.hermes/hermes-agent` directly.
- [ ] Run auxiliary relay, auxiliary client, compression, and Antigravity integration tests to GREEN.
- [ ] Verify reconstructed `agent/auxiliary_client.py` hash matches the tree manifest entry.
## Task 3 — RED/GREEN: make Codex GPT-6 Luna the default

**SSOT/config targets**
- `config/config.yaml.template`
- focused config-contract test added under `tests/reconciliation/` if no existing test covers the root model tuple
- live `/home/ubuntu/.hermes/config.yaml` is execution-stage only

- [ ] Add a failing SSOT test asserting root `model.provider == openai-codex` and `model.default == gpt-6-luna`.
- [ ] Add a discovery assertion that `gpt-6-luna-900k` is never synthesized when absent from Codex live discovery.
- [ ] Run the focused test to prove RED on the current template.
- [ ] Update only the SSOT template to the approved tuple.
- [ ] Re-run config/Codex tests to GREEN.
- [ ] Do not alter stored session overrides, `state.db`, or `sessions.json`.

## Task 4 — RED/GREEN: targeted SSOT-vs-live drift gate
**Targets**
- `scripts/deploy_hermes_runtime.py` or a minimal adjacent verifier, whichever yields the smallest change
- `tests/reconciliation/test_runtime_dependency_drift.py` and/or a new focused selective-parity test
- a release-specific selective runtime manifest for this repair

- [ ] Define the exact managed runtime paths for this release, including `agent/auxiliary_client.py` and any model-routing files changed by Task 1.
- [ ] Add a synthetic failing test: candidate hash differs from live destination → gate reports the exact path and fails.
- [ ] Add boundary test: unrelated unmanaged live drift does not fail this selective release gate.
- [ ] Implement the minimal preflight/read-back comparison.
- [ ] Run the targeted drift tests to GREEN.
- [ ] Demonstrate the gate against the current VPS read-only: it must identify the existing `agent/auxiliary_client.py` mismatch before deployment.

## Task 5 — Candidate consolidation & quality gates

- [ ] Generate one incremental upstream patch for new Hermes core changes rather than editing historical patches.
- [ ] Append it to `docs/reconciliation/hermes-runtime-source-lock.json` and regenerate the tree manifest deterministically.
- [ ] Build a fresh reconstructed candidate and validate it.
- [ ] Build the selective deployment payload for only this incident's approved runtime files.
- [ ] Run targeted suites, then `bash scripts/run_contract_tests.sh`.
- [ ] Run `bash scripts/guard/secret-scan.sh --tree`.
- [ ] Run `python3 scripts/guard/pii-review.py --diff origin/main..HEAD`.
- [ ] Recompute/validate the source coverage manifest as required by the repository contract.
## Task 6 — Phase 3 owner gate before execution/deployment

Present the Review Brief & Architecture Lock with:
- Root Cause: live auxiliary middleware drift caused Antigravity compression to hit its dummy URL; fallback then used provider-rejected OpenCode Free.
- Selected Values: fail-close `opencode-free`; default `openai-codex/gpt-6-luna`; no session migration; targeted drift gate.
- Output Preview: picker rejection for OpenCode Free, working Codex default for new/global routing, Antigravity compression using middleware instead of direct 127.0.0.1 traffic.
- Artifacts: this spec, four tickets, and this plan.
- Exact candidate SHA/diff scope if Phase 4 preparation has produced one.
- Status: plan only / ready for owner approval.

**MANDATORY STOP:** no live config write, no framework deployment, no gateway reload, no session mutation, no push/PR/merge.

## Post-approval execution/smoke requirements

After an explicit Phase 3 approval, Phase 4/5 must use TDD and protected Git flow. Runtime smoke must prove: (1) global config resolves to `openai-codex/gpt-6-luna`; (2) OpenCode Free is unavailable in shared Telegram/WhatsApp picker; (3) compression invokes Antigravity successfully without `Connection refused` to the dummy URL; (4) no fallback reaches `opencode-free`; (5) live hashes match the selective approved candidate after deployment.

Existing active sessions remain untouched throughout; the owner will manually run Hermes `/model` and retry as already decided.
