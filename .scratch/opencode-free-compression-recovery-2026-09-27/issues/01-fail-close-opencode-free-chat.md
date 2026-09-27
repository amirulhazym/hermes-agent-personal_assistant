# 01 — Fail Closed OpenCode Free Chat Surface

**What to build:** Make `opencode-free` unavailable to Hermes chat selection while the provider's external-client restriction remains, without touching OpenCode Go.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Add RED tests proving shared picker discovery excludes `opencode-free`.
- [ ] Add RED tests proving typed selections via `opencode-free`, `free`, and known free model IDs are rejected.
- [ ] Implement the smallest provider/catalog/model-switch policy needed to satisfy those tests.
- [ ] Preserve existing `opencode-zen` fail-closed behavior and `opencode-go` behavior.
- [ ] Do not spoof OpenCode identity or headers.
- [ ] Re-run targeted picker/provider tests and confirm GREEN.
