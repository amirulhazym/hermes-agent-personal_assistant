# Git/live byte-forensics and evidence-packaging reference

Use this reference for a user-approved read-only reconciliation between controlled source, historical commits, candidate trees, live files, and a running gateway.

## 1. Evidence contract

Start by writing a scope block into the evidence root:

- owner boundary timestamp and timezone;
- repositories/paths allowed;
- Git commands allowed;
- explicit prohibitions: tests/imports/probes, service actions, network/Drive/OAuth, decryption, checkout/reset/stash/commit/merge/rebase, trigger/state/config writes;
- exact missingness labels.

Use a new unique directory such as `/tmp/<task>-YYYYMMDD-HHMMSS/`. Only temporary evidence writes belong there. Never use the live runtime tree as the output directory.

## 2. Repository and commit ledger

For every requested token and every local repository:

```text
git -C <repo> rev-parse --verify '<token>^{commit}'
git -C <repo> show -s --format='%H%n%ct%n%ci%n%P%n%s%n%an <%ae>%n%cn <%ce>' <full-sha>
git -C <repo> branch --contains <full-sha> --format='%(refname:short)'
git -C <repo> tag --contains <full-sha>
```

Record:

```json
{
  "token": "...",
  "repository": "/absolute/path",
  "full_sha": "40 chars",
  "commit_timestamp": "timezone-bearing value",
  "parents": ["..."],
  "subject": "...",
  "is_merge_commit": false,
  "branches_containing": [],
  "tags_containing": [],
  "candidate_head": "...",
  "main_head": "...",
  "reachable_from_candidate_head": true,
  "reachable_from_main": false
}
```

For a prefix token, report the resolved full SHA. If no local repository resolves it, emit `COMMIT OBJECT NOT AVAILABLE LOCALLY`; never fetch to fill the gap.

## 3. Exact object extraction

For each commit/path pair:

1. Check `git cat-file -e '<sha>:<path>'`.
2. Resolve the Git blob with `git rev-parse '<sha>:<path>'`.
3. Extract exact bytes with `git show '<sha>:<path>' > <evidence-root>/commit-files/<unambiguous-name>`.
4. Run `sha256sum` and read-only `stat` on the extracted file.
5. Record original commit/path, blob SHA, file SHA-256, size, and attachment path.

Recommended manifest fields:

```text
commit_token
full_commit
repository
original_path
status
blob_sha
sha256
size
attachment
```

Never replace an absent historical path with a current live or candidate file. The absence row must say `PATH ABSENT IN THIS COMMIT`.

## 4. Pre-boundary path history

For each path, use the owner boundary exactly, including timezone:

```text
git -C <repo> log --all --before='<YYYY-MM-DD HH:MM:SS +08:00>' -1 --format='%H' -- <path>
```

Then record the selected commit's timestamp, parent, subject, blob SHA, extracted file SHA-256, and:

```text
git -C <repo> merge-base --is-ancestor <last-pre-boundary> <controlled-release>
```

Use two independent fields:

- `PRE-10 SOURCE EXISTS — DEPLOYMENT NOT PROVEN`
- `GATE-6 DEPLOYMENT PROVEN`

A path can be byte-identical to a controlled release while its deployment remains unproven. A path can have a pre-boundary commit that is not an ancestor of the named release; do not silently upgrade it to the release baseline.

## 5. Merge and reconciliation ledger

For merge `<merge>`:

```text
git -C <repo> diff-tree -m --name-status <merge>
git -C <repo> diff --full-index --no-ext-diff <parent-1> <merge> -- <path>
git -C <repo> diff --full-index --no-ext-diff <parent-2> <merge> -- <path>
```

Compare the result blob with each parent:

- result equals parent 1 → `BYTE-IDENTICAL TO PARENT 1`;
- result equals parent 2 → `BYTE-IDENTICAL TO PARENT 2`;
- result equals both → `BYTE-IDENTICAL TO BOTH PARENTS`;
- result differs from both → `DIFFERS FROM BOTH PARENTS — PROVENANCE UNKNOWN`.

Only claim conflict-marker evidence if the retained result bytes contain `<<<<<<<`, `=======`, or `>>>>>>>`. No marker is not proof of no manual resolution.

For a follow-up restoration commit, record exact before/after blobs and search local Git history for prior commits with the exact after blob. State `exact blob match proven; copy/restore command not retained` unless the command itself is present.

## 6. Live and candidate collection

Candidate:

- extract from the exact candidate commit object;
- hash the current candidate working tree separately;
- compare but do not conflate the two;
- label candidate bytes `CANDIDATE ONLY — NOT DEPLOYED` until deployment evidence exists.

Live:

```text
sha256sum <exact-live-paths>
stat -c '%n|size=%s|mtime=%y|owner=%U:%G|mode=%a|mode_symbolic=%A' <exact-live-paths>
```

Copy only into the evidence root, preserving the original path in the manifest. Do not execute, import, compile, or probe the copied code.

A running process started before a file's current mtime is evidence that the current disk bytes are not proven to be in memory. It is not enough to inspect the disk file and write `ACTIVE IN GATEWAY MEMORY PROVEN`.

## 7. Matrix fields

Use one row per requested path. Recommended columns:

- Gate/predeploy copy;
- controlled release;
- last pre-boundary Git version;
- each merge parent;
- merge result;
- follow-up result;
- later commits;
- candidate commit;
- candidate working tree;
- current live disk;
- active gateway memory.

Each byte-bearing cell should include:

```text
sha256=<12+ hex> | <evidence label> | byte-identical-to=<peer cells>
```

Keep the active-memory column separate: it may contain `ACTIVE IN GATEWAY MEMORY NOT PROVEN` without a byte hash.

## 8. Package layout

For large delivery, use numbered archives:

```text
package-1-commit-repository-metadata.tar.gz
package-2-historical-and-release-objects.tar.gz
package-3-reconciliation-diffs-and-parents.tar.gz
package-4-current-live-and-candidate.tar.gz
package-5-artifacts-matrix-and-findings.tar.gz
```

Include:

- raw command outputs;
- exact extracted files;
- parent files and patches;
- live/candidate manifests;
- missingness ledger;
- matrix and findings;
- package index with member counts;
- package SHA-256 manifest.

Before delivery, re-list each archive and re-hash it. Re-read candidate/main refs and run read-only staged/unstaged diff checks. If any artifact is unavailable, attach no substitute and state `MISSING / NOT RETAINED / NOT ATTACHED`.

## 9. Causality language

Use:

- `DIRECTLY CHANGED BY COMMIT — PROVEN` for a path-level diff;
- `DEPLOYED FROM COMMIT — PROVEN` only when retained deployment evidence matches the exact bytes;
- `OUT-OF-BAND WRITER UNKNOWN` when the live writer/copy command is absent;
- `CORRELATION ONLY` when timing/identity does not prove causation;
- `MERGE/REBASE CAUSATION NOT PROVEN` when a source change is the only evidence;
- `ACTIVE IN GATEWAY MEMORY NOT PROVEN` when process memory/load identity is unavailable.

Do not use “approved”, “deployed”, “working”, “active”, or “recovered” as synonyms for a newer timestamp, Git membership, candidate presence, or live-disk presence.
