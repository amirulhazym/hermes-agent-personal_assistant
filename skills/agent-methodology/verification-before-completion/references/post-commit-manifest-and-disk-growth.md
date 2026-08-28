# Post-Commit Manifest and Disk-Growth Evidence Recipe

Use for local source-closure candidates and sudden disk-use changes.

## Candidate post-commit gate

A worktree/provenance hash check can pass before commit while a Git-object validator cannot yet validate newly staged paths. The correct sequence is:

```text
worktree intended-path hashes
→ staged diff check
→ secret/privacy gates
→ bounded isolated tests
→ one approved local commit
→ strict validator against final commit SHA
→ report final SHA only
```

For a source-coverage manifest:

- `runtime-deploy` rows require a safe destination under the approved runtime root;
- `source-only` rows require `destination: null`;
- source hashes must be computed from the exact final commit object, not only from the worktree;
- if a row fails after commit, downgrade to `PARTIAL/BLOCKED`, fix the exact row within scope, amend or create a new SHA, and rerun the affected gates;
- an amended SHA supersedes the earlier SHA.

Useful evidence fields:

```text
candidate branch
final commit SHA
branch ahead/behind state
staged file count and insertions
staged diff-check exit/result
manifest parsed/validated counts
secret/privacy result
bounded test counts + isolated residual replay
push/deploy/live status
```

## Disk-growth probe

Read-only baseline:

```bash
date --iso-8601=seconds
df --block-size=1 -P /
du -x -B1 -d 1 /tmp
du -x -B1 -d 1 "$HOME"
stat -c '%n size=%s mtime=%y' suspected/files
lsof -nP -- suspected/file
```

For SQLite, use `file:<path>?mode=ro&immutable=1` and query metadata/counts only. Do not read private message bodies to explain occupancy. Sample size twice or more; report observed byte delta, not an invented rate. If `dbstat` or a detailed size scan times out, label per-table allocation unknown.

Separate:

- active growth: file size changes while an owner process has it open;
- static accumulation: old overlays, virtualenvs, node modules, Git objects, backups, snapshots, and caches;
- deletion evidence: exact path, process/dependency check, retained evidence, and post-delete `df`/health check.

An absent path without deletion logs is a discrepancy/data gap, not proof that the current agent deleted it. A lower disk percentage is not equivalent to source-closure or release success.
