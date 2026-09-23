# 04 — Integrate, deploy, and verify shared /model behavior

**What to build:** Deterministic SSOT reconstruction/deployment plus Telegram and WhatsApp verification for the refreshed four-provider scope.

**Blocked by:** 02 — Core provider refresh; 03 — Antigravity default refresh.

**Status:** pre-release integration verified; live deployment pending exact-SHA owner release approval.

- [x] Generate/update exact upstream and Antigravity patch artifacts and their hashes/locks.
- [x] Reconstruct the combined candidate runtime and Antigravity dependency candidate.
- [x] Run targeted four-provider tests plus shared /model gateway tests.
- [x] Verify candidate picker inventory/contracts for openai-codex, deepseek, opencode-zen, and antigravity.
- [x] Verify Telegram interactive and WhatsApp text-fallback paths derive from the same authenticated provider catalog.
- [x] Fix the integration gap where WhatsApp fallback still surfaced an empty OpenCode Zen row.
- [ ] Publish/promote the final exact candidate to protected origin/main under the owner release gate.
- [ ] Preserve rollback bytes and dry-run/execute the supported live deployment procedure.
- [ ] Clear affected provider-model cache only through the approved deployment procedure.
- [ ] Restart/reload only the required gateway process.
- [ ] Run bounded post-deploy live provider and Telegram/WhatsApp channel smoke tests without selecting paid Zen models.

Pre-release integration evidence: ../evidence/task6-integration-receipt.md
