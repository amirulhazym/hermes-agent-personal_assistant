# Chain Reminder Engine — Architecture, Pitfalls & Debugging

Covers the Domino Chain reminder subsystem: `chain_calc.py` (state/timing decisions),
`chain_llm.py` (text generation), `chain_monitor.sh` (cron entry point),
`chain-state.json` (reminder counts / cooldowns).

## Delivery path (verified 2026-08-02)

- Cron job "Domino Chain Medication Monitor" (no_agent, `*/15 5-22 * * *`,
  script `chain_monitor.sh`, deliver whatsapp).
- `chain_monitor.sh` → `chain_calc.py --next` (should_fire decision) →
  `chain_llm.py <SLOT>` for text → stdout = delivered verbatim.
- `chain_llm.py main()` uses ONLY the deterministic `render_reminder()`; it NEVER
  calls `call_llm()`. => BOTH the LLM path (`build_user_prompt`/`call_llm`) AND the
  per-count escalation templates in `chain_calc.generate_reminder()` are NOT in the
  delivery path (dead code as of 2026-08). Editing them has zero delivery effect.
  If you want escalating/changing text, edit `render_reminder()`.
- Delivered text (P1+P2 fix, 2026-08-02) has FOUR shapes:
  (1) heads-up: "belum due lagi — boleh ambil lepas <ready_time>. Tunggu sampai
  waktu tu ya, nanti saya ingatkan balik."; (2) gentle due (#1-2): "belum ambil
  lagi. Dah pukul <now>, update bila dah ambil."; (3) push due (#3-4): "ini kali
  ke-N saya ingatkan — ... masih belum ambil ... jangan lupa ya, update lepas
  makan."; (4) urgent due (#5+): "Hai boss!! ... dah N kali saya ingatkan ...
  ambil sekarang dan update saya." Tier is derived from the reminder count.

## Heads-up vs due — the 2026-08-02 incident root cause

- `is_scheduled_heads_up()` (chain_calc.py) fires when the slot's CONFIGURED time
  (med-schedule.json, e.g. B=08:00) has arrived but the DYNAMIC ready time
  (gap-based: A+1h → 09:10) hasn't matured. Legitimate concept ("your usual time is
  here, but wait for the gap") — but the rendered text must say that.
- `render_reminder()` has NO heads-up branch, so it emits the OVERDUE template
  ("belum ambil lagi. Dah pukul X, update bila dah ambil") for a slot that is NOT
  due — telling the user to take a med before the minimum gap matured.
- Incident: A confirmed 08:10 (chat reply said "B bolehlah lepas ~09:10"), then the
  08:16 cron tick fired the heads-up: "B belum ambil lagi. Dah pukul 08:15". Direct
  self-contradiction 55 min before B was ready. Followed literally, the user takes B
  6 min after A — violating the 1-hour gap rule the chain exists to enforce.
- RULE (now enforced): a heads-up reminder must communicate "target time dah
  sampai, tapi kena tunggu sampai <ready_time>" — never "belum ambil, update bila
  dah ambil". render_reminder() branches on `now < ready_time`.
- FIXED 2026-08-02 (P1): `is_scheduled_heads_up()` only returns True inside
  `HEADS_UP_WINDOW_MIN = 30` minutes before ready_time, AND the fire loop gates the
  heads-up branch to fire AT MOST ONCE per slot per day (`reminder_counts[slot] > 0`
  → skip). So a slot pushed late by a gap never nags early, and the 30-min window
  never double-sends the same heads-up. Verified: frozen-time repro + e2e monitor
  dry-run (08:16 silent → 08:40 heads-up #1 → 08:55 silent → 09:10 due #2 gentle →
  09:25 due #3 push).

## Frequency is a feature — user preference (2026-08-02)

- User WANTS frequent reminders until he confirms intake. NEVER propose removing or
  capping frequency, nor quiet-hours for day/evening/night windows.
- Morning-asleep spam (e.g. 6 identical messages 06:00–08:00 while asleep) is
  ACCEPTED by the user as unavoidable — don't push fixes there unless he asks.
- The real defect when messages look spammy is IDENTICAL TEXT: escalation
  (gentle → push → urgent → critical) is designed but never delivered. Fix direction
  = count-aware escalating text in `render_reminder()`, not fewer messages.

## Cooldown / escalation facts (chain_calc.py)

- `COOLDOWN_INTERVAL`: count 1–2 → 15 min; count 3–6 (urgent) → 30 min; count 7+
  (critical) → 15 min. Partial slots → 120 min flat.
- Observed morning pattern 2026-08-02 (A unconfirmed until 08:10): fired 06:00,
  06:15, 06:30, 07:00, 07:30, 08:00; silent 06:45/07:15/07:45. Six messages in 2h
  is DESIGNED behaviour, not a bug — do not "fix" it without user approval.

## Debugging techniques

1. **Frozen-time simulation**: `CHAIN_CALC_NOW_MYT=2026-08-02T08:16:00+08:00 python3
   chain_calc.py --next` freezes `now_myt()`. BUT `chain_calc` reads chain-state.json
   via a module-level `STATE_FILE` const — to simulate PRE-reminder state, import
   chain_calc, monkeypatch `chain_calc.STATE_FILE = Path('/tmp/test-state.json')`
   with a stripped copy (`reminder_counts={}`), then call `calculate_chain()`.
   (Setting `os.environ['STATE_FILE']` does NOT work — the const is bound at import.)
2. **Cron evidence trail**: `~/.hermes/cron/output/<job_id>/YYYY-MM-DD_HH-MM-SS.md`.
   Fired runs contain the delivered reminder text; silent runs are 166-byte files
   with "Status: silent (empty output)". Size heuristic: fired ≈ 295+ bytes, silent
   = 166. This reconstructs the exact firing timeline (the monitor job id is
   `c97c00f2fb46`).
3. **Reminder text = what fired**: the no_agent cron's stdout IS the delivered
   message — no separate delivery log needed for the monitor.
4. **chain-state.json only shows current counts**: chain_monitor housekeeping clears
   a slot's reminder counts once it is effectively done. To reconstruct history, use
   cron output files, not chain-state.

## P1+P2 fix — IMPLEMENTED & VERIFIED (2026-08-02)

- P1 (heads-up): `HEADS_UP_WINDOW_MIN=30` window in `is_scheduled_heads_up()` +
  once-per-day gate in the fire loop + heads-up branch in `render_reminder()`
  (wording "belum due lagi — boleh ambil lepas <ready>", never "belum ambil lagi").
- P2 (escalation): `ESCALATION_WORDING` tiers gentle/push/urgent wired into
  `render_reminder()` via reminder count (#1-2 / #3-4 / #5+). Deterministic; all
  tiers pass `validate_reminder_text()`'s 3-line contract.
- Tests: `test_chain_llm.py` (heads-up render + gentle/push/urgent wording),
  `test_chain_adapter.py` (B silent 54 min before ready / fires at ready-30 /
  fires once then quiet until due), `test_chain_monitor.py`. 29 chain + 30
  med_chain tests green.
- Backups: `chain_calc.py.bak3`, `chain_llm.py.bak3` (pre-fix). Cron
  `c97c00f2fb46` picks the fix up automatically — every tick is a fresh process
  reading the patched files; no restart/deploy step.
