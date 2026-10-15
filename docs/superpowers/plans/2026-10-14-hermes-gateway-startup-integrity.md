# 2026-10-14 Hermes Gateway Startup Integrity — B1 TDD Plan & Receipt

Scope: approved isolated SSOT-only Phase 4. No source commit, push, PR, merge, live changes, scan or restart.

1. Verify source authority: official base `29112bef099274229cadff79cdff7bf7b99c4b77`, original 7-entry lock, baseline manifest (PASS).
2. RED: add B1 tests; startup test failed because integrity-status file was absent, as expected.
3. GREEN: minimal lifecycle change; 24 focused lifecycle tests passed.
4. RED: pending integrity readiness test failed with missing `integrity_verification` check.
5. GREEN: add integrity-only readiness diagnostic; 52 focused tests passed.
6. Generate one minimal upstream overlay and append one hash-pinned lock entry (order 8).
7. Reconstruct with updated lock + write/validate tree manifest: PASS, 10936 files; four modified source paths exactly match isolated candidate.
8. Run focused regression on reconstructed output: 52 passed.
9. Verify patch scope, security hygiene, unchanged original SSOT and unchanged running PID; stop for next owner gate.

Patch: `patches/upstream-hermes/2026-10-14_gateway-startup-integrity-b1.patch`
Patch SHA-256: `4ce08d3a83e1309c6ef2ac258ca9bcf25e1e82222caaa9ba6f96775b83502ebd`
Candidate output: `/tmp/hermes-b1-isolated-D1bx9v/rebuilt-safety`.

Future gates: full security/contract CI and owner-authorized publication, then separately approved controlled live rollout. No runtime results or real cold-start SLO proven.


## 2026-10-15 B1 safety correction (isolated only)
Owner independently reproduced fail-open after failed atomic verification-status write, clean shutdown and subsequent clean startup. Publication is HOLD.
RED: added regression that injects failure only into `gateway-integrity-verification.json`, then clean-restarts. Prior candidate wrongly returned `not_required` (assertion failed).
Minimal GREEN change:
- `mark_exited` carries `prior_integrity_incident_id` across clean shutdown, without carrying `prior_unclean_exit` boolean.
- `record_startup` clean path preserves previous incident reference.
- `readiness` treats absent verification file with incident reference as `degraded/unverified`; stale verified records are rejected even after clean restart.
- No heavy database scan or new background verifier.
Regression covers repeated 3 clean restarts after status write failure, first boot unaffected, pending-record preservation, and old verified record not reused after NEW unclean incident write failure.

GREEN on corrected candidate: 52 focused tests. On final rebuilt candidate: 52 passed. Explicit real SQLite corruption fixtures on temporary DB: 3 passed. Patch apply/reverse PASS; 8-entry source-lock and tree-manifest reconstruction PASS (10936 files).
Patch SHA-256: `4ce08d3a83e1309c6ef2ac258ca9bcf25e1e82222caaa9ba6f96775b83502ebd`.
Tree SHA-256: `303b3377419b80b5cdfb66b4ebcbb8092f7288ea4ee70049a789e2c0ff9a6135`.
Correction-only exact diff: `/tmp/hermes-b1-isolated-D1bx9v/B1-SAFETY-CORRECTION-ONLY.diff` (3 paths: lifecycle ledger, readiness, new tests).
Health monitor audit: local `health_check.py` sends alerts only; `/health/detailed` serializes a degraded state in a regular JSON HTTP response; systemd `Restart=always` responds to process termination, not a degraded JSON field. No direct readiness-degraded -> auto-restart trigger identified in inspected local paths. External consumers remain unknown.
Approval: no Phase 5, commit, push, PR, merge, deployment, restart or production DB scan.


## 2026-10-15 B1 controlled SSOT capture gate reconciliation
Owner authorized isolated branch capture and gates, no publication/deployment. Source-lock append changed authoritative patch-series digest.
Initial full contract suite: 138 passed, 3 failed, all from existing contracts pinning the old 7-entry series/digest:
- `tests/reconciliation/test_hermes_runtime_reconstruction.py`: expected series updated to include the SHA-256-pinned B1 overlay.
- `docs/reconciliation/hermes-runtime-model-refresh-deploy-manifest.json`: synchronize derived `patch_series_digest` only; entries unchanged.
- `docs/reconciliation/hermes-runtime-opencode-free-compression-recovery-deploy-manifest.json`: synchronize derived `patch_series_digest` only; entries unchanged.
No provider model selection or deployment behavior changed. Re-run all 141 contract cases and all source/security gates before local branch commit; further unexpected failures are an owner HOLD.
