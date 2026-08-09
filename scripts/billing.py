#!/usr/bin/env python3
"""Unified API billing checker for Hermes.

Checks:
  - DeepSeek (pay-per-use balance via API)
  - OpenCode Go (subscription — fallback to console URL)
  - Self-tracked usage (aggregated from Hermes session DB)
Output is designed for Telegram/WhatsApp display.
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta


def redact(text):
    """Redact sensitive patterns from output."""
    import re
    text = re.sub(r'(?i)(sk-|API[_-]KEY|api[_-]key)[\w\-_.]{10,}', r'\1***', text)
    # Redact only strings that look like high-entropy API keys/tokens
    # (starts with sk-/pk-/tok-/, or has mixed-case + digits + >30 chars)
    text = re.sub(
        r'\b(?:sk-|pk-|tok-|ghp_|gho_|ghu_|ghs_|ghr_)[\w\-]{20,}\b',
        lambda m: m.group(0)[:8] + '***' + m.group(0)[-4:],
        text,
    )
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
    """Check OpenCode Go subscription status.

    OpenCode Go has NO publicly documented usage/billing API.
    Verified by testing 6+ candidate endpoints — all returned 404.
    The only way to see usage is via the web console (requires OAuth login).

    This function verifies the API key is valid by making a minimal test
    call to the correct Go endpoint, then returns subscription info.

    Usage limits (per official docs):
      5-hour:  $12
      weekly:  $30
      monthly: $60
    """
    api_key = get_env_val("OPENCODE_GO_API_KEY")
    if not api_key:
        return None

    # Verify key is valid with a minimal test call to the correct Go endpoint
    # Correct endpoint (from official docs): https://opencode.ai/zen/go/v1/chat/completions
    key_valid = False
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "10",
             "https://opencode.ai/zen/go/v1/chat/completions",
             "-H", f"Authorization: Bearer {api_key}",
             "-H", "Content-Type: application/json",
             "-d", '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"ok"}],"max_tokens":1}'],
            capture_output=True, text=True, timeout=12
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                if "usage" in data or "choices" in data:
                    key_valid = True
            except json.JSONDecodeError:
                pass
    except Exception:
        pass

    return {
        "key_valid": key_valid,
        "fallback": True,  # No usage API available
    }


# ── OpenCode Go model pricing (per 1M tokens, from official docs) ──
# Source: https://opencode.ai/docs/usage/go (retrieved 2026-07-03)
GO_MODEL_PRICING = {
    # model_id: (input_per_1M, output_per_1M, cached_read_per_1M)
    "deepseek-v4-flash":       (0.27, 1.10, 0.027),
    "deepseek-v4-pro":         (0.55, 2.19, 0.055),
    "mimo-v2.5":               (0.14, 0.28, 0.0028),
    "mimo-v2.5-pro":           (1.74, 3.48, 0.0145),
    "glm-5.2":                 (1.40, 4.40, 0.26),
    "glm-5.1":                 (1.40, 4.40, 0.26),
    "kimi-k2.7-code":          (0.95, 4.00, 0.19),
    "kimi-k2.6":               (0.95, 4.00, 0.16),
    "minimax-m3":              (0.20, 0.80, 0.02),
    "minimax-m2.7":            (0.15, 0.60, 0.015),
    "qwen3.7-max":             (0.50, 2.00, 0.05),
    "qwen3.7-plus":            (0.30, 1.20, 0.03),
    "qwen3.6-plus":            (0.30, 1.20, 0.03),
}


def estimate_go_cost(model, input_tokens, output_tokens, cache_read_tokens=0):
    """Estimate USD cost for an OpenCode Go API call based on token counts."""
    if not model:
        return 0.0
    # Normalize model name (strip opencode-go/ prefix, lowercase)
    model_key = model.lower().replace("opencode-go/", "")
    pricing = GO_MODEL_PRICING.get(model_key)
    if not pricing:
        return 0.0
    input_rate, output_rate, cached_rate = pricing
    # Cost = (tokens / 1_000_000) * rate_per_1M
    cost = (input_tokens / 1_000_000 * input_rate
            + output_tokens / 1_000_000 * output_rate
            + cache_read_tokens / 1_000_000 * cached_rate)
    return cost


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


def _fmt_num(n):
    """Format a large number with commas."""
    if n is None:
        return "0"
    return f"{n:,}"


def check_self_tracked():
    """Query Hermes session DB for actual token usage by provider."""
    state_db = os.path.expanduser("~/.hermes/state.db")
    if not os.path.exists(state_db):
        return None

    try:
        conn = sqlite3.connect(state_db)
        conn.row_factory = sqlite3.Row
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)

        def _ts(dt):
            return dt.timestamp()

        # Today per provider
        cur = conn.execute("""
            SELECT
                billing_provider,
                COUNT(*) as sessions,
                SUM(input_tokens) as in_tok,
                SUM(output_tokens) as out_tok,
                SUM(cache_read_tokens) as cache_r,
                SUM(cache_write_tokens) as cache_w,
                SUM(reasoning_tokens) as reason_tok
            FROM sessions
            WHERE started_at >= ? AND billing_provider IS NOT NULL
            GROUP BY billing_provider
            ORDER BY SUM(output_tokens) DESC
        """, (_ts(today_start),))
        today_rows = cur.fetchall()

        # This week
        cur = conn.execute("""
            SELECT billing_provider,
                   SUM(input_tokens + output_tokens) as total
            FROM sessions
            WHERE started_at >= ? AND billing_provider IS NOT NULL
            GROUP BY billing_provider
        """, (_ts(week_start),))
        week_map = {r["billing_provider"]: r["total"] or 0 for r in cur.fetchall()}

        # This month
        cur = conn.execute("""
            SELECT billing_provider,
                   SUM(input_tokens + output_tokens) as total
            FROM sessions
            WHERE started_at >= ? AND billing_provider IS NOT NULL
            GROUP BY billing_provider
        """, (_ts(month_start),))
        month_map = {r["billing_provider"]: r["total"] or 0 for r in cur.fetchall()}

        # Model breakdown (all time, recent first)
        cur = conn.execute("""
            SELECT billing_provider, model,
                   SUM(input_tokens + output_tokens) as total_tok,
                   MAX(started_at) as last_used
            FROM sessions
            WHERE billing_provider IS NOT NULL AND model IS NOT NULL
            GROUP BY billing_provider, model
            ORDER BY last_used DESC
            LIMIT 15
        """)
        model_rows = cur.fetchall()

        # Go cost estimation (month)
        cur = conn.execute("""
            SELECT model,
                   SUM(input_tokens) as in_tok,
                   SUM(output_tokens) as out_tok,
                   SUM(cache_read_tokens) as cache_r
            FROM sessions
            WHERE billing_provider LIKE '%opencode-go%'
              AND started_at >= ?
            GROUP BY model
        """, (_ts(month_start),))
        go_model_rows = cur.fetchall()

        conn.close()

        return {
            "today": today_rows,
            "week": week_map,
            "month": month_map,
            "models": model_rows,
            "go_cost_rows": go_model_rows,
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    output_lines = []
    output_lines.append("📊 **Billing Report**")
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
        output_lines.append(f"{status_icon} **DeepSeek** · {'Available' if ds.get('available') else 'Unavailable'}")

        rates = fetch_rates()
        for entry in ds["lines"]:
            cur = entry["currency"]
            bal = entry["balance"]
            if bal > 0:
                formatted = format_balance(bal, cur)
                if cur == "CNY":
                    myr = rates.get("MYR", "N/A")
                    usd = rates.get("USD", "N/A")
                    conv_parts = []
                    if myr != "N/A":
                        conv_parts.append(f"~RM{bal * float(myr):.2f}")
                    if usd != "N/A":
                        conv_parts.append(f"~${bal * float(usd):.2f}")
                    if conv_parts:
                        output_lines.append(f"   💰 {formatted} · {' · '.join(conv_parts)}")
                    else:
                        output_lines.append(f"   💰 {formatted}")

    output_lines.append("")

    # ── OpenCode Go (subscription usage) ──
    go = check_opencode_go()
    if go is None:
        output_lines.append("❌ **OpenCode Go** — no API key configured")
    elif go.get("fallback"):
        key_icon = "✅" if go.get("key_valid") else "⚠️"
        output_lines.append(f"📦 **OpenCode Go** · key {key_icon}")
        output_lines.append("   $12/5h · $30/week · $60/month")
    else:
        output_lines.append("📦 **OpenCode Go**")
        output_lines.append(f"   5h:  {usage_bar(go['five_hour'], 12)}")
        output_lines.append(f"   wk:  {usage_bar(go['weekly'], 30)}")
        output_lines.append(f"   mo:  {usage_bar(go['monthly'], 60)}")

    output_lines.append("")

    # ── Self-tracked usage (from Hermes session DB) ──
    st = check_self_tracked()
    if st and "error" not in st:
        today = st["today"]
        if today:
            output_lines.append("📈 **Self-Tracked** (month)")

            # Aggregate monthly totals per provider
            month_data = {}
            for row in today:
                p = row["billing_provider"] or "unknown"
                month_data[p] = st["month"].get(p, 0) or 0

            # Cost estimation for Go models
            total_month_cost = 0.0
            for mr in st.get("go_cost_rows", []):
                model = mr["model"] or ""
                cost = estimate_go_cost(
                    model,
                    (mr["in_tok"] or 0) + (mr["cache_r"] or 0),
                    mr["out_tok"] or 0,
                    mr["cache_r"] or 0,
                )
                total_month_cost += cost

            # Sort providers by token count descending
            sorted_providers = sorted(month_data.items(), key=lambda x: -x[1])
            total_month_tok = sum(month_data.values())
            bar_width = 10

            for p, mo_tok in sorted_providers:
                mo_fmt = _fmt_num(mo_tok)
                pct = (mo_tok / total_month_tok * 100) if total_month_tok > 0 else 0
                filled = int(pct / 100 * bar_width)
                filled = min(filled, bar_width)
                bar = "█" * filled + "░" * (bar_width - filled)
                output_lines.append(f"   {p:<14s} {mo_fmt:>10s}  {bar}  {pct:.0f}%")

            # Separator
            output_lines.append(f"   {'─' * 40}")

            # Total row
            total_fmt = _fmt_num(total_month_tok)
            output_lines.append(f"   {'Total':<14s} {total_fmt:>10s}  {'█' * bar_width}  100%")

            # Go spend row
            if total_month_cost > 0:
                go_pct = total_month_cost / 60 * 100 if total_month_cost > 0 else 0
                go_filled = int(go_pct / 100 * bar_width)
                go_filled = min(go_filled, bar_width)
                go_bar = "█" * go_filled + "░" * (bar_width - go_filled)
                output_lines.append(f"   {'💰 Spend':<14s} ${total_month_cost:<8.2f} {go_bar}  {go_pct:.0f}%  of $60")

            output_lines.append("")

        # Model breakdown — kept in code but disabled (too noisy for daily use)
        # if st.get("models"):
        #     output_lines.append("**Model breakdown** (all time, most recent first):")
        #     for m in st["models"][:8]:
        #         p = m["billing_provider"] or "?"
        #         model = m["model"] or "?"
        #         tok = _fmt_num(m["total_tok"] or 0)
        #         output_lines.append(f"   · `{model}` ({p}) — {tok} tokens")
    elif st and "error" in st:
        output_lines.append(f"⚠️ **Self-tracked usage** — {st['error']}")
    else:
        output_lines.append("ℹ️  **Self-tracked usage** — no session DB found")

    output_lines.append("")
    output_lines.append("───")
    output_lines.append("💡 Usage: /billing · or ask 'check billing'")

    raw_output = "\n".join(output_lines)
    print(redact(raw_output))


if __name__ == "__main__":
    main()
