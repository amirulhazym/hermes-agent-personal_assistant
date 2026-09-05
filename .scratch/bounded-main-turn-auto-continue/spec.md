# Bounded Main-Turn Auto-Continue

## Problem Statement

The active Hermes profile caps the main agent at `agent.max_turns: 100`. Fresh runtime evidence shows repeated `max_iterations_reached(100/100)` exits, including recent heavy development turns. At the cap, Hermes performs its existing summary/grace-call fallback with tools removed; it does not resume the same work automatically.

The existing `auto_continue` implementation is for crash/restart recovery in TUI/Desktop sessions. It is not a max-iteration continuation mechanism. The upstream request for `auto_continue_on_max_iterations` remains a proposal and is not present in the current source.

## Solution

Add an opt-in, bounded, progress-aware continuation policy for **main CLI/gateway conversation turns only**.

The active profile will use a 300-iteration window and permit at most two additional continuation windows. A continuation is admitted only when the current window has objective progress evidence and no safety/approval/interrupt/provider blocker. When the bound is reached or the policy denies continuation, the existing summary/fallback behavior remains authoritative.

The implementation must be represented as a patch overlay in the personal SSOT repository; the deployment-managed framework checkout is not edited directly.

## User Stories

1. As a Hermes user, I want a heavy main-agent task to continue after the first 300 tool-calling iterations when it is demonstrably progressing, so that long coding work is not truncated by an arbitrary cap.
2. As a Hermes user, I want automatic continuation to stop after two additional windows, so that a faulty loop cannot consume unbounded tokens.
3. As a Hermes user, I want continuation denied when the last window is blocked, interrupted, awaiting approval, or has unknown external side effects, so that Hermes does not repeat unsafe work.
4. As a Hermes user, I want the continuation prompt to tell the model to inspect current state before repeating actions, so that already-completed writes are not duplicated.
5. As a Hermes user, I want the continuation to preserve the original task and conversation history, so that the model does not lose context at the window boundary.
6. As a Hermes user, I want automatic continuation to remain limited to ordinary main CLI/gateway turns, so that `/goal` and subagent budgets do not silently acquire a second continuation engine.
7. As a Hermes operator, I want every continuation decision to expose the window number, budget used, progress evidence, deny reason, and idempotency key, so that a later audit can distinguish continuation from a new user turn.
8. As a Hermes operator, I want the existing summary fallback to remain unchanged when the feature is disabled, denied, interrupted, or exhausted, so that the safety baseline remains available.
9. As a Hermes operator, I want the feature default disabled in the general product configuration and explicitly enabled in the active profile, so that enabling it is deliberate rather than a silent global behavior change.
10. As a maintainer, I want config parsing, policy decisions, loop wiring, and gateway/CLI behavior covered by isolated and seam-level tests, so that a helper-only green test cannot be mistaken for an integrated fix.

## Implementation Decisions

### Locked scope and values

- Main window: `300` iterations for the active profile.
- Automatic continuation bound: `2` additional windows.
- Execution surface: main CLI/gateway conversation turns only.
- Explicitly out of the first slice: `/goal` continuation loops and `delegation.max_iterations` subagent budgets.
- General default: feature disabled unless explicitly configured.
- Active-profile activation: explicit configuration after owner release approval; no runtime configuration mutation during Phase 2/3.

### Configuration contract

Add an `agent.auto_continue_on_max_iterations` configuration block with:

- `enabled: bool`;
- `max_auto_continues: positive integer`, normalized to the configured bound;
- a safe continuation prompt with explicit instructions to inspect current state, avoid repeating completed work, stop for blockers/approval/destructive or externally visible actions, and report if unable to continue.

`agent.max_turns` remains the per-window integer budget and is set to `300` for the active profile. The existing unlimited spellings remain supported but are not used for this release.

### Progress contract

A `ProgressSnapshot` is captured for each main-turn window from existing tool execution and mutation/checkpoint evidence. It must distinguish:

