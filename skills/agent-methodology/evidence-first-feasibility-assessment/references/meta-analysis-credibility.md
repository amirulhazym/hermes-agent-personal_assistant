# Meta-Analysis Credibility: Verified Session Trace

Date: 2026-07-07
Session: 20260707_061532_2ec7e7c7 (98 messages, WhatsApp, deepseek-v4-pro)

## The Failure Pattern

An analysis agent (loaded systematic-debugging + diagnosing-bugs skills) produced a
3-part diagnostic narrative at 07:57 MYT. The narrative claimed:

1. Agent fabricated B confirmation — quoted user as saying "dah makan dah pun jam 7.15am tadi"
2. Supply data is stale — "Data staleness + no substitution awareness"
3. Chain monitor doesn't use LLM — "The fix was never applied to this cron"
4. 8 issues categorized with specific timestamps

A second agent (fact-check pass at 09:18) verified these claims against the session DB
and found:

| Claim | Analysis Said | Session Evidence | Verdict |
|-------|--------------|-----------------|---------|
| B confirmation fabricated | "dah makan dah pun jam 7.15am tadi" → auto-mapped to B | User said "Dah makan Dexa dan letram, b done" (msg 11975) — correct confirmation | **CONTRADICTED** |
| Supply data is stale | 2 occurrences of noisy alerts | med-supply.json last_updated=2026-07-07 (today). Alert was real but data was not stale | **CONTRADICTED** |
| Chain monitor no LLM | "no_agent=true, static Python script" | chain_monitor.sh calls chain_llm.py which uses SAME model as chat | **CONTRADICTED** |
| Timeline accuracy | 06:15 A✅ → 06:57 noise → 07:03 panto Q → 07:15 takes panto → 07:15 cron → 07:48 clarification → 07:50 mis-log → 07:51 user corrects | 07:50-07:51 section could not be verified — session truncated, 58 middle messages unseen | **PARTIAL** |

## Root Cause

The analysis agent suffered from the same self-gated verification failure it was
diagnosing: it was confident in its narrative, never verified against source data
(session DB), and produced a compelling but partially false diagnosis.

**Two-factor root cause:**
1. Agent-intrinsic: LLM defaulted to pattern-completion (smooth narrative) over
   verification (stop and check session DB)
2. System-architectural: No guard required the analysis to be grounded against
   source data before delivery

## Guardrails That Would Have Prevented This

1. **Pre-delivery session cross-reference:** Before presenting any analysis that
   claims specific user messages or timestamps, search the session DB for those
   exact messages. If they don't exist, the narrative is fabricated.
2. **Confidence gating on truncated data:** If the session has N messages and you
   only loaded M < N, state: "This analysis is based on partial session data
   (M/N messages). Claims about messages in the unseen section pending verification."
3. **Phase ordering:** Evidence-first (check source data) → Analysis (build narrative)
   NOT: Analysis (build narrative) → Verification (optional, skipped when confident).

## Session Structure Metadata

The session DB stores messages with:
- id (integer, sequential)
- role (user/assistant/tool/session_meta)
- content (the actual text)
- timestamp (Unix epoch)

Key limitation: `session_search` with a session_id returns at most 20+10 messages
in truncated mode. The middle section is only accessible by scrolling with
`around_message_id` + `window` parameters. A thorough analysis requires scrolling
through ALL message windows, which is time-consuming but necessary for accuracy.

## Corrected Timeline (After Full Verification)

| Time | Event | Evidence |
|------|-------|----------|
| 06:15 | A confirmed ✅ | msg 11825-11827 |
| 06:15 | Supply alert "STOCK OUT: Pyridoxine" (noise) | med_confirm.py output (msg 11827) |
| 06:57 | User angry about supply alert | msg 11830 |
| ~06:58 | Agent debugged, patched med_confirm.py (exclude confirmed drugs from alerts) | msg 11831-11845 |
| ~07:03-07:45 | Pantoprazole research (browser, failed web_search) | msgs in middle section |
| ~07:15 | Cron fired B reminder mid-chat (unseen by agent) | Cron schedule */15 5-22 |
| ~07:57 | Agent produced 3-part analysis (above) | msg 11957 |
| ~08:18 | User said "Dah makan Dexa dan letram, b done" | msg 11975 |
| ~08:18 | Agent correctly logged B at 08:20, updated to 08:00 | msgs 11976-11982 |

## Lesson

When you are the SECOND agent reviewing a FIRST agent's analysis, your most
important job is NOT to extend the analysis — it is to VERIFY the analysis
against source data. The analysis is INPUT, not truth. Treat it as a
"hypothesis" document, not a "findings" document, until each claim is
confirmed against the session DB.
