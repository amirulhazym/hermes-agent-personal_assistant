```markdown
# Hermes Agent (MarryJane) — Deep Audit Report

> **Auditor:** Zhipu-1 (Zhipu Chat)
> **Date:** 28 June 2026
> **Method:** Manual review of `AUDIT.md` + `CLAUDE_AUDIT_PROMPT.md` + web validation
> **Scope:** Architecture, security, reliability, cost, operations, vision alignment

---

## 0. Audit Methodology & Limitations

### What was reviewed
- `CLAUDE_AUDIT_PROMPT.md` (10 dimensions)
- `AUDIT.md` (system snapshot, 191 lines)
- Web validation of: baileys vulnerability status, Hermes Agent features, WSL2 backup patterns, OpenCode Zen free tier terms, AI side-income landscape

### What was NOT reviewed (blind spots)
- `~/.hermes/config.yaml` (actual config)
- `SOUL.md` (persona definition)
- `hermes cron list` output (actual job definitions)
- Live logs (`gateway.log`, `errors.log`, `watchdog.log`)
- `watchdog.sh`, `gateway-start.ps1`, `fix-models.sh` source code
- `MEMORY.md`, `USER.md` content
- `RUNBOOK.md`, `DECISIONS.md` content
- `npm ls` / `pip list` dependency tree

### Recommended next round artifacts to share
1. `config.yaml` (sanitize API keys)
2. `SOUL.md` full content
3. `hermes cron list` output (sanitize drug names)
4. Last 200 lines of `gateway.log` + `errors.log`
5. `watchdog.sh` + `gateway-start.ps1` content
6. `fix-models.sh` + patch file content
7. `MEMORY.md` + `USER.md`
8. `hermes doctor` full output
9. `RUNBOOK.md` + `DECISIONS.md`
10. `npm ls` + `pip list` output

---

## 1. Executive Summary

In 5 days across 16 phases, you've built a dual-platform (Telegram + WhatsApp) AI assistant with cron system (27 jobs), medication reminders, computer-use, web search/extract, STT/TTS — all on free tiers, documented with rare discipline. Your documentation maturity (PRD, RUNBOOK, DECISIONS, PROGRESS, AGENTS, AUDIT) is your biggest asset and exactly what makes this productizable later.

However, there are critical gaps: **baileys vulnerability actually HAS a fix upstream** (your AUDIT.md incorrectly states "no upstream fix"), **API keys were exposed in plaintext and not yet rotated**, **no backup for WSL2 VHDX**, and **gateway_state.json bug + no remote restart** means if the assistant goes down while you're away, it stays down until you return. For single-user personal use, some of these are tolerable; for "future business/services" vision, all must be fixed before any client onboarding.

Architecture is fundamentally sound — dual-platform + Hermes + free-tier routing is exactly the pattern Hermes was designed for. The problem isn't design, it's operational resilience & security hygiene.

---

## 2. Critical Issues (Fix Today)

### C1. Baileys Vulnerability HAS Fix — AUDIT.md is Outdated

| Field | Detail |
|---|---|
| **Issue** | AUDIT.md states "1 critical (baileys) has no fix upstream". This is **incorrect**. |
| **Vulnerability** | CVE-2026-48063 (CVSS 9.3) — Message upsert / hist sync spoofing + app state corruption |
| **Affected** | baileys < 6.7.22, and 7.0.0-rc.1 through 7.0.0-rc.11 |
| **Fixed in** | **baileys 6.7.22** (stable) and **7.0.0-rc.12+** |
| **Why it matters** | Allows attacker to inject fake `messages.upsert` events with fake message keys. For a health-critical bot delivering medication reminders, attacker could inject **fake medication reminders** or suppress real ones. This is a life-safety risk, not theoretical. |
| **Fix** | `npm install @whiskeysockets/baileys@6.7.22` (stable) or `@whiskeysockets/baileys@7.0.0-rc13` (latest). Then `npm audit` to verify 0 criticals. |
| **Priority** | **CRITICAL** |
| **References** | [GHSA-qvv5-jq5g-4cgg](https://github.com/WhiskeySockets/Baileys/security/advisories/GHSA-qvv5-jq5g-4cgg), [CVE-2026-48063](https://advisories.gitlab.com/npm/baileys/CVE-2026-48063) |

### C2. API Keys Not Rotated After Plaintext Exposure

| Field | Detail |
|---|---|
| **Issue** | AUDIT.md "Needs Review" section says keys "should be regenerated" — still in todo state, not done. |
| **Keys affected** | NVIDIA + OpenCode Zen (both exposed in conversation history) |
| **Why it matters** | Compromised keys = anyone with conversation logs or git history can use your free tier quota. If you later add paid balance, they burn your money. |
| **Fix** | (a) Login NVIDIA developer portal → revoke old key → generate new → update `.env`. (b) Same for OpenCode Zen. (c) `git log --all -p \| grep -i "key"` to verify no keys in git history. (d) Verify `.env` is in `.gitignore`. (e) Install `git-secrets` or `trufflehog` pre-commit hook. |
| **Priority** | **CRITICAL** |

### C3. No Backup for WSL2 VHDX / `~/.hermes/`

| Field | Detail |
|---|---|
| **Issue** | No automated backup for WSL2 disk or config. 49MB `state.db`, `MEMORY.md`, `SOUL.md`, cron definitions, `config.yaml`, `.env`, plugins — all in one VHDX that can corrupt. |
| **Why it matters** | WSL2 VHDX corruption = full rebuild. Estimated recovery: 4-8 hours (reinstall Hermes, reconfigure providers, rebuild cron from memory, re-pair WhatsApp). If `MEMORY.md` or `SOUL.md` lost, you lose 5 days of persona tuning. For business vision: client data loss = liability. |
| **Fix** | Windows Task Scheduler job (PowerShell) that runs weekly: `wsl --shutdown; wsl --export hermes-agent F:\backups\hermes-agent-$(Get-Date -Format yyyyMMdd).tar`. Keep last 4 snapshots. Plus daily robocopy of `~/.hermes/{config.yaml,SOUL.md,MEMORY.md,USER.md,cron/,scripts/,plugins/}` to `F:\backups\hermes-config-daily\`. |
| **Priority** | **CRITICAL** |
| **References** | [WSL backup patterns](https://github.com/microsoft/WSL/issues/8185), [WSL backup guide](https://wsl-ui.octasoft.co.uk/blog/backing-up-and-restoring-wsl-distributions) |

### C4. `gateway_state.json` Stale "running" Bug + No Remote Restart

| Field | Detail |
|---|---|
| **Issue** | After SIGTERM, file still says "running", blocks restart. Current fix: `rm ~/.hermes/gateway_state.json` — but requires PowerShell access. Zero mechanism to restart from phone. |
| **Why it matters** | Single point of failure with no remote recovery. If gateway crashes while you travel, assistant down until you return. Combined with C1 (baileys spoofing can corrupt state), this is an availability deadlock. |
| **Fix** | (a) Fix root cause: add `rm -f ~/.hermes/gateway_state.json` to gateway startup script (idempotent cleanup before start). (b) Add health endpoint: small Flask/FastAPI server on `localhost:8787` with `/restart`, `/status`, `/health` endpoints, secured with token allowlist. (c) Telegram bot command `/mj restart` that triggers endpoint with DM pairing + command allowlist (do NOT accept raw shell exec). (d) Alternative: Tailscale SSH to WSL2 from phone for emergency access. |
| **Priority** | **CRITICAL** |
| **References** | [OpenClaw Telegram integration patterns](https://clawtrust.ai/blog/openclaw-telegram-bot-setup), [Telegram bot setup](https://docs.openclaw.ai/channels/telegram) |

### C5. Real Medication Names Still in Cron System

| Field | Detail |
|---|---|
| **Issue** | Docs sanitized (Akurit-4 → Medication A), but cron system itself still stores "Akurit-4, Pyridoxine, Dexa, Letram" in `hermes cron list`. |
| **Why it matters** | Akurit-4 = rifampicin + isoniazid + pyrazinamide + ethambutol = **TB treatment**. This is sensitive health data. If you ever: share `hermes cron list` output in debugging, screenshot for tutorial, or onboard a client — data leaks. For business vision: GDPR/PDPA-class health data exposure. |
| **Fix** | Alias drug names in cron system itself, not just docs. Pattern: cron job name = "Medication A", job payload references local `medications.yaml` (gitignored) that maps "Medication A" → "Akurit-4" at delivery time. Cron system stores only aliases; real names live in one gitignored file. |
| **Priority** | **CRITICAL** for vision, **HIGH** for personal use |

---

## 3. High Priority Issues

### H1. No Fallback Provider

| Field | Detail |
|---|---|
| **Issue** | OpenCode Zen free tier = single point of failure. If they change terms, rate-limit aggressively, or outage — assistant goes blind. |
| **Why it matters** | Hermes natively supports OpenRouter (200+ models), NVIDIA NIM, NovitaAI, z.ai/GLM, etc. Not using fallback is unnecessary risk. |
| **Fix** | Add OpenRouter as secondary provider (free models available, $20 pay-as-you-go tier). Configure model fallback chain: OpenCode Zen → OpenRouter → (optional) direct DeepSeek API. |
| **Priority** | **HIGH** |
| **References** | [Hermes Agent providers](https://github.com/nousresearch/hermes-agent), [OpenCode Zen](https://opencode.ai/zen) |

### H2. Model Overrides Applied to Source Files — Fragile

| Field | Detail |
|---|---|
| **Issue** | `fix-models.sh` recovery approach survives `git pull` (no conflicts) but NOT `hermes update`. Manual recovery = human error waiting to happen. |
| **Why it matters** | Every `hermes update` = re-run `fix-models.sh` manually. If forgotten, model routing breaks silently. |
| **Fix** | Move overrides to config-only (check if Hermes v0.17 supports config-level model overrides — test `hermes config set models.*`). If not supported, automate: post-update git hook that auto-runs `fix-models.sh` + verifies with `hermes doctor`. Document the hook in RUNBOOK. |
| **Priority** | **HIGH** |

### H3. DeepSeek API Key Exists But Unused

| Field | Detail |
|---|---|
| **Issue** | You have DeepSeek API key but route through OpenCode Zen. Suboptimal cost + latency path. |
| **Why it matters** | Direct DeepSeek API = lower latency (no proxy hop), cheaper (no intermediary markup), more reliable (one less dependency). OpenCode Zen free tier is shared across all users and has usage limits. |
| **Fix** | Test direct DeepSeek API as primary for a week. Compare latency + reliability. If better, switch primary to DeepSeek, keep OpenCode Zen as fallback. Cost: DeepSeek V4 Flash ~$0.01-0.02/day for personal use — well under $5/month target. |
| **Priority** | **HIGH** |
| **References** | [OpenCode Zen limits](https://www.reddit.com/r/opencodeCLI/comments/1qcxore/what_are_the_limit_rates_for_the_free_models_on) |

### H4. cua-driver MCP Runs as Subprocess of Gateway

| Field | Detail |
|---|---|
| **Issue** | Coupling — gateway crash = computer-use dies. Restart gateway = restart cua-driver. |
| **Why it matters** | If you're doing long-running computer-use task (e.g., batch file processing), gateway restart kills it mid-task. |
| **Fix** | Option A — run cua-driver as separate process (PowerShell scheduled task at logon, auto-restart on crash). Option B — accept coupling but add `cua-driver` health check to watchdog. Option B is fine for personal use. |
| **Priority** | **HIGH** if you use computer-use often, **MEDIUM** otherwise |

### H5. Watchdog v2 — 5-min Blind Spot + Liveness vs Functional Health

| Field | Detail |
|---|---|
| **Issue** | 5-min polling = up to 5-min downtime window. Also: does watchdog check process liveness (PID exists) or functional health (can it actually send a Telegram message)? |
| **Why it matters** | Process alive ≠ functional. Gateway can hang (deadlock) with PID still running but no message delivery. Watchdog that only checks PID = false positive green. |
| **Fix** | (a) Reduce to 2-min polling (cheap). (b) Add functional health check: watchdog sends test message to private "self-test" Telegram chat, verifies delivery within 30s. (c) Log watchdog results to `watchdog.log` with structured JSON for trend analysis. |
| **Priority** | **HIGH** |

### H6. Node.js/npm Not on PATH

| Field | Detail |
|---|---|
| **Issue** | WhatsApp bridge uses `~/.hermes/node/bin/node` via venv entry point. Maintenance friction. |
| **Why it matters** | Future you (or client onboarding) will struggle with "node: command not found" confusion. Also `npm audit` requires PATH. |
| **Fix** | `echo 'export PATH="$HOME/.hermes/node/bin:$PATH"' >> ~/.bashrc` — 30 seconds. |
| **Priority** | **HIGH** (quick win) |

### H7. Docs-Only Git Repo with Single Patch File — Patch Drift

| Field | Detail |
|---|---|
| **Issue** | `patches/2026-06-27_gemini-removal-model-overrides.patch` is single source of truth for source modifications. If upstream evolves and patch no longer applies cleanly, silent breakage. |
| **Why it matters** | Patches rot. 3 months from now, you won't remember context. |
| **Fix** | (a) Move to a fork of hermes-agent in your GitHub (private), apply overrides as commits, `git rebase` on upstream. (b) Or: keep patch but add CI test that verifies patch applies cleanly against latest upstream weekly. (c) Document override rationale in DECISIONS.md ADR format. |
| **Priority** | **HIGH** |

---

## 4. Medium Priority Issues

| # | Issue | Why It Matters | Fix | Priority |
|---|---|---|---|---|
| M1 | 27 cron jobs (20 medication) — hardcoded | Maintenance nightmare, hard to adjust schedule, drug-name exposure surface | Single scheduler cron job that reads `medications.yaml` + `schedule.yaml`, generates reminders dynamically | MEDIUM |
| M2 | `state.db` 50MB in 5 days (86 sessions) | Growth rate ~10MB/day → ~3.6GB/year. WAL/SHM bloat | Add weekly `VACUUM` + enforce 90-day retention. Monitor `PRAGMA wal_checkpoint` | MEDIUM |
| M3 | MEMORY.md 2501 + USER.md 1300 chars | Within Hermes design bounds (~3600 chars / ~1300 tokens intentional) but may feel shallow | Consider external memory provider (Mem0, Hindsight, Holographic) for richer recall if personalization feels shallow. Built-in stays as core. | MEDIUM |
| M4 | Obsidian vault connected but not integrated | Big missed synergy — PARA vault is your knowledge base | Hermes plugin/script that reads daily notes, writes MJ summaries to Obsidian, uses vault as RAG source for personal context | MEDIUM |
| M5 | Log rotation — verify gateway.log actually rotates | 4.7MB in 5 days = ~340MB/year if no rotation | Verify `logrotate` config triggers, add size-based rotation (10MB), keep 7 archives | MEDIUM |
| M6 | Prompt caching 5min TTL — unverified effectiveness | If hit rate low, caching is wasted complexity | Add logging: cache hit/miss ratio. If <30%, increase TTL or restructure prompts to be more prefix-stable | MEDIUM |
| M7 | STT faster-whisper base model — Malay/rojak accuracy | Base model weak on Malay + code-switching | Test `medium` model (still local, free) with `language="ms"` hint. Or whisper.cpp for better CPU efficiency | MEDIUM |
| M8 | trafilatura fails on JS-heavy sites | Silent failure on SPAs (React/Vue sites) | Add fallback: detect empty extraction → fallback to Playwright headless render → re-extract | MEDIUM |
| M9 | `__editable__.hermes_agent-0.17.0.pth` — `import tools` works but `import hermes_agent` doesn't | Confusing for future debugging | Document in RUNBOOK. Not a bug, just editable install behavior | MEDIUM (doc only) |

---

## 5. Low Priority / Nice-to-Have

| # | Issue | Fix | Priority |
|---|---|---|---|
| L1 | Add `hermes doctor` to weekly cron (Sunday 06:00, before Log Rotate) | 1 line in crontab | LOW |
| L2 | `gateway_state.json` PID exposure — low sensitivity, acceptable for single-user | Ensure file is `chmod 600` and not in any git-tracked path | LOW |
| L3 | edge-tts (en-US-AriaNeural) — adequate for personal use | Consider `ms-MY-OsmanNeural` for Malay voice consistency if you rojak heavy | LOW |
| L4 | DDGS rate limits — monitor | If hit, add 1-second delay between searches or cache results | LOW |
| L5 | Config v31 — review `hermes config diff v30 v31` changelog | Check for new features worth enabling (memory providers, skills hub enhancements) | LOW |

---

## 6. Quick Wins (<30 min each)

1. **Rotate NVIDIA + OpenCode Zen API keys** — delete old, generate new, update `.env`
2. **Upgrade baileys to 6.7.22+** — `npm install @whiskeysockets/baileys@6.7.22`
3. **Add `wsl --export` weekly backup** — Windows Task Scheduler, 5 lines PowerShell
4. **Add `rm -f ~/.hermes/gateway_state.json` to gateway-start.ps1** — kills stale-state bug at root
5. **Add npm to PATH** — `echo 'export PATH="$HOME/.hermes/node/bin:$PATH"' >> ~/.bashrc`
6. **Add `hermes doctor` to weekly cron** — 1 line
7. **Alias medication names in cron system** — rename 20 jobs to Medication A/B/C, move real names to gitignored `medications.yaml`
8. **Add OpenRouter as fallback provider** — signup, add key to `.env`, add to config fallback chain
9. **Verify `.env` in `.gitignore`** — `git check-ignore .env` should return the path

---

## 7. Long-Term Recommendations

1. **Migrate model overrides to fork + rebase workflow** — replace patch file with private GitHub fork, apply overrides as commits, weekly `git rebase upstream/main`
2. **Build gateway remote restart via Telegram** — secured endpoint + DM pairing + command allowlist
3. **Consolidate medication crons into config-driven scheduler** — single job reads `medications.yaml`, easier to maintain + sanitize
4. **Integrate Obsidian vault as Hermes knowledge source** — read PARA structure, write daily MJ summaries, use as RAG for personal context
5. **Adopt external memory provider** — Mem0 or Hindsight for structured fact extraction across sessions
6. **Build IaC reprovisioning script** — bash/Ansible playbook that rebuilds entire stack (WSL2 + Hermes + config + cron + plugins) in <1 hour from backup
7. **Structured telemetry** — JSON logs + simple Grafana dashboard (or just `jq` queries on logs) for observability
8. **Direct DeepSeek API migration** — measure for 2 weeks, switch if better
9. **Pre-commit secret scanning** — `trufflehog` or `git-secrets` hook to prevent future key leaks

---

## 8. Additional Audit Dimensions (Beyond AUDIT.md's 10)

### A. Agent Quality & Prompt Engineering

| Field | Detail |
|---|---|
| **Finding** | `SOUL.md` persona definition exists but not audited. `max_turns=60` may be too high (cost/latency) or too low (complex tasks). No hallucination guardrails visible. |
| **Recommendation** | Share `SOUL.md` for review. Test `max_turns=30` vs 60 for typical tasks. Add explicit "refuse if unsure" instruction in SOUL. |
| **Priority** | **HIGH** |

### B. Observability & Telemetry

| Field | Detail |
|---|---|
| **Finding** | Logs are text-based, no structured metrics, no tracing. Watchdog is binary (up/down). |
| **Recommendation** | Add JSON-structured logs (model used, tokens, latency, tool calls). Weekly `jq` summary report. Optional: OpenTelemetry export. |
| **Priority** | **MEDIUM** |

### C. Resilience & Self-Healing

| Field | Detail |
|---|---|
| **Finding** | No circuit breaker on provider calls. No graceful degradation (if vision model fails, does text-only fallback work?). No retry-with-backoff pattern. |
| **Recommendation** | Add provider-level circuit breaker (3 failures → skip 5 min). Test graceful degradation paths. Document fallback behavior in RUNBOOK. |
| **Priority** | **HIGH** |

### D. UX & Conversation Design

| Field | Detail |
|---|---|
| **Finding** | Multi-turn coherence untested. Quiet hours 23:00-07:00 + max 3 pings — but ping quality (is the ping useful or annoying?) unmeasured. Rojak language handling on STT/TTS untested. |
| **Recommendation** | Run 1-week "conversation diary" — rate each MJ interaction 1-5 for usefulness. Adjust SOUL + ping triggers based on data. |
| **Priority** | **MEDIUM** |

### E. Extensibility & Plugin Architecture

| Field | Detail |
|---|---|
| **Finding** | Custom trafilatura plugin loads from `~/.hermes/plugins/` — no isolation, no testing, no versioning. If plugin crashes, does gateway crash? |
| **Recommendation** | Add plugin-level try/except wrapping (if Hermes doesn't already). Write 1 unit test for trafilatura plugin. Pin plugin version. |
| **Priority** | **MEDIUM** |

### F. Knowledge Management & Memory Strategy

| Field | Detail |
|---|---|
| **Finding** | MEMORY.md 2501 + USER.md 1300 chars is within Hermes bounded design but may feel shallow for "deepening model of who you are" goal. No external memory provider. Obsidian vault not integrated. |
| **Recommendation** | Pilot Mem0 or Hindsight for 2 weeks. Compare recall quality. Built-in stays as core, external as enrichment. |
| **Priority** | **MEDIUM** |
| **References** | [Hermes Memory Providers](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers), [Agent Memory Providers Compared](https://www.glukhov.org/ai-systems/memory/agent-memory-providers) |

### G. Reproducibility & IaC

| Field | Detail |
|---|---|
| **Finding** | Manual setup across 16 phases. No provisioning script. If laptop dies, rebuild = 4-8 hours from memory + docs. |
| **Recommendation** | Write `provision.sh` that: installs Hermes, restores config from backup, restores cron, reinstalls plugins. Target: <1 hour rebuild from backup. |
| **Priority** | **HIGH** (critical for vision) |

### H. Documentation & Knowledge Transfer

| Field | Detail |
|---|---|
| **Finding** | RUNBOOK + DECISIONS exist but ADR (Architecture Decision Record) format unclear. Onboarding readiness untested. |
| **Recommendation** | Convert DECISIONS.md to formal ADR format (Context / Decision / Consequences). Have a friend try to follow RUNBOOK cold — note where they get stuck. |
| **Priority** | **HIGH** (critical for vision) |

### I. Legal & Compliance

| Field | Detail |
|---|---|
| **Finding** | WhatsApp ToS on automated messaging — baileys is unofficial library, account ban risk. Telegram bot ToS fine. Medication data = health data (PDPA Malaysia applies if you ever commercialize). Provider ToS (OpenCode Zen, NVIDIA) on personal vs commercial use. |
| **Recommendation** | Document ToS posture in DECISIONS.md. For commercialization: switch WhatsApp to official Business API, add PDPA-compliant data handling. Check OpenCode Zen ToS for commercial use. |
| **Priority** | **HIGH** (for vision) |

### J. Performance & Latency

| Field | Detail |
|---|---|
| **Finding** | No latency baselines measured. Cold start time unknown. Prompt caching effectiveness unverified. Model routing latency (OpenCode Zen proxy hop) unmeasured. |
| **Recommendation** | Add latency logging to gateway.log. Measure: cold start, warm response, vision request, web search round-trip. Set baselines. Optimize if >5s p95. |
| **Priority** | **MEDIUM** |

---

## 9. Vision Lens (Short-term Hype vs Long-term Gain)

Your vision has two horizons:
- **Short-term hype:** Demoable, portfolio, proof of competency, "wow" factor
- **Long-term gain:** Productizable, repeatable, deep expertise, sustained side income

### Quadrant Analysis

| Dimension | Short-term Hype | Long-term Gain | Quadrant |
|---|---|---|---|
| Reproducibility & IaC | High | High | **Sweet spot — do first** |
| Documentation & ADRs | High | High | **Sweet spot — do first** |
| Agent Quality & SOUL | High | High | **Sweet spot — do first** |
| Security & Compliance | Medium | High | **Foundations — compound later** |
| Memory Strategy | Medium | High | **Foundations — compound later** |
| Observability | Low | High | **Foundations — compound later** |
| Backup & DR | Low | High | **Foundations — compound later** |
| Computer-use demos | High | Low | **Hype plays — demo only** |
| Voice/TTS polish | High | Low | **Hype plays — demo only** |
| UI polish | Medium | Low | **Skip for now** |

### Vision-Reframed Priorities

- Critical issue C5 (medication names in cron) becomes **MORE urgent** — not just personal privacy, but PDPA liability if you onboard a client with health data
- Critical issue C3 (no backup) becomes **MORE urgent** — a service business cannot operate without DR
- Dimension G (Reproducibility/IaC) jumps to **top priority** — you cannot sell what you cannot reproduce
- Dimension H (Documentation/ADRs) jumps to **top priority** — services require handover
- Dimension I (Legal/Compliance) becomes **gating** for commercialization — WhatsApp baileys + medication data + paid clients = legal landmine

### Short-term Hype Plays (Genuinely Valuable for Portfolio)

1. Build a public "Hermes Agent setup guide" from your DECISIONS.md (sanitized) — content marketing + proof of expertise
2. Demo video: "5-day build of a $0/month personal AI assistant with medication reminders + computer-use" — short-form content
3. Open-source the `provision.sh` + `fix-models.sh` patterns (not your config) — GitHub credibility

### Long-term Gain Plays (Build Deep Expertise)

1. Become the "Hermes Agent specialist" in your region — niche expertise is monetizable (custom agent builds for local businesses, $500-1500 per agent)
2. Document a repeatable "personal AI assistant as a service" offering: setup + customization + maintenance retainer
3. Build a library of sanitized, reusable patterns (medication scheduler, Obsidian integration, multi-provider fallback) — these become your service modules

---

## 10. Final Verdict

| Aspect | Rating | Notes |
|---|---|---|
| **Overall system health** | **6.5/10** | Sound architecture, critical security/ops gaps |
| **Documentation discipline** | 9/10 | Rare strength, biggest asset for productization |
| **Architecture design** | 7.5/10 | Sound, Hermes-native |
| **Security hygiene** | 4/10 | Keys exposed, baileys unfixed, health data in cron |
| **Operational resilience** | 4/10 | No backup, no remote restart, 5-min blind spot |
| **Cost efficiency** | 9/10 | $0/month, smart free-tier routing |

### Biggest Risk
Combination of baileys spoofing (can inject fake medication reminders) + no WSL2 backup + no remote restart = a corrupted session or VHDX failure takes assistant down for hours with no recovery path, and an attacker could silently manipulate health-critical reminders.

### Biggest Strength
Documentation discipline — 16 phases with ADRs, RUNBOOK, DECISIONS, AUDIT prompt. This is exactly what 99% of personal projects lack, and it's the #1 asset for converting this into a sellable service later.

---

## 11. Recommended Next Steps

### Immediate (Today)
1. Rotate API keys (C2)
2. Upgrade baileys to 6.7.22+ (C1)
3. Add `wsl --export` weekly backup (C3)
4. Add `rm -f ~/.hermes/gateway_state.json` to gateway-start.ps1 (C4)

### This Week
5. Alias medication names in cron system (C5)
6. Add OpenRouter as fallback provider (H1)
7. Add npm to PATH (H6)
8. Add `hermes doctor` to weekly cron (L1)

### Next Round Audit Artifacts to Share
For deeper analysis on Agent Quality + Resilience dimensions, share:
- `SOUL.md` content
- `config.yaml` (sanitize API keys)
- `watchdog.sh` source
- `gateway-start.ps1` source
- `fix-models.sh` source
- `MEMORY.md` + `USER.md` content
- `RUNBOOK.md` + `DECISIONS.md` content
- `hermes doctor` full output
- Last 200 lines of `gateway.log` + `errors.log`

---

## 12. Discussion Prompts for AI Coding Agent

Use these prompts with your AI coding agent to discuss solutions:

1. **Baileys upgrade:** "Review the baileys 6.7.22 release notes. Are there any breaking changes we need to handle? What's our rollback plan if the upgrade breaks WhatsApp bridge?"

2. **Gateway remote restart:** "Design a secure Telegram-based restart mechanism. Requirements: DM pairing only, command allowlist (restart/status/health), no raw shell exec, token-based auth. What's the minimal Flask/FastAPI implementation?"

3. **Medication cron refactor:** "Design a config-driven medication scheduler. Input: `medications.yaml` (gitignored, maps aliases to real names + schedule). Output: single cron job that generates reminders dynamically. How do we migrate 20 hardcoded jobs to this pattern without losing history?"

4. **WSL2 backup automation:** "Write a PowerShell script for Windows Task Scheduler that: shuts down WSL, exports to tar, keeps last 4 snapshots, logs to `F:\backups\backup.log`. What's the optimal schedule (weekly? daily?)"

5. **Model override strategy:** "Evaluate: config-only overrides vs fork+rebase vs patch+CI test. Which is most maintainable for a solo developer who updates Hermes monthly? What's the implementation effort for each?"

6. **Reprovisioning script:** "Outline a `provision.sh` that rebuilds the entire stack from backup in <1 hour. What are the dependencies? What's the testing approach?"

7. **External memory provider pilot:** "Compare Mem0 vs Hindsight vs Holographic for Hermes Agent. Which is easiest to pilot for 2 weeks? What's the integration path? How do we measure if recall quality improves?"

8. **Observability upgrade:** "Design a structured logging schema for gateway.log. Fields: timestamp, level, model, tokens_in, tokens_out, latency_ms, tool_calls, cache_hit. How do we add this without breaking existing log parsers?"

9. **ADR migration:** "Convert DECISIONS.md to formal ADR format. Template: Context / Decision / Consequences / Status. How many ADRs should we have? What's the numbering scheme?"

10. **Commercialization path:** "Map the legal/compliance requirements for converting this personal assistant into a paid service. WhatsApp Business API migration, PDPA compliance, provider ToS review, data handling agreements. What's the critical path?"

---

*End of audit report. Share this file with your AI coding agent to begin solution discussion.*
```