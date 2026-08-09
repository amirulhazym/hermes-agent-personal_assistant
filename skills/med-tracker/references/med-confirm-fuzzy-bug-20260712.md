# med_confirm.py Fuzzy Confirm Bug + Clock Drift + Unverified Calcium-Dexa Claim

Date: 2026-07-12
Skill: med-tracker

---

## 1. Fuzzy Drug-Level Confirm Corrupts Other Drugs in Slot

### What happened

`med_confirm.py <slot> <fuzzy_drug>` is documented as a drug-level confirm that should only mark the requested drug. On 2026-07-12 it silently marked **other required drugs in the same slot as taken at current VPS time**.

### Verified incidents

**Incident B — Dexa + Letram:**
- User: "Dexa aku dah makan 8am tadi, lupa pula nak telan letram sekali."
- Agent ran: `python3 ~/.hermes/scripts/med_confirm.py B dexa --at 08:00`
- Result:
  - `dexamethasone_1` → `taken@08:00` ✅
  - `levetiracetam_b` → `taken@08:09` ❌ (user said he forgot it)
- Overall slot B became `completed` instead of `partial`.

**Incident C — Calcium + Dexa:**
- User: "Both CC dah makan around 9.50AM tadi ... Dexa siang baru nak makan."
- Agent ran: `python3 ~/.hermes/scripts/med_confirm.py C calcium --at 09:50`
- Result:
  - `calcium` → `taken@09:50` ✅
  - `dexamethasone_2` → `taken@12:27` ❌ (user had NOT taken it)

### Pattern

The corruption happens on the **first drug-level confirm that creates the slot entry for the day**. Subsequent drug-level confirms in the same slot only add the requested drug without overwriting existing ones.

### Immediate mitigation

1. **Dry-run first** when confirming the first drug in a multi-drug slot:
   ```bash
   python3 ~/.hermes/scripts/med_confirm.py --dry-run C calcium --at 09:50
   ```
2. Inspect output. If any drug other than the requested one would become `taken`, do NOT run live.
3. After live confirm, verify immediately:
   ```bash
   python3 ~/.hermes/scripts/med_confirm.py --check C
   ```
4. If corruption occurred, reset only the wrongly-marked drug:
   ```bash
   python3 ~/.hermes/scripts/med_confirm.py --reset C dexamethasone_2
   ```

### Root-cause hypothesis

`confirm_drug()` may call `get_slot_entry()` or an initializer that writes default `taken` entries for all required drugs, then overwrites only the requested drug with the `--at` time. The other drugs retain the current-time default.

### Fix status

NOT YET FIXED in code. Until fixed, always dry-run + verify on first drug-level confirm of the day in a multi-drug slot.

---

## 2. VPS Clock Drift Corrupts Med Times

### What happened

`med_confirm.py` uses the VPS system clock via `get_now_hm()` whenever a time is not explicitly supplied or when it writes default entries. On 2026-07-12 the VPS clock drifted from the user's actual local time.

- User WhatsApp message timestamp: 09:15 +08
- VPS `TZ=Asia/Kuala_Lumpur date`: 12:29 +08
- Gap: ~3 hours 15 minutes

This contributed to the Dexa #2 corruption above: even though the user only confirmed CC at 09:50, Dexa #2 was written at 12:27 (VPS current time).

### Impact

- Confirmation timestamps can be hours off from user's real intake time.
- Chain timing (C → D → E) shifts by the drift amount.
- Cron reminders fire at wrong wall-clock times relative to the user's day.

### Mitigation

1. Always prefer explicit `--at HH:MM` from the user's stated time.
2. Check VPS time when a confirm looks odd:
   ```bash
   TZ=Asia/Kuala_Lumpur date '+%H:%M %Z'
   ```
3. Fix drift at source:
   ```bash
   sudo timedatectl set-ntp true
   # or set manually if NTP unavailable
   sudo timedatectl set-time 'YYYY-MM-DD HH:MM:SS'
   ```
4. Flag clock drift to the user explicitly.

---

## 3. Unverified Claim: "Calcium Chelates Dexamethasone"

### What happened

The agent proactively told the user:
> "Dexa dengan Calcium jangan serentak — calcium chelate Dexa, absorb turun."

The user asked for sources. The agent could not verify the claim.

### Sources checked

| Source | Result | Notes |
|--------|--------|-------|
| MedlinePlus (NIH) Dexamethasone | ❌ No mention | Checked full page for calcium/antacid/magnesium/aluminum |
| Medical News Today Dexamethasone | ❌ No mention | Searched page text for calcium/antacid/absorption |
| Wikipedia Dexamethasone | ❌ No mention | Searched page text for calcium/antacid |
| DailyMed (FDA labels) | ⚠ Inconclusive | Search loaded; did not locate specific calcium-carbonate interaction in accessible labels |
| Drugs.com interaction checker | 🚫 Blocked | Access Denied from VPS |
| PubMed | 🚫 Blocked | NCBI bot detection |
| Google Scholar | 🚫 Blocked | Google bot detection |

### Conclusion

**The dexamethasone-calcium carbonate chelation claim is UNVERIFIED in accessible sources.** The agent had to retract it. The user's routine of taking Dexa siang + Calcium Carbonate + Calcitriol together after lunch, as instructed by the doctor, is not contradicted by any source the agent could access.

### Correct behavior for future

1. Before stating any interaction, mechanism, or absorption claim, run:
   ```bash
   python3 ~/.hermes/scripts/med_interact.py validate
   python3 ~/.hermes/scripts/med_interact.py check dexamethasone calcium
   ```
2. If `med_interact.py` has no data, check 2-3 accessible authoritative sources.
3. If verification fails, say **"unverified"** or **"I couldn't find a source for that"** — do not present as fact.
4. The prescribing doctor's instructions override general web information unless a verified contraindication exists.

---

## Reproduction commands

```bash
# Verify current VPS time
TZ=Asia/Kuala_Lumpur date '+%H:%M %Z'

# Dry-run before a risky first drug-level confirm
python3 ~/.hermes/scripts/med_confirm.py --dry-run C calcium --at 09:50

# Inspect slot state
python3 ~/.hermes/scripts/med_confirm.py --check C

# Reset a wrongly-marked drug
python3 ~/.hermes/scripts/med_confirm.py --reset C dexamethasone_2

# Check interactions
python3 ~/.hermes/scripts/med_interact.py validate
python3 ~/.hermes/scripts/med_interact.py check dexamethasone calcium
```
