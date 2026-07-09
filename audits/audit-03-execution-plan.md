<!-- ===== OVERHAUL ADDENDUM — 2026-07-09 (OpenCode deep-audit extension) =====
Original v2.2-baseline plan (Sections 0-6) preserved verbatim. New OVERHAUL
PHASES O1-O8 (mapping deep findings F-14..F-24) appended below. No prior text
removed or altered.
============================================================================= -->

# audit-03-execution-plan.md — Prioritized Fix & Sync Plan

> Auditor: OpenCode (executor). Jane/MJ (native VPS agent) = verifier only.
> All changes require user "yes" before commit/push. Med-changing scripts require `--dry-run` first.
> Every fix maps to a finding in audit-02 and to the user's two end-goals: **side-income generation** and **ADHD compensation**.

---

## 0. Principles
1. **Fix the live-VPS blockers first** (gateway restart safety, med correctness) — these protect the user's health and uptime.
2. **Separate the two workstreams**: audit/med system vs anti-bot fragrantica engine. Don't let one block the other.
3. **Every med-state change = backup + `--dry-run`** (FULL-GUIDE Phase 5).
4. **Sync last**: only after P0/P1 fixed, and VPS runtime state (med JSON, jobs.json, gateway_state) stays OFF GitHub (PII/PDPA).

---

## 1. Fix priority table

| # | Finding | Severity | Fix effort | Depends on | Human gate |
|---|---|---|---|---|---|
| P0-1 | F-03 watchdog wrong home → gateway stale-state live | CRITICAL | S (sed) | none | yes (restart safety) |
| P0-2 | F-02 Akurit-2 rename across state files | CRITICAL | M | none | **yes — health data** |
| P0-3 | F-01 med chain blind-shift model | CRITICAL | L (redesign) | F-08 | **yes — clinical model** |
| P1-1 | F-04 chain-state last_reminder_sent clobber | HIGH | S | none | no |
| P1-2 | F-05 V2 Overnight LLM cron scope/cost | HIGH | S/M | none | yes (separate workstream) |
| P1-3 | F-06 providers: '{}' string | HIGH | S | none | no |
| P2-1 | F-07 check_ds_balance.sh wrong home | MED | S | P0-1 | no |
| P2-2 | F-08 GAPS vs nominal 1h mismatch | MED | S | none | no |
| P2-3 | F-09 MEMORY.md at capacity | MED | M | none | no |
| P2-4 | F-10 med names in cron/job metadata | MED | S | sync plan | no |
| P3-1 | F-11 orphan scripts (hello_watch, minimax_proxy) | LOW | S | none | no |
| P3-2 | F-12 stale prep-doc evidence | LOW | doc | none | no |
| P3-3 | F-13 fallback provider alias comment | LOW | doc | none | no |

