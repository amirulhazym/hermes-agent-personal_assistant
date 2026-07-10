# Hermes Agent — System Context & Understanding (Audit 01)

> **Auditor:** ZCode (fresh, independent pass) · **Date:** 2026-07-05
> **Source of truth:** `C:/Users/amiru/hermes-snapshot-20260705/` — a complete rsync of the live VPS `~/.hermes/` (Tencent Lighthouse, Singapore), taken 2026-07-05.
> **Stance:** Unbiased. I did NOT read any prior audit document (`MJay/audits/*`, `AUDIT.md`, `CLAUDE_AUDIT_PROMPT.md`, `NEW_AUDIT_PROMPT.md`, `snapshot/audits/*`). I read the code, data, and project governance docs (PRD/PROGRESS/DECISIONS/RUNBOOK) only.
> **Method:** Static-first, evidence-cited (`file:line`). Selectively attempted dry-run (see §0).

---

## 0. Verification note (what I could and could not prove here)

- **Could NOT run the med scripts live.** This audit runs on Windows (Python 3.13.7) where `chain_calc.py` **hard-crashes at import** due to a missing `tzdata` package (`ModuleNotFoundError: No module named 'tzdata'`, raised at `chain_calc.py:27` `ZoneInfo('Asia/Kuala_Lumpur')`). I did not install packages, to keep this a read-only audit. Therefore behavioral claims about `med_confirm.py` / `chain_calc.py` runtime paths are marked **THEORETICAL / UNVERIFIED** where I could not execute them. The `tzdata` crash is itself a real, reproduced finding (see Doc 2, finding S-DTZ-1).
- **All code/data findings are from direct file reads** with `file:line` citations. No claim rests on a prior audit.
- `42crunch-api-security-testing` was referenced in the task. **It does not apply** — see §9.

---

## 1. Executive summary — what this system is

Hermes (persona "MarryJane"/"Jane") is a personal AI assistant built on the open-source **Nous Research Hermes Agent** (v0.17.0), running as a single long-lived gateway process on a Tencent Lighthouse VPS (Singapore). It connects **WhatsApp** (via Baileys bridge) and **Telegram** (Bot API) to one "brain," and proactively messages the owner (Amirulhazym) via a **Hermes cron scheduler**.

The system has grown far beyond its original "reminder bot" shape. Today it has three load-bearing subsystems:

1. **Medication "Domino Chain"** — the patient-safety core. 5 daily slots (A–E) for a TB-meningitis regimen (Akurit-4, Dexamethasone taper, Levetiracetam, B-Complex, Calcium, Calcitriol), tracked at **drug-level** granularity with chain-dependent reminder timing and an automatic Dexamethasone taper engine.
2. **Proactive cron layer** — ~14 jobs (per `cron/jobs.json`): briefings, check-ins, reports, the Domino Chain monitor (every 15 min), taper alert, compliance report, appointment reminders, watchdogs.
3. **Agent persona + skills/hooks** — `SOUL.md`, a `med-tracker` skill, an `anti-fabrication-guardrails` skill, a `malaysia-country-selector` skill, and a `skill-trigger` hook that auto-injects skills on message keywords.

Supporting layers: `config.yaml` (providers/models/features), JSON state files, a 141 MB `state.db` (SQLite), and `whatsapp/session/` credential stores.

**The thing that matters most — and is most fragile — is the medication layer.** It is where patient data lives, where silent data corruption has already occurred (Pattern A in the brief), and where the audit found the densest cluster of CRITICAL/HIGH issues.

---

## 2. Architecture (text + mermaid)

### 2.1 Component map

