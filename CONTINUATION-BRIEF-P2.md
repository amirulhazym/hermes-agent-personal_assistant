# Hermes Agent Overhaul — CONTINUATION BRIEF P2 (fresh session handoff)

> **Attach BOTH this file AND `OVERHAUL-EXECUTION-PROMPT.md` to the new session.**
> `OVERHAUL-EXECUTION-PROMPT.md` = immutable mandate (skills, freeze rule, R1–R7).
> This file = live progress through P1 + the FULL P2 execution plan. A fresh agent
> has full context without re-deriving anything — which is what prevents the
> context-limit stall.
>
> Paste both into a NEW OpenCode session pointed at workspace
> `F:\AI Prep\OVIS\Hermes Agent\MJay`. Read both fully before acting.

---

## 0. ROLE & MANDATE

You are the user's strategic advisor + executor for a full overhaul of the
**Hermes Agent** — a personal AI assistant for user `amirulhazym` (Malaysian,
Manglish, EEE grad, self-taught AI). It runs on a VPS and bridges Telegram +
WhatsApp, with medication-reminder (TB treatment) logic as its most critical
feature.

The authoritative execution brief is **`OVERHAUL-EXECUTION-PROMPT.md`** in this
workspace. READ IT FULLY before any implementation work. Key points it sets:
- Mandatory skills: `using-superpowers`, `mattpocock`, `evidence-first`,
  `incremental-implementation`, `gsd` mindset. Load skills before acting.
- "Freeze is real" rule: do NOT break live med logic. Per-step user approval.
- R1: context-window monitoring — for hy3-free model, **60% (~150k tokens) is a
  HARD STOP**; request a fresh context before it dies silently. Use subagents or
  a new session per phase.
- R2 checkpoint discipline: after each task, STOP, report evidence, ask owner to
  confirm before next.
- MJ (native Hermes agent) = VERIFIER ONLY, never executor. Only OpenCode (you)
  makes changes.

**Phase 0 = DONE. P0 = DONE. P1 = DONE (all 12 tasks, verified). Execution is
now at P2 (Akurit-4 → Akurit-2 propagation).**

## 1. HARD CONSTRAINTS (non-negotiable)

- **Skills mandatory** before any action (see §0). Use `test-driven-development`
  and `verification-before-completion` for P2 edits.
- **Evidence-first labels**: VALIDATED / UNTESTED / REJECTED. Never claim success
  without raw command output as proof.
- **Single-source findings**: flag if only one source claims something.
- **No secrets in files**: never print/commit `.env`, bot tokens, API keys,
  WhatsApp session folders. Reference secrets by ENV VAR NAME only.
- **MJ = verifier ONLY**. Only OpenCode (you) changes the VPS.
- **Sequential discipline**: one step, verify, then next.
- **STOP and ask before** destructive / irreversible / paid / deploy / external.
- **Manglish OK** in user comms.
- **Per-step approval**: riskier steps need explicit user "yes".

## 2. ENVIRONMENT

- **VPS**: Tencent Lighthouse SG, `ubuntu@119.28.119.151`, home `/home/ubuntu`.
  SSH: `ssh -o ConnectTimeout=10 ubuntu@119.28.119.151`.
- **Hermes install**: `~/.hermes/` (config, hooks, scripts, whatsapp/session).
  Agent code: `~/.hermes/hermes-agent/` (venv at `hermes-agent/venv/bin/hermes`).
- **Gateway supervision**: `systemd --user` service `hermes-gateway.service`
  (enabled, `Restart=always`).
  Restart: `ssh ubuntu@119.28.119.151 'systemctl --user restart hermes-gateway'`.
  Health check (cron `*/15`): `health_check.py` only ALERTS, does not restart.
- **VPS timezone**: `Asia/Shanghai` (UTC+8) = MYT — time-based med logic works.
- **Local workspace (this repo)**: `F:\AI Prep\OVIS\Hermes Agent\MJay` (git repo;
  mirrors docs/audits only — NEVER med PII JSON).
