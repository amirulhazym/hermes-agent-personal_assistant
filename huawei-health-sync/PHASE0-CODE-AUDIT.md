# Phase 0 — Code Audit (Huawei Health cloud client, vendored)

Date: 2026-11-15 16:1x MYT
Source: `and7ey/huawei_health` main branch (MIT), release v1.0.8 (2026-10-02)
Vendored to: `/home/ubuntu/hermes-huawei-sync/vendor/`

## Files + integrity

| File | Size | sha256 |
|---|---|---|
| `client.py` | 33,3xx bytes | `e8c04803c815d690b9c3e15a9861919ba147e67a94bb4244d52ecd245146a4b1` |
| `const.py` | 4,7xx bytes | `914e4995e710edf301badb01bd9024b75ac6d8e0f7e0cf80301d56e298442673` |

`__init__.py` empty. `client.py` was patched at import block (lines 30–81) to
`try: from .const import … / except ImportError: from const import …` so both
package import (`vendor.client`) and standalone import (`vendor/` on `sys.path`) work.
This patch was explicitly anticipated by the execution plan (Gate 0 stop condition).

## Dependencies

`NON_STDLIB: []` — modules loaded after `import const, client` are all in
`sys.stdlib_module_names` (gzip, json, logging, ssl, time, urllib*, uuid, dataclasses,
datetime, typing). No pip installs, no Home Assistant import.

## Auth surface (verified via `inspect.signature`)

```
authorization_url(*, client_id='10414141', scopes=SCOPES, language='en') -> str
authorization_code_from(answer: str) -> str | None
exchange_authorization_code(code: str, *, client_id='10414141', session_host=None, uid=None, timeout=30) -> Tokens
refresh_tokens(tokens: Tokens, *, client_id='10414141', timeout=30) -> Tokens
query_access_token(access_token: str, *, client_id='10414141', session_host=None, timeout=30) -> dict
Tokens(access_token=None, refresh_token=None, uid=None, site_id=None, expires_at=0.0,
       refresh_expires_at=0.0, session_host=None, on_change=None, dirty=False)
Tokens methods: apply, as_dict, needs_rotation, refresh_dead
```

## Read surface (`HuaweiHealthClient`)

```
__init__(tokens, *, host=None, device_code=None, version='and_health_16.1.6.320',
         token_type=2, app_id='com.huawei.health', client_id='10414141',
         language=None, timeout=30)
sports_stat(start:int, end:int, device_code:int|None=None) -> dict
sports_daily(start:int, end:int) -> dict
sports_detail(start:int, end:int, sport_types:Iterable[int], query_type=1, data_type=2) -> dict
health_stat(start:int, end:int, types:Iterable[int], device_code=0) -> dict
health_data(start:int, end:int, type_id:int, query_type=1, data_type=2) -> dict
daily_summary(days:int=3) -> list[dict]
health_summary(days:int=3, types=(7,9,11,12)) -> list[dict]
sessions(days:int=7) -> list[dict]
bind_devices() -> dict
rotate() -> None
post(path:str, extra:dict|None=None) -> dict      # generic escape hatch
```

## Endpoints (`const.READ_PATHS`)

```
sports_stat   /dataQuery/sport/v2/getSportsStat
sports_daily  /dataQuery/sport/getSportsDimenStat
sports_detail /dataQuery/sport/getSportsDataByTime
health_stat   /dataQuery/health/getHealthStat
health_data   /dataQuery/health/getHealthData
sync_versions /dataQuery/common/getSyncVersions
bind_devices  /profile/device/getBindDevice
```

`HEALTH_TYPES = {7: heart_rate, 9: professional_sleep, 11: stress, 12: exercise_intensity}`

## Error / limit constants (live values)

```
AUTH_FAILED_CODES   = (1002, 1004)
RT_INVALID_CODE     = 20020003
CODE_INVALID_CODE   = 20020001
BAD_HUID_CODE       = 20010004
INVALID_DEVICE_CODE = 30005
BY_TIME_WINDOW_DAYS = 10          # window > 10 days -> resultCode 1001
TOKEN_LIVE_SLACK    = 120         # seconds before expiry to rotate
REFRESH_TOKEN_TTL   = 15552000    # == 180 days
TOKEN_TYPE          = 2
HMS_APP_ID          = "10414141"
REDIRECT_URI        = "hms://redirect_url"
```

## Host tables — as shipped (NOT as the plan assumes)

```
APP_HOSTS = (
  'https://sportdata-drru.things.dbankcloud.ru',    # 1  RU
  'https://sportdata-dre.things.dbankcloud.com',    # 2  EU
  'https://sportdata-dra.things.dbankcloud.com',    # 3  ASIA  <-- MY should be this
  'https://healthdata.dbankcloud.cn',               # 4  CN
)
SESSION_HOSTS = (
  'https://healthcommon-drru.things.dbankcloud.ru', # 1  RU
  'https://healthcommon-dre.things.dbankcloud.com', # 2  EU
)                                                   # <-- NO 'dra' entry at all
```

Plan Part 0.3.3 asked to verify `sportdata-dra` and `healthcommon-dra` are "present and
prioritized first". Observed:
- `sportdata-dra` present but at index 2 (third), not first.
- `healthcommon-dra` **absent** from `SESSION_HOSTS` — i.e. the code's token
  obtain/refresh/query controller never targets the Asia shard.

Live DNS/HTTP probe (2026-11-15 16:xx MYT, from the Singapore VPS):
both `sportdata-dra.things.dbankcloud.com` and `healthcommon-dra.things.dbankcloud.com`
resolve to `159.138.91.5` and return `HTTP/1.1 403 Forbidden`,
`Content-Length: 554`, `ETag: "6a588861-22a"` (identical on both hosts → generic gateway
rejection for unauthenticated requests; proves reachability, not region entitlement).

**Decision needed before Phase 1** — not applied, because it is a behaviour change:
(a) rely on the client's own host iteration (drru → dre → dra) which the author says works,
(b) pin `dra` first for `APP_HOSTS` only (data reads) and add `healthcommon-dra` as an
    additional `SESSION_HOSTS` candidate, or
(c) leave code untouched and let `exchange_authorization_code(session_host=None)` fall back.

## Gap found vs the plan

Plan Part 2.1 says staleness must read `cloud_last_sync_at` from `getSyncVersions` /
`getBindDevice`. Reality: `getSyncVersions` has **no client wrapper** — only `bind_devices()`
and the generic `post(path, extra)`. So either a thin wrapper is written in Phase 2
(`client.post(READ_PATHS['sync_versions'], …)` with an unknown body schema), or the
staleness gate falls back to the latest record timestamp returned by `sports_stat` /
`health_stat`. The body schema for `getSyncVersions` is undocumented → must be inspected
live in Phase 1 before relying on it.

## Gate 0 results (raw)

```
700 /home/ubuntu/secrets
600 /home/ubuntu/secrets/huawei_tokens.json
750 /home/ubuntu/hermes-huawei-sync
-rw-rw-r-- 33K client.py ; -rw-rw-r-- 4.7K const.py
IMPORT_OK            (standalone, plan's exact command)
PACKAGE_IMPORT_OK    (vendor.client)
NON_STDLIB: []
```

Remaining Gate 0 item that is NOT machine-verifiable: owner confirmation that Huawei
Health + HMS Core are whitelisted on the Honor 600 Pro 5G (MagicOS 11.0) — plan Part 0.1.