```
                    USER (WhatsApp + Telegram)
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
     WhatsApp (Baileys bridge            Telegram (Bot API)
     on VPS, port 3000)                  via Hermes gateway
            │                                   │
            └──────────────┬────────────────────┘
                           ▼
              ┌──────────────────────────────────┐
              │  Hermes Gateway (single process)  │
              │  - platform adapters              │
              │  - session routing                │
              │  - cron scheduler (60s tick,      │
              │      file-locked .tick.lock)      │
              │  - agent core (SOUL.md, MEMORY)   │
              │  - approvals / slash commands     │
              └──────────────┬───────────────────┘
                             │
          ┌──────────────────┼─────────────────────────┐
          ▼                  ▼                          ▼
   ┌────────────┐   ┌─────────────────┐        ┌──────────────────┐
   │ LLM calls  │   │  Cron jobs       │        │  Skills / Hooks  │
   │(opencode-go│   │ (cron/jobs.json) │        │ med-tracker,      │
   │ deepseek-v4│   │ no_agent scripts │        │ anti-fab, skill-  │
   │ -pro / zen)│   │ = pure Python    │        │ trigger hook     │
   └────────────┘   └────────┬─────────┘        └────────┬─────────┘
                             │                            │
                             ▼                            │
                   ┌──────────────────┐                  │
                   │ chain_monitor.sh │◄─────────────────┘ (injected ctx)
                   │ → chain_calc.py  │
                   │ → chain_llm.py   │
                   └────────┬─────────┘
                            ▼
              ┌─────────────────────────────┐
              │  STATE (JSON + SQLite)       │
              │ med-status / chain-state /   │
              │ dexa_taper / med-supply /    │
              │ med-interactions / subs /    │
              │ appointments / config.yaml / │
              │ state.db (sessions/memory)    │
              └─────────────────────────────┘
```

### 2.2 End-to-end data flow (a "I took B" cycle)

```mermaid
flowchart TD
    U[User: "I took B 9:10am" on WhatsApp] --> R[Gateway routes msg to agent]
    R --> H{skill-trigger hook<br/>agent:start}
    H -->|regex match| T[Write triggered_skills.txt = med-tracker]
    T --> S[Agent loads med-tracker skill]
    S --> M[Agent resolves drug via med_resolve.py]
    M --> C[Agent runs: med_confirm.py B --time 09:10]
    C --> W[med_confirm.confirm_slot writes med-status.json<br/>+ decrements med-supply + rotates .bak]
    W --> OK[Confirmation echoed to chat]
    C -. every 15 min .-> CM[chain_monitor.sh: chain_calc.py --next]
    CM --> F{should_fire?}
    F -->|yes| LL[chain_llm.py builds Manglish reminder]
    F -->|no| ID[increment reminder_count in chain-state.json]
    LL --> D[Deliver to whatsapp:120363428305511789]
```

(Flow reconstructed statically from `med_confirm.py:412-510`, `chain_monitor.sh:24-94`, `chain_calc.py:444-633`, `chain_llm.py:270`, `handler.py:22-45`, `HOOK.yaml:1-5`.)

---

## 3. Subsystem A — Medication "Domino Chain"

### 3.1 Slot model (from `med-schedule.json`)
| Slot | Drugs (drug_id) | Time / window | Notes |
|---|---|---|---|
| A | Akurit-4 (`akurit_4`), Pyridoxine (`pyridoxine`) | 06:00, empty stomach | `med-schedule.json:6-18` |
| B | Levetiracetam (`levetiracetam_b`), Dexamethasone #1 (`dexamethasone_1`, 5mg) | 08:00 | `med-schedule.json:19-31` |
| C | Dexa #2 (`dexamethasone_2`, 5mg), Calcium (`calcium`), Calcitriol (`calcitriol`), B-Complex (`b_complex`, required:false, Wed/Sat only) | 12:00 | `med-schedule.json:32-46` |
| D | Dexa #3 (`dexamethasone_3`, 4mg) | 16:00 | `med-schedule.json:47-58` |
| E | Levetiracetam (`levetiracetam_e`, 500mg) | 20:00 | `med-schedule.json:59-70` |

Gap rules in `med-schedule.json:80-87`: A→B min 1h; B→C 4h; C→D 4h; B→E 12h.

### 3.2 "Partial" definition
`recalc_overall()` (`med_confirm.py:165-178`) counts only `required` drugs; `partial` = some-but-not-all required taken. `b_complex` is `required:false` so excluded from completion math but still stamped by slot-confirm (see Doc 2, finding C-1).

### 3.3 Chain dependency math
`calculate_ready_time()` (`chain_calc.py:397-441`) computes each slot's next ready time as `prior_slot.actual_intake + fixed_gap` (gaps in `chain_calc.py:35-41`). `chain_times` is populated only from **confirmed/partial** slots (`chain_calc.py:454-463`). **If a predecessor slot is still pending (no actual time), downstream slots fall back to static defaults** — so the "if A is late, everything shifts" promise breaks exactly when the chain is most broken (finding C-6).

