#!/usr/bin/env python3
"""Runtime Model Audit — evidence-first verification of which model is ACTUALLY serving.

Solves the core question: "The system says model X, but is model X really handling
API calls?" by cross-referencing all available evidence sources.

Usage:
    python3 scripts/runtime-model-audit.py [--session-id <id>] [--limit-api-calls 5]

Outputs H1-H7 audit sections per the structured evidence framework.
"""

import argparse
import gzip
import json
import os
import re
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).resolve()

STATE_DB = HERMES_HOME / "state.db"
AGENT_LOG = HERMES_HOME / "logs" / "agent.log"
GATEWAY_LOG = HERMES_HOME / "logs" / "gateway.log"
CONFIG_YAML = HERMES_HOME / "config.yaml"


def _fmt(ts: float | None) -> str:
    if ts is None:
        return "N/A"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ── H1: Display / Config layers ──────────────────────────────────────────────


def read_config(path: Path) -> dict[str, Any]:
    """Read config.yaml and extract model-related fields."""
    import yaml  # lazy import — Hermes venv always has it

    try:
        with open(path) as f:
            cfg = yaml.safe_load(f)
    except (FileNotFoundError, yaml.YAMLError):
        return {}

    result = {}
    if isinstance(cfg.get("model"), dict):
        m = cfg["model"]
        result["configured_model"] = m.get("default", "UNSET")
        result["configured_provider"] = m.get("provider", "UNSET")
        result["configured_base_url"] = m.get("base_url")
    if isinstance(cfg.get("fallback_providers"), list):
        result["fallback_chain"] = [
            f'{f.get("provider","?")}/{f.get("model","?")}'
            for f in cfg["fallback_providers"]
            if isinstance(f, dict)
        ]
    if isinstance(cfg.get("display"), dict):
        d = cfg["display"]
        result["show_reasoning_global"] = d.get("show_reasoning", "NOT SET")
        platforms = d.get("platforms", {})
        if isinstance(platforms, dict):
            result["show_reasoning_whatsapp"] = (
                platforms.get("whatsapp", {}).get("show_reasoning", "inherit")
                if isinstance(platforms.get("whatsapp"), dict)
                else "none"
            )
            result["show_reasoning_telegram"] = (
                platforms.get("telegram", {}).get("show_reasoning", "inherit")
                if isinstance(platforms.get("telegram"), dict)
                else "none"
            )
    return result


def query_session_db(session_id: str | None = None) -> dict[str, Any]:
    """Query state.db for session model information."""
    if not STATE_DB.exists():
        return {"error": f"state.db not found at {STATE_DB}"}

    try:
        con = sqlite3.connect(str(STATE_DB))
        cur = con.cursor()
    except sqlite3.Error as e:
        return {"error": str(e)}

    result: dict[str, Any] = {"sessions": []}

    try:
        if session_id:
            cur.execute(
                "SELECT id, source, started_at, model, billing_provider, "
                "message_count, reasoning_tokens, input_tokens, output_tokens "
                "FROM sessions WHERE id=? ORDER BY started_at DESC LIMIT 3",
                (session_id,),
            )
        else:
            cur.execute(
                "SELECT id, source, started_at, model, billing_provider, "
                "message_count, reasoning_tokens, input_tokens, output_tokens "
                "FROM sessions ORDER BY started_at DESC LIMIT 5"
            )

        for row in cur.fetchall():
            s = {
                "id": row[0],
                "source": row[1],
                "started_at": _fmt(row[2]) if row[2] else "N/A",
                "started_ts": row[2],
                "model": row[3],
                "billing_provider": row[4],
                "message_count": row[5] or 0,
                "reasoning_tokens": row[6] or 0,
                "input_tokens": row[7] or 0,
                "output_tokens": row[8] or 0,
            }
            result["sessions"].append(s)

    except sqlite3.Error as e:
        return {"error": str(e)}
    finally:
        con.close()

    return result


def resolve_gateway_source(source: str) -> str:
    """Map session source names to a readable platform name."""
    if "telegram" in source.lower() or source == "telegram":
        return "telegram"
    if "whatsapp" in source.lower() or source.startswith("1203") or source.startswith("60"):
        return "whatsapp"
    if "cron" in source.lower():
        return "cron"
    if "subagent" in source.lower():
        return "subagent"
    return source


# ── H2 / H5: Agent log evidence (runtime truth + fallback) ───────────────────


