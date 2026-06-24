# PRD — Hermes Personal AI Agent on WhatsApp + Telegram, powered by DeepSeek V4

> **Document type:** Product Requirements Document + build brief for an AI coding agent such as OpenCode or Codex.  
> **Product:** Personal Hermes Agent based on the real open-source Nous Research Hermes Agent.  
> **Version:** 2.0 final candidate  
> **Last updated:** 24 June 2026  
> **Primary language:** English for implementation precision. The finished assistant may speak Malay, English, or rojak according to user preference.  
> **Owner:** Amirul / user  
> **Execution style:** Build in explicit phases, with human checkpoints and strict human-in-the-loop guardrails.

---

## 0. How the coding agent must read this PRD

This file is the master spec. Treat it as the single source of truth unless the human explicitly updates it.

Before doing implementation work:

1. Read this entire PRD first.
2. Read Section 7, Human-in-the-Loop & Safety Protocol, twice. It overrides speed and convenience.
3. Fetch the latest official docs listed in Section 6 before running setup commands, writing config, or assuming model names, CLI flags, provider schemas, or pricing.
4. Work phase-by-phase. At the end of every phase, stop, report what changed, and wait for explicit approval before continuing.
5. Maintain:
   - `PROGRESS.md` — what was done, commands run, blockers, test results.
   - `DECISIONS.md` — decisions made, source links checked, reasons, and human approvals.
   - `RUNBOOK.md` — operational handover once the system is live.

This PRD is intentionally conservative. The goal is a powerful personal assistant, not an agent that silently does dangerous things.

---

## 1. Executive summary

The goal is to deploy and customize a powerful, humanized, always-on personal AI assistant named **Hermes** that can chat with the user through **WhatsApp and Telegram**, remember them over time, proactively message them first, and operate as a practical second brain.

The key product direction:

> Use the real open-source **Nous Research Hermes Agent** as the core agent. Do not build a separate Hermes clone from scratch.

Hermes Agent already provides the hardest foundation:

- persistent memory and cross-session recall;
- a self-improving skill system;
- one long-running messaging gateway process;
- support for WhatsApp, Telegram, and many other platforms;
- a cron scheduler that can proactively deliver messages to messaging platforms;
- model/provider abstraction;
- tool use, approvals, session management, and operational commands.

The final system should behave like:

> **One brain, many faces.**

WhatsApp and Telegram are not separate assistants. They are two access surfaces for the same Hermes brain:

- same durable memory;
- same `SOUL.md` persona;
- same user profile;
- same skills;
- same model configuration;
- same safety policy;
- same proactive scheduler.

Live chat threads may remain platform-specific, because that keeps WhatsApp and Telegram conversations clean. Durable knowledge must be shared across both.

Cost constraint:

> **DeepSeek API is the only paid component.**

Everything else must use free tiers, open-source software, self-hosting, or hardware the user already owns. Any additional paid service, hosted tool, API, fallback model, subscription, deployment product, or cloud resource requires explicit human approval.

---

## 2. Goals and non-goals

### 2.1 Goals

G1 — **Same Hermes brain across WhatsApp and Telegram**  
The user can talk to Hermes from either platform. Hermes should understand the same user, remember the same durable facts, and apply the same persona and safety policy.

G2 — **DeepSeek as the only paid brain**  
Default model is `deepseek-v4-flash`. Optional escalation to `deepseek-v4-pro` is allowed because it is still the same paid DeepSeek line item, but it must be owner-controlled.

G3 — **Humanized personal assistant**  
Hermes should feel like a useful, warm, sharp personal assistant — not a generic chatbot. It should adapt to the user’s language, tone, routines, goals, and preferred level of detail.

G4 — **Proactive behavior**  
Hermes can message first: briefings, check-ins, reminders, follow-ups, habit nudges, unfinished task prompts, and operational alerts.

G5 — **Persistent memory**  
Hermes remembers useful durable facts, preferences, commitments, recurring goals, deadlines, and corrections across restarts and across both messaging platforms.

G6 — **Free infrastructure where possible**  
The runtime should live on Oracle Cloud Always Free ARM or user-owned hardware. No paid infrastructure unless the human explicitly chooses it.

G7 — **Strict human-in-the-loop control**  
Build-time coding agents and the finished runtime assistant must both ask before destructive, irreversible, costly, credential-touching, public, third-party, or security-sensitive actions.

G8 — **Operationally survivable**  
The gateway should survive reboots and crashes, protect secrets, rotate logs, document recovery steps, and provide a runbook.

### 2.2 Non-goals for v1

- Do not build a new agent framework from scratch.
- Do not build a multi-tenant SaaS.
- Do not use a local LLM as the main model.
- Do not use paid web search, paid hosted browser automation, paid TTS, paid image generation, or paid non-DeepSeek fallback providers.
- Do not enable WhatsApp groups by default.
- Do not expose Hermes to non-allowlisted users.
- Do not use the official WhatsApp Business Cloud API in v1 unless the human later chooses it.
- Do not let Hermes autonomously spend money, send third-party messages, post publicly, delete data, or alter infrastructure without confirmation.

---

## 3. Product concept

Hermes should become a personal assistant that lives where the user already communicates.

### 3.1 Platform roles

| Platform | Role in v1 | Why it matters |
|---|---|---|
| WhatsApp | Daily natural chat, quick personal check-ins, reminders, casual conversation | User already uses it frequently; easiest access; feels human |
| Telegram | Control/admin surface, richer bot capabilities, files, topics, fallback if WhatsApp breaks | Official Bot API; easier customization; lower ban risk |

### 3.2 Same-brain behavior

Hermes must share durable knowledge across both platforms:

- user identity and preferences;
- language/tone preference;
- schedule/routine facts;
- goals and habits;
- deadlines and open loops;
- important people/projects;
- assistant rules and boundaries;
- learned skills.

