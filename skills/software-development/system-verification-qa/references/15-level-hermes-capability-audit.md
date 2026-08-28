# 15-Level Hermes Capability Audit (YanXbt framework)

Audit procedure for answering "what level is our Hermes setup?" against the
YanXbt Substack article "15 Levels of Hermes Agent" (Jun 21 2026, verified vs
Hermes v0.17.0 docs). Proven 2026-08-09 on this VPS — all claims below were
re-verified live during that audit.

## Key manual

| Level | Name | Live evidence to collect |
|---|---|---|
| 1 | One-shot prompts | toolset list (`hermes tools list`) — tool-calling active |
| 2 | Memory + SOUL.md | `~/.hermes/SOUL.md` (lines/size), memory tool state |
| 3 | Slash commands | `display.busy_input_mode` in config; /background /steer /queue /model in v0.17 registry |
| 4 | Skills + model-per-task | `find ~/.hermes/skills -name SKILL.md | wc -l`; `auxiliary.*` in config (cheap models for vision/web_extract/compression = false) |
| 5 | MCPs | `hermes mcp list` — count + which |
| 6 | Sub-agents | `delegation.max_concurrent_children/depth`; grep agent.log for `platform=subagent` |
| 7 | Async ops | `hermes cron list` → Mode (no-agent = $0); `/goal` existence + usage count in logs; `checkpoints.enabled` |
| 8 | Multi-profile | `hermes profile list` |
| 9 | Knowledge base | `~/wiki` existence/SCHEMA.md; OBSIDIAN_VAULT_PATH in .env |
| 10 | Kanban | `hermes kanban list` (tasks), kanban skills installed, `kanban.dispatch_in_gateway` |
| 11 | Voice | `stt.enabled` + `tts.provider` in config |
| 12 | Browser | browser toolset flag in `hermes tools list` |
| 13 | API server | grep `API_SERVER_ENABLED` in .env |
| 14 | IDE/ACP | process check for `hermes acp` |
| 15 | Profile distributions | `hermes profile list` (dist columns), git packaging age |

## One-shot evidence batch (read-only, ~30s)

```bash
hermes --version
wc -l ~/.hermes/SOUL.md
hermes cron list 2>&1 | grep -E "Name:|Schedule:|Mode:|Deliver:"
hermes profile list
hermes mcp list
hermes tools list
hermes kanban list
grep -cE "goal_mode|GoalJudge|active goal" ~/.hermes/logs/agent.log
grep -E "platform=subagent" ~/.hermes/logs/agent.log | tail -3
grep -c "API_SERVER_ENABLED" ~/.hermes/.env
python3 -c "...yaml read config: model, delegation, compression.threshold, display.busy_input_mode, checkpoints.enabled, curator, budget, stt/tts, auxiliary provider/model map..."
```

## Token-economics checklist (article appendix)

- right model per task (aux config) ✅/❌
- wakeAgent gates (script-decides cron) ✅/❌
- no_agent mode jobs ✅/❌ (all-no-agent = $0 forever)
- pre-run scripts injected as context ✅/❌
- lean tool sets per cron ✅/❌
- tool_search enabled (`tools.tool_search: true`) ✅/❌
- compression.threshold (0.50 default; 0.40 for long /goal runs) — value
- curator: enabled + consolidate opt-in ✅/❌
- budget.daily_max_usd/session_max_usd/monthly_max_usd — **usually NOT set** → flag as top gap

## Verdict style

P1 🔴 gaps first (budget caps, checkpoints), then per-level ⚠️/✅/❌ lines, one
line each, then "our level = X–Y" with proof tags. Full .md via MEDIA; chat
gets condensed verdict.

## Verified state 2026-07-09 (VPS, default profile)

- v0.17.0, +13 local commits; SOUL.md 131 lines; memory ~98% full
- delegation concurrency 3, depth 1; busy_input_mode interrupt (auto-demoted
  to queue when subagents active — gateway log 2026-07-20)
- 6 cron jobs, ALL no-agent mode ($0) — medial conventions (chain_monitor 15min, med-compliance weekly, dexa taper daily, appointment reminder, log rotate, hello-watch 30s)
- 1 MCP (tavily); no API server; no ACP; no kanban tasks; 1 profile; /goal 0 usage
- wiki ~/wiki fully populated (SCHEMA.md, decisions/, runbooks/, raw/, obsidian-linked)
- auxiliary: vision=opencode-zen mimo-v2.5-free, web_extract/compression=deepseek-v4-flash, approval=deepseek
- budget caps NOT set; checkpoints.enabled False → flagged P1/P2
- verdict = Level 7–9

## Pitfall: extracting long Substack articles (web_extract truncation)

`web_extract` LLM-summarizes pages > ~5000 chars and caps at ~5000 — it CUT
the article mid-Level-4. Recovery:

```bash
curl -sL "<url>" -H "User-Agent: Mozilla/5.0 ..." -o /tmp/article.html
```

Then parse the `<div class="body markup">` region. DO NOT regex the first
`<div class="body markup">` occurrence naively — the Substack HTML contains
multiple nested divs with the same class; naive `re.search(...</div></div>)`
grabs only a stub (~6 chars). Robust: `start = raw.find('<div class="body markup">')`,
`end = raw.find('<div class="post-footer', start)` if present, else a generous
window; strip tags preserving h2/h3/li; unescape entities. Verify with a
character count before trusting the result (`len(text) > 20k` for a real 15-level article).

Pitfall: don't report a level from a truncated article — the LAST 10 levels
were missing in the first extract and would have silently produced a wrong audit.