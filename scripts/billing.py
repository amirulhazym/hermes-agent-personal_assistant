#!/usr/bin/env python3
"""Unified API billing checker for Hermes.

Checks DeepSeek (pay-per-use balance) and OpenCode Go (subscription usage).
Output is designed for Telegram/WhatsApp display.
"""

import json
import os
import subprocess
import sys
from datetime import datetime


def redact(text):
    """Redact sensitive patterns from output."""
    import re
    text = re.sub(r'(?i)(sk-|API[_-]KEY|api[_-]key)[\w\-_.]{10,}', r'\1***', text)
    text = re.sub(r'[\w\-_.]{20,}', lambda m: m.group(0)[:6] + '***' + m.group(0)[-4:] if
                  any(c in m.group(0) for c in '.-_') and len(m.group(0)) > 20 else m.group(0), text)
    return text


def get_env_val(key):
    """Read env value from ~/.hermes/.env"""
    env_path = os.path.expanduser("~/.hermes/.env")
    if not os.path.exists(env_path):
        return None
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == key:
                return v.strip('"\' ')
    return None


def check_deepseek():
    """Check DeepSeek API balance."""
    api_key = get_env_val("DEEPSEEK_API_KEY")
    if not api_key:
        return None

    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "10",
             "https://api.deepseek.com/v1/user/balance",
             "-H", f"Authorization: Bearer {api_key}",
             "-H", "Accept: application/json"],
            capture_output=True, text=True, timeout=12
        )
        if result.returncode != 0:
            return {"error": f"curl failed (exit {result.returncode})"}

        data = json.loads(result.stdout)

        balance_infos = data.get("balance_infos", [])
        if not balance_infos and "total_balance" in data:
            balance_infos = [data]

        available = data.get("is_available", True)
        lines = []

        for b in balance_infos:
            currency = b.get("currency", "??")
            balance = b.get("total_balance", "0")
            try:
                balance_f = float(balance)
            except (ValueError, TypeError):
                balance_f = 0

            lines.append({
                "currency": currency,
                "balance": balance_f,
                "available": available,
            })

        return {"lines": lines, "available": available}
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse: {e}"}
    except subprocess.TimeoutExpired:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}


def check_opencode_go():
    """Check OpenCode Go subscription usage.

    OpenCode Go has no publicly documented usage API. We probe candidate
    undocumented endpoints with the Go bearer key. If none respond, we
    return a fallback message directing the user to the console.

    Usage limits (per official docs):
      5-hour:  $12
      weekly:  $30
      monthly: $60
    """
    api_key = get_env_val("OPENCODE_GO_API_KEY")
    if not api_key:
        return None

    candidate_endpoints = [
        "https://opencode.ai/zen/go/v1/usage",
        "https://opencode.ai/api/v1/usage",
        "https://opencode.ai/auth/api/usage",
        "https://opencode.ai/zen/v1/usage",
    ]

    for url in candidate_endpoints:
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "8", "-w", "\n%{http_code}",
                 url,
                 "-H", f"Authorization: Bearer {api_key}",
                 "-H", "Accept: application/json"],
                capture_output=True, text=True, timeout=10
            )
            raw = result.stdout.strip()
            if not raw:
                continue

            # Split body and HTTP status code (curl -w appends status)
            parts = raw.rsplit("\n", 1)
            if len(parts) == 2:
                body, status_str = parts
            else:
                body, status_str = raw, "0"

            try:
                status = int(status_str.strip())
            except ValueError:
                status = 0

            if status == 404 or status == 401 or status == 403:
                continue

            if status == 200:
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    continue

                # Try to extract usage from various possible response shapes
                usage = data.get("usage") or data.get("data") or data
                if not isinstance(usage, dict):
                    continue

                five_h = _extract_cost(usage, ["five_hour", "5h", "hourly_5", "current_5h"])
                weekly = _extract_cost(usage, ["weekly", "week", "current_week"])
                monthly = _extract_cost(usage, ["monthly", "month", "current_month"])

                if five_h is not None or weekly is not None or monthly is not None:
                    return {
                        "five_hour": five_h or 0.0,
                        "weekly": weekly or 0.0,
                        "monthly": monthly or 0.0,
                        "endpoint": url,
                    }

        except subprocess.TimeoutExpired:
            continue
        except Exception:
            continue

    return {"fallback": True}


