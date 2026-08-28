# Corrective Closure Plan — Goal 1 + Goal 2

**Status:** PLAN ONLY — no corrective implementation executed
**Baseline source of truth:** `/tmp/claims-verification-report-20260828.md`
**Baseline accepted by owner:** Goal 1 = `PARTIAL / NOT COMPLETE`; Goal 2 = `PARTIAL / NOT COMPLETE`
**Scope lock:** Close only the material `FALSE`, `PARTIAL`, and `NOT PROVEN` items in the accepted verification report. Do not redesign either goal or add unrelated cleanup.

---

## 1. Scope and non-goals

### In scope

- Prove and repair the actual SSOT → deployment-managed runtime path.
- Close the identified live → SSOT source drift with per-path classification.
- Determine the role and safe disposition of the third Git root `/home/ubuntu/.hermes`.
- Repair the invalid nightly schedule and false-PASS logic.
- Implement the approved audit-only/self-improvement proposal flow.
- Add dedicated tests for the nightly script and its HOLD/FAIL behaviour.
- Reconcile the on-disk plan/governance documents with the later approved corrections.
- Run a separate final read-only verifier over every acceptance criterion.

### Explicit non-goals

- No new architecture or replacement goal.
- No blind copy of all live files.
- No deletion/rewrite of `/home/ubuntu/.hermes` before its role and contents are classified.
- No raw secrets, private persona, sessions, databases, or medical state in public Git.
- No automatic push to `origin/main`, force-push, remote branch deletion, or blind rebase.
- No gateway restart merely to make a report look complete. A restart is a separate existing release/runtime gate if active-process proof genuinely requires it.

---

## 2. Report claim → corrective-task map

| Report finding | Status from accepted report | Corrective task(s) |
|---|---|---|
| Runtime still executes from `/home/ubuntu/.hermes/hermes-agent`; SSOT → runtime promotion not proven | `FALSE / NOT PROVEN` | G1.1, G1.5, G1.6 |
| Deploy helper rejects the v3 manifest and the current live checkout does not match the runtime tree manifest | `PROVEN FAILURE` | G1.1 |
| Three differing common script files and 32 live-only script files | `PARTIAL` | G1.2, G1.3, G1.4 |
| Skills/hooks/plugins also have live-only and differing files | `PARTIAL` | G1.2, G1.3, G1.4 |
| Three Git roots exist; `/home/ubuntu/.hermes` has 665 tracked files and 478 status entries | `FALSE` for one-repo state | G1.3, G1.6 |
| `SOUL.md` is absent from personal repo but tracked/modified in `.hermes` root repo | `MISLEADING / PARTIAL` | G1.3, G1.4 |
| Old branch heads/stash objects are in the bundle, but some branch heads are not Git objects in personal repo | `PARTIAL` | G1.2, G1.3 |
| Local personal `main` is six commits ahead; remote `origin/main` is unchanged | `PROVEN LOCAL ONLY` | G1.5, G1.6; existing release gate remains |
| Nightly job exists but stored `schedule` is `{}`; CLI shows `Schedule: ?`, `Next run: ?` | `FALSE / NOT SCHEDULED` | G2.2, G2.6 |
| Nightly receipt reported `PASS` while `Working Tree Clean: False` | `FALSE-PASS DEFECT` | G2.3, G2.5 |
| Secret scan checks staged state only; PII review checks `HEAD~1..HEAD` only | `PARTIAL / INSUFFICIENT COVERAGE` | G2.3, G2.5 |
| Self-improvement beyond Git hygiene is not implemented | `FALSE / NOT IMPLEMENTED` | G2.4, G2.5 |
| No dedicated nightly-script tests were found | `NOT PROVEN` | G2.5 |
| Committed plan still contains old “read-only runtime” wording and unchecked planning state | `PARTIAL / STALE ARTIFACT` | G2.1 |
| Final completion was declared without a separate final criterion-by-criterion VPS verifier | `PROCESS GAP` | G2.7 |

---

## 3. Execution order and gates

The tasks are sequential because they share source ownership, manifests, live paths, and the cron contract. No task is auto-advanced merely because the previous command exited zero.

```text
G1.0 → G1.1 → G1.2 → G1.3 → G1.4 → G1.5 → G1.6
                                      │
                                      └→ G2.1 → G2.2 → G2.3 → G2.4 → G2.5 → G2.6 → G2.7
```

A checkpoint is required after G1.4 before any live apply, and after G2.5 before enabling the recurring scheduler.

---

# Goal 1 — Corrective closure

## G1.0 — Fresh controlled re-baseline

**Purpose**
Recheck the accepted report’s identities at execution time without treating an old report, branch label, or prior SHA as current proof.

**Locations / inputs**

- `/home/ubuntu/hermes-agent-personal_assistant-work`
- `/home/ubuntu/hermes-agent-personal_assistant-work/.worktrees/`
- `/home/ubuntu/.hermes/hermes-agent`
- `/home/ubuntu/.hermes`
- current systemd unit and process metadata
- current direct remote refs (`git ls-remote`, read-only)
- accepted report `/tmp/claims-verification-report-20260828.md`

**Expected outcome**

- A timestamped baseline JSON/Markdown record containing exact Git roots, branches, HEADs, worktrees, remotes, service path, process path, cron row, bundle hash, and current statuses.
- The accepted report remains the historical baseline; any change since then is called out rather than silently merged into it.

**Validation / evidence required**

- `git rev-parse --show-toplevel`, `git status --short --branch`, `git rev-parse HEAD` for every relevant root.
- `git worktree list --porcelain`.
- `git ls-remote` for personal `origin/main` and official upstream `main`.
- `systemctl --user show`, process command/cwd, import paths, and editable-install mapping.
- `hermes cron list` plus raw job object readback.

**Runtime/destructive impact**
None. Read-only inspection only.

**Rollback**
Delete only the temporary evidence directory; no live or Git state rollback is needed.

---

## G1.1 — Diagnose and correct the deployment/reconstruction contract

**Purpose**
Find the exact reason the approved SSOT → runtime helper rejects its inputs, then use the correct existing manifest boundary without bypassing validation.

**Verified starting failure**

```text
Using v3 application coverage manifest:
DEPLOY FAIL: runtime tree manifest base SHA does not match source lock

Using runtime tree manifest against current live checkout:
DEPLOY FAIL: runtime tree path set mismatch
```

**Locations**

- `docs/reconciliation/v3-source-coverage-manifest.json`
- `docs/reconciliation/hermes-runtime-source-lock.json`
- `docs/reconciliation/hermes-runtime-tree-manifest.json`
- `scripts/reconstruct_hermes_runtime.py`
- `scripts/deploy_hermes_runtime.py`
- temporary isolated materialization directory under `/tmp`

**Expected outcome**

- A written contract map distinguishes:
  - application source-coverage manifest (`v3`),
  - authoritative runtime source lock,
  - full materialized runtime-tree manifest,
  - deployment source-tree input.
- The official pinned base plus ordered patch series can be reconstructed into a disposable tree.
- The disposable tree passes the runtime-tree manifest validation.
- Deployment dry-run against that disposable tree returns a clean plan with `writes=0`, `deletes=0`, and `restart=0`.
- If a check still fails, the task remains `HOLD`; no `--force`, `--3way`, wildcard copy, or validation bypass is permitted.

**Validation / evidence required**

- Exact command and complete output from `reconstruct_hermes_runtime.py --validate`.
- Exact per-file/path-set/hash/mode validation result.
- Exact command and output from `deploy_hermes_runtime.py --dry-run` using the correct materialized source tree and runtime manifest.
- A root-cause note explaining why the prior v3-manifest invocation was invalid.

**Runtime/destructive impact**
No live writes. Temporary files only; no service action.

**Rollback**
Remove the disposable materialization directory. Source lock and live runtime remain unchanged.

---

## G1.2 — Build the complete live-to-SSOT source-closure inventory

**Purpose**
Replace broad “scripts reconciled” wording with an exact per-path classification and zero unexplained drift target.

**Required inventory**

- The 3 differing common script files:
  - `guard/pii-review.py`
  - `test_chain_adapter.py`
  - `test_effective_done.py`
- The 32 filtered live-only script paths from the accepted report.
- Differing/live-only paths under `skills/`, `hooks/`, and `plugins/`.
- Source-like paths tracked or modified in the `.hermes` root repository that materially affect Goal 1.
- File mode, symlink/type, byte hash, Git tracking state, and mtime for each candidate path.

