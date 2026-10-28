# Spec — Nightly Git Hygiene Delta Scan & Gate Recovery

## Problem Statement

The automated nightly git hygiene cron job (`nightly-git-hygiene`, scheduled at 23:55 MYT) and its verification watchdog (`nightly-git-closure-watchdog`, scheduled at 01:55 MYT) have failed 11 consecutive nights.
The failure root cause on the live runtime is that `run_full_delta_gates()` builds a temporary Git index (`_temporary_worktree_index`) using `git add` across the entire working tree. When encountering an uncommitted research directory with an unborn nested Git repository (`.scratch/opencode-free-provider-refresh-20261017/v4-patch-preflight-final/`), Git aborts with `error: '...' does not have a commit checked out; fatal: adding files failed`.
Furthermore, candidate fixes in the development workspace have remained uncommitted and undeployed, keeping live runtime scripts failing while redundant branches (`feat/hermes-gateway-b1-integrity-20261015`) trigger recurring hold warnings.

## Solution

1. Replace the temporary-index git-add mechanism in `scripts/nightly_git_hygiene.py` with the direct, NUL-safe, fail-closed `candidate_delta_scan.py` scanner.
2. Isolate test-suite Git writes (`tests/reconciliation/test_runtime_dependency_drift.py`) so testing never mutates live Git storage.
3. Keep the candidate `.scratch` research intact and safely scanned.
4. Cleanly archive or sanitize the two untracked, incomplete test fixtures (`test_opencode_native_free_mock_gateway.py` and `test_reconstruct_nested_output_patch.py`) so the contract test suite passes 100%.
5. Publish all fixes to protected `main` via autonomous GitHub PR, deploy the updated hygiene script to `~/.hermes/scripts/`, and prune the redundant stale branch.

## User Stories

1. As an operator, I want the 23:55 nightly git hygiene job to scan all working tree changes without using `git add` or building a temporary index, so that nested unborn Git repositories in `.scratch` do not crash the audit.
2. As an operator, I want all candidate files (including ignored and untracked files under approved scratch roots) to be scanned for secrets, PII, and trailing whitespace, so that security hygiene is never compromised.
3. As an operator, I want test suites running in development or CI to execute Git mutations exclusively inside isolated throwaway clones without alternates, so that live Git object databases remain immutable.
4. As an operator, I want `scripts/run_contract_tests.sh` to run 100% green without failures from speculative untracked test fixtures, so that CI status checks pass cleanly during PR verification.
5. As an operator, I want the verified hygiene fixes autonomously published to `main` via protected PR flow and deployed with hash verification to `~/.hermes/scripts/nightly_git_hygiene.py`, so that live cron runs succeed automatically without manual SSH patching.
6. As an operator, I want redundant local and remote branches (`feat/hermes-gateway-b1-integrity-20261015`) safely removed once proven identical to `main`, so that nightly reports stay clean without false hold alerts.

## Implementation Decisions

- **Candidate Delta Scanner Architecture:** Direct filesystem traversal using `os.scandir` with `O_NOFOLLOW` and file descriptor walking, combined with NUL-delimited Git path queries (`git diff -z`, `git ls-files -z`).
- **Fail-Closed Gate Contract:** Any unreadable path, unsupported node (fifo, socket), unexpected modification during scan, or scanner crash emits `FAIL`. `HOLD` is reserved solely for automated passes awaiting owner classification.
- **Git Write Isolation:** `tests/reconciliation/test_runtime_dependency_drift.py` clones the live repository into a temporary directory with `--no-hardlinks` and asserts no alternates file exists before staging and writing trees.
- **Controlled Deployment:** Deploy `scripts/nightly_git_hygiene.py` to `~/.hermes/scripts/` and assert exact SHA-256 match.

## Testing Decisions

- Only test external behavior (exit codes, structured JSON status, gate records), not internal private helpers.
- Run targeted pytest suites covering scanner acceptance, nightly hygiene scenarios, and runtime drift isolation.
- Run full contract test suite via `bash scripts/run_contract_tests.sh` and ensure 100% pass before PR creation.

## Out of Scope

- Modifying or deploying memory threshold changes to live `health_check.py` (remains candidate-only in `test_memory_hysteresis.py`).
- Deleting or cleaning `.scratch/opencode-free-provider-refresh-20261017/`.
- Deploying OpenCode free-provider v4 lab features (remains in research/candidate phase).
- Modifying the 01:55 watchdog schedule or logic.
