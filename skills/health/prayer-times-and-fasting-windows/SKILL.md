---
name: prayer-times-and-fasting-windows
description: Use when asked berbuka/iftar or prayer times.
metadata:
  hermes:
    tags: [prayer-times, fasting, IF, malaysia, jakim]
    category: health
    related_skills: [diet-tracker, health-log-state-verification, diet-food-verdicts]
---

# Prayer Times & Fasting Windows

Scope: any question shaped like "pukul berapa waktu berbuka aku", "maghrib hari ni", "dah berapa jam aku puasa", "bila boleh makan".

Two different things must be kept apart:

1. **Official prayer time** (maghrib / imsak / fajr) — JAKIM is the external authority.
2. **His own eating-window boundary** (buka IF) — derived from the `diet-log.json` anchor plus his 17–19 h band. JAKIM maghrib is *not* his buka time unless he says so.

`diet-tracker` (user-owned) owns meal logging and the 5-category report. `health-log-state-verification` owns state/write integrity. **This skill owns time resolution.**

## 1. Disambiguate "berbuka" before answering

- **IF berbuka** (the normal case — his fast is 17–19 h, broken in the afternoon) → anchor arithmetic in §3.
- **Ramadan iftar** → maghrib.

Do not assume Ramadan. The API returns the Hijri date in the same payload — read it. Verified 2026-11-13: `hijri: "1448-06-03"` (Jamadilakhir, non-Ramadan), so berbuka meant IF break and maghrib 18:58 was only a fallback option, never the answer.

## 2. Official times — JAKIM e-solat API (VERIFIED 2026-11-13)

```
https://www.e-solat.gov.my/index.php?r=esolatApi/takwimsolat&period=today&zone=SGR01
```

Plain GET with a browser User-Agent returns JSON:

```json
{"prayerTime":[{"hijri":"1448-06-03","date":"13-Nov-2026","day":"Friday",
 "imsak":"05:38:00","fajr":"05:48:00","syuruk":"06:56:00","dhuha":"07:21:00",
 "dhuhr":"13:00:00","asr":"16:22:00","maghrib":"18:58:00","isha":"20:11:00"}],
 "status":"OK!","serverTime":"2026-11-13 15:10:48","zone":"SGR01"}
```

Run `scripts/prayer_times.py --zone SGR01` rather than hand-writing the URL.

- **Puchong = zone `SGR01`** (Selangor / Petaling). Verified working.
- Do NOT guess other zone codes — look them up on e-solat's zone list. A wrong zone returns a confidently wrong maghrib.
- No region gate: the endpoint answered fine from a Singapore-hosted VPS. Still print the zone in the answer so he can sanity-check it.
- Only `period=today` is verified in-session. The UI also uses `period=date|month|year` with `&date=DD-MM-YYYY`; treat those as **UNTESTED** until you actually see a response.

## 3. His buka time — anchor arithmetic, not a fixed clock

His IF break is not a scheduled hour; it moves with yesterday's last intake.

1. Read `~/.hermes/diet-log.json` → the most recent day carrying `last_intake_time` (or the last timestamped `meal_items` / `meals` entry). That timestamp is the anchor.
   **The field is prose, not a timestamp.** Recent days carry strings like `"~20:07 (masa mesej; boss: \"that's all for today\")"` (14 Nov) and `"~20:00 (julat 19:50-20:00, anggaran boss)"` (13 Nov). Regex the leading `HH:MM`, keep the `~` as an uncertainty label, and quote the raw string in the reply so he can correct the anchor. `datetime.strptime` on the field directly raises on the `~` and the parenthetical.
2. Compute the band **with a tool**, never mentally: anchor + 17 h / 18 h / 19 h.
3. Report elapsed-from-anchor to now, and say explicitly when he is already past the 19 h ceiling.
4. Compare against his own recent pattern (10 Nov 15:13 · 11 Nov 14:55 · 12 Nov 14:00) to say whether today is early or late *for him*.

### 3b. The anchor must be a FOOD time — a medication timestamp is never an anchor (2026-11-19)

`last_intake_time` is written by an agent, so it can carry *two* clocks in one sentence and only one of
them is food. Real string that broke an answer: `"~20:50 (window 2; boss: letram malam 8.50pm + makan
window 2 masa sama)"`. I used 20:50 as the anchor and told him the 19 h ceiling was 15:50. He replied
**"wtf, kau kira daripada letram ke?? … aku makan window 2 jam 7.50pm"** — the food was **19:50**, the
20:50 was the levetiracetam. Correct ceiling: **14:50**, a full hour earlier. Verdict happened to stay
the same (inside band either way), but the numbers he checked were off by 60 min.

Before computing from `last_intake_time`:

1. **Read the parenthetical.** If it names a drug (`letram`, `dexa`, `cc`, `akurit`), the time is a med
   time or a med/food mash-up → not usable as-is.
2. **Cross-check the food rows** — `logs[DATE]['meal_items']` entries with a `time` field, and the
   `meals[]` prose lines ("Buka IF (15:00): …", "Window 2 (~19:50): …"). Those are the food record.
3. **If the two disagree or the food rows inherit the med time**, say so and ask one question ("window 2
   habis pukul berapa? makanan, bukan ubat") before quoting a band. Do not silently pick either.
4. **When he corrects the anchor, repair the entry** — backup `diet-log.json`, rewrite every window-2
   `meal_items[].time`, the `meals[]` string, `last_intake_time`, `eating_window_today`, `status`, add a
   `CORRECTION` line to `data_quality` and a `corrections[]` entry, then read back. kcal/macros do not
   change when only the clock was wrong — say that explicitly so he knows the totals were not re-priced.
5. **Never write a med timestamp into `last_intake_time` again.** Med time goes in `med-status.json`; the
   food anchor carries only food. A same-minute coincidence ("letram + makan serentak") is still written as
   the food line, with the drug omitted.

### 3c. "Ubat reset IF tak?" — no, only calories do

Levetiracetam / dexamethasone / Akurit / Calcium+Calcitriol tablets are not intake events for fasting
purposes: practical energy ≈ 0, no meaningful insulin response, so they neither break nor reset the window.
State the boundary that matters — the fast breaks on **calories and macros**: milk, juice, sugary kopi/milo,
or "makan sikit". Answer in one short paragraph; do not turn it into a dosing lecture, since the meds are
prescribed and not optional.

Do NOT: invent a log entry or portion for a day with no entry; present maghrib as "his berbuka" in a non-Ramadan month; recommend stretching to maghrib (23 h+) — his band caps at 19 h and extra fast length is not extra deficit.

Answer shape — DEFAULT IS SHORT (owner correction 2026-11-24):

```
verdict + elapsed in one line -> one line: CC lepas makan, then log Window 1
```

Example: `Boleh berbuka sekarang — 17j 27m dari 19:40 semalam. CC lepas makan, then log Window 1.`

That is the whole answer. Do NOT emit the 16/17/18/19 h table, the median/max stats, the record
comparison, a trailing question, or a tool/command name by default — the 2026-11-24 A/B test showed
that shape produced 648-char/15-line answers for a one-line question.

Expand ONLY when he asks for it explicitly: "option", "julat", "waktu-waktu", "berapa lama lagi",
"kenapa", or when a value is genuinely uncertain (then quote the anchor and the uncertainty, 2 lines).
Ceiling even then: ≤700 chars, no tables.

### 3d. The Slot C reminder IS the berbuka reminder (OD phase) — 2026-11-20

Once the midday Dexa is tapered off (`dexa_taper.json` freq `OD`), Slot C holds **CC only**
(Calcium Carbonate + Calcitriol) and must be taken with food. Its reminder therefore belongs at the
fasting break — and the break hour must be **computed from the log, never assumed**.

Owner reaction when I proposed suppressing CC "until 19:00": **"kau tahu je kan IF tu puasa apa?
bila masa aku berbuka jam 19:00?"** That hour was my invention; do not repeat it in a fix, a plan,
or a hypothetical.

Distribution computed from `diet-log.json.fasting_hours` (20 Nov 2026, n=26):
min **17.03 h**, median **18.60 h**, mean 18.56 h, max 20.05 h, stdev 0.91 → with the 19 Nov 19:40
anchor: 17 h floor **12:41**, median target **14:16** (actual buka 13–19 Nov: 14:00–15:13).

### Owner-locked final spec (2026-11-20, after three correction rounds — do not re-decide these)

- ~~Trigger = the 17 h floor (anchor + min), NOT the median.~~ **SUPERSEDED 2026-11-23 — see §3f.**
  Thresholds are now constants (`MIN_FLOOR_H 16.0`, `TARGET_H 17.0`, `HEADS_UP_LEAD_H 2.0`); the single
  merged alert fires 2 h before the 17 h optimum, and the median is context only.
- **Header is exactly `‼️ Waktu Berbuka IF & CC ‼️`** — no "Waktu Ubat (…)" wrapper, no "Ubat CC"
  (owner: "instead of 'ubat cc' just tulis as 'CC'"). Validator must accept this exact line.
- **Body is an ALERT, not a nag**: elapsed fast hours since yesterday's last-food time → ready berbuka
  IF → ready to take CC after eating → "key in/log apa yang kau makan untuk Window 1". Never ship the
  generic "belum due lagi — tunggu sampai waktu tu" heads-up for this slot: the 14:00 cron tick
  delivered that at 18.4 h fast and drew "Apabenda reminder kau macam ni??".
- **Silent before the floor**: the chain opens its fire window 15 min before ready_time; a pre-17h
  alert would claim 17h at ~16.8h. `chain_llm._berbuka_ready_gate()` returns silent (exit 0, no state
  write) until now ≥ ready_time. Applies only to C-with-zero-Dexa; other slots untouched.
- **Repeat semantics unchanged**: reminder keeps firing every cooldown while CC is unconfirmed;
  only header/text changed, purpose (log CC) identical. Owner confirmed this explicitly.

Three files must agree, or the text contradicts the timing:

1. `~/.hermes/scripts/if_berbuka.py` — `berbuka_plan()` / `berbuka_target_hhmm()`. Reads the last
   **food** anchor (`last_intake_time`, §3b rules); `target` = anchor + **min** (17 h floor),
   `median_target` kept separately as context. Returns `None` when the anchor is older than yesterday
   (`basis_stale`) so callers fall back instead of nagging from an old meal.
2. `chain_calc.calculate_ready_time()` — for slot `C`, if `get_dexa_dose('C') == 0` return the berbuka
   target; otherwise fall through to normal chain math (`B + 4 h`). Guarded by try/except → fallback.
3. `chain_llm.render_reminder()` — `berbuka_mode` branch: custom header (above), body built from the
   plan (elapsed hours + last-food time + CC + log Window 1), escalation tiers 1/2/3+ reworded for
   berbuka. `validate_reminder_text()` demands exactly 3 non-empty lines and a body that **starts**
   with the salutation (`Hai boss` …); it was extended to accept the exact berbuka header line.
   `_berbuka_ready_gate()` in `main()` enforces the pre-floor silence.

Verify without touching live state: `python3 chain_calc.py --display` (C should show the 17h-floor
time), and call `render_reminder()` directly with a monkeypatched `now` + `reminder_counts`.
`python3 chain_calc.py --template --slot C` fails with `Invalid slot: --SLOT` — import the module instead.

### 3e. The "16 h minimum" question — physiology vs policy (2026-11-22; policy changed 2026-11-23)

He asked twice in one afternoon: *"Kalau berbuka sekarang, IF aku menjadi tak?"* then *"bukan minimum
sebenar IF adalah 16 jam ke?"*. Answer shape: **verdict → what his own data says → physiology as a
gradient → the mechanical consequence** — never reassurance, never a lecture.

- **Policy is a constant; data is only context (changed 2026-11-23, §3f).** Until 22 Nov the floor was
  `min(fasting_hours)` (= shortest logged fast). That meant one short day *became* the rule: the 22 Nov
  entry (15.67 h, its own note said "BAWAH floor 17j") dropped the floor to 15.67 h and the 23 Nov 13:45
  alert told him "ready berbuka" at 15.8 h — under his own 16 h minimum. He called it out hard: **"Wtf,
  how this can be approved?"** Nothing had approved it; a statistic did. Now `MIN_FLOOR_H 16.0` /
  `TARGET_H 17.0` are owner-locked constants and sub-floor days stay in the log as history only.
  When explaining to him, quote the distribution as context: 22 Nov n=28, `min_h 17.03` at the time,
  `median_h 18.41`, `max 20.05` — and say clearly that the numbers no longer set timing.
- **16:8 is convention, not a threshold.** No authority publishes a minimum IF duration; 16 h is simply
  the most common protocol shape (Hopkins / Cleveland Clinic describe it as a schedule, not a cutoff).
  Benefits ramp across roughly 12–18 h depending on last meal, activity and glycogen — a gradient with
  no switch at 16.
- **Evidence state, labelled honestly.** BMJ umbrella review (99 trials, 6,582 adults): all IF strategies
  ≈ continuous energy restriction for weight loss; IF not superior — so fast *length* is not the lever,
  the deficit is. Caveat that must travel with it: bmj.com served a Cloudflare interstitial and the full
  text could not be read, so this is **snippet-level**, not a read paper. Never upgrade it.
- **"Jadi tak?" is answered from his record, not from theory.** 22 Nov: 15.67 h (21:30 → 13:10) = the
  shortest fast in 28 logged days, every other day ≥17.03 h. Say that plainly, separate
  *record-discipline* from *physiology* (still a real fast), and add the Dexa-day caveat instead of
  moralising about fast length: on a Dexa day the **protein floor outranks extra hours** (111.6 g vs
  94.4 g floor mattered more than 1 h 25 m of fast).
- **Then give the arithmetic he actually wants**, tool-computed: 16 h floor → anchor + 16 h (21:30 →
  13:30), 17 h → 14:31. He is checking numbers, so quote both and say which floor each belongs to.

Worked case, script lines and source URLs: `references/if-minimum-16h-floor-20261122.md`.
Mechanism answer bank for the "did my IF work / insulin / fat burning" question (evidence labels,
protein-break handling, steroid confound): `references/if-mechanics-insulin-fat-oxidation.md`.

### 3f. Owner lock 2026-11-23: constants + ONE merged alert, 2 h early

He approved the constant floor and then changed the delivery shape himself:

- "Approve B" → clamp floor at 16 h, trigger at the **17 h optimum** (not the data minimum).
- Then: "alert tu kena keluar 2 jam awal sebelum waktu berbuka".
- Then: "Cannot be dua alert, satu alert je but combine/merge dua alert dalam satu. Sebabnya at the end,
  aku akan makan cc selepas berbuka IF juga."

So: **one message, fired 2 h before berbuka, carrying berbuka hour + CC + log-Window-1.** Two *wordings*
inside that one message, split by the clock — never two reminders, and never "ready" before the target:

| Clock (anchor 22:00) | Text shape |
|---|---|
| 13:00 (anchor + 15 h) | heads-up: "Berbuka optimum 17j pukul 15:00 — lagi X.Xj … Lepas berbuka/makan: <drugs>, then key in/log Window 1" |
| 15:00 (anchor + 17 h) | existing ready text: "dah ~17j puasa … Ready berbuka IF dan ready untuk <drugs> lepas makan" |

Implementation facts that must stay true:

1. `if_berbuka.py`: `MIN_FLOOR_H = 16.0`, `TARGET_H = 17.0`, `HEADS_UP_LEAD_H = 2.0`;
   `berbuka_plan()` returns `target` (17 h), `heads_up` (17 h − 2 h), `min_target` (16 h), plus the raw
   `stats` for display only. `berbuka_target_hhmm()` returns **`heads_up`** (that is the chain fire time).
2. `chain_llm.render_reminder()`: `pre_target` branch renders heads-up; at/after target it renders the
   ready text. Validator still needs exactly 3 non-empty lines, so the body stays ONE line containing the
   exact pending drug names + dosages.
3. `_berbuka_ready_gate()` now gates on the heads-up hour (12:30–12:59 ticks stay silent); silence
   writes nothing, so `chain_monitor.sh` never increments the count for a suppressed tick.
4. Sub-floor days remain in `diet-log.json` untouched — the log records what happened, the code owns policy.

**Testing trap:** `berbuka_plan()` reads the real clock, so calling `render_reminder()` with a fake
`chain['now']` still prints the *current* `fast_now_h` (e.g. 16.1 j at a fake 13:05). Monkeypatch the
module before rendering:

```python
real = if_berbuka.berbuka_plan
if_berbuka.berbuka_plan = lambda now=None, _f=fake_dt: real(_f)
```

Verified 2026-11-23: 13:05 → "baru ~15.1j … lagi 1.9j"; 15:05 → "dah ~17.1j … Ready berbuka";
validator True on both; gate False 12:30/12:59, True 13:00; `chain_calc.py --display` → `C ~13:00`.

### 3g. One command answers "pukul berapa aku patut berbuka" (2026-11-24)

`python3 ~/.hermes/scripts/if_berbuka.py --json` already returns the whole plan from the live anchor — no
mental arithmetic, no second script, no reading `diet-log.json` by hand:

```json
{"basis_date":"2026-11-23","basis_time":"19:40","basis_raw":"19:40 (boss: 'Last makan pukul 7.40pm')",
 "fast_now_h":17.46,"basis_stale":false,
 "min_target":"11:40","target":"12:40","heads_up":"10:40","median_target":"13:59"}
```

- `target` = 17 h optimum (the clock the reminder refers to)
- `min_target` = 16 h floor · `heads_up` = alert fire time (target − 2 h)
- `median_target` = context only, never the answer · `basis_stale` = anchor older than yesterday → fall back
- `already_broken` / `broken_at` = today's own log already proves the fast ended (window end or a food
  timestamp). When true, the answer is **"dah berbuka pukul HH:MM"**, never "boleh berbuka sekarang" —
  `target` in that case is a past clock, not an invitation. Fixed 2026-11-24 after the script told him
  "boleh berbuka sekarang" at 15:39 when Window 1 had been logged at 13:40.

