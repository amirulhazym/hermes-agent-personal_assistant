# Pattern G — med-auto-confirm Hook False Positive
## Root Cause Analysis & Structural Fix Plan

**Author:** MarryJane (MJ) — Native VPS Agent
**Date:** 2026-07-10
**Status:** DRAFT — for user review before insertion into audit documents
**Epistemic Standard:** Evidence-first. Every claim cites specific code lines, timestamps, and file content.

---

## 1. Executive Summary

Pada **2026-07-10 ~05:00:58**, med-auto-confirm hook (deployed 2026-07-09 sebagai structural fix untuk auto-log med confirmations) tersilap *false-positive match* pada chat user yang sedang berbincang tentang isu *20:00 dari semalam*. Hook tu execute `med_confirm.py A --at 20:00` dan cipta entry rosak:

```json
"A": {
  "2026-07-10": {
    "drugs": {
      "akurit_4":  {"status": "taken", "time": "20:00"},
      "pyridoxine":{"status": "taken", "time": "20:00"}
    },
    "overall": "completed"
  }
}
```

**Kesan:** 20:00 adalah masa depan (~13 jam dari sekarang jam 07:06). Sistem reminder lumpuh total — A dianggap "done", B's ready_time jadi 21:00 (bukan 08:00). Tiada reminder pagi ini untuk A mahupun B. Chain-state.json `today` terkunci pada 2026-07-09 (day-roll tak sempat jalan kerana gated di belakang silent-exit).

**Punca utama:** `SLOT_RE = \b[A-Ea-e]\b` — terlalu loose. Match *mana-mana* huruf A-E tunggal dalam apa jua konteks perbualan. Bila user sedang bincang "20:00 tu masalah semalam", hook nampak huruf "A" → SLOT_RE match, TIME_RE grab "20:00", dan `_already_logged()` pulang False (memang belum ada entry untuk hari ni) → execute.

---

## 2. Timeline Lengkap

### 2026-07-09 (Pre-Freeze)

| Masa | Event | Details |
|------|-------|---------|
| Pagi 9 Jul | Pharmacy swap: Akurit-4 → Akurit-2 | Dilaporkan oleh user |
| 07:49 | **med-auto-confirm hook deploy** | Structural fix: auto-log med confirmations from inbound messages BEFORE agent processes them. `HOOK.yaml` declares "Fail-open". |
| Sepanjang hari | 3 auditors (Real OpenCode, Z.ai, Gemini) menjalankan audit | Real OpenCode sahaja jumpa hook (F-22, O6) — label MEDIUM, risau "double-write race" tapi tak examine regex/false-positive. Z.ai + Gemini TAK jumpa F-22. |
| Malam 9 Jul | User dan Jane bincang isu 20:00 (Slot C ke? A ke?) | Perbualan ini jadi *ammunition* untuk false-positive esok |

### 2026-07-10 (Post-Audit)

| Masa (MYT) | Event | Bukti |
|------------|-------|-------|
| 05:00:58 | **med-auto-confirm hook FALSE POSITIVE** | `HOOK.yaml`: message mengandungi huruf "A" + masa "20:00" dari perbualan → SLOT_RE+TIME_RE match → `_already_logged('A','2026-07-10')`=False → execute `med_confirm.py A --at 20:00` |
| ~05:00:58 | **med-status.json kini rosak** | A/2026-07-10 = completed @ 20:00 (masa depan). Bukti: lines 99-111 med-status.json |
| 05:15 | cron tick → chain_calc --next | `is_confirmed('A')`→True → skip A. B's ready_time = 20:00+1h = ~21:00 > 05:15 → skip. `should_fire`=False → silent exit. Day-roll block (60-69) tak pernah sampai. |
| 06:00 → 07:00 | cron tick setiap 15 min | Sama pattern — should_fire=False setiap kali. Day-roll tak jalan. |
| 07:06 | User tanya "kenapa takde reminder?" | Saya trace, jumpa root cause. |

### Bukti Kewujudan Entry Rosak

**File: `~/.hermes/med-status.json` lines 99-111:**
```json
"A": {
  "2026-07-10": {
    "drugs": {
      "akurit_4":   {"status": "taken", "time": "20:00"},
      "pyridoxine": {"status": "taken", "time": "20:00"}
    },
    "overall": "completed"
  }
}
```

**`chain_calc.py --next` pada 07:06:**
```json
{
  "next_slot": "B",
  "next_ready_time": "21:00",
  "should_fire": false,
  "chain_str": "A ✅ 20:00 → B ~21:00 → C ~12:00 → D ~16:00 → E ~20:00"
}
```

**`chain-state.json` (frozen pada 07-09):**
```json
{
  "today": "2026-07-09",
  "last_reminder_times": {"E": "21:00"}
}
```

---

## 3. Root Cause Analysis (Detailed Code Trace)

### 3.1 The Hook — How It Works

**File: `hooks/med-auto-confirm/`** — komponen berikut:

```
hooks/med-auto-confirm/
├── HOOK.yaml        # Hook registration
└── handler.py       # The hook execution logic
```

**`HOOK.yaml` (verified line-by-line):**
```yaml
name: med-auto-confirm
description: Auto-log medication confirmations from inbound messages BEFORE the agent processes them, so med-status.json is always correct and the reminder cron stops. Fail-open.
trigger: on_message
run: handler.py
```

**`handler.py` logic (key sections):**

