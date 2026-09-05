# 01 — Main-turn progress policy and bounded continuation

**What to build:** A configured main-agent turn can decide, from objective tool/mutation evidence, whether a 300-iteration window may continue once, without changing `/goal` or subagent behavior.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] The real config loader exposes the opt-in continuation block and the active profile can represent `max_turns: 300` plus `max_auto_continues: 2` without changing the live profile yet.
- [ ] A policy decision distinguishes eligible progress from repeated/no-op, blocked, unknown-effect, interrupted, approval-pending, and provider-failure windows.
- [ ] The policy emits a structured decision receipt containing the turn ID, window index, budget values, progress kinds, and idempotency key without secrets or raw tool payloads.
- [ ] Focused RED-GREEN tests cover enabled, disabled, malformed, progress, no-progress, and safety-denied cases.
