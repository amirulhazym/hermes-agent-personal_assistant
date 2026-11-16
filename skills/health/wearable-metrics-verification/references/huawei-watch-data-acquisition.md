# Huawei Watch Fit 4 Pro → Hermes: acquisition paths

Researched 2026-11-15 for the owner's question "macam mana nak bagi kau connect dengan health
data smartwatch, kurangkan manual key-in". Watch: **Huawei Watch Fit 4 Pro**, health data
producing since 2026-11-14 (HR + device kcal from that date; earlier sessions are MODELED MET).

Goal is narrow: replace hand-transcribing *daily device kcal, steps, resting HR, sleep* into the
diet/TDEE workflow. It is **not** a licence to trust a number more — Tests 1–5 in SKILL.md still run.

## Verification status — read this before quoting anything below

| Claim | Status |
|---|---|
| `and7ey/huawei_health` exists, MIT, Python, active (last push 2026-10-02, 17★, not archived) | VERIFIED via GitHub API |
| Its `client.py` is stdlib-only and does not import Home Assistant | VERIFIED in source + README |
| Endpoint/const set (`APP_HOSTS`, `SESSION_HOSTS`, `READ_PATHS`, `HMS_APP_ID`, scopes) | VERIFIED by reading `const.py` |
| Field list (steps, kcal, HR, sleep stages, HRV, SpO2, stress, workouts) | VERIFIED as documented in README; not yet seen in a live MY payload |
| **Any live login / token / data pull from the owner's account** | **NOT ATTEMPTED — THEORETICAL** |
| Malaysia (:dra / :dre) host serving a MY account | UNVERIFIED — code comment claims "every group answers for any client", RU was the tested one |
| Gadgetbridge supports Fit 4 Pro | UNVERIFIED — only a search snippet ("0.87.0+", HarmonyOS 5 TruSleep); gadgetbridge.org unreachable from the VPS that day |
| Health Kit approval available to an individual | UNVERIFIED — no application attempted |

## Option A — Huawei Health app cloud client (recommended first attempt)

Repo `and7ey/huawei_health`: reads the **Huawei Health app's own cloud**
(`sportdata-dr*.things.dbankcloud.*`, `/dataQuery/*`), which the phone app already syncs into.
Not the Health Kit partner API — no AppGallery registration, no Huawei approval.

Why it fits the VPS: `client.py` is pure stdlib and blocking, explicitly written to run outside
Home Assistant (`Tokens(refresh_token=…, uid=…, session_host=…)` → `HuaweiHealthClient(tokens).daily_summary(3)`).
The HA wrapper is optional — the protocol layer is what we would vendor.

Constants worth knowing (from `const.py`):

```
APP_HOSTS     sportdata-drru.things.dbankcloud.ru   (RU)
              sportdata-dre.things.dbankcloud.com   (EU)
              sportdata-dra.things.dbankcloud.com   (Asia — the one a MY account should use)
              healthdata.dbankcloud.cn              (CN)
SESSION_HOSTS healthcommon-drru.things.dbankcloud.ru / healthcommon-dre.things.dbankcloud.com
READ_PATHS    /dataQuery/sport/v2/getSportsStat, /dataQuery/sport/getSportsDimenStat,
              /dataQuery/sport/getSportsDataByTime, /dataQuery/health/getHealthStat,
              /dataQuery/health/getHealthData, /dataQuery/common/getSyncVersions
HMS_APP_ID    10414141        APP_VERSION  and_health_16.1.6.320
REFRESH TTL   180 days        *ByTime windows capped at 10 calendar days
```

Fields the client can expose (README table): steps, distance, kcal, active minutes, walking
minutes, active hours, intensity minutes, resting/avg/max/min HR, sleep total + deep/REM/light/awake
+ sleep score + efficiency + last HRV + last SpO2, stress, last workout (type/min/km/kcal).

The first four are exactly what the deficit workflow needs; sleep and resting HR make a better
PAL story than a blanket 1.2.

Caveats that must be told to the owner up front:

- **Unofficial, reverse-engineered** from APK 16.1.6.320; a Huawei app update can break it
  (`resultCode` errors are the tell). README itself flags possible ToS conflict.
- **Login needs one human step**: the consent page carries a sliding captcha, so a browser
  (mobile device mode in DevTools) must complete it once. After that the client rotates tokens
  for 180 days.
- **One live session per account**: the phone app and the client share the refresh token and
  whoever rotates last wins. Poll infrequently (2×/day) and expect occasional re-login.
- **Tokens are medical-data credentials for 180 days** — store `chmod 600`, never paste in chat,
  back it up like a password.

Sketch of the build (not yet executed):

1. Vendor `client.py` + `const.py` under the personal repo's `scripts/`, no pip deps.
2. One-time browser-assisted login → `~/.hermes/secrets/huawei_tokens.json` (0600).
3. Cron 2×/day: refresh → `daily_summary()` → append to `~/.hermes/health-cloud/daily.json`
   with `provenance: app-cloud pull`, `region_host: <host actually used>`.
4. Hermes reads that file when computing TDEE, and reports the source tier per SKILL.md rule 2.

## Option B — official Health Kit

AppGallery Connect app + Health Kit permission application + per-scope user consent; data via
the Android SDK or cloud REST. Correct and sanctioned, but the approval gate is the problem for a
single-person use case and the client is an Android app, not a VPS script. No application was
attempted, so treat "an individual can get these scopes" as UNVERIFIED rather than impossible.

## Option C — Privacy Centre data request (manual baseline)

HUAWEI ID → Privacy Centre → **Request Your Data** → choose the **Health app** option → Huawei
emails a download link (reported within ~a day) to the data archive.
Official and free; latency and manual download mean it is a periodic reconciliation, not a feed.
Official doc: `consumer.huawei.com/en/support/content/en-us00746223/`. The "Health app" menu step
comes from a community forum post, not Huawei documentation — one source, low confidence on the
exact wording.

## Option D — Strava

Huawei Health can link to Strava for **workouts only** (HR, duration, distance, kcal per session).
Strava's API is free, so this is a cheap way to get session-level data — but it says nothing about
all-day steps, sleep, or resting HR, so it does not remove the daily key-in by itself.

## Option E — Gadgetbridge (least certain)

Pairs the watch directly to Android without Huawei Health, keeping data local. On 2026-11-15
`gadgetbridge.org` refused TCP from this VPS (connection reset) under both web_extract and
headless Chrome, and Codeberg returned HTTP 429 — so the support matrix could not be read first-hand.
A search snippet claimed "Huawei Watch Fit 4 Pro" with TruSleep stages from Gadgetbridge 0.87.0+
(HarmonyOS 5+); that is **one unverified source**. Also costs a re-pair (losing Huawei Health
features) and depends on a phone, so it ranks below A for this owner.

## What the answer must NOT claim

- That any of these already works for his account — nothing was exercised live.
- That Health Connect closes the gap: multiple 2026 sources say Huawei Health offers no native
  Health Connect sync. Correlated blog sources, so treat as "no documented official path" rather
  than proof of impossibility.
- That Gadgetbridge definitively does or does not support the device — the site was unreachable.