**Classification values**

Each path receives exactly one primary disposition:

- `CAPTURE-IN-SSOT`
- `ALREADY-REPRESENTED`
- `RUNTIME/GENERATED/STATE-ONLY`
- `OBSOLETE-DUPLICATE`
- `INTENTIONALLY-EXCLUDED-PRIVATE`
- `OWNER-DECISION`

No path may be omitted solely because it is dormant, unreferenced by the current cron list, or absent from a prior manifest.

**Expected outcome**

- A deduplicated inventory with no unexplained live-only or differing source-like path.
- All ambiguous paths remain preserved and marked `OWNER-DECISION`, not silently dropped.
- Private runtime data is represented only by a safe schema/template/reference where needed; raw state is not copied to public Git.

**Validation / evidence required**

- Inventory file with one row per path and source/live/repository/hash/status fields.
- Exact counts before and after classification.
- `sha256`/mode comparisons for every path selected for capture.
- Secret and PII results over the intended candidate path set, including untracked source-like files.

**Runtime/destructive impact**
Read-only inventory. No live file changes and no medical state writes.

**Rollback**
Delete only temporary inventory output. No source rollback required.

---

## G1.3 — Reconcile historical branch/stash evidence and determine the third Git-root role

**Purpose**
Close the preservation gap without claiming that a bundle automatically equals SSOT incorporation, and determine what `/home/ubuntu/.hermes` actually is before any cleanup.

### Historical branch/stash subtask

Use the already verified bundle:

```text
/home/ubuntu/.hermes/backups/live_branches_and_stashes_20260828.bundle
sha256=5dbe4789576a339f16b3514ef09d92c25ef841f6572ba7160b234de9aea0cba5
```

The two stash refs already have independently recovered object IDs:

```text
stash@{0} = 44d0264481528d81513a741f682c7167e4abb12e
stash@{1} = 12712ce7392801a835fdf3efd9a0cd1dd7818156
```

Use a disposable repository to inspect each old branch head and its unique commit/path set. Compare each against the personal SSOT by exact Git object/path/hash evidence. The personal repo not containing a commit object is not itself proof that the file-level behavior was lost; classify it explicitly as bundle-only, patch-represented, captured, or unresolved.

### `.hermes` root subtask

**Current evidence to explain:**

```text
root=/home/ubuntu/.hermes
branch=hermes-local
HEAD=08cf26ba9488183a969cc821daea735c2990b33e
remotes=(none)
tracked_count=665
status_entries=478
SOUL.md tracked and modified
```

Inspect its creation/history, tracked path families, current source-like modifications, `.git` role, and relationship to `$HERMES_HOME`, the live scripts/skills/config/state, and the separate framework checkout.

**Expected outcome**

- A role statement backed by history and path evidence:
  - `RUNTIME-DATA-DIRECTORY`,
  - `LOCAL-RECOVERY/SNAPSHOT-REPO`,
  - `DEVELOPMENT-REPO`, or
  - `UNRESOLVED`.
- A path-level explanation for the 665 tracked files, the 478 status entries, and why `SOUL.md` is tracked there.
- A disposition recommendation that preserves the physical `$HERMES_HOME` runtime directory but removes its normal development ambiguity.
- No deletion or history rewrite until the owner selects the disposition after seeing this evidence.

**Recommended default for owner review**
Treat `/home/ubuntu/.hermes` as the live runtime-data directory, not a development SSOT; preserve its Git metadata as a recovery artifact until all unique source/private paths are classified and independently backed up. Decommissioning the `.git` metadata is a separate destructive action, not an automatic cleanup step.

**Validation / evidence required**

- Git history and path-family inventory.
- Exact list of source-like paths not represented in personal SSOT.
- Exact `SOUL.md` tracking/provenance result and privacy disposition.
- Bundle/object recovery evidence for all named old refs.
- Owner-facing disposition record before any destructive action.

**Runtime/destructive impact**
Read-only audit. No `.git` deletion, reset, rewrite, or runtime-state movement.

**Rollback**
No rollback required. Preserve all evidence and the bundle.

---

