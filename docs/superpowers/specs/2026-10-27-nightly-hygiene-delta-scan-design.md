# Nightly Hygiene Delta Scan — Design

Date: 2026-10-27
Status: owner-approved design sections; implementation candidate only
Objective: ROOT-CAUSE REPAIR — make nightly quality gates scan the intended worktree delta without constructing a Git temporary index, while keeping the approved scratch candidate in scope and preserving fail-closed reporting.

## Locked scope and non-goals

- Scan tracked changes relative to `HEAD`, ordinary Git-visible untracked files, and every non-`.git` file beneath `.scratch/opencode-free-provider-refresh-20261017`, including ignored files and files beneath its unborn nested repository.
- Preserve all scratch bytes and the divergent branch. Do not initialize repositories, delete/exclude files, stage, commit, push, change cron, or deploy runtime scripts.
- Do not change the 01:55 watchdog schedule, wrapper, no-agent mode, or closure policy.
- Keep the unsafe contract suite blocked until its live Git-object writes are isolated.
- This design does not resolve runtime drift, branch disposition, or memory-alert thresholds; those remain separate read-only/candidate lanes.

## Approaches considered

- **Temporary Git index:** rejected for this failure class; an unborn nested repository makes index population abort before independent gates run, and it creates more Git state than required.
- **Direct path manifest (selected):** NUL-safe Git path discovery plus no-follow enumeration of the approved candidate root; scan bytes directly without staging or object writes. It covers ignored candidate files while preserving the scratch tree.
- **Exclude/archive the scratch candidate:** rejected by owner direction; the tree stays intact and in scope.

## Components and data flow

1. `collect_delta_manifest(repo, candidate_root)` gathers tracked paths with a NUL-delimited `git diff --no-renames --name-only -z HEAD --`, ordinary Git-visible untracked paths with `git ls-files --others --exclude-standard -z`, and a no-follow filesystem walk of the approved candidate root. Git queries set `GIT_OPTIONAL_LOCKS=0`. No `git add`, temporary index, clone, or Git object write is allowed.
2. The collector deduplicates paths and records relative path, node type, and `lstat` identity/metadata. `.git` entries are metadata and excluded. Directory traversal does not follow symlinks. File opens walk directory components with directory descriptors and `O_NOFOLLOW`; regular files are read once, while symlinks are read with `readlink` and scanned as their stored target text. Deleted tracked paths remain represented as deletion rows but require no candidate-byte scan. Unsupported nodes, enumeration errors, or unreadable files fail closed.
3. `scan_manifest()` passes the same bytes for each regular file to existing byte-level secret and PII rule functions; symlinks pass encoded link-target bytes. Tracked whitespace uses read-only `git diff --check HEAD`. New/untracked files, including ignored files beneath the approved root, receive direct byte-level whitespace checks against the current exact path/line/body-hash allowlist.
4. Output contains escaped paths, rule/category, counts, and manifest digest only—never matched secret/PII values. The manifest digest covers sorted path/type/metadata records. A second enumeration and `lstat` comparison after scanning detects added, removed, replaced, or changed paths. Any discrepancy is `FAIL`.
5. The orchestrator reports every required gate. Missing, failed, incomplete, or unrun gates are `FAIL`. `HOLD` is permitted only after all automated gates pass and owner classification/review remains.

## Existing scanner integration constraint

The current secret/PII CLI modes use Git-defined tracked/staged/diff scopes; they cannot prove coverage of ignored files beneath the approved root. The whitespace CLI is staged-only and reads staged blobs. The new scanner must call/factor byte-level rule helpers and an equivalent direct allowlist check; invoking those CLIs alone is insufficient. Existing rule semantics and value-redaction must be preserved.

## Testing and acceptance

- Collector tests cover modified/staged tracked files, ordinary untracked files, ignored files under the candidate root, nested `.git` exclusion with sibling files still included, deleted tracked paths, symlinks without target traversal, NUL/newline-containing names, and duplicate-path elimination.
- Failure tests cover unreadable/missing files, unsupported nodes, Git command errors, scanner exceptions, and path/metadata mutation during scanning. Each must return `FAIL`, not `PASS` or `HOLD`.
- Scanner tests cover secret/PII hits with output assertions that matched values never appear; exact allowlisted whitespace passes while altered/new trailing whitespace fails.
- Integration tests prove the full candidate manifest reaches each scanner and that no temporary Git index, object, staging, or commit is created.
- Contract tests remain blocked until `tests/reconciliation/test_runtime_dependency_drift.py` performs every mutating Git operation in a disposable `git clone --no-hardlinks` with no alternates, and a regression test proves the source object/index metadata and bytes remain unchanged. A temporary object directory with the live object store configured as an alternate is not sufficient: the regression fixture reproduced mtime changes to pre-existing alternate objects even though their hashes were unchanged.
- Run affected tests, the safe contract subset after isolation, Python compile checks, `git diff --check`, and current secret/PII guards. Do not claim a full nightly/cron pass until the actual scheduled path is separately verified after exact-SHA deployment approval.

## Resource and recovery constraints

The inspected approved scratch root contained 10,997 regular files (174,995,002 bytes); the largest was 5,810,842 bytes. Scan sequentially, retain at most one file's bytes plus detector state, and include a resource-bound test. This snapshot is a planning baseline, not a permanent count. Any implementation failure leaves scratch bytes and Git state untouched; rollback is limited to reverting the candidate source/test diff.

## Evidence boundaries

- Candidate source/tests passing proves only SSOT candidate behavior.
- Live scripts remain at their current hashes until separately approved deployment; do not call the scheduled job repaired before runtime read-back and a fresh scheduled execution.
- Branch, runtime drift, watchdog, and memory-alert work remain independent acceptance rows; this change does not close them.