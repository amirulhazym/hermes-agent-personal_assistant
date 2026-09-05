# Bounded Main-Turn Auto-Continue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use strict RED-GREEN-REFACTOR TDD and cross-boundary seam verification. Do not edit the deployment-managed framework checkout directly; represent the final framework change as a patch overlay in the personal SSOT.

**Goal:** Let a progressing main CLI/gateway turn continue through two additional 300-iteration windows while preserving approval, idempotency, cost, and existing fallback safety.

**Architecture:** Keep the existing per-window `agent.max_turns` budget and add a narrow continuation controller at the existing `run_conversation()` production seam. The controller consumes structured tool/mutation/checkpoint progress evidence, emits a decision receipt, and appends a synthetic `auto_continue` message only when the current window is eligible. `/goal` and delegation remain separate budget owners.

**Tech Stack:** Python 3.11, PyYAML/config loader, Hermes `AIAgent.run_conversation`, SessionDB synthetic-message metadata, pytest, existing gateway/CLI contract guards, SSOT patch overlays.

## Global Constraints

- Active profile target: `agent.max_turns: 300`.
- Active profile continuation bound: `2` additional windows.
- First implementation surface: main CLI/gateway turns only.
- General feature default: disabled; active-profile enablement is a separate approved config action.
- Never auto-continue after approval/clarify, user interrupt, provider failure, timeout, unknown side effect, or no objective progress.
- Never write directly to `/home/ubuntu/.hermes/hermes-agent` during development.
- Do not alter `/goal`, delegation budgets, or the paused Nightly Git task in this feature.
- No force-push; final publication follows protected-main flow only after owner release approval.

---

## Task 1: Configuration contract and receipt types

**Files:**
- Modify: `hermes_cli/config_defaults.py`
- Modify: `hermes_cli/config.py`
- Modify: `gateway/run.py` only if the existing config bridge does not expose the new block
- Test: `tests/hermes_cli/test_iteration_auto_continue_config.py`

**Interfaces:**
- Consumes: existing resolved `agent.max_turns` and user config loader.
- Produces: typed/validated continuation settings and stable receipt field names for the controller.

- [ ] **Step 1: Write the failing tests.** Cover absent/disabled config, enabled config with `max_auto_continues=2`, malformed values, non-positive values, and preservation of `agent.max_turns=300`.
- [ ] **Step 2: Run the focused test and confirm RED.**

Run:
```bash
PYTHONPATH=. pytest -q tests/hermes_cli/test_iteration_auto_continue_config.py
```

Expected: collection or assertion failures because the new config block/normalizer does not exist.
- [ ] **Step 3: Implement the smallest config normalization path.** Keep the feature disabled by default, validate the positive continuation bound, and preserve the existing unlimited spelling resolver unchanged.
- [ ] **Step 4: Run the focused test and confirm GREEN.**
- [ ] **Step 5: Run the existing resolver regression test.**

Run:
```bash
PYTHONPATH=. pytest -q tests/hermes_cli/test_resolve_turn_limit.py
```

Expected: all existing resolver tests pass.

---

## Task 2: Progress snapshot and continuation decision policy

**Files:**
- Create: `agent/iteration_continuation.py`
- Modify: `agent/tool_executor.py` only at the existing canonical tool-result/effect-disposition seam
- Modify: `agent/agent_init.py` for per-agent policy state
- Test: `tests/run_agent/test_iteration_continuation_policy.py`

**Interfaces:**
- Consumes: window budget state, tool completion outcomes, file-mutation/checkpoint evidence, interrupt/failure/approval flags.
- Produces: `ProgressSnapshot`, `ContinuationDecision`, and a deterministic idempotency key for `(turn_id, window_index)`.

- [ ] **Step 1: Write the failing policy tests.** Include one eligible-progress case, repeated/no-op case, unknown-effect case, interrupted case, approval-pending case, provider-failure case, disabled case, and exhausted-bound case.
- [ ] **Step 2: Run the focused policy test and confirm RED.**
- [ ] **Step 3: Implement the minimal immutable snapshot/decision types.** Count only canonical tool outcomes; do not treat a blocked or unknown-effect call as progress. Preserve secret-free fingerprints only.
- [ ] **Step 4: Wire the existing tool-result seam to update per-window evidence.** Do not add a second tool execution pipeline.
- [ ] **Step 5: Run policy and existing tool-executor tests.**

Run:
```bash
PYTHONPATH=. pytest -q tests/run_agent/test_iteration_continuation_policy.py tests/run_agent/test_tool_activity_heartbeat.py
```

Expected: all focused tests pass.

---

## Task 3: Wire one continuation into the real `run_conversation()` seam

**Files:**
- Modify: `agent/conversation_loop.py`
- Modify: `agent/turn_finalizer.py` only to expose a non-summary continuation decision before fallback
- Modify: `agent/iteration_budget.py` if an explicit safe window reset/extension is required
- Test: `tests/run_agent/test_iteration_budget_auto_continue.py`

**Interfaces:**
- Consumes: `ContinuationDecision` from Task 2 and existing max-iteration/finalizer state.
- Produces: one synthetic continuation message per idempotency key, a fresh 300-iteration window, and a final structured receipt.

