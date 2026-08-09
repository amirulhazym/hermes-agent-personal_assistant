# Domino Chain Medication System — Architecture (v3)

## Overview

Replaces 20 individual cron jobs (5 meds × 1 initial + 3 follow-ups) with a single state-aware cron job that fires every 15 minutes and knows exactly when to remind based on actual intake times. V3 adds taper engine, supply tracking, interaction checking, and dynamic slot management.

## Components

```
┌─────────────────────────────────────────────────────────┐
│                    DATA LAYER                            │
│                                                          │
│  med-schedule.json  ─── Rules & drug info (static)       │
│  med-status.json    ─── Actual intake log (written by    │
│                         user confirmation)               │
│  chain-state.json   ─── Reminder counts & escalation     │
│                         (written by cron script)         │
│  dexa_taper.json    ─── Date-dependent dexa dosing       │
│  med-supply.json    ─── Pill inventory per drug          │
│  substitutions.json ─── Drug alternatives                │
│  med-interactions.json ─── Drug interaction safety       │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   ENGINE LAYER                           │
│                                                          │
│  chain_calc.py     ─── Core logic:                      │
│                         ・Read schedule + status         │
│                         ・Read taper schedule            │
│                         ・Calculate chain ready times    │
│                         ・Dynamic slot management        │
│                         ・Generate contextual reminders  │
│                         ・Output chain display           │
│                         ・Taper-aware dose display       │
└─────────────────────────┬───────────────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            │                           │
            ▼                           ▼
┌─────────────────────┐   ┌─────────────────────────────┐
│   CRON LAYER        │   │    CHAT LAYER               │
│                     │   │                             │
│ chain_monitor.sh    │   │ med_confirm.py              │
│ no_agent cron       │   │ (called by Jane when user   │
│ Every 15 min        │   │  confirms via chat)         │
│ Reads chain state   │   │                             │
│ Fires reminders     │   │ Logs actual time            │
│ Escalates tone      │   │ Resets reminder count       │
│                     │   │ Auto-decrements supply      │
│ taper_alert.py      │   │                             │
│ Daily 06:00         │   │ med_resolve.py              │
│ Alerts on dose      │   │ (drug name resolver)        │
│ changes             │   │                             │
└─────────────────────┘   │ med_supply.py               │
                          │ (supply CLI)                │
                          │                             │
                          │ med_substitute.py           │
                          │ (substitution query)        │
                          │                             │
                          │ med_interact.py             │
                          │ (interaction checker)       │
                          │                             │
                          │ med_report.py               │
                          │ (weekly compliance report)  │
                          └─────────────────────────────┘
```

## Cron Schedule

- **Schedule:** `*/15 5-22 * * *`
- **Mode:** no_agent (script output = message delivered to user)
- **No LLM calls** — all logic is pure Python/bash
- **Silent when nothing to say** — empty stdout = nothing delivered

## Chain Logic (Gap Rules)

```
A → [1h] → B → [4h] → C → [4h] → D → [? gap to E] → E
                 ↘               ↗
              [12h] --- Levetiracetam ---
```

| Gap | Duration | Reason |
|-----|----------|--------|
| A→B | 1 hour | Food settling time after Akurit-4 (perut kosong), before Levetiracetam |
| B→C | 4 hours | Dexamethasone spacing |
| C→D | 4 hours | Dexamethasone spacing |
| B→E | 12 hours | Levetiracetam twice-daily coverage |

When a med is confirmed at time T, downstream ready times automatically shift:
- B_ready = A_actual + 1h (or B_default 08:00, whichever is later)
- C_ready = B_actual + 4h (or C_default 12:00)
- D_ready = C_actual + 4h (or D_default 16:00)
- E_ready = B_actual + 12h (or E_default 20:00)

## Escalation Levels

Tone escalates every 15 minutes if unconfirmed:

| Level | Count | Tone |
|-------|-------|------|
| Normal | 0 | Friendly, informative. Includes drug info, timing context |
| Gentle | 1 | Mild nudge. "belum ambil lagi?" Mentions consequences |
| Push | 2 | Direct. "Dah 3x tanya." Time pressure |
| Urgent | 3-4 | "Dah pukul X." Cumulative delay, chain disruption |
| Critical | 5+ | "⚠️ CRITICAL." Desperate. Explains health consequences |

Slot A and E have the most critical escalation path because forgetting A = entire day disrupted, forgetting E = anticonvulsant gap.

## Templates Per Slot

Each slot (A-E) has unique templates that reference:
- Drug names and dosages (from med-schedule.json)
- Previous med time (e.g., "A tadi 08:15 ✅")
- Ready time for current slot
- Chain disruption consequences
- Time of day context (pagi/lunch/mlm)

See chain_calc.py generate_reminder() function for full template definitions.

## Confirmation Flow (via Chat)

```
User: "dah makan A"
   ↓
Jane detects via med-tracker skill
   ↓
Jane runs: med_confirm.py A --at HH:MM
   → Writes to med-status.json
   ↓
Jane runs: chain_calc.py --update A
   → Resets reminder count in chain-state.json
   → Cron stops pestering about A
   ↓
Jane runs: chain_calc.py --display
   → Shows adjusted chain: "A ✓ 08:15 → B ~09:15 → C ~13:15..."
   ↓
Jane responds with: ✅ A at 08:15 + chain display
```

## Time Windows

Reminders only fire between 05:00–22:00 MYT (cron schedule + code guard).

- Before 05:00: Silent (sleep time)
- 05:00–22:00: Active (every 15 min)
- After 22:00: Silent (wind down)

Within active hours, reminders only fire when a slot is READY (now >= calculated ready_time).

## Files

| File | Path | Role |
|------|------|------|
| Schedule | `~/.hermes/med-schedule.json` | Static rules for all meds |
| Status log | `~/.hermes/med-status.json` | Daily intake log with actual times |
| Chain state | `~/.hermes/chain-state.json` | Reminder counts, escalation, cooldown |
| **Taper schedule** | `~/.hermes/dexa_taper.json` | **Date-dependent dexa dosing (21 phases)** |
| **Supply tracker** | `~/.hermes/med-supply.json` | **Pill inventory, auto-decrement** |
| **Substitution DB** | `~/.hermes/substitutions.json` | **Drug alternatives** |
| **Interaction DB** | `~/.hermes/med-interactions.json` | **Drug interaction safety** |
| Engine | `~/.hermes/scripts/chain_calc.py` | Core logic + taper engine + templates |
| Cron script | `~/.hermes/scripts/chain_monitor.sh` | no_agent cron worker |
| **Taper alert** | `~/.hermes/scripts/taper_alert.py` | **Daily 06:00, dose change alerts** |
| CLI tool | `~/.hermes/scripts/med_confirm.py` | Manual confirmation + auto-decrement |
| **Drug resolver** | `~/.hermes/scripts/med_resolve.py` | **Drug name → drug_id resolver** |
| **Supply CLI** | `~/.hermes/scripts/med_supply.py` | **Check/refill/set supply** |
| **Substitute CLI** | `~/.hermes/scripts/med_substitute.py` | **Query alternatives** |
| **Interaction CLI** | `~/.hermes/scripts/med_interact.py` | **Check pair / validate regimen** |
| **Report** | `~/.hermes/scripts/med_report.py` | **Weekly compliance report** |