`get_actual_time()` (`chain_calc.py:362-383`) returns the **latest** taken time despite a docstring claiming "earliest" — internally consistent for gap math, but a maintenance hazard (finding C-5).

### 3.4 Taper engine
`dexa_taper.json` carries 21 phases (id 1–21), each with `total_mg`, `freq` (TDS/BD/OD/STOP), per-slot `dose_*` and `times[]`. Current = **Phase 5** (2026-07-01 → 2026-07-14, TDS, 5/5/4 = 14mg) (`dexa_taper.json:83-97`). `taper_alert.py` detects phase end within `ALERT_DAYS=3` (`taper_alert.py:24,165-195`). Slot→dexa mapping: `B→dose_morning, C→dose_midday, D→dose_afternoon` (`dexa_taper.json:367-371`).

### 3.5 State write matrix (scripts × JSON files)
| Script | med-status | med-schedule | chain-state | dexa_taper | med-supply | med-interactions | substitutions | appointments |
|---|---|---|---|---|---|---|---|---|
| med_confirm.py | **R+W** (`:94-95`) | R | — | — | W (`:228-231`) | — | — | — |
| chain_calc.py | R | R | **R+W** (`:136-139`) | R | — | — | — | — |
| chain_monitor.sh | — | — | **R+W** (`:79`, no backup) | — | — | — | — | — |
| chain_llm.py | — | — | R (via chain_calc) | R | — | — | — | — |
| med_resolve.py | — | R | — | — | — | — | — | — |
| med_supply.py | — | — | — | — | **R+W** (`:39-40`) | — | — | — |
| med_report.py | R | R | — | R | R | — | — | — |
| med_interact.py | — | R | — | — | — | R | — | — |
| med_substitute.py | — | — | — | — | — | — | R | — |
| med_appointments.py | — | — | — | R | — | — | — | **R+W** (`:37-38`) |
| taper_alert.py | — | — | — | R | R | — | — | — |

**Atomicity:** NONE of the writers use a tempfile + atomic `os.replace`. Every write is in-place `open(path,'w')` / `write_text`. Only `med_confirm.py` rotates `.bak1→.bak3` (`:84-92`). `chain_monitor.sh` (the hottest writer, every 15 min) writes `chain-state.json` with **no backup and no atomicity** (`:79`).

---

## 4. Subsystem B — Cron layer (`cron/jobs.json`)

