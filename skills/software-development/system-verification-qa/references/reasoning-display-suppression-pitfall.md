# Reasoning Display Suppression — Diagnostic Checklist

## Symptom

User reports: "Reasoning effort set to xhigh but response comes back instantly with no visible thinking."

## Root Causes (ordered by probability)

### 1. Platform-level show_reasoning: false (MOST COMMON)

Config path: `display.platforms.<platform>.show_reasoning` and `display.show_reasoning`

- WhatsApp defaults to `false` for performance (line 411 in config.yaml)
- Telegram defaults to `true`
- The global `display.show_reasoning` (line 427) is a master switch

**The model IS thinking. The API returns `reasoning_content`. The gateway strips it before delivery.**

### 2. Question is too simple

DeepSeek V4 Flash completes thinking in ~2 seconds for trivial questions ("What is 2+2?"). User sees instant response → assumes no thinking.

Evidence: live-probed 2026-07-15 — deepseek-v4-flash with xhigh produced 95 reasoning tokens in 2.51s for "What is 2+2?".

### 3. Model family always thinks

DeepSeek V4 family ALWAYS returns `reasoning_content` through the opencode relay — even when no `reasoning_effort` field is sent. The `extra_body.thinking.type=disabled` toggle returns status 200 but thinking still appears in the response.

## Diagnostic Protocol

Do NOT assume "no thinking" from user's subjective experience alone. Verify empirically:

```
Step 1: Check config
  → grep -A2 'show_reasoning' ~/.hermes/config.yaml
  → Check both display.show_reasoning AND display.platforms.<platform>.show_reasoning

Step 2: Live API probe (detached from Hermes gateway)
  → Use the probe script: scripts/probe-reasoning-effort.py
  → Or direct curl_cffi (impersonate=chrome120) — plain urllib gets Cloudflare 403
  → Send identical prompt with reasoning_effort=xhigh
  → Check response for: reasoning_content (DeepSeek) or reasoning (MiMo) or reasoning_details (MiMo)
  → Check usage.completion_tokens_details.reasoning_tokens

Step 3: Compare tokens
  → xhigh vs no-effort-field → should differ significantly for complex prompts
  → Small variance for simple prompts is NORMAL

Step 4: If API probe confirms thinking but user can't see it
  → Fix: hermes config set display.platforms.whatsapp.show_reasoning true
  → Alternative: just confirm to user "API confirms thinking with N tokens"
```

## Config Reference

```yaml
# ~/.hermes/config.yaml
display:
  show_reasoning: false                    # Master switch — affects ALL platforms
  reasoning_full: false                    # Full vs truncated reasoning
  reasoning_style: code                    # Display format
  platforms:
    whatsapp:
      show_reasoning: false                # WhatsApp-specific override
    telegram:
      show_reasoning: true                 # Telegram sees reasoning
```

## Provenance

- Discovered 2026-07-15: User reported xhigh "not working" on WhatsApp but API proved 95 reasoning tokens returned
- Root cause: `display.platforms.whatsapp.show_reasoning: false` (default config)
- Verified via 5-effort-level probe (xhigh/medium/max/low/none) all returning reasoning_content