## G1.4 — Capture only approved source-like deltas into an isolated SSOT candidate

**Purpose**
Port the classified source closure into the personal repository without blindly copying runtime state or changing the live service.

**Locations**

- Isolated candidate worktree based on personal `main`.
- Only paths with disposition `CAPTURE-IN-SSOT`.
- Source-coverage and runtime-reconstruction metadata where the selected source affects those manifests.

**Expected outcome**

- Selected live custom source is represented in the SSOT using the repository’s existing representation:
  - sanitized source,
  - template/schema,
  - exact upstream overlay patch,
  - or documented private/recovery reference.
- Ignored operational files such as `med-schedule.json` and `dexa_taper.json` remain private/ignored unless a separate safe representation is explicitly required; byte parity alone is not called Git capture.
- `SOUL.md`, credentials, databases, sessions, and raw medical state are not added to public Git.
- The candidate has one exact SHA and no unexplained source drift in the classified scope.

**Validation / evidence required**

- Candidate `git status --short --branch` and exact HEAD.
- Per-path before/after hashes and modes.
- Candidate path manifest and updated provenance metadata.
- Full intended-path secret/PII scan, not staged-only scan.
- Affected source and dataflow tests in an isolated `HOME`/`HERMES_HOME`.

**Runtime/destructive impact**
Personal candidate files only. No live copy, no config/state change, no service action.

**Rollback**
Revert the local candidate commit(s) or discard the isolated worktree. Do not restore by overwriting live state.

---

## G1.5 — Prove the SSOT → deployment-managed runtime flow

**Purpose**
Demonstrate the complete author → verify → approved deployment/reconstruction → runtime readback chain while keeping active-process proof separate from on-disk proof.

**Pre-deployment path**

1. Author/capture only in the personal SSOT candidate.
2. Run isolated tests and privacy gates.
3. Reconstruct the full runtime tree from the pinned official base plus ordered overlays.
4. Validate the runtime manifest and file modes.
5. Run deployment dry-run against the materialized tree.
6. Record candidate SHA, manifest digest, per-file hashes, and deployment plan.

**Live apply boundary**

An actual apply to `/home/ubuntu/.hermes/hermes-agent` requires the existing exact-SHA release gate:

```text
APPROVE RELEASE <full-40-character-sha>
```

The general corrective-plan approval does not silently bypass this separate runtime/release gate.

**Expected outcome**

- Dry-run proof passes with no live mutation.
- If an owner-approved live apply is later performed, the deployment receipt records:
  - exact release SHA,
  - exact manifest ID/digest,
  - rollback snapshot path,
  - every written file/hash/mode,
  - `restart=0` unless separately approved.
- Post-apply readback proves live-on-disk parity.
- Current service PID/command/cwd remains separately recorded.
- Active-process loading is labelled `PROVEN` only after a controlled reload/restart or equivalent import proof; on-disk parity alone remains `DEPLOYED-ON-DISK / ACTIVE-MEMORY-NOT-PROVEN`.

**Runtime/destructive impact**

- Dry-run: none.
- Live apply: modifies only manifest-declared runtime source files, with a per-path rollback snapshot.
- Restart: not automatic; service interruption is possible only under a separately approved controlled restart/reload.

**Rollback**

Use the deployment helper’s exact rollback snapshot for the applied manifest. Do not use wildcard restore, recursive delete, `git reset --hard`, or blanket overwrite. If preflight/readback fails, stop and restore only the touched manifest paths.

---

## G1.6 — Goal 1 final read-only verification

**Purpose**
Prevent “files/commits exist” from being reported as “Goal 1 complete”.

**Required acceptance checks**

- Personal SSOT is the only normal development workspace by documented rule and actual workflow evidence.
- All relevant physical Git roots/worktrees are enumerated and have an explicit role.
- No unexplained source-like live drift remains in the agreed closure scope.
- The third `.hermes` Git root has an evidence-backed disposition; if it remains, it is clearly governed as non-development runtime/recovery storage.
- Runtime source path, manifest, candidate SHA, deployed-on-disk SHA/hashes, and active-process status are separate and consistent.
- The old branch/stash evidence has a proven recovery destination and no unclassified unique work.
- Personal remote publication status is reported separately; local SSOT is not called durable remote source until remote reachability is proven.

