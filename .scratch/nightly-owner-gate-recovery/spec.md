# Nightly Owner-Gate & Recovery Repair

## Problem Statement
The Nightly Git workflow currently violates the owner-gated publication constitution and loses reliable scheduler provenance in failure/recovery paths.

Fresh evidence on 2026-09-26 proves:
1. test_deadline_timeout_executes_without_chat_continuation explicitly expects no-response timeout to push main, contradicting AGENTS.md section 7 Push Gate.
2. 23:55 creates a per-run one-shot timeout job while the permanent 00:25 nightly-autofix-30m job also runs, creating overlapping remediation ownership.
3. process_pending() marks a timeout plan executing then unconditionally calls _cancel_timeout_job(timeout_job_id). On 2026-09-26 the running one-shot job deleted itself, its fire-claim heartbeat lost ownership about 60 seconds later, and the state was stranded at executing until the 00:25 agent repaired it.
4. Same-run remediation rewrites the history receipt with a later timestamp and drops scheduler_execution; the 01:55 watchdog searches by the mutable timestamp and therefore reported the real 23:55 primary as MISSING.
5. The watchdog labels a clean but ahead/behind repository as NOT CLEAN, conflating worktree cleanliness with remote synchronization.

## Solution
Make the permanent scheduled chain authoritative:
23:55 audit -> 00:25 agent safe remediation -> 01:55 watchdog verification.

New 23:55 runs do not create per-run one-shot timeout jobs. The persisted pending record remains the deterministic owner/safe-remediation state contract.

Publication actions (push_main, push_merged_main, and any chain containing them) are OWNER-REQUIRED. decision=timeout must fail closed before executing any action in such a chain. Only explicit decision=approve with the exact run ID may enter a publication chain.

For backward compatibility, decision=timeout must never cancel/delete its own historical one-shot timeout job before terminal state is persisted.

Primary provenance is immutable. Initial 23:55 receipt identity (primary timestamp/date and scheduler execution binding) is retained across later same-run updates; later writes use a distinct updated_at field. Watchdog primary discovery uses immutable primary provenance with legacy fallback.

Watchdog keeps the existing 01:55 schedule, no-agent mode, and verification role, but reports repository state accurately:
- CLEAN+SYNCED
- CLEAN+UNSYNCED
- DIRTY
- UNKNOWN
Owner-gated unpublished clean state is HOLD/OWNER_REQUIRED, not a false dirty claim and never auto-published.

## User Stories
1. As the owner, I want protected origin/main publication to require my explicit approval so that silence can never authorize a push.
2. As the owner, I want exactly one scheduled autonomous remediation layer at 00:25 so that concurrent timeout workers cannot race each other.
3. As the owner, I want Nightly pending state to reach a terminal/blocked state even when a worker dies so that stale executing records do not persist silently.
4. As the owner, I want the 01:55 watchdog to retain the exact 23:55 scheduler identity after remediation updates so that a real primary cannot become MISSING.
5. As the owner, I want clean-but-unsynced Git state reported separately from dirty work so that Nightly status is accurate.

## Implementation Decisions
- Source-first changes only in /home/ubuntu/hermes-agent-personal_assistant-work.
- Primary production scope: scripts/nightly_git_hygiene.py and scripts/nightly_git_closure_watchdog.py.
- Tests primarily in tests/reconciliation/test_nightly_closure_workflow.py and tests/reconciliation/test_nightly_watchdog_and_resilience.py; add narrower tests only if needed.
- Do not change generic cron/scheduler.py unless RED tests prove the Nightly-only design cannot satisfy acceptance criteria. If generic scheduler change becomes necessary, STOP and return to owner gate before widening scope.
- New runs do not call _schedule_timeout_job; legacy helper/wrapper may remain for backward-compatible handling and historical reconstruction unless removal is separately justified.
- Exact owner approval remains represented by process_pending(decision=approve, exact run_id).
- Any timeout path containing push_main or push_merged_main is blocked before executing the first action.
- Safe local actions may remain executable by timeout/watchdog recovery only if they are individually fail-closed and do not include an owner-required publication chain.
- Same-run receipt updates retain primary timestamp and scheduler binding; updated_at records later mutation time.
- 01:55 watchdog schedule and mode remain unchanged.
- Current blocked historical pending state is evidence only; no migration/mutation of it is required for source correctness.
- Deployment, after a later exact release approval, is manifest/hash/rollback controlled and limited to changed runtime-deploy Nightly scripts.

## Testing Decisions
RED-first regressions must prove:
- no-response timeout cannot change origin/main;
- a publication chain cannot partially mutate local Git before being blocked;
- explicit owner approval still performs the approved deterministic publication path in isolated repo fixtures;
- new run_nightly() does not schedule a per-run timeout job;
- legacy timeout execution does not self-delete before terminal persistence;
- interruption/crash after executing is recoverable/fail-closed;
- later same-run updates preserve original primary timestamp and scheduler execution ID;
- watchdog at 01:55 finds the primary after a 00:25 update;
- missing/ambiguous scheduler evidence remains fail-closed;
- clean+ahead is reported CLEAN+UNSYNCED and HOLD when owner publication is pending;
- dirty working tree remains DIRTY/blocked;
- existing PASS and explicit REJECT flows remain correct.

Run targeted suites, then full scripts/run_contract_tests.sh, guards, manifest recompute/validate, live/source hash preflight, selective deployment dry-run, and post-deploy read-back.

## Out of Scope
- Model provider behavior and Antigravity model-refresh code.
- Generic Hermes cron scheduler changes unless explicitly re-gated.
- Changing 23:55 / 00:25 / 01:55 schedules.
- Automatic protected publication.
- Credentials, account settings, unrelated cron jobs, Gemini work, or gateway architecture changes.
