# 3-Test Acceptance Criteria

## Staged Testing Plan (from external analysis, confirmed)

### Test 1 — Forced Bootstrap
**Purpose**: Migrate running gateway (still has drain_timeout=180) to new gateway with drain_timeout=0.

**Method**: Phase 1 escalation (bridge-first kill + SIGKILL).

**Acceptance Criteria**:
- Bridge killed first (SIGTERM), verified exit before gateway kill
- Gateway SIGKILL (status=9/KILL in journal)
- systemd restarts at RestartSec=5
- New gateway PID differs from old PID
- New gateway loaded `restart_drain_timeout: 0` (verify via config.yaml and journal)
- Outcome classified: `verified_forced_bootstrap`
- **MUST NOT** be called `clean` or `graceful`

### Test 2 — First Clean SIGTERM Restart
**Purpose**: Validate the graceful restart path with drain_timeout=0.

**Method**: Phase 2 graceful (planned-stop marker + SIGTERM only).

**Acceptance Criteria**:
- One SIGTERM only — no SIGINT, no SIGKILL, no bridge kill
- Gateway exits normally (exit code 0)
- systemd starts a new PID after RestartSec=5
- Total readiness under 30 seconds (from script launch to new gateway serving)
- PID file matches systemd `MainPID`
- Exactly one gateway process
- Exactly one bridge child
- Port 3000 belongs to the new bridge
- Expected hooks loaded (3+)
- Expected adapters loaded (2 — Telegram + WhatsApp)
- Telegram returns to expected state (journal shows connected)
- WhatsApp returns to expected state (journal shows connected)
- Auto-resume completes (interrupted session gets synthetic resume event)
- Transaction ends in `verified_graceful`
- No stale `requested`, `stopping`, or `verifying` state remains

### Test 3 — Second Clean SIGTERM Restart
**Purpose**: Validate the path is repeatable, not a one-off.

**Method**: Phase 2 graceful (same as Test 2).

**Acceptance Criteria**: Same as Test 2.

**Additional**: Verify that Test 2's verified_graceful outcome was properly persisted and the restart-state was clean before Test 3 started.

## Stopping Rules
If ANY criterion in a test fails:
- **Stop immediately**. Do not proceed to the next test.
- Investigate the failure before repeating.
- A failed Test 1 means the bootstrap didn't work — config change may not have persisted.
- A failed Test 2 or 3 means the graceful path has an issue — drain_timeout=0 may not be active.

## What 3 Passing Tests Prove
✅ The root-cause fix (drain_timeout=0) is validated
✅ The forced migration (bootstrap) works
✅ The normal graceful restart path works repeatedly
✅ Transition record and outcome classification function
✅ Verification checklist catches issues

## What 3 Tests Do NOT Prove
❌ Bounded recovery from every future shutdown hang (e.g., adapter disconnect blocks)
❌ Safety under concurrent users (not relevant for single-user setup)
❌ All platform failure scenarios
❌ Long-term 20-run reliability

These are explicitly out of scope for v1.

## Staged Production Rollout
```
Test 1 (Bootstrap) → verify → stop
    ↓
Stability period (5 min) → verify drain=0
    ↓
Test 2 (Graceful) → verify → stop
    ↓
Stability period (5 min)
    ↓
Test 3 (Graceful) → verify → stop
    ↓
INITIAL ACCEPTANCE (3/3)
    ↓
Continue toward 20 cumulative successful restarts over days/weeks
```

20 consecutive restarts in one session is NOT required — that's the target for "proven working" over time, not for initial approval.
