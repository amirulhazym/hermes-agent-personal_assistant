# Implementation Plan: Deterministic Diet Tracker & ADHD Reporting Engine

**Target Date:** 2026-10-26  
**Status:** Pending Approval (Phase 3 Gate)  
**Spec Reference:** `.scratch/diet-tracker/spec.md`  

---

### Task 1: Write Unit Tests for Diet Report Engine (Red)
- **Path:** `tests/diet/test_diet_report.py`
- **Actions:**
  - Create test cases with mock diet-log JSON fixture.
  - Test calculation of intake, TDEE, net deficit.
  - Test EOD format contains all 5 required section emojis and headers.
  - Test compact format contains 3 lines.
  - Test missing date / empty file resilience.
- **Run:** `pytest tests/diet/test_diet_report.py` (Must fail initially).

---

### Task 2: Implement Deterministic Script (`scripts/diet_report.py`) (Green)
- **Path:** `scripts/diet_report.py`
- **Actions:**
  - Implement robust CLI argument parsing (`--date`, `--mode`, `--path`, `--json`).
  - Implement calculation routines.
  - Implement WhatsApp formatting templates (EOD 5-category + Compact).
- **Run:** `pytest tests/diet/test_diet_report.py` (Must pass 100%).

---

### Task 3: Author Dedicated Skill (`skills/diet-tracker/SKILL.md`)
- **Path:** `skills/diet-tracker/SKILL.md`
- **Actions:**
  - Add YAML frontmatter.
  - Document the 5-Category structure.
  - Add Clinical Dexa Taper Diet Rules (sodium flushing, potassium, protein targets).
  - Add CLI execution instructions.

---

### Task 4: Update Cron Check-In Job (`91dd42eacfba`)
- **Path:** `~/.hermes/cron/jobs.json`
- **Actions:**
  - Update prompt for job `91dd42eacfba` to run `python3 ~/.hermes/scripts/diet_report.py --mode eod` when log exists.

---

### Task 5: SSOT Git & Protected PR Flow
- **Actions:**
  - Update `docs/reconciliation/v3-source-coverage-manifest.json` with new script & skill.
  - Run security and manifest checks.
  - Open branch, PR, verify CI, squash merge to protected `main`.
  - Deploy to live `~/.hermes/scripts/` and `~/.hermes/skills/`.
