# Huawei Option A — Phase 0 code facts (verified 2026-11-15)

Source vendored: `and7ey/huawei_health` main (MIT, release v1.0.8 / 2026-10-02).
Local: `~/hermes-huawei-sync/vendor/{client.py,const.py}`, secrets at `~/secrets/huawei_tokens.json` (0600).
Pre-patch sha256: client `e8c0480…146a4b1`, const `914e499…298442673`.

## Constants that matter (live values from `const.py`)

```
HMS_APP_ID = "10414141"        APP_ID = "com.huawei.health"
APP_VERSION = "and_health_16.1.6.320"
REDIRECT_URI = "hms://redirect_url"
SCOPES = base.profile, healthkit/step.both, healthkit/activityrecord.both
AUTH_FAILED_CODES = (1002, 1004)   RT_INVALID_CODE = 20020003
CODE_INVALID_CODE = 20020001       BAD_HUID_CODE = 20010004
INVALID_DEVICE_CODE = 30005        BY_TIME_WINDOW_DAYS = 10   (wider window -> 1001)
TOKEN_LIVE_SLACK = 120s            REFRESH_TOKEN_TTL = 15552000  (== 180 days)
```

Read surface (`HuaweiHealthClient`): `sports_stat(start,end,device_code=None)`, `sports_daily`,
`sports_detail(start,end,sport_types)`, `health_stat(start,end,types)`, `health_data(...)`,
plus conveniences `daily_summary(days=3)`, `health_summary(days=3, types=(7,9,11,12))`,
`sessions(days=7)`, `bind_devices()`, `rotate()`, `post(path, extra)`.
`HEALTH_TYPES = {7: heart_rate, 9: professional_sleep, 11: stress, 12: exercise_intensity}`.

## Host tables — the plan's assumption is wrong

```
APP_HOSTS     = drru(.ru) , dre(.com) , dra(.com) , healthdata.dbankcloud.cn   # dra is THIRD
SESSION_HOSTS = healthcommon-drru(.ru) , healthcommon-dre(.com)                # NO dra entry
```

So "pin the Asia session host" is not a config toggle — `healthcommon-dra` is absent from the code's
token controller and would be a behaviour change needing an owner decision, not an autonomous edit.

## DNS/TLS probe (Singapore VPS, 2026-11-15)

```
sportdata-dra.things.dbankcloud.com     -> 159.138.91.5   HTTP/1.1 403  Content-Length 554  ETag "6a588861-22a"
healthcommon-dra.things.dbankcloud.com  -> 159.138.91.5   HTTP/1.1 403  Content-Length 554  ETag "6a588861-22a"
sportdata-dre / healthcommon-dre / *-drru also resolve
```

Identical body/ETag from two different regional hosts = generic gateway rejection. It proves reachability,
**not** that the host serves his MY account. Only the OAuth exchange can answer region.

## Standalone vendoring requires an import patch

`client.py` ships `from .const import (...)`; the plan's gate command (`sys.path.insert(vendor); import client`)
fails with `ImportError: attempted relative import with no known parent package`. Working patch (keeps both
import styles):

```python
try:                      # package: vendor.client
    from .const import (...)
except ImportError:       # standalone: vendor/ on sys.path
    from const import (...)
```

After the patch: `IMPORT_OK` (standalone) and `PACKAGE_IMPORT_OK` (package) both hold, `NON_STDLIB: []`
(verified by diffing loaded modules against `sys.stdlib_module_names`).

## Gap that breaks the planned staleness gate

`getSyncVersions` exists only as `READ_PATHS['sync_versions']` — there is **no** client wrapper (only
`bind_devices()` and the generic `post()`), and its request-body schema is undocumented. Either write a
thin wrapper after inspecting a live response, or fall back to the newest record timestamp from
`sports_stat` / `health_stat`. Do not promise `cloud_last_sync_at` before one of those exists.

## Alternatives, resolved (so they are not re-researched)

- `mryot/YotHealth` — official **Health Kit** REST (`healthkit-store.cloud.huawei.asia`,
  `client_id` + `client_secret`), i.e. it sits on the route that needs AppGallery registration and
  enterprise verification. Not a fallback for a personal account.
- `and7ey/huawei-health-docs` — exists (HTML, no license), companion docs only.
- Privacy-Centre "Request Your Data" (choose Health app) — official, free, multi-day latency; backfill only.
- Strava link-out — workouts only, no sleep/steps/RHR.
- Gadgetbridge — `gadgetbridge.org` is unreachable from this VPS (TCP reset, both web_extract and a real
  browser). Version/support claims about Fit 4 Pro are therefore **unverified here**; check from another
  network before quoting them.