**Validation / evidence required**

A fresh read-only report containing exact outputs for every check. Any material `PARTIAL` or `FALSE` keeps Goal 1 `NOT COMPLETE`.

**Runtime/destructive impact**
None. Read-only final verifier.

**Rollback**
Not applicable.

---

# Goal 2 — Corrective closure

## G2.1 — Reconcile the on-disk plan and governance contract

**Purpose**
Remove contradictions between chat-approved corrections and the committed plan/governance files before changing the automation again.

**Files**

- `docs/superpowers/plans/2026-08-28-single-repo-and-nightly-git-flow.md`
- `AGENTS.md` only where the current wording is contradicted by the verified contract
- relevant source-lock/deployment references

**Required corrections**

- Replace ambiguous “read-only runtime” wording with `deployment-managed / no-direct-development runtime`.
- Document the actual SSOT → materialized runtime input chain.
- Use only `candidate/nightly-YYYYMMDD` for nightly candidate naming.
- Record that the stash refs are explicitly pinned by object ID and independently recovered before deletion.
- Define scheduler states: `REGISTERED`, `SCHEDULED`, and `FIRED`.
- Define `PASS`, `HOLD`, and `FAIL` semantics.
- State that governance/AGENTS/skill/SOP changes are proposal-only until owner review.
- Add the mandatory final read-only criterion verifier and the four required labels: `PROVEN`, `PARTIAL`, `FALSE`, `NOT APPLICABLE`.

**Expected outcome**

The plan, AGENTS policy, script contract, and runtime-manifest references describe the same workflow. No unchecked planning artifact is presented as an execution receipt.

**Validation / evidence required**

- `git diff --check` and Markdown consistency checks.
- A contradiction scan for old terms, old branch naming, invalid manifest references, and missing final-verifier rule.
- Local candidate commit only; no remote push.

**Runtime/destructive impact**
Personal documentation/governance candidate only. No runtime or cron mutation in this task.

**Rollback**
Revert the local documentation commit.

---

## G2.2 — Repair the nightly scheduler configuration while disabled

**Purpose**
Convert the currently registered-but-unscheduled job into a valid Hermes cron job without allowing it to fire before the corrected script and tests pass, and without relying on a hand-written malformed JSON shape.

**Current failure**

```json
"name": "nightly-git-hygiene",
"enabled": true,
"no_agent": true,
"schedule": {}
```

and:

```text
Schedule: ?
Next run: ?
```

**Required sequencing / safety rule**

1. Snapshot the exact current job object before changing it.
2. Pause or disable the existing job through the supported Hermes scheduler interface.
3. Read back and prove `enabled=false` (or the equivalent paused state) before writing the valid recurring schedule.
4. Configure the intended `55 23 * * *` MYT schedule while the job remains disabled.
5. Keep the job disabled through G2.3, G2.4, and G2.5.
6. Enable it only after Checkpoint B passes, as part of G2.6; enabling is not a G2.2 action.

**Expected outcome**

- Job ID remains explicit and unique.
- `no_agent: true` remains set.
- Script path remains the personal SSOT script.
- Workdir remains the personal SSOT workspace.
- Schedule is stored in the Hermes-supported cron representation for `55 23 * * *` MYT.
- During G2.2–G2.5, the raw job object proves `enabled=false`/paused and the job cannot fire.
- After G2.6 enables it, `hermes cron list` shows the exact intended schedule and a concrete next-run timestamp.

**Validation / evidence required**

- Inspect the installed Hermes cron create/update/pause contract first.
- Capture the pre-change job object.
- Pause/disable first and capture raw readback proving the disabled state.
- Apply the schedule update through the supported scheduler interface or its verified schema path while still disabled.
- Read back the raw job object and confirm no execution was created during G2.2–G2.5.
- Run `hermes cron list` while disabled and again after G2.6 enables it; capture both rows.
- Separately verify one scheduler-triggered execution in G2.6 using the job ID, fresh execution metadata, stdout/stderr, receipt timestamp, and delivery record. A successful “run accepted” response alone is insufficient.

**Runtime/destructive impact**
Changes one scheduled-job record and intentionally pauses it during corrective work; no service restart. No nightly message may be delivered before G2.6.

