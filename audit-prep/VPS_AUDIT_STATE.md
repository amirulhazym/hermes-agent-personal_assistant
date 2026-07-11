# VPS Audit State — Source of Truth Snapshot
Last updated: 2026-07-08 02:56 MYT (by VPS Native Auditor)

## Purpose
This file is the VPS-side record of what has ALREADY changed/verified on the live
system. Any external AI agent (Gemini/Antigravity coding agent) MUST rsync PULL
from VPS before auditing, and cross-check claims against this file + live VPS.

## VERIFIED VPS STATE (live, not PC snapshot)

### Phase 1 (deployed by external AI, VERIFIED by native auditor)
- `redact_pii: true` (config.yaml line 383)
- `fallback_providers:` 3 tiers (deepseek → opencode-zen → opencode-go) (lines 6-12)
- `mcp_servers: {}` (line 740) — cua-driver Windows path removed
- Gateway restarted clean: PID 2543798, Telegram+WhatsApp connected
- Default model changed to `deepseek-v4-flash-free` (line 2) — hidden change, not in report

### Med System — E2.x findings (cross-checked both sides, AGREED)
- **E2.1**: Engine CORRECT on VPS. chain_calc.py line 222 =
  `'C': 'dose_2pm' if freq == 'BD' else 'dose_midday'`
  Only DISPLAY bug at line 982 (--summary shows 0mg instead of dose_2pm).
  Status: P2, display-only. NOT engine-level.
- **E2.2**: decrement(drug_id, amount=1) supports qty but med_confirm.py calls
  without qty. med-schedule.json has NO qty field. Status: SKIP, need schedule update.
- **E2.3**: CONFIRMED REAL. med_confirm.py line 264-270 has NO guard before
  decrement. Fix: add `if existing_status == 'taken': continue` in confirm_slot
  (line 264) AND confirm_drug (line 318). Status: P1, VPS NOT YET FIXED.
- **E2.4**: TIME_RULES (med_resolve.py 86-90) is dynamic clock-window, NOT static.
  Edge-case only in BD phase (Slot D inactive, resolver maps 5pm→D).
  Status: P3, low priority.

### BLOCKED ACTIONS
- PC→VPS file copy: BLOCKED. PC snapshot stale (line 222 outdated there).
  Copy would REVERT working VPS fix. All edits MUST be applied directly on VPS.

## RULES (agreed by boss)
1. VPS live > WSL2/PC > GitHub (source of truth hierarchy)
2. No PC→VPS copy. Ever.
3. No deploy without Native Auditor verification.
4. External AI = auditor/executor. Native Auditor = verifier of VPS truth.
5. Before any audit batch: external AI MUST rsync PULL VPS→PC for fresh snapshot.

## PENDING (not yet tackled from 8-dimension audit)
- Backup gap (no offsite backup of ~/.hermes/)
- MEMORY.md at 100% (9055/9000 chars) — silent write failures
- Appointment auto-complete (appointments.json status stale "upcoming" for 7/6)
- Gateway stale-state bug (gateway_state.json persists "running" after SIGTERM)
- Git auto-commit hook (no commits since Jul 1)
- hello-world-watch cron every 1m (CPU waste)
