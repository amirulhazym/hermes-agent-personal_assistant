# Remote CI and live-deploy verification reference

Use this reference when an exact-SHA release has both a public Git remote and a
running Hermes gateway. It records a reusable evidence pattern, not permission
to deploy.

## Preflight evidence

1. Verify the candidate worktree is clean and its full SHA is the expected
   approved SHA.
2. Verify remote `main` read-only with:
   `git ls-remote <remote> refs/heads/main`.
3. Parse the manifest and classify rows into `source-only` and
   `runtime-deploy`. For every source row, read the blob at the candidate SHA
   and verify the declared SHA-256. For every runtime row, hash the live
   destination and classify `MATCH`, `DIFF`, or `ABSENT`.
4. Treat mtime only as a triage signal. If a differing live file has an mtime
   after the candidate commit, stop before writing and capture the live bytes
   into a new candidate. A one-line newer skill/config change is still a real
   source delta.
5. Recheck live hashes immediately before the first write. This closes the
   race between preflight and deployment.

## Rollback snapshot

Create a directory outside the runtime with mode `0700`; preserve every
existing runtime destination, not only files that differ. Write metadata with
mode `0600` containing destination, relative snapshot path, pre-deploy SHA-256,
mode, owner, apparent bytes and allocated bytes. Hash-verify every copied
snapshot file before writing live files. Check exact-file open handles where
practical, but do not mistake `lsof` absence for proof that a process will
reload the file.

## Atomic deployment

Deploy only explicit `runtime-deploy` rows. Stage each file in the destination
filesystem, fsync it, preserve the existing mode for overwrites, use the Git
mode for new files, then `os.replace` into place. If any write or post-write
hash check fails, roll back every touched path from the verified snapshot and
report rollback status separately. Never combine deployment with cleanup of
backups, overlays, caches or logs.

## Remote CI forensic loop

When GitHub reports a failed check:

- query `/commits/<sha>/check-runs`;
- query `/actions/jobs/<job-id>` for step-level conclusions;
- query `/check-runs/<job-id>/annotations` for actionable annotations;
- query public push events to confirm the actual `before` and `head` SHAs;
- reproduce the exact `before..head` range locally.

A local pass does not erase a remote failure. If the failure is caused by an
opaque workflow range, make a narrow diagnostic fix that prints the range and
checks both commits with `git cat-file -e`, then run the guard. Any workflow
change must also update its manifest source hash and payload hash before a new
commit is validated. Push only fast-forward, wait for the new remote run, and
use the new SHA in all final evidence.

## Completion matrix

Do not collapse these into one PASS:

| Gate | Evidence required |
|---|---|
| Remote promotion | `git ls-remote` equals final candidate SHA |
| Source closure | manifest validator passes at that exact SHA |
| CI | remote check-run completed successfully; inspect all required steps |
| On-disk deploy | every runtime destination hash equals candidate blob |
| Rollback | snapshot metadata and all snapshot hashes verify |
| Process reload | service restart/reload observed; PID/start time or equivalent proves it |
| Channel smoke | controlled post-deploy Telegram/WhatsApp delivery evidence |

A running/configured service proves only service/configuration state. It does
not prove process reload or channel delivery. Historical timeout, flood-control,
`send_path_degraded`, or bridge-disconnect entries require a fresh controlled
smoke test before calling channel health proven. If restart is unsafe during an
active owner session, report `ON-DISK-DEPLOYED` and leave process/channel gates
`PENDING`.
