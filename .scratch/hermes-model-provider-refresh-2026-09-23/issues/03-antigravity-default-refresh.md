# 03 — Refresh Antigravity fallback default

**What to build:** A source-represented Antigravity plugin change that makes Gemini 3.8 Flash the fallback/default without replacing its live entitlement catalog.

**Blocked by:** 01 — Lock provider catalog contracts.

**Status:** ready-for-agent after owner approval

- [ ] Change plugin fallback/default from `gemini-3.7-flash` to `gemini-3.8-flash`.
- [ ] Preserve the current live logical catalog and wire-route mappings.
- [ ] Keep `antigravity-preview-09-2026` out of the model picker because it is a managed-agent ID, not this bridge's model ID.
- [ ] Represent the change in SSOT patch/reconstruction evidence before deployment.
- [ ] Keep the live plugin checkout untouched until the deployment gate.