**Rollback**
Snapshot the exact prior job object, then restore that object through the same supported scheduler interface if the update fails. If the job was originally enabled, restore that exact prior state only after the failed corrective attempt is recorded. Do not delete unrelated jobs.

---

## G2.3 — Fix nightly status semantics and security/diff coverage

**Purpose**
Remove the false-PASS path and make the nightly audit inspect the intended daily/uncommitted source delta without weakening security gates.

**Required status contract**

- `PASS`: required checks completed successfully; no dirty/unclassified source-like change; no unresolved divergence/hold. A clean local `main` ahead of `origin/main` is still `PASS` with `release_pending=true`; it is not an automatic push and is not a failure by itself.
- `HOLD`: owner or classification decision is required, including dirty/untracked source-like changes, divergence, unmerged stale unique branches, or ambiguous source disposition. Pending release publication alone is **not** a HOLD; it is represented as `release_pending=true` metadata under `PASS`.
- `FAIL`: an automated safety/quality gate failed or could not execute, including test failure, secret/PII finding, malformed manifest/schedule, command error, or missing required evidence.

**Receipt semantics for a clean local `main` ahead of `origin/main`**

The receipt must represent this state explicitly and consistently:

```json
{
  "status": "PASS",
  "release_pending": true,
  "push_allowed": false,
  "owner_approval_required_for_push": true
}
```

The exact JSON may contain additional evidence fields, but these four meanings must not contradict each other. `release_pending=true` does not authorize a push and does not change the overall status to `HOLD`.

The receipt must never report overall `PASS` while an acceptance-relevant field is false or an unresolved hold exists.

**Required delta coverage**

The implementation must inspect, without staging or committing user work:

- commits created during the relevant MYT day;
- staged changes;
- unstaged tracked changes;
- untracked source-like files;
- the exact candidate path manifest used by the secret/PII scanners.

`--staged` and `HEAD~1..HEAD` may remain as component probes, but they cannot be the only nightly coverage for an uncommitted daily delta.

**Expected outcome**

- The JSON receipt records raw command status/exit evidence, scan scope, test scope, dirty/untracked classification, sync state, branch actions, holds, proposal path, and release metadata.
- Dirty source-like state produces `HOLD`, not `PASS`.
- Security findings block commit/push preparation and produce `FAIL`/security hold without printing matched secret bytes.
- A clean local `main` ahead of remote produces `PASS` plus `release_pending=true`; it never performs a push.
- No auto-commit and no push are introduced.
- Only merged local branches with no unique commits are eligible for local cleanup; unmerged unique branches are retained and reported.

**Validation / evidence required**

- Unit tests plus isolated temporary Git repositories for all status paths.
- Negative tests proving a dirty tree cannot return overall `PASS`.
- A positive test proving clean local-ahead state returns `PASS`, `release_pending=true`, and `push_allowed=false`.
- Scan-scope test proving an untracked candidate file is included.
- Failure-output redaction test proving secret values are not printed.
- Repeated-run/idempotency test proving a clean run does not create uncontrolled changes.

**Runtime/destructive impact**
The script may write its receipt and proposal files and may prune a verified merged local branch. It must not touch live runtime source, runtime state, or remote refs.

**Rollback**
Revert the local SSOT script/test commit. Restore any accidentally removed merged local branch from the exact retained commit SHA; no remote deletion is permitted.

---

## G2.4 — Implement the approved self-improvement proposal flow

**Purpose**
Add the missing positive-learning component while keeping the default nightly execution deterministic and audit-only.

**Daily inputs**

- that day’s Git status/commit/branch/sync evidence;
- that day’s test and secret/PII gate results;
- scheduler execution/errors for this job;
- relevant gateway/tool errors that directly affect the Git/runtime workflow.

Do not ingest raw medical state, private conversations, credentials, or full message bodies merely to find Git lessons.

**Self-improvement behaviour**

1. Normalize repeated errors into a stable pattern key.
2. Require recurrence evidence from at least two distinct audit executions before calling it a recurring workflow issue.
3. Write a bounded proposal only when a structural lesson exists:
   `docs/proposals/nightly-YYYYMMDD.md`.
