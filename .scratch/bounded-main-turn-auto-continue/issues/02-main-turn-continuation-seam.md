# 02 — Main-turn continuation seam and idempotent synthetic message

**What to build:** When ticket 01 admits continuation, the actual main `run_conversation()` path appends one bounded state-checking continuation, opens the next 300-iteration window, and resumes the same task without duplicating the continuation.

**Blocked by:** 01 — Main-turn progress policy and bounded continuation

**Status:** ready-for-agent

- [ ] A real conversation seam test proves one eligible budget exhaustion creates exactly one synthetic `display_kind: auto_continue` message and one new window.
- [ ] The continuation retains the original task, instructs the model to inspect current state before repeating work, and does not bypass approval/safety gates.
- [ ] The same turn/window idempotency key cannot append or execute a duplicate continuation.
- [ ] User interrupt, provider failure, unknown effect, and no-progress paths return to the existing summary/fallback behavior.
- [ ] The second permitted continuation is admitted only when its own window independently passes the progress gate; the third exhaustion is terminal for this feature.