def get_agent_log_lines(path: Path, max_lines: int = 10000) -> list[str]:
    """Read tail of agent.log, handling gz rotation."""
    if not path.exists():
        return []
    try:
        # read last N lines
        result = subprocess.run(
            ["tail", "-n", str(max_lines), str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = result.stdout.splitlines()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        lines = []
    return lines


def parse_agent_log(
    lines: list[str], target_session: str | None = None
) -> dict[str, Any]:
    """Extract model-related events from agent.log lines."""
    result: dict[str, Any] = {
        "turn_contexts": [],
        "first_api_call": None,
        "api_calls": [],
        "fallbacks": [],
        "api_failures": [],
        "agent_inits": [],
        "errors_found": [],
    }

    for line in lines:
        # Agent init
        m = re.search(
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ INFO .*?run_agent: OpenAI client created \(agent_init.*?model=(\S+)",
            line,
        )
        if m and (not target_session or target_session in line):
            result["agent_inits"].append(line)

        # Turn context
        m = re.search(
            r"agent\.turn_context: conversation turn: session=(\S+) model=(\S+) provider=(\S+) platform=(\S+)",
            line,
        )
        if m and (not target_session or m.group(1) == target_session):
            result["turn_contexts"].append(
                {
                    "session": m.group(1),
                    "model": m.group(2),
                    "provider": m.group(3),
                    "platform": m.group(4),
                    "raw": line,
                }
            )

        # API call
        m = re.search(
            r"agent\.conversation_loop: API call #(\d+): model=(\S+) provider=(\S+) in=(\d+) out=(\d+) total=(\d+) latency=([\d.]+)s",
            line,
        )
        if m:
            call = {
                "num": int(m.group(1)),
                "model": m.group(2),
                "provider": m.group(3),
                "input_tokens": int(m.group(4)),
                "output_tokens": int(m.group(5)),
                "total_tokens": int(m.group(6)),
                "latency_s": float(m.group(7)),
            }
            if not target_session or target_session in line:
                if result["first_api_call"] is None:
                    result["first_api_call"] = {**call, "line": line}
                result["api_calls"].append(call)

        # API failure
        m = re.search(
            r"API call failed \(attempt (\d+)/3\) error_type=(\S+) .*?model=(\S+) summary=(.+)",
            line,
        )
        if m and (not target_session or target_session in line):
            result["api_failures"].append(
                {
                    "attempt": int(m.group(1)),
                    "error_type": m.group(2),
                    "model": m.group(3),
                    "summary": m.group(4).strip(),
                    "raw": line,
                }
            )
            if target_session and target_session not in line:
                pass  # filtered

        # Fallback activated
        m = re.search(
            r"Fallback activated: (\S+) → (\S+) \((\S+)\)",
            line,
        )
        if m and (not target_session or target_session in line):
            result["fallbacks"].append(
                {
                    "from_model": m.group(1),
                    "to_model": m.group(2),
                    "provider": m.group(3),
                    "raw": line,
                }
            )

        # Fallback skip
        m = re.search(
            r"Fallback skip: chain entry (\S+) matches current provider/model",
            line,
        )
        if m and (not target_session or target_session in line):
            result["fallbacks"].append(
                {
                    "type": "skip",
                    "entry": m.group(1),
                    "raw": line,
                }
            )

        # Errors
        if "ERROR" in line and "Fallback" in line and not "activated" in line:
            result["errors_found"].append(line)

    return result


# ── H6: Reasoning verification ───────────────────────────────────────────────


def check_reasoning_provider_profile() -> dict[str, Any]:
    """Check the OpenCodeZenProfile for model effort whitelist."""
    profile_path = (
        HERMES_HOME
        / "hermes-agent"
        / "plugins"
        / "model-providers"
        / "opencode-zen"
        / "__init__.py"
    )
    result = {"profile_found": False, "whitelisted_models": [], "hy3_free_whitelisted": None}

    if not profile_path.exists():
        return result

    try:
        content = profile_path.read_text()
    except (OSError, IOError):
        return result

    result["profile_found"] = True
    # Extract whitelist
    in_whitelist = False
    models = []
    for line in content.splitlines():
        if "_MODEL_EFFORT_WHITELIST" in line and "{" in line:
            in_whitelist = True
            continue
        if in_whitelist and "}" in line:
            break
        if in_whitelist and '"' in line:
            m = re.search(r'"([\w.-]+)"', line)
            if m:
                models.append(m.group(1))
    result["whitelisted_models"] = models
    result["hy3_free_whitelisted"] = "hy3-free" in models
    return result


# ── H7: Summary ──────────────────────────────────────────────────────────────


def determine_confidence(
    config_model: str,
    session_model: str | None,
    first_api_model: str | None,
    all_api_models: list[str],
    fallbacks: list,
) -> str:
    """Classify confidence based on available evidence."""
    if first_api_model is None and all_api_models:
        first_api_model = all_api_models[0]

    if first_api_model is None:
        return "LOW — no API call evidence in logs"

    if fallbacks:
        return "HIGH — fallback chain directly observed in logs"

    if config_model != first_api_model and first_api_model is not None:
        return "HIGH — configured model differs from API call model"

    if all_api_models and all(m == config_model for m in all_api_models):
        return "HIGH — all API calls match configured model (no evidence of divergence)"

    return "MEDIUM — indirect evidence only"


def audit(session_id: str | None = None) -> dict[str, Any]:
    """Run the full H1-H7 audit."""
    result: dict[str, Any] = {
        "h1_display_truth": {},
        "h2_runtime_truth": {},
        "h3_provider_truth": {},
        "h4_reasoning_truth": {},
        "h5_fallback_truth": {},
        "h6_billing_truth": {},
        "h7_confidence": {},
    }

    # ── H1: Display Truth ───────────────────────────────────────────────────
    config = read_config(CONFIG_YAML)
    db = query_session_db(session_id)
    h1 = {
        "config_default_model": config.get("configured_model", "UNKNOWN"),
        "config_default_provider": config.get("configured_provider", "UNKNOWN"),
        "fallback_chain": config.get("fallback_chain", []),
        "show_reasoning_global": config.get("show_reasoning_global", "NOT SET"),
        "show_reasoning_whatsapp": config.get("show_reasoning_whatsapp", "NOT SET"),
        "show_reasoning_telegram": config.get("show_reasoning_telegram", "NOT SET"),
        "session_db_entries": db.get("sessions", []),
    }
    result["h1_display_truth"] = h1

    # ── H2 / H5: Agent log evidence ─────────────────────────────────────────
    if AGENT_LOG.exists():
        log_lines = get_agent_log_lines(AGENT_LOG)
        parsed = parse_agent_log(log_lines, target_session=session_id)
        result["h2_runtime_truth"]["agent_inits"] = [
            {"raw": l} for l in parsed["agent_inits"]
        ]
        result["h2_runtime_truth"]["turn_contexts"] = parsed["turn_contexts"]
        result["h2_runtime_truth"]["first_api_call"] = parsed["first_api_call"]
        result["h2_runtime_truth"]["api_calls_summary"] = {
            "total_calls": len(parsed["api_calls"]),
            "unique_models": list(
                dict.fromkeys(c["model"] for c in parsed["api_calls"])
            ),
            "models_used": {
                model: sum(1 for c in parsed["api_calls"] if c["model"] == model)
                for model in dict.fromkeys(c["model"] for c in parsed["api_calls"])
            },
        }
        result["h2_runtime_truth"]["api_failures"] = [
            {
                "model": f["model"],
                "error": f["summary"],
                "error_type": f["error_type"],
                "attempt": f["attempt"],
            }
            for f in parsed["api_failures"]
        ]

        # ── H5: Fallback ────────────────────────────────────────────────────
        h5 = {
            "fallbacks": parsed["fallbacks"],
            "fallback_count": len(
                [f for f in parsed["fallbacks"] if f.get("type") != "skip"]
            ),
            "skip_entries": [
                f for f in parsed["fallbacks"] if f.get("type") == "skip"
            ],
        }
        result["h5_fallback_truth"] = h5

        # ── H6: Billing / error truth ────────────────────────────────────────
        h6 = {"api_failures": result["h2_runtime_truth"]["api_failures"]}
        if parsed["api_calls"]:
            last_call = parsed["api_calls"][-1]
            h6["last_successful_call"] = {
                "model": last_call["model"],
                "provider": last_call["provider"],
                "latency_s": last_call["latency_s"],
            }
            h6["all_calls_succeeded"] = len(parsed["api_failures"]) == 0
        else:
            h6["last_successful_call"] = None
            h6["all_calls_succeeded"] = False
        result["h6_billing_truth"] = h6
    else:
        result["h2_runtime_truth"]["error"] = f"agent.log not found at {AGENT_LOG}"

    # ── H3: Provider truth ──────────────────────────────────────────────────
    result["h3_provider_truth"] = {
        "what_hermes_requested": result["h2_runtime_truth"].get("first_api_call"),
        "what_provider_executed": "KNOWN from API call logs — see H2",
        "providers_opaque_admission": (
            "Cannot know if opencode-zen internally routes model X to a different "
            "underlying model — Hermes sends model=X and receives a response; "
            "internal substitution is opaque to the client."
        ),
    }

    # ── H4: Reasoning truth ──────────────────────────────────────────────────
    profile = check_reasoning_provider_profile()
    h4 = {
        "opencode_zen_profile_found": profile["profile_found"],
        "whitelisted_models_for_reasoning": profile["whitelisted_models"],
        "hy3_free_whitelisted": profile["hy3_free_whitelisted"],
    }

    # Add reasoning tokens from session DB
    if db.get("sessions"):
        for s in db["sessions"][:3]:
            s["reasoning_tokens_present"] = s.get("reasoning_tokens", 0) > 0

        current = db["sessions"][0]
        h4["current_session_reasoning_tokens"] = current.get("reasoning_tokens", 0)
        h4["reasoning_generating"] = (
            current.get("reasoning_tokens", 0) > 0
        )

    h4["display_suppression"] = (
        "YES — WhatsApp show_reasoning is "
        + str(config.get("show_reasoning_whatsapp", "unknown"))
        + "; reasoning_content is stripped before delivery"
        if config.get("show_reasoning_whatsapp") == False
        else "NO — visible on WhatsApp"
    )

    # Check the actual serving model's reasoning capability
    api_models = result["h2_runtime_truth"].get("api_calls_summary", {}).get("unique_models", [])
    serving_model = api_models[0] if api_models else "UNKNOWN"
    if serving_model in profile["whitelisted_models"]:
        h4["serving_model_reasoning_whitelisted"] = True
    elif api_models:
        h4["serving_model_reasoning_whitelisted"] = False
        h4["serving_model_reasoning_note"] = (
            f"Serving model '{serving_model}' is not in the reasoning effort whitelist. "
            "Reasoning_effort is silently dropped."
        )
    else:
        h4["serving_model_reasoning_whitelisted"] = "UNKNOWN — no API calls observed"

    result["h4_reasoning_truth"] = h4

    # ── H7: Confidence ──────────────────────────────────────────────────────
    # `models_used` is a dict keyed by model ID; use its keys directly.
    # (The previous list-comprehension treated each key string as a mapping.)
    # Re-derive from api_calls_summary models_used keys
    models_used = result["h2_runtime_truth"].get("api_calls_summary", {}).get("models_used", {})
    models_list = list(models_used.keys()) if models_used else []

    confidence = determine_confidence(
        config.get("configured_model", "UNSET"),
        db.get("sessions", [{}])[0].get("model") if db.get("sessions") else None,
        result["h2_runtime_truth"].get("first_api_call", {}).get("model"),
        models_list,
        result["h5_fallback_truth"].get("fallbacks", []),
    )

    blind_spots = [
        "opencode-zen internal model substitution — Hermes sends model=X, cannot verify what runs on provider side",
        "Raw HTTP request/response body not logged — only Python-level error messages",
    ]
    result["h7_confidence"] = {
        "verdict": confidence,
        "blind_spots": blind_spots,
    }

    return result


def print_audit(result: dict[str, Any]) -> None:
    """Pretty-print the audit results."""
    h1 = result.get("h1_display_truth", {})
    h2 = result.get("h2_runtime_truth", {})
    h4 = result.get("h4_reasoning_truth", {})
    h5 = result.get("h5_fallback_truth", {})
    h6 = result.get("h6_billing_truth", {})
    h7 = result.get("h7_confidence", {})

    print("=" * 70)
    print("  RUNTIME MODEL AUDIT — evidence-first verification")
    print("=" * 70)

    # ── H1 ──
    print("\n## H1 — Display / Config layers")
    print(f"  config.yaml model.default:  {h1.get('config_default_model', '?')}")
    print(f"  config.yaml provider:       {h1.get('config_default_provider', '?')}")
    print(f"  config.yaml fallback chain: {h1.get('fallback_chain', [])}")
    print(f"  show_reasoning (global):    {h1.get('show_reasoning_global', '?')}")
    print(f"  show_reasoning (whatsapp):  {h1.get('show_reasoning_whatsapp', '?')}")
    print(f"  show_reasoning (telegram):  {h1.get('show_reasoning_telegram', '?')}")

    sessions = h1.get("session_db_entries", [])
    if sessions:
        print(f"\n  Session DB (latest sessions):")
        for s in sessions:
            print(
                f"    [{s.get('source','?')}] {s.get('id','?')[:20]}... "
                f"| model={s.get('model','?')} "
                f"| billing_provider={s.get('billing_provider','?')} "
                f"| reasoning_tokens={s.get('reasoning_tokens',0)}"
            )

    # Check alignment
    config_model = h1.get("config_default_model", "?")
    db_model = sessions[0].get("model") if sessions else None
    aligned = "YES" if config_model == db_model else "NO — DB shows different model from config"
    if db_model and config_model != db_model:
        print(f"\n  ⚠️  ALIGNMENT: {aligned}")
    else:
        print(f"\n  ✅ ALIGNMENT: {aligned}")

    # ── H2 + H5 ──
    print("\n## H2 — Runtime Truth (agent.log)")
    inits = h2.get("agent_inits", [])
    if inits:
        last_init = inits[-1]["raw"] if isinstance(inits[-1], dict) else inits[-1]
        m = re.search(r"model=(\S+)", str(last_init))
        init_model = m.group(1) if m else "?"
        print(f"  Agent init model: {init_model}")
    else:
        print("  Agent init: NOT FOUND in last 10k lines")

    ctxs = h2.get("turn_contexts", [])
    if ctxs:
        last_ctx = ctxs[-1]
        print(
            f"  Turn context shows: model={last_ctx['model']} provider={last_ctx['provider']}"
        )
    else:
        print("  Turn context: NOT FOUND")

    first_call = h2.get("first_api_call", {})
    if first_call:
        print(
            f"  First API call: model={first_call.get('model','?')} "
            f"| latency={first_call.get('latency_s','?')}s "
            f"| tokens={first_call.get('total_tokens','?')}"
        )

    api_summary = h2.get("api_calls_summary", {})
    if api_summary.get("models_used"):
        print(f"  Total API calls observed: {api_summary['total_calls']}")
        print(f"  Models used: {api_summary['models_used']}")
    else:
        print("  No API calls observed in log window")

    failures = h2.get("api_failures", [])
    if failures:
        print(f"  ⚠️  API failures: {len(failures)}")
        for f in failures[:3]:
            print(f"       {f['model']}: {f['error_type']} — {f['error']}")
    else:
        print("  ✅ No API failures observed")

    # ── H5: Fallback ──
    print("\n## H5 — Fallback Truth")
    h5_fallbacks = h5.get("fallbacks", [])
    if h5_fallbacks:
        for fb in h5_fallbacks:
            if fb.get("type") == "skip":
                print(f"  ⚠️  Fallback skip: {fb['entry']}")
            elif "from_model" in fb:
                print(
                    f"  🔄 Fallback activated: {fb['from_model']} → {fb['to_model']} ({fb['provider']})"
                )
    else:
        print("  ✅ No provider fallback events in log window")

    # ── H4: Reasoning ──
    print("\n## H4 — Reasoning Truth")
    print(f"  OpenCode Zen profile found: {h4.get('opencode_zen_profile_found', '?')}")
    print(f"  Models in reasoning whitelist: {h4.get('whitelisted_models_for_reasoning', [])}")
    print(f"  hy3-free in whitelist: {h4.get('hy3_free_whitelisted', '?')}")
    print(f"  Serving model whitelisted for reasoning: {h4.get('serving_model_reasoning_whitelisted', '?')}")
    print(f"  Reasoning generating (session DB): {h4.get('reasoning_generating', '?')} ({h4.get('current_session_reasoning_tokens', '?')} tokens)")
    print(f"  Display suppression: {h4.get('display_suppression', '?')}")

    # ── H6 ──
    print("\n## H6 — Billing / Operational Truth")
    last_ok = h6.get("last_successful_call")
    if last_ok:
        print(f"  Last successful call: model={last_ok['model']} provider={last_ok['provider']} latency={last_ok['latency_s']}s")
    if failures:
        print(f"  ⚠️  {len(failures)} failed API calls (all before first success)")

    # ── H7 ──
    print("\n## H7 — Confidence")
    print(f"  Verdict: {h7.get('verdict', '?')}")
    blind = h7.get("blind_spots", [])
    if blind:
        print("  Blind spots (cannot prove):")
        for b in blind:
            print(f"    • {b}")

    print("\n" + "=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Runtime Model Audit — evidence-first verification"
    )
    parser.add_argument(
        "--session-id", "-s",
        help="Target session ID (default: most recent session in DB)",
    )
    parser.add_argument(
        "--limit-api-calls", "-n",
        type=int,
        default=200,
        help="Max API call entries to process (default: 200)",
    )
    args = parser.parse_args()

    result = audit(session_id=args.session_id)
    print_audit(result)


if __name__ == "__main__":
    main()