4. Include the pattern key, dates/execution IDs, exact evidence paths, observed impact, and a proposed change.
5. Do not edit `AGENTS.md`, skills, SOPs, or release policy automatically.
6. Owner review is required before a proposal becomes a governance/source change.
7. If no recurring issue is proven, write no proposal and report `no proposal`.

**Expected outcome**

The nightly flow can identify recurring Git/workflow failures and produce an evidence-backed proposal, but it cannot unilaterally rewrite its own rules.

**Validation / evidence required**

- Synthetic isolated log fixtures for one-off and repeated errors.
- Test that one occurrence produces no proposal.
- Test that two distinct executions produce exactly one deduplicated proposal.
- Test that the proposal contains evidence paths and no secret/private payload.
- Test that AGENTS/skill/SOP files are never modified by the nightly runner.

**Runtime/destructive impact**
Writes a proposal/receipt under the approved local paths. No live service change, no remote Git mutation, no governance mutation.

**Rollback**
Remove/revert only the generated proposal and local script/test commit. Preserve the raw evidence used to create it.

---

## G2.5 — Add dedicated nightly-script tests and scenario coverage

**Purpose**
Make the approved scenario matrix executable instead of relying on one manual run.

**Required test cases**

1. Clean tree + all gates pass → `PASS`.
2. Dirty tracked tree → `HOLD`.
3. Untracked source-like file → `HOLD` and included in scan manifest.
4. Test command failure → `FAIL`, no commit/push.
5. Secret scan failure → `FAIL`/security hold, redacted output.
6. PII scan failure → `FAIL`/security hold, redacted output.
7. Local/remote divergence → `HOLD`, no automatic rebase/merge.
8. Local `main` ahead of remote without divergence → `PASS` with `release_pending=true`, `push_allowed=false`, and no push.
9. Merged local branch → eligible for local-only cleanup after all gates pass.
10. Unmerged stale branch with unique commits → retained and reported.
11. Upstream ahead → reported as update available; no blind merge.
12. Malformed scheduler/manifest state → `FAIL` or `HOLD` with exact reason.
13. Proposal one-off vs recurring behaviour.
14. Dry-run mode performs no branch deletion and no source commit.

**Expected outcome**

The script’s actual implementation and the documented nightly scenarios agree. Every scenario has a stable machine-readable assertion.

**Validation / evidence required**

- Dedicated test file(s) committed in the personal SSOT.
- Fresh isolated test output with exit code and counts.
- No tests use production `HOME`, `HERMES_HOME`, databases, medical state, or live branch refs.
- A test proves the script’s receipt status is internally consistent.

**Runtime/destructive impact**
Test-only temporary repositories and homes. No live mutation.

**Rollback**
Revert only the nightly test/script candidate commit.

---

## G2.6 — Verify scheduler execution and receipt lifecycle

**Purpose**
Separate `REGISTERED`, `SCHEDULED`, and `FIRED` instead of treating a job row as proof that the job runs.

**Expected outcome**

- G2.6 begins only after Checkpoint B passes and is the first task allowed to enable the job.
- `REGISTERED`: exact job ID exists and, after G2.6 enables it, is enabled/no-agent with the intended script/workdir.
- `SCHEDULED`: CLI parses the schedule and shows a concrete next run.
- `FIRED`: a real scheduler execution has fresh metadata, script output/exit status, receipt update, and delivery evidence.
- Empty/no-action output is reported as a silent run, not as failure; script errors are visible as failures.

**Validation / evidence required**

- `hermes cron list` readback.
- One real `hermes cron run <job-id>` execution readback after the corrected script passes.
- Cron execution log/output directory evidence.
- Receipt JSON/Markdown readback with matching timestamp, HEAD, status, gates, and holds.
- A later scheduled-tick observation, if needed to prove the recurring 23:55 trigger rather than only manual firing. Until that exists, recurring-fire status remains `UNVERIFIED`.

**Runtime/destructive impact**
May deliver one owner-facing audit message. No gateway restart; no source deployment.

**Rollback**
Pause/remove only the named nightly job through the supported scheduler interface and restore its pre-change object if required. Do not touch unrelated cron jobs.

---

## G2.7 — Mandatory final read-only criterion verifier

**Purpose**
Apply the process correction required by the owner after the previous overclaim.

**Required output for every approved acceptance criterion**

