---
name: huawei-health-cloud-sync
description: Use when reading Huawei Health (Watch Fit 4 Pro) data on the VPS — cloud endpoint map, token safety, workout reconstruction from health series, and the pitfalls found live.
metadata:
  hermes:
    tags: [huawei, health, wearable, oauth, sync]
    category: health
    related_skills: [diet-tracker, health-log-state-verification]
---

# Huawei Health Cloud Sync (Option A)

Read-only pull of a HUAWEI ID's health telemetry from the **Huawei Health app cloud**
(`sportdata-dra.things.dbankcloud.com` + `healthcommon-dra.things.dbankcloud.com`), using the
vendored MIT client from `and7ey/huawei_health` (v1.0.8) plus local extractors.

Verified live 2026-11-15 on: Watch Fit 4 Pro (`productId 822`, HarmonyOS 6.1.0.117) paired to an
Honor 600 Pro 5G (MagicOS 11.0), HUAWEI ID region **MY**.

## 1. Auth (one human step, then 180 days)

1. `client.authorization_url()` → send the URL to the owner.
2. Owner runs it in **desktop Chrome incognito**, logs in, taps Allow, and copies the
   `Failed to launch 'hms://redirect_url?code=…'` line from the Console.
3. `python3 exchange_code.py '<pasted line>'` — exchanges the code, writes
   `~/secrets/huawei_tokens.json` atomically (mode 600).

Pitfalls that cost real time:

- On a phone in desktop mode the blue **Allow** button is dead (`display=touch` binds touch events).
  Phone-only flow: disable HMS Core link handling, use native mobile Chrome, then copy the
  `hms://` URL out of the address bar after the click.
- Repeatedly reusing the same authorization URL produces
  `hms://redirect_url?…&error=1201&error_description=invalid+ticket`. Start a fresh incognito
  session and a fresh URL; complete within ~2 minutes.
- The authorization code is **single-use and short-lived**; a `20020001` means expired/used →
  regenerate the URL.
- `Tokens.as_dict` is a **property**, not a method (`tokens.as_dict`, never `tokens.as_dict()`).

## 2. Region routing (MY)

- Data host: `sportdata-dra.things.dbankcloud.com` must be **first** in `APP_HOSTS`.
- Token host: `healthcommon-dra.things.dbankcloud.com` is **not** in the upstream `SESSION_HOSTS`
  and must be added and pinned first; it is the host that actually issued MY tokens.
- `dre` (EU) and `drru` (RU) stay behind as fallbacks. DNS/HTTP 403 probes prove reachability
  only — never region entitlement.

## 3. What the endpoints really return

| Path | Reality on MY account |
|---|---|
| `/dataQuery/sport/v2/getSportsStat` | one row, `sportType: 0`, daily totals only; `calorie` is **milli-kcal** (divide by 1000) and is **active** kcal (excludes BMR) |
| `/dataQuery/sport/getSportsDimenStat` | per-type daily rows, but only walking/climbing appear |
| `/dataQuery/sport/getSportsDataByTime` | minute GPS/step segments; **no indoor workout record exists here** |
| `/dataQuery/health/getHealthStat` | daily sleep/HR/stress summaries; `maxHeartRate` is routine-sample only, `lastAvgSpO2 = -1` means "no sleep SpO2" |
| `/dataQuery/health/getHealthData` | the real treasure: type 7 dynamic HR (1-min during workouts), type 8 weight, type 12 exercise intensity, type 16 daytime SpO2 |
| `/dataQuery/common/getSyncVersions` | exists (1001 on every body shape tried) — schema unknown, do not rely on it |

Workout reconstruction (see `workout_reconstructor.py`):

- workout kcal = `sportBasicInfo.calorie − walkCalories − climbCalories` (÷1000);
- duration = contiguous `type=12` minutes (gap ≤ 3 min);
- HR = `type=7` samples inside that window (avg/max beat `getHealthStat`);
- filter: block ≥ 30 min **and** attributed kcal ≥ 100, otherwise it is awake noise;
- if a `/sport/` GPS session overlaps ≥ 50% of a block, mark `already_logged` — never double count;
- `getHealthData` rejects ranges wider than 7 days (`1001`); weight lookback must be chunked.

## 4. Token concurrency (verified)

Post-expiry rotation (2026-11-15 20:25) minted a new **access** token while the **refresh** token
hash stayed identical → VPS and phone share one refresh token without invalidating each other.
The Huawei Health app stayed logged in across three rotations in one evening.

## 5. Run shape

- `sync_huawei.py` → `data/YYYY-MM-DD.json`, `data/latest.json`, `data/status.json`.
- `schema_validator.py` → bounds + provenance gate; exit 0 = pass.
- `~/.hermes/scripts/huawei_health_sync.sh` → no_agent cron wrapper; **stdout is the message**,
  silent on the normal path; speaks only for auth expiry, sync failure, RSS > 40 MB, or stale data.
- Cron: 09:30 / 15:00 / 22:30 MYT (`no_agent`, deliver to origin chat).

## 6. Deficit math

`TDEE = 1449 + max(217.35, device_active_kcal)`. Never add device kcal on top of a
PAL-multiplied TDEE (double count), and never swap the PAL floor out entirely (watch under-counts
NEAT on low-step days). Lock after 7 days of side-by-side data.
