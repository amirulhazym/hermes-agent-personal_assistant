# 02 — Refresh Codex, DeepSeek, and Zen core provider logic

**What to build:** Current, fail-closed provider catalogs and compatibility behavior in the upstream-Hermes overlay source.

**Blocked by:** 01 — Lock provider catalog contracts.

**Status:** ready-for-agent after owner approval

- [ ] Add GPT-6 Astra/Sol/Luna to Codex offline fallback without overriding live OAuth discovery.
- [ ] Canonicalize DeepSeek V4.1 Flash to `deepseek-flash`; retain currently supported V4 Pro.
- [ ] Update DeepSeek thinking detection/effort handling for `deepseek-flash`.
- [ ] Remove retired DeepSeek Flash aliases from interactive picker paths while preserving safe legacy normalization.
- [ ] Enforce the requested Zen free-only policy at the shared catalog/selection boundary.
- [ ] Do not expose Jev as a normal Hermes chat model.
- [ ] Do not bypass OpenCode's external-client free-tier restriction.
