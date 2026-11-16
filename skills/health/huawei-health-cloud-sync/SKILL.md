---
name: huawei-health-cloud-sync
description: Use when pulling Huawei Health watch data via cloud API.
metadata:
  hermes:
    tags: [huawei, health, wearable, oauth, cron, integration]
    category: health
    related_skills: [health-log-state-verification, hermes-no-agent-cron-pattern, diet-tracker]
---

# Huawei Health → local agent (app-cloud client)

The Huawei Health **app's own cloud** (`sportdata-dr*.things.dbankcloud.*`, `/dataQuery/*`) is the only
zero-cost path to per-day watch data for a personal account: the official Health Kit route needs an
AppGallery app + `client_secret` + developer/enterprise verification, and the HUAWEI ID Privacy Centre
export is manual with multi-day latency. Working implementation: `and7ey/huawei_health` (MIT) — its
`client.py` + `const.py` are stdlib-only and lift out of Home Assistant cleanly.

Verified live 2026-11-15: Malaysia HUAWEI ID, Watch Fit 4 Pro on HarmonyOS 6.1.0.117,
Honor 600 Pro 5G host phone, Python 3.11 on a 1.9 GB VPS.

## Non-negotiable agent rules (Phase 5, owner SOP 2026-11-16)

**Rule A — No ephemeral reads.** Never answer a live Huawei Health question from an ad-hoc
terminal snippet. Run `python3 ~/hermes-huawei-sync/sync_huawei.py` first so `data/latest.json`
(and `data/YYYY-MM-DD.json`) is current, then read the persisted JSON. Ad-hoc API probes during a
chat produced 367.3 → 375.0 → 380.8 kcal across three consecutive answers while the files on disk
stayed at the oldest value. If you *do* probe live, say so explicitly and do not present the
number as the persisted state.

**Rule B — Settling transparency.** Always quote `fetched_at`. If `sync_settling == true`
(a `type=12` block ended < 30 min ago), label every calorie figure
`[PRELIMINARY — watch still syncing to cloud]` and do not revise-argue with your own previous
number; state that the total is still climbing.

**Rule C — Provenance honesty.** A reconstructed block has no sport label. Never write
"indoor bike" / "cycling" unless `workouts[].modality_source == "user_confirmed"` (owner-confirmed
via the sidecar). Otherwise say "unclassified workout (reconstructed from intensity + HR)" and ask
for the modality once, then persist it with `sync_huawei.py --annotate`.

### CLI modes (all read-only against the cloud)

```bash
python3 sync_huawei.py                                  # today -> daily + latest.json
python3 sync_huawei.py --date 20261114                  # historical -> daily only
python3 sync_huawei.py --finalize-yesterday             # re-close yesterday
python3 sync_huawei.py --annotate 2026-11-16 17:33 "Indoor cycle"   # then sync that day
```

The 09:30 MYT cron run executes `--finalize-yesterday` before today's sync, so activity logged
after the 22:30 run is never lost from yesterday's file.

### Calorie attribution (stationary-cadence overlap)

