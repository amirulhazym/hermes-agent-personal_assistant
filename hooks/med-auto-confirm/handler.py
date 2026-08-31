"""
med-auto-confirm hook — Pattern G fixed (2026-07-11).

Structural guarantee: medication confirmations are written to med-status.json
BEFORE the agent responds, so the reminder cron stops firing duplicates.
Fail-open: any error is logged, never blocks the agent.

Fixes vs the original (Pattern G incident 2026-07-10 silent lockout):
  G-1  Slot is accepted ONLY via an explicit "slot X" token OR a drug name.
       A bare A-E letter in natural/Manglish text ("Apa", "Bagi") no longer
       triggers a false confirmation.
  G-2  validate_timestamp() rejects any time >2h in the future. med_confirm.py
       is never called with a future timestamp.
  G-3  is_med_confirmation(): requires a completion word (dah makan/done/confirm…)
       AND a resolved slot/drug. Discussion-only messages are ignored.
  G-4  _already_logged() treats a future-timed stored entry as CORRUPT -> not
       blocking -> the real confirmation is allowed to overwrite it.
  G-6  Every decision (skip / confirm / reject) is appended to
       logs/med-auto-confirm-audit.log.

Pharmacy swap (confirmed 2026-07-09): Akurit-4 -> Akurit-2. DRUG_MAP maps both
"akurit-2" and legacy "akurit-4" mentions to drug_id "akurit_2".

EVENT: agent:start
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
STATUS_FILE = HERMES_HOME / "med-status.json"
CONFIRM_SCRIPT = HERMES_HOME / "scripts" / "med_confirm.py"
AUDIT_LOG = HERMES_HOME / "logs" / "med-auto-confirm-audit.log"
CHAIN_WARN_LOG = HERMES_HOME / "logs" / "med_chain_warnings.jsonl"
FUTURE_LIMIT = timedelta(hours=2)

# P1 (T11): deterministic chain-consistency check. Fail-open import — if the
# engine is missing/broken, the hook must still confirm meds normally.
try:
    sys.path.insert(0, str(HERMES_HOME / "scripts" / "med_chain"))
    from chain_consistency import consistency_warnings
except Exception:
    consistency_warnings = None

# Safety Gate is fail-closed for medication auto-write: absent/broken active
# regimen data must HOLD, never silently confirm. It only writes a structured
# HOLD record; it never writes med status/supply/reminder state.
sys.path.insert(0, str(HERMES_HOME / "scripts"))
try:
    from med_safety_gate import evaluate as evaluate_safety, persist_hold, is_regimen_change
except Exception:
    evaluate_safety = None
    persist_hold = None
    is_regimen_change = None

# Past-tense completion signals + med references.
COMPLETE_RE = re.compile(
    r"\b(dah\s*makan|sudah\s*makan|dah\s*ambil|dah\s*telan|dah\s*selesa[ii]kan?"
    r"|selesai|siap|done|took|ate|confirm|dah\s*confirm|telan|makan)\b",
    re.IGNORECASE,
)

# Negative intent has precedence over completion words. A question or future
# plan must never become a state mutation merely because it contains "makan".
QUESTION_RE = re.compile(
    r"\b(boleh\s+ke|can\s+i|should\s+i|nak\s+makan|akan\s+makan|japgi|nanti|"
    r"dah\s+log\s+ke|logged\s+ke|recorded\s+ke|confirm\s+ke|berapa\s+jam)\b"
    r"|[?]",
    re.IGNORECASE,
)
STATUS_QUERY_RE = re.compile(
    r"\b(dah\s+log|sudah\s+log|logged|recorded|status|check|semak|log\s+ke|"
    r"confirm\s+ke)\b",
    re.IGNORECASE,
)

# Gateway messages have one leading envelope timestamp. A second WhatsApp-style
# timestamp plus a sender label means the user pasted/quoted chat history; never
# treat medication words inside that history as a fresh intake event.
QUOTED_TRANSCRIPT_RE = re.compile(
    r"(?:^|\n)\s*\[\d{1,2}/\d{1,2},\s*\d{1,2}:\d{2}[^\]]*\]\s*[^\n:]{1,80}:",
    re.IGNORECASE,
)

# Explicit slot token ONLY (G-1): "slot A", "Slot B la", "slot C".
SLOT_TOKEN_RE = re.compile(r"\bslot\s*([A-Ea-e])\b", re.IGNORECASE)

# Drug-name -> (slot, drug_id). Akurit-2 is the current drug (swap 9/7/2026);
# legacy "akurit-4" mentions also map to akurit_2 so no stale name is written.
DRUG_MAP = [
    # Specific match first: "akurit-2", "akurit 2", legacy "akurit-4"
    (r"\bakurit[- ]?(2|4)\b", "A", "akurit_2"),
    # Fallback: bare "akurit" (e.g. "akurit+pyridoxine" or just "akurit")
    (r"\bakurit\b", "A", "akurit_2"),
    (r"\bpyridoxine\b", "A", "pyridoxine"),
    (r"\bvitamin\s*b6\b", "A", "pyridoxine"),
    (r"\bb\s*6\b", "A", "pyridoxine"),
    (r"\bletram\b", None, None),
    (r"\blevetiracetam\b", None, None),
    (r"\bdexa(?:methasone)?\b", None, None),
    (r"\bcalcium\b|\bkalsium\b", "C", "calcium"),
    (r"\bcalcitriol\b|\bvitamin\s*d\b", "C", "calcitriol"),
    (r"\bb[- ]?complex\b|\bswisse\b", "C", "b_complex"),
]

# Inbound gateway messages carry a leading envelope timestamp, e.g.
#   [Thu 2026-08-13 20:34:27 +08] Dah makan letram jam 8.32pm
# That envelope contains the YEAR ("2026") which, under a loose 4-digit time
# pattern, gets mis-parsed as "20:26". We strip the envelope FIRST so the
# year can never reach the time parser. This is a structural separation, not a
# pattern tweak — the envelope is consumed by a dedicated matcher, not scanned
# as free text.
ENV_RE = re.compile(r"^\s*\[[^\]]*\]\s*")

# Time patterns — tolerant (2026-08-13 owner directive): in a med confirmation
# context any plausible time shape is accepted. Order is significant:
#   1. leader (jam/pukul/at/@/pada) + H.MM OR compact HHMM  (jam 12:15 / jam 1215)
#   2. bare H.MM or H:MM with optional am/pm                (4.32pm / 12:15)
#   3. bare compact HHMM with optional am/pm                (815 / 1215)
#   4. bare H + am/pm                                      (8pm / 6am)
# The compact forms MUST be tried before the loose "leader + 1-2 digits" shape,
# otherwise "jam 610" grabs only "61" and the trailing "0" is lost.
TIME_RE = re.compile(
    r"(?:(?:\bpukul\b|\bjam\b|\bat\b|@|\bpada\b)\s*"
    r"(?:(?P<ah>\d{1,2})(?:[:.](?P<am>\d{2}))?"          # jam 4.25 / jam 12:15
    r"|(?P<bh>\d{1,2})(?P<bm>\d{2}))"              # jam 1215 / jam 610
    r"\s*(?P<ap1>am|pm)?)"
    r"|(?P<ch>\d{1,2})[:.](?P<cm>\d{2})\s*(?P<ap2>am|pm)?"   # 4.25pm / 12:15
    r"|(?P<dh>\d{1,2})(?P<dm>\d{2})\s*(?P<ap3>am|pm)?"       # 815 / 1215
    r"|(?P<eh>\d{1,2})\s*(?P<ap4>am|pm)",                      # 8pm / 6am
    re.IGNORECASE,
)

# Context words that disambiguate 12h times.
_AM_HINT = re.compile(r"\b(pagi|subuh)\b", re.IGNORECASE)
_PM_HINT = re.compile(
    r"\b(petang|tengah\s*hari|siang|malam|lepas\s*(?:zuhur|asar)|pm)\b",
    re.IGNORECASE,
)


def _audit(msg: str) -> None:
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def _parse_time(message: str, now: datetime):
    """Extract HH:MM from message. Returns None if no time found.

    Tolerant, context-aware (2026-08-13 owner directive):
      1. leading word:  "jam 1.49pm" / "pukul 8.12" / "at 20:00"
      2. separator:     "4.32pm tadi" / "4:32" / "16.32" (am/pm optional)
      3. compact typo:  "432pm" -> 4:32pm, "815" -> 8:15
      4. bare + am/pm:  "4pm" / "6am"

    Without am/pm the 12h ambiguity is resolved by:
      - context words (pagi -> AM; petang/malam/siang -> PM);
      - hour > 12 is already 24h;
      - otherwise nearest-to-now (within ±12h) wins.
    """
    # Strip the leading gateway envelope ([...] timestamp) BEFORE scanning.
    # The envelope year ("2026") must never be reachable by TIME_RE.
    body = ENV_RE.sub("", message)
    m = TIME_RE.search(body)
    if not m:
        return None
    g = m.groupdict()
    ap = (g.get("ap1") or g.get("ap2") or g.get("ap3") or g.get("ap4") or "").lower()
    if g.get("ah") is not None:
        hour, minute = int(g["ah"]), int(g["am"] or 0)
    elif g.get("bh") is not None:
        # Compact leader form "jam 1215" / "jam 610": explicit HHMM, treat as
        # 24h directly. No 12h/nearest-to-now ambiguity — the user typed the
        # full time. "610" -> 06:10, "815" -> 08:15, "2015" -> 20:15.
        hour, minute = int(g["bh"]), int(g["bm"])
    elif g.get("ch") is not None:
        hour, minute = int(g["ch"]), int(g["cm"] or 0)
    elif g.get("dh") is not None:
        # Bare compact "815" / "1215" / "2015": explicit HHMM, 24h directly.
        hour, minute = int(g["dh"]), int(g["dm"])
    elif g.get("eh") is not None:
        hour, minute = int(g["eh"]), 0
    else:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    if ap:
        if ap == "pm" and hour < 12:
            hour += 12
        elif ap == "am" and hour == 12:
            hour = 0
    elif hour <= 12 and g.get("bh") is None and g.get("dh") is None:
        # Only single-number forms without a separator (e.g. bare "8") reach
        # 12h ambiguity. Compact HHMM (bh/dh) and explicit H.MM (ah/ch) are
        # already 24h-clean by the time we get here.
        if _AM_HINT.search(body) and not _PM_HINT.search(body):
            if hour == 12:
                hour = 0
        elif _PM_HINT.search(body) and not _AM_HINT.search(body):
            if hour < 12:
                hour += 12
        else:
            # No context hint: prefer the most recent PAST candidate (med
            # reports describe intake that already happened); if both are
            # in the future, pick the nearest one.
            cands = [hour, hour + 12 if hour < 12 else hour - 12]
            now_h = now.hour + now.minute / 60
            past = [c for c in cands if c <= now_h]
            if past:
                hour = max(past)
            else:
                hour = min(cands, key=lambda c: abs(c - now_h))
    return datetime(now.year, now.month, now.day, hour, minute)


def _validate_timestamp(dt: datetime, now: datetime) -> bool:
    """True if dt is acceptable (not in the future beyond FUTURE_LIMIT)."""
    if dt is None:
        return True
    return dt <= now + FUTURE_LIMIT


def _resolve_slot_drug(message: str, now: datetime):
    """
    Return (slot, drug_id_or_None, time_or_None). slot=None means DO NOT act.
    Priority: drug name (time-disambiguated) > explicit "slot X" token.
    """
    time_dt = _parse_time(message, now)
    time_str = f"{time_dt.hour:02d}:{time_dt.minute:02d}" if time_dt else None

    h = (time_dt.hour + time_dt.minute / 60) if time_dt else now.hour + now.minute / 60
    for pat, s, d in DRUG_MAP:
        if re.search(pat, message, re.IGNORECASE):
            if d is None:
                if re.search(r"letram|levetiracetam", pat, re.IGNORECASE):
                    return ("B", "levetiracetam_b", time_str) if h < 14 else ("E", "levetiracetam_e", time_str)
                if re.search(r"dexa", pat, re.IGNORECASE):
                    if h < 10:
                        return "B", "dexamethasone_1", time_str
                    if 10 <= h < 14:
                        return "C", "dexamethasone_2", time_str
                    return "D", "dexamethasone_3", time_str
            return s, d, time_str

    slot_m = SLOT_TOKEN_RE.search(message)
    if slot_m:
        slot = slot_m.group(1).upper()
        for pat, s, d in DRUG_MAP:
            if s == slot and re.search(pat, message, re.IGNORECASE):
                return slot, d, time_str
        return slot, None, time_str

    # G-1 guard: bare letter only accepted if near a completion phrase.
    # This prevents false matches like "Apa", "Bagi" while allowing
    # "dah makan A", "done A", "confirm A", "A dah selesai" etc.
    BARE_LETTER_NEAR = re.compile(
        r"\b([A-Ea-e])\b",
    )
    # Completion-signal words that indicate a genuine med confirmation
    NEAR_WORDS = (
        r"dah\s*makan|sudah\s*makan|dah\s*ambil|dah\s*telan|"
        r"selesai|siap|done|confirm|took|ate|makan|ambil|telan"
    )
    for m in BARE_LETTER_NEAR.finditer(message):
        letter = m.group(1).upper()
        # Only accept bare A-E if it's relatively near a completion word
        start = max(0, m.start() - 30)
        end = min(len(message), m.end() + 30)
        snippet = message[start:end]
        if re.search(NEAR_WORDS, snippet, re.IGNORECASE):
            return letter, None, time_str

    return None, None, time_str


def _already_logged(slot: str, today: str) -> bool:
    """True if a VALID (non-future) entry already exists for slot today."""
    try:
        if not STATUS_FILE.exists():
            return False
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        entry = data.get("meds", {}).get(slot, {}).get(today)
        if entry is None:
            return False
        # G-4: a future-timed entry is corrupt -> allow overwrite.
        t = entry.get("time") or entry.get("actual_time")
        if t:
            try:
                hh, mm = map(int, str(t).split(":"))
                now = datetime.now()
                dt = datetime(now.year, now.month, now.day, hh, mm)
                if dt > now + FUTURE_LIMIT:
                    return False
            except Exception:
                pass
        if entry.get("overall") == "completed":
            return True
        # Partial entry still allows further drug confirmations.
        if entry.get("overall") == "partial":
            return False
        return False
    except Exception:
        return False


def is_med_confirmation(message: str) -> bool:
    if QUOTED_TRANSCRIPT_RE.search(message):
        return False
    if QUESTION_RE.search(message) or STATUS_QUERY_RE.search(message):
        return False
    return bool(COMPLETE_RE.search(message))


def _load_confirmed_times(today: str) -> dict:
    """Read currently-confirmed slot times for today from med-status.json.

    Returns {slot: 'HH:MM'}. Read-only; any failure -> empty dict.
    """
    try:
        if not STATUS_FILE.exists():
            return {}
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        out = {}
        for slot, daymap in data.get("meds", {}).items():
            entry = daymap.get(today) if isinstance(daymap, dict) else None
            if not entry:
                continue
            t = entry.get("actual_time") or entry.get("time")
            if isinstance(t, str) and len(t) >= 5:
                out[slot] = t[:5]
        return out
    except Exception:
        return {}


def _write_chain_warnings(slot: str, time_str: str, warnings: list) -> None:
    """Persist chain-consistency warnings for later surfacing (machine-readable)."""
    try:
        CHAIN_WARN_LOG.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "slot": slot,
            "time": time_str,
            "warnings": warnings,
        }
        with open(CHAIN_WARN_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass


def _check_chain_consistency(slot: str, time_str: str, today: str) -> None:
    """Run the deterministic engine against a stated med time (fail-open)."""
    if consistency_warnings is None or not time_str:
        return
    try:
        known = _load_confirmed_times(today)
        warns = consistency_warnings(slot, time_str, known)
        if warns:
            for w in warns:
                _audit(f"CHAIN-WARN slot={slot} time={time_str} {w}")
            _write_chain_warnings(slot, time_str, warns)
    except Exception as e:
        _audit(f"CHAIN-CHECK-ERROR {e}")


def _confirm_result_ok(result) -> bool:
    if result.returncode != 0:
        return False
    try:
        payload = json.loads(result.stdout or "")
    except (TypeError, json.JSONDecodeError):
        return False
    return payload.get("ok") is True and payload.get("dry_run") is not True


def handle(event_type: str, context: dict) -> None:
    if event_type != "agent:start":
        return

    message = context.get("message", "")
    if not message:
        return

    # Regimen-change reports are safety events even without intake-completion words.
    # They must reach a durable HOLD instead of silently skipping the hook.
    if is_regimen_change is not None and is_regimen_change(message):
        now = datetime.now()
        stated = _parse_time(message, now)
        stated_time = f"{stated.hour:02d}:{stated.minute:02d}" if stated else ""
        if evaluate_safety is None or persist_hold is None:
            _audit("HOLD safety-gate-unavailable for regimen-change: no medication write")
            return
        try:
            decision = evaluate_safety(message, stated_time, now)
            hold = persist_hold(decision)
            _audit(f"HOLD regimen-change hold_id={hold['hold_id']} findings={decision.get('findings', [])!r}")
        except Exception as exc:
            _audit(f"HOLD regimen-change-persist-error {exc!r}: no medication write")
        return

    if not is_med_confirmation(message):
        return

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    # G-2: reject future time (>2h ahead) before evaluating any intake write.
    time_dt = _parse_time(message, now)
    if time_dt is None:
        # No parseable time. This is a CLARIFY case, not a silent rejection:
        # the agent sees the message and must ask the user for the actual
        # intake time (owner requirement 2026-08-12). No state is written.
        _audit(f"CLARIFY missing-intake-time msg={message!r}")
        return
    time_str = f"{time_dt.hour:02d}:{time_dt.minute:02d}"
    if not _validate_timestamp(time_dt, now):
        _audit(f"REJECT future-time time={time_str} msg={message!r}")
        return

    # Safety Gate owns clinical parsing and routing. Do not use the legacy
    # first-match router for writes: it can diverge from active schedule/taper.
    if evaluate_safety is None or persist_hold is None:
        _audit("HOLD safety-gate-unavailable: no medication write")
        return
    try:
        decision = evaluate_safety(message, time_str, now)
    except Exception as exc:
        _audit(f"HOLD safety-gate-evaluation-error {exc!r}: no medication write")
        return
    if decision.get("decision") == "HOLD":
        try:
            hold = persist_hold(decision)
            _audit(f"HOLD safety-gate hold_id={hold['hold_id']} findings={decision.get('findings', [])!r}")
        except Exception as exc:
            _audit(f"HOLD safety-gate-persist-error {exc!r}: no medication write")
        return

    mentions = decision.get("mentions", [])
    slots = {m.get("slot") for m in mentions if m.get("slot")}
    drug_ids = list(dict.fromkeys(m.get("drug_id") for m in mentions if m.get("drug_id")))
    if len(slots) != 1 or not drug_ids:
        _audit(f"HOLD safety-gate-invalid-allow decision={decision!r}: no medication write")
        return
    slot = next(iter(slots))

    # T11 (P1): deterministic chain-consistency check. Fail-open — never blocks
    # the confirmation; only audits + records warnings when a stated time
    # contradicts the computed chain.
    _check_chain_consistency(slot, time_str, today)

    if _already_logged(slot, today):
        _audit(f"SKIP already-logged slot={slot}")
        return

    if not CONFIRM_SCRIPT.exists():
        _audit(f"ERROR script-missing {CONFIRM_SCRIPT}")
        return

    compound_ids = {m.get("compound_id") for m in mentions if m.get("compound_id")}
    is_one_compound = len(compound_ids) == 1 and all(m.get("compound_id") in compound_ids for m in mentions)
    compound_id = next(iter(compound_ids)) if is_one_compound else None
    if compound_id is not None:
        cmd = [sys.executable, str(CONFIRM_SCRIPT), slot, "--compound", compound_id]
        if time_str:
            cmd += ["--at", time_str]
        cmd += ["--source-text", message]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30,
                env={**os.environ, "HERMES_HOME": str(HERMES_HOME), "HOME": str(HERMES_HOME.parent)},
            )
            if _confirm_result_ok(result):
                _audit(f"CONFIRM compound={compound_id} slot={slot} time={time_str} msg={message!r}")
            else:
                _audit(f"ERROR compound={compound_id} rc={result.returncode} output={result.stdout[:300]!r} err={result.stderr[:200]}")
        except Exception as exc:
            _audit(f"ERROR compound={compound_id} exception {exc}")
        return

    results = []
    for current_drug_id in drug_ids:
        cmd = [sys.executable, str(CONFIRM_SCRIPT), slot]
        if current_drug_id:
            cmd.append(current_drug_id)
        if time_str:
            cmd += ["--at", time_str]
        cmd += ["--source-text", message]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "HERMES_HOME": str(HERMES_HOME), "HOME": str(HERMES_HOME.parent)},
            )
            results.append(result)
            if _confirm_result_ok(result):
                _audit(f"CONFIRM slot={slot} drug={current_drug_id} time={time_str} msg={message!r}")
            else:
                _audit(f"ERROR med_confirm drug={current_drug_id} rc={result.returncode} output={result.stdout[:300]!r} err={result.stderr[:200]}")
                break
        except Exception as e:
            _audit(f"ERROR drug={current_drug_id} exception {e}")
            break
