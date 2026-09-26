# 01 — Enforce owner-gated publication and remove per-run timeout scheduling

Blocked by: none

Vertical slice:
- Add RED tests proving timeout/no-response cannot publish or partially execute a publication chain.
- Add RED test proving new 23:55 runs do not create per-run timeout jobs.
- Minimally change Nightly action gating/scheduling.
- Preserve explicit owner approve/reject behavior.
- Run closure-workflow targeted tests.

Acceptance:
- exact owner approve path still works in isolated fixtures;
- timeout publication produces HOLD/OWNER_REQUIRED with actions_taken empty;
- no new one-shot timeout job is scheduled by run_nightly().