- [ ] **Step 1: Write the failing seam tests.** Exercise a real `AIAgent.run_conversation()` path with a controlled provider sequence: eligible progress → budget exhaustion → continuation → final text.
- [ ] **Step 2: Run the seam test and confirm RED.** Expected current behavior: the first exhaustion enters summary/fallback and no `auto_continue` row is appended.
- [ ] **Step 3: Implement the smallest loop control path.** At an eligible budget boundary, append a synthetic user message with `display_kind=auto_continue`, preserve the original prompt, advance the window index, reset only the iteration-window counter, and continue through the existing tool/API path. Do not mutate the cached system prompt or toolset.
- [ ] **Step 4: Add idempotency and safety tests.** Prove duplicate keys, interrupts, provider failures, unknown effects, no-progress windows, and second-window exhaustion all fall back without duplicate work.
- [ ] **Step 5: Run the focused seam suite and existing finalizer tests.**

Run:
```bash
PYTHONPATH=. pytest -q tests/run_agent/test_iteration_budget_auto_continue.py tests/agent/test_turn_finalizer_iteration_limit_exit.py tests/run_agent/test_verification_continuation_budget.py
```

Expected: all focused tests pass and legacy summary behavior remains green.

---

## Task 4: CLI/gateway persistence and boundary integration

**Files:**
- Modify: `gateway/run.py` only for shared config/receipt propagation if required by the seam
- Modify: `hermes_state.py` only if existing display metadata cannot persist the receipt
- Test: `tests/gateway/test_iteration_auto_continue.py`
- Test: `tests/hermes_cli/test_iteration_auto_continue_cli.py`

**Interfaces:**
- Consumes: the production `run_conversation()` result and existing SessionDB/display-kind projection.
- Produces: identical policy behavior through CLI and gateway main-turn entry points, with no changes to `/goal` or delegation.

- [ ] **Step 1: Write seam RED tests** for CLI and gateway entry points, persisted `display_kind`, user-turn accounting, and secret-free receipt fields.
- [ ] **Step 2: Run the tests and confirm the current source does not propagate the new receipt/continuation path.
- [ ] **Step 3: Wire the narrowest existing persistence and gateway projection path.** Do not add a new database table unless the existing metadata contract cannot represent the required fields.
- [ ] **Step 4: Run gateway/CLI focused suites and negative scope tests** proving `/goal` and delegation budgets are unchanged.

Run:
```bash
PYTHONPATH=. pytest -q tests/gateway/test_iteration_auto_continue.py tests/hermes_cli/test_iteration_auto_continue_cli.py tests/gateway/test_goal_max_turns_config.py tests/tools/test_delegate.py
```

Expected: all focused tests pass.

---

## Task 5: Candidate gates, patch representation, and live-readiness receipt

**Files:**
- Create: `patches/upstream-hermes/2026-09-05_bounded-main-turn-auto-continue.patch`
- Modify: `docs/reconciliation/hermes-runtime-source-lock.json`
- Modify: `docs/reconciliation/v3-source-coverage-manifest.json`
- Test/receipt: existing `scripts/guard/*` and contract runner outputs

- [ ] Run `git diff --check` and `git diff --cached --check` on the exact intended path set.
- [ ] Run the focused feature suites and the relevant full gateway/agent regression suites.
- [ ] Run `bash scripts/guard/secret-scan.sh --tree` and preserve only PASS/clean path output.
- [ ] Run `python3 scripts/guard/pii-review.py --diff origin/main..HEAD` and resolve every candidate-path result.
- [ ] Recompute and validate the manifest against the final candidate SHA.
- [ ] Run `bash scripts/run_contract_tests.sh` and preserve the final exit code.
- [ ] Confirm the runtime dependency patch applies cleanly to the pinned upstream base in an isolated validation copy; do not apply it to the live framework checkout.
- [ ] Stop for the Phase 3/owner release gate before any runtime config change, deployment, gateway restart, push, PR, or merge.

---

## Checkpoints

### Checkpoint A — after Task 2

- Config policy tests pass.
- Progress policy tests pass.
- No production loop wiring exists yet.

### Checkpoint B — after Task 4

- Real `run_conversation()` seam and CLI/gateway entry points pass.
- Duplicate/approval/unknown-effect/no-progress negative tests pass.
- `/goal` and delegation remain unchanged.

### Checkpoint C — before Phase 3 approval

- Exact candidate path set and patch overlay are reproducible.
- Focused/full relevant tests and all security/manifest/contract gates have fresh outputs.
- No live runtime mutation has occurred.

## Rollback

Before implementation, preserve the current candidate source and patch manifests. Each task is independently revertible. If a candidate byte change invalidates earlier test evidence, rerun affected gates from the new exact SHA. Runtime rollback is an exact-manifest restoration of the pre-release framework files and active configuration; no wildcard or reset-based rollback is permitted.

## Known Limitations

- Progress detection is conservative and cannot prove semantic task completion; it only decides whether a continuation is safe to attempt.
- A run can still stop on provider errors, inactivity/resource limits, context pressure, user interruption, or the two-window bound.
- Natural production proof of the continuation path requires a future real heavy task; controlled tests cannot be labeled NATURAL-PROVEN.
