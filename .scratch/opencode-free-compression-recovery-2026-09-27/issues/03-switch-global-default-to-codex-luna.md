# 03 — Switch Global Default to Codex GPT-6 Luna

**What to build:** Make `openai-codex / gpt-6-luna` the owner-selected global default in SSOT configuration and later the live config, while preserving existing session overrides.

**Blocked by:** 01 — OpenCode Free chat surface must already fail closed

**Status:** ready-for-agent

- [ ] Add/adjust config-contract tests for `model.provider: openai-codex` and `model.default: gpt-6-luna`.
- [ ] Update `config/config.yaml.template` to the approved default.
- [ ] Assert current live Codex discovery contains `gpt-6-luna`.
- [ ] Assert `gpt-6-luna-900k` is not synthesized when absent from live discovery.
- [ ] Do not mutate stored session model overrides or session rows.
- [ ] Live `~/.hermes/config.yaml` update and gateway reload remain blocked until Phase 3 approval.
