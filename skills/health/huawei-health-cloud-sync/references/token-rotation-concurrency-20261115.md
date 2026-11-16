# Token rotation concurrency — raw evidence (2026-11-15, MY account)

Runtime: Singapore VPS, Python 3.11.15, vendored `and7ey/huawei_health` client, `session_host`
`healthcommon-dra.things.dbankcloud.com`, `sportdata-dra...` for reads.

## A. Refresh while the access token is still valid = no-op

```
before  RT=4a68dcd93b3f  AT=a2f17972f3eb  refresh_expires_days=179.89
refresh_tokens(tokens)
after   RT=4a68dcd93b3f  AT=a2f17972f3eb  refresh_expires_days=179.89
RT_CHANGED=False  AT_CHANGED=False
```

Hashes are `sha256(value)[:12]`. Interpretation: inside the access-token lifetime the server hands back the
same pair, so a VPS refresh cannot invalidate a concurrently logged-in phone in this window.

## B. Forced rotations + reads

```
T0 baseline            : OK resultCode=0 kcal=428.584
rotate #1              : OK, new access expires_in 2897 s
T1 after rotate #1     : OK resultCode=0 kcal=428.584
rotate #2              : OK, new access expires_in 2897 s
T2 after rotate #2     : OK resultCode=0 kcal=428.584
```

(`expires_in` identical after both rotations — consistent with the same access token being reused.)

## C. Phone-side activity between rotations

Owner opened Huawei Health, pulled to refresh, browsed HR/sleep. Immediate VPS probe:

```
access_expires_in_s=1809
T3 PROBE (after app refresh): OK resultCode=0 kcal=431.549 steps=2408
```

So app-side refresh did not rotate the VPS pair out. Note: the app only rotates when *its* access token
expires, so this orders the test one way only — the reverse (post-expiry) direction needs step 5 of the
accelerated protocol.

## D. What the accelerated protocol still has to prove

- Post-`expires_at` refresh: does the minted pair change the refresh token? Baseline `4a68dcd93b3f` written to
  `data/gate4_rt_baseline.txt` at 19:45; probe scheduled 20:25 (after natural expiry ≈20:16).
- Verdict rules used by the probe script:
  - read OK + RT unchanged → PASS, phone and VPS can share the refresh token
  - read OK + RT changed → PASS but flag collision risk on the next phone-side rotation
  - read fails `20020003` / `1002` / `1004` → FAIL, treat as NO-GO and plan re-login or a fallback source

## E. Session-record absence vs daily aggregate (same day)

```
sportStat rows: 1   sportTypes: [0]   kcal 428584 (=428.584 kcal)  duration 96 min
exerciseTimeBasic.totalMidHighIntensity: 25 (pre-workout) -> 114 (post-workout)
getSportsDataByTime(today, SESSION_SPORT_TYPES) -> 3 records, all sportType 2, duration 1 min
getSportsDataByTime(today, tuple(range(1,15)))  -> resultCode 1001 parameter invalid
```

Indoor-cycling session never appeared in the cloud that evening even though the daily aggregate absorbed it.

## F. Memory readings (same payload, different runs)

```
Maximum resident set size (kbytes): 29516   (17:12)
RSS_KB=29644                                (17:35 cron)
RSS_KB=30164                                (19:15, includes token rotation)
```

812-line `client.py`; `daily_summary()` calls `sports_stat()` a second time.
