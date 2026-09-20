# 06 — Controlled live release and final verification

**What to build:** Publish the fully reconciled source, deploy only the approved monitor/runtime representations that require live synchronization, advance the deployed reference only after proof, and demonstrate final health.

**Blocked by:** 02 — Repair post-push smoke cron boundary; 04 — Reset drift contract after reconciliation; 05 — Preserve intentional Gemini branch without false HOLD.

**Status:** ready-for-agent

- [ ] All required security, PII, manifest, contract, and targeted regression gates pass at the exact candidate SHA.
- [ ] Protected PR flow merges the approved source and local `main` matches `origin/main`.
- [ ] Controlled live synchronization touches only the approved manifest paths and records rollback hashes.
- [ ] Post-push smoke produces fresh receipts with no new user-bus error.
- [ ] Drift monitor reports zero managed mismatches and PASS.
- [ ] Gemini V2 remains retained/unmerged; current health remains free of failed components.
