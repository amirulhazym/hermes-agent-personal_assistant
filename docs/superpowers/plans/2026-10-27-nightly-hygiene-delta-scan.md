# Nightly Hygiene Delta Scan Implementation Plan

> Inline execution in `/home/ubuntu/hermes-agent-personal_assistant-work`; no new SSOT repository, branch, or worktree. Disposable temporary clones are allowed only inside tests to isolate Git writes. Preserve existing candidate edits and keep the untracked baseline visible.

**Goal:** Replace temporary-index-dependent hygiene coverage with a fail-closed, read-only manifest scan that includes the approved scratch candidate and never mutates Git objects or live runtime state.

**Architecture:** Collect a deduplicated NUL-safe path manifest from Git plus a no-follow walk of the approved candidate root. Read each file once through no-follow file descriptors, call the existing byte-level scanners and exact whitespace allowlist, then re-enumerate and compare metadata. Keep the contract-test runner blocked until its Git writes are isolated.

**Tech Stack:** Python 3.11, stdlib `os`, `stat`, `hashlib`, Git CLI, pytest/unittest; existing secret, PII, and whitespace rule helpers.

## Global constraints

- Do not delete, initialize, stage, commit, push, or exclude scratch/branch content.
- Do not modify live `~/.hermes` scripts, cron jobs, watchdog behavior, or runtime files.
- No Git temporary index, object write, clone, or worktree creation in the nightly delta gate.
- A missing, failed, unrun, unreadable, unsupported, or changed manifest entry is `FAIL`.
- `HOLD` only follows complete automated PASS where owner review remains.
- No release/deployment claim without exact-SHA approval and live read-back.

---

## Phase 1 — Isolate contract-test Git writes

### Task 1: Add an isolated Git-write helper test

**Files:** Modify `tests/reconciliation/test_runtime_dependency_drift.py`.

- [ ] Add `create_isolated_git_checkout(source, temp_root) -> Path`, using `git clone --no-hardlinks`; assert the disposable checkout has no `.git/objects/info/alternates` file.
- [ ] In a temporary Git fixture, create a previously committed alternate blob, return to the base commit, then stage that blob and run `write-tree` only in the disposable clone. Snapshot source object/index paths, sizes, mtimes, and SHA-256 before/after; assert exact equality.
- [ ] Run `python3 -m pytest -q tests/reconciliation/test_runtime_dependency_drift.py -k isolated_git_write_helper`; expected: the alternate-based implementation fails because Git refreshes metadata on pre-existing objects in its alternate ODB.
- [ ] Update the live-parity test to use `GIT_OPTIONAL_LOCKS=0` for source reads, clone the live repo with `--no-hardlinks`, mirror only tracked dirty paths into that copy, and run `git add`/`write-tree` there. Assert the live source object/index snapshot is unchanged.
- [ ] Run `python3 -m pytest -q tests/reconciliation/test_runtime_dependency_drift.py` under an outer live-storage snapshot; expected: all tests pass and source Git storage is unchanged.

**Rollback:** Revert only the test file changes. Live Antigravity state must remain unchanged.

## Phase 2 — Add direct manifest collection and byte scanning

### Task 2: Add collector contract tests

**Files:** Create `tests/guard/test_candidate_delta_scan.py`.

- [ ] Use temporary directories and a temporary Git repository only. Cover tracked modified/staged paths, ordinary untracked paths, ignored files under the candidate root, nested `.git` metadata exclusion, a sibling file beneath the unborn repo, deleted tracked paths, symlink target text without following it, newline-containing filenames, and duplicate elimination.
- [ ] Add negative cases for Git query failure, unsupported nodes, unreadable/missing paths, and mutation/add/remove/replace during scan. Assert each produces a failed result.
- [ ] Run the new test module before implementation; expected: import/API failures, not setup errors.

### Task 3: Implement manifest collection

**Files:** Create `scripts/guard/candidate_delta_scan.py`.

- [ ] Implement `collect_delta_manifest(repo, candidate_root)` with `git diff --no-renames --name-only -z HEAD --`, `git ls-files --others --exclude-standard -z`, and an `os.scandir`/`os.fwalk` no-follow traversal of the candidate root. Set `GIT_OPTIONAL_LOCKS=0` on Git reads.
- [ ] Preserve path bytes/surrogate escapes; serialize diagnostics with escaped paths. Skip every `.git` path component.
- [ ] Store path, node type, and `lstat` identity/metadata; retain deletion rows without trying to open deleted files.
- [ ] Open parent directories and files through directory descriptors with `O_NOFOLLOW`; read symlinks with `readlink` and scan their target text, never dereferencing them.
- [ ] Rerun collector tests; expected: all collection and fail-closed cases pass, and no temp-index/object-write API is used.

**Rollback:** Remove the new module and tests; existing source edits remain untouched.

### Task 4: Add scanner and allowlist tests

**Files:** Modify `scripts/guard/whitespace_review.py`; test in `tests/guard/test_candidate_delta_scan.py`.