Worked case: asked 24 Nov 13:07 MYT with the 23 Nov 19:40 anchor → `fast_now_h 17.46`, `target 12:40`
already **27 min past** → verdict "boleh berbuka sekarang", 19 h ceiling 14:40 quoted as the remaining band,
CC named as after-food.

Answer shape (per §3 default): **verdict + elapsed in one line → one line CC + log Window 1**. No clock
table, no stats, no tool name, no trailing question unless he asks for the windows. The 24 Nov 13:07 case
that inspired this section was answered with a 5-part structure and drew a complaint about length; the
short form is the fix, not a compromise.

`--check` is the reminder path (silent before target); use `--json` for a human question, `--check` only
when testing the reminder text itself.

## 4. After he confirms buka

- Log the meal per `diet-tracker` (user-owned) with the MAX-BOUND portion policy. Label any assumed quantity as **ANDAIAN**, give the basis, and ask only the one genuinely missing detail (e.g. how many slices).
- **Slot C (Calcium Carbonate + Calcitriol) rides the buka meal.** Check `med-status.json` → `meds.C['YYYY-MM-DD']`; if unlogged, remind. Never log it without his own words (compound-CC path in `health-log-state-verification` §2).
- "Baru nak makan cc" (= about to take it) is **future intent, not a confirmation** — remind with the layering order (nasi/lauk > ubat > sisa makanan) and wait for his completion word before writing.
- When the day's entry closes partial, say so in the entry itself (`status`, `pending`, `deficit_uniform.basis` labelled PARTIAL) — device active kcal at 15:00 is a snapshot, not the day's burn.