Platform-specific live session history can remain separate:

- WhatsApp DM has its own active chat thread.
- Telegram DM has its own active chat thread.
- Telegram topics, if enabled later, each have isolated live context.

When the user switches platforms mid-task, Hermes should restore context through durable memory and session search rather than merging both live chats into one confusing stream.

### 3.3 Model selection behavior

Default:

- `deepseek-v4-flash`
- non-thinking or low-reasoning mode for routine chat if available and appropriate;
- cheap, fast, always-on behavior.

Optional escalation:

- `deepseek-v4-pro`
- owner/admin only;
- used for hard reasoning, planning, large synthesis, debugging, or high-stakes analysis;
- Hermes must expose usage/cost clearly through `/usage` or logs.

Avoid:

- `deepseek-chat`
- `deepseek-reasoner`

These legacy aliases were documented by DeepSeek as scheduled for deprecation on 2026-07-24 15:59 UTC. Use direct V4 model IDs.

---

## 4. Cost model and constraints

### 4.1 Hard cost rule

The only allowed paid component is:

- DeepSeek API usage for `deepseek-v4-flash` and optional `deepseek-v4-pro`.

Everything else must be free:

| Component | v1 choice | Cost |
|---|---|---|
| Agent framework | Nous Research Hermes Agent | Free / open source |
| WhatsApp transport | Hermes WhatsApp bridge via Baileys | Free |
| Telegram transport | Telegram Bot API through Hermes gateway | Free |
| Hosting | Oracle Cloud Always Free ARM or owned hardware | Free |
| Database/memory | Hermes local files + SQLite/session storage | Free |
| Scheduler | Hermes cron | Free |
| Source control | GitHub free or local git | Free |
| Web lookup | Free/self-host/open fallback only | Free |
| Coding agent | OpenCode or Codex available to the user | Free/already owned |

### 4.2 Explicitly forbidden without approval

The coding agent must not silently enable:

- Nous Portal subscription;
- paid hosted web search;
- paid hosted browser automation;
- paid image generation;
- paid TTS;
- OpenRouter paid fallback;
- Hugging Face paid inference fallback;
- paid VPS;
- WhatsApp Business Cloud API billing;
- Twilio/SMS;
- paid database or managed vector store;
- paid monitoring/Sentry/Datadog/etc.

If a paid option is the best route, document it as an optional upgrade and ask the human.

### 4.3 Token hygiene

To keep the DeepSeek bill tiny:

- Keep the system prompt and persona stable so context caching can help.
- Avoid rewriting massive system prompts every turn.
- Use Flash for routine chat, compression, extraction, and lightweight tool decisions.
- Use Pro only on explicit owner/admin command or a confirmed escalation.
- Set usage monitoring and monthly budget alerts.
- Add loop protection for cron and background tasks.

### 4.4 Hard spend cap

DeepSeek does not provide a spending-limit API. Credits are deducted from balance with no automatic throttle. To prevent runaway costs, the following mechanism must be implemented:

1. **Monthly budget**: Human sets a monthly DeepSeek spend ceiling in USD.
2. **Cron guard**: If month-to-date spend exceeds the ceiling, all cron jobs are automatically paused. User is alerted via Telegram.
3. **Per-job token budgets**: Each cron job has an approximate per-run token budget. Jobs that exceed their budget by more than 2× are rate-limited or paused.
4. **Re-enable**: Resuming cron after a cap breach requires explicit human action.
5. **Usage visibility**: `/usage` reports month-to-date spend. Weekly usage report delivered via cron to Telegram.

The cap mechanism must be implemented during Phase 6 (gateway service) at latest, using `hermes cron pause` / `hermes cron resume` and the DeepSeek usage data returned in API responses.

---

## 5. Architecture

```text
                        USER
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
   WhatsApp app                  Telegram app
   daily chat                    admin/rich chat
          │                             │
          │                             │
          ▼                             ▼
 ┌────────────────┐            ┌────────────────┐
 │ WhatsApp bridge│            │ Telegram Bot API│
 │ Baileys via    │            │ official bot    │
 │ Hermes gateway │            │ via Hermes      │
 └───────┬────────┘            └───────┬────────┘
         │                             │
         └──────────────┬──────────────┘
                        ▼
       ┌────────────────────────────────────┐
       │       Hermes Gateway Process        │
       │ one long-running multi-platform app │
       │                                    │
       │ - platform adapters                 │
       │ - session routing                   │
       │ - cron scheduler                    │
       │ - background tasks                  │
       │ - approvals                         │
       │ - slash commands                    │
       └─────────────────┬──────────────────┘
                         ▼
       ┌────────────────────────────────────┐
       │          Hermes Agent Core          │
       │                                    │
       │ - SOUL.md persona                   │
       │ - USER.md profile                   │
       │ - MEMORY.md / durable memory        │
       │ - SQLite/session search             │
       │ - skills and self-improvement       │
       │ - tool policy and safety rules      │
       └─────────────────┬──────────────────┘
                         ▼
       ┌────────────────────────────────────┐
       │          DeepSeek API               │
       │                                    │
       │ default: deepseek-v4-flash          │
       │ optional: deepseek-v4-pro           │
       │ base URL: https://api.deepseek.com  │
       └────────────────────────────────────┘
```

The Hermes gateway includes a built-in per-adapter circuit breaker. If the WhatsApp or Telegram adapter experiences repeated connection failures, network errors, or rate-limit responses, the breaker auto-pauses that adapter. An operator notification is sent to the home channel of another live platform. The user can inspect adapter state with `/platform list` and manually resume with `/platform resume <name>`. This reduces the risk of silent platform disconnection from a single-process gateway.

### 5.1 Hosting topology

