# Read-Only Audit Techniques

Verified 2026-08-06 on the post-reconciliation live VPS audit (9-path manifest compare, nested overlay verify, GitHub capability probe). Every recipe here mutates nothing.

## 1. Verify a patch is applied WITHOUT modifying anything

```bash
# exit 0  => the worktree already contains the patch's changes (cleanly reversible)
git apply --reverse --check <patch>
# exit 0  => the patch applies cleanly (i.e. NOT yet applied)
git apply --check <patch>
```

- When both fail, the patch is applied but diverged. Isolate which files diverge by looping over the patch's file list (from `git apply --stat`) with per-path checks:
  ```bash
  git apply --reverse --check <patch> --include=<path/to/file>   # per file
  ```
- Plain `git apply` (no `--index`) leaves patch-added files as **UNTRACKED** and modifications as ` M` — expected, not drift. New-file reverse-checks fail if the file's content was edited after creation.
- Verify the patch's documented base claim: `git cat-file -t <base_sha>` must be `commit`; compare base vs HEAD to tell whether local commits superseded the patch.
- Byte-compare any recorded patch artifact against main: `git show <release>:<path> | sha256sum` vs `sha256sum <live-copy>`.

## 2. Attribute file changes by mtime clustering

`stat -c '%y %n'` over a group of files: files written in ONE operation share the SAME mtime second. A diverged file whose mtime matches the batch that created the rest of an overlay predates the deployment — never attribute it to the deploy, and never infer timing from branch names or commit messages.

Example that resolved this: 1 of 26 overlay files failed reverse-check; its mtime (31-Jul 12:32:58.560) matched the other 25 files' write batch (12:32:58.55x), while the deploy was 6-Aug 10:40 — therefore pre-existing drift, NOT deploy-introduced.

## 3. Light read-only DB checks (large SQLite)

`PRAGMA quick_check` on a 1.1 GB DB exceeded 180 s and timed out — do NOT run it on big databases. Use instead:

```python
con = sqlite3.connect('file:<path>?mode=ro', uri=True, timeout=3)
con.execute("PRAGMA journal_mode")                      # wal/delete — proves active
con.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%session%'")
# bounded row counts only (wrap in timeout)
```

0-byte `.db` files are strays, not databases — check size before opening.

## 4. Prove what code a running service loads (triple-source, never branch names)

1. Unit file: `ExecStart`, `WorkingDirectory`, `Environment=HERMES_HOME=...`
2. `/proc/<pid>/exe` + `/proc/<pid>/cwd` readlinks
3. Runtime state files that record argv (e.g. `gateway_state.json` → `argv`)

Note: user-level units (`systemctl --user`) are INVISIBLE to plain `systemctl list-units` — check both levels. Parent PID of a process can point at `systemd --user` (PID of the user manager), which is how you detect user-level supervision.

## 5. GitHub write-capability probe (creates NO refs)

```bash
git remote -v | sed -E 's#(https://)[^@/]+@#\1***@#'        # redact embedded creds
git config --get credential.helper; git config --global --get credential.helper
timeout 15 ssh -o BatchMode=yes -T owner@example.invalid          # "Permission denied (publickey)" = no key
which gh && gh auth status
GIT_TERMINAL_PROMPT=0 git push --dry-run origin HEAD:refs/heads/temp/<probe-name>
git ls-remote --heads origin | wc -l                       # must be unchanged afterwards
```

With no credentials, the dry-run fails cleanly at auth ("could not read Username") without hanging and without creating a remote ref. Verify the head count afterwards to prove no probe branch exists.

## 6. Crash-loop / restart forensics

```bash
journalctl --user -u <unit> --since ... --until ... | grep -iE 'exit|failed|main process'
```

- "Main process exited, code=exited, status=1/FAILURE" + `Restart=always` + `StartLimitIntervalSec=0` = crash loop until something external changes.
- Correlate the first STABLE start time with the deploy timestamp — a stable instance starting seconds after the deploy = the deploy was the recovery point (this proved Gate 6's restart resolved the 08:09–10:41 loop).
- Grep the unit journal window BEFORE the failure for the exit cause (bridge poll failures, killed processes).

## 7. Manifest SHA provenance

- Deployment manifests often record SHAs at an OLDER integration commit than the release. Recompute every source SHA at the RELEASE commit (`git show <release>:<path> | sha256sum`) and compare recorded-vs-release-vs-live in ONE table. recorded == release means no source change between manifest and tag (then live-vs-release is the only axis).
- A pre-deploy `snapshot.txt` (EXISTS/ABSENT per path + SHA + mode + owner) plus `rollback.sh` defines the deploy scope and the rollback contract — cite both as provenance.
- Distinguish manifest destinations that are file copies vs `git apply` vs `(reference)` — the reference-type mapping may land in a subdirectory of the named destination; locate the exact live path by SHA search before calling it MISSING.