- **Test runner**: **stdlib `unittest`**, NOT pytest. pytest is NOT installed in
  the venv (discovered during P1). Run tests as
  `~/.hermes/hermes-agent/venv/bin/python <test_file>.py`.

## 3. USER-PHASE AUTHORIZATION (still in effect)

User authorized **live VPS changes for this overhaul phase**, WITH:
- gateway-restart + immediate verification after EACH step;
- only OpenCode (you) makes changes — never the Hermes agent/Jane.
- Per-step approval still required for riskier steps.

## 4. Q&A DECISIONS ALREADY MADE (do not re-litigate)

- **Q1**: Akurit-4 → **Akurit-2** swap CONFIRMED. Full intake (4 biji) started
  **9/7/2026**. Latest appointment **6/7/2026**.
  - **P2 dosage/composition (CONFIRMED for P2)**: **4 biji Akurit-2 per day**,
    at the usual slot-A time. Note MUST change to
    **"Rifampicin+Isoniazid"** (DROP Pyrazinamide+Ethambutol) — that is the
    exact difference between Akurit-4 (4-drug) and Akurit-2 (2-drug: RIF+INH).
- **Q2 (med-status history — CORRECT RULE, do NOT be lazy)**:
  - `med-status.json` entries **dated >= 2026-07-09** must record `akurit_2`
    (the swap took effect 9/7; anything logged as `akurit_4` from 9/7 onward is
    WRONG and must be rewritten to `akurit_2`).
  - Entries **dated < 2026-07-09** stay `akurit_4` — that is historical truth
    (Akurit-4 genuinely was taken then). Do NOT rewrite pre-swap history.
- **Q3**: Full v3 build of `MED_CHAIN_ENGINE_SPEC_v3`. (**DONE in P1.**)
- **Q4**: Remove standalone MiniMax provider + plugin + leftovers; keep minimax
  via `opencode-zen`/`opencode-go`. (**DONE P0-S5.**)
- **Q5**: Split but partially build multi-agent setup; document for later. (Phase 4.)
- **Q6**: Approve all verification methods; check deeply every file/word.
- **Q7**: Approve `chmod 700 whatsapp/session`. (**DONE P0-S3.**)

## 5. COMPLETED WORK — P0, P1 FULLY DONE (all verified)

### P0 (critical quick fixes) — DONE
- **P0-S1 (PII leak)**: `.gitignore` + `sync/SYNC-MECHANISM.md` fixed. VERIFIED
  `git check-ignore` excludes PII files.
- **P0-S2a**: Disabled `med-auto-confirm` hook, restarted. VERIFIED.
- **P0-S2b (Pattern G fix)**: Rewrote `handler.py` with G-1..G-7, DRUG_MAP
  `akurit_4`→`akurit_2`, dexa fix. `test_med_auto_confirm.py` **14/14 PASS**.
  VERIFIED hook loaded; gateway running.
- **P0-S2c (G-5 freeze fix)**: Rewrote `chain_monitor.sh`. VERIFIED.
- **P0-S3 (session perms)**: `chmod 700 whatsapp/session`. VERIFIED.
- **P0-S4 (paths + supervisor)**: `/home/amirul`→`home/ubuntu` fixes + `watchdog.sh`
  rewrite. VERIFIED restart works; TG/WA connected.
- **P0-S5 (MiniMax removal)**: Removed registrations + plugin + proxy. VERIFIED
  standalone `MiniMax-M*` gone, opencode minimax preserved. Backups in
  `~/hermes-overhaul-backup/`.

### P1 (Medication Chain Engine v3) — DONE & VERIFIED
Built directly on VPS in `~/.hermes/scripts/med_chain/` (new dir, non-destructive)
using **TDD (Red-Green-Refactor)** with stdlib `unittest` (pytest unavailable).