```python
# SLOT_REGEX — MATCHES ANY SINGLE LETTER A-E
SLOT_RE = re.compile(r'\b[A-Ea-e]\b', re.IGNORECASE)

# TIME_REGEX — MATCHES ANY TIME-LIKE STRING
TIME_RE = re.compile(r'(\d{1,2}):(\d{2})', re.IGNORECASE)

def _already_logged(slot: str, today: str) -> bool:
    """Check if slot already has an entry for today."""
    status = load_json(STATUS_FILE)
    entry = status.get('meds', {}).get(slot, {}).get(today)
    # BUG: Only checks existence — does NOT verify entry validity
    return entry is not None

def handle(message: str) -> dict:
    # Match slot letter
    slot_match = SLOT_RE.search(message)
    if not slot_match:
        return {"action": "skip", "reason": "no slot match"}
    
    # Match time
    time_match = TIME_RE.search(message)
    time_arg = f"--at {time_match.group()}" if time_match else ""
    
    slot_letter = slot_match.group().upper()
    
    # BUG: _already_logged only checks if entry EXISTS, not if it's VALID
    if _already_logged(slot_letter, today_str()):
        return {"action": "skip", "reason": "already logged"}
    
    # EXECUTE — no guard against future timestamps
    result = run_med_confirm(slot_letter, time_arg)
    return {"action": "confirm", "slot": slot_letter, "time": time_arg}
```

### 3.2 Mengapa False Positive Terjadi — Step-by-Step

**Step 1: SLOT_RE = `\b[A-Ea-e]\b` match**
- Pattern: word boundary + any single letter A-E + word boundary
- Match pada: literally ANY occurrence of "A", "B", "C", "D", or "E" in any English/Manglish sentence
- Contoh ayat trigger: "A **tu**", "**A**pa", "**C**uba", "**B**agi", "**D**ah", "**E**sok"
- **Pada kejadian 10 Jul:** User ada cakap pasal isu **"A"** (atau dalam konteks bincang "20:00 tu masalah semalam") — ayat tu ada huruf "A" → SLOT_RE match.
- **Root Cause:** Single letter regex terlalu greedy. Tiada context check (drug name, "slot A", "dah makan").

**Step 2: TIME_RE = `(\d{1,2}):(\d{2})` match**
- Pattern: any HH:MM format
- Match pada: ANY time string dalam message, termasuk bila user sedang *discuss* timing semalam
- **Pada kejadian 10 Jul:** Ayat user mengandungi "20:00" — ini adalah masa dari perbualan tentang isu semalam, BUKAN intake time untuk pagi ni.
- **Root Cause:** Hook tak bezakan "time mentioned in conversation" vs "time of actual medication intake."

**Step 3: `_already_logged('A', '2026-07-10')` return False**
- Semak adakah entry A untuk hari ni dalam med-status.json
- Pada 05:00:58, memang belum ada entry untuk 07-10 (hari baru)
- Return False → "belum logged" → proceed untuk confirm
- **Root Cause:** Guard hanya check EXISTENCE, tak check VALIDITY. Kalau ada entry dengan timestamp masa depan (corrupt), tetap return True. Tapi dalam kes ni memang belum ada entry.

**Step 4: `med_confirm.py A --at 20:00` execute**
- Hook call med_confirm.py dengan slot dan time yang salah
- `confirm_slot('A', '2026-07-10', '20:00')` tulis `akurit_4` dan `pyridoxine` sebagai taken pada 20:00
- **Tiada validasi:** "20:00" adalah masa depan >13 jam dari sekarang — tiada guard reject timestamp yang mustahil.

### 3.3 Cascading Effect — Macam Mana Reminder Mati

```
                    ┌─────────────────────────────────────────────────────────┐
                    │  Hook false positive cipta entry rosak (A ✅ 20:00)     │
                    │  med-status.json → A/2026-07-10 = completed @ 20:00   │
                    └────────────────────┬────────────────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │  1. is_confirmed('A') = True                            │
                    │     (entry.completed → overall='completed')             │
                    └────────────────────┬────────────────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │  2. Reminder loop skip A                                │
                    │     chain_calc.py:585: st['status'] == 'done' → skip    │
                    │     A tak masuk pertimbangan reminder                   │
                    └────────────────────┬────────────────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │  3. B's ready_time dikira dari A's actual time          │
                    │     chain_calc.py:432: b_min = a_min + 1h               │
                    │     a_min = 20:00 → b_min = 21:00                       │
                    │     (tapi sepatutnya A=06:00 → B~08:00)                 │
                    └────────────────────┬────────────────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │  4. Pada 06:00-07:06, B's ready_time = 21:00 > now     │
                    │     → B "belum ready" → skip                            │
                    │     chain_calc.py:615: if now >= ready_time... → False  │
                    └────────────────────┬────────────────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │  5. should_fire = False → chain_monitor.sh silent exit  │
                    │     chain_monitor.sh:34-36: exit 0 (silent)            │
                    └────────────────────┬────────────────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │  6. Day-roll block (lines 60-69) TAK PERNAH sampai      │
                    │     State 'today' kekal 2026-07-09                      │
                    │     Besok pun masih frozen — perpetual loop             │
                    └─────────────────────────────────────────────────────────┘
```

### 3.4 Secondary Bug: Day-Roll Gated Behind should_fire

**File: `scripts/chain_monitor.sh`, Lines 34-69:**

