# Hermes Monitor & Runtime Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:executing-plans` task-by-task. The owner requires a hard stop after each T: verify → commit/push/protected flow → report evidence → wait for explicit approval of the next T.

**Goal:** Restore accurate Hermes monitoring and SSOT/runtime reconciliation without changing unrelated system behavior.

**Architecture:** Keep the existing SSOT/live split. Repair the cron-to-user-systemd boundary for smoke monitoring, capture intentional live custom source back into the SSOT, then rebuild the deployed manifest/reference contract. Nightly branch handling gets one exact owner-approved retained-branch exception while unknown stale unique branches keep the existing HOLD safety behavior.

**Tech Stack:** Python 3.11, Bash, pytest, Git, GitHub protected PR flow, system cron, systemd user service, Hermes reconciliation manifest.

## Global Constraints

- Work only in the personal SSOT or an owner-approved worktree attached to it.
- Do not directly develop inside the framework runtime.
- Do not alter medical/private mutable state.
- Do not merge, delete, or activate `feat/gemini-antigravity-v2-agentic-depth`.
- Do not delete its linked worktree.
- Do not change the five-minute post-push cron cadence.
- Do not advance the deployed runtime reference until source, manifest, protected publication, controlled deployment, and read-back are proven.
- Do not include work from a later T in an earlier T commit or PR.
- After every T, stop and wait for owner approval.

---

## T01 — Durable `/xcute` execution foundation

**Files:**
- Create: `.scratch/hermes-monitor-runtime-reconciliation/spec.md`
- Create: six ticket files under `.scratch/hermes-monitor-runtime-reconciliation/issues/`
- Create: `docs/superpowers/plans/2026-09-21-hermes-monitor-runtime-reconciliation.md`

**Interfaces:**
- Consumes: owner-approved T01–T06 scope and fresh read-only evidence.
- Produces: durable spec/tickets/plan consumed by T02–T06.

- [ ] **Step 1: Create the owner-approved isolated worktree from exact `origin/main`.**

Run:
```bash
git worktree add -b fix/hermes-monitor-runtime-reconciliation-20260921-t01 \
  /home/ubuntu/worktrees/hermes-monitor-runtime-reconciliation-t01 origin/main
```
Expected: new worktree HEAD equals `origin/main`; primary `main` remains clean.

- [ ] **Step 2: Materialize spec, six tickets, and this plan.**

Expected: only planning artifacts appear in `git status`; no script/runtime/config/manifest/product file changes.

- [ ] **Step 3: Self-review artifacts.**

Run:
```bash
grep -RInE 'T[B]D|T[O]DO|implement[[:space:]]+later|fill[[:space:]]+in[[:space:]]+details' \
  .scratch/hermes-monitor-runtime-reconciliation \
  docs/superpowers/plans/2026-09-21-hermes-monitor-runtime-reconciliation.md
git diff --check
git status --short
```
Expected: placeholder scan empty; whitespace check exits 0; path set is planning-only.

- [ ] **Step 4: Stage and run planning-diff security gates.**

Run:
```bash
git add .scratch/hermes-monitor-runtime-reconciliation \
  docs/superpowers/plans/2026-09-21-hermes-monitor-runtime-reconciliation.md
bash scripts/guard/secret-scan.sh --staged
python3 scripts/guard/pii-review.py --diff HEAD
git diff --cached --check
```
Expected: every command exits 0.

- [ ] **Step 5: Commit only T01.**

Commit message:
```text
docs(xcute): establish monitor reconciliation execution plan

T01: materialize the approved Hermes monitor/runtime reconciliation
specification, tracer-bullet tickets, and task-by-task protected execution
plan. This commit changes planning artifacts only; no runtime, monitor,
scheduler, manifest, or product behavior is modified.
```

- [ ] **Step 6: Push and complete protected PR flow.**

Expected: PR contains only T01 planning artifacts; required checks pass; squash merge succeeds; publication branch is removed; local `main` and `origin/main` are synchronized.

---
## T02 — Repair post-push smoke cron boundary

**Files:**
- Modify: `scripts/monitor/post_push_smoke.sh`
- Modify/Create: focused reconciliation test under `tests/reconciliation/` for cron-like user-bus behavior.
- Controlled live sync after protected publication: `~/.hermes/scripts/post_push_smoke.sh`.

**Interfaces:**
- Consumes: system-cron environment and existing `hermes-gateway.service`.
- Produces: fresh smoke receipts without relying on an interactive login environment.

- [ ] **Step 1: Write a RED regression test** that runs the service-probe seam in a sanitized environment and proves the current user-bus lookup fails.
- [ ] **Step 2: Run the focused test and capture the RED evidence.** Expected current failure contains `Failed to connect to bus` or equivalent non-zero user-service probe.
- [ ] **Step 3: Implement the minimal boundary fix.** The script must derive/export:
```bash
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"
```
Service probes must fail into receipt/report logic rather than terminate before receipt generation.
- [ ] **Step 4: Prove GREEN** in isolated and cron-like environments: active gateway and PID resolve; isolated JSON/Markdown receipts are generated.
- [ ] **Step 5: Run targeted regression + guards, commit/push/protected merge, then exact live sync with pre-change rollback bytes.**
- [ ] **Step 6: Observe a real five-minute cron tick.** Receipt timestamp must advance and the smoke log must gain zero new `Failed to connect to bus` lines.

---

## T03 — Capture intentional live source into SSOT

**Files:**
- Modify only the freshly re-derived live-different subset under `plugins/lightclawbot/`.
- Modify only the freshly re-derived live-different subset under `skills/devops/whatsapp-bridge-maintenance/` and `skills/research/medication-safety-research/`.
- Do not modify already aligned paths.

