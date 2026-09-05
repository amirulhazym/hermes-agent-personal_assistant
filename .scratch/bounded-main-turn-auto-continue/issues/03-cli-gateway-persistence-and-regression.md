# 03 — CLI/gateway persistence, receipts, and regression coverage

**What to build:** The bounded continuation behavior is wired through both main CLI and gateway entry points, persisted with the existing synthetic-message metadata path, and verified without changing `/goal` or delegation budgets.

**Blocked by:** 02 — Main-turn continuation seam and idempotent synthetic message

**Status:** ready-for-agent

- [ ] CLI and gateway main-turn paths use the same continuation policy and receipt fields.
- [ ] Persisted continuation metadata identifies the original turn, window, count, decision, and idempotency key; synthetic rows do not count as real user turns.
- [ ] Logs expose eligible/denied/exhausted decisions with bounded, secret-free fields.
- [ ] Existing max-iteration summary behavior remains unchanged when the feature is disabled or denied.
- [ ] Focused gateway/CLI regression suites, current resolver tests, and contract/security/manifest gates pass.
- [ ] `/goal` and delegation tests prove their existing budgets and behavior remain unchanged.