## Pitfalls

- Answering "berbuka" with maghrib in a non-Ramadan month.
- Assuming a fixed buka hour instead of reading the anchor from `diet-log.json`.
- Quoting a plausible berbuka clock hour inside a *proposal* ("suppress CC until 19:00"). Even as a
  hypothetical it reads as a fabricated fact — 2026-11-20 he answered "bila masa aku berbuka jam
  19:00?". State the derived target, or say the data isn't there yet.
- Shipping a berbuka reminder as a generic "belum due / tunggu" nag, or triggering at the median
  instead of the 17h floor, or keeping the "Waktu Ubat (…)" wrapper header. All three were corrected
  by the owner on 2026-11-20; the final spec is in §3d — implement it verbatim, don't re-derive it.
- Mental datetime arithmetic — use a tool and quote the anchor text (`12 Nov 19:50 → 13 Nov 15:10 = 19j 20m`).
- Skipping the anchor read because "he berbuka around the same time" — the last `last_intake_time` may itself be an estimate (`~`), and the answer inherits that. Say the qualifier out loud instead of rounding it to an exact minute.
- Reading the anchor from `meal_items` when `last_intake_time` exists: the meals array is often per-window and unordered by clock; the explicit field wins — **unless its parenthetical names a medication**, in which case §3b applies and the food rows decide.
- Anchoring on a time that came from a drug confirmation. 2026-11-19: anchor read `~20:50`, food was `19:50`; every derived time (17/18/19 h) shifted an hour and he caught it immediately. Ubat ≠ makanan, every time.
- Buka time disclosed *after the fact* is an estimate, not a log. 2026-11-16 he answered "dah berbuka around 3pm i think" when asked at 17:18 — compute from it, but label it "anggaran boss" in the reply and write `~15:00` (never `15:00`) into `diet-log.json.fasting_window` + `fasting_note`.
- Staggered eating: he may say "pemakanan aku ada penjarakkan masa yang bukan makan sekaligus". Then the buka hour is NOT the last intake — leave `last_intake_time` as `PENDING - boss belum nyatakan` and ask him for the last item's own time. Never reuse the buka hour as tomorrow's anchor.
- **Letting an observed statistic BE the policy threshold.** `min(fasting_hours)` turned one breach day
  (22 Nov, 15.67 h) into the floor, and the 23 Nov alert said "ready berbuka" at 15.8 h — under his own
  16 h minimum. Owner: "Wtf, how this can be approved?" Thresholds are owner-locked constants in code
  with the incident named in a comment; min/median are display context only (§3f).
