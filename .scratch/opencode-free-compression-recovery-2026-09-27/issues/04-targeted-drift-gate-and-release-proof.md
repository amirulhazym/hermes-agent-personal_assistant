# 04 — Targeted Drift Gate & Release Proof

**What to build:** Add a targeted preflight/read-back gate for this repair's managed runtime paths so SSOT-vs-live byte drift is visible before deployment and verified after deployment.

**Blocked by:** 01, 02, 03

**Status:** ready-for-agent

- [ ] Add a RED synthetic test where a managed target such as `agent/auxiliary_client.py` has the wrong live SHA and the gate fails with that path.
- [ ] Implement the smallest selective parity check using the approved reconstructed candidate/release manifest.
- [ ] Keep repository-only reconstruction tests distinct from live-byte parity checks.
- [ ] Generate the selective deployment manifest for only the approved repair runtime files.
- [ ] Run dry-run preflight, targeted/full regression, secret scan, PII review, and manifest validation.
- [ ] After owner release approval only: deploy exact candidate bytes, update live default config, reload gateway, run `/compress`-equivalent smoke, and read back hashes.
- [ ] Stop again before any publication/deployment step that requires an exact release SHA approval.
