---
name: wearable-metrics-verification
description: "Verify smartwatch workout calories and HR bands."
version: 1.0.0
author: Hermes (curator-managed)
license: MIT
metadata:
  hermes:
    tags: [Fitness, Wearables, Energy Expenditure, MET, Heart Rate, Verification]
    category: health
---

# Wearable Metrics Verification

Use when the user reports smartwatch / activity-tracker data (workout kcal, HR, zones,
steps) and you must estimate or sanity-check energy burn. Smartwatch calorie numbers
are a model output, not a measurement: treat them as a claim to test against physiology
— never as the answer, never as garbage either.

## Trigger

- "Ni data jam aku" / screenshot of a workout summary (duration, kcal, HR, zones)
- "Berapa anggaran kalori burn" for a specific session
- Steps / HR numbers being used to justify a TDEE or deficit claim
- Total vs active calories confusion ("beza dia apa?")

## 4 mandatory rules for the canonical feed (Phase 6, 2026-11-16)

Everything below assumes these; violating any one of them is what turns a correct number into a
trust break.

1. **Canonical file only — no ad-hoc cloud probes.** Wearable kcal, steps, HR, sleep, SpO₂, body
   weight and workouts come from `/home/ubuntu/hermes-huawei-sync/data/latest.json` (today) or
   `data/YYYY-MM-DD.json` (history). Quote its `fetched_at`. Need freshness mid-query → run
   `python3 /home/ubuntu/hermes-huawei-sync/sync_huawei.py --sync-diet-log` first, then read the
   file. Never run inline Python against the Huawei Cloud endpoints.
2. **Settling window is part of the answer.** `sync_settling == true` (last block ended < 30 min
   ago) → prefix with `[PRELIMINARY — watch masih sync ke cloud]`; do not quote-and-revise twice.
3. **Modality provenance is not optional.** Only `modality_source == "user_confirmed"` lets you
   name the sport. Otherwise: `"unclassified workout (reconstructed from intensity + HR)"` and
   offer `--annotate DATE HH:MM "Label"` once.
4. **One weight, one BMR, both dynamic.** `body_weight_kg` from `latest.json` feeds the models;
   `profile.latest_weight_kg` in `diet-log.json` is auto-mirrored by `--sync-diet-log`. BMR is
   `tdee_calibration.bmr_kcal` (Mifflin-St Jeor: 1441 kcal at 59.0 kg, 1449 at 59.8 kg) — never a
   hardcoded 1449. TDEE = `BMR + max(0.15×BMR, device_active)` and stays a **candidate**.

## Core arithmetic (use a tool, never mental math)

```
kcal_per_MET_min = 3.5 * weight_kg / 200
gross_kcal       = MET * kcal_per_MET_min * minutes
resting_kcal     = kcal_per_MET_min * minutes      # 1 MET over the same window
net/active_kcal  = gross_kcal - resting_kcal
implied_MET      = watch_kcal / minutes / kcal_per_MET_min
```

Weight: use the latest **verified** weight and say which one. If stale, say how old —
the whole band scales with it.

## Test 1 — implied MET plausibility

Compute `implied_MET` from the watch figure, compare with the Compendium band for that
specific activity.

- inside band → accept; report "consistent", not "verified accurate".
- >15% above band → suspect (a) the figure is *active* kcal treated as *gross*, or
  (b) algorithm overestimate.
- wildly above band (e.g. >9 for recreational racket sport) → reject and say what the
  number would have to mean physically.

## Test 2 — total vs active calories

Most watches label workout kcal ambiguously. Resolve before any deficit math:

1. State both interpretations with their implied MET.
2. Pick the physiologically plausible one and say why.
3. Tell the user exactly where to look: workout detail → `Average heart rate` /
   `Max heart rate` / `Active calories` vs `Total calories`.
4. Until confirmed, report the **band**. Once the user confirms, lock one figure and
   mark the old band superseded in the log.

Beginner one-liners that worked:
`Total calories = semua tenaga badan guna hari tu, termasuk bernafas & jantung berdegup.`
`Active calories = tenaga EXTRA sebab bergerak/bersenam sahaja.`

## Test 3 — HR cross-check

```
HRmax: Tanaka 208 - 0.7*age   |   220 - age
%HRmax = avg_HR / HRmax
```

