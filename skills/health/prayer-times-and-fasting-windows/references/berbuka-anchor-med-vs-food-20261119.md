# Berbuka anchor contaminated by a medication timestamp — 2026-11-19

## What was asked

14:46 — *"pukul berapa waktu berbuka aku harini?"*. Non-Ramadan (`hijri 1448-06-09`, Jamadilakhir),
zone SGR01, JAKIM maghrib 18:59 (quoted only as the puasa-sunat alternative, never as his buka time).

## What went wrong

The previous day's anchor was read straight off `diet-log.json`:

```json
"last_intake_time": "~20:50 (window 2; boss: letram malam 8.50pm + makan window 2 masa sama)"
```

Computed band: 17 h = 13:50 · 18 h = 14:50 · 19 h = 15:50, and the reply said "17j 56m, boleh buka".

His pushback, verbatim: **"wtf, kau kira daripada letram ke?? last aku key in makan window 2 semalam
jam berapa?? that's it. letram ni boleh membatalkan/reset IF ke?"**

Then, after I read the log back at him: **"salah tu, tu letram sahaja. salah aku tak mentioned betul
betul, aku makan window 2 jam 7.50pm"**.

The field's own parenthetical contained both clocks and I anchored on the wrong one. Root cause is the
wording I wrote on 18 Nov — the drug was listed first and the food second, with "masa sama" doing the
work of permission.

## Correct numbers

Anchor **18 Nov ~19:50** (his words: "aku makan window 2 jam 7.50pm"):

| band | time |
|---|---|
| 17 h | 12:50 |
| 18 h | 13:50 |
| 19 h | 14:50 (ceiling) |

At 14:53 → **19 j 03 m**, i.e. 3 min past his own ceiling. The earlier answer was a full hour off
(ceiling claimed 15:50). Verdict ("boleh buka") was unchanged only because he was inside the band under
both anchors — say that honestly instead of letting a correct verdict launder a wrong number.

## Repair actually run (read-back verified)

Backup first: `cp -p diet-log.json diet-log.json.bak-window2time-20261119-1452`.

Fields rewritten on `logs['2026-11-18']`:

1. all `meal_items[]` rows with `window: window_2` → `time: "~19:50"` (4 rows: telur 1 biji, ayam tomyam
   72 g, kubis bunga 40 g, minyak 1 tsp)
2. `meals[7]` string `"Window 2 (~20:50): …"` → `"Window 2 (~19:50): …"`
3. `last_intake_time` → `"~19:50 (boss 19 Nov: 'aku makan window 2 jam 7.50pm'; 20:50 tu LETRAM sahaja, bukan makanan)"`
4. `eating_window_today` → `"15:00 -> ~19:50 (window ditutup)"`, `status` → tutup ~19:50
5. `data_quality` += `CORRECTION 2026-11-19: …`; `corrections[]` entry with `from`/`to`/`source`

Read-back confirmed: 4× `~19:50`, totals still **718 kcal / P 58.55** and 10 items — a clock correction
does not re-price the day, and the reply should say so.

## The med/IF question he asked in the same turn

"letram ni boleh membatalkan/reset IF ke?" — **no.** Tablets (levetiracetam, dexamethasone, Akurit,
calcium+calcitriol) carry negligible energy and trigger no meaningful insulin response, so they neither
break nor reset the window. The fast breaks on **calories/macros**: milk, juice, sweetened kopi/milo,
"makan sikit". Answer it in one short paragraph and do not add dosing commentary.

## Rules extracted

- A `last_intake_time` whose parenthetical names a drug is **unverified as a food anchor** — cross-check
  `meal_items[].time` and the `meals[]` strings, or ask one question before quoting a band.
- When writing the anchor, record the food line only; med times live in `med-status.json`.
- Acknowledging a wrong anchor: own it in one line, show the corrected field values from read-back, state
  the honest consequence ("verdict betul tapi sebabnya salah, beza 1 jam"). No defensiveness, no re-derivation
  of the whole day.
