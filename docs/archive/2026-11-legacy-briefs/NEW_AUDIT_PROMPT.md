# Audit Session Prompt — Hermes Agent (MarryJane / MJ)

> Copy this entire prompt into a **new OpenCode session**.
> No template, no checklist — just context and freedom to explore.

---

## Context

I have a personal AI assistant called **Hermes Agent (MarryJane / MJ)** built on NousResearch's Hermes Agent v0.17.0. It runs in WSL2 on Windows 11, connects Telegram + WhatsApp, and uses OpenCode Zen (free) + OpenCode Go (subscription) + NVIDIA (free) + DeepSeek for models.

You can read the full system snapshot in `AUDIT.md` and the build history in `PROGRESS.md`.

I also have **6 AI audit reports** saved in the repo under `audits/`. These were done by various AIs (Zhipu, Qwen, Sakana, Claude — still pending). Some followed a structured template I gave, some were free-form exploration.

## My Ask

**I don't want you to follow any template or checklist.** Just read everything and explore naturally. Here's what I care about:

- **What did the other audits find that actually matters?** (cross-reference all 6 reports, find consensus and divergence)
- **What did they miss?** (things that aren't in any audit but you notice from reading the system files)
- **What is genuinely fragile, over-engineered, or risky?**
- **What is missing that would make a real difference?**
- **What enhancements would improve the system meaningfully?** (not just cosmetic)
- **Which audit findings are signal vs noise?** (call out template-driven findings that aren't relevant)

## Specific Things I Want Investigated

These are things I encountered during development that I want a fresh pair of eyes on:

1. **`gateway_state.json` stale-state bug** — when gateway gets SIGTERM, the state file persists "running" and blocks restart. Is this a Hermes bug, our config problem, or expected behavior?

2. **Why "Mixture of Agents (MoA)" keeps appearing in /model picker** — I tried removing it from `_PROVIDER_MODELS` and `CANONICAL_PROVIDERS` in `hermes_cli/models.py` and restarted the gateway, but it's still there. Investigate why (pyc caching? auto-extend? gateway model cache?).

3. **OpenCode Go integration** — I added it as a provider (already natively supported in v0.17.0), updated model list, added skip-live-fetch. Does the integration look correct? Any gaps?

4. **Current OpenCode Go model list** — I manually curated 13 models from the official docs. Is this list still accurate? Should any be added/removed?

5. **Config migration v30→v31** — `hermes doctor --fix` migrated config. What changed? Any regressions?

6. **`fix-models.sh` strategy** — I have a script that restores model overrides after `hermes update`. Is this approach robust? Is there a better way?

## Output I Want

Don't structure this as a rigid report. Just tell me, in whatever order makes sense to you:

1. What you agree with from the other audits (and what you disagree with)
2. What the real priority items are (critical vs nice-to-have, in your own judgment)
3. Specific things I should fix, change, or investigate
4. A health score out of 10, and why

Be honest. If the system is solid in some areas, say so. If it's a mess in others, say that too. No sugar-coating.

---

## Files to Read

### System docs (for context)
- `AUDIT.md` — full system snapshot
- `PROGRESS.md` — build history across 16 phases
- `README.md` — overview
- `DECISIONS.md` — key decisions made

### Audit reports (cross-reference these)
- `audits/zhipu1-audit.md` — Zhipu structured audit
- `audits/zhipu2-audit.md` — Zhipu deep audit (biggest file, 88 KB)
- `audits/zhipu-exploration-audit.md` — Zhipu free-form exploration
- `audits/qwen-audit.md` — Qwen structured audit
- `audits/qwen-exploration.md` — Qwen free-form exploration
- `audits/sakana-audit.md` — Sakana audit

### Source files (if needed for investigation)
- `patches/2026-06-27_gemini-removal-model-overrides.patch`
- `../.hermes/hermes-agent/hermes_cli/models.py` — model config and provider setup
- `../.hermes/hermes-agent/hermes_cli/auth.py` — provider registry
- `../.hermes/scripts/fix-models.sh` — post-update model restoration script

---

Start when ready. No rush — explore thoroughly.
