# 04 — Reset drift contract after reconciliation

**What to build:** Recompute the runtime deployment manifest from reconciled source and simplify drift classification so the deployed manifest is the single runtime-byte expectation.

**Blocked by:** 03 — Capture intentional live source into SSOT.

**Status:** ready-for-agent

- [ ] Reconciled source and live runtime are proven equivalent for every managed runtime-deploy path before the reference advances.
- [ ] Historical hardcoded known-drift exceptions are removed rather than expanded.
- [ ] Zero drift returns PASS; an injected managed mismatch returns FAIL.
- [ ] Manifest recompute and validation pass at the exact candidate SHA.
- [ ] The deployed reference is not changed before protected source publication and controlled deployment.