- **Saying "ready berbuka" before the target clock**, even when the alert deliberately fires early. One
  merged alert, wording split by clock: heads-up ("pukul HH:MM — lagi X.Xj") before 17 h, ready after.
  Firing early with ready-wording is the same 15.8 h bug wearing a different shirt.
- Worked case 2026-11-15: anchor `14 Nov ~20:07` → 17j = 13:07 / 18j = 14:07 / 19j = 15:07; asked at 13:13 = 17j 06m, so "dah boleh buka" inside the band. Same payload: `zone=SGR01`, `hijri 1448-06-05` (non-Ramadan), maghrib 18:59 — quoted only as the Ramadan-only alternative, never as his buka time.
- Reading `med-status.json` at `data['YYYY-MM-DD']` → `{}`. Shape is `data['meds'][SLOT][DATE]`; an empty dict means **wrong path**, not "nothing logged".
- VPS `date` prints CST (Asia/Shanghai). Same +08 offset as MYT so HH:MM needs no conversion, but label the anchor line MYT — never cite raw CST output as MYT evidence.

## References

- `scripts/prayer_times.py` — fetch and print one zone's times (raw JSON + the fields that matter).
- `references/berbuka-time-20261113.md` — worked case: raw payload, computed windows, the reply actually sent.
- `references/berbuka-time-20261116.md` — worked case: buka time disclosed late as an estimate, staggered eating, entry left OPEN with PENDING anchor.
- `references/berbuka-anchor-med-vs-food-20261119.md` — worked case: anchor contaminated by a letram timestamp, the 1-hour error, the diet-log repair sequence and its read-back.
- `references/berbuka-reminder-derivation-20261120.md` — Slot C → berbuka reminder: the 20 Nov spec, the
  3-line message contract, dry-run recipes, **and the 2026-11-23 correction** (min(data) drift → owner
  constants 16/17, single merged 2 h-early alert).
- `references/if-minimum-16h-floor-20261122.md` — "isn't IF minimum 16 h?": the data-derived floor, the 28-day distribution, the BMJ evidence state and its Cloudflare caveat, plus the two replies actually sent.
- `references/if-mechanics-insulin-fat-oxidation.md` — answer bank for "did today's IF work, how about insulin / fat burning /
  autophagy": evidence-labelled mechanics, accidental-break handling, Dexa confound, and the numbers quoted on 2026-11-23.