14 jobs (per the snapshot `jobs.json`; RUNBOOK lists 28 but the snapshot's `jobs.json` defines 14 — see Doc 2 finding X-JOB-1 on inventory drift). Key jobs:

| Job | Schedule | Command | no_agent | deliver |
|---|---|---|---|---|
| Morning Briefing | `0 7 * * *` | agent prompt | false | whatsapp |
| Evening Check-in | `0 21 * * *` | agent prompt | false | whatsapp |
| Daily Usage Report | `0 8 * * *` | agent prompt | false | telegram |
| Goal Check-in | `0 20 * * 1,3,5` | agent prompt | false | whatsapp |
| Weekly Review | `0 10 * * 0` | agent prompt | false | telegram |
| Daily Health | `0 9 * * *` | agent prompt | false | telegram |
| DeepSeek Balance Check | `0 9 * * 1,5` | agent prompt | false | telegram |
| Log Rotate | `0 6 * * 0` | `logrotate-run.sh` | true | local |
| **Domino Chain Monitor** | `*/15 5-22 * * *` | `chain_monitor.sh` | true | **whatsapp:120363428305511789** |
| hello-world-watch | every 1m | `hello_watch.py` | true | **whatsapp:120363428305511789** |
| Dexa Taper Alert | `0 6 * * *` | `taper_alert.py` | true | whatsapp |
| Weekly Med Compliance | `0 10 * * 0` | `med_report.py` | true | whatsapp |
| Appointment Reminder | `0 20 * * *` | `med_appointments.py` | true | whatsapp |
| Memory Watchdog | `0 9 * * *` | `memory_watch.py` | true | telegram |

**Good news:** No `deliver:"origin"` strings exist (the Pattern C bug from the brief is **already fixed** — every med cron uses an explicit `whatsapp:120363428305511789` target).

**Cross-ref:** `channel_directory.json:45` confirms `120363428305511789@g.us` is the medical WhatsApp **group**; `13186321408227@lid` (`:15`) is the home DM. The `hello-world-watch` beacon delivers to the **group**, not the DM (finding X-ROUTE-1).

---

## 5. Subsystem C — Persona, skills, hooks

- **`SOUL.md`** — MarryJane persona; instructs the agent to read+load+delete `triggered_skills.txt` each turn (`:123-131`).
- **`skill-trigger` hook** (`HOOK.yaml:1-5`, `handler.py:22-45`) — fires on `agent:start`; regex→skill map writes `triggered_skills.txt`. **Fails open** (errors swallowed, `handler.py:88-93`).
- **`med-tracker` skill** — drug_id mapping, taper engine, cooldown logic, confirmation CLI guidance; strict "no fabrication / always resolve before confirming" rules.
- **`anti-fabrication-guardrails`** — 3 layers: hook injects skill → SOUL instructs load → `med_resolve.py` rejects unknown drug names. **Advisory, not a hard gate** (finding X-FAB-1).
- **`malaysia-country-selector-interaction`** — NOT in the hook trigger map; only loaded if the agent voluntarily remembers (finding X-HOOK-1).

---

## 6. Config & providers (`config.yaml`)

- **Live chat:** `default: deepseek-v4-pro`, `provider: opencode-go`, `base_url: https://opencode.ai/zen/go/v1` (`config.yaml:2-4`).
- **`providers: {}`**, **`fallback_providers: []`** (`config.yaml:5-6`) — no fallback. A commented `fallback_model` block exists (`:740-761`) but is **not enabled**.
- **Cron model snapshot:** every job stores `provider_snapshot: "deepseek"` / `model_snapshot: "deepseek-v4-flash"` (`cron/jobs.json:11-12`) — a *different* tuple from live chat, and **unreferenced by any code** (finding X-MODEL-1).
- **Feature flags:** `security.redact_secrets: true`, `tirith_fail_open: true` (`:569-573`); `cron_mode: deny` (`:532-534`); `hooks_auto_accept: false` (`:565`); `computer_use.enabled: true` (`:695`); `plugins.enabled: [web-trafilatura, hybrid-web]` (`:697-699`).
- **No YAML anchors** — verified, nothing to decode.

---

## 7. State & persistence

- **JSON files** (see §3.5 matrix) — the live medication/chain/taper/supply state.
- **`state.db`** — 141 MB SQLite (sessions, durable memory). `sessions.auto_prune: false` (per PROGRESS/explorer note). No `vacuum` retention visible for it.
- **`cron/output/`** — accumulates a markdown file **per cron tick** (hello-world-watch alone = ~1 file/min). No cleanup cron (only `logrotate-run.sh` for logs) (finding X-MEM-1).
- **`whatsapp/session/creds.json`** — private Signal/WhatsApp identity keys. **No `.gitignore` anywhere in the tree** (finding S-SEC-2).

---

## 8. "Should do" vs "actually does" (gaps surfaced during mapping)

| Intended behavior (PRD / design) | Actual behavior (code) | Evidence |
|---|---|---|
| "If A is late, all slots shift" | Downstream slots fall back to static default when a predecessor is pending | `chain_calc.py:397-441`, `:454-463` |
| `med-schedule.json` is "single source of truth" | Dexa `dosage` is pinned to Phase 5 and goes **stale** at taper transition (2026-07-14); only `dexa_taper.json` is authoritative | `med-schedule.json:26,38,53` vs `dexa_taper.json` |
| Supply tracking warns when low | 7/10 drugs have `current: null`; common `confirm_slot` path doesn't decrement → net no tracking | `med-supply.json:54,59,66,77,98,109` |
| Anti-fabrication is a hard gate | It's advisory (SOUL instruction + tool rejection); hook fails open | `anti-fabrication-guardrails/SKILL.md`, `handler.py:88-93` |
| DeepSeek is the only paid brain, no paid fallbacks | Live uses `opencode-go`, `fallback_providers: []` (commented-out only) | `config.yaml:2-6,740-761` |
| Secrets never committed | No `.gitignore`; WhatsApp creds on disk | `whatsapp/session/creds.json` + absent `.gitignore` |
| Gateway "broken" per med-tracker SKILL.md | `gateway_state.json` says running/connected; logs confirm | `SKILL.md:654` vs `gateway_state.json:1` |

---

## 9. Is `42crunch-api-security-testing` applicable? — **No.**

The task referenced the 42Crunch audit skill (REST/OpenAPI API security testing). I checked for an HTTP/REST/OpenAPI/webhook surface across `config.yaml` and the scripts:

- `config.yaml` contains **only outbound API URLs** (`opencode.ai/zen/...`, `portal.nousresearch.com`, `hermes-agent.nousresearch.com/...`). No `flask`/`fastapi`/`express`/`webhook`/`/api/`/`openapi`/`swagger` server definitions. `gateway.api_server.max_concurrent_runs: 10` (`:618-619`) is an internal run limiter, not an exposed route.
- The **only** HTTP listener in the tree is `skills/agent-methodology/brainstorming/scripts/server.cjs` — a localhost, cookie-gated dev server bundled with a skill, **not** the Hermes gateway and not exposed beyond localhost.

**Verdict:** The Hermes gateway exposes **no API surface** to audit with 42Crunch. The skill does not apply to this system. (It would only become relevant if that brainstorming dev server were ever exposed beyond localhost — out of scope.) I did not force-fit it. Security findings in this audit are instead about **secret hygiene / .gitignore / credential-on-disk** (see Doc 2, S-SEC-*), which 42Crunch would not have covered anyway.

---

## 10. Open questions / confusions (documented, not diagnosed)

1. **TZ of the cron scheduler.** `config.yaml` sets `timezone: Asia/Kuala_Lumpur` (`:481`) and `chain_calc.py` uses `ZoneInfo('Asia/Kuala_Lumpur')`, but the **cron scheduler's effective TZ** is not in the snapshot. `chain-state.json` timestamps *suggest* MYT, but this is UNVERIFIED. If the host is UTC, every med reminder fires 8h off (finding X-TZ-1).
2. **`last_reminder_times` uses naive `datetime.now()`** in `chain_monitor.sh:76-77`, while the reader uses MYT — a TZ mismatch bug independent of the host TZ question (finding C-11).
3. **BD-phase 2pm dexa dose has no slot** — `dexa_taper.json` carries `dose_2pm` for BD phases (phase 10+, from 2026-09-09) but med-schedule/chain only model A–E, so the 2pm dose is never surfaced (finding S-DRIFT-2).
4. **`chain-state.json` counts not date-keyed** — accumulate across days (finding C-4).
5. **Legacy vs drug-level `med-status.json` shape drift** — different dates use different formats; no canonical enforced (explorer note §7).
6. **`b_complex` stamped on non-Wed/Sat days** — `confirm_slot C` marks it taken regardless of `condition:"Rabu & Sabtu SAHAJA"` (explorer note).

---

## 11. Appendix — file inventory audited (all present in snapshot)

Data (13): `config.yaml`, `med-schedule.json`, `med-status.json` (+.bak1-3), `chain-state.json`, `dexa_taper.json`, `med-supply.json`, `med-interactions.json`, `substitutions.json`, `appointments.json`, `SOUL.md`, `gateway_state.json`, `channel_directory.json`, `cron/jobs.json`.
Scripts (13): `med_confirm.py`, `chain_calc.py`, `chain_monitor.sh`, `chain_llm.py`, `med_resolve.py`, `med_supply.py`, `med_report.py`, `med_interact.py`, `med_substitute.py`, `med_appointments.py`, `taper_alert.py`, `hello_watch.py`, `memory_watch.py`.
Skills/hooks: `skills/med-tracker/`, `skills/software-development/anti-fabrication-guardrails/`, `skills/software-development/malaysia-country-selector-interaction/`, `hooks/skill-trigger/`.
Governance (read for Doc 3 only): `MJay/{PRD,PROGRESS,DECISIONS,RUNBOOK}.md`.

*End of Audit 01. See `2026-07-05-zcode-audit-02-findings.md` for the issue list and `2026-07-05-zcode-audit-03-execution-plan.md` for the fix plan.*
