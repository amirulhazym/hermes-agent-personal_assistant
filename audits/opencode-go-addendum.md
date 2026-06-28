# Audit Addendum — OpenCode Go Subscription (28 June 2026)

> Generated: 28 June 2026, after the cross-audit synthesis was delivered.
> Purpose: Correct the temporal scope gap in the six audit reports.

---

## Scope gap

All six audit reports (`zhipu1-audit.md`, `zhipu2-audit.md`, `zhipu-exploration-audit.md`, `qwen-audit.md`, `qwen-exploration.md`, `sakana-audit.md`) and `AUDIT.md` itself were written **before** the OpenCode Go subscription was integrated into the system.

The live `~/.hermes/config.yaml` at audit time shows:

```yaml
model:
  default: minimax-m3
  provider: opencode-go
```

This means the system is now running on a **paid OpenCode Go subscription** ($5 first month → $10/month) with **MiniMax M3** as the daily driver — not "deepseek-v4-flash-free via OpenCode Zen" as stated in `AUDIT.md` line 17 and assumed by every audit.

## Findings now obsolete as current-state concerns

These were raised as critical/high by consensus across multiple audits but **no longer apply** to the current runtime:

| Finding | Raised by | Why obsolete now |
|---|---|---|
| Free-tier SPOF / OpenCode Zen single-vendor lock-in | zhipu1 H1, zhipu2 C4, qwen-audit, qwen-exploration, sakana | Paid Go subscription is the primary path; OpenCode Zen free tier is now fallback only. Free-tier deprecation risk is no longer the primary availability concern. |
| "DeepSeek API key exists but unused" recommendation to switch default to direct DeepSeek | zhipu1 H3, zhipu2 C4, qwen-audit F6 | The default is now MiniMax M3 via OpenCode Go. Switching to direct DeepSeek is no longer the implied next step — it would be a deliberate cost/latency tradeoff against the Go subscription. |
| $0/month cost framing | README, AUDIT.md, most audits | Current runtime cost is $5–$10/month (Go subscription) plus any DeepSeek top-up usage. Cost-efficiency scores of 9/10 in audits should be revised downward to ~7/10. |
| "100% free-tier API dependency — expensive paperweight" | qwen-exploration F5 | No longer accurate. The system has a paid tier with documented usage limits ($12/5h, $30/week, $60/month). |

## Findings that STILL apply regardless of the subscription

| Finding | Raised by | Still relevant because |
|---|---|---|
| `fix-models.sh` source-patching fragility | zhipu1 H7, zhipu2 C6, qwen-audit F4 | The script that restores the OpenCode Go curated model list after `hermes update` is broken (M1 in cross-audit synthesis). Subscription doesn't change patch-drift risk. |
| `gateway_state.json` stale-state bug | zhipu1 C4, zhipu2 C1, qwen-audit F8 | Independent of provider. |
| No remote restart from phone | zhipu1 C4, zhipu2 H1, qwen-audit F9 | Independent of provider. |
| 27 medication crons anti-pattern | zhipu1 M1, zhipu2 H5, qwen-exploration | Independent of provider. |
| Real drug names in `hermes cron list` | zhipu1 C5, zhipu2 M1, sakana | Independent of provider. |
| No automated backup / F: drive SPOF | zhipu1 C3, zhipu2 C5 | Independent of provider. |
| baileys vulnerability claims | zhipu1 C1, zhipu2 C3 | Still unverified advisories — treat as hallucinated until confirmed. |

## New concern introduced by the subscription

**Default cost/quality tradeoff may be misaligned with workload.** MiniMax M3 ($1.20/1M output) is ~4× the cost of DeepSeek V4 Flash ($0.28/1M output) via the same Go subscription. For a workload dominated by medication reminders and briefings, Flash is likely the better default; M3 should be reserved for `/model` switches on hard tasks. None of the audits caught this because none asked to see the live config — they all read the stale `AUDIT.md` snapshot.

## Revised health score

Cross-audit synthesis scored the system **7.5/10**. With the OpenCode Go subscription acknowledged:

- **Cost efficiency**: was 9/10 (free), now ~7/10 (paid but reasonable; potential overpay from M3 default).
- **Model/provider resilience**: was 5/10 (free-tier SPOF), now ~7/10 (paid subscription with documented limits + free-tier fallback available).
- **Overall**: 7.5/10 unchanged — the subscription fixes the free-tier-SPOF concern but introduces a default-model cost inefficiency that roughly cancels the gain until the default is switched to Flash.

Score will move to ~8.5 once `fix-models.sh` is repaired (M1) and the MoA picker is patched (M2), regardless of the default model choice.
