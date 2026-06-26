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

### Decisions Made (2026-06-26)

| # | Decision | Rationale |
|---|---|---|
| 7 | **Persona renamed to MarryJane (MJ)** | User evolved SOUL.md from "Hermes" to "MarryJane" — a female PA persona with high EQ/IQ. Name "Jane" used in self-reference. Evidence-first, dislikes hallucinations. |
| 8 | **reasoning_effort set to xhigh** | After evaluation, user chose maximum reasoning depth. DeepSeek Pro supports thinking mode with best analysis quality. |
| 9 | **Obsidian integration** | Vault at `F:\obsidian-vault\` (PARA structure: 0-inbox through 5-journal + templates). `OBSIDIAN_VAULT_PATH` in `.env` connects Hermes to vault. Obsidian 1.12.7 portable at `F:\Obsidian\` (zero C: drive). Hermes can read, search, create, edit vault notes via Obsidian skill. |
| 10 | **Medication reminder system** | 20 cron jobs: 5 medication slots (Akurit-4, Dexa x3, Letram) + 15 follow-ups (+15/+30/+45 min each). Web-verified with Mayo Clinic, PubMed. Tracked in Health.md. User wants SERIOUS medical compliance. |
| 11 | **Total 27 cron jobs** | 7 system (from Phase 6-8) + 20 medication + DeepSeek Balance Check script. All active. |
| 12 | **Computer use attempt** | User tried but failed. Computer-use skill exists but isn't configured properly. Desired for remote desktop control from phone. Parked pending investigation. |
| 13 | **Gateway reliability fix (startup v3)** | Internet-check-before-start, post-start validation, 3-retry loop. Prevents gateway starting before hotspot connects. |
| 14 | **opencode.json push rule** | Changed from `"deny"` to `"ask"` — user can push with approval. GitHub also switched to SSH auth (no token). |
| 15 | **DeepSeek Balance Check** | No-agent cron script (`check_ds_balance.sh`) runs Mon/Fri to Telegram. Monitors DeepSeek credits via API. |
| 16 | **User calls MJ "Jane"** | Evolved organically through chat. SOUL.md updated: "When I refer to myself, use 'Jane'."

### Decisions Made (2026-06-26)

| # | Decision | Rationale |
|---|---|---|
| 1 | **Obsidian vault** created on F: drive at `F:\obsidian-vault\` with numbered PARA structure | Second brain / knowledge base accessible to Hermes via Obsidian skill. Plain .md files, zero lock-in. Portable app, zero C: drive impact. |
| 2 | **PARA folder system** adopted (0-inbox → 5-journal + templates) | Structured knowledge management: 0-inbox for quick capture, 1-projects for active work, 2-areas for ongoing responsibilities, 3-resources for reference, 4-archive for completed, 5-journal for daily logs. |
| 3 | **reasoning_effort** kept at xhigh (maps to max on DeepSeek API) | Evaluated high vs max cost difference. Max provides better reasoning quality. Cost overhead (~$0.0002-0.0007/query) negligible within RM25 monthly cap. Changed to high briefly but reverted — max stays as default. |
| 4 | **5 medication reminder cron jobs** deployed (06:00-20:00 daily) | Daily WhatsApp reminders for TB medication (Akurit-4), Dexamethasone (×3), Letram, and supplements. Each fires once, boss confirms dose via reply. |
| 5 | **Health.md in Obsidian vault** set as source of truth for medication schedule | All medication timing, verified instructions (empty stomach for Akurit-4, calcium timing), and cron job IDs documented in vault note. Hermes references it directly. |
