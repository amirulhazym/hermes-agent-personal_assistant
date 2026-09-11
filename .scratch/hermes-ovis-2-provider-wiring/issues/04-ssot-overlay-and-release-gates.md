# 04 — Capture the framework guard as an SSOT overlay

**What to build:** The tested fail-closed profile-routing change is represented as an exact upstream patch overlay with reproducible source, security, manifest, and contract evidence.

**Blocked by:** 01 — Fail closed on stale or unserved profile routing; 02 — Serve `bot_2` as the canonical multiplexed bot profile; 03 — Verify provider wiring under `bot_2` without generation

**Status:** ready-for-agent

- [ ] The patch applies to the pinned runtime base in an isolated candidate and changes only the intended profile-routing seam/tests.
- [ ] The runtime source lock and tree manifest contain the final patch identity and exact changed paths.
- [ ] Focused tests, relevant gateway multiplex tests, secret scan, PII review, diff checks, manifest validation, and contract tests have fresh raw outputs.
- [ ] Candidate, on-disk deployment, active process, and user-visible channel states are reported separately.
- [ ] The work stops at the exact owner release gate; no push, deploy, reload, or release approval is inferred from candidate-green tests.
