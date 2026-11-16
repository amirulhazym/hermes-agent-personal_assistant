# Huawei Health Cloud Sync & Workout Reconstructor (Option A)

Zero-cost, stdlib-only Python 3.11 ingestion pipeline that synchronizes daily biometric, sleep, heart-rate, body-weight, SpO2, and reconstructed indoor workout metrics from **Huawei Watch Fit 4 Pro** (`HarmonyOS 6.1.0.117`) into structured local JSON for **Hermes Agent**.

---

## 1. System Architecture & End-to-End Data Flow

Because Huawei's official enterprise Health Kit requires AppGallery business verification and manual privacy exports carry multi-day latency, this integration implements **Option A**: a reverse-engineered, read-only OAuth client targeting Huawei's consumer Asia (`dra`) cloud endpoints.

```text
+-----------------------------------+
|   Huawei Watch Fit 4 Pro          |
|   (HarmonyOS 6.1.0.117)           |
|   - 1-min HR during workouts      |
|   - 10-min baseline HR & SpO2     |
|   - TruSleep stages & steps       |
+-----------------+-----------------+
                  | Bluetooth (BLE)
                  v
+-----------------------------------+
|   Huawei Health App (Android)     |
|   (Honor 600 Pro 5G / MagicOS 11) |
|   - Hourly background cloud push  |
+-----------------+-----------------+
                  | HTTPS (OAuth 2.0 Bearer + x-token)
                  v
+-----------------------------------+
|   Huawei Cloud (Asia / DRA Shard) |
|   - sportdata-dra.things...       |
|   - healthcommon-dra.things...    |
+-----------------+-----------------+
                  | Cron: 09:30 / 15:00 / 22:30 MYT
                  v
+-----------------------------------+       +----------------------------------+
|   sync_huawei.py (Ubuntu VPS)     |------>| ~/secrets/huawei_tokens.json     |
|   - Pre-expiry token rotation     |       | (chmod 0600, outside Git repo)   |
|   - --finalize-yesterday @ 09:30  |       +----------------------------------+
+-----------------+-----------------+
                  |
                  v
+-----------------------------------+
|   workout_reconstructor.py        |
|   - Rebuilds indoor workouts from |
|     type=12 intensity + type=7 HR |
|   - Caps wrist-cadence walk kcal  |
|   - Merges user annotations       |
+-----------------+-----------------+
                  |
                  v
+-----------------------------------+       +----------------------------------+
|   schema_validator.py             |------>| data/YYYY-MM-DD.json             |
|   - Bounds & provenance gate      |       | data/latest.json                 |
|   - Lean-schema sanity check      |       | data/status.json                 |
+-----------------------------------+       +-----------------+----------------+
                                                              |
                                                              v
                                            +----------------------------------+
                                            | huawei_health_sync.sh + Hermes   |
                                            | - RSS gate (RSS_LIMIT_KB=40000)  |
                                            | - Dynamic TDEE & settling guard  |
                                            +----------------------------------+
```

---

## 2. Repository & Runtime Layout

```text
huawei-health-sync/                  # SSOT Repo Directory
├── README.md                        # Architecture, endpoints, math & operational guide
├── sync_huawei.py                   # Main CLI & cron orchestrator (atomic JSON writes)
├── workout_reconstructor.py         # Indoor session reconstructor & walk-cap engine
├── schema_validator.py              # Bounds, provenance & lean-schema sanity gate
├── exchange_code.py                 # One-shot OAuth authorization code -> token exchanger
├── phase1_probe.py                  # Read-only endpoint & device binding diagnostic probe
├── huawei_health_sync.sh            # Alert-only cron wrapper (tracked copy)
├── PHASE0-CODE-AUDIT.md             # Upstream client audit & stdlib verification
├── PHASE1-2-EVIDENCE.md             # Live DRA endpoint verification receipt
└── vendor/
    ├── __init__.py
    ├── client.py                    # Self-rotating OAuth & Huawei cloud HTTP client (MIT)
    └── const.py                     # Asia (DRA) host pins, scopes & protocol constants
```

**Runtime Separation (VPS Deployment):**
- **Execution Directory:** `/home/ubuntu/hermes-huawei-sync/` (contains Python modules, `vendor/`, `data/`, `logs/`, and `README.md`; does not hold `huawei_health_sync.sh`)
- **Active Cron Wrapper:** `/home/ubuntu/.hermes/scripts/huawei_health_sync.sh` (invoked by Hermes cron; enforces `RSS_LIMIT_KB=40000`)
- **Secret Store (Never Committed):** `/home/ubuntu/secrets/huawei_tokens.json` (`0600` permissions inside `0700` directory)

---

## 3. Reverse-Engineered Endpoints & Data Model

Huawei Cloud does not expose indoor non-GPS workouts (such as stationary cycling) in `/dataQuery/sport/getSportsDataByTime`. Instead, this pipeline synthesizes complete session records by combining daily totals with minute-level time-series streams:

