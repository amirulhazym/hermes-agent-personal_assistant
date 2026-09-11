# 03 — Verify provider wiring under `bot_2` without generation

**What to build:** A fresh-process provider receipt proves the `bot_2` resolver, `/model` picker inventory, and zero-token model discovery independently, while external provider failures remain explicitly classified.

**Blocked by:** 02 — Serve `bot_2` as the canonical multiplexed bot profile

**Status:** ready-for-agent

- [ ] The actual resolver under `HERMES_HOME=bot_2` returns concrete definitions for the configured providers that are present in the profile.
- [ ] The actual picker path exposes non-empty provider/model rows for `bot_2`; static config appearance alone is not accepted.
- [ ] The zero-token probe captures HTTP status/model counts per provider without sending a completion request.
- [ ] Antigravity connection refusal and Fiq HTTP 503 are reported as shared/external status; Codex/Copilot HTTP 400 remains unresolved probe/auth-contract status unless separately proven.
- [ ] No inference, credential rotation, OAuth refresh, or “all providers fixed” claim occurs in this ticket.