Recommended:

- one Oracle Cloud Always Free ARM instance;
- Ubuntu Linux;
- one non-root `hermes` user;
- Hermes installed in the user account;
- gateway installed as a user service with lingering, or system service if explicitly chosen;
- all secrets in `~/.hermes/.env`;
- Hermes home backed up privately.

Alternative:

- user-owned mini-PC, old laptop, Raspberry Pi, or always-on Linux box.

### 5.2 Why Telegram is v1 core

Telegram is not just a backup. It gives Hermes a better control surface:

- official Bot API;
- no WhatsApp web-protocol ban risk;
- easy BotFather setup;
- file/image handling;
- rich bot commands;
- topics and parallel conversations;
- safer admin/control channel;
- useful fallback if WhatsApp pairing breaks.

WhatsApp remains the primary casual access surface because the user naturally lives there.

---

## 6. Official documentation to verify before build

The coding agent must open current official docs before implementation. Do not rely only on this PRD for volatile command syntax, model routing, pricing, or config schema.

### 6.1 Hermes Agent

- Main site: https://hermes-agent.nousresearch.com/
- GitHub repo: https://github.com/NousResearch/hermes-agent
- Docs home: https://hermes-agent.nousresearch.com/docs/
- Messaging gateway: https://hermes-agent.nousresearch.com/docs/user-guide/messaging
- WhatsApp: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/whatsapp
- Telegram: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram
- Cron scheduler: https://hermes-agent.nousresearch.com/docs/user-guide/features/cron
- Providers/model config: https://hermes-agent.nousresearch.com/docs/integrations/providers
- Configuration: https://hermes-agent.nousresearch.com/docs/user-guide/configuration

Key facts already verified on 24 June 2026:

- Hermes gateway supports many platforms from one process.
- Hermes gateway includes WhatsApp and Telegram.
- Gateway slash commands include `/model`, `/sethome`, `/usage`, `/status`, `/approve`, `/deny`, `/topic`, `/background`, and others.
- Cron delivery targets include `whatsapp`, `telegram`, and `all`.
- Telegram supports allowlists such as `TELEGRAM_ALLOWED_USERS`.
- WhatsApp docs specify `WHATSAPP_ENABLED`, `WHATSAPP_MODE`, and `WHATSAPP_ALLOWED_USERS`.
- WhatsApp bridge uses Baileys and requires Node.js, not Puppeteer/Chromium.

### 6.2 DeepSeek

- API docs: https://api-docs.deepseek.com/
- Pricing: https://api-docs.deepseek.com/quick_start/pricing
- Hermes integration: https://api-docs.deepseek.com/quick_start/agent_integrations/hermes
- Platform/API key: https://platform.deepseek.com/

Key facts already verified on 24 June 2026:

- Models include `deepseek-v4-flash` and `deepseek-v4-pro`.
- OpenAI-compatible base URL is documented as `https://api.deepseek.com`.
- Context length is 1M.
- Maximum output is 384K.
- JSON output and tool calls are supported.
- Pricing is per 1M tokens:
  - Flash cache-hit input: `$0.0028`
  - Flash cache-miss input: `$0.14`
  - Flash output: `$0.28`
  - Pro cache-hit input: `$0.003625`
  - Pro cache-miss input: `$0.435`
  - Pro output: `$0.87`
- Legacy names `deepseek-chat` and `deepseek-reasoner` are scheduled for deprecation on 2026-07-24 15:59 UTC.

### 6.3 WhatsApp and Telegram transports

- Baileys: https://github.com/WhiskeySockets/Baileys
- Telegram Bot API: https://core.telegram.org/bots/api
- BotFather: https://core.telegram.org/bots/features#botfather
- Optional WhatsApp Cloud API upgrade path: https://developers.facebook.com/docs/whatsapp/cloud-api

### 6.4 Coding-agent safety docs

OpenCode:

- Docs: https://opencode.ai/docs/
- Agents/Plan/Build: https://opencode.ai/docs/agents/
- Permissions: https://opencode.ai/docs/permissions/
- Config: https://opencode.ai/docs/config/
- Rules: https://opencode.ai/docs/rules/

Codex:

- CLI reference: https://developers.openai.com/codex/cli/reference
- Agent approvals & security: https://developers.openai.com/codex/agent-approvals-security
- Sandboxing: https://developers.openai.com/codex/concepts/sandboxing
- Config reference: https://developers.openai.com/codex/config-reference
- AGENTS.md guide: https://developers.openai.com/codex/guides/agents-md

### 6.5 Free hosting

- Oracle Cloud Free Tier: https://www.oracle.com/cloud/free/
- Always Free resources: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm

Key facts already verified on 24 June 2026:

- Always Free Ampere A1 is documented as 1,500 OCPU hours and 9,000 GB hours monthly.
- For Always Free tenancies, this is equivalent to **2 OCPUs and 12 GB memory**.
- Always Free block storage includes 200 GB total.
- Idle Always Free instances may be reclaimed under Oracle’s idle criteria.
- Credit/debit card identity verification is required.

---

## 7. Human-in-the-Loop & safety protocol

This is the highest-priority section.

The human must never be surprised.

These rules apply to:

1. the coding agent building Hermes;
2. Hermes itself at runtime.

### 7.1 Build-time HITL for coding agents

Before implementation, create project-level guardrails so safety does not depend on the human remembering to switch modes.

#### Always ask first

The coding agent must stop and ask before:

