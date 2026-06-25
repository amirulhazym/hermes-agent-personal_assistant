# DECISIONS.md — Hermes Personal AI Agent

> Record of verified facts, decisions made, source links checked, reasons, and human approvals.
> Maintained per PRD §0.

## Phase 0 — Pre-flight Verification (24 June 2026)

### Decision: Proceed to Phase 1

**Status**: APPROVED (conditional on A1-A2 amendments → applied)

### Verified Documentation Links

All links from PRD §6 verified against live pages on 2026-06-24:

| Link | Status | Notes |
|---|---|---|
| hermes-agent.nousresearch.com | LIVE | v0.17.0 (v2026.6.19) |
| github.com/NousResearch/hermes-agent | LIVE | 201k stars, MIT, 12,677 commits |
| hermes-agent.nousresearch.com/docs/ | LIVE | Full documentation available |
| api-docs.deepseek.com | LIVE | Models confirmed |
| api-docs.deepseek.com/quick_start/pricing | LIVE | Pricing matches PRD exactly |
| api-docs.deepseek.com/quick_start/agent_integrations/hermes | LIVE | Hermes integration guide confirmed |
| github.com/WhiskeySockets/Baileys | LIVE | v7.0.0-rc13, 9.9k stars, actively maintained |
| core.telegram.org/bots/api | NOT FETCHED | Standard, well-known; not verified (low risk) |
| docs.oracle.com/.../Always_Free_Resources.htm | LIVE | Limits confirmed: 2 OCPUs, 12 GB, 200 GB |
| opencode.ai/docs/config/ | LIVE | Schema confirmed, PRD's opencode.json valid |
| opencode.ai/docs/permissions/ | LIVE | v1.1.1+, granular rules confirmed |

### Verified Facts

#### Hermes Agent (as of 2026-06-24)
- **Current version**: v0.17.0 (tag: v2026.6.19, released 2026-06-19)
- **Install command**: `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`
- **Windows install**: `iex (irm https://hermes-agent.nousresearch.com/install.ps1)`
- **Hermes home**: `~/.hermes/`
- **Config file**: `~/.hermes/config.yaml` (YAML format)
- **Secrets file**: `~/.hermes/.env`
- **Memory files**: `~/.hermes/memories/MEMORY.md` + `USER.md` (profile-scoped, shared across all platforms)
- **Persona file**: `~/.hermes/SOUL.md`
- **WhatsApp session**: `~/.hermes/platforms/whatsapp/session/`
- **Gateway service**: `hermes gateway install` (user service) or `sudo hermes gateway install --system`
- **Cron**: Anti-loop built-in, 60s scheduler tick, file-locked at `~/.hermes/cron/.tick.lock`
- **Jobs storage**: `~/.hermes/cron/jobs.json`
- **Circuit breaker**: Per-adapter, auto-pause on failures, `/platform list` for inspection
- **Model wizard**: `hermes model` (interactive, not `hermes model setup`)
- **DeepSeek provider**: First-class support via `DEEPSEEK_API_KEY`

#### DeepSeek API (as of 2026-06-24)
- **Current model IDs**: `deepseek-v4-flash`, `deepseek-v4-pro`
- **Legacy aliases**: `deepseek-chat`, `deepseek-reasoner` → deprecated 2026-07-24 15:59 UTC
- **Base URL (OpenAI format)**: `https://api.deepseek.com`
- **Base URL (Anthropic format)**: `https://api.deepseek.com/anthropic`
- **Context window**: 1M tokens input
- **Max output**: 384K tokens
- **Concurrency limits**: Flash 2500, Pro 500
- **Context caching**: Automatic disk-based, enabled by default, best-effort
- **Pricing (per 1M tokens)**:
  - Flash cache-hit input: $0.0028
  - Flash cache-miss input: $0.14
  - Flash output: $0.28
  - Pro cache-hit input: $0.003625
  - Pro cache-miss input: $0.435
  - Pro output: $0.87
- **Spending-limit API**: None. Only manual balance monitoring. Credits deducted from topped-up or granted balance.

#### Baileys (WhatsApp Bridge)
- **Status**: Actively maintained by WhiskeySockets / Rajeh Taher
- **Latest release**: v7.0.0-rc13 (2026-05-21)
- **Stats**: 9.9k stars, 3.1k forks, 2,256 commits, 46 releases
- **Risk**: Unofficial reverse-engineered protocol. WhatsApp can break compatibility.
- **Hermes mitigation**: Circuit breaker, session persistence, re-pair flow, `/platform` monitoring
- **Upgrade path**: Hermes supports WhatsApp Business Cloud API as an official alternative adapter

#### Oracle Cloud Always Free (as of 2026-06-24)
- **ARM compute**: 1,500 OCPU hours + 9,000 GB hours monthly = 2 OCPUs + 12 GB memory
- **Block volume**: 200 GB total (boot + block)
- **Minimum boot volume**: 47 GB (default 50 GB for compute instances)
- **Images**: Ubuntu is Always Free-eligible
- **Idle reclamation**: CPU < 20% (95th %ile), network < 20%, memory < 20% over 7 days
- **Capacity risk**: "Out of host capacity" errors possible; retry or choose different AD
- **Identity verification**: Credit/debit card required