Approximate, for an untrained adult: 60-70% HRmax ≈ MET 4.5-6; 70-80% ≈ MET 6-8.
Use device `max HR` to confirm real intensity variance (intervals, rallies) rather than
assuming steady state.

**Reject HR-only regression equations.** Keytel (2005) men's equation returns absurd
submaximal values (measured this session: ~825 kcal for 76 min at 131 bpm). Show the
number, name it as a known submaximal overestimate, discard it. Do NOT average it into
the band — averaging a known-biased model manufactures false precision.

## Test 4 — unmonitored session: scale from a device anchor, never invent

When the user did the *same modality* but wore no tracker, do not reach for a generic MET table
first — scale their own last measured session, then bound it with the talk test.

```
anchor_rate = device_kcal / anchor_minutes        # same bike, same person
 gross_today = anchor_rate * today_minutes
  net_today  = gross_today - (kcal_per_MET_min * today_minutes)
```

A scaled anchor inherits the anchor's own error **and** the day's intensity difference, so the
output is always `MODELED, not measured` — say those words. Never let a scaled number into a
deficit claim without the band attached.

### Talk test beats sweat as an intensity cue

| Self-report | Reading | Cap |
|---|---|---|
| boleh nyanyi / cakap penuh santai | below ventilatory threshold | ≤ ~5.5 MET |
| cakap pendek-pendek, nafas controllable | around VT1 | 6–7 MET |
| tak boleh cakap, nafas berat | above VT1 | 7+ MET |

Sweat is a weak cue — "peluh banyak awal, then tak banyak" is equally consistent with heat
acclimatisation and with dropping effort. Say that instead of silently picking one, and lead the
verdict with the talk test.

Verified 2026-11-10: 70 min Zero bike, no watch. Scaled the 11-08 anchor (481 kcal / 76.15 min =
6.32 kcal/min, implied 6.0 MET) → 442 gross / 366 net. Owner then reported he could
"nyanyi santai sikit²" → capped at MET 5.5 → 403 gross / **327 net** (band 290–366). Delivered 327
as the point value with the band and offered to re-raise to 363 if the effort actually felt harder.
Owner accepted without challenge — the "here is why I downgraded, tell me to raise it" move works.

### Weight anchor: history beats the profile summary field

`diet-log.json` `profile.latest_weight_kg` can disagree with the last `weight_history` record
(2026-11-10: `62.0` in the summary field vs `62.8` from the IPR clinical vitals slip). Trust the
history entry, cite its source, fix the summary field, and say the fix out loud — the entire kcal
band scales linearly with this number.

## Test 5 — all-day device kcal on a no-workout day: do NOT add it to a PAL-based TDEE

A watch figure on a day with **no logged session** (e.g. "jam cuma show 88 kcal, 1621 steps") is not
free deficit. It is almost always already inside the PAL multiplier.

The comparison to run first, in this order:

```
pal_overhead_kcal = BMR * (PAL - 1)        # what the model already credits above lying still
device_kcal       = figure shown on the watch
if device_kcal < pal_overhead_kcal:  -> model is ALREADY more generous; add nothing
```

Worked case, 2026-11-14: BMR 1449 kcal at 59.8 kg, PAL 1.2 → overhead **290 kcal**; watch showed
**88 kcal**. Adding 88 would credit the same walking twice. Deficit stayed `1739 - 801.5 = 938`.

**Active vs total, without asking (inference test):** if the reported kcal is **below BMR**, it cannot
be a whole-day total — nothing alive burns less than BMR — so it must be active-only. State the
inference and its caveat, do not silently assume the label.

**Recording rule:** write it to the log as `device_activity` with `recorded_in_deficit: false`, the
steps, the raw kcal, the inference, and `provenance: single source, not cross-validated`. The number is
evidence about the day's movement, not an input to burn.

**Floor:** never push PAL below 1.2 because the step count is tiny. 1,621 steps ≈ 1.2 km is still a
living adult's floor; PAL 1.2 is the bottom of the scale, not a dial to keep lowering.

**Framing that landed** (owner accepted, no pushback): "kalau aku tambah 88 atas PAL 1.2, aku kira
aktiviti yang sama dua kali — deficit nampak lebih besar dari realiti." Say the double-count
mechanism, not just "tak boleh".

## Test 6 — daily-gap attribution for a stationary session: cap `walkCalories`

