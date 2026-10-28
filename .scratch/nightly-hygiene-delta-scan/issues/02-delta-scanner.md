# 02 — NUL-Safe Candidate Delta Scanner Implementation

**What to build:** Build `scripts/guard/candidate_delta_scan.py` and `scripts/guard/whitespace_review.py` direct byte checking to scan tracked, untracked, ignored, and nested repository files without invoking `git add` or building a temporary index.

**Blocked by:** 01 — Test Isolation for Git Object Writes

**Status:** ready-for-agent

- [ ] `candidate_delta_scan.py` implements NUL-safe path discovery and fail-closed no-follow directory traversal.
- [ ] Direct whitespace checks evaluate file bytes against the exact allowlist without checkout mutations.
- [ ] All 17 unit and acceptance tests in `tests/guard/test_candidate_delta_scan.py` pass.
