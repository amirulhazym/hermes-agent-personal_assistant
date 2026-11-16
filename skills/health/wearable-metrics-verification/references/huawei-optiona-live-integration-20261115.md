# Huawei app-cloud pull (Option A) — what actually worked, 2026-11-15

Status matrix first, because most of the earlier writing about this path was theory:

| Stage | State |
|---|---|
| Vendor `client.py` + `const.py`, standalone import | VERIFIED (Gate 0) |
| OAuth login on the owner's MY account | VERIFIED (Gate 1) |
| Read `sportStat` / `healthStat` / `bindDevices` | VERIFIED, `resultCode: 0` |
| Puller + schema validator | VERIFIED (Gate 2) |
| Cron scheduling | NOT RUN |
| Token concurrency vs phone app (24 h) | NOT RUN |
| MY-region ToS exposure | UNVERIFIED |

## 1. Login capture — the phone worked, the desktop-mode phone did not

The plan insisted on a desktop browser + DevTools. The owner refused to open a PC and got there on
the phone anyway. Sequence that matters:

1. Fresh **incognito**, paste the per-flow auth URL **once**, log in inside the flow (do not pre-login
   at `id1.cloud.huawei.com` in a different tab first).
2. After `Allow`, the page throws
   `Failed to launch 'hms://redirect_url?code=…&state=…' because the scheme does not have a registered handler.`
   That line **is** the code. Copy the whole line and send it immediately — the code is single-use and
   short-lived; the URL itself is not time-limited.

Failure modes seen, in order:

- **Blue `Allow` does nothing.** Phone in *desktop mode* → `display=touch` page binds a touch handler the
  desktop layout does not fire. Also `display=page` variants did not help. Nothing to do with login or
  captcha — do not chase those.
- **`hms://redirect_url?sub_error=20132&error_description=invalid+ticket&error=1201`.** CAS ticket stale
  because the URL had been opened ~20 min earlier and re-tried across three variants. Fix: brand-new
  URL, brand-new incognito session, finish inside a couple of minutes.
- Ignore the CSP `script-src 'none'` console noise and the `simulator.js` stack traces — they are not
  the cause, and reading them as the cause wastes a round trip.

HMS Core and AppGallery were uninstalled mid-session and the flow still worked. Our client never touches
HMS; the phone app syncs over Bluetooth without it (owner's two days of use is better evidence than the
plan's assumption — the plan told him to whitelist HMS Core, which turned out unnecessary).

## 2. The bug that ate a valid code

`client.Tokens.as_dict` is a **`@property`**, not a method. A helper that does `tokens.as_dict()` raises
`TypeError: 'dict' object is not callable` **after** `exchange_authorization_code()` has already consumed
the single-use code — the tokens are minted and then lost with the process.

- Defensive form: `data = tokens.as_dict; data = dict(data() if callable(data) else data)`.
- Smoke-test the whole save path offline first with a fake `Tokens(...)` and a `/tmp` target, then run it
  live. A crash *after* the exchange costs another full login round trip.
- `Tokens.apply()` fires `on_change` on every rotation — wire it to the atomic token save, otherwise a
  refreshed pair lives only in memory.

## 3. Region pin — decision (b) was correct and provably so

The vendored `const.py` ships `APP_HOSTS` ordered RU → EU → **ASIA (index 2)** and `SESSION_HOSTS`
**without any Asia entry**. Adding `healthcommon-dra.things.dbankcloud.com` at index 0 is what made the
login land: the saved token's `session_host` came back as that exact host, and the client then reported
`sportdata-dra.things.dbankcloud.com` with `resultCode: 0` on every read.

DNS/HTTP probe alone proves nothing: both `sportdata-dra` and `healthcommon-dra` resolve to `159.138.91.5`
and answer `HTTP 403` with the identical `ETag: "6a588861-22a"` — a generic gateway rejection. Only the
token exchange distinguishes a working region from a reachable one.

`bind_devices()` confirms the account: `HONOR 600 Pro` (`VKP-NX9`) plus the watch (`productId 822`,
`uniqueId 4SPBB2…ANDROID2…`).

## 4. Unit and field map (observed, not documented)

`getSportsStat` → `sportStat[0]`:

```
sportBasicInfo: steps, distance (metres), duration (minutes), calorie  <-- kcal x 1000  (109256 -> 109.3)
activeHourBasic.countActiveHour        exerciseTimeBasic.totalMidHighIntensity (minutes)
goalAchieveBasic.stepGoalValueStat     (10000) ; calorieGoalValueStat is also x1000 (515000)
```

`getHealthStat` (types 7 / 9 / 11 / 12):

```
heartRateBasic: maxHeartRate, minHeartRate, lastHeartRate, lastRestHeartRate,
                avgRestingHeartRate   <-- 0 means "no resting measurement", not a reading
professionalSleep: allSleepTime, deepSleepTime, lightSleepTime, dreamTime (=REM),
                awakeTime, sleepScore, sleepEfficiency, fallAsleepTime / wakeupTime (epoch ms)
stressBasic: meanScore, lastScore, maxScore, minScore
```

Worked check: 2026-11-15 — 1,754 steps · 1,626 m · 109.3 kcal · sleep 276 min (deep 60 / light 179 /
REM 37 / awake 2, score 71, efficiency 96%) fell asleep 03:01, woke 07:39 · HR max 123 / min 50 /
last rest 56. Sleep and HR blocks are nested objects with no `value` key — printing
`{k: v.get('value')}` shows `None` for them and looks like missing data. It is not.

## 5. Staleness and Gate 2 numbers

`getSyncVersions` has no client wrapper (`READ_PATHS` has the path, but only `post()` reaches it and the
body schema is undocumented). Staleness therefore uses `max(generateTime)` across returned records
(epoch ms) → `staleness_minutes`; label the source in the JSON so nobody assumes the sync endpoint ran.

Gate 2 raw output:

```
[17:12:58] OK kcal=109.4 steps=1754 stale=1min
Maximum resident set size (kbytes): 29516     # gate < 30000 -> PASS by 484 KB, i.e. thin
Exit status: 0 ; schema_validator: PASS
```

If RSS ever fails the gate, drop `daily_summary_3d` from the payload first.

## 6. Layout that was built

```
~/secrets/huawei_tokens.json                 0600, keys access_token/refresh_token/uid/site_id/
                                             expires_at/refresh_expires_at/session_host
~/hermes-huawei-sync/vendor/{client,const}.py  vendored, standalone-import patched
~/hermes-huawei-sync/exchange_code.py        code -> tokens, atomic save, never prints secrets
~/hermes-huawei-sync/phase1_probe.py         read-only resultCode probe
~/hermes-huawei-sync/sync_huawei.py          puller; exit 0 ok / 2 auth expired / 3 other
~/hermes-huawei-sync/schema_validator.py     bounds + provenance gate
~/hermes-huawei-sync/data/{YYYY-MM-DD,latest,status}.json
```

Still open before automation is trusted: the 24 h token-concurrency test (does a VPS refresh log the
phone out?), and `TDEE_candidate = BMR + max(PAL_overhead, device_active)` staying a candidate for ~7
days of side-by-side data.