- [ ] Reuse existing secret and PII byte-level `findings(path, data)` functions; do not invoke tracked/staged-only CLI modes as proof of full candidate coverage.
- [ ] Add direct whitespace evaluation from bytes using existing `Issue` and exact path/line/body-hash allowlist semantics for untracked/new files only. Keep tracked whitespace on read-only `git diff --check HEAD` as approved.
- [ ] Assert secret/PII diagnostic output contains path and rule/category only, never the matched bytes.
- [ ] Assert an exact existing allowlist match passes and a changed body hash/new trailing whitespace fails.
- [ ] Run the scanner tests first; expected: tests fail because direct path APIs are not yet available.

### Task 5: Implement `scan_manifest()`

**Files:** Create/modify `scripts/guard/candidate_delta_scan.py`, `scripts/guard/whitespace_review.py`.

- [ ] Read each regular file once and feed the same bytes to secret, PII, and whitespace checks; feed encoded `readlink` bytes for symlinks.
- [ ] Record counts, escaped path/rule findings, and a deterministic digest over sorted path/type/metadata records only. Never record matched secret/PII values.
- [ ] Re-enumerate after scanning and compare path set plus device/inode/mode/size/mtime_ns/ctime_ns; any mismatch/error is `FAIL`.
- [ ] Add a resource test that scans sequentially and does not retain all 175 MB of candidate bytes.
- [ ] Rerun scanner tests; expected: all pass with redacted output and fail-closed error behavior.

## Phase 3 — Integrate the nightly gate

### Task 6: Replace temporary-index path in `run_full_delta_gates`

**Files:** Modify `scripts/nightly_git_hygiene.py` and its tests.

- [ ] Add a regression test that creates an unborn nested repository and proves the direct scanner still inspects its non-`.git` files without running `git add` or building a temporary index.
- [ ] Run the regression test before changing the gate; expected: old temporary-index path fails on the unborn repository.
- [ ] Integrate the direct scanner and preserve separate daily-commit security/PII gates. Remove only the temporary-index-dependent worktree scanning path; do not alter watchdog logic or status meanings.
- [ ] Mark every required scanner result explicitly. Any not-run required gate or incomplete path manifest is `FAIL`; owner review is `HOLD` only after all automated gates pass.
- [ ] Run `python3 -m pytest -q tests/reconciliation/test_nightly_git_hygiene.py tests/guard/test_candidate_delta_scan.py`; expected: all passed.

**Rollback:** Revert the integration hunk only; keep collector tests/module as an independently removable slice.

## Phase 4 — Verification and state-boundary proof

### Task 7: Run bounded candidate gates after test isolation

- [ ] Run `python3 -m pytest -q tests/reconciliation/test_runtime_dependency_drift.py` and the affected hygiene/guard tests; the runtime test itself snapshots source Git storage.
- [ ] Run `bash scripts/run_contract_tests.sh` only after Task 1 proves Git object isolation; expected final marker: `=== contract suite complete ===`, exit code 0.
- [ ] Run `python3 -m py_compile scripts/nightly_git_hygiene.py scripts/guard/candidate_delta_scan.py scripts/guard/whitespace_review.py tests/reconciliation/test_runtime_dependency_drift.py`.
- [ ] Run `git diff --check`, `python3 scripts/guard/secret_scan.py diff HEAD`, `python3 scripts/guard/pii-review.py --diff HEAD`, and direct candidate-manifest scans. Report each scope separately; HEAD-only results do not prove ignored/untracked coverage.
- [ ] Read back git status, current `HEAD`, origin `main`, live hygiene/watchdog hashes, and cron definitions. Acceptance: live scripts, cron definitions, untracked scratch bytes, and branch refs unchanged.

## Phase 5 — Other incident lanes (read-only/candidate only)

### Task 8: Diagnose memory alert flapping

- [ ] Re-read live `health_check.py`, `memory_watch.py`, alert cadence/state, and a bounded `/proc/meminfo`/process sample.
- [ ] Add isolated tests for sustained-low, recovery-threshold, and critical-memory behavior only after deriving thresholds from the existing policy and observed samples.
- [ ] Do not change live thresholds or alerting configuration in this candidate.

### Task 9: Classify branch and runtime drift

- [ ] Review the unique commit on `feat/hermes-gateway-b1-integrity-20261015` against current main; record exact files and provenance.
- [ ] Recompute hashes for each reported source/live drift and map every path to the deployment manifest.
- [ ] Do not merge/delete the branch or deploy runtime changes. Report exact decisions still needed and keep the 01:55 watchdog unchanged.

## Final status gates

- Candidate scanner behavior proven by focused tests; contract suite only reported PASS after Task 1 and final output.
- No live, cron, Git-object, scratch-content, or branch mutation.
- Candidate remains uncommitted and undeployed. Exact-SHA approval is required before publication; deployment/reload/live scheduled execution remain separate future proof.
- Report any failed command or unrun gate explicitly; never aggregate partial evidence into a clean nightly result.