**Independent vs sequential:**
- Independent (can parallelize): P0-1, P0-2, P1-1, P1-3, P2-1, P2-2, P2-4, P3-1.
- Sequential: P0-3 (med redesign) **must follow** P2-2 (reconcile GAPS vs nominal first, or you'll bake the 1h error into the new model). P2-3 (memory) better done before any big new-skill work.

---

## 2. Per-fix detail (file / change / verify)

### P0-1 — Fix watchdog + check_ds_balance home dir  [F-03, F-07]
- **File:** `scripts/watchdog.sh:9-13`, `scripts/check_ds_balance.sh:3`.
- **Change:** Replace `/home/amirul/.hermes` with `${HERMES_HOME:-$HOME/.hermes}`.
- **Verify:** `bash -n scripts/watchdog.sh`; confirm `ls -l $HOME/.hermes/gateway_state.json` is the path the script will `rm`. Simulate: `STATE_FILE=$HOME/.hermes/gateway_state.json; rm -f "$STATE_FILE"` dry check.
- **Why it matters:** restores the only mitigation for the gateway stale-state P0. Uptime = reliability = foundation for everything else.

### P0-2 — Track the 9/7 Akurit-2 swap  [F-02]
- **File:** `med-schedule.json:13-22`, `med-status.json` (historical), `med-interactions.json:6-7`, `substitutions.json`.
- **Change:** `akurit_4`→`akurit_2`, name `Akurit-4`→`Akurit-2`; re-verify drug composition string (INH/RIF/PZA/ETB) matches the new 4-dose product; update interaction name.
- **Verify:** `--dry-run` in med_confirm/resolver; `grep -rn akurit_4 ~/.hermes/*.{json,py}` returns 0; spot-check one day's reminder still resolves.
- **Human gate:** **YES** — this is health data; user must confirm the exact product swap (4-dose Akurit-2 composition) before applying.
- **Why it matters:** ADHD + TB meningitis → wrong drug advice is dangerous. System must reflect reality.

### P0-3 — Re-model the med chain (kill blind-shift)  [F-01 + F-08]
- **File:** `scripts/chain_calc.py:36-46` (GAPS), `:416-460` (calculate_ready_time), `med-schedule.json:85` (shift_logic rule text).
- **New model (per charter):**
  - Akurit-2 (A): empty stomach. Gates B's *earliest* time only (min 1h after A). Does NOT move Dexa/Levetiracetam.
  - Dexamethasone #1/#2/#3: anchored to fixed 08:00 / 12:00 / 16:00 (independent of A), hard 4h Dexa→Dexa constraint.
  - Levetiracetam B/E: 12h pair, independent of A.
  - Late A → only B's earliest shifts within its window; Dexa holds its clock unless clinically advised.
- **Verify:** unit-test `calculate_ready_time` for A-late scenarios: assert C/D stay at 12:00/16:00; assert B earliest ≥ A+1h but ≤ B window end. Update `shift_logic` text to the correct model.
- **Human gate:** **YES** — clinical timing model must be user-approved; offer to research Dexa 4h-gap rationale if user wants tighter/looser.
- **Why it matters:** directly serves ADHD-compensation (predictable, correct nudges) and health safety.

### P1-1 — Fix chain-state clobber  [F-04]
- **File:** `scripts/chain_monitor.sh:85`.
- **Change:** `state.setdefault('last_reminder_sent', {})[slot] = counts[slot]` (merge, not replace). Same for `last_reminder_times` (already correct at :89).
- **Verify:** run monitor twice for different slots; confirm both slots persist in `last_reminder_sent`.

### P1-2 — Re-scope V2 Overnight Build cron  [F-05]
- **File:** `cron/jobs.json` `1bf7fcc00b60`.
- **Change:** Move to anti-bot project (separate tag/repo) OR convert to `no-agent` + static report script; stop daily LLM spend on unrelated work.
- **Human gate:** **YES** — separate workstream; user decides if it stays.

### P1-3 — Fix providers: '{}'  [F-06]
- **File:** `config.yaml:5`.
- **Change:** `providers: {}` (unquoted).
- **Verify:** `hermes gateway status` still works; no AttributeError in logs.

### P2-2 — Reconcile GAPS vs nominal  [F-08]
- **File:** `chain_calc.py:38`, `med-schedule.json` slot times.
- **Change:** pick one truth (recommend B nominal 08:00 → set `A_to_B: 2.0`, or relabel). Do this BEFORE P0-3.

### P2-3 — Memory headroom  [F-09]
- **File:** `memories/MEMORY.md`, `config.yaml` `memory_char_limit`.
- **Change:** prune stale entries via curator; move stable facts to SOUL.md/USER.md; consider raising limit.
- **Verify:** `wc -c` drops below ~7000; confirm no silent truncation in recent writes.
- **Why it matters:** ADHD safety net depends on memory not being full.

### P2-4 / P3 — Hygiene  [F-10, F-11, F-12, F-13]
- Generic job names; delete `hello_watch.py`, `hello-world.sh`, `minimax_proxy.py` (or mark deprecated); correct prep-doc A6; add alias comment.

---

## 3. Cross-platform sync (Bidirectional) — do LAST
Per `09-MASTER-SYNC-DOC.md` + `10-RESPONSE-TO-OPENCODE.md`. After P0/P1 fixes:
1. **VPS → PC:** daily `rsync ~/.hermes/ → WSL2` (exclude `.env`, `logs/`, `cache/`, `*.db*`). Verify via Jane.
2. **PC → VPS:** OpenCode edits → `git commit` (hermes-live) → VPS `git pull`. **Needs user "yes" per AGENTS.md.**
3. **GitHub:** push `hermes-live → main` AFTER review. **VPS runtime state (med JSON, jobs.json, gateway_state) MUST NOT go to GitHub** (PDPA, F-10).
4. **Commit the 9/7 config fixes** (config.yaml, models.py, run.py) currently UNCOMMITTED on VPS — these are not in `mjay/` repo at all (08-APPENDIX A8). **User "yes" required.**

---

## 4. Mapping to user end-goals
- **Side-income:** The anti-bot fragrantica engine (separate workstream, P1-2) is the income experiment. MJ should eventually *help* run/monitor it (not just chat). Keep it alive but separated so audit fixes don't destabilize it, and so its daily LLM cost (F-05) is visible/controlled.
- **ADHD compensation:** P0-3 (correct, predictable med nudges), P2-3 (memory headroom), P0-1 (system uptime) are the highest-leverage fixes for the ADHD use-case. A reliable external brain that never drops a med reminder or a memory is the core value.

---

## 5. Quick wins (<30 min, safe, no human gate except commits)
- P1-1 (1-line merge fix)
- P1-3 (unquote `providers`)
- P2-2 (GAPS constant)
- P3-1 (delete orphan scripts)
- P2-1 (watchdog home var — pairs with P0-1)

## 6. Explicit NON-actions (per user instructions)
- **Do NOT** pursue MiniMax API issue (user ignored 9/7).
- **Do NOT** reproduce Gemini's CVE/taper claims (struck in audit-02).
- **Do NOT** commit/push without explicit "yes".
- **Do NOT** modify original `~/.hermes/` files except via the above fixes after approval + backup.

---

## OVERHAUL PHASES O1–O8 (2026-07-09 deep-audit extension)

These augment — not replace — the P0–P3 table above. They target the deeper
layers (cost, state architecture, privacy, automation hygiene) and the F-01 med
engine adoption. Each maps to the user's side-income + ADHD goals.

| # | Finding(s) | Severity | Fix effort | Human gate |
|---|---|---|---|---|
| O1 | F-14, F-15, F-19 (cost/config) | HIGH | S | no (verify) |
| O2 | F-16 (med state ACID) | MED | L (design) | yes (health data) |
| O3 | F-17, F-18 (privacy) | MED | S | no |
| O4 | F-20 (cron hygiene) | LOW | S | no |
| O5 | F-21 (cache docs) | LOW | S/doc | no |
| O6 | F-22 (med-auto-confirm hook) | MED | M | yes (med pipeline) |
| O7 | F-23 (restart scripts) | LOW | S | no |
| O8 | F-24 / F-01 (med engine adopt) | CRIT | L | yes (clinical) |

### O1 — Cost & concurrency hardening  [F-14, F-15, F-19]
- **File:** `config.yaml:16,36`; `config.yaml:195-308` (auxiliary block).
- **Change:** `reasoning_effort: high → medium` (default); `max_concurrent_sessions: null → 4–8`; assign cheaper/`reasoning_effort: none` models to aux roles (curator, kanban_decomposer, compression, etc.).
- **Verify:** gateway restart; `hermes cron list` still works; spot-check a turn's token usage drops; confirm aux roles resolve to cheaper model via `auxiliary_client` log.
- **Why:** highest-leverage, near-zero-risk cost + reliability win. Directly extends ADHD-compensation uptime (fewer OOM/stalls).

### O2 — Med state onto a transactional store  [F-16]
- **File:** `med-status.json`, `chain-state.json`, `med-schedule.json` (+ interactions/substitutions).
- **Change:** migrate to SQLite (mirror `kanban.db` pattern) or add atomic write+lock to JSON. Keep backups (`.bak1-3` pattern already exists — good).
- **Verify:** race test (concurrent cron + manual confirm); confirm no clobber like F-04.
- **Human gate:** YES — health data.
- **Why:** makes the safety-critical med pipeline robust; prerequisites the F-01 engine (O8).

### O3 — Privacy / PDPA hardening  [F-17, F-18]
- **File:** `.env` (remove `MINIMAX_API_KEY`), `channel_directory.json`, `jobs.json`, sync exclusions.
- **Change:** delete stale `MINIMAX_API_KEY`; ensure `channel_directory.json` + med JSON + `jobs.json` are excluded from any GitHub sync (audit-03 §3 already mandates this); consider generic job names (F-10).
- **Verify:** grep `.env` for MINIMAX gone; confirm sync script excludes the PII files.
- **Why:** avoids PDPA breach if any state ever leaves the box.

### O4 — Cron hygiene  [F-20]
- **File:** `cron/jobs.json`.
- **Change:** delete obsolete paused jobs (`hello-world-watch`, `Routine Analysis Start Weekend` if abandoned); correct audit-01 §5 "removed" wording.
- **Verify:** `hermes cron list` reflects fewer jobs; no active job lost.

### O5 — Cache/state documentation  [F-21]
- **File:** `.skills_prompt_snapshot.json`, `provider_models_cache.json`, `ollama_cloud_models_cache.json`, `models_dev_cache.json`.
- **Change:** document each cache's purpose + rotation; ensure all excluded from sync.
- **Verify:** none present in a dry-run sync diff to GitHub.

### O6 — Reconcile `med-auto-confirm` hook with med pipeline  [F-22]
- **File:** `hooks/med-auto-confirm/handler.py` + `HOOK.yaml`; `scripts/med_confirm.py`.
- **Change:** document exact write path; make idempotent; ensure no conflicting double-write with `med_confirm.py`.
- **Human gate:** YES — med pipeline.
- **Why:** prevents silent med-state corruption before O8 redesign.

### O7 — Consolidate restart scripts  [F-23]
- **File:** `scripts/gw_restart.sh`, `restart_gateway.sh`, `hermes_gateway_restart.sh`.
- **Change:** pick one canonical script (fix F-03 home-dir bug in it), delete the other two; point watchdog/systemd at the canonical one.
- **Verify:** restart path tested; watchdog uses canonical script.

### O8 — Adopt deterministic med engine (F-01 fix)  [F-24]
- **File:** `MED_CHAIN_ENGINE_SPEC_v3.md` → produce final `solve.py`/`route.py`/`resolve_conflict.py`.
- **Change (Phase C):** read full spec; verify clinically-correct model (A gates only B's earliest via 1h empty-stomach wait; Dexa fixed 08/12/16; Levetiracetam 12h pair); reconcile GAPS with F-08; refine gaps; finalize. Replace `chain_calc.py` blind-shift with the deterministic engine.
- **Human gate:** YES — clinical timing.
- **Why:** resolves the #1 defect (F-01) at its root (LLM auto-linearization), and is the user-approved path. Serves ADHD-compensation (correct, predictable nudges) + health safety.

### Mapping to user end-goals (overhaul extension)
- **Side-income:** O1/O5 keep the system cheap + stable so the anti-bot income engine (F-05) runs on a reliable, cost-visible base; O8's deterministic engine is reusable for any scheduled/monitored service the user productizes.
- **ADHD compensation:** O1 (uptime), O2 (robust med memory), O6/O8 (correct, conflict-free med nudges), F-09 memory headroom — together they make MJ a dependable external brain.
- **Medication intelligence (2026-level):** O8 + O2 replace the 2010-style linear chain with a deterministic constraint solver — the upgrade the user explicitly wants.

---

## OVERHAUL ADDENDUM — F-01 Final Remediation Spec (Phase C, 2026-07-09)

**Status:** Evaluates + refines `MED_CHAIN_ENGINE_SPEC_v3.md` (MJ native agent, design-only, not yet implemented). Approved disposition for **F-01** (audit-02) and **F-24**.

### C.1 Root cause (systematic-debugging Phase 1)
- `scripts/chain_calc.py:416-460` hard-codes a single **linear** chain: `B=A+GAPS[A_to_B]`, `C=B+...`, `D=C+...`, `E=B+...`. The LLM layer then *auto-linearizes* the branched dependency graph, so a late A blindly shifts every slot (F-01). Root cause = representing an independent-clocked regimen as one dependency chain. The fix is a **deterministic constraint engine** (spec's design) — not another patch to the linear math.

### C.2 Corrected constraint model (refines spec rules 001–006)
Per the user's clinically-correct model (verified 2026-07-09): A only gates B's *earliest* via ~1h empty-stomach wait; **Dexa #1/#2/#3 are fixed clocks (08:00 / 12:00 / 16:00), independent of A**; Dexa→Dexa ~4h is a *validation* property, not a B-derived edge; Levetiracetam B/E = 12h pair.

```
Slot A  (Akurit-2 + Pyridoxine)   scheduled 06:00   | gates B earliest via min_gap 1h
Slot B  (Levetiracetam + Dexa#1)  scheduled 08:00   | earliest = max(08:00, A + 1h)
Slot C  (Dexa#2 + Ca/Calcitriol/B-Complex) scheduled 12:00  | FIXED (independent)
Slot D  (Dexa#3)                  scheduled 16:00   | FIXED (independent)
Slot E  (Levetiracetam)           scheduled 20:00   | = B + 12h (Leve pair; moves with B)
Slot PRN (Pantoprazole)           on-demand         | not in chain
```

**Solver semantics (corrected):**
- Each slot has `scheduled` time + `earliest` bound from constraints. `final = max(scheduled, earliest)`.
- Propagate **downstream only** along real edges (A→B min_gap; B→E +12h). Dexa C/D are terminal fixed nodes (no inbound edge from B).
- **Validation constraints (not edges):** `C - B ≈ 4h`, `D - C ≈ 4h`. If a late A pushes B's earliest past 08:00, the validator raises a **medical_safety conflict** (B late vs Dexa fixed) → alert, do NOT silently reschedule Dexa.
- **Missed-dose policy (NEW, was missing in spec):** if `final` < now (slot time already passed because A was very late), mark slot `MISSED`, send alert, never schedule in the past. Critical for safety.

### C.3 Corrected `rules.json` (v1)
```json
{
  "schema_version": 1,
  "domain": "medication",
  "slots": {
    "A": {"scheduled": "06:00", "gates": ["B"]},
    "B": {"scheduled": "08:00", "paired_12h": "E"},
    "C": {"scheduled": "12:00", "fixed": true},
    "D": {"scheduled": "16:00", "fixed": true},
    "E": {"scheduled": "20:00", "offset_from": "B", "hours": 12}
  },
  "constraints": [
    {"id": "rule_001", "type": "min_gap", "from": "A", "to": "B", "hours": 1, "priority": 95},
    {"id": "rule_002", "type": "validate_gap", "from": "B", "to": "C", "hours": 4, "priority": 95},
    {"id": "rule_003", "type": "validate_gap", "from": "C", "to": "D", "hours": 4, "priority": 95},
    {"id": "rule_004", "type": "offset", "from": "B", "to": "E", "hours": 12, "priority": 95},
    {"id": "rule_005", "type": "independent", "slot": "C", "priority": 100},
    {"id": "rule_006", "type": "independent", "slot": "D", "priority": 100}
  ],
  "missed_dose": {"policy": "alert_and_skip", "never_schedule_past": true}
}
```
Key change vs spec v3: `rule_002/003` are now `validate_gap` (not `fixed_gap` propagation); C/D carry `"fixed": true`; added `missed_dose` policy.

### C.4 Conflict resolver (keep spec's priority stack)
`doctor_prescription:100 > medical_safety:95 > user_request:60 > preference:20`. Example: user says "C=1pm" while B=09:43 → validator sees C-B≠4h → medical_safety(95) beats user_request(60) → C stays 12:00 (fixed), conflict logged. Dexa is NEVER moved by a user/Late-A input.

### C.5 Integration points (build order, refined from spec)
1. `scripts/med_chain/rules.json` (v1 above).
2. `solve.py` — topological solve, `final = max(scheduled, earliest)`, downstream-only, returns `{slots, untouched, conflicts[], missed[]}`.
3. `resolve_conflict.py` — priority stack (above).
4. `tests/` — **must include regression #17** ("E ikut C" → permanent fail) + **new A-late-Dexa-fixed test**: A=10:00 → B earliest 11:00, C=12:00 (fixed, untouched), D=16:00 (fixed), E=23:00 (B+12h); assert Dexa did NOT shift.
5. `validate_semantic.py` + `trace.py` (append to `logs/med_chain_trace.jsonl`).
6. `route.py` — low→solver→send; high→+validator+reviewer.
7. `why.py` — explainability (`/why D`).
8. **Patch `chain_calc.py` to call the solver** (replace `:416-460` linear math).
9. **`chain_monitor.sh` + `med-auto-confirm` hook (F-22) must also use the solver** so all writers agree; fix `chain-state.json` clobber (F-04) to persist per-slot.
10. Reconciles **F-08**: A_to_B `min_gap 1h` is now correctly the *earliest* bound, while `scheduled B=08:00` is the default — no more 1h-early bug.

### C.6 Verification (before any production switch)
- Unit tests green (regression #17 + A-late-Dexa-fixed + missed-dose).
- Dry-run on last 7 days of `med-status.json`: compare engine output vs what the old linear chain would have sent; confirm Dexa stayed fixed and only B's earliest moved on late-A days.
- `--dry-run` + `.bak` backup of `med-schedule.json`/`chain-state.json` (FULL-GUIDE Phase 5).
- **Human gate: YES** — clinical timing model must be user-approved before flipping the live reminder path.

### C.7 Defects found in original spec v3 (resolved by this addendum)
- D1: Dexa modeled as `fixed_gap` from B (wrong causal model) → changed to `fixed` + `validate_gap`.
- D2: no `scheduled` vs `earliest` distinction (caused F-08) → added `final = max(scheduled, earliest)`.
- D3: no missed-dose handling → added `missed_dose` policy.
- D4: worked examples assumed unstated prior state → examples must be self-contained + covered by tests.
