# 04 — Release, deploy, and prove the scheduled chain

Blocked by: 01-owner-gated-timeout, 02-terminal-state-and-primary-provenance, 03-watchdog-resolution-and-state-semantics

Vertical slice:
- Full contract/security/manifest gates.
- Freeze exact candidate SHA and stop for exact owner release approval.
- After approval only: protected-main publication, CI, rollback snapshot, selective Nightly-script deployment, hash read-back.
- Observe a real 23:55 -> 00:25 -> 01:55 cycle.

Acceptance:
- no unapproved public push;
- runtime script hashes match approved manifest;
- scheduled primary is scheduler-bound and found by watchdog;
- future owner-pending cases are proven by deterministic isolated regression even if the live nightly has no publication pending on the observation night.
