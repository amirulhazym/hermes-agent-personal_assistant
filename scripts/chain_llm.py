#!/usr/bin/env python3
"""
chain_llm.py — Generate medication reminders using the SAME model that the
current Hermes chat session is using.

Reads ~/.hermes/config.yaml to discover the active model/provider/base_url,
picks the right API key from ~/.hermes/.env, and calls the chat completions
endpoint with a tightly-scoped prompt that has full chain context.

Provider support:
  - opencode-go  (paid)  → OPENCODE_GO_API_KEY
  - opencode-zen (free)  → OPENCODE_ZEN_API_KEY
  - deepseek     (cheap) → DEEPSEEK_API_KEY
  - a6api        (configured gateway) → A6API_API_KEY

All 3 use the OpenAI-compatible /v1/chat/completions endpoint shape. The
only differences are base_url and which env var holds the API key.

Cloudflare 1010 workaround: opencode-go/zen require browser-like headers
(User-Agent). DeepSeek doesn't care. We send browser-like headers always —
harmless for DeepSeek, required for opencode.

Usage:
    chain_llm.py                  # Generate reminder for next slot (or silent)
    chain_llm.py C                # Generate reminder for specific slot
    chain_llm.py --silent-ok      # Don't error if no reminder (just exit 0)
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
HERMES_HOME = Path.home() / ".hermes"
CONFIG_FILE = HERMES_HOME / "config.yaml"
ENV_FILE = HERMES_HOME / ".env"

# ── Provider → env var mapping ────────────────────────────────────────────
# The 3 providers we actually use, period. Anything else falls back to deepseek.
PROVIDER_KEY_ENV = {
    "opencode-go": "OPENCODE_GO_API_KEY",
    "opencode-zen": "OPENCODE_ZEN_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "a6api": "A6API_API_KEY",
}

# Default base_urls (in case config.yaml doesn't specify one)
DEFAULT_BASE_URLS = {
    "opencode-go": "https://opencode.ai/zen/go",
    "opencode-zen": "https://opencode.ai/zen",
    "deepseek": "https://api.deepseek.com",
    "a6api": "https://a6api.com/v1",
}


# ═══════════════════════════════════════════════════════════════════════════
#  CONFIG + ENV LOADING
# ═══════════════════════════════════════════════════════════════════════════

def _parse_simple_yaml(path: Path) -> dict:
    """
    Minimal YAML parser — only handles the flat top-level + one-level-deep
    keys we need from config.yaml (model.default, model.provider, etc.).
    No nested block support — keeps us free of PyYAML dependency.
    """
    out: dict = {}
    if not path.exists():
        return out
    current_section = None
    for raw in path.read_text().splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        # Section header at column 0 (no leading whitespace, ends with ":")
        if not line.startswith((" ", "\t")) and line.endswith(":"):
            current_section = line[:-1].strip()
            out.setdefault(current_section, {})
            continue
        # key: value INSIDE a section (may be indented)
        if current_section and ":" in line:
            # Strip up to 4 spaces of indent to read the key
            stripped = line.lstrip(" ")
            # key: value
            if ":" in stripped:
                k, _, v = stripped.partition(":")
                out[current_section][k.strip()] = v.strip()
    return out


def _load_env() -> dict:
    env = {}
    if not ENV_FILE.exists():
        return env
    for raw in ENV_FILE.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def get_active_model_config() -> tuple[str, str, str]:
    """
    Read config.yaml → return (model_name, provider, base_url).
    Falls back to deepseek if config is missing or unparseable.
    """
    cfg = _parse_simple_yaml(CONFIG_FILE).get("model", {})
    provider = cfg.get("provider", "deepseek")
    model = cfg.get("default", "deepseek-v4-flash")
    base_url = cfg.get("base_url") or DEFAULT_BASE_URLS.get(provider, DEFAULT_BASE_URLS["deepseek"])
    return model, provider, base_url.rstrip("/")


# ═══════════════════════════════════════════════════════════════════════════
#  LLM CALL
# ═══════════════════════════════════════════════════════════════════════════

def _build_headers(api_key: str) -> dict:
    """
    Headers that pass Cloudflare bot detection on opencode-go/zen. Harmless
    on DeepSeek (it ignores User-Agent/Origin/Referer).
    """
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://opencode.ai",
        "Referer": "https://opencode.ai/",
    }


def _parse_sse_content(raw: str) -> str:
    """Extract assistant text from OpenAI-compatible SSE or JSON responses."""
    chunks = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        try:
            item = json.loads(payload)
        except json.JSONDecodeError:
            continue
        choices = item.get("choices") or []
        if not choices:
            continue
        choice = choices[0]
        delta = choice.get("delta") or {}
        content = delta.get("content")
        if content is None:
            content = (choice.get("message") or {}).get("content")
        if content:
            chunks.append(content)
    if chunks:
        return "".join(chunks).strip()
    try:
        item = json.loads(raw)
        return ((item.get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()
    except (json.JSONDecodeError, AttributeError, IndexError):
        return ""


def call_llm(
    model: str,
    provider: str,
    base_url: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 300,
    timeout: int = 20,
) -> str | None:
    """
    Make a single OpenAI-format chat completions call. Returns the assistant
    message content, or None on any failure. Caller must suppress delivery;
    no hardcoded medical fallback is permitted.
    """
    # Config may contain origin or OpenAI-compatible /v1 base.
    api_base = base_url.rstrip("/")
    if not api_base.endswith("/v1"):
        api_base += "/v1"
    url = f"{api_base}/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "stream": True,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=_build_headers(api_key), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw_lines = []
            while True:
                line = r.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", "replace")
                raw_lines.append(decoded)
                if decoded.strip() == "data: [DONE]":
                    break
            content = _parse_sse_content("".join(raw_lines))
            # Strip any leaked <think>...</think> blocks (some models echo reasoning)
            import re
            content = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL).strip()
            return content if content else None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError) as e:
        print(f"[chain_llm] LLM call failed ({type(e).__name__}): {e}", file=sys.stderr)
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  REMINDER PROMPT BUILDER
# ═══════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """\
You are a personal medical reminder assistant for Amirulhazym (Malaysian, EEE
grad, Muslim, on TB + epilepsy treatment). You generate short, human-like
medication reminders in Manglish (Malay-English mix). Your output replaces a
rigid template — be warm but concise, mirror his casual tone, never robotic.

