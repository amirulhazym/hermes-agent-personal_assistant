# 01 — Fail closed on stale or unserved profile routing

**What to build:** An inbound source that explicitly names a missing/unserved profile is rejected before agent/provider resolution instead of silently falling back to the global/default Hermes home.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] The existing missing-profile regression is RED before implementation: it currently expects global fallback and must be changed to the fail-closed contract.
- [ ] `GatewayRunner` and the secondary-profile message handler reject/drop an explicit profile whose directory or served-profile membership is absent.
- [ ] The rejection path uses secret-free context and does not load default/global provider config, credentials, memory, or persona.
- [ ] A genuinely unrouted source with no explicit profile preserves the existing default-profile behavior.
- [ ] Focused profile-resolution and rejected-route tests pass in an isolated framework candidate.
