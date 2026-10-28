# 04 — Test Suite Contract Alignment & 100% Green Verification

**What to build:** Align untracked speculative test fixtures so that `scripts/run_contract_tests.sh` runs cleanly and achieves 100% PASS without regression.

**Blocked by:** 03 — Nightly Gate Integration & Temporary Index Replacement

**Status:** ready-for-agent

- [ ] Untracked speculative test fixtures calling incomplete schema-v2 APIs are safely isolated from the contract test runner.
- [ ] `bash scripts/run_contract_tests.sh` finishes with exit code 0 and outputs `=== contract suite complete ===`.
- [ ] Static checks (`git diff --check`, secret-scan, pii-review) pass without error.