**Interfaces:**
- Consumes: exact live bytes plus current source-closure ledger classification.
- Produces: privacy-safe durable source matching intentional live custom source.

- [ ] **Step 1: Re-derive the live-vs-current-main difference set by SHA-256.** The expected count is evidence, not a hardcoded requirement; any changed count must be explained before writing.
- [ ] **Step 2: Capture exact pre-copy hashes and copy only the currently different live source files into the isolated candidate.**
- [ ] **Step 3: Review the resulting diff for secrets, PII, private mutable data, generated artifacts, and accidental runtime-only values.** Any ambiguous path blocks capture until classified.
- [ ] **Step 4: Run secret/PII guards plus relevant Lightclaw and skill checks.**
- [ ] **Step 5: Verify every captured source hash equals its corresponding live source hash and prove the pre-aligned path set stayed unchanged.**
- [ ] **Step 6: Commit/push/protected merge T03 only.** No live runtime overwrite is permitted in this slice.

---

## T04 — Reset drift contract after reconciliation

**Files:**
- Modify: `scripts/monitor/drift_check.sh`
- Modify mirrored canonical script only where repository convention requires it: `scripts/drift_check.sh`
- Modify: `docs/reconciliation/v3-source-coverage-manifest.json`
- Modify/Create: drift regression tests under `tests/reconciliation/`

**Interfaces:**
- Consumes: reconciled SSOT source from T03.
- Produces: deterministic deployed-manifest drift verdict.

- [ ] **Step 1: Write RED tests** for zero-drift PASS and managed mismatch FAIL without historical exception lists.
- [ ] **Step 2: Remove the hardcoded known-drift classification** from the candidate rather than expanding it.
- [ ] **Step 3: Recompute the manifest against the exact candidate HEAD and validate it.**
- [ ] **Step 4: Prove reconciled source/live managed path equivalence** before reference advancement is allowed.
- [ ] **Step 5: Run drift regression, reconciliation suite, guards, manifest validation, and contract tests.**
- [ ] **Step 6: Commit/push/protected merge T04 source.** Do not advance the live deployed reference before controlled deployment.

---

## T05 — Preserve intentional Gemini branch without false HOLD

**Files:**
- Modify: `scripts/nightly_git_hygiene.py`
- Modify: `tests/reconciliation/test_nightly_git_hygiene.py`
- Modify: `tests/reconciliation/test_nightly_closure_workflow.py`
- Delete local ref only after proof: `xcute/pre-closure-614ab`

**Interfaces:**
- Consumes: exact owner-approved retained branch identity.
- Produces: informational retention for that branch while preserving HOLD for unknown stale unique branches.

- [ ] **Step 1: Write RED tests** using the exact retained Gemini branch name and a separate unknown stale unique branch.
- [ ] **Step 2: Add a narrow retained-branch classification.** Do not add a wildcard family exemption.
- [ ] **Step 3: Prove Gemini branch/worktree tip and cleanliness are unchanged.**
- [ ] **Step 4: Re-run `git cherry main xcute/pre-closure-614ab`.** Require patch-equivalent output before local branch deletion.
- [ ] **Step 5: Run nightly targeted regression and guards.**
- [ ] **Step 6: Commit/push/protected merge T05 and verify nightly preview:** approved retained branch produces no HOLD; unknown stale unique branch still produces HOLD.

---
## T06 — Controlled live release and final verification

**Files/state:**
- Synchronize only approved runtime-deploy monitor/source paths from the merged SSOT manifest.
- Update the live deployed-runtime reference only after exact deployed bytes are proven.
- Preserve rollback snapshots/hashes for every touched live file.

**Interfaces:**
- Consumes: protected merged T02–T05 source.
- Produces: accurate live smoke/drift/nightly monitoring and a new proven deployed reference.

- [ ] **Step 1: Run final pre-deploy manifest dry-run and exact write-set review.**
- [ ] **Step 2: Capture rollback bytes/hashes for only the approved live write set.**
- [ ] **Step 3: Deploy exact manifest paths.** No wildcard copy and no unrelated deletion.
- [ ] **Step 4: Verify on-disk hashes equal the merged SSOT manifest.**
- [ ] **Step 5: Advance deployed reference to the exact merged/deployed source SHA only after parity proof.**
- [ ] **Step 6: Run live post-push smoke, drift check, nightly preview, health read-back, and final repository synchronization checks.**

Expected final evidence:
```text
main == origin/main
post-push receipt timestamp fresh
new user-bus errors = 0
drift_total = 0
drift status = PASS
Gemini V2 branch/worktree retained and unmerged
xcute/pre-closure-614ab local ref absent
health consecutive_fails = 0
failed_components = []
```

---
## Owner Sequence Gate

Even where tickets are technically independent, execution order is owner-locked:

```text
T01 → report/prove → owner approves T02
T02 → report/prove → owner approves T03
T03 → report/prove → owner approves T04
T04 → report/prove → owner approves T05
T05 → report/prove → owner approves T06
T06 → final closure
```

No automatic continuation across a T boundary.

## Rollback Boundary

- T01 rollback is Git-only: revert the planning commit if required; it has no live-system effect.
- T02 and T06 live writes require byte-for-byte pre-change backups and post-write hash verification before success is claimed.
- T03 is source capture only; no live write is allowed.
- T04 does not advance the live deployed reference until controlled deployment proves parity.
- T05 never deletes the retained Gemini branch/worktree; only the separately proven patch-equivalent local pre-closure ref is eligible for deletion.

## Completion Rule

A T is complete only when its own acceptance criteria, tests/guards, Git publication state, and fresh read-back evidence all pass. A completed T does not authorize the next T; explicit owner approval is required.