#### OpenCode Configuration (as of 2026-06-23)
- **Schema URL**: `https://opencode.ai/config.json` — current
- **Version**: v1.1.1+ (permissions refactored, legacy `tools` boolean config deprecated)
- **PRD's opencode.json**: Fully valid against current schema
- **Permission keys**: `read`, `edit`, `glob`, `grep`, `bash`, `task`, `skill`, `question`, `webfetch`, `websearch`, `lsp`, `external_directory`, `doom_loop`
- **Default permission model**: Most permissions default to `"allow"`, `.env` files denied by default for `read`
- **Added**: `"task": "ask"` to gate subagent launches (not in original PRD config)
- **Granular bash rules**: Wildcard pattern matching with `*` and `?`. Last matching rule wins.

### Deviations from Original PRD

1. **WhatsApp session path**: Docs show `~/.hermes/platforms/whatsapp/session/`, not `~/.hermes/.env`. PRD amended (A5).
2. **WhatsApp phone format**: Docs require country code WITHOUT leading `+`. PRD amended (A5).
3. **CLI command**: `hermes model` is the interactive wizard. `hermes model setup` does not exist.
4. **Config keys**: Actual Hermes config uses `model.provider` + `model.default` structure.
5. **Memory sharing**: Confirmed profile-scoped across all platforms — architecture matches PRD intent exactly.
6. **Circuit breaker**: Built into Hermes — PRD amended (A3).
7. **Cron anti-loop**: Hermes enforces this natively. PRD acknowledged.
8. **WhatsApp Cloud API**: Hermes supports official Meta path — PRD amended (A8).

### PRD Amendments Applied

| # | Section | Change | Priority |
|---|---|---|---|
| A1 | §15 Risks | Added "DeepSeek API outage/rate-limit/degraded" risk row | Critical |
| A2 | New §4.4 | Added hard spend cap mechanism (monthly budget, cron guard, per-job budgets) | Critical |
| A3 | §5 Architecture | Added circuit breaker documentation | High |
| A4 | §9 Phase 2 | Added Hermes version pin to v0.17.0 (v2026.6.19) | High |
| A5 | §8.1 Env vars | Corrected WhatsApp session path and phone format | Medium |
| A6 | §9 Phase 9, §11.1 | Marked free web lookup as best-effort only | Medium |
| A7 | §8.4 Gateway config | Verified YAML nesting already correct (no change needed) | Low |
| A8 | §13.3 Platform risk | Documented WhatsApp Cloud API as official upgrade path | Low |

### Decisions Made (2026-06-24)

1. **Host target**: Owned hardware — WSL2 on user's Windows 11 PC, distro stored at `F:\wsl\hermes-agent\` (zero C: drive impact). Ryzen 5 5600G, 16 GB RAM, F: drive 250+ GB free.
2. **DeepSeek API key**: Ready and configured
3. **WhatsApp bot number**: Dedicated SIM registered for WhatsApp (Baileys bridge)
4. **WhatsApp user number**: Owner's personal number (allowlisted, can message bot)
5. **Telegram**: Bot created via @BotFather. User allowlisted.
6. **Spend cap**: RM25 (~$5.30 USD) for first-month monitoring. Reassess after one month.
7. **Timezone**: Asia/Kuala_Lumpur (default)
8. **Proactive caps**: 3/day + 2/week (default)
9. **Coding agent**: OpenCode (currently in use)
10. **WSL2 distro**: Named `hermes-agent`, Ubuntu 24.04.4 LTS, user: amirul
11. **Hermes version**: v0.17.0 (2026.6.19) — matches pinned version
12. **Both platforms verified working**: Telegram responds via DeepSeek V4 Flash. WhatsApp responds via DeepSeek V4 Flash. Gateway connects both platforms from single process.
13. **DeepSeek Pro escalation**: To use `deepseek-v4-pro` for hard tasks, send `/model deepseek:deepseek-v4-pro` in any chat or run `hermes config set model.default deepseek-v4-pro` + gateway restart. Pro is owner/admin-only (gated via `allow_admin_from`). Flash is restored with `/model deepseek:deepseek-v4-flash`.
14. **Access control**: Non-allowlisted users denied by default (`GATEWAY_ALLOW_ALL_USERS` not set). Telegram allowlist: owner user ID. WhatsApp allowlist: owner's personal number. Admin/user split configured: owner has admin access.

### Still Open

All infrastructure and account questions resolved.

### Decisions Made (2026-06-25)

| # | Decision | Rationale |
|---|---|---|
| 1 | **Systemd disabled** in WSL2 | Systemd caused WSL2 hangs and killed background gateway processes. Default WSL2 init handles `setsid`/`nohup` correctly. |
| 2 | **Docker Desktop moved to F:** | Freed 4.8 GB on C: drive. All WSL distros now on F:\wsl\. |
| 3 | **Gateway startup script (v2)** | Uses `pgrep` exit codes instead of text parsing for reliable detection. Located at `F:\hermes\gateway-start.ps1`. |
| 4 | **Watchdog cron** | Every 5 min, no-agent ($0), auto-restarts gateway if dead. |
| 5 | **RUNBOOK.md written** | Complete operational documentation covering all procedures. |
| 6 | **Phase 10 security audit** | All 5 items passed. Allowlists, secrets, logs, permissions verified. |