- successful non-blocked tool outcomes;
- tool errors, blocked calls, cancellations, timeouts, and unknown-effect outcomes;
- new file-mutation evidence and checkpoint evidence;
- repeated tool-call/result signatures;
- window number and idempotency key.

A continuation is eligible only when the turn ended specifically because the iteration window was exhausted, the turn was not interrupted/failed/awaiting approval, no unknown-effect or unresolved side-effect result is pending, the continuation bound is not exhausted, and the snapshot contains non-repeated forward-progress evidence. A model-written claim of progress alone is not sufficient evidence.

### Continuation state and idempotency

The continuation controller owns a per-main-turn state containing the original turn ID, current window index, continuation count, prior progress fingerprints, and the last decision. Each synthetic continuation receives a deterministic idempotency key derived from the turn ID and window index. The same key must never enqueue or append a second continuation.

The synthetic message is persisted with the existing synthetic/display metadata path as `display_kind: auto_continue`; it is not treated as a real user message for user-turn accounting. The original task text is retained in the continuation metadata/prompt so the model receives a bounded, state-checking instruction rather than a nested continuation note.

### Fallback and safety behavior

- Disabled policy: preserve current summary/grace-call behavior.
- No-progress policy: preserve current summary/grace-call behavior and record the deny reason.
- Bound exhausted: preserve current summary/grace-call behavior and record `max_auto_continues_exhausted`.
- User interrupt, clarification/approval pending, provider/API failure, tool timeout, or unknown side effect: do not auto-continue.
- Auto-continuation must not authorize, bypass, duplicate, or suppress any existing tool approval/safety gate.
- No crash-recovery or restart auto-continue behavior is changed by this feature.

### Observability contract

The decision receipt must include `turn_id`, `window_index`, `budget_used`, `budget_max`, `continuation_count`, `progress_kinds`, `decision`, `deny_reason` when applicable, and `idempotency_key`. It must be available in agent logs and in the persisted synthetic message metadata without recording secrets or full tool payloads.

## Testing Decisions

Tests must exercise observable behavior, not only helper internals.

1. Config tests must prove the 300-window value and bounded continuation block are loaded through the real config path, with disabled/default and malformed-value behavior.
2. Policy tests must cover progress, no-progress, repeated-call, unknown-effect, approval, interrupt, provider failure, and exhausted-bound cases.
3. Loop seam tests must prove a real `run_conversation()` path appends at most one synthetic continuation per idempotency key, preserves the original task, resets the next window correctly, and falls back to summary when denied.
4. Persistence tests must prove synthetic messages retain `display_kind: auto_continue` and metadata while user-turn accounting excludes them.
5. Gateway/CLI integration tests must prove both surfaces receive the same policy and no `/goal` or delegation path is changed.
6. Adversarial tests must prove a successful but repeated no-op tool cycle does not qualify as progress and an unknown-effect tool result blocks continuation.
7. The implementation must use strict RED → GREEN → REFACTOR cycles. The existing targeted resolver tests are baseline evidence only; any candidate byte change requires fresh affected-suite runs.

## Out of Scope

- Implementing or enabling auto-continuation for `/goal` loops.
- Changing subagent/delegation budgets or concurrency.
- Replacing or redesigning the existing crash/restart auto-continue path.
- Making the main iteration budget mathematically infinite.
- Automatic continuation after provider errors, user interrupts, approval prompts, or unknown external side effects.
- New remote services, new API providers, or new persistent database tables unless a tested existing metadata path is insufficient.
- Nightly Git 23:55/01:55 implementation; that checkpoint remains paused until this feature reaches its owner-approved release boundary.

## Further Notes

The current session database records the affected sessions with broad lifecycle reasons such as `session_reset` or `compression`; the budget-exhaustion reason is visible in agent logs but is not currently the session `end_reason`. The feature therefore treats structured continuation metadata and log receipts as an explicit observability requirement rather than inferring lifecycle state from `sessions.end_reason`.