Hard rules:
- Follow this exact shape:
  ‼️ Waktu Ubat ([Pagi/Tengah Hari/Petang/Malam]) ‼️

  [short salutation] [natural reminder sentence]

  [SLOT:N-YYMMDD]
- Salutation and context MUST be on the same line after the header. Correct:
  "Morning boss, Levetiracetam 500mg belum makan lagi, now dah 8pm ni. Take asap ya, nanti update saya."
- Salutation must be short and natural: "Pagi boss", "Morning boss", "Hai boss",
  or "Selamat petang boss". Match time of day. Do not put it on its own line.
- Use the user's daily Malaysian Manglish style. Example:
  "Boss, Levetiracetam 500mg belum makan lagi, now dah 8pm ni. Take asap ya,
  nanti update saya."
- Do NOT write "dah ready sejak...", "ready since...", "please take now", or
  other robotic status wording. State the current situation naturally.
- Keep header and reminder easy to scan in WhatsApp. Blank line before log code.
- Always include the log code on its own final line:
  [SLOT:N-YYMMDD] where N is reminder number for this slot today.
- 2-4 short lines max, excluding header and log code.
- Match urgency: first reminder = gentle; repeated reminders = progressively firmer.
- If pending drugs are listed, mention only those — not drugs already taken.
- Never claim a drug is safe without medical authority — remind timing only.
"""


def build_user_prompt(slot: str, chain: dict, slot_meta: dict) -> str:
    """Build the user prompt that contains full chain context for the LLM."""
    now = chain.get("now", "?")
    count = chain.get("reminder_counts", {}).get(slot, 0)
    ready = slot_meta.get("ready_time", "?")
    actual = slot_meta.get("actual_time")
    overall = slot_meta.get("overall", "pending")
    pending = slot_meta.get("pending_drugs", [])

    # Compact summary of all 5 slots
    slot_lines = []
    for s in ["A", "B", "C", "D", "E"]:
        st = chain.get("slots", {}).get(s, {})
        if st.get("confirmed"):
            t = st.get("actual_time", "?")
            slot_lines.append(f"  {s}: ✅ done at {t}")
        elif st.get("overall") == "partial":
            t = st.get("actual_time", "?")
            slot_lines.append(f"  {s}: ◐ partial (some drugs at {t})")
        elif st.get("ready_time"):
            slot_lines.append(f"  {s}: pending, ready {st['ready_time']}")
        else:
            slot_lines.append(f"  {s}: pending")
    slots_summary = "\n".join(slot_lines)

    pending_text = ""
    if pending:
        names = [f"{d.get('drug','?')} {d.get('dosage','')}" for d in pending]
        pending_text = f"PENDING DRUGS for slot {slot}: {', '.join(names)}"

    # ── Recent chat context ──────────────────────────────────────────────
    chat_context = ""
    try:
        import sqlite3
        from pathlib import Path
        db_path = Path.home() / ".hermes" / "state.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            # Find latest WhatsApp session (today)
            session = conn.execute(
                """SELECT id FROM sessions
                   WHERE source = 'whatsapp'
                   ORDER BY started_at DESC LIMIT 1"""
            ).fetchone()
            if session:
                msgs = conn.execute(
                    """SELECT role, content, timestamp FROM messages
                       WHERE session_id = ? AND role = 'user'
                       ORDER BY timestamp DESC LIMIT 10""",
                    (session["id"],)
                ).fetchall()
                if msgs:
                    lines = []
                    for m in reversed(msgs):  # oldest first
                        from datetime import datetime as dt
                        ts = dt.fromtimestamp(m["timestamp"]).strftime("%H:%M")
                        # Trim long messages
                        text = (m["content"] or "")[:200]
                        lines.append(f"  [{ts}] {text}")
                    chat_context = "Recent chat conversation (user said):\n" + "\n".join(lines)
            conn.close()
    except Exception as e:
        chat_context = f"# (chat context unavailable: {e})"

    state_instruction = pending_text if pending else (
        f"Slot {slot} is {overall}; do not invent or generalize any drug name."
    )

    return f"""\
