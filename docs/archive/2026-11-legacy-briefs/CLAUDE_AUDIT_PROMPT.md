# Claude Audit Prompt — Hermes Agent (MarryJane)

> Copy and paste this entire prompt to Claude. Attach `AUDIT.md` alongside this prompt.

---

## Context

You are auditing a personal AI assistant system called **Hermes Agent (MarryJane/MJ)** — a dual-platform (Telegram + WhatsApp) AI assistant built on top of NousResearch's Hermes Agent v0.17.0, running in WSL2 on Windows 11, with models routed through OpenCode Zen (free tier) and NVIDIA (free tier).

The owner Amirul has been building this system for ~5 days (24–28 June 2026) across 16 documented phases. The full system snapshot is in `AUDIT.md` (attached).

## System Constraints

1. **Zero C: drive usage** — everything lives on F:\ drive (WSL2 VHDX, Obsidian vault, cua-driver)
2. **Zero paid services** except DeepSeek API (which is not yet configured — currently routing through OpenCode Zen free tier)
3. **Privacy-critical** — all drug names, company names, and PII have been sanitized in docs; but medication cron jobs internally still use real drug names
4. **Malay/English/rojak** language flow
5. **Quiet hours** 23:00–07:00 MYT, max 3 proactive pings/day
6. **No systemd** in WSL2 — gateway managed via PowerShell Start-Process
7. **Google Gemini fully removed** — provider, registry, plugin all cleaned

## What I Need From You

Perform a **comprehensive deep audit** covering ALL of the following dimensions. Be specific, actionable, and prioritised. For each finding, state: (1) what the issue is, (2) why it matters, (3) how to fix it, and (4) priority (critical/high/medium/low).

### 1. Architecture & Reliability
- Is the current dual-platform (Telegram + WhatsApp) architecture sound for a personal assistant?
- The `gateway_state.json` persistence bug (stale "running" state after SIGTERM) — is this a Hermes design flaw or our misconfiguration? What's the proper fix?
- Gateway restart from phone (no PowerShell access) — is there any mechanism or workaround?
- The gateway currently starts from PowerShell via `Start-Process -WindowStyle Hidden` — what are the failure modes? Any better approach without systemd?
- **cua-driver MCP** runs as a subprocess of the gateway — any stability concerns?

### 2. Security & Privacy
- Review `AUDIT.md` for any remaining PII/exposure risks in the MJay repo or WSL2 configuration
- The cron system still stores real medication names internally (Akurit-4, Dexamethasone, Pyridoxine, Letram, etc.) — should we alias these in the cron system itself, or is this acceptable for a single-user system?
- API keys (NVIDIA, OpenCode Zen) were shared in plaintext during conversation — how should we handle secrets rotation? What's the proper process?
- `gateway_state.json` exposes PID, platform state — any concern?
- **baileys WhatsApp library** has 1 critical vulnerability (message spoofing / state corruption via crafted protocolMessage payload, GHSA-qvv5-jq5g-4cgg) with no upstream fix — is this a practical risk for a personal assistant bot? Should we pin to a specific known-safe commit, or switch to a different WhatsApp library?
- Any concerns with the custom trafilatura user plugin loading from `~/.hermes/plugins/`?
- Is there any risk with MCP servers (cua-driver.exe) running as subprocess of the gateway?

### 3. Model & Provider Configuration
- Current setup: DeepSeek V4 Flash Free (OpenCode Zen) as default, Vision via minimax M3 (NVIDIA) — is this optimal for a personal assistant?
- **Model overrides** (custom NVIDIA 5-model list, OpenCode Zen 6-model list, Gemini removal) are applied to source files (`hermes_cli/models.py`, `agent/models_dev.py`, `hermes_cli/auth.py`) — they survive `git pull` if no conflicts, but NOT `hermes update`. Is the current `fix-models.sh` recovery approach robust? Any better approach (e.g., config-only overrides, plugin)?
- **Config v31** — what changed from v30? Any important new features we should enable?
- Lack of **fallback provider** — is this risky? Should we configure OpenRouter or another fallback?
- DeepSeek API key exists but is not used (we route through OpenCode Zen) — is this optimal cost-wise? Should we switch to direct DeepSeek API?