1. deleting, overwriting, truncating, or moving files destructively;
2. touching secrets, API keys, `.env`, WhatsApp session folders, Telegram bot tokens, or auth files;
3. committing, pushing, force-pushing, changing git remotes, or rewriting history;
4. spending money or enabling any paid service;
5. deploying, starting/stopping system services, editing systemd/launchd, or opening firewall ports;
6. installing system-level packages;
7. sending real messages to anyone except the user’s allowlisted test account;
8. scanning/linking WhatsApp QR;
9. editing outside the intended project/workspace;
10. running bulk operations with external effects;
11. enabling group access;
12. enabling allow-all access;
13. enabling paid fallback models/tools;
14. transmitting sensitive user data to external services beyond DeepSeek/Hermes requirements.

When asking, the agent must explain:

- what it wants to do;
- why it is needed;
- what command/config/diff will be used;
- what can go wrong;
- how to revert.

Then wait for an explicit human “yes”.

#### Allowed without asking

The coding agent may autonomously:

- read files;
- search the repo;
- inspect docs;
- draft files inside the project;
- run safe local checks;
- run tests/builds that do not alter tracked files;
- update documentation inside the project after the human has requested implementation.

### 7.2 OpenCode project guardrail

If OpenCode is used, create `opencode.json` at the project root.

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "plan",
  "share": "manual",
  "permission": {
    "*": "ask",
    "edit": "allow",
    "webfetch": "ask",
    "bash": {
      "*": "ask",
      "pwd": "allow",
      "ls *": "allow",
      "cat *": "allow",
      "grep *": "allow",
      "rg *": "allow",
      "git status": "allow",
      "git diff*": "allow",
      "git log*": "allow",
      "git add *": "ask",
      "git commit *": "ask",
      "git push *": "deny",
      "rm *": "deny",
      "mv *": "ask",
      "sudo *": "deny",
      "systemctl *": "ask",
      "docker *": "ask",
      "npm install -g *": "deny"
    },
    "external_directory": {
      "~/.hermes/**": "ask",
      "~/.codex/**": "ask",
      "~/.config/opencode/**": "ask"
    }
  }
}
```

Important: OpenCode Plan mode is safer, but this config is still required because the human may accidentally stay in Build mode.

### 7.3 Codex guardrail

If Codex is used, prefer conservative permissions.

Current Codex docs support both direct sandbox keys and newer permission profiles. Do not combine `default_permissions` with `sandbox_mode` / `[sandbox_workspace_write]`; choose one compatible approach for the installed Codex version and record the effective setting in `DECISIONS.md`.

Recommended current-profile baseline:

```toml
# ~/.codex/config.toml
default_permissions = ":workspace"

[apps._default]
destructive_enabled = false
open_world_enabled = false
default_tools_approval_mode = "prompt"
```

Paranoid planning/review profile:

```toml
# ~/.codex/paranoid.config.toml or equivalent profile file
default_permissions = ":read-only"

[apps._default]
destructive_enabled = false
open_world_enabled = false
default_tools_approval_mode = "prompt"
```

If the installed Codex version still uses direct sandbox keys, use this instead:

```toml
# ~/.codex/config.toml
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = false
```

Do not use:

- `danger-full-access`;
- `default_permissions = ":danger-full-access"`;
- `--ask-for-approval never`;
- `--dangerously-bypass-approvals-and-sandbox`;
- any “yolo” equivalent.

The important behavior is: routine project work may happen inside the workspace, while network access, external writes, destructive app/tool actions, and risky operations require human confirmation.

### 7.4 AGENTS.md requirement

Create `AGENTS.md` at the project root with:

```md
# Agent Safety Rules

Before any destructive, irreversible, costly, credential-touching, deploy, external-message, public-posting, or out-of-scope action, STOP and ask the human in plain language. Wait for an explicit "yes".

These rules apply regardless of Plan mode, Build mode, sandbox mode, or approval presets.

Never print, commit, upload, or transmit secrets. Treat `.env`, Telegram bot tokens, DeepSeek keys, and WhatsApp session folders as sensitive.

No paid service may be enabled unless the human explicitly approves it.
```

### 7.5 Runtime HITL inside Hermes

The finished Hermes assistant must ask before:

- sending a message/email to a third party;
- posting publicly;
- deleting or overwriting data;
- changing infrastructure;
- running shell commands with side effects;
- exposing secrets;
- making purchases or enabling paid services;
- modifying calendar/events if connected later;
- contacting other people;
- joining or responding in groups;
- switching to a more expensive mode automatically.

Use a draft-confirm-act pattern:

1. Draft the proposed action.
2. Ask for confirmation.
3. Wait for explicit approval.
4. Execute only the approved action.
5. Report the result.

---

## 8. Configuration interfaces

This section defines the intended public config surface. Exact schema and command names must be verified against current docs during implementation.

### 8.1 Environment variables

Store secrets in `~/.hermes/.env`.

```bash
# DeepSeek
DEEPSEEK_API_KEY=...

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_USERS=123456789

# WhatsApp
WHATSAPP_ENABLED=true
WHATSAPP_MODE=bot
WHATSAPP_ALLOWED_USERS=60123456789       # country code, digits only, no + sign

Never commit this file. WhatsApp session credentials are stored in `~/.hermes/platforms/whatsapp/session/` (managed by `hermes whatsapp`, never hand-edit). Protect this directory like a password.

### 8.2 Hermes model config

Representative `~/.hermes/config.yaml` intent:

```yaml
model:
  provider: deepseek
  default: deepseek-v4-flash
  base_url: https://api.deepseek.com

auxiliary:
  compression:
    provider: main
  approval:
    provider: main
  extraction:
    provider: main
```

If Hermes’ current DeepSeek setup wizard writes a different shape, keep the wizard’s current schema and record it in `DECISIONS.md`.

### 8.3 Optional Pro model escalation

Preferred behavior:

- Configure both Flash and Pro if Hermes supports provider/model switching cleanly.
- Default every new session to Flash.
- Allow `/model deepseek:deepseek-v4-pro` or equivalent only for owner/admin.
- Log usage after Pro sessions.