```text
PROVEN
PARTIAL
FALSE
NOT APPLICABLE
```

**Verifier rules**

- Check the actual final VPS state, not only the candidate repository.
- Check source, Git refs, remote refs, manifests, scheduler, service/process mapping, live-on-disk hashes, and active-process evidence separately.
- Preserve failed, skipped, timeout, malformed, and unavailable results.
- A component PASS cannot upgrade a parent Goal to complete.
- Any material `PARTIAL` or `FALSE` means the Goal remains `NOT COMPLETE`.
- `FIRED` scheduler proof, deployed-on-disk proof, active-memory proof, and channel-delivery proof remain separate.

**Expected outcome**

A final report with one row per Goal 1/Goal 2 acceptance criterion, exact evidence path/command, and one of the four required labels. The report must end with separate verdicts:

```text
Goal 1: COMPLETE only if every material criterion is PROVEN or NOT APPLICABLE
Goal 2: COMPLETE only if every material criterion is PROVEN or NOT APPLICABLE
Release/push/deploy/restart: separate status, never implied by Goal completion
```

**Validation / evidence required**

- Fresh verifier command output and exit state.
- Exact final candidate SHA and personal-remote reachability status.
- Exact runtime/deployment receipt if live apply occurred.
- Exact cron registration/schedule/fire evidence.
- Exact final service/process mapping.

**Runtime/destructive impact**
Read-only only. No commit, push, cron update, deployment, or restart.

**Rollback**
Not applicable.

---

## 4. Checkpoints and stop rules

### Checkpoint A — after G1.4

Do not apply anything to the live runtime until all of these are proven:

- source-closure inventory complete;
- every selected capture path has a disposition;
- materialized runtime tree validates;
- deploy dry-run passes;
- privacy gates pass;
- exact candidate SHA is recorded.

### Checkpoint B — after G2.5

The nightly job must remain paused/disabled from the start of G2.2 through this checkpoint. Do not enable the recurring scheduler until:

- nightly script tests pass;
- dirty state cannot produce `PASS`;
- untracked delta is scanned;
- divergence/test/security scenarios produce the documented statuses;
- proposal generation is isolated and owner-gated.

Only after these conditions pass may G2.6 enable the job and verify its parsed schedule/next run.

### Hard stop conditions

Stop and report, without “helpful” fallback, if any of these occur:

- manifest/path validation still fails;
- source-like path cannot be classified;
- private/secret/PII material would enter public Git;
- `.hermes` root role cannot be determined;
- deployment would overwrite newer live evidence without preservation;
- service/runtime dependency is unclear;
- final verifier returns any material `FALSE` or unresolved `PARTIAL`;
- a scheduler command is accepted but no execution evidence appears.

---

## 5. Owner decisions genuinely required

### Decision D1 — disposition of `/home/ubuntu/.hermes` Git metadata

**Why it matters:** It is a third Git root with tracked `SOUL.md`, 665 tracked files, and 478 current status entries. Its role cannot be inferred safely from the directory name.

**Recommended default:** Keep `/home/ubuntu/.hermes` as the live `$HERMES_HOME` runtime-data directory, govern it as **no-development/recovery storage**, preserve its Git history until every source/private path is classified and backed up, then consider decommissioning only the `.git` metadata under a separate destructive approval.

**Not needed now:** No decision is needed before the read-only G1.3 audit. The decision is needed before `.git` deletion, history rewrite, or source/private data removal.

### Conditional D2 — unresolved unique source paths

Only if G1.2/G1.3 leaves a path genuinely ambiguous after direct inspection, the owner must choose its disposition. No such path should be silently guessed now.

### Existing gates, not new decisions

These were already agreed and are not reopened:

- `candidate/nightly-YYYYMMDD` naming;
- nightly time `23:55 MYT`;
- no automatic push to protected `origin/main`;
- exact-SHA release approval before live apply;
- restart only when genuinely required and separately permitted.

---

## 6. Final plan acceptance condition

This plan is ready for **plan approval only**, not execution. After plan approval, execution must proceed sequentially with evidence shown after each gated task. No Goal may be called complete unless G2.7 produces a fresh final report in which every material acceptance criterion is `PROVEN` or `NOT APPLICABLE`.