```bash
# Line 34-36: ⚠️ SILENT EXIT — escapes BEFORE day-roll
if [ "$SHOULD_FIRE" != "True" ]; then
    exit 0
fi

# Lines 47-91: Day-roll + state update — NEVER REACHED if should_fire=False
python3 -c "
...
today = _dt.date.today().isoformat()          # Line 61
state_today = state.get('today')               # Line 62
if state_today != today:                        # Line 63
    state['reminder_counts'] = {}              # Line 64
    state['last_reminder_sent'] = {}           # Line 65
    state['last_reminder_times'] = {}          # Line 66
    state['today'] = today                     # Line 67
...
"
```

**Masalah:** Kalau tiada reminder yang patut fire, script exit terus — tak sempat update `today`. Jadi bila A rosak → should_fire=False → exit → today tak update → esok should_fire masih False → infinite loop.

**FIX:** Day-roll MUST be extracted OUT of the should_fire gate. Ia patut jalan EVERY tick, regardless of whether a reminder fires.

---

## 4. Impact Analysis

### 4.1 Immediate Impact (10 Jul 2026)

| Kesan | Severity | Penjelasan |
|-------|----------|------------|
| Tiada reminder A pagi | **HIGH** | Med A (Akurit-2 + Pyridoxine) untuk TB Meningitis — terlepas reminder |
| Tiada reminder B pagi | **HIGH** | Med B (Dexamethasone #1 + Levetiracetam) — terlepas reminder |
| State `today` frozen | **MEDIUM** | chain-state.json kekal 07-09 — esok hari sama akan berulang |
| User kena tanya manually | **LOW** | User sedar masalah — tapi untuk ADHD user, expectation adalah sistem remind proaktif |

### 4.2 Systemic Risk

| Risk | Severity | Notes |
|------|----------|-------|
| Boleh repeat bila-bila | **HIGH** | SLOT_RE loose → mana-mana chat yang ada "A" + "HH:MM" boleh trigger |
| Terutama malam hari | **HIGH** | Bila user discuss timing petang/malam, TIME_RE boleh grab jam 20:00/21:00 → create entry untuk keesokan hari |
| Tiada audit trail | **HIGH** | Hook "fail-open" → errors are silent — agent dan user tak sedar hook buat apa |
| Perpetual loop jika frozen | **MEDIUM** | Day-roll gating → sekali frozen, forever frozen sampai manual fix |

### 4.3 Clinical Risk

- **TB Meningitis** drugs: Akurit-2 (Rifampicin, INH, Pyrazinamide, Ethambutol) + Dexamethasone (tapering)
- Terlepas dose = **clinical risk** (drug resistance for TB, relapse risk for TB Meningitis)
- System yang sepatutnya *prevent* missed dose, actually *caused* silent missed reminder

---

## 5. Why All 3 Auditors Missed This

### 5.1 What Each Found

| Auditor | Finding | Severity | What They Said | What They MISSED |
|---------|---------|----------|----------------|------------------|
| **Real OpenCode** (root `audit-01/02/03.md`) | F-22 | MEDIUM | "med-auto-confirm hook silently auto-writes med state pre-agent… undocumented automation… fail-open" | ❌ Regex SLOT_RE, false-positive mechanism, timestamp validation |
| **Z.ai** | D9 (audit-01) | GAP | "Guardrails cover text output, not state writes" — hanya anti-fabrication hook, bukan med-auto-confirm | ❌ Langsung tak jumpa med-auto-confirm hook sebagai entiti |
| **Gemini** (`opencode-audit/`, INCOMPLETE — rate-limited 9 Jul) | — (not found) | — | Audit tak siap (rate limit). Tiada F-22 / med-auto-confirm mention dalam file. | ❌ Missed entirely — audit truncated sebelum sampai hooks section |

### 5.2 Kenapa Mereka Miss — 4 Reasons

**1. Timing — audit dilakukan SEBELUM false positive terjadi.**

| Event | Time |
|-------|------|
| hook deploy (structural fix pre-freeze) | 2026-07-09 pagi |
| Real OpenCode, Z.ai, Gemini audits | 2026-07-09 (siang/malam) |
| **False positive pertama** (entry A/07-10 20:00) | **2026-07-10 05:00:58** |
| User report "takde reminder" | 2026-07-10 07:06 |

The false positive hadn't happened yet when audits ran — it happened THE NEXT DAY. Auditors can't catch a runtime failure that hasn't occurred. **But they could have caught the design flaw (loose regex) via code review** — which they all missed.

**2. Static code analysis trap.**

Semua auditor baca `HOOK.yaml`:
```yaml
description: Auto-log medication confirmations from inbound messages BEFORE the agent processes them
```

Mereka stop kat sini — nampak "auto-log" dan "fail-open", terus fokus pada isu "double-write race condition" (hook + med_confirm.py separate paths). **Tak pernah trace handler.py untuk examine SLOT_RE regex atau simulate false-positive scenario.**

Ini classic static-vs-runtime gap: hook nampak "innocent" dari segi architecture, tapi regex yang harmless dalam isolation jadi masalah dalam runtime dengan conversational context.

**3. Regex invisibility — `\b[A-Ea-e]\b` nampak standard.**

Pattern `\b[A-Ea-e]\b` adalah *word boundary + character class* — nampak macam regex biasa untuk detect slot letters. Auditor (yang bukan regex security expert) tak trigger alarm sebab:
- Nampak macam standard character matching
- Tak nampak dia akan match kata-kata biasa macam "Apa", "Bagi", "Cuba"
- Dalam isolation memang tak nampak bahaya — baru nampak bila test dengan real message corpus

**4. Focus bias — "double-write race" lebih obvious.**

Semua auditor alert pada surface-level issue (two code paths writing same state — hook vs agent vs med_confirm.py). Mereka tulis finding dan recommendation untuk reconcile. Tapi tak ada yang tanya: **"Apa jadi kalau hook tu tersalah match?"** — soalan runtime behaviour, bukan static analysis.

### 5.3 This is a New Pattern (Pattern G)

Dari segi failure mode classification, ini **tidak covered** oleh Pattern A-E yang sedia ada:

| Pattern | Description | Covers This? |
|---------|-------------|-------------|
| Pattern A | Agent reset med data tanpa check history | ❌ |
| Pattern B | Agent hallucinate drug info | ❌ |
| Pattern C | Cron silent failure | ❌ (sebab cascading effect, bukan cron failure) |
| Pattern D | Over-assume reset | ❌ |
| Pattern E | Wrong timezone/time parsing | Sebahagian (TIME_RE grab wrong time, tapi punca utama SLOT_RE) |
| **Pattern G** (NEW) | **Hook auto-log false positive — regex match chat conversation (bukan intake) → cipta entry rosak dengan timestamp dari context perbualan** | ✅ |

**Pattern G definition:**
> *"An auto-confirmation hook with loose regex patterns (SLOT_RE + TIME_RE) false-positive matches a conversational message that discusses medication topics (not confirming intake), extracts a time value from the discussion context, and creates a corrupt med-status entry with a future/impossible timestamp. The corrupt entry suppresses all subsequent reminders for that slot and downstream dependent slots."*

---

## 6. Structural Fix Plan

### 6.1 Immediate Fixes (after freeze lifted — order by safety)

| # | Fix | File | Complexity | Risk |
|---|-----|------|------------|------|
| **G-1** | **Tighten SLOT_RE — mesti ada medication context** | hooks/med-auto-confirm/handler.py | S | Low |
| **G-2** | **Add timestamp validation — reject future times** | hooks/med-auto-confirm/handler.py | S | None |
| **G-3** | **Add context guard — only auto-log on intent keywords** | hooks/med-auto-confirm/handler.py | M | Low |
| **G-4** | **Fix _already_logged — validate entry validity, not just existence** | hooks/med-auto-confirm/handler.py | S | None |
| **G-5** | **Move day-roll reset outside should_fire gate** | scripts/chain_monitor.sh | S | Low |
| **G-6** | **Add audit log — record every hook execution** | hooks/med-auto-confirm/handler.py | M | None |
| **G-7** | **Add regression test for false-positive scenario** | tests/ (new) | M | None |

#### G-1: Tighten SLOT_RE

**Current (too loose):**
```python
SLOT_RE = re.compile(r'\b[A-Ea-e]\b', re.IGNORECASE)
```

**Proposed (two-pass approach — most robust):**
```python
# Pass 1: Detect medication intent context
MED_INTENT_RE = re.compile(
    r'\b('
    r'slot\s+[A-Ea-e]|'       # "slot A", "slot B"
    r'dah\s+makan\s+[A-Ea-e]|' # "dah makan A"
    r'dah\s+minum\s+[A-Ea-e]|' # "dah minum A"
    r'confirm\s+[A-Ea-e]|'     # "confirm A"
    r'done\s+[A-Ea-e]|'        # "done B"
    r'ambil\s+[A-Ea-e]|'       # "ambil A"
    r'[A-Ea-e]\s+dah\b|'       # "A dah" (Manglish: "A dah makan")
    r'[A-Ea-e]\s+done|'        # "A done"
    r'[A-Ea-e]\s+siap|'        # "A siap"
    r'[A-Ea-e]\s+habis|'       # "A habis"
    r'akurit|dexa\b|letra|calcium|calcitriol|panto|'  # drug names
    r'b\s*complex|pyridoxine|levetiracetam|'           # drug names (full)
    r')\b',
    re.IGNORECASE
)
```

**Rationale:** Single letter A-E is too common in natural language. By requiring medication intent keywords around the letter (or a drug name), we drastically reduce false positives. The drug name match covers cases where user just says "dah makan akurit" without the slot letter.

**Alternative (minimal change — if two-pass too complex):**
```python
SLOT_RE = re.compile(
    r'\b(?:'
    r'(?:dah\s+makan|dah\s+minum|confirm|done|ambil|siap|habis)\s+([A-E])|'
    r'([A-E])\s+(?:dah|done|siap|habis)|'
    r'slot\s+([A-E])'
    r')\b',
    re.IGNORECASE
)
```
(Match only if slot letter has medication intent nearby.)

#### G-2: Timestamp Validation

**Add sebelum execute med_confirm.py:**

```python
from datetime import datetime, timedelta
MYT = ZoneInfo('Asia/Kuala_Lumpur')

def validate_timestamp(time_str: str) -> bool:
    """Reject timestamps that are in the future or impossible."""
    try:
        now = datetime.now(MYT)
        parsed = datetime.strptime(time_str, '%H:%M').replace(
            year=now.year, month=now.month, day=now.day,
            tzinfo=MYT
        )
        # Future timestamp (more than 2h ahead) = impossible untuk pagi ni
        if parsed > now + timedelta(hours=2):
            return False
        return True
    except ValueError:
        return False
```

**Changes in handler.py:**
```python
if time_match:
    time_str = time_match.group()
    if not validate_timestamp(time_str):
        # Silent reject — log but don't execute
        logger.warning(f"Rejected future timestamp {time_str} for slot {slot_letter}")
        return {"action": "skip", "reason": "future_timestamp"}
```

**Note:** "2h buffer" because user might say "dah makan A 07:00" at 06:30 — 30 min is okay. 20:00 at 05:00 is >13h ahead → reject.

#### G-3: Context Guard

**Add structural guard — verify message is genuinely a medication confirmation:**

```python
def is_med_confirmation(message: str) -> bool:
    """
    Determine if message is a genuine medication confirmation vs general chat.
    
    Returns True if:
    1. Message contains medication intent keywords (dah makan, done, etc.)
    2. Message is SHORT + within 30 min of a reminder fire (simple reply)
    
    Returns False if:
    - Message is long (discussion/analysis, not confirmation)
    - Message has no medication confirmation structure
    """
    # Quick check: intent keywords must be present
    intent_keywords = [
        'dah makan', 'dah minum', 'dah ambil',
        'done', 'confirm', 'siap', 'habis',
        'yes', 'ya', 'yup', 'ok', 'okay'
    ]
    message_lower = message.lower().strip()
    
    # Direct intent match
    for kw in intent_keywords:
        if kw in message_lower:
            return True
    
    # Short reply within reminder window (30 min) — handled by checking
    # if a reminder was recently sent for the matched slot
    # (requires state lookup — see G-4)
    
    return False
```

#### G-4: Fix _already_logged — Check Entry Validity

**Current:**
```python
def _already_logged(slot: str, today: str) -> bool:
    entry = status.get('meds', {}).get(slot, {}).get(today)
    return entry is not None  # BUG: hanya check existence
```

**Proposed:**
```python
def _already_logged(slot: str, today: str) -> bool:
    """Check if slot has a VALID entry for today.
    Returns True only if entry exists AND is not corrupt (future timestamp)."""
    entry = status.get('meds', {}).get(slot, {}).get(today)
    if entry is None:
        return False
    
    # Check for future timestamps — treat as corrupt
    if isinstance(entry, dict):
        if 'time' in entry and _is_future_time(entry['time']):
            logger.warning(f"Corrupt entry for {slot}/{today}: future time {entry['time']}")
            return False  # Allow overwrite
        if 'drugs' in entry:
            for drug_id, drug_info in entry['drugs'].items():
                if drug_info.get('time') and _is_future_time(drug_info['time']):
                    logger.warning(f"Corrupt drug entry {drug_id} for {slot}/{today}: future time")
                    return False  # Allow overwrite
    
    return True

def _is_future_time(time_str: str) -> bool:
    """Check if a time string is in the future (invalid for medication log)."""
    try:
        now = datetime.now(MYT)
        parsed_time = datetime.strptime(time_str, '%H:%M').replace(
            year=now.year, month=now.month, day=now.day, tzinfo=MYT
        )
        return parsed_time > now + timedelta(hours=1)
    except (ValueError, TypeError):
        return False
```

#### G-5: Move Day-Roll Outside should_fire Gate

**File: `scripts/chain_monitor.sh`**

**Current structure (bug):**
```
Step 1: chain_calc --next → should_fire?
Step 2: if NOT should_fire → exit 0  ← exits BEFORE day-roll
Step 3: day-roll reset (update today)
Step 4: increment counters
```

**Proposed structure (fix):**
```
Step 1: ALWAYS run day-roll reset first ← independent of should_fire
Step 2: chain_calc --next → should_fire?
Step 3: if NOT should_fire → exit 0
Step 4: increment counters
```

**Concrete code change:**

Extract the day-roll block from inside the `python3 -c` at lines 47-91 and place it as a SEPARATE `python3 -c` call BEFORE the should_fire check:

```bash
# ── Step 0: Day-boundary reset (ALWAYS run, independent of should_fire) ──
python3 -c "
import json, sys, datetime as _dt
from pathlib import Path

state_file = Path('$STATE_FILE')
try:
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
except (json.JSONDecodeError, IOError):
    state = {}

today = _dt.date.today().isoformat()
state_today = state.get('today')
if state_today != today:
    state['reminder_counts'] = {}
    state['last_reminder_sent'] = {}
    state['last_reminder_times'] = {}
    state['today'] = today
    state.pop('slot_overrides', None)
    state_file.write_text(json.dumps(state, indent=2))
" 2>/dev/null || true

# ── Step 1: Check if reminder should fire ──────────────────────────────────
NEXT_OUTPUT=$(python3 "$CALC_PY" --next 2>/dev/null) || {
    ...
}
```

#### G-6: Add Audit Log

**Add logging to handler.py so every hook execution is recorded:**

```python
import logging
from pathlib import Path

AUDIT_LOG = Path.home() / '.hermes' / 'logs' / 'med-auto-confirm-audit.log'
logger = logging.getLogger('med-auto-confirm')

def log_hook_action(action: str, slot: str, time: str, message: str, reason: str):
    """Log every hook execution for audit trail."""
    entry = {
        'timestamp': datetime.now(MYT).isoformat(),
        'action': action,           # 'confirm', 'skip'
        'slot': slot,
        'time_matched': time,
        'message_preview': message[:100],
        'reason': reason
    }
    with open(AUDIT_LOG, 'a') as f:
        f.write(json.dumps(entry) + '\n')
```

**Usage at each decision point:**
```python
if not slot_match:
    log_hook_action('skip', '-', '-', message, 'no_slot_match')
    return ...

if _already_logged(slot, today):
    log_hook_action('skip', slot, '-', message, 'already_logged')
    ...

# If passes all guards and executes:
log_hook_action('confirm', slot, time_str, message, 'auto_confirmed')
result = run_med_confirm(slot, time_arg)
```

#### G-7: Regression Test

**New test file: `tests/test_med_auto_confirm_hook.py`**

Test cases yang MUST pass:
1. **Test false-positive conversation** — message "A tu 20:00 tu masalah semalam" → should NOT create entry
2. **Test genuine confirmation** — "dah makan A" → should create entry (no time = use now)
3. **Test genuine confirmation with time** — "dah makan A 07:00" → should create entry at 07:00
4. **Test future timestamp rejection** — "dah makan A 20:00" at 07:00 → should reject (timestamp >2h future)
5. **Test drug name match** — "dah makan akurit" → should resolve to slot A, create entry
6. **Test short reply to reminder** — user replies "ok" or "done" within 30 min of A reminder → should confirm
7. **Test long discussion** — "A tu sebenarnya... pasal 20:00 semalam... B pun..." → should NOT match

---

## 7. Insertion Map — Where to Add in Audit Documents

Arahan untuk user: buka setiap file audit, cari section yang dinyatakan, dan add content baru sebagai subsection. **Jangan ganti atau edit content sedia ada** — cuma tambah subsection baru.

### 7.1 Real OpenCode Audit Files (root: audit-01/02/03.md)

#### File: `audit-01-system-context.md`

| Add After | Content Type | Description |
|-----------|-------------|-------------|
| Section 5: "Integration Layer" (deep-dive) | **New subsection: 5.2 med-auto-confirm Hook Risk** | Add details about the hook: location, what it does, SLOT_RE regex, risk of false positive. Refer to F-22 for severity. |
| OR after line 107 (mentions med-auto-confirm) | **Expanded paragraph** | The existing line says "hooks/med-auto-confirm/ ... auto-writes med state pre-agent… Fail-open". Expand to include: "Post-audit discovery (10 Jul): SLOT_RE = \b[A-Ea-e]\b is too loose — caused false-positive on 10 Jul 05:00:58, creating corrupt med-status entry A/2026-07-10 @ 20:00 (future time). See PATTERN-G-fix-doc.md for full details." |

**Section heading to add:**
```markdown
### 5.2 Critical Hook Risk (Discovered Post-Audit, 2026-07-10)

**Severity: CRITICAL (was MEDIUM in F-22) — must be upgraded.**

The `med-auto-confirm` hook's SLOT_RE (`\b[A-Ea-e]\b`) is too loose and caused a
**false-positive medication entry** on 2026-07-10 at 05:00:58. See
`PATTERN-G-fix-doc.md` for full root-cause analysis + fix plan.

**Quick summary:**
- Hook matched a conversational message discussing yesterday's 20:00 issue
- SLOT_RE matched letter "A", TIME_RE grabbed "20:00" from discussion context
- med_confirm.py executed → created corrupt entry A/2026-07-10 @ 20:00 (future time)
- Entire reminder system disabled for slots A and B all morning
- **Pattern G** — new failure mode: auto-log hook false-positive on chat
```

#### File: `audit-02-findings.md`

| Add After | Content Type | Description |
|-----------|-------------|-------------|
| Finding F-22 (med-auto-confirm hook) | **Upgrade F-22 from MEDIUM to CRITICAL** | Add note: "POST-AUDIT UPDATE (2026-07-10): F-22 severity upgraded to CRITICAL. The hook caused a false-positive medication entry on 2026-07-10. Full analysis in PATTERN-G-fix-doc.md. Recommendation: apply G-1 through G-7 fixes." |
| After F-24 | **New finding: F-25 [CRITICAL]** | Document the false-positive as a new finding: regex too loose, timestamp not validated, day-roll gating bug exposed. |

**New finding text to add:**
```markdown
### F-25 [CRITICAL][NEW — POST-AUDIT] med-auto-confirm hook false positive
(PATTERN G) — Slot regex too loose, no timestamp validation

- **File:** `hooks/med-auto-confirm/handler.py` (SLOT_RE, _already_logged)
- **Date discovered:** 2026-07-10 (after audit completed — runtime failure)
- **Root cause:** SLOT_RE = `\b[A-Ea-e]\b` matches ANY single letter A-E
  in natural language. Combined with TIME_RE grabbing any HH:MM from
  conversational context, the hook can false-positive on messages that
  DISCUSS medication timing rather than CONFIRM intake.
- **Incident:** 2026-07-10 05:00:58 — user discussed yesterday's "20:00"
  issue; hook matched "A" + "20:00"; created corrupt med-status entry:
  A/2026-07-10 = akurit_4 @ 20:00, pyridoxine @ 20:00.
- **Impact:** Entire reminder chain disabled for 10 Jul morning (A + B).
  chain-state.json 'today' frozen on 2026-07-09 (day-roll gating bug
  exposed — see chain_monitor.sh:34-36 vs 60-69).
- **Severity:** CRITICAL (patient-safety adjacent — TB Meningitis drugs
  missed their reminder window).
- **Fix:** See PATTERN-G-fix-doc.md, fixes G-1 through G-7.
- **New failure pattern:** Pattern G — "Auto-confirmation hook false
  positive on chat conversation (not intake) creates corrupt entry with
  timestamp from conversational context."
```

#### File: `audit-03-execution-plan.md`

| Add After | Content Type | Description |
|-----------|-------------|-------------|
| Overhaul Phase O6 (reconcile med-auto-confirm hook) | **Add O6 sub-items: O6a-O6g** | Detail the 7 fixes (G-1 through G-7). Change O6 priority from MEDIUM to CRITICAL. Add dependency: must be done before O8 (med engine). |

**Addition text:**
```markdown
### O6 Update — CRITICAL priority (upgraded from MEDIUM post-audit)

**Post-audit incident (2026-07-10):** Hook caused false-positive medication
entry. The F-22 finding must be fixed before any other med pipeline changes
(O8), because the hook runs BEFORE the agent and can corrupt state
regardless of engine design.

**O6 sub-fixes (from PATTERN-G-fix-doc.md):**

| Sub-ID | Fix | File | Priority |
|--------|-----|------|----------|
| O6a | Tighten SLOT_RE — require medication context | handler.py | P0 |
| O6b | Add timestamp validation — reject future times | handler.py | P0 |
| O6c | Add context guard — intent keywords only | handler.py | P0 |
| O6d | Fix _already_logged — validate entry validity | handler.py | P0 |
| O6e | Move day-roll outside should_fire gate | chain_monitor.sh | P0 |
| O6f | Add audit log for hook executions | handler.py | P1 |
| O6g | Regression tests for false-positive scenarios | tests/ | P1 |

**Dependency chain:**
O6 → O8 (don't build new med engine while hook can corrupt its state)
```

### 7.2 Z.ai Audit Files

#### File: `2026-07-09-zai-fresh-audit/zai-audit-01-system-context.md`

| Add After | Content Type | Description |
|-----------|-------------|-------------|
| Section D9: "Hooks & guardrails" | **Add note at end of D9** | Z.ai's D9 notes anti-fabrication hook covers text not state. Add: "POST-AUDIT DISCOVERY: med-auto-confirm hook (separate hook) has a CRITICAL false-positive vulnerability. See PATTERN-G-fix-doc.md for details." |
| Section 5: "What I could NOT verify" | **Add new UNVERIFIED item** | Add item: "med-auto-confirm hook regex patterns — not examined for false-positive potential" |

#### File: `2026-07-09-zai-fresh-audit/zai-audit-02-findings.md`

| Add After | Content Type | Description |
|-----------|-------------|-------------|
| End of Section D9/Hooks (after "Hooks cover text, not state") | **New finding: Z-F-01 [CRITICAL]** | Pattern G — med-auto-confirm hook false positive. Detail the incident. |

**New finding text:**
```markdown
### Z-F-01 [CRITICAL][POST-AUDIT] med-auto-confirm hook false-positive (Pattern G)

**Date discovered:** 2026-07-10 (runtime incident — after audit completed)

**Description:** The `med-auto-confirm` hook (under `hooks/med-auto-confirm/`)
uses `SLOT_RE = \b[A-Ea-e]\b` to match medication slot letters. This regex
matches ANY single letter A-E in natural language, including common Manglish
words ("Apa", "Bagi", "Cuba", "Dah", "Esk". When combined with
`TIME_RE = (\d{1,2}):(\d{2})` which grabs any HH:MM from the message, a
conversational message discussing medication timing (not confirming intake)
can trigger the hook and create a corrupt med-status entry.

**Incident** (2026-07-10 05:00:58):
- User discussed previous day's "20:00" timing issue
- SLOT_RE matched letter "A" in message
- TIME_RE grabbed "20:00" from discussion context
- `_already_logged('A', '2026-07-10')` returned False (no entry yet)
- Hook executed `med_confirm.py A --at 20:00`
- Created A/2026-07-10 = akurit_4 + pyridoxine @ 20:00 (future time)

**Impact:**
- `is_confirmed('A')` → True → A reminder suppressed
- B's ready_time = 20:00+1h = 21:00 → B also suppressed
- silent exit → day-roll never executed → state frozen on 07-09
- No morning reminders for TB Meningitis drugs

**Severity:** CRITICAL (patient-safety adjacent)
**Fix:** See PATTERN-G-fix-doc.md (G-1 through G-7)
**Pattern:** **Pattern G** — new failure mode not covered by Patterns A-E

**Note:** Z.ai's original audit examined anti-fabrication hook only and
concluded "guardrails cover text, not state writes." This is CORRECT but
INCOMPLETE — the med-auto-confirm hook (different hook) was not audited;
it is a state-MUTATING hook with loose input validation.
```

#### File: `2026-07-09-zai-fresh-audit/zai-audit-03-execution-plan.md`

| Add After | Content Type | Description |
|-----------|-------------|-------------|
| After P17 (add pre-write guard on med state mutations) | **Add Z-P17a — fix med-auto-confirm hook as P0** | The existing P17 is generic. Add specific sub-fix for the hook. Must be done before P6 (med engine). |

### 7.3 Gemini (Root) Audit Files

The Gemini audit files live in the `opencode-audit/` folder. You instructed Gemini to "act as OpenCode" by pasting the v2.2 prompt (which carried OpenCode context), so Gemini's output mimics OpenCode's structure and even labels itself "Auditor: OpenCode" internally — but its audit was **rate-limited on 9 Jul and is INCOMPLETE**. Critically, Gemini's files do **NOT** currently contain F-22 (med-auto-confirm) — that finding is missing because the audit truncated before reaching the hooks section. **When you continue Gemini's session, ensure it adds F-22 + the false-positive analysis.** For now, the insertion points below tell you where to manually add the content.

#### File: `opencode-audit/audit-01-system-context.md`

| Add After | Content Type |
|-----------|-------------|
| Section 8: "Integration Layer" (the paragraph mentioning med-auto-confirm) | Expand to add false-positive risk — same as Real OpenCode 5.2 (Section 7.1) |

#### File: `opencode-audit/audit-02-findings.md`

| Add After | Content Type |
|-----------|-------------|
| (ADD — currently MISSING) F-22 | Gemini's file has NO F-22. Add it as a NEW finding: "med-auto-confirm hook silently auto-writes med state pre-agent… fail-open" + post-audit incident note. Severity MEDIUM → CRITICAL. |
| After F-24 (last finding before "OVERHAUL ADDENDUM — Resolved") | Add F-25 [CRITICAL] — same content as Real OpenCode F-25 above (Section 7.1) |

#### File: `opencode-audit/audit-03-execution-plan.md`

| Add After | Content Type |
|-----------|-------------|
| Overhaul Phase O6 | Add O6 sub-items (O6a-O6g) with dependency: O6 must precede O8 (same as Real OpenCode Section 7.1) |

---

## 8. Summary: File Change Map

### Files That Need Code Changes (after freeze lifted)

| File | Change | Fix Reference |
|------|--------|---------------|
| `hooks/med-auto-confirm/handler.py` | Tighten SLOT_RE, add timestamp validation, add context guard, fix _already_logged, add audit log | G-1, G-2, G-3, G-4, G-6 |
| `hooks/med-auto-confirm/HOOK.yaml` | Update description to reflect new safety measures | G-1..G-6 |
| `scripts/chain_monitor.sh` | Move day-roll before should_fire gate | G-5 |
| `tests/test_med_auto_confirm_hook.py` (NEW) | Regression tests | G-7 |

### Files That Need Document Insertions (manual, by user)

| File | Type | Section to Add |
|------|------|----------------|
| `audit-01-system-context.md` (root, Real OpenCode) | New subsection | 5.2 Critical Hook Risk |
| `audit-02-findings.md` (root, Real OpenCode) | Upgrade F-22 + New F-25 | F-25 [CRITICAL] Pattern G |
| `audit-03-execution-plan.md` (root, Real OpenCode) | O6 update (sub-items O6a-O6g) | Upgrade priority to CRITICAL |
| `zai-audit-01-system-context.md` | D9 note + new UNVERIFIED item | Post-audit discovery note |
| `zai-audit-02-findings.md` | New Z-F-01 finding | Z-F-01 [CRITICAL] Pattern G |
| `zai-audit-03-execution-plan.md` | New Z-P17a sub-fix | Hook fix as P0 priority |
| `opencode-audit/audit-01-system-context.md` (Gemini, INCOMPLETE) | Section 8 note (ADD — Gemini missed this) | Hook false-positive risk |
| `opencode-audit/audit-02-findings.md` (Gemini, INCOMPLETE) | ADD F-22 + New F-25 (Gemini missed these) | F-25 [CRITICAL] |
| `opencode-audit/audit-03-execution-plan.md` (Gemini, INCOMPLETE) | O6 sub-items (ADD — Gemini missed) | O6a-O6g, dependency on O8 |

---

## 9. Provenance & Timestamp Tracking (for alignment)

Use this to map each audit file to its true source. The folder names are MISLEADING:

| Source | Folder / Path | mtime (MYT) | Status | Notes |
|--------|---------------|-------------|--------|-------|
| **Z.ai** | `2026-07-09-zai-fresh-audit/` | 18:41 (audit-01/03), 19:40 (audit-02) | ✅ DONE | First auditor. Missed med-auto-confirm (only anti-fabrication hook in D9). |
| **Gemini** | `opencode-audit/` | **19:18:38 (all 3 identical)** | ⚠️ INCOMPLETE — rate-limited | Acted "as OpenCode" via v2.2 prompt. Audit truncated — NO F-22 / med-auto-confirm finding. Smaller files (6.8/9.2/5.7KB). User belum sambung. |
| **Real OpenCode** | root `audit-01/02/03.md` | 20:33–20:36 | ✅ DONE | Last + most thorough. Has OVERHAUL ADDENDUM (Sections 7-14 deep-dives). LARGER files (17/25/19KB). Contains F-22 (med-auto-confirm specific). |

**Key alignment note:** The `opencode-audit/` folder is MISLABELED — it contains Gemini's output, not OpenCode's. The files internally say "Auditor: OpenCode" because you instructed Gemini to act as OpenCode. Don't be confused by the folder name or the internal "Auditor:" field when aligning.

**F-22 / med-auto-confirm coverage matrix:**

| Source | Has F-22 (med-auto-confirm)? | Location |
|--------|-------------------------------|----------|
| Real OpenCode (root) | ✅ YES | audit-02-findings.md F-22 + audit-03 O6 + audit-01 line 107 |
| Z.ai | ❌ NO (only generic D9 hooks) | zai-audit-01 D9 |
| Gemini (opencode-audit/) | ❌ NO (audit truncated) | — missing, needs ADD when continued |

## End of Document