If Hermes does not support a clean named “Flash/Pro” menu for DeepSeek, implement this as a documented manual switch rather than a custom hack.

### 8.4 Gateway platform config

Representative intent:

```yaml
gateway:
  message_timestamps:
    enabled: true
  platforms:
    telegram:
      extra:
        allow_from:
          - "123456789"
        allow_admin_from:
          - "123456789"
        user_allowed_commands:
          - help
          - whoami
          - status
    whatsapp:
      unauthorized_dm_behavior: ignore
```

Default:

- one owner/admin;
- no group access;
- no allow-all;
- unknown users ignored or pairing-disabled unless human chooses pairing.

### 8.5 Owner/admin-only commands

These commands are owner/admin-only:

- `/model`
- `/sethome`
- `/topic`
- `/usage`
- `/status`
- `/approve`
- `/deny`
- `/update`
- `/background`
- `/reload-mcp`
- `/rollback`

Regular chat is allowed only from the user’s allowlisted account(s).

### 8.6 Cron routing defaults

| Job type | Default delivery | Rationale |
|---|---|---|
| Morning personal briefing | WhatsApp | Natural daily access |
| Evening check-in | WhatsApp | Human-feeling daily habit |
| Deadline reminders | WhatsApp, optionally Telegram if urgent | User should see it |
| Weekly review | Telegram | Longer structured output |
| Usage/cost report | Telegram | Admin/control surface |
| Gateway health alert | Telegram, optionally all if critical | Telegram is safer fallback |
| WhatsApp broken/re-pair needed | Telegram | Fallback channel |

Use `all` only for genuinely urgent owner-only alerts. Do not spam both platforms by default.

---

## 9. Phased implementation plan

Every phase ends with a checkpoint. Do not chain phases without the human’s explicit go-ahead.

### Phase 0 — Pre-flight and current-doc verification

Tasks:

- Read this PRD fully.
- Read official docs from Section 6.
- Record checked links and key findings in `DECISIONS.md`.
- Confirm host target:
  - Oracle Always Free ARM; or
  - owned hardware.
- Confirm the user has:
  - DeepSeek API key;
  - dedicated WhatsApp bot number;
  - Telegram account for BotFather setup.

Acceptance:

- `DECISIONS.md` contains doc links and verified command/config facts.
- Host choice is documented.
- No secrets are requested in chat logs.

Checkpoint:

- Report verified facts and proposed next phase.
- Wait.

### Phase 1 — Project guardrails

Tasks:

- Initialize project repository if not already initialized.
- Create `AGENTS.md`.
- Create `PROGRESS.md`.
- Create `DECISIONS.md`.
- If using OpenCode, create `opencode.json`.
- If using Codex, document the user-approved config posture in `DECISIONS.md`.
- Add `.gitignore` entries for:
  - `.env`
  - `*.key`
  - `*.pem`
  - `auth.json`
  - `session/`
  - `.hermes/`
  - logs containing secrets.

Acceptance:

- Build-time HITL is documented and enforced as much as the selected agent supports.
- No secret-bearing files are tracked.

Checkpoint:

- Show the guardrail files.
- Wait.

### Phase 2 — Install Hermes Agent

Tasks:

- **Pin version**: Use Hermes Agent v0.17.0 (tag: v2026.6.19). Verify the installed version with `hermes --version`. If the install script pulls a newer version, downgrade to the pinned tag before proceeding.
- Use the official install method for the host OS.
- For Linux/macOS/WSL, current docs show:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

- For Windows native, current docs show a PowerShell installer. Verify before use.
- Confirm `hermes` CLI is available.
- Confirm `~/.hermes/` exists.

Acceptance:

- `hermes --help` or equivalent works.
- No provider secrets configured yet unless the user is ready.

Checkpoint:

- Report install result.
- Wait.

### Phase 3 — Configure DeepSeek V4

Tasks:

- Add `DEEPSEEK_API_KEY` through Hermes’ recommended secret mechanism.
- Configure DeepSeek provider through `hermes model` or current setup wizard.
- Default model: `deepseek-v4-flash`.
- Optional model: `deepseek-v4-pro`.
- Base URL: `https://api.deepseek.com`, unless the current Hermes wizard requires another exact value.
- Ensure auxiliary tasks route to the main DeepSeek provider by default.
- Do not configure non-DeepSeek paid fallbacks.

Acceptance:

- Terminal Hermes chat responds using Flash.
- `/usage` or logs expose token usage.
- Pro is either configured as owner/admin-only or documented as manual escalation.
- Legacy model aliases are not used.

Checkpoint:

- Show a short sanitized transcript and token/cost estimate.
- Wait.

### Phase 4 — Connect Telegram

Tasks:

- Human creates a bot with BotFather.
- Human provides the bot token through `~/.hermes/.env`, not chat.
- Set `TELEGRAM_ALLOWED_USERS` to the user’s Telegram numeric user ID.
- Set owner/admin access for the same user.
- Configure `/sethome` or `TELEGRAM_HOME_CHANNEL` as required by current Hermes docs.
- Disable group access by default.
- If groups are tested, only test with an allowlisted private test group and explicit approval.
- Optionally enable Telegram rich messages only if copy/paste behavior remains acceptable.

Acceptance:

- User can DM Hermes on Telegram.
- Non-allowlisted Telegram user is denied/ignored.
- Owner/admin-only commands work for the user.
- `/usage`, `/status`, `/model`, `/approve`, `/deny` are available only to owner/admin where supported.

Checkpoint:

- Report bot status and access-control test.
- Wait.

### Phase 5 — Connect WhatsApp

Tasks:

- Use dedicated bot number mode, not the user’s personal WhatsApp, unless the human explicitly chooses self-chat for testing.
- Ensure Node.js v18+ is available; v22 recommended if current Hermes docs prefer it.
- Run current Hermes WhatsApp setup, currently documented as:

