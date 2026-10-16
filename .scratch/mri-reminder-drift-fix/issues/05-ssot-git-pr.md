# 05 — SSOT Git Capture, Tests & PR Publication

**What to build:** Capture the new scripts, test suite, and spec documentation into the personal development SSOT repository, run regression/security checks, and publish via the standard protected PR flow.

**Blocked by:** 01, 02, 03, 04

**Status:** ready-for-agent

- [ ] Write unit test in `tests/scripts/test_mri_reminder.py` covering script output formats and exit codes.
- [ ] Run security scans (`secret-scan.sh`, `pii-review.py`, manifest checks).
- [ ] Push to `feat/mri-reminder-no-agent-drift-fix`, verify CI, squash-merge, and sync local `main`.