`dimenDailyActivity.walkCalories` absorbs part of a stationary session's wrist/cadence motion, so
raw `total − walk − climb` under-attributes the workout. `workout_reconstructor.workout_active_pool()`
caps walking kcal at the physical cost of the recorded steps
(`0.035 kcal/step × weight/60`) whenever an unlogged workout block exists, and exposes
`walk_capped`, `raw_walk_kcal`, `effective_walk_kcal`, `max_step_kcal`, `workout_active_kcal`.
Each workout also carries `estimated_gross_kcal = active_kcal + duration_min × (1449/1440)`
(matches the app's "total calories" display) and `modality` / `modality_source`.

## Deployment shape that works

```
~/hermes-huawei-sync/
├── vendor/{client.py,const.py,__init__.py}   # vendored, MIT
├── sync_huawei.py          # pull + normalize + staleness/settling gate + atomic write + CLI modes
├── workout_reconstructor.py# type=12 blocks, HR, weight, SpO2, calorie attribution, modality
├── schema_validator.py     # bounds gate before latest.json is replaced
├── exchange_code.py        # one-shot code→token exchange (see templates/)
└── data/{YYYY-MM-DD.json,latest.json,status.json,workout_annotations.json}
~/secrets/huawei_tokens.json   # 0600, dir 0700
```

Cron: three no_agent jobs (09:30 / 15:00 / 22:30 MYT) wrapping one alert-only script — see
`hermes-no-agent-cron-pattern` for the stdout-is-the-message contract. Normal path prints nothing.

## 1. Vendoring: the import patch is mandatory

`client.py` ships `from .const import (...)` → `python3 -c "import client"` fails with
`attempted relative import with no known parent package`. Wrap the import block:

```python
try:  # package import: vendor.client
    from .const import (...)
except ImportError:  # standalone: vendor/ on sys.path
    from const import (...)
```

Verify both forms (`IMPORT_OK` standalone + `PACKAGE_IMPORT_OK`) and print `NON_STDLIB: []` by diffing
loaded modules against `sys.stdlib_module_names`.

## 2. Host pinning (required for a MY account)

Upstream `const.py` ships `APP_HOSTS` = (drru RU, dre EU, **dra ASIA**, cn) and `SESSION_HOSTS` = (drru, dre)
— the Asia **session** host does not exist in the code at all. Pin:

```
APP_HOSTS[0]     = https://sportdata-dra.things.dbankcloud.com
SESSION_HOSTS[0] = https://healthcommon-dra.things.dbankcloud.com   # ADDED, not upstream
```

keep the others behind as fallback. Verified live: the exchange returned `session_host = healthcommon-dra...`
and every read returned `resultCode 0` for the MY account.

A generic `HTTP 403` + identical `ETag` on several hosts is **not** region evidence — it is the gateway
rejecting an unauthenticated request. Only the exchange plus a `resultCode 0` read proves the shard.

## 3. Login capture (human step) — the only sequence that worked

1. Fresh **incognito** window. Do not pre-login at `id1.cloud.huawei.com` in another tab.
2. Paste the generated authorize URL **once**; let the flow redirect to login itself.
3. Complete within ~2 minutes. Consent → **Allow** once.
4. Capture: DevTools → Console → red line
   `Failed to launch 'hms://redirect_url?code=...' because the scheme does not have a registered handler.`
   On a phone without DevTools the same string shows in Chrome's `ERR_UNKNOWN_URL_SCHEME` page / address bar.
5. Send the whole line; exchange immediately (single-use code).

### Login failure modes and their exact tells

| Symptom | Cause | Fix |
|---|---|---|
| `sub_error=20132&error=1201 invalid+ticket` | stale/reused CAS ticket (URL opened repeatedly or hours later) | new URL + new incognito + one attempt |
| `Allow` visible but tap/click does nothing | `display=touch` page needs touch events; phone "desktop mode" kills it | native mobile Chrome (not desktop mode), or desktop DevTools device emulation **with reload** |
| Huawei Health opens instead of an error page | HMS Core handles `hms://` | capture on desktop browser, or disable HMS Core "Open supported links" first |
| CSP `script-src 'none'` errors in console | Huawei's own analytics blocked | **noise**, not the failure |

HMS Core is **not** required by the VPS client (zero HMS: plain HTTPS + OAuth token), and the owner ran
the phone app two days without it with watch sync intact — do not add HMS Core as a prerequisite. Only the
**Huawei Health** battery/background whitelist matters (it must run to push watch data to the cloud).

## 4. The token-loss trap (cost: one wasted live code)

`Tokens.as_dict` is a `@property`, **not** a method. `tokens.as_dict()` raises
`TypeError: 'dict' object is not callable` *after* the exchange already succeeded — the code is consumed and
the tokens exist only in the dead process.

Rules:

- Defensive read: `raw = tokens.as_dict; data = dict(raw() if callable(raw) else raw)`.
- **Smoke-test the save path offline before burning a code**: fake `Tokens(...)`, `SECRETS` pointed at
  `/tmp`, assert atomic write + `0600` + reloadable keys. Only then run against a real code.
- Never print token values — print `keys`, `HAS_RT`, `uid_present`, `session_host`,
  `access_expires_in_s`.
- Persist on rotation: pass `on_change=lambda t: save(t.as_dict)`; `Tokens.apply()` calls it, so a rotated
  pair reaches disk before anything else speaks for the account.

Template: `templates/exchange_code.py`.

## 5. Payload units (verified against a real response)

| Field | Reality |
|---|---|
| `sportBasicInfo.calorie` | **milli-kcal** → divide by 1000 (raw `109256` = 109.3 kcal; `daily_summary()` agrees) |
| `sportBasicInfo.steps` / `distance` | steps / **metres** |
| `duration`, `walkDurations` | minutes |
| `professionalSleep.allSleepTime` etc. | minutes (`dreamTime` = REM) |
| `fallAsleepTime` / `wakeupTime` / `generateTime` | **epoch milliseconds** |
| `heartRateBasic.avgRestingHeartRate = 0` | *no measurement*, not a value — use `lastRestHeartRate` |
| `bind_devices()` | returns the phone (e.g. `HONOR 600 Pro`, `VKP-NX9`) **and** the watch (`productId 822`) |

Field map + raw sample: `references/payload-field-map-20261115.md`.

## 6. Energy math — never add device kcal on top of a PAL-based TDEE

Huawei's daily ring reports **active calories only** (excludes BMR). A tracker using `TDEE = BMR × PAL
1.15–1.20` already contains an activity slice — adding device kcal double-counts, while replacing PAL
outright undercounts on low-step days (device said 88 kcal where the PAL slice was ~290). Use a floor rule:

```
TDEE = BMR + max(BMR × 0.15, device_active_kcal)
```

Emit a `tdee_calibration` block (bmr, pal_floor, device_active, candidate_tdee, legacy PAL-1.20 value,
delta) and **lock the formula for 7 days** of side-by-side data before changing the tracker.

## 7. Staleness + validation gates

- Watch → phone (BLE) → cloud needs the phone app to sync; expect ~1 h cloud latency, and a dead
  background process means stale numbers, not zero activity.
- `getSyncVersions` has **no client wrapper** (`READ_PATHS` entry only) → derive staleness from the latest
  record `generateTime` and record that in the payload (`source` field).
- Flag stale when `staleness_minutes > 180` or (`steps == 0` after 10:00 local).
- Bounds gate before writing `latest.json`: `0 ≤ active_kcal ≤ 4000`, `0 ≤ steps ≤ 100000`,
  `30 ≤ resting_bpm ≤ 140`, `0 ≤ sleep.total_minutes ≤ 1440` — catches the ×1000 unit error instantly.
- Log peak RSS every run (`resource.getrusage(...).ru_maxrss` in a `finally` block, printed as `RSS_KB=`) so
  a tight memory budget is observable instead of discovered.

## 9. Proving the alert-only wrapper without touching production state

An alert-only cron is only trustworthy if you have **seen both paths**. Give the wrapper two test hooks
(read from env, defaulting to production) so the alert branches can be exercised against fabricated state:

```bash
SYNC="${HUAWEI_SYNC_PY:-/home/ubuntu/hermes-huawei-sync/sync_huawei.py}"
STATUS_FILE="${HUAWEI_STATUS_FILE:-/home/ubuntu/hermes-huawei-sync/data/status.json}"
[ "${HUAWEI_SKIP_SYNC:-0}" = "1" ] || { OUT=$(python3 "$SYNC" 2>&1); RC=$?; }
```

Five tests that actually matter, all runnable in one call:

| Test | Setup | Expected |
|---|---|---|
| normal | real run, fresh + VALID | **0 bytes stdout** (silent) |
| stale | `STATUS_FILE` with `is_stale: true` | 2-line stale alert |
| expired | `auth_state: EXPIRED` | 2-line re-login alert |
| failure | `HUAWEI_SYNC_PY=/tmp/fail.py` (exit 3) | "sync gagal" — must NOT claim auth expiry |
| missing state | bogus `STATUS_FILE` path | silent, exit 0 |
| memory | real run pushed above the RSS gate | 2-line RSS alert, distinct wording from stale/auth |

Separate the *failure* branch from the *auth-expired* branch in the script: a generic crash that says
"token expired" trains the owner to ignore a real re-login alert. Also note that any stdout you print in a
test is **not** delivered by the manual shell run, but it will be delivered if it happens inside a real
cron tick — keep ad-hoc probes on a temp status file, never on the live one.

## 10. Reporting-script trap

`grep -c pattern file || echo 0` prints **two** zeros (`grep -c` already prints `0` and exits 1). Use
`X=$(grep -c ... || true); X=${X:-0}`. Caught live in the 24 h Gate-4 report.

## 11. Token concurrency — what "rotation" actually does (verified)

Measured on a MY account, 2026-11-15:

- `refresh_tokens()` while the access token is **still valid** returns the *same* pair: refresh-token hash and
  access-token hash unchanged, `refresh_expires_at` did not slide (179.89 d before and after).
- Two forced rotations back-to-back, each followed by a read → `resultCode 0` both times. The owner then opened
  the phone app and pulled to refresh → the VPS token still read fine.
- So the "whoever rotates wins" collision only matters in the **post-expiry minting** window. The decisive test
  is a refresh *after* `expires_at` has passed, comparing refresh-token hashes against a pre-expiry baseline.

### Accelerated Gate-4 protocol (compresses a 24 h soak into about an hour)

1. Baseline read → record `resultCode` + `sha256(refresh_token)[:12]` into a baseline file.
2. Force one rotation → read again.
3. Owner opens the phone app, pull-to-refresh, browse HR/sleep → read again. `20020003` here means the app
   rotated the pair out from under the VPS.
4. Force a second rotation → read again.
5. **Post-expiry**: wait past `expires_at` (≈1 h), refresh once more, compare the refresh-token hash with the
   baseline, read again.
6. Only then call PASS — and still require owner confirmation that the phone is logged in; the agent cannot see
   the phone, so phone state is *attested*, never measured.

Do step 5 as a one-shot no_agent cron instead of idling in chat. The probe prints hashes and result codes only,
never token values, and ends with the one question the agent cannot answer itself.

## 12. Workout records: the daily aggregate is not a session list

- `getSportsStat` returns **exactly one row** with `sportType: 0` (whole-day totals). There is **no** per-sport-type
  breakdown, so "read the extra rows to discover the indoor-cycling ID" is not possible.
- `sports_detail(start, end, sport_types)` rejects unknown IDs with `resultCode 1001 parameter invalid`; only
  `SESSION_SPORT_TYPES` (1,2,3,4,9,10,14) are accepted. You cannot brute-force sport-type IDs.
- A finished workout can raise daily `calorie` and `exerciseTimeBasic.totalMidHighIntensity` while leaving **no
  session record** in `getSportsDataByTime` (observed: +304 kcal from an indoor-cycling session, cloud still
  holding only three 1-minute `sportType 2` segments **and** zero rows for types 3/10/13, across
  `dataSource` 0/1/2/999). The missing record is real — but that does **not** mean the workout is unavailable:
  see §12b. Never stop at the first endpoint family that returns nothing.
- `sessions()` returns `datetime` objects → `json.dumps(..., default=str)`.

### 12b. Workouts are reconstructable from `getHealthData`, not from `/dataQuery/sport/*`

Verified 2026-11-15 on the indoor-cycling session that `getSportsDataByTime` did not contain. The series
endpoint carries everything:

| type | key | gives |
|---|---|---|
| 12 | `EXERCISE_INTENSITY` (`exerciseType`) | one sample per active minute → contiguous blocks = workout windows |
| 7 | `DATA_POINT_DYNAMIC_HEARTRATE` | HR samples; **switches from ~10-min to 1-min cadence during a workout** |
| 8 | `WEIGHT_BODYFAT_BROAD` (`bodyWeight`) | body weight, no manual entry needed |
| 16 | `BLOOD_OXYGEN_SATURATION` (`avgSaturation`) | **daytime** SpO2 samples (the sleep value in `professionalSleep` can be `-1`) |

Procedure (`templates/workout_reconstructor.py` is the working module):

1. Exercise kcal = `sportBasicInfo.calorie − effective_walkCalories − climbCalories`, ÷ 1000, where
   `effective_walkCalories` is capped at `steps × 0.035 × weight/60` whenever a workout block exists
   (Phase 5 — see the attribution note above and `references/phase5-attribution-and-cli-20261116.md`).
   Without the cap a stationary session is under-attributed by ~17 % (16 Nov: 268.6 vs 322.2 kcal).
2. Group type-12 minute stamps into blocks (gap ≤ 3 min). **Owner-locked filter (Phase 4.5, 2026-11-15):** a
   block counts only if it is **≥ 30 minutes** AND carries **≥ 100 kcal** of attributed gap. Verified on the
   same day: the 89-minute cycling block (`17:18–18:48`) survives; the 24-minute late-night block
   (`00:03–00:34`, avg 107.5 bpm) is awake movement and must not appear in `workouts[]`.
3. Compute avg/min/max HR from type-7 samples inside each block (verified: avg **109.4**, max **129** — while
   `getHealthStat.heartRateBasic.maxHeartRate` capped at **123** because it samples routine minutes only).
4. Attribute the kcal gap to the qualifying block(s) **by duration** (`active_kcal` per block) when more than
   one survives the filter; never invent per-second or per-activity splits, and state the duration-allocation
   basis in `provenance`. **No double count:** if an explicit `/sport/` GPS session (types 3/4/9) overlaps
   ≥ 50 % of a block, mark `already_logged: true` and drop it from the allocation.

   **Memory pitfall:** if you `del` the raw payloads to save RAM, build every derived list first. Calling
   `del payload, annotated, eligible` and *then* referencing them raised
   `UnboundLocalError: annotated` → sync exited 3 and the wrapper fired a real alert. `gc.collect()` is only
   safe after all reads are finished.
5. `spo2_avg` = **mean of type-16 samples**, plus `spo2_latest` = last sample (mean 96.9 % over 8 samples where
   a single sample read 99.0 % — quoting the single sample overstates it).
6. Weight: today's type-8 value, else a **14-day lookback** (query in ≤7-day chunks, newest day first — wider
   ranges return `1001`), and persist `body_weight_measured_date` so an old weight is never presented as today's.

Cost: four extra `getHealthData` pulls, and the type-7 series is ~256 KB — expect peak RSS to rise (see §13).

### 12c. Type-ID enumeration rules

- Accepted by `getSportsDataByTime`: `1,2,3,4,6,7,8,9,10,13,14`. Rejected with `resultCode 1001`: `0,11,12,15,16,
  20,100,264,265`. So "indoor cycling is sportType 265" is untestable — the server refuses unknown IDs and you
  cannot brute-force the table.
- `*ByTime` windows want `YYYYMMDD` ints; epoch **milliseconds** are rejected with `1001` even though the
  upstream docstring says both are accepted.
- Guessed paths return `404 {"message":"Not Found"}` instead of a `resultCode` — a cheap way to prove an endpoint
  does not exist (`getSportRecord`, `getWorkoutRecord`, `getSportRecords`, `getWorkoutData`, `getSportStatDetail`
  all 404-ed). `getSyncVersions` exists (returns `1001 parameter invalid`) but rejects every body shape tried and
  still has no wrapper.

Sleep extras inside `professionalSleep`: `lastAvgHrv` is a real number (38 that night), `lastAvgSpO2 = -1` means
**no measurement** — same sentinel convention as `avgRestingHeartRate = 0`. Do not ship a `-1` as an SpO2 reading.

## 13. Memory budget is tighter than the line count suggests

`client.py` is 812 lines, and `daily_summary(days)` internally calls `sports_stat` **again** (line ~618), so a
payload that does both plus `bind_devices()` pays for two stats round-trips. Peak RSS measured 29,516 KB,
29,644 KB and 30,164 KB on otherwise identical runs; dropping `daily_summary_3d` and adding the four
`getHealthData` pulls (§12b) moved it to **31,468 KB**. A hard 30,000 KB gate therefore flips on variance and on
any added series — do not pretend it is stable.

Measure with `/usr/bin/time -v` **and** log `RSS_KB=` from `resource.getrusage(...).ru_maxrss` on every run
(including failures, via `finally`). When a gate sits within a few percent of the limit, say so explicitly and
put the choice to the owner instead of quietly relaxing it: on a 1.9 GB host 31 MB is ~4 % of RAM, so the honest
options are (a) raise the gate with the headroom rationale, (b) run the expensive reconstruction only on the
end-of-day tick, or (c) trim payload fields (`devices`, unused `daily_summary`). Report the breach either way.

**Owner decision 2026-11-15:** reconstruction stays on all three ticks; `daily_summary_3d` removed; the full
`devices` dump removed from the daily JSON (the validator now fails if a top-level `devices` key reappears);
RSS gate raised to **40 000 KB** with `RSS_KB=` still logged on every run.

## References

- `references/token-rotation-concurrency-20261115.md` — raw hashes/resultCodes for the idempotent-refresh finding and the accelerated Gate-4 sequence.
- `references/login-capture-and-token-loss-20261115.md` — attempt-by-attempt transcript: dead button, `1201 invalid ticket`, lost tokens, the successful capture.
- `references/payload-field-map-20261115.md` — raw `getSportsStat` / `getHealthStat` responses with real numbers.
- `references/workout-reconstruction-20261115.md` — the missing-session investigation end to end: what each endpoint returned, the reconstructor numbers, and the claims that did not survive checking.
- `references/phase45-hardening-and-release-gate-20261115.md` — owner-locked filter/RSS/lean-schema decisions, the live verification numbers, the two hardening bugs, the secret-scan redaction rules, and the AGENTS.md-vs-plan approval-token conflict.
- `references/phase5-attribution-and-cli-20261116.md` — the trust-break incident: ephemeral-read drift, stationary-cadence walk cap (0.86 % vs app), settling flag, modality sidecar, CLI modes, verified 3-day parity table, and the test file.
- `templates/exchange_code.py` — property-safe, atomic, secret-free exchange helper.
- `templates/workout_reconstructor.py` — stdlib module that rebuilds workouts + weight + SpO2 from `getHealthData`.
