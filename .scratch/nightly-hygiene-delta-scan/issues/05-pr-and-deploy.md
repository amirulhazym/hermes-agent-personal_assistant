# 05 — Protected Main PR Publication & Controlled Deployment

**What to build:** Commit verified candidate changes to local `main`, execute autonomous GitHub PR publication with CI verification, prune redundant branch `feat/hermes-gateway-b1-integrity-20261015`, and deploy the updated script to `~/.hermes/scripts/nightly_git_hygiene.py`.

**Blocked by:** 04 — Test Suite Contract Alignment & 100% Green Verification

**Status:** ready-for-agent

- [ ] Source coverage manifest recomputed and validated.
- [ ] Autonomous PR created, CI checks polled until successful, and squash-merged to `origin/main`.
- [ ] Redundant branch `feat/hermes-gateway-b1-integrity-20261015` deleted locally and remotely.
- [ ] `~/.hermes/scripts/nightly_git_hygiene.py` updated and SHA-256 verified against repository `main`.
- [ ] Live dry-run of nightly hygiene confirms exit code 0 / clean hold report without temporary index errors.
