---
name: hermes-release-deploy
description: Exact-SHA, manifest-driven promotion and deployment after one explicit owner release approval.
---

# Hermes Release & Deploy

This procedure is forbidden until the owner provides the exact approval:
`APPROVE RELEASE <full-sha>`. Candidate construction alone does not authorize
promotion, deployment, restart or channel verification messages.

## 1. Distinguish the hashes

Keep these fields separate:

- `base_main_sha`: verified source base;
- `candidate_sha`: tested Git commit to approve;
- `payload_hash`: optional hash of a generated manifest/package payload;
- per-file `source_hash`: Git-object content hash/hash algorithm as documented;
- `deployed_hash`: observed live destination hash after deployment.

A payload hash is not a candidate SHA and must not be used as one.

## 2. Validate the complete manifest

Every intentionally source-managed destination in the release must have an
explicit manifest row. Validate source existence at `candidate_sha`, source
hash, explicit safe destination under `/home/ubuntu/.hermes`, mode/ownership,
and no wildcard/recursive/delete action. Reject secret, database, session,
private-memory, log and credential destinations.

Before overwrite, compare the live destination against the manifest and check
for newer live customization. Preserve readable newer state/diffs before any
write. Never silently overwrite a newer live source-like file.

A changed live hash is not automatically safe to overwrite. Use mtime only as a
triage signal; content/hash provenance and owner intent remain authoritative. If
a live file is newer than the candidate, stop before deployment, capture that
exact live file into a new candidate, regenerate its manifest hash/payload hash,
rerun the release gates, and obtain approval for the new exact candidate SHA.
Do not silently reuse approval for a superseded SHA.

## 2.5 Repository-aware guard working-directory invariant

Before running any candidate validator or guard that shells out to `git`, explicitly set its working directory to the candidate worktree and prove it with `git rev-parse --show-toplevel`. This applies to manifest validators, secret scanners, PII diff screens, and similar scripts.

A `not a Git worktree` error or `release SHA is not a commit` from a shell launched outside the candidate repository is a **harness/CWD failure**, not candidate evidence. Record that failed invocation, then rerun the identical guard from the correct candidate worktree before classifying the gate. Never downgrade a candidate from an out-of-worktree false failure, and never silently omit the failed attempt.

## 3. Controlled deployment

Create and verify a mode-700 rollback snapshot (metadata mode 600) of every existing runtime destination before writing.
existing runtime destination before writing. Record pre-deploy SHA-256, mode,
owner, apparent bytes and allocated bytes. Recheck every live destination
against the preflight snapshot immediately before the first write; abort before
any write if a destination changed during the preflight window.

Stage each file atomically in the destination filesystem, preserve the existing
mode for overwrites, use the candidate Git mode for new files, and deploy only
explicit `runtime-deploy` manifest rows. Keep `source-only` rows in Git only.
On any mid-deploy error, roll back from the verified snapshot and report rollback
status separately. Never delete overlays/backups as an implicit part of release.

## 4. CI failure diagnosis and candidate mutation

A remote CI failure is a release blocker even when local gates pass. Query the
remote check-run and job-step state, then reproduce the exact event range
(`before..head`) locally. If the remote failure is caused by an opaque workflow
range/environment issue, make the smallest workflow diagnostic fix, update any
manifest source/payload hashes affected by that workflow change, create a new
candidate SHA, rerun all local gates, push fast-forward only, and wait for the
new remote run. Do not call the previous SHA released.

## 5. Verify and finalize

Verify every deployed hash, rollback-snapshot hash, exact remote `main` SHA,
manifest validation, CI check-run conclusion, gateway service/PID, and isolated
smoke tests. Record candidate/payload/deployed hashes distinctly.

Separate these verdicts explicitly:

- `ON-DISK-DEPLOYED`: destination hashes match the candidate;
- `PROCESS-LOADED`: the running process was restarted/reloaded and is known to
  use the new files;
- `CHANNEL-SMOKE-PROVEN`: controlled post-deploy delivery succeeded;
- `RELEASE-COMPLETE`: only when all required acceptance gates are proven.

An active service plus configured Telegram/WhatsApp proves neither process
reload nor channel delivery. Historical send errors require a fresh controlled
smoke test; do not infer channel health from configuration status. If the
active gateway session must not be restarted, leave runtime activation as
`PENDING` instead of claiming full completion.

Temporary branches/artifacts are cleaned only under the approved post-release
flow; never force-push or delete preservation evidence.

## Session-specific evidence pattern

For the detailed remote-CI forensic sequence and rollback/deployment evidence
layout, see `references/remote-ci-and-live-deploy-verification.md`.
