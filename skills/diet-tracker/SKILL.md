---
name: diet-tracker
description: Deterministic diet, nutrition macros, and caloric deficit tracking for Amirulhazym. Enforces ADHD-friendly 5-category visual reports on WhatsApp and counters Dexa-induced sodium retention.
disable-model-invocation: false
license: MIT
metadata:
  hermes:
    tags: [Diet, Nutrition, ADHD, Health, Dexa, Deficit]
    category: health
    related_skills: [med-tracker, i-have-adhd]
---

# Diet Tracker & ADHD Nutrition Protocol

## Domain Rules & Constraints
1. **ADHD Visual Formatting (WhatsApp):**
   - Strictly prohibit unstructured dense paragraphs or conversational rambling when discussing diet.
   - All diet and nutrition responses MUST follow the structured format:
     - 📋 1. LOG PEMAKANAN HARIAN (INTAKE)
     - 🧪 2. PROFIL NUTRISI (MACROS)
     - 🔬 3. KAJIAN BIOMEDIKAL: PROS & CONS (Khas Dexa & Pemulihan)
     - ⚖️ 4. TENAGA KELUAR & STATUS DEFISIT (BURN)
     - ⚡ 5. NEXT ACTION MALAM INI
2. **Clinical Dexa Taper Rules:**
   - Dexamethasone induces mineralocorticoid sodium retention, causing edema / water retention.
   - NEVER suggest adding salt/sodium to drinks or electrolytes post-workout. Prioritize potassium-rich sources (e.g. bananas, ulam) to promote natural renal sodium clearance.
   - Sparing lean muscle: prioritize high-biological-value protein (eggs, chicken, fish) to counteract steroid catabolism while maintaining calorie deficit.
   - Low-carb / zero rice preferred to prevent steroid-induced insulin resistance and visceral fat deposition.
3. **Execution Tool:**
   - Always update `~/.hermes/diet-log.json` when the user reports meal/exercise events.
   - Use `python3 scripts/diet_report.py [--mode eod|compact]` to generate deterministic formatted reports rather than constructing ad-hoc prose.

## Wearable Burn Inputs — 4 Mandatory Rules (Phase 6, 2026-11-16)

Burn, TDEE and deficit must never be argued from memory, a screenshot, or an ad-hoc cloud
probe. One canonical feed, one settling rule, one modality rule, one weight.

1. **Canonical file only — no ad-hoc cloud probes.**
   - Wearable calories, steps, HR, sleep, SpO₂, body weight and workouts come from
     `/home/ubuntu/hermes-huawei-sync/data/latest.json` (today) or
     `data/YYYY-MM-DD.json` (history). That file is the SSOT; quote its `fetched_at`.
   - If freshness is genuinely required mid-query, run
     `python3 /home/ubuntu/hermes-huawei-sync/sync_huawei.py --sync-diet-log` first, then
     read the file. **Never** run inline Python against Huawei Cloud endpoints — ad-hoc probes
     are what produced 367.3 → 375.0 → 380.8 kcal for one session on 2026-11-16.
2. **Settling window is part of the answer.**
   - Read `sync_settling` and `fetched_at` before quoting any device number.
   - `sync_settling == true` (workout block ended < 30 min ago) → prefix the number with
     `[PRELIMINARY — watch masih sync ke cloud]` and say when it settles. Do not revise the
     same figure twice in a row; label it preliminary instead.
3. **Modality provenance is not optional.**
   - A sport name may only be stated as fact when `modality_source == "user_confirmed"`.
   - `modality_source == "reconstructed_intensity_hr"` → report
     `"unclassified workout (reconstructed from intensity + HR)"` and offer
     `--annotate DATE HH:MM "Label"` once. Never call it "indoor bike" because it looks like one.
4. **One weight, one BMR, both dynamic.**
   - Weight: `body_weight_kg` + `body_weight_measured_date` from `latest.json`.
     `profile.latest_weight_kg` in `diet-log.json` is auto-mirrored from it by
     `--sync-diet-log` on every cron run — if the two disagree, the JSON payload wins and the
     mismatch gets stated, not silently averaged.
   - BMR: read `tdee_calibration.bmr_kcal` (Mifflin-St Jeor on that weight; 1441 kcal at 59.0 kg,
     1449 at 59.8 kg). Never hardcode 1449. TDEE stays
     `BMR + max(0.15×BMR, device_active_kcal)` and stays a **candidate** until ~7 days of
     side-by-side data.
