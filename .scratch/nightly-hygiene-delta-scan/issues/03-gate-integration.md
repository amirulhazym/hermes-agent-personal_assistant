# 03 — Nightly Gate Integration & Temporary Index Replacement

**What to build:** Integrate `candidate_delta_scan.py` into `scripts/nightly_git_hygiene.py`, replacing `_temporary_worktree_index` while preserving separate daily-commit security and PII gates.

**Blocked by:** 02 — NUL-Safe Candidate Delta Scanner Implementation

**Status:** ready-for-agent

- [ ] `run_full_delta_gates()` executes manifest scanning instead of `_temporary_worktree_index`.
- [ ] Regression test verifies that nested unborn repositories and ignored candidate files are scanned without invoking `git add`.
- [ ] `python3 -m pytest -q tests/reconciliation/test_nightly_git_hygiene.py` passes completely.
