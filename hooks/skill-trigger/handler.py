"""
skill-trigger hook — auto-detect medication/message patterns and flag
required skills by writing ~/.hermes/triggered_skills.txt.

The agent's system prompt (SOUL.md) instructs it to read this file at
the start of each turn, load the listed skills, and delete the file.

Design principles:
- Fails open: errors are logged and swallowed — never blocks message flow.
- Lightweight: regex patterns only, no API calls, no LLM.
- Extensible: add new patterns/triggers to the TRIGGER_MAP below.
"""

import os
import re
import sys
from pathlib import Path

# ── Trigger map ──────────────────────────────────────────────────────────
# Add new domains here.  Keys are regex patterns, values are skill names.
# The FIRST match wins (order matters — put specific patterns before broad).
# Multiple patterns may match → all matched skills are written (set).
TRIGGER_MAP: list[tuple[str, str]] = [
    # Medication domain
    (r"\bdah\s*makan\b",           "med-tracker"),
    (r"\bmakan\s*ubat\b",          "med-tracker"),
    (r"\bletram\b",                "med-tracker"),
    (r"\blevetiracetam\b",         "med-tracker"),
    (r"\bakurit\b",                "med-tracker"),
    (r"\bdexa\b",                  "med-tracker"),
    (r"\bdexamethasone\b",         "med-tracker"),
    (r"\bpyridoxine\b",            "med-tracker"),
    (r"\bcalcitriol\b",            "med-tracker"),
    (r"\b\d+\s*biji\b",            "med-tracker"),   # "4 biji" = dose quantity
    (r"\bconfirm\s*med\b",         "med-tracker"),
    (r"\bslot\s*[A-Ea-e]\b",       "med-tracker"),
    (r"\b[A-Ea-e]\s*done\b",       "med-tracker"),   # "E done"
    (r"\b[A-Ea-e]\s*siap\b",       "med-tracker"),   # "B siap"
    (r"\bselesai[a-z]*\s*[A-Ea-e]\b", "med-tracker"), # "selesai D"

    # Web Operator domain (PX-1b)
    (r"\b/browse\b",                 "web-operator"),
    (r"\bbrowse\s+(?:open|to|https?://)", "web-operator"),
    (r"\bopen\s+https?://",           "web-operator"),
    (r"\bclick through\b",            "web-operator"),
    (r"\bfill form\b",               "web-operator"),
    (r"\blog\s*in and\b",            "web-operator"),
    (r"\bnavigate (?:to|this)\b",     "web-operator"),
    (r"\bmulti-step browse\b",        "web-operator"),
    (r"\bcomputer use\b",             "web-operator"),
    (r"\bnamed app\b",                 "web-operator"),
    (r"\bopen notepad\b",              "web-operator"),

    # Research domain (PX-1 Fasa 2) — skill dir name under ~/.hermes/skills
    (r"\bresearch\b",              "research-expert"),
    (r"\binvestigat(?:e|ion)\b",   "research-expert"),
    (r"\bliterature\s*scan\b",     "research-expert"),
    (r"\bfact[-\s]?check\b",       "research-expert"),
    (r"\bcited\s+sources?\b",      "research-expert"),
    (r"\bdeep\s+research\b",       "research-expert"),
    (r"\bcompare\s+(?:options|vendors|tools|approaches)\b", "research-expert"),
    (r"\bdue\s+diligence\b",       "research-expert"),

    # Explanation domain — confusion activates medium mode only.
    (r"\baku\s+tak\s+faham\b",      "non-tech"),
    (r"\bapa\s+benda\s+ni\b",       "non-tech"),
    (r"\bmaksud\s+k(a|au)\s+apa\b",  "non-tech"),
    (r"\bexplain\s+balik\b",          "non-tech"),
    (r"\bsimplify\b",                 "non-tech"),
    (r"\baku\s+lost\b",              "non-tech"),
    (r"\btak\s+nampak\s+point\b",    "non-tech"),
]

HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
TRIGGER_FILE = HERMES_HOME / "triggered_skills.txt"


def handle(event_type: str, context: dict) -> None:
    """
    Hook handler called by HookRegistry on ``agent:start``.

    Args:
        event_type: The event name (e.g. ``"agent:start"``).
        context:    Dict with keys ``platform``, ``user_id``, ``chat_id``,
                    ``session_id``, ``message`` (truncated 500 chars), etc.
    """
    if event_type != "agent:start":
        return

    message = context.get("message", "")
    if not message:
        return

    matched_skills: set[str] = set()

    for pattern, skill_name in TRIGGER_MAP:
        try:
            if re.search(pattern, message, re.IGNORECASE):
                matched_skills.add(skill_name)
        except re.error:
            # Malformed pattern — skip, don't crash
            continue

    if not matched_skills:
        return

    try:
        TRIGGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        TRIGGER_FILE.write_text("\n".join(sorted(matched_skills)), encoding="utf-8")
        print(
            f"[hooks:skill-trigger] Wrote {TRIGGER_FILE}: "
            f"{', '.join(sorted(matched_skills))}",
            flush=True,
        )
    except Exception as e:
        print(
            f"[hooks:skill-trigger] Failed to write {TRIGGER_FILE}: {e}",
            file=sys.stderr,
            flush=True,
        )