A stationary session (indoor bike, rower, treadmill) has no distance, so Huawei's daily step
aggregator books part of the wrist/cadence motion into `dimenDailyActivity.walkCalories`. Plain
`total − walk − climb` therefore *under*-attributes the workout. Cap walking kcal at the physical
cost of the recorded steps whenever an unlogged workout block exists:

```
max_step_kcal       = steps * 0.035 * (weight_kg / 60)
effective_walk_kcal = min(raw_walk_kcal, max_step_kcal)     # cap only with a workout block
workout_active_kcal = max(0, total_active_kcal - effective_walk_kcal - climb_kcal)
```

Verified 2026-11-16 (indoor cycle, 70 min, avg HR 123.6, 59.0 kg): total active 380.8 kcal, raw
walk 111.1 kcal for 1,671 steps → cap 57.5 → **pooled 322.2** vs the app's 325 active (0.86% gap),
against **268.6** from raw subtraction. Exposure matters: report `walk_capped`, `raw_walk_kcal`,
`effective_walk_kcal`, `max_step_kcal` alongside the pooled figure.

The pooled number is still a **day-level pool apportioned by block duration**, not a per-session
measurement — the cloud has no per-block kcal. Say that out loud every time.

**Gross vs active.** `estimated_gross_kcal = active_kcal + duration_min * (BMR/1440)` reproduces the
app's "total calories" display (322.2 + 70 min → 392.6 vs app 410). State which of the two you are
quoting; mixing them is how a 20% deficit error enters.

**Provenance of the *modality*.** A `type=12` intensity block plus `type=7` HR series contains no
sport name. Unless the owner confirmed the label (sidecar annotation),
write "unclassified workout (reconstructed from intensity + HR)" — never "indoor bike" as if the
sensor said it. This exact overclaim (16 Nov) was read as fabrication and cost the session's trust.

**Settling window.** Watch→cloud aggregation keeps moving for ~30 min after a session ends (16 Nov:
367.3 → 375.0 → 380.8 kcal across three reads). Quote `fetched_at`, and if the last block ended
< 30 min ago label the figure `[PRELIMINARY — watch still syncing]` instead of revising your own
number twice in a row. Answer from the persisted sync JSON, not an ad-hoc probe.

**The ask may not be yours.** When he says *"aku tak faham apa yang kau suruh check"*, resolve who
asked before apologising: automated reports (e.g. the 16:00 Gate-4 cron) also deliver "perlu
pengesahan kau" lines into the chat. Read `~/.hermes/cron/output/<job_id>/` for today's run, then
name the source explicitly ("itu dari laporan automatik 16:00, bukan chat ni") and tell him whether
anything is actually required. Mis-attributing a cron ask to yourself reads as the agent inventing
work. Full case + the drift/trust contract: `references/huawei-sync-drift-and-trust-contract.md`.

## Where the numbers come from — data acquisition (removes manual key-in)

Manual transcription of watch figures is the weakest link in every test above: a mistyped
kcal or a mislabelled active-vs-total turns into a wrong deficit. When the owner asks how to
feed device data in automatically, answer from the ordered options in
`references/huawei-watch-data-acquisition.md` (Huawei Watch Fit 4 Pro, researched 2026-11-15)
— app-cloud pull client, official Health Kit, Privacy-Centre data request, Strava, Gadgetbridge.

Two rules that survive any integration:

1. An automated feed only removes the transcription error. It does **not** upgrade a device
   number to a measurement — Tests 1–5 still run, and all-day device kcal is still not additive
   on top of a PAL-based TDEE (Test 5).
2. State the provenance tier when quoting a feed: `live app-cloud pull` / `manual export` /
   `user keyed in`. A nightly pull from the same wrist sensor is still a single source.

**Status of the paths, as of 2026-11-16 (supersedes the 2026-11-15 line):** the app-cloud pull
(Option A) is **LIVE** — OAuth login against the owner's MY account, reads returning
`resultCode: 0`, cron at 09:30 / 15:00 / 22:30 MYT (`last_status=ok`), token rotation observed
live on 15:00 and 22:30 runs with no mobile logout, and peak RSS 31.8 MB against the 40 MB gate.
Still **not** proven: any claim of a general accuracy bound (the 0.86% figure is n=1, one session),
and the ~7-day TDEE candidate lock. Everything else (Health Kit, Privacy-Centre export, Strava)
stays THEORETICAL or gated. Do not present an unrun phase as working — state which gate it reached. Verified recipe, raw numbers and
the failure modes that cost the session: `references/huawei-optiona-live-integration-20261115.md`.

