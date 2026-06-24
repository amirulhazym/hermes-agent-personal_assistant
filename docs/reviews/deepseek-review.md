# DeepSeek Review — Independent Second-Pass PRD Assessment (Session 2)

> This review was requested after a handoff from the previous session. It audits the Mimo Review's claims without assuming they are correct, and adds findings from the Claude conversation history (`goal-objective.md`).

---

## 1. Audit of Previous Review

### AGREE — Real gaps the PRD under-addresses

**DeepSeek single-vendor lock-in with no outage strategy.**
The risk table (PRD §15) covers "credits run out" but not "API unreachable / rate-limited / degraded." The PRD forbids all fallback providers (§4.2). When DeepSeek is down, Hermes has no defined behavior — no queuing, no retry, no "I'm unavailable" message.

**No hard cost cap — only alerts.**
Token hygiene (§4.3) lists "budget alerts" but no automatic throttle. DeepSeek has no spending-limit API. A runaway cron loop or memory-compression spiral could drain credits silently.

**Cross-platform state boundary is undefined.**
The PRD says "durable memory shared, session threads separate," but real usage blurs the line. If the user tells Hermes "I have a headache today" on WhatsApp at 9 AM, should that affect Telegram responses? The acceptance test (§14.4) only covers explicit learn-then-recall, not ambiguous edge cases.

**Cost-spike from runaway processes.**
"Loop protection" is mentioned once (§4.3) but never defined. No cron concurrency limit, no max-response-length gate, no per-job token budget.

### PARTIALLY AGREE — Risk is real but overstated

**WhatsApp Baileys risk.**
Baileys is actively maintained (WhiskeySockets), and the PRD already layers reasonable mitigations: dedicated number, allowlist, low volume, Telegram fallback, re-pair runbook. The "1-3 month failure" claim is speculative without evidence. However, a WhatsApp session-health monitoring cron (to detect silent drops) is a valid addition.

**Oracle Always Free reclamation.**
Real but manageable. The gateway's baseline activity (periodic cron + API polling) likely exceeds Oracle's idle threshold. The bigger practical risk is Oracle *never having ARM capacity* in the user's region — requiring owned-hardware on day one.

**Memory noise / garbage collection.**
Valid long-term concern, but Hermes Agent's memory system may already handle staleness. Phase 0 inspection should answer this before it becomes a PRD amendment.

### DISAGREE — Criticism was wrong or premature

**"Start Telegram-only MVP."**
The PRD already sequences Telegram (Phase 4) before WhatsApp (Phase 5). The criticism is redundant.

**"Cron timezone is underspecified."**
Malaysia (`Asia/Kuala_Lumpur`) has no DST. This is noise.

**"Memory sharing might not work." / "Hermes might not be production-ready."**
These are exactly what Phase 0 exists to verify. The PRD's instruction to "read current docs before acting" (§0) anticipates uncertainty. Amend after inspection, not before.

**"Proactive messaging will be annoying."**
The PRD already defines quiet hours, daily caps (3/day), backoff behavior, and stop/later/snooze commands (§10.3). This is a Phase 8-9 tuning exercise, not an architecture flaw. The caps are a reasonable starting point.

---

## 2. Risks the Previous Session Missed Entirely

1. **Hermes Agent version lock.** The PRD never specifies a minimum version or commit hash. The install script (`curl | bash`) pulls latest by default — a breaking update between Phase 2 and Phase 6 means debugging a moving target.

2. **Node.js ARM compatibility for Baileys.** WhatsApp bridge requires Node.js. Oracle ARM runs aarch64. Some native Node modules (WebSocket/protobuf stack) have spotty ARM support. This must be verified before committing to Oracle as the host.

3. **WhatsApp protocol drift detection.** Baileys tracks WhatsApp Web's protocol. WhatsApp has pushed mandatory Web version migrations before. If Baileys lags a forced update, the bridge breaks silently — the session appears connected but protocol version is rejected. The PRD has no detection mechanism for this scenario.

4. **DeepSeek model deprecation timeline is imminent.** Legacy aliases deprecate July 24, 2026 (~30 days from PRD date). Phase 0 must verify that Hermes' DeepSeek provider adapter supports `deepseek-v4-flash` / `deepseek-v4-pro` as direct model IDs, not just the legacy aliases.

5. **"Free web lookup" doesn't exist at quality.** Phase 9 lists free web search. Free APIs (DuckDuckGo rate-limited, SerpAPI free-tier 100/month) produce poor results vs. paid options. This capability will either be broken on arrival or tempt paid usage. Should be documented as best-effort only.

---

## 3. Strength Evaluation

### Weakest Arguments in Previous Review
- "WhatsApp pairing breaks in 1-3 months" — no evidence. Baileys has multi-year deployments.
- "Start Telegram-only" — already the phase order.
- "Memory might not be straightforward" — Hermes explicitly markets this as a headline feature. Test first.
- "Proactive messaging will be annoying" — premature. The PRD's controls in §10.3 are adequate.

### Strongest Arguments in Previous Review
- DeepSeek is a single point of model failure with no defined outage behavior.
- The "same brain" concept works in ideal tests but real boundary cases are unresolved.
- Runaway processes with alerting-only create genuine cost-integrity risk.

---

## 4. Recommended PRD Changes Before Implementation

| # | Change | Priority |
|---|--------|----------|
| 1 | Add risk entry for "DeepSeek API outage/rate-limit" with mitigation (graceful degrade, retry queue, Telegram alert) | High |
| 2 | Add risk entry for "Hermes Agent breaking update" (pin version, test upgrades in staging) | High |
| 3 | Define a hard-spend-cap mechanism: cron disabled if monthly spend exceeds threshold | High |
| 4 | Pin Hermes Agent to a minimum version/commit hash discovered during Phase 0 | Medium |
| 5 | Document "free web lookup" as best-effort, not a guaranteed capability | Medium |
| 6 | Add WhatsApp session-health monitoring cron (detect silent disconnection) | Medium |

Items 1-3 should be PRD amendments. Items 4-6 can be captured as open questions during Phase 0 and recorded in `DECISIONS.md`.

---

## 5. Verdict

**Proceed with Phase 0 now.** The PRD is solid enough to begin doc verification. The gaps identified here are real but are *discovery items* — Phase 0 exists precisely to surface them. The approach:

1. Start Phase 0 immediately (read current Hermes + DeepSeek docs, verify all links in §6)
2. Record all 6 items above as open questions in initial `DECISIONS.md`
3. Amend the PRD after Phase 0 findings, before any installation begins

Phase 0 costs nothing but reading time. It is the safety gate before we commit to any tool execution.
