# Mimo Review — PRD Critical Assessment (Session 1)

> First-pass architecture critique by the initial compose session, before the second-review handoff.

## Biggest Architecture Risks Identified

1. **Single-process gateway is a single point of failure.** WhatsApp, Telegram, cron, memory, and LLM connection in one process. If it crashes, both platforms go down. Split-brain possible where process is alive but one adapter is dead.

2. **WhatsApp via Baileys is a ticking time bomb.** Unofficial reverse-engineered protocol. WhatsApp actively detects and bans automation. If banned, the entire "lives where you already communicate" value prop collapses.

3. **Oracle Always Free ARM is not guaranteed uptime.** Oracle reclaims idle instances. A low-traffic personal assistant might not generate enough activity to avoid reclamation.

## Assumptions That Might Be Wrong

1. "Hermes Agent is production-ready" — unverified. It's open-source; documentation may lag, breaking changes possible, edge cases in WhatsApp bridge uncovered.

2. "DeepSeek V4 pricing stays cheap" — fragile. No fallback strategy if prices rise, outages occur, or rate-limiting becomes aggressive.

3. "Memory sharing across platforms is straightforward." Hermes may not cleanly separate durable knowledge from session context. Memory pollution risk.

4. "Proactive messaging will feel helpful, not annoying." Most users mute proactive bots. No feedback loop to measure whether pings are welcome.

## Ambiguities

1. Which `.env` file location — PRD says `~/.hermes/.env` but Hermes may use different path.
2. "Same brain" operational mechanism undefined — is it shared SQLite, shared memory dir, or custom config?
3. No conflict resolution for cross-platform state — what's durable vs. ephemeral?
4. No escalation path if DeepSeek is down — should Hermes queue, degrade, or just be silent?
5. Cron timezone handling underspecified — DST transitions, persistence across restarts.

## Proposed Changes

1. Start with Telegram-only MVP. WhatsApp adds too much complexity for v0.
2. Add health-check endpoint that tests all adapters individually.
3. Define rollback procedure for each phase.
4. Add DeepSeek outage strategy (graceful degrade, not silent failure).
5. Define "humanized" concretely — persona, system prompt, and how to test it.

## What Would Likely Fail in Production

1. **WhatsApp pairing breaks within 1-3 months.** Most common Baileys failure mode.
2. **Proactive messages tuned wrong.** 3/day cap sounds reasonable on paper but will need weeks of manual tuning.
3. **Memory becomes noisy.** No garbage collection — stale, contradictory, low-value memories accumulate. After 3 months, recall degrades.
4. **DeepSeek costs spike unexpectedly.** Runaway cron loop or memory compression could burn credits before detection.
5. **"Same brain" test passes in demo, fails in practice.** Clean acceptance tests don't capture messy real-world context switching.

## Bottom Line (Session 1)

Optimistic PRD. Biggest risks: WhatsApp instability, DeepSeek single-vendor lock-in, gap between same-brain concept and implementation.