def _extract_cost(data, keys):
    """Extract a cost value from a dict using candidate keys."""
    for k in keys:
        if k in data:
            try:
                v = data[k]
                if isinstance(v, dict):
                    v = v.get("cost") or v.get("amount") or v.get("usage") or v.get("dollars")
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def fetch_rates():
    """Fetch CNY→MYR and CNY→USD rates."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "10",
             "https://api.exchangerate-api.com/v4/latest/CNY"],
            capture_output=True, text=True, timeout=12
        )
        data = json.loads(result.stdout)
        rates = data.get("rates", {})
        return {
            "MYR": rates.get("MYR", "N/A"),
            "USD": rates.get("USD", "N/A"),
            "SGD": rates.get("SGD", "N/A"),
        }
    except Exception:
        return {"MYR": "N/A", "USD": "N/A", "SGD": "N/A"}


def format_balance(amount, currency):
    """Format a balance value with currency symbol."""
    symbols = {"CNY": "¥", "USD": "$", "MYR": "RM", "SGD": "S$", "EUR": "€", "GBP": "£"}
    sym = symbols.get(currency, f"{currency} ")
    return f"{sym}{amount:.2f}"


def usage_bar(used, cap):
    """Render an ASCII usage bar with percentage."""
    pct = (used / cap * 100) if cap > 0 else 0
    bar_width = 10
    filled = int(pct / 100 * bar_width)
    filled = min(filled, bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    pct_str = f"{pct:.0f}%"
    color_emoji = "🟢" if pct < 60 else ("🟡" if pct < 85 else "🔴")
    return f"{color_emoji} {bar} ${used:.2f}/${cap:.0f} ({pct_str})"


def main():
    output_lines = []
    output_lines.append("📊 **API Billing Report**")
    output_lines.append(f"🕐 {datetime.now().strftime('%d %b %Y, %I:%M %p')}")
    output_lines.append("")

    # ── DeepSeek (pay-per-use balance) ──
    ds = check_deepseek()
    if ds is None:
        output_lines.append("❌ **DeepSeek** — no API key configured")
    elif "error" in ds:
        output_lines.append(f"⚠️ **DeepSeek** — {ds['error']}")
    else:
        status_icon = "✅" if ds.get("available", False) else "⚠️"
        output_lines.append(f"{status_icon} **DeepSeek** (pay-per-use)")
        output_lines.append(f"   Status: {'Available' if ds.get('available') else 'Unavailable'}")

        rates = fetch_rates()
        for entry in ds["lines"]:
            cur = entry["currency"]
            bal = entry["balance"]
            formatted = format_balance(bal, cur)
            output_lines.append(f"   · Balance: {formatted}")

            if cur == "CNY" and bal > 0:
                myr = rates.get("MYR", "N/A")
                usd = rates.get("USD", "N/A")
                sgd = rates.get("SGD", "N/A")
                conversions = []
                if myr != "N/A":
                    conversions.append(f"~RM{bal * float(myr):.2f}")
                if usd != "N/A":
                    conversions.append(f"~${bal * float(usd):.2f} USD")
                if sgd != "N/A":
                    conversions.append(f"~S${bal * float(sgd):.2f}")
                if conversions:
                    output_lines.append(f"   · ≈ {' · '.join(conversions)}")

    output_lines.append("")

    # ── OpenCode Go (subscription usage) ──
    go = check_opencode_go()
    if go is None:
        output_lines.append("❌ **OpenCode Go** — no API key configured")
    elif go.get("fallback"):
        output_lines.append("📦 **OpenCode Go** (subscription)")
        output_lines.append("   · Usage limits: $12/5h · $30/week · $60/month")
        output_lines.append("   · ℹ️  No public usage API — check console:")
        output_lines.append("   · 🔗 https://opencode.ai/auth")
    else:
        output_lines.append("📦 **OpenCode Go** (subscription)")
        output_lines.append(f"   · Usage limits: $12/5h · $30/week · $60/month")
        output_lines.append("")
        output_lines.append(f"   5-hour:  {usage_bar(go['five_hour'], 12)}")
        output_lines.append(f"   Weekly:  {usage_bar(go['weekly'], 30)}")
        output_lines.append(f"   Monthly: {usage_bar(go['monthly'], 60)}")

    output_lines.append("")
    output_lines.append("───")
    output_lines.append("💡 Usage: /billing · or ask 'check billing'")

    raw_output = "\n".join(output_lines)
    print(redact(raw_output))


if __name__ == "__main__":
    main()
