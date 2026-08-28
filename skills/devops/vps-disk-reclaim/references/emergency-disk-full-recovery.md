# Emergency 100%-full-disk recovery

Use this reference when the root filesystem is full enough that Hermes/tooling cannot create its own temporary sandbox. This is a disk-recovery procedure, not permission to resume the original build, test, deployment, or source task.

## Observed failure pattern

A tool may fail before running the requested code with an error shaped like:

```text
OSError: [Errno 28] No space left on device: '/tmp/<tool-sandbox>'
```

Treat any interrupted/orphaned command as **unknown execution state**. Inspect the filesystem before retrying. In the 2026-08-19 incident, a candidate reconstruction path existed but lacked a required source file; it was invalid and was not trusted.

A direct recursive-delete command may also be rejected by an execution safety wrapper before execution. Preserve that failure; do not assume partial deletion. If the owner has already approved the exact path set, run the same preprinted list through a direct shell filesystem operation and verify every path afterward. Never widen the list to compensate.

## Bounded procedure

### 1. Direct-terminal bootstrap

Until there is meaningful free space, use direct shell commands only:

```bash
df -B1 -P /
for p in /tmp/<candidate-1> /tmp/<candidate-2>; do
  [ -e "$p" ] && du -x -B1 -s "$p"
done
```

Do not use an operation that needs a new agent sandbox, large temporary archive, reconstruction output, or pytest cache. Capture the raw `ENOSPC` output in the report.

### 2. Pre-delete evidence

For each proposed path, record:

- exact absolute path;
- allocated size from `du -x -B1 -s`;
- file/directory/symlink type;
- why it is disposable (`INCOMPLETE`, `SUPERSEDED`, `RESULT-CAPTURED`, or `INVALID`);
- result-log or manifest path retained elsewhere, when applicable.

Check process references without relying on an application-level claim:

```bash
for proc in /proc/[0-9]*; do
  readlink "$proc/cwd" "$proc/root" 2>/dev/null
  for fd in "$proc"/fd/*; do readlink "$fd" 2>/dev/null; done
 done
```

Match the returned paths against the exact deletion set. Also run `git worktree list --porcelain` from every relevant canonical parent repository. A standalone disposable clone is not automatically a registered worktree, but its test result must be captured before deletion.

### 3. Never-delete set

Keep all of the following unless a separate explicit owner decision changes scope:

- canonical application repository and any registered worktree;
- live `~/.hermes` source, runtime state, config, credentials, or service/session data;
- persistent incident evidence and its SQLite backup/copy;
- `SOUL.md` and other owner-designated preservation files;
- the current valid remediated candidate tree;
- the true C0 baseline and C3 comparison baseline needed for attribution/rollback;
- any path referenced/open by a running process;
- the only copy of a patch, raw test output, rollback manifest, or source-like evidence.

Only delete exact temporary artifacts already classified as disposable: incomplete reconstruction outputs, superseded test overlays/clones whose result logs are retained, and old pytest temporary directories after the authoritative suite is no longer running.

### 4. Execute and verify

Print the exact deletion list immediately before execution. Afterward:

```bash
df -B1 -P /
for p in <same-exact-list>; do
  [ -e "$p" ] && printf 'STILL_PRESENT %s\n' "$p" || printf 'ABSENT %s\n' "$p"
done
```

`du` is evidence about the target allocation; `df` is the authority for actual reclaimed filesystem space. Report both before/after values. Do not call recovery successful after freeing only a few hundred MB if the next operation needs a clone/reconstruction or large cache.

### 5. Health and persistence boundary

Check, read-only:

- gateway service `active/running` and its PID;
- WhatsApp bridge process and listening port;
- canonical/live Git roots and HEADs;
- protected path existence and sizes.

Do not restart the gateway or bridge during this lane unless separately authorized. Do not perform a live DB probe or test message if the owner prohibited it. In that case report:

```text
Disk prerequisite: PASS
Session persistence end-to-end: UNVERIFIED — no DB/session write was run by instruction
```

A live process plus restored disk headroom proves infrastructure recovery, not that a new session row was persisted.

## Stop rule

Once free space, protection checks, and runtime-health checks are complete, stop the turn. Do not continue the interrupted Gate 2/reconstruction/pytest/rollback task in the same recovery turn. The next turn must re-audit current filesystem/VCS state before resuming; do not trust the interrupted command narrative.
