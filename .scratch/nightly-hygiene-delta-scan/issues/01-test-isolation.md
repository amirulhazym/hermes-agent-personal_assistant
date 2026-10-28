# 01 — Test Isolation for Git Object Writes

**What to build:** Isolate contract and drift test suites so that running tests never writes objects or modifies index timestamps in the live runtime Git repository.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `tests/reconciliation/test_runtime_dependency_drift.py` creates throwaway clones with `--no-hardlinks` and verifies no alternates exist before writing trees.
- [ ] Source Git object store and index before-and-after snapshots match byte-for-byte.
- [ ] `python3 -m pytest -q tests/reconciliation/test_runtime_dependency_drift.py` passes 5/5.
