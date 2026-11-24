# Worked case — 2026-11-16 (estimated buka, staggered eating)

## Question
"pukul berapa berbuka IF aku harini?" at 14:33 MYT.

## Resolution
- Anchor = `diet-log.json.logs['2026-11-15'].last_intake_time` = `"~20:05 (boss: 'last makan 8.05pm')"` — his own words from the previous evening.
- Band: 17 h = 13:05 · 18 h = 14:05 · 19 h = 15:05 (computed with Python, not mentally).
- Asked at 14:33 → 18 h 28 m elapsed, inside the band, 32 min before the 19 h ceiling.
- JAKIM payload same call: `zone=SGR01`, `date=16-Nov-2026`, `hijri=1448-06-06` (non-Ramadan), maghrib 18:59 — quoted only as a Ramadan-only alternative, never as his buka time.
- Recent pattern used for "early or late for him": 15:13 · 14:55 · 14:00 · 15:10 · 14:20 · 14:20.

## What changed after the answer
He came back at 17:18 with "aku dah berbuka around 3pm i think" plus 4 food items, and added
"pemakanan aku ada penjarakkan masa yang bukan makan sekaligus" — eating was staggered, so the
3 pm hour is not the last intake.

Consequences encoded in the entry:
- `fasting_window`: `"15 Nov ~20:05 -> 16 Nov ~15:00"`, `fasting_hours: 18.92` — estimate flagged in `fasting_note` as "ANGGARAN boss, bukan exact".
- `last_intake_time`: `PENDING - boss belum nyatakan; makan dijarakkan` — asked him for the real last item time instead of reusing 15:00.
- `status`: OPEN; `pending[]` lists last_intake_time, window 2, Slot C, device-kcal snapshot.
- `deficit_uniform.basis` marked PARTIAL because device active kcal was still the 15:00 snapshot (14.2 kcal).

## Numbers logged (MAX-BOUND anchors reused, nothing invented)
- Telur rebus 2 biji — 100 g / 156 kcal / P 12.6 / C 1.2 / F 10.6
- Ayam goreng saiz kecil 1 ketul — 50 g / 100 kcal / P 15.0 (anchor 11 Nov "isi, dicuci & diperah"; hari ni tak dicuci → kekal hujung atas)
- Tomato besar 1 biji — 180 g / 36 kcal / P 1.6
- Tempe air fryer saiz biasa — 30 g / 60 kcal / P 5.5 ("back to saiz biasa" = 30 g, bukan 60 g double 15 Nov)
- Total 352 kcal · P 34.7 · C 11.7 · F 18.0 → protein floor gap 37.1–61.0 g flagged above the calorie gap.

## State write
`diet-log.json` updated with a timestamped `.bak-` copy first, then read back (`totals`, `deficit_uniform`,
`len(meal_items)`) before reporting — the write is not the proof, the read-back is.