| Endpoint | Type / Sport ID | Extracted Metrics | Role in Pipeline |
| :--- | :--- | :--- | :--- |
| `/dataQuery/sport/v2/getSportsStat` | `sportType: 0` | `steps`, `distance`, `calorie` (milli-kcal), `walkCalories`, `climbCalories`, `countActiveHour` | Authoritative daily active totals & calorie pool source |
| `/dataQuery/health/getHealthStat` | `types: (7, 9, 11, 12)` | `professionalSleep`, `heartRateBasic`, `stressBasic`, `totalMidHighIntensity` | Sleep architecture, resting HR, and daily stress summary |
| `/dataQuery/health/getHealthData` | `type: 12` (`EXERCISE_INTENSITY`) | Per-minute active timestamps (`exerciseType`) | Contiguous workout window detection (gap <= 3 min, duration >= 30 min) |
| `/dataQuery/health/getHealthData` | `type: 7` (`DYNAMIC_HEARTRATE`) | 1-minute resolution heart rate samples during workouts | True workout `avg_bpm`, `max_bpm`, and `min_bpm` |
| `/dataQuery/health/getHealthData` | `type: 8` (`WEIGHT_BODYFAT_BROAD`) | `bodyWeight` (kg) with 14-day chunked lookback | Dynamic weight anchor for calorie cap & BMR calculations |
| `/dataQuery/health/getHealthData` | `type: 16` (`BLOOD_OXYGEN_SATURATION`) | Daytime `avgSaturation` samples | Multi-sample daily `spo2_avg` and `spo2_latest` |
| `/dataQuery/sport/getSportsDataByTime` | `sportTypes: (3, 4, 9)` | Outdoor GPS sessions (cycling, running, swimming) | Overlap deduplication (`>= 50%` overlap marks `already_logged: true`) |

---

## 4. Energy Math & Calorie Attribution Logic

### A. Stationary-Cadence Walk Overlap Correction (`workout_active_pool`)
During indoor stationary cycling, wrist motion causes Huawei's step aggregator to book excess calories into `dimenDailyActivity.walkCalories`, which would otherwise under-attribute the workout pool when subtracted from daily active calories. When an unlogged workout block exists (`>= 30 min` and `>= 100 kcal`), effective walking expenditure is bounded by physical step cost:

$$\text{MaxWalkKcal} = \text{Steps} \times 0.035 \times \left(\frac{\text{Weight}_{\text{kg}}}{60.0}\right)$$

$$\text{WorkoutActiveKcal} = \text{TotalActiveKcal} - \min(\text{RawWalkKcal}, \text{MaxWalkKcal}) - \text{ClimbKcal}$$

*Observed benchmark (n=1, 2026-11-16 70-min indoor cycle @ 59.0 kg):* `380.8` total active - `57.5` capped walk (`111.1` raw) - `1.1` climb = **`322.2 kcal`**, vs. **`325 kcal`** displayed in the official Huawei Health mobile app (`2.8 kcal` / `0.86%` variance).

### B. Active vs. Gross Workout Calories
- **`active_kcal`:** Net exercise expenditure above rest (used in daily deficit calculations).
- **`estimated_gross_kcal`:** `active_kcal + (duration_min * (BMR / 1440))` (matches the gross headline figure displayed in the Huawei Health mobile app without double-counting BMR in TDEE).

### C. TDEE Floor Calibration Rule
To prevent double-counting watch calories on top of a PAL multiplier while avoiding under-counting on low-step days:

$$\text{TDEE} = \text{BMR} + \max(\text{BMR} \times 0.15,\ \text{DeviceActiveKcal})$$

---

## 5. CLI Usage & Automation

### Manual Commands
```bash
# 1. Standard sync for today (updates data/YYYY-MM-DD.json, data/latest.json, data/status.json)
python3 sync_huawei.py

# 2. Historical single-day backfill (updates data/YYYY-MM-DD.json only; leaves latest.json untouched)
python3 sync_huawei.py --date 20261114

# 3. Re-finalize yesterday's record (captures late-night activity after the 22:30 MYT cron)
python3 sync_huawei.py --finalize-yesterday

# 4. Attach an owner-confirmed sport label to a reconstructed workout block and re-sync
python3 sync_huawei.py --annotate 2026-11-16 17:33 "Indoor cycle"

# 5. Validate output schema & bounds
python3 schema_validator.py data/latest.json
```

### Automated Cron Schedule (`no_agent` Silent Contract)
`huawei_health_sync.sh` runs via Hermes cron at **09:30**, **15:00**, and **22:30 MYT**:
- **09:30 MYT:** Executes `--finalize-yesterday` first, then syncs today.
- **Silent Normal Path:** Emits `0 bytes` stdout when `auth_state == "VALID"`, `is_stale == false`, and `RSS_KB <= 40000`.
- **Alert-Only Path:** Emits a concise WhatsApp alert only on `auth_state == "EXPIRED"` (exit `2`), script failure (exit `3`), RSS breach (`> 40,000 KB`), or data staleness (`> 180 min`).

---

## 6. Security & Verification

- **Token Concurrency & Storage:** `vendor/client.py` rotates expiring access tokens atomically (`tmp -> fsync -> chmod 0600 -> os.replace`) while preserving the shared 180-day refresh token by design (no mobile app session eviction observed across live post-expiry cron rotations).
- **Zero-Secret Hygiene:** Tokens, device serials, and raw runtime JSON files (`data/*.json`) are excluded via `.gitignore` and verified by repository-wide `scripts/guard/secret-scan.sh`.
- **Contract Tests:**
  ```bash
  pytest tests/huawei/test_workout_attribution.py
  ```