```bash
hermes whatsapp
```

- Human scans QR from the dedicated bot phone.
- Configure:

```bash
WHATSAPP_ENABLED=true
WHATSAPP_MODE=bot
WHATSAPP_ALLOWED_USERS=60123456789
```

- Protect WhatsApp session files.
- Do not enable groups.
- Do not set `WHATSAPP_ALLOWED_USERS=*`.

Acceptance:

- User can message Hermes on WhatsApp.
- Non-allowlisted sender is ignored/denied.
- Hermes replies through DeepSeek Flash.
- WhatsApp session survives gateway restart.

Checkpoint:

- Report access-control test and session protection status.
- Wait.

### Phase 6 — Always-on gateway and service management

Tasks:

- Install Hermes gateway as a service.
- Prefer user service + lingering on headless Linux if current Hermes docs recommend it.
- Avoid root/system service unless human approves.
- Configure gateway restart behavior.
- Configure log rotation.
- Redact partial phone numbers and tokens where possible.
- Configure startup after reboot.
- Add health report cron to Telegram.

Acceptance:

- Gateway starts after reboot.
- Telegram and WhatsApp both reconnect.
- Logs are accessible and do not expose secrets.
- Crash simulation recovers.

Checkpoint:

- Report service status and recovery proof.
- Wait.

### Phase 7 — Persona, memory, and same-brain behavior

Tasks:

- Create `SOUL.md`.
- Create/seed `USER.md`.
- Define memory policy.
- Configure Hermes memory/session behavior per current docs.
- Add explicit “same brain, many faces” rule:
  - durable memory is shared;
  - active platform sessions can remain separate;
  - platform switch should use memory/session search to restore context.

Acceptance:

- Teach Hermes a fact on WhatsApp.
- Reset or switch context.
- Ask on Telegram.
- Hermes recalls the durable fact correctly.
- Hermes does not confuse two unrelated live threads.

Checkpoint:

- Show a sanitized same-brain test transcript.
- Wait.

### Phase 8 — Proactive cron layer

Tasks:

- Configure timezone to `Asia/Kuala_Lumpur` unless the user chooses otherwise.
- Create cron jobs:
  - morning briefing;
  - evening check-in;
  - deadline follow-up;
  - habit/goal nudge;
  - weekly review;
  - usage/cost report;
  - gateway health report.
- Deliver personal nudges mostly to WhatsApp.
- Deliver admin/ops reports mostly to Telegram.
- Use `all` only for urgent owner-only alerts.
- Add quiet hours.
- Add daily proactive-message cap.
- Add “stop/later/snooze” behavior.

Acceptance:

- A test cron sends to WhatsApp.
- A test cron sends to Telegram.
- A test urgent route can deliver to `all`.
- Quiet-hours rule suppresses or reschedules.
- No duplicate spam.

Checkpoint:

- Show cron list and test output.
- Wait.

### Phase 9 — Capability skills

Add only free capabilities in v1:

- reminders/tasks;
- daily/weekly briefings;
- habit and goal tracking;
- “remember this” durable memory command/pattern;
- web lookup using free/self-host fallback only (best-effort; quality varies; paid options require explicit approval);
- voice note handling where Hermes/platform supports it;
- draft-and-confirm outbound messaging;
- background research tasks;
- usage/cost checks.

Do not enable paid Tool Gateway services.

Acceptance:

- At least three practical capabilities work end-to-end across messaging.
- Any capability that would cost money is documented as optional, disabled by default.

Checkpoint:

- Demo capabilities.
- Wait.

### Phase 10 — Hardening and handover

Tasks:

- Review allowlists.
- Review admin-only commands.
- Review `.gitignore`.
- Review secret storage.
- Review logs for leaks.
- Review cron spam controls.
- Review DeepSeek usage/budget controls.
- Write `RUNBOOK.md`.
- Document backup/restore.
- Document re-pairing WhatsApp.
- Document rotating Telegram and DeepSeek keys.
- Document model switching.

Acceptance:

- Full test plan passes.
- Runbook is sufficient for a non-expert.
- No non-DeepSeek paid service is active.

Checkpoint:

- Final handover report.
- Done.

---

## 10. Humanized assistant design

### 10.1 `SOUL.md` requirements

Hermes should be:

- warm but not clingy;
- direct but not harsh;
- curious but not nosy;
- practical;
- lightly playful;
- able to speak Malay/English/rojak naturally;
- concise by default on WhatsApp;
- more structured on Telegram when doing admin/review work;
- comfortable asking questions first when the user’s intent is unclear;
- honest about uncertainty;
- respectful of quiet hours.

Example tone:

- “Pagi. Quick one — today ada 3 benda yang likely need attention.”
- “Aku can help draft, but sending to another person needs your confirmation dulu.”
- “This feels like a Pro-model task. Nak I switch to DeepSeek Pro for this run, or keep Flash?”
- “Noted. Aku’ll remember this as durable preference, not just chat context.”

### 10.2 Memory policy

Remember:

- stable user preferences;
- corrections;
- goals;
- habits;
- deadlines;
- recurring commitments;
- important people/projects;
- health/productivity patterns the user explicitly shares;
- decisions made;
- “remember this” instructions.

Do not remember by default:

- random jokes;
- sensitive secrets;
- one-off complaints unless the user asks;
- private third-party details that are not useful;
- raw documents unless intentionally stored.

Ask before storing:

- medical details;
- financial account details;
- legal matters;
- identity documents;
- passwords/API keys;
- sensitive relationship information.

### 10.3 Proactive behavior rules

Hermes can message first, but must not become annoying.

Default rules:

