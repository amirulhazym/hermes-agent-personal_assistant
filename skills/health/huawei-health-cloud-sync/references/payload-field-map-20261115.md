# Payload field map — real response (2026-11-15, MY account)

## getSportsStat (today)

```json
{"resultCode": 0, "sportStat": [{
  "recordDay": 20261115, "timeZone": "+0800", "dataSource": 999, "version": 1794732721233,
  "sportBasicInfo": {"steps": 1754, "distance": 1626, "calorie": 109256,
                     "altitude": 10.4, "floor": 0, "duration": 71},
  "dimenDailyActivity": {"walkSteps": 1577, "climbSteps": 167, "walkCalories": 33201,
                         "walkDistances": 1478, "walkDurations": 68},
  "exerciseTimeBasic": {"totalMidHighIntensity": 25, "intensityMap": {"6": 1, "8": 24}},
  "activeHourBasic": {"countActiveHour": 9},
  "goalAchieveBasic": {"stepGoalValueStat": 10000, "calorieGoalValueStat": 515000}
}]}
```

- `calorie` / `walkCalories` / `calorieGoalValueStat` are **milli-kcal** (`109256 → 109.3 kcal`).
- `distance` is **metres**; `duration`, `walkDurations` are **minutes**.
- `daily_summary(days)` normalizes to `{date, steps, distance_m, kcal, duration_min, walk_min,
  active_hours, exercise_min, step_goal}` — use it to cross-check your own divisors.

## getHealthStat (types 7 / 9 / 11 / 12)

```json
{"resultCode": 0,
 "heartRateTotal": [{"heartRateBasic": {"maxHeartRate": 123, "minHeartRate": 50,
   "avgRestingHeartRate": 0, "lastHeartRate": 73, "lastRestHeartRate": 56}}],
 "professionalSleepTotal": [{"professionalSleep": {
   "fallAsleepTime": <epoch_ms>, "wakeupTime": <epoch_ms>,
   "sleepScore": 71, "sleepEfficiency": 96, "sleepLatency": 7,
   "lightSleepTime": 179, "deepSleepTime": 60, "dreamTime": 37,
   "awakeTime": 2, "allSleepTime": 276, "wakeupCnt": 1}}],
 "stressTotal": [{"stressBasic": {"measureCount": 30, "maxScore": 54, "meanScore": 43}}],
 "exerciseIntensityTotal": [{"exerciseIntensityBasic": {"totalMidHighIntensity": 25}}]}
```

Mappings: `dreamTime` = REM. `avgRestingHeartRate: 0` = no measurement (fall back to
`lastRestHeartRate`). Timestamps are epoch **ms** → fell asleep 03:01, woke 07:39, 276 min total.

## bind_devices

```json
{"resultCode": 0, "deviceInfos": [
 {"name": "VKP-NX9", "manufacturer": "HONOR", "productId": 32,
  "deviceData": "{\"mMap\":{\"model\":\"HONOR 600 Pro\",\"marketCode\":\"VKP-NX9\"}}"},
 {"name": "Sport Health Manual", "productId": 1},
 {"productId": 822, "uniqueId": "4SPBB26713101822#ANDROID2…"}
]}
```

`productId 822` = the watch. Useful for proving which devices feed the account.

## Constants worth quoting from `const.py`

```
AUTH_FAILED_CODES   = (1002, 1004)
RT_INVALID_CODE     = 20020003
CODE_INVALID_CODE   = 20020001     # expired or already-used auth code
BAD_HUID_CODE       = 20010004
INVALID_DEVICE_CODE = 30005
BY_TIME_WINDOW_DAYS = 10           # > 10 days -> resultCode 1001
TOKEN_LIVE_SLACK    = 120          # seconds before expiry to rotate
REFRESH_TOKEN_TTL   = 15552000     # 180 days
HMS_APP_ID          = "10414141"
REDIRECT_URI        = "hms://redirect_url"
```