Current time: {now} MYT
Slot to remind: {slot} (reminder #{count+1} for this slot today)
Slot ready time: {ready}
Slot status: {overall}
{state_instruction}

Today's chain state:
{slots_summary}

{chat_context}

Generate a natural, short Manglish reminder for slot {slot}. Header must be line 1;
salutation plus drug-specific context must be line 2; blank line; log code line last.
Name every pending drug with its exact dosage. Never replace a drug name with
"ubat", "ubat malam", "medication", or a generic label.
End with log code: [{slot}:{count+1}-{datetime.now().strftime('%y%m%d')}]
"""


def validate_reminder_text(text: str, slot: str, pending_drugs: list[dict] | None = None) -> bool:
    """Reject output that does not follow the WhatsApp reminder contract."""
    import re

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 3:
        return False
    if not lines[0].startswith("‼️ Waktu Ubat (") or not lines[0].endswith(") ‼️"):
        return False
    if not any(lines[1].startswith(prefix) for prefix in (
        "Pagi boss", "Morning boss", "Hai boss", "Selamat petang boss",
    )):
        return False
    if not re.fullmatch(rf"\[{slot}:\d+-\d{{6}}\]", lines[2]):
        return False
    body = lines[1].lower()
    if "dah ready sejak" in body or "ready since" in body:
        return False
    if pending_drugs:
        for drug in pending_drugs:
            name = str(drug.get("drug", "")).strip().lower()
            dosage = str(drug.get("dosage", "")).strip().lower()
            if not name or name not in body or (dosage and dosage not in body):
                return False
    return True


# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

TIME_LABELS = {
    "A": "Pagi",
    "B": "Pagi",
    "C": "Tengah Hari",
    "D": "Petang",
    "E": "Malam",
}


def render_reminder(slot: str, chain: dict, slot_meta: dict, *, date_code: str | None = None) -> str:
    """Render the fixed WhatsApp reminder contract from current pending drugs."""
    pending = slot_meta.get("pending_drugs") or []
    if not pending:
        raise ValueError(f"slot {slot} has no pending drugs")

    drug_names = []
    for drug in pending:
        name = str(drug.get("drug", "")).strip()
        dosage = str(drug.get("dosage", "")).strip()
        if not name or not dosage:
            raise ValueError(f"slot {slot} has incomplete pending-drug data")
        drug_names.append(f"{name} {dosage}")

    if len(drug_names) == 1:
        drugs_text = drug_names[0]
    elif len(drug_names) == 2:
        drugs_text = f"{drug_names[0]} dan {drug_names[1]}"
    else:
        drugs_text = f"{', '.join(drug_names[:-1])}, dan {drug_names[-1]}"

    now = chain.get("now", "?")
    count = int((chain.get("reminder_counts") or {}).get(slot, 0)) + 1
    date_code = date_code or datetime.now().strftime("%y%m%d")
    return (
        f"‼️ Waktu Ubat ({TIME_LABELS[slot]}) ‼️\n\n"
        f"Hai boss, {drugs_text} belum ambil lagi. Dah pukul {now}, update bila dah ambil.\n\n"
        f"[{slot}:{count}-{date_code}]"
    )


def main() -> int:
    explicit_slot = None
    silent_ok = "--silent-ok" in sys.argv
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if args:
        explicit_slot = args[0].upper()
        if explicit_slot not in TIME_LABELS:
            print(f"Invalid slot: {explicit_slot}", file=sys.stderr)
            return 1

    sys.path.insert(0, str(HERMES_HOME / "scripts"))
    try:
        import chain_calc  # type: ignore
    except ImportError as exc:
        print(f"[chain_llm] Cannot import chain_calc: {exc}", file=sys.stderr)
        return 1

    chain = chain_calc.calculate_chain()
    if not chain.get("reminder", {}).get("should_fire") and not explicit_slot:
        return 0 if silent_ok else 1

    slot = explicit_slot or chain["reminder"]["reason"]
    slot_meta = chain.get("slots", {}).get(slot, {})
    try:
        text = render_reminder(slot, chain, slot_meta)
    except ValueError as exc:
        print(f"[chain_llm] reminder suppressed: {exc}", file=sys.stderr)
        return 1

    if not validate_reminder_text(text, slot, slot_meta.get("pending_drugs", [])):
        print(f"[chain_llm] deterministic renderer violated reminder contract", file=sys.stderr)
        return 1

    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