### 4. Monitoring & Operations
- **Watchdog v2** runs every 5 min via crontab — does it actually work? Any gaps in crash detection?
- **Logs**: gateway.log (4.7 MB, 3046 lines), agent.log, errors.log — is log rotation working? Any log-related blind spots?
- **Gateway startup script v4** (`F:\hermes\gateway-start.ps1`) — internet-aware with 20×30s retry, post-start validation, 3-retry loop — is this robust enough? Any edge cases?
- **`hermes doctor` works** (0 errors, minor warnings) — how often should we run it? Should we add it to cron?

### 5. Cost & Sustainability
- Current cost: $0/month (OpenCode Zen free + NVIDIA free + DDGS free + faster-whisper local)
- Weaknesses: No fallback if free tiers change terms, no DeepSeek API usage yet
- What's the optimal path to a sustainable <$5/month setup?
- Is the current **prompt caching** (5min TTL) effective?

### 6. Cron & Job Health
- 27 active cron jobs (7 system + 20 medication) — are there too many? Any that can be consolidated?
- "Daily Health" has intermittent "Broken pipe" errors historically — root cause?
- No-agent script jobs (Log Rotate, DeepSeek Balance Check, Daily API Billing) seem stable — any improvements?
- The medication reminders are hardcoded in cron (20 jobs) — is there a better pattern (e.g., a single scheduler job that reads a config)?

### 7. Data & State Management
- `state.db` is ~50 MB with active WAL/SHM files — is this size normal for 5 days of usage (86 sessions)? Any cleanup needed?
- Session retention: 90 days — appropriate?
- Memory: `MEMORY.md` (2501 chars) + `USER.md` (1300 chars) — is this sufficient? Should we use an external memory provider?
- **Obsidian vault** at `F:\obsidian-vault\` is connected but not deeply integrated — any patterns for better Hermes-Obsidian synergy?

### 8. Development & Maintenance
- **Git repo is docs-only** (`amirulhazym/hermes-agent-personal_assistant`) — source changes saved as patch file. Is this the right strategy? Any risk of patch drift?
- The `__editable__.hermes_agent-0.17.0.pth` mechanism means `import tools` works but `import hermes_agent` does not — is this a concern?
- **Node.js/npm not on PATH** — WhatsApp bridge uses `~/.hermes/node/bin/node` via venv entry point. Should we add to PATH for easier maintenance?
- Upstream Hermes Agent evolves fast — what's the upgrade strategy? When to `hermes update` vs wait?

### 9. Feature Gaps
- **Computer use** (cua-driver) is installed and verified working — any usage patterns or limitations to be aware of?
- **Voice/TTS** currently uses edge-tts (free) — adequate or should we consider alternatives?
- **STT** uses faster-whisper (local, base model) — accuracy for Malay/English rojak?
- **Web search** via DDGS (free, unlimited) — any rate limit concerns?
- **Web extraction** via trafilatura (custom plugin) — limitations on JS-heavy sites?
- What features are we NOT using that Hermes v0.17.0 offers that would add value?

### 10. Backup & Disaster Recovery
- Current backup strategy: git push for docs, no automated backup for WSL2 disk/config
- What should be backed up? How often? Where?
- If the WSL2 VHDX corrupts, what's the estimated recovery time?
- Should we snapshot `~/.hermes/` periodically?

---

## Output Format

Please structure your response as:

```
# Executive Summary (2-3 paragraphs)

# Critical Issues (must fix immediately)
1. ...
2. ...

# High Priority
...

# Medium Priority (worth doing)
...

# Low Priority / Nice-to-Have
...

# Quick Wins (can do in <30 min each)
...

# Long-Term Recommendations
...

# Final Verdict
Overall system health score: X/10
Biggest risk: ...
Biggest strength: ...
```

Be brutally honest. Do not sugar-coat. The owner wants to know what can break, what is already broken, and what to fix before it breaks.
