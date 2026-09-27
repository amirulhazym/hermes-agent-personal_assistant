# Implementation Plan — Nightly Owner-Gate & Recovery

## Task 1 — Publication authority RED
1. Replace/add timeout test so a clean local-ahead repo stays unpublished after the 30-minute timeout.
2. Assert origin/main unchanged, actions_taken empty, pending terminal/block status owner-required.
3. Add divergence/publication-chain test proving no local merge occurs before owner authorization.
4. Run targeted test and confirm RED on current code.

## Task 2 — Publication authority GREEN
1. Add an explicit owner-required action-chain predicate.
2. Make process_pending(timeout) block before any owner-required chain executes.
3. Preserve process_pending(approve) exact-run behavior.
4. Run targeted tests to GREEN.

## Task 3 — Remove per-run scheduler overlap RED/GREEN
1. Add RED test that run_nightly() with owner-pending or investigation state does not call schedule_timeout.
2. Change new-run persistence to record pending/deadline state without creating a dynamic one-shot job.
3. Keep the permanent 00:25 agent job untouched.
4. Run closure workflow + autofix-context tests.

## Task 4 — Legacy self-cancel regression RED/GREEN
1. Build a legacy pending fixture with timeout_job_id.
2. RED: prove current timeout path cancels/removes its own job before terminal completion.
3. Change timeout cancellation so reject/owner-approve can cancel a future job, but a currently executing timeout does not self-delete.
4. Prove terminal state is persisted and old wrapper execution remains safe.

## Task 5 — Immutable primary provenance RED/GREEN
1. Create primary at 23:55 with scheduler execution binding.
2. Update same run after 00:25.
3. RED: current history timestamp/binding is overwritten.
4. Preserve immutable primary timestamp/date/scheduler binding and write updated_at.
5. Verify old pending formats fail closed or use safe fallback.

## Task 6 — Watchdog resolution/state RED/GREEN
1. RED: 23:55 primary updated at 00:25 must still be found at 01:55.
2. Update finder/evidence helpers to use immutable primary provenance.
3. RED: clean local-ahead currently returns NOT CLEAN.
4. Return CLEAN+UNSYNCED and classify owner-pending as HOLD/OWNER_REQUIRED.
5. Preserve missing/ambiguous/dirty fail-closed behavior.

## Task 7 — Regression and candidate construction
1. Run Nightly targeted reconciliation suites.
2. Run full bash scripts/run_contract_tests.sh.
3. Secret scan, PII review, whitespace/diff check.
4. Recompute/validate v3-source-coverage-manifest.json.
5. Verify only intended Nightly files/tests/manifest changed.
6. Freeze exact candidate SHA and STOP for APPROVE RELEASE full-sha.

## Task 8 — Post-approval release/deploy
1. Protected-main publication + required CI.
2. Snapshot live destinations; verify no prewrite drift.
3. Deploy only changed runtime-deploy Nightly scripts using manifest-controlled atomic writes.
4. Verify deployed hashes; no gateway restart unless runtime loading evidence proves it is required.
5. Preserve rollback receipt.

## Task 9 — Scheduled proof
1. Observe real 23:55 primary execution and scheduler binding.
2. Observe 00:25 permanent autofix agent.
3. Observe 01:55 watchdog locating the exact primary.
4. Report scheduler recovery proven only for behaviors actually exercised live; use deterministic isolated regressions for owner-pending timeout behavior if that night has no pending publication.