**Owner attestation is not a measurement.** At a calibration gate the owner may answer *"semua sama"*
instead of reading five numbers off the screen. Record it as `owner-attested` with the date and the
exact words; never upgrade it to "verified by measurement" in a later report, and never claim a
screenshot exists. The cloud values captured at that moment go in the same note so a future session
has the other half of the comparison.

Before writing any phase of that build, load `references/huawei-optiona-phase0-code-facts.md`: the
vendored client's real constants, the host-table discrepancy (Asia data host is third in `APP_HOSTS`,
and `SESSION_HOSTS` has **no** Asia entry at all), the standalone-import patch, and the
`getSyncVersions` gap that breaks the planned staleness gate.

**Calibration rule for the feed once it exists:** `TDEE_candidate = BMR + max(PAL_overhead,
device_active)`, and it stays a candidate until ~7 days of side-by-side data. Do not adopt
`TDEE = BMR + device_active` outright: on a low-NEAT day the watch undercounts (2026-11-14: 88 kcal
reported vs a 290 kcal PAL overhead), which would *inflate* his deficit rather than protect it.

## Hard rules

1. **Never 1:1 compare two different activities.** Steady-state indoor cycling and
   intermittent racket sport are not interchangeable at equal average HR. Owner's words:
   "both definitely different sports … comparison hanya boleh untuk kau reporting sebarang
   differential." Use cross-activity figures only for a differential or a research-grounded
   question.
2. **Label single-source MET values.** If the Compendium value came from a secondary page
   rather than the primary table, say so.
3. **Band first, then lock.** No RPE, no power meter → a band is the honest output.
4. **Do not double-count.** Base TDEE already carries ambient activity; state that the
   exercise hour was counted at rest baseline in the PAL. All-day step/active-kcal figures are
   covered by the PAL too — see Test 5 before adding them.
5. **Resting kcal is not free.** ~100 kcal at 62 kg over 90 min; subtracting it is what
   converts gross → active and prevents a ~20% overstated deficit.
6. **A session label is never sensor output.** Steps/distance/HR cannot name the sport. Only an
owner-confirmed annotation makes "indoor cycle" a fact rather than a guess.
7. **Two numbers for one session must reconcile out loud.** When active vs gross or two pulls
disagree, show both, name which one feeds which formula, and never silently swap — the owner
reads a shifting number as fabrication even when every single value was correct.

## Output shape

One emoji per numbered section, one fact per line — same discipline as
`explain-tech-to-user` ("Number-heavy reports" section). Sequence that worked:
`🏸 1. Sesi` → `🔥 2. Kalori` → `📐 3. Cross-check` → `⚖️ 4. TDEE` → `⚠️ 5. Nota jujur`,
then ONE concrete action (e.g. "bagi screenshot page detail workout").

## References

- `references/watch-crosscheck-worked-examples.md` — two fully worked sessions with raw
  device figures, every formula output, and the accept/reject reasoning.
- `references/unmonitored-session-scaling.md` — worked scaling run (anchor → 70 min session →
  talk-test cap → deficit), with the exact numbers and the weight-anchor conflict.
- `references/all-day-device-kcal-and-pal.md` — no-workout day (1621 steps / 88 kcal): the PAL-overhead
  comparison, the active-vs-total inference, and the `device_activity` log record written.
- `references/huawei-watch-data-acquisition.md` — Huawei Watch Fit 4 Pro → Hermes: the five acquisition
  paths, the MIT app-cloud client (fields, auth, endpoints, caveats), and an explicit what-was-verified
  vs what-is-still-theory table.
- `references/huawei-optiona-live-integration-20261115.md` — the app-cloud pull after it actually worked:
  login capture on a phone browser, `error=1201 invalid+ticket`, the `as_dict`-is-a-property crash that
  ate a single-use code, region pin proof, kcal×1000 unit scaling, observed field map, staleness via
  `generateTime`, Gate 2 RSS/validator results, and what is still unverified.
- `references/huawei-sync-drift-and-trust-contract.md` — the 2026-11-16 trust break: three reads of the
  same session (367.3 → 375.0 → 380.8), probe-vs-persisted-file discipline, `sync_settling`, the
  walk-cadence cap, `--annotate` modality sidecar, and how a cron-delivered "perlu pengesahan kau"
  line gets mis-read as the agent asking for something.