- quiet hours: 23:00–07:00 Malaysia time;
- max proactive non-urgent pings: 3/day;
- max friendly/random check-ins: 2/week;
- do not repeat the same nudge twice in a row;
- if the user says “stop”, stop that category;
- if the user says “later”, ask or infer a snooze time;
- if the user ignores several nudges, back off;
- urgent alerts can bypass quiet hours only if the user configured them.

### 10.4 Proactive cron playbook

| Schedule | Destination | Prompt intent |
|---|---|---|
| 07:00 daily | WhatsApp | Short personal morning briefing: today’s commitments, reminders, one useful nudge |
| 21:00 daily | WhatsApp | Evening check-in: wins, unfinished loops, what to carry tomorrow |
| Day before deadline | WhatsApp | Confirm deadline status and ask if user wants help |
| Mon/Wed/Fri evening | WhatsApp | Habit/goal check-in |
| Weekly Sunday | Telegram | Structured weekly review with open loops and suggested next week priorities |
| Daily admin | Telegram | Usage/cost/gateway health summary |
| Critical failure | Telegram or all | Alert if WhatsApp disconnected, DeepSeek 402/429, gateway restart loop |

---

## 11. Capabilities backlog

### 11.1 v1 must-have

- Cross-platform chat through WhatsApp and Telegram.
- Same durable memory across both.
- DeepSeek Flash default.
- Owner-controlled Pro escalation.
- Proactive cron messages.
- Reminder/task capture.
- Habit/goal logging.
- Draft-and-confirm for external messages.
- Runtime approval flow.
- Free web lookup (best-effort only; free-tier APIs are rate-limited and quality varies; paid options require explicit human approval).
- Gateway health and usage reports.

### 11.2 v1 nice-to-have

- Telegram topics for separate workspaces.
- Voice note transcription if free and supported by Hermes/platform config.
- Weekly “open loops” report.
- Project-specific memory sections.
- User-defined “do not disturb” profiles.
- Natural-language snooze/reschedule.

### 11.3 Roadmap

- Calendar integration, only with explicit approval.
- Notes app integration, only with explicit approval.
- Email draft integration, draft-only by default.
- Home Assistant integration, approval-gated.
- GitHub/project assistant skills.
- Official WhatsApp Cloud API migration if ban risk becomes unacceptable.

---

## 12. Hosting playbook

### 12.1 Recommended: Oracle Cloud Always Free ARM

Use:

- Ubuntu image;
- 1 VM with up to 2 OCPU / 12 GB RAM;
- default 50 GB boot volume or adjusted within Always Free limits;
- SSH key auth;
- minimal open ports;
- no public web UI unless needed;
- Tailscale or equivalent free private networking if desired.

Important:

- Always Free resources must be created in the home region.
- Capacity can be unavailable; retry or choose another availability domain if possible.
- Idle instances can be reclaimed, so keep legitimate gateway activity and monitoring.
- Credit/debit card is required for identity verification.
- Avoid paid resources outside Always Free limits.

### 12.2 Alternative: owned hardware

An old laptop, mini-PC, or Raspberry Pi can run Hermes if it is stable and always on.

Pros:

- no cloud signup friction;
- no capacity issues;
- no cloud billing risk.

Cons:

- power/internet reliability depends on home setup;
- harder remote recovery;
- needs local backup discipline.

### 12.3 Not recommended for v1

- tiny 1 GB free VMs;
- Android/Termux for WhatsApp bridge;
- free tiers that sleep aggressively;
- paid VPS unless the human explicitly chooses reliability over the zero-cost constraint.

---

## 13. Security and operations

### 13.1 Secrets

Treat these as highly sensitive:

- DeepSeek API key;
- Telegram bot token;
- WhatsApp session folder;
- Hermes auth files;
- `.env`;
- private backups;
- SSH keys.

Rules:

- never commit;
- never print full values;
- never send to the model except as required for direct API operation;
- redact in logs;
- rotate if exposed.

### 13.2 Access control

Default:

- allowlist user’s WhatsApp number;
- allowlist user’s Telegram ID;
- owner/admin is only the user;
- no groups;
- no allow-all;
- pairing disabled or manual unless chosen.

### 13.3 Platform risk

WhatsApp via Baileys is unofficial.

Hermes also supports the WhatsApp Business Cloud API as a fully supported alternative adapter. This is the official Meta-supported path with no account ban risk, but requires a Meta Business account and a public webhook URL. It can run in parallel with the Baileys bridge. This is the primary upgrade path if Baileys ban risk becomes unacceptable during v1 operation.

Mitigations:

- dedicated bot number;
- no bulk sends;
- no group auto-replies;
- limited proactive rate;
- re-pair runbook;
- Telegram fallback.

Telegram is safer operationally because it uses the official Bot API.

### 13.4 Runtime command/tool risk

Hermes has powerful tools and platform-specific toolsets. Keep dangerous operations approval-gated.

Minimum runtime policy:

- terminal commands requiring side effects need approval;
- file deletion needs approval;
- outbound third-party communication needs approval;
- public posts need approval;
- purchases need approval;
- model escalation to Pro should be owner/admin-only.

### 13.5 Logs and backups

Logs:

- rotate;
- redact;
- avoid message dumps unless needed for debugging;
- never include full secrets.

Backups:

- back up memory, skills, config, and runbook;
- treat WhatsApp session backups as sensitive;
- store privately;
- document restore process.

---

## 14. Testing and acceptance

The build is accepted only when all relevant tests pass.

### 14.1 Model tests

- Flash replies coherently.
- Usage is visible.
- Pro can be selected only by owner/admin or remains manual.
- No deprecated model aliases are configured.

### 14.2 Telegram tests

- User can DM Hermes.
- Non-allowlisted user cannot use Hermes.
- Owner/admin commands work for the user.
- Group access is disabled by default.
- `/usage`, `/status`, `/model`, `/approve`, `/deny` behavior is documented.