Artifacts created on VPS:
- `rules.json` — 6 constraints (schema v1).
- `solve.py` — deterministic forward constraint solver.
- `resolve_conflict.py` — priority stack (doctor/medical/user/preference).
- `chain_trace.py` — execution trace → `~/.hermes/logs/med_chain_trace.jsonl`
  (renamed from `trace.py` — that name collides with Python stdlib `trace`).
- `validate_semantic.py` — LLM-output vs solver truth.
- `route.py` — low/high complexity router (`send`/`review`).
- `why.py` — explainability API.
- `chain_consistency.py` — contradiction checker (used by the hook, T11).
- `chain_review.py` — rule-based self-audit (T12).
- `tests/` — `test_solver.py`, `test_offsets.py`, `test_conflicts.py`,
  `test_regression.py`, `test_trace.py`, `test_validate.py`, `test_route.py`,
  `test_why.py`, `test_mingap.py`, `test_consistency.py`, `test_review.py`
  → **21 tests, ALL PASS**.

Integration (freeze-safe):
- **T10**: `chain_calc.py` patched — added `compute_slots_deterministic()`
  (guarded, returns `None` on any error → existing GAP math runs unchanged).
  Backup: `chain_calc.py.bak`. VERIFIED: `chain_calc.py --display` new vs `.bak`
  **identical**; engine path correct (A→B→C→D→E forward; **E never from C** —
  regression #17 safe).
- **T11**: `hooks/med-auto-confirm/handler.py` patched — on every med
  confirmation that states a time, runs `chain_consistency.consistency_warnings`
  and audits + writes `logs/med_chain_warnings.jsonl` on contradiction. Fail-open
  (never blocks confirmation). Backup: `handler.py.bak`. VERIFIED: hook loaded
  post-restart, new test `test_hook_chain.py` **PASSED**, gateway active, WA
  connected, no traceback.
- **T12**: `chain_review.py` — demonstrated all 6 rules PASSED.

**TDD caught 2 real bugs during P1 (plan improvements):**
1. My own `solve.py` wrongly blocked `rule_004` (E=B+12h) via an incorrect
   `independent` guard → fixed (independent only protects a *user-set* value).
2. `trace.py` shadows Python stdlib `trace` → renamed `chain_trace.py`.

**Deviations from written plan (approved by user):**
- pytest → stdlib `unittest` (pytest not installed).
- `trace.py` → `chain_trace.py` (stdlib collision).

## 6. P2 — AKURIT-4 → AKURIT-2 PROPAGATION (PLAN, READY TO EXECUTE)

**Goal**: make the live system consistently say **Akurit-2** everywhere from
9/7/2026 onward, with correct dosage (4 biji) and correct composition note
(RIF+Isoniazid). The hook (`handler.py`) is ALREADY swap-aware (P0 DRUG_MAP maps
both `akurit-2` and `akurit-4` → `akurit_2`), so no hook logic change is needed.

### Live references found (read-only grep, this session)
| File | `akurit` count | P2 action |
|---|---|---|
| `med-schedule.json` | 3 | **Primary** — slot A drug → Akurit-2 |
| `substitutions.json` | 3 | Add `akurit_2` block; add to `prescription_only` |
| `med-supply.json` | 3 | Relabel `akurit_4`→`akurit_2` (current stock) |
| `med-interactions.json` | 14 | Relabel current-drug references `akurit_4`→`akurit_2` |
| `med-status.json` | 8 | **Per Q2 rule** (see §4) — rewrite 9/7+ entries to `akurit_2`; keep pre-9/7 as `akurit_4` |
| `scripts/med_supply.py` | 7 | Display strings → `akurit_2` |
| `scripts/med_interact.py` | 4 | Display strings → `akurit_2` |
| `scripts/med_resolve.py` | 3 | Display strings → `akurit_2` |
| `scripts/med_substitute.py` | 1 | Display strings → `akurit_2` |
| `hooks/skill-trigger/handler.py` | 1 | Display string → `akurit_2` |
| `chain_calc.py` | 0 | none |
| `hooks/med-auto-confirm/handler.py` | 3 | already `akurit_2` (P0) — no change |

### Execution steps (freeze-safe, backup-first, per-step)
- **P2-S0 (Backup)**: copy every file to be touched into
  `~/hermes-overhaul-backup/pre-p2/` (reversible). VERIFY each backup exists.
- **P2-S1 `med-schedule.json` (slot A)**:
  - `name`: "Akurit-4 + Pyridoxine" → "Akurit-2 + Pyridoxine"
  - drug entry `Akurit-4` → `Akurit-2`; `drug_id` `akurit_4` → `akurit_2`
  - `dosage`: "4 tablet" (stays — 4 biji per Q1)
  - `note`: "Isoniazid+Rifampicin+Pyrazinamide+Ethambutol" →
    **"Rifampicin+Isoniazid"** (drop PZA+Ethambutol, per Q1)
  - VERIFY: `python -m json.tool` parses; grep shows `akurit_2`, zero `akurit_4`
    in this file.
- **P2-S2 `substitutions.json`**:
  - Add `"akurit_2"` block (original "Akurit-2 (Rifampicin+Isoniazid)", slot A,
    `no_substitute_available: true`).
  - `general_rules.prescription_only`: add `"akurit_2"`.
  - (Keep the historical `akurit_4` block — it documents what was used pre-swap.)
  - VERIFY parse + grep.
- **P2-S3 `med-supply.json` + `med-interactions.json`**: relabel current-drug
  `akurit_4`→`akurit_2` (only where it denotes the CURRENT drug, not historical
  notes). VERIFY parse + grep.
- **P2-S4 scripts display strings**: `med_supply.py`, `med_interact.py`,
  `med_resolve.py`, `med_substitute.py`, `hooks/skill-trigger/handler.py` —
  replace user-facing `Akurit-4`/`akurit_4` labels with `Akurit-2`/`akurit_2`.
  VERIFY each file `py_compile` + grep.
- **P2-S5 `med-status.json` (SENSITIVE — per Q2 rule)**:
  - For each date key **>= 2026-07-09**, rewrite any `akurit_4` drug id/name to
    `akurit_2`. Leave dates **< 2026-07-09** untouched (historical).
  - Do this with a guarded Python script (read → transform only matching dates →
    write), never hand-edit PII. Keep a timestamped backup.
  - VERIFY: `python -c` counts of `akurit_4` per date bucket; confirm zero
    `akurit_4` on/after 9/7, and pre-9/7 history preserved.
- **P2-S6 (verify live)**:
  - `chain_calc.py --display` still clean; run a med-confirm dry check.
  - `grep -rni "akurit_4" ~/.hermes --include=*.json --include=*.py` → only
    intentional historical references remain (substitutions.json `akurit_4` block,
    med-status pre-9/7 entries).
  - Restart gateway: `systemctl --user restart hermes-gateway`; verify active,
    hook loaded, TG/WA connected, no traceback.
  - Re-run hook consistency test if touched.

### Context ratio (P2 vs P1)
- P1 used ~60% of the 256k limit (12-module engine + 21 tests + 2 skills + many
  verify cycles).
- P2 is ~6–8 file edits, **no new engine build, no new test suite** (verification
  is grep/display/parse + one guarded transform script). Expected **≈30–40% of
  P1's usage** (~20–25% of limit). Comfortably fits ONE session — but because the
  PREVIOUS session ended near the 60% hard stop, **P2 runs in THIS fresh session**.

## 7. REORIENTATION COMMANDS (run first in new session)

```
# Local repo
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" status
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" log --oneline -5

# Mandate + this brief
# open: OVERHAUL-EXECUTION-PROMPT.md, CONTINUATION-BRIEF-P2.md

# VPS orientation
ssh ubuntu@119.28.119.151 'systemctl --user status hermes-gateway --no-pager | head -6'
ssh ubuntu@119.28.119.151 'cat ~/.hermes/chain-state.json | head -20'
ssh ubuntu@119.28.119.151 'ls -la ~/.hermes/scripts/med_chain/'            # EXPECT: exists (P1 built)
ssh ubuntu@119.28.119.151 '~/.hermes/hermes-agent/venv/bin/python -m unittest discover -s /home/ubuntu/.hermes/scripts/med_chain/tests -p "test_*.py"'  # EXPECT: 21 passed
ssh ubuntu@119.28.119.151 'ls -la ~/hermes-overhaul-backup/'

# P2 targets (read-only first)
ssh ubuntu@119.28.119.151 'cat ~/.hermes/med-schedule.json'
ssh ubuntu@119.28.119.151 'grep -rlni "akurit" /home/ubuntu/.hermes --include=*.py --include=*.json --include=*.yaml --include=*.sh 2>/dev/null | grep -v /logs/ | grep -v backup-pre'
```

## 8. NEXT MOVES (after P2)

- **P3**: Cost/config hygiene (F-14/15/19/06, memory headroom, cron scope,
  skill curation).
- **Phase 4**: Partial multi-agent setup, documented for later full build.

## 9. KEY FILES

Local workspace:
- `OVERHAUL-EXECUTION-PROMPT.md` — mandate (authority). **Attach to new session.**
- `CONTINUATION-BRIEF-P2.md` — this file. **Attach to new session.**
- `docs/superpowers/plans/2026-07-11-med-chain-engine-v3.md` — P1 plan (reference).
- `audit-prep/MED_CHAIN_ENGINE_SPEC_v3.md` — P1 design reference.
- `.gitignore`, `sync/SYNC-MECHANISM.md` — P0-S1 PII fixes.

VPS (`~/.hermes/...`):
- `scripts/med_chain/` — **P1 engine (exists)**: rules.json, solve.py,
  resolve_conflict.py, chain_trace.py, validate_semantic.py, route.py, why.py,
  chain_consistency.py, chain_review.py, tests/ (21 tests).
- `scripts/chain_calc.py` (+`.bak`) — P1 T10 patch (engine source of truth,
  freeze-safe fallback).
- `hooks/med-auto-confirm/handler.py` (+`.bak`) — P0 Pattern G + P1 T11
  consistency check; `test_med_auto_confirm.py` (14) + `test_hook_chain.py` (3).
- `scripts/med_supply.py`, `med_interact.py`, `med_resolve.py`, `med_substitute.py`
  — P2-S4 display-string targets.
- `med-schedule.json`, `substitutions.json`, `med-supply.json`,
  `med-interactions.json`, `med-status.json` — P2 data targets (med-status = PII,
  handle per Q2 rule).
- `scripts/chain_monitor.sh` (+`.bak`) — G-5 fix (P0-S2c).
- `whatsapp/session` — chmod 700 (P0-S3).
- `scripts/watchdog.sh`(+`.bak`), `check_ds_balance.sh`(+`.bak`),
  `restart_gateway.sh`(+`.bak`) — path fix (P0-S4).
- `config.yaml` — `providers: '{}'`.
- `~/.config/systemd/user/hermes-gateway.service` — gateway supervisor.
- `logs/med-auto-confirm-audit.log`, `logs/med_chain_warnings.jsonl`,
  `logs/med_chain_trace.jsonl` — audit trails.
- `~/hermes-overhaul-backup/` — all P0/P1 backups (reversible) + `pre-p2/` (P2).

## 10. SESSION DISCIPLINE REMINDER

- One step, verify, then next. Never batch unverified changes.
- Tag evidence: VALIDATED/UNTESTED/REJECTED.
- Ask before destructive/irreversible/paid actions.
- **Context: 60% hard stop for hy3-free** — request fresh session before stall.
- Keep the user informed concisely; preserve Manglish tone in user-facing text.
- **P2 med-status edit is the only sensitive/PII step (P2-S5)** — use a guarded
  transform script, keep a timestamped backup, and follow the Q2 date rule
  EXACTLY (>= 9/7 → akurit_2; < 9/7 → leave as akurit_4).
