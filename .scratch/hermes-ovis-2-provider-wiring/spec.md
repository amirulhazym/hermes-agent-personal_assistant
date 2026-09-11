# `hermes_ovis_2_bot` Provider Wiring and Profile Safety

**Canonical spec:** `docs/superpowers/specs/2026-09-11-hermes-ovis-2-provider-wiring.md`

**Locked decisions:**

- Canonical profile: `bot_2`.
- Runtime: one default multiplex gateway; no standalone `bot_2` gateway.
- Verification: zero-token resolver/picker/model-list checks only; no paid generation.
- Source behavior: explicit missing/unserved profiles fail closed; they never fall back to global/default provider configuration.

**User-visible outcome:** `@hermes_ovis_2_bot` is served under `bot_2`, its provider configuration is the effective profile configuration, and stale `ovis2` state cannot silently route a turn through the default provider path.

**Acceptance boundary:** provider registration, resolver, picker inventory, and zero-token model discovery are separate checks. Antigravity connection refusal and Fiq HTTP 503 are recorded as external/shared failures; they are not reclassified as profile-wiring failures. Gateway reload and Telegram channel E2E remain separate post-approval gates.

**Tracer bullets:**

1. Reject stale/missing profile sources instead of global fallback.
2. Serve `bot_2` from the default multiplex gateway and retire the duplicate standalone owner.
3. Verify `bot_2` provider resolver/picker/model lists without generation.
4. Capture the framework change as an exact SSOT patch and run release gates.