### 14.3 WhatsApp tests

- User can message Hermes from allowlisted number.
- Non-allowlisted number is ignored/denied.
- Dedicated bot number is used.
- Session survives gateway restart.
- No groups enabled.

### 14.4 Same-brain tests

- Teach durable fact on WhatsApp.
- Recall it on Telegram.
- Teach durable fact on Telegram.
- Recall it on WhatsApp.
- Confirm unrelated live platform threads do not become merged/confusing.

### 14.5 Proactive tests

- Cron sends test job to WhatsApp.
- Cron sends test job to Telegram.
- Cron can route urgent test to `all`.
- Quiet-hours behavior works.
- Daily cap/backoff works.

### 14.6 Runtime HITL tests

Hermes must ask before simulated:

- “send this message to my boss”;
- “delete this file”;
- “post this publicly”;
- “switch to paid non-DeepSeek provider”;
- “enable group replies”.

### 14.7 Ops tests

- Gateway starts after reboot.
- Gateway recovers after process kill.
- Logs do not expose secrets.
- `.gitignore` protects secret/session files.
- Runbook covers restart, re-pair, token rotation, model switch, and backups.

### 14.8 Cost tests

- No non-DeepSeek paid services enabled.
- DeepSeek spend can be viewed.
- Budget alert exists.
- Cron/background loops have limits.

---

## 15. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| WhatsApp bot number banned | Medium | Medium | Dedicated number, no bulk, allowlist, Telegram fallback |
| Oracle capacity unavailable | Medium | Low/Medium | Retry, choose another AD/region if possible, use owned hardware |
| DeepSeek credits run out | Medium | Medium | Usage reports, budget alerts, graceful alert on 402 |
| Agent sends annoying proactive pings | Medium | Low/Medium | Quiet hours, caps, backoff, stop/later commands |
| Secrets leak into logs/git | Low | High | `.gitignore`, redaction, no printing secrets |
| Coding agent performs risky action | Low | High | Config-enforced HITL + AGENTS.md + phase checkpoints |
| Runtime Hermes takes risky action | Low | High | Approval classifier + draft-confirm-act |
| Telegram bot token leaked | Low | High | Rotate token through BotFather, never commit `.env` |
| DeepSeek model aliases deprecated | Known | Low | Use direct V4 model IDs |
| Gateway/service instability | Medium | Medium | Auto-restart, health cron, logs, runbook |
| DeepSeek API outage/rate-limit/degraded | Medium | High | Graceful degrade: user-visible "[Hermes is temporarily unavailable]" reply. Retry with exponential backoff. Telegram alert if outage exceeds 5 min. Cron jobs queue during outage. No silent failures. |

---

## 16. Deliverables

Final build should produce:

- configured Hermes Agent installation;
- WhatsApp bot connection;
- Telegram bot connection;
- DeepSeek Flash default model;
- optional DeepSeek Pro escalation path;
- `SOUL.md`;
- `USER.md`;
- memory policy;
- cron jobs;
- `AGENTS.md`;
- `opencode.json` if using OpenCode;
- `.gitignore`;
- `PROGRESS.md`;
- `DECISIONS.md`;
- `RUNBOOK.md`;
- tested gateway service;
- final acceptance report.

---

## 17. Glossary

- **Hermes Agent** — the open-source Nous Research self-improving AI agent used as the core.
- **Gateway** — Hermes’ long-running background process that connects messaging platforms and runs cron.
- **Same brain** — shared durable memory, persona, skills, and policy across platforms.
- **Face** — a platform interface such as WhatsApp or Telegram.
- **Baileys** — open-source WhatsApp Web protocol library used by the Hermes WhatsApp bridge.
- **BotFather** — Telegram’s official bot creation/configuration bot.
- **DeepSeek V4 Flash** — default low-cost model.
- **DeepSeek V4 Pro** — optional higher-capability DeepSeek model.
- **HITL** — Human-in-the-Loop; explicit human approval before risky action.
- **Cron** — Hermes scheduled task system for proactive messaging.
- **SOUL.md** — persona/voice file.
- **USER.md** — durable user profile.

---

## Appendix A — Quick command sketch

Verify every command against current official docs before running.

```bash
# Install Hermes
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Configure model/provider interactively
hermes model
# Choose DeepSeek
# Enter API key through the secure prompt
# Base URL: https://api.deepseek.com
# Default model: deepseek-v4-flash

# Configure messaging platforms interactively
hermes gateway setup

# Telegram may require:
# - BotFather token in ~/.hermes/.env
# - TELEGRAM_ALLOWED_USERS=<numeric_user_id>
# - /sethome from the desired Telegram chat

# WhatsApp current docs show:
hermes whatsapp
# Human scans QR using dedicated bot number
# Then set WHATSAPP_ALLOWED_USERS=<phone_number_with_country_code_no_plus>

# Run gateway
hermes gateway

# Install gateway service
hermes gateway install

# Inspect cron
hermes cron list
hermes cron status
```

---

## Appendix B — Source checklist

The implementer must confirm these before build:

- [ ] Hermes install command is current.
- [ ] Hermes DeepSeek provider setup is current.
- [ ] DeepSeek model names and pricing are current.
- [ ] Telegram setup variables and allowlist schema are current.
- [ ] WhatsApp setup command and allowlist schema are current.
- [ ] Cron delivery target syntax is current.
- [ ] Gateway service installation behavior is current for the host OS.
- [ ] OpenCode/Codex permission config syntax is current.
- [ ] Oracle Always Free limits are current.

---

*End of PRD. Build carefully, keep DeepSeek as the only paid component, and make Hermes feel like one capable assistant living naturally across WhatsApp and Telegram.*
