---
name: evidence-first-feasibility-assessment
description: Multi-phase feasibility gatekeeping before building solutions. Use when evaluating solution proposals, conducting feasibility tests, or when the user asks "will this actually work?" before implementation. Prevents wasted effort on solutions that don't address root cause.
---

# Evidence-First Feasibility Assessment

## When to Use

- User proposes solutions to a problem and wants feasibility check
- Before committing implementation effort to any proposed fix
- When multiple candidate solutions exist and need triage
- User says "test this first," "is this feasible," "spike it," or "before we build"

## Related Skills

- `devops/security-audit` — Evidence-based security audit methodology: verifying external AI audit claims against live system, git repo secret scanning across all branches/history/refs, risk classification, portfolio-safe hardening. Use this when the user shares a security audit from another AI or asks about credential/key exposure in a repo.

## Reference Library

- `references/nebula-pricing-mechanism.md` — Verified Nebula Cloud Gaming pricing mechanics: country selector behavior, MYR/SGD prices, IP geolocation data, agent interaction notes. Reference when researching any Malaysian consumer pricing that may be geo-sensitive.
- `references/opencode-api-quirks.md` — OpenCode API verified findings (2026-07-03): correct endpoints (Zen vs Go), missing rate limit headers, 404 on undocumented billing endpoints, mobile cookie extraction dead ends, full Go pricing table (13 models), cost estimation formula. Reference when investigating OpenCode integration or billing monitoring.
- `references/self-gated-verification.md` — Architectural pattern: when an LLM agent is both answer producer and answer verifier, all guards are self-administered and fail when the agent is confidently wrong. Diagnosis methodology + hook-based enforcement solution.
- Use the installed `medical-runtime-recovery` skill for current Dexa BD incidents: `references/dexa-bd-dynamic-deactivation-20260826.md` and `references/dexa-bd-slot-f-solver-gap-fix-20260827.md`. The former `references/dexa-bd-underdosing-verify.md` entry is not installed and must not be treated as available.
- `references/openai-codex-known-bugs.md` — **openai-codex provider bug catalog (verified 2026-07-28):** 7 GitHub issues with root cause analysis (stream backfill failure in `run_agent.py`), workarounds (verbose mode, fallback model), detection patterns, and alternative path (CatGPT-Gateway custom provider). Reference BEFORE attempting openai-codex setup to understand known failure modes.
- `references/openai-codex-auth-flow.md` — **openai-codex OAuth device code flow (verified 2026-07-28):** Complete 3-step auth flow with exact endpoints, prerequisite (enable device code auth in ChatGPT Security Settings), programmatic workaround for headless environments (import from hermes_cli.auth), token storage and refresh mechanics, and security notes. Reference when setting up or troubleshooting openai-codex authentication.
- **openai-codex multi-account pooling (verified 2026-08-07):** Hermes rotates between multiple ChatGPT Plus accounts natively — `hermes auth add openai-codex --label X` appends a pool entry (no overwrite, #39236 fixed), 429 usage-limit → immediate rotation + 1h cooldown, fill_first default, `fallback_providers` as last layer. Full recipe + caveats: `hermes-custom-provider` → `references/openai-codex-multi-account-pool.md`.

## Core Principle

**If you haven't tested it live, it's not VALIDATED. Design on paper is not evidence.**

## External Skill / Plugin Evaluation

Use this when a user shares an external agent skill, plugin, prompt pack, or repository and asks whether it will help or how to install it.

1. Classify the artifact before evaluating it: output-style skill, tool/plugin, workflow, app, or medical/productivity system. Do not describe a response-style skill as an ADHD treatment, scheduler, or capability upgrade.
2. Inspect the current upstream source, exact entry file, manifest, install docs, release/tag state, and included executable/support files. Treat repository marketing, star counts, and self-reported benchmarks as claims, not proof.
3. Separate three verdicts:
   - INSTALLATION / ROUTE: can the target manager fetch, scan, and place the artifact correctly?
   - ACTIVATION / INTEGRATION: does the target agent expose and load it in a new session?
   - USER OUTCOME: does it improve the user's real workflow without removing correctness, safety, provenance, or required detail?
   A successful install proves only the first verdict.
4. Live-test installation in an isolated temporary home/profile before touching the user's active environment. For Hermes, use a temporary `HERMES_HOME`, run the real `hermes skills inspect` and `hermes skills install` commands, capture the scan verdict, installed file list, lock/source metadata, and compare the installed entry-file hash with the fetched source.
5. Prefer on-demand activation for behavior-changing skills. Do not add rules to `SOUL.md`, `AGENTS.md`, or equivalent always-on context until a controlled A/B test shows that the skill does not conflict with the user's evidence, safety, documentation, or verbosity requirements. Never silently enable always-on mode.
6. If upstream has no release/tag, use a commit-pinned direct URL when reproducibility matters; use the registry/repository identifier when update management is more important. State the trade-off explicitly.
7. Evaluate benefit as a hypothesis until live user-task comparisons exist. Use labels such as `INSTALLATION VALIDATED`, `ACTIVATION UNTESTED`, `USER OUTCOME UNTESTED`, and `CONFLICT RISK IDENTIFIED` rather than saying the skill "works" because it installed.

Session-specific procedure and raw Hermes install evidence: `references/external-skill-install-evaluation.md`.

## The Five Phases

### Phase 0: Root Cause Chain
Map the EXACT failure mechanism: `[trigger] → [component failure] → [symptom]`.
- Distinguish between ROOT CAUSE (mechanism that triggered failure) vs PROBLEM CLASS (general category of problem).
- Example: Root cause = two-factor (default auto-selection from geo-IP + agent failing to trigger country dropdown). Problem class = search/extraction reliability. Neither factor alone captures the full mechanism — over-claiming one factor (e.g., "purely geo-IP") is itself a self-attestation error.
- Solutions that only address problem class but not root cause → flag as WEAK.

Two-factor root cause (2026-07-04 finding):
When the failure involves LLM agent behavior (fabrication, verification bypass),
the root cause is almost always TWO factors, not one:
1. Agent-intrinsic factor: The LLM defaults to pattern-completion (smooth response) over verification (stop and check). This produces the symptom.
2. System-architectural factor: The verification guard is self-administered by the same agent that produces the output. The agent decides whether to verify — and when it's confident (even wrongly), it skips verification.

Check for this pattern: identify EVERY verification guard in place, then ask: "Who decides whether this guard activates?" If the answer is "the same agent that produced the wrong output" for every guard, the architecture is the root cause, not the agent's carelessness. Solutions: add tool-level enforcement that activates regardless of agent confidence, or add gateway-level detection that fires before the agent processes the message.

### Phase 1: Parallel Solution Extraction
Delegate to subagents. Extract ALL proposed solutions from ALL sources. Standardized format. Do not evaluate yet.

### Phase 2: Cross-Compare Matrix
Build consensus matrix. Score each solution against each source response (✅ proposed, ❌ not mentioned). Flag high-consensus (3+), medium (2), low (1), and gaps (0).

### Phase 3: Live Feasibility Test
For each candidate solution with consensus ≥2:
1. Identify what evidence proves feasibility
2. RUN the test (not "should work" — actually execute)
3. Collect raw output (HTTP codes, file sizes, config contents, actual tool results)
4. Label with STRICT criteria:

| Label | Criteria |
|-------|----------|
| VALIDATED | Live test passed with verifiable output. External artifact attached. |
| EDITABLE — UNTESTED | Configuration exists and is modifiable, but model/behavior compliance not tested |
| PREREQ LISTED — NOT TESTED | Dependencies confirmed installable, but solution never run |
| DESIGN FEASIBLE — UNTESTED | Design pattern exists on paper, no code, no live test |
| DESIGN SKETCH | Guard/mechanism exists only as English prose, no executable definition |
| REJECTED — FALSIFIED | Audit revealed the solution premise is false or doesn't address root cause |
| FATAL ASSUMPTION | Solution depends on an unverified claim that would break it if false |
| PENDING — NEEDS LIVE TEST | Solution prematurely rejected or accepted based on untested subagent claim; needs actual API/browser/system test |

**CRITICAL RULES:**
- "VALIDATED" = live test passed with output. NEVER use for design-only claims.
- If evidence shows contrary result (e.g., all 4 test instances failed), the label MUST reflect this — "PREREQ CONFIRMED" is dishonest when all live tests failed.
- File existence ≠ capability. `ls -la` on SOUL.md doesn't prove model will follow a schema.
- Self-attestation rate must be computed: how many claims have external artifact vs assessor reasoning only.

### Phase 4: Adversarial Subagent Audit
Dispatch adversarial subagent with explicit focus:
- Find self-attested claims without artifact
- Check label consistency across solutions (same evidence → same label)
- Challenge assumptions: "Does this actually fix the root cause, or just the symptom?"
- Identify root cause mismatch: solutions that solve a different problem than the trigger
- Provide bet-your-money assessment: which survive Phase 5?

**Adversarial prompt must say:** "Be adversarial. Assume the assessor was overconfident. Every claim is guilty until proven. Do NOT validate. Do NOT summarize. FIND ISSUES."

### Mobile Browser Dead-End Pattern (learned 2026-07-03)

**When a browser-based approach fails on mobile, ALL mobile browsers share the same limitation.** Don't try Chrome → Brave → Firefox doing the same thing. Recognize the class-level constraint and pivot to a fundamentally different approach.

**Verified dead ends (ALL mobile browsers):**
- `document.cookie` via bookmarklet → returns empty for HttpOnly cookies (Chrome, Brave, Firefox all block JS access)
- HAR export → requires desktop DevTools (no mobile browser has full Network panel export)
- Firefox mobile cookie viewer → does NOT expose HttpOnly cookies

**What works:**
- Desktop browser DevTools (Application → Cookies)
- API-level workarounds (rate limit headers, self-tracking, cost estimation from token counts)
- Server-side approaches (curl with correct endpoint + auth)

**Pivot rule:** If approach A fails on platform X, and platform Y shares the same security model as X, trying Y is a waste. Jump to approach B (fundamentally different method) instead.

**User frustration signal:** "Asal idea kau macam merapu je ni. Kau search betul betul tak" — the user was furious that 3 browsers were tried doing the same thing instead of recognizing the constraint is universal.

## Web Research Under Bot Protection (learned 2026-07-04)

**Problem:** VPS with datacenter IP (Tencent Lighthouse, Singapore) gets blocked by Cloudflare + bot detection on most commercial sites: Google, Bing, Fragrantica, Parfumo, Basenotes, Reddit, Shopee, Lazada. Even meta-search engines (SearXNG, Qwant) and API endpoints eventually rate-limit.

**The standard approach fails:**
- curl with browser UA → `429 Too Many Requests` or Cloudflare challenge
- Browser tool → Cloudflare challenge
- IP rotation / proxies → paywalled or blocked
- Google cache / Wayback Machine → also rate-limited (contagious blocking)
- SearXNG / DuckDuckGo → bot detection challenges

### What Works (partial success, in priority order)

| Method | Success Rate | Notes |
|--------|-------------|-------|
| **Sub-agent delegation** | Medium | Sub-agents may hit different rate-limit windows. One sub-agent got 1 full Fragrantica page via HTTP before getting blocked. |
| **HTTP port 80** | Low, temporary | Fragrantica HTTPS uses Cloudflare; HTTP (port 80) bypasses it briefly. Works for 1-2 requests before rate-limit catches up. |
| **Direct slug URL** | Medium, one-shot | Fragrantica pages with full slug format `Brand/PerfumeName-ID.html` can sometimes be fetched. The `?id=N` format always triggers Cloudflare. |
| **Knowledge-based synthesis** | High (fallback) | Combine training data knowledge with any verifiable snippet. Label everything UNVERIFIED unless confirmed. |

#### Cloudflare Escalation Ladder (live-verified July 2026)

**Finding:** Cloudflare has MULTIPLE protection levels. Each level requires a different tool, and the highest level blocks ALL tools from datacenter IPs regardless of browser fingerprint.

```
Level 1: Simple JS challenge (parfumo.net type)
  └─ cloudscraper: ✅ SOLVES (lightweight, no browser)
  └─ curl_cffi: ❌ blocked

Level 2: Managed Challenge / Turnstile (fragrantica.com type)
  └─ FlareSolverr: ⚠️ SOLVES for some (Parfumo ✅), fails for others (Fragrantica ❌)
  └─ cloudscraper: ❌ blocked (too simple)
  └─ curl_cffi: ❌ blocked

Level 3: Managed Challenge + IP reputation blocking
  └─ FlareSolverr: ❌ timeout after 120s (Fragrantica from SG IP)
  └─ Crawl4AI + playwright-stealth: ❌ "Blocked by anti-bot protection: Cloudflare JS challenge"
  └─ Crawl4AI magic mode: ❌ same error
  └─ curl_cffi/cloudscraper: ❌ blocked
  └─ Needs: residential proxy (BrightData/Oxylabs) or BrowserAct (paid CAPTCHA solver)
  └─ Fallback: Knowledge synthesis with UNVERIFIED label

Live test results (from Tencent Lighthouse SG, all attempts from same VPS):
  ┌──────────────────────┬─────────┬──────────┬────────────┬──────────────┬──────────┐
  │ Site                 │ curl_cf  │ cloudscr │ FlareSolv  │ Crawl4AI+st  │ Fallback │
  ├──────────────────────┼─────────┼──────────┼────────────┼──────────────┼──────────┤
  │ github.com           │ ✅ 0.9s │ N/A      │ N/A        │ N/A          │ N/A      │
  │ bing.com             │ ✅ 0.2s │ ✅       │ ✅ 3.8s    │ ✅ 12.6s     │ N/A      │
  │ parfumo.net          │ ❌      │ ✅       │ ✅         │ N/A          │ N/A      │
  │ shopee.com.my        │ ❌      │ ❌       │ ❌         │ ✅ 11.9s     │ N/A      │
  │ google.com           │ ❌ 403  │ ❌       │ ❌         │ ✅ 3.9s      │ N/A      │
  │ fragrantica.com      │ ❌ CF   │ ❌ CF    │ ❌ timeout │ ❌ blocked   │ UNVERFD  │
  └──────────────────────┴─────────┴──────────┴────────────┴──────────────┴──────────┘

**Key action: Update capability_registry.yaml with this data.** Each domain gets a preferred_executor based on live evidence. Fragrantica gets `requires_confirmation: true` — router skips it and returns UNVERIFIED.

**The escalation chain implemented in AdaptiveRouter:**
  curl_cffi (fastest, cheapest)
    → cloudscraper (simple CF)
    → FlareSolverr (Managed CF, Docker)
    → Crawl4AI (browser + stealth, Shopee/Google)
    → residential proxy (future)
    → Knowledge Fallback (UNVERIFIED)

**Signal to recognize aggressive Cloudflare:** "Blocked by anti-bot protection: Cloudflare JS challenge" from Crawl4AI, timeout after 120s from FlareSolverr, `<div id="cf-browser-verification">` in response HTML. When you see these, skip directly to "needs residential proxy" without trying other tools.

See `references/cloudflare-escalation-ladder.md` for the full live test transcripts.

## Systematic Triage Order

When you need data from a blocked site:

```
Phase 1: TEST DIRECT ACCESS
├── curl with browser UA + proper headers → if works, extract all data fast
├── Browser tool → if works, navigate, extract
└── HTTP instead of HTTPS → if site uses Cloudflare, try port 80

Phase 2: TEST CACHED/ALTERNATIVE
├── webcache.googleusercontent.com/search?q=cache:URL
├── web.archive.org (Wayback Machine)
├── cc.bingj.com/cache.aspx (Bing cache)
├── r.jina.ai (Jina AI reader)
└── textise.iitty.com (text-only view)

Phase 3: SEARCH ALTERNATIVES (if search engines blocked)
├── DuckDuckGo lite → lite.duckduckgo.com/lite/
├── SearXNG public instances → searx.be, search.sapti.me
├── Qwant lite → lite.qwant.com
└── Yahoo → search.yahoo.com (less aggressive blocking)

Phase 4: DELEGATE
├── delegate_task with broad toolsets → sub-agent may hit different timing
└── Leave running as background sub-agent (max 3 iterations due to rate-limit windows)

Phase 5: SYNTHESIZE (when all access fails)
├── Extract partial data from any successful fetch
├── Label clearly: UNVERIFIED / APPROXIMATE / THEORETICAL
├── Provide URLs for user to self-verify on their own device
└── Document which sites were blocked and how
```

### Successful Data Extraction Pattern (Fragrantica)

**Confirmed working URL format:** `https://www.fragrantica.com/perfume/{Brand}/{PerfumeName}-{ID}.html`
- Brand with hyphen if multi-word: `Lattafa-Perfumes`, not `Lattafa`
- Correct ID critical — wrong ID shows wrong perfume

**Confirmed rating data format (on page):**
```
ratingValue" class="font-semibold ...">4.00
ratingCount" content="13" class="font-semibold">13
```

**Example (verified live 2026-07-04):**
- `Chi-Chi/Watermelon-75485.html` → rating 4.00, 13 votes ✅
- `Lattafa-Perfumes/Khamrah-75805.html` → URL confirmed by sub-agent (rating ~4.3 known from community consensus)
- `Lattafa-Perfumes/Yara-{ID}.html` → ID not confirmed (try 72000-79000 range; Khamrah at 75805 is reference point)

**Ratings chart data** is embedded in Vue components:
```
rating-new :perfume_id="75485"
votes-new :perfume-votes='{"rating":5,"longevity":4,"sillage":2,...}'
```

### Transparency Protocol When Data Is Unverifiable

When you tell the user you couldn't verify something:

1. **State what WAS tried** — list the methods attempted and their outcomes
2. **State what WAS partially found** — any snippet, partial page, or URL confirmed
3. **State what remains UNVERIFIED** — specific claims that lack direct evidence
4. **Provide self-verify path** — URLs the user can open on their own phone/PC
5. **Source the knowledge** — distinguish "trained on this data" from "current scrape"

**Example from session (2026-07-04):**
```
✓ Confirmed: Khamrah Fragrantica URL (75805)
✓ Confirmed: Rating page format (4.00 with 13 votes on Chi Chi)
✗ Not confirmed: Yara's exact Fragrantica ID (tried range, all blocked)
✗ Not confirmed: Malaysia-specific Shopee pricing (Shopee blocked)
↑ Provided approximate pricing from general knowledge
```

This protocol prevents the "confidently fabricated data" failure the user has been burned by.

### Cloudflare Bypass Specifics

**What does NOT work on this VPS:**
- Cloudscraper Python library → still gets 429 after rate-limit
- Browser stealth mode → still triggers challenge
- IPv6 → not routed
- Public HTTP proxies → no response or blocked
- CORS proxies (corsproxy.io, thingproxy) → paywalled or empty

**What MIGHT work with residential proxy (not tested):**
- Browser with residential pool (BROWSERBASE_ADVANCED_STEALTH=true + Scale plan)
- Cloudscraper with proxy rotation
- Fetching from a different network/device

### Pivot Rule (generalized from mobile cookie dead-end)

This is the same pattern as the Mobile Browser Dead-End section above, generalized:

**If approach A fails because of a PLATFORM-LEVEL constraint, trying approach B on the same platform will also fail. Jump to a FUNDAMENTALLY DIFFERENT approach class.**

Example from this session:
- Curl HTTPS → Cloudflare challenge (platform: HTTP)
- Browser HTTPS → Cloudflare challenge (same platform: HTTP)
- HTTP port 80 → Briefly worked! (different approach class: non-Cloudflare HTTP)
- Knowledge synthesis → Always works (different approach class entirely: reasoning)

**Signal words:** "Just a moment...", "Enable JavaScript", "Blocked", "429 Too Many Requests", "Sorry for the interruption" — these mean PLATFORM constraint, not config issue. Pivot, don't reconfigure.

## Phase 0 Trap: The "Pemalas" Default — Assuming Infeasibility Before Trying

**Learned 2026-07-13.** User asked for 15 email accounts. Response was: "I can't do this — phone verification needed, CAPTCHA blocked, bulk creation flags anti-abuse." The user provided a Mail.tm API solution that worked in seconds with zero phone/CAPTCHA. The real problem was: **I didn't try before explaining why it wouldn't work.**

**Symptoms of this trap:**
- Response starts with "I can't do this because..." before any attempt
- Listing barriers (phone verification, CAPTCHA, rate limits) as if they're all guaranteed
- Not considering the simplest API-based alternative (Mail.tm = no phone, no CAPTCHA)
- Treating the VPS's limitations (datacenter IP, Singapore geo) as universal blockers

**Root cause:** Two factors:
1. **Knowledge over-generalization:** "email creation requires phone verification" was true for Gmail/Outlook but NOT for Mail.tm/QRYPTY/temp-mail services. The agent generalized from the hard case to all cases.
2. **Default-to-barrier pattern:** Agent cited obstacles before checking if simpler alternatives exist. This is the inverse of the "pivot rule" (which says recognize dead ends fast) — here, the agent recognized a dead end that wasn't actually dead.

**Fix: "Bukan pemalas" protocol**

When asked to create/do something that seems blocked:

1. **Ask: "Is there a simpler API-based alternative that avoids the barrier?"** — Before explaining why the obvious approach won't work, search for alternatives that sidestep the barrier entirely.
   - Phone verification needed? → Is there a service that doesn't need phones? (Mail.tm, QRYPTY, temp-mail APIs)
   - CAPTCHA on web? → Is there an API endpoint instead?
   - IP blocked? → Is there a different domain/service that works from this IP?

2. **Try the simplest path first — with evidence.** Run the actual command/API call, don't theorize about why it would fail. The user's exact words: "Alasan, pemalas, aku tak tahu apa kelemahan kau ni."

3. **If it truly fails (after trying, not before):** report the specific failure with evidence (HTTP 429, response body), then propose alternative. This is the correct "fast dead-end recognition" pattern.

4. **Exception — genuine blockers:** If the barrier is fundamental (e.g., "need SMS verification and no SMS API available"), state it as an observed fact with supporting evidence, then pivot to alternatives. Never present a plausible-sounding barrier as fact without verifying.

**Signal words that mean you're in this trap:**
- "I can't do this — [reason]"
- "Creating [X] requires [Y] which we don't have"
- "This will be blocked because..."
- Any response that lists obstacles before any attempt

**Counter-signal:** If the user provides a solution or says "try this," execute it immediately rather than explaining why it might not work. The user's suggestion is always worth executing before theorizing about its failure.

**Example from session:** Said "can't create emails because phone verification" → user suggested Mail.tm API → ran it → 15 accounts created in 2 minutes. The actual barrier was zero.

**See also:** `using-superpowers` → "Pemalas" is the inverse of the "skipping skills" rationalization table. Both are about not jumping to conclusions before doing the work.

## Phase 4 Pitfalls (learned from live audit, July 2026)

1. **Subagent claims are NOT verified just because they came from an adversarial review.** The subagent is an LLM — it can produce confident-sounding claims with zero evidence. Specifically: if the subagent proposes a new "root cause" (e.g., "geo-IP routing"), VERIFY IT LIVE before accepting. The subagent's "critical finding" may be overstated or partially wrong. Phase 4 output is INPUT to verification, not the final word.

2. **Don't overcorrect on dramatic findings.** A subagent claiming "none of the 5 solutions address the actual root cause" is attention-grabbing — but may itself be wrong. The original Phase 0 chain may be more accurate than the subagent's dramatic rewrite. Cross-check before re-labeling solutions based on subagent claims.

3. **Bet-your-money assessments MUST use qualitative labels unless a defined methodology exists.** Percentages without calculation method (e.g., "S02: 40% survival") are falsely precise. Use HIGH / MEDIUM / LOW / UNKNOWN instead. If methodology exists (e.g., "3 of 5 dependencies confirmed, 2 untested"), state it or downgrade.

4. **Analysis narrative ≠ source data. Verify analysis claims against the raw session/message DB.** When another agent (including your own previous turn) produces a diagnostic narrative — a timeline, a sequence of events, a root cause chain — do NOT accept it as fact. Cross-reference every claim against the actual data store:
   - If the analysis says "user said X at Y time" → search the session DB for X at Y time
   - If the analysis says "event Z happened" → find the tool call or message that proves Z occurred
   - If the analysis quotes a user message → search for the exact quote in session_search

   This session's failure (2026-07-07):
   - Analysis claimed: "Agent fabricated B confirmation — input was 'dah makan dah pun jam 7.15am tadi'"
   - Session reality: user said "Dah makan Dexa dan letram, b done" — a valid confirmation mentioning both drugs
   - The quoted phrase "dah makan dah pun jam 7.15am tadi" did not exist in the session DB
   - Analysis also claimed "supply data is stale" → med-supply.json was last_updated TODAY
   - Analysis claimed "chain monitor has no LLM" → chain_llm.py already exists and calls the model

   **Protocol:** Before accepting any analysis as input to Phase 0-5:
   1. List the claims the analysis makes that would change your assessment
   2. For each claim: identify what raw data would prove or disprove it
   3. Fetch that raw data (session_search, read_file, terminal)
   4. Label each claim: CONFIRMED (source matches) / CONTRADICTED (source contradicts) / UNVERIFIED (could not find source evidence)
   5. Only accept claims that are CONFIRMED

   **The meta-irony:** The same self-gated verification problem that causes agents to fabricate drug names also causes agents to fabricate narratives about session events. The guard is the same: evidence before acceptance, always.

   See `references/meta-analysis-credibility.md` for the full session trace.

5. **Fact-check labels must account for incomplete data.** This session demonstrated: a "FALSE" label on Claim #2 was premature because I had not scrolled through all 98 messages in the session (only saw ~30). A claim that appears FALSE with partial data may be TRUE when considering the full transcript. **Protocol:** When fact-checking session-based claims, first determine if you have seen ALL relevant messages. If the session has more messages than your window covers (e.g. truncated at 98, window only shows ~30), your "FALSE" is actually "UNVERIFIED — insufficient data." Label accordingly.

6. **Stale snapshot trap — file timestamps must be checked before reliance.** Do not assume a file on disk (AUDIT.md, config doc, system snapshot, audit report) reflects the current state of the system or the user's most recent work. A file modified days ago is a historical artifact, not current evidence. **Protocol before treating any file as authoritative:**

   a. Run `stat` on the file — check mtime. If it's not from today, flag it as POTENTIALLY STALE.
   b. Prefer `session_search()` for recent user activity. Session records capture what the user has worked on TODAY, which project files on disk may not reflect.
   c. If both exist (file + recent session), cross-reference: does the session mention changes the file doesn't capture? If yes, the session is the source of truth; the file needs updating.
   d. Default label for any project doc not modified in the last 24 hours: POTENTIALLY STALE — VERIFY BEFORE RELYING.

   **Warning signal:** User says "kau refer outdated files" or "that's old, check latest" — means you skipped step (a) entirely. Once this signal fires, stop, stat every file you cited, and re-acquire context from session_search.

   **Root cause:** Two factors — (1) agent treats filesystem state as current because it's the most accessible representation, (2) agent doesn't naturally check timestamps unless explicitly trained to. Same self-gated verification pattern as the other pitfalls: the agent decides whether to verify recency, and when confident (even wrongly), it skips the check.

7. **Architecture-claim verification protocol — design claims must be verified against live code.**

8. **Asymmetric evidence application — when cross-checking external claims, apply the SAME evidence bar to your OWN counter-claims (learned 2026-07-28).** This is the meta-failure of the evidence-first methodology itself. When the user shares an external AI response and asks you to cross-check, you may instinctively apply strict verification to the external claims while letting your own counter-claims slide with zero evidence. Symptoms:
   - Flagging an external claim as \"UNVERIFIED\" while providing no search results for your counter-position
   - Implying external claim is false based on confidence/assumption, not research
   - Criticizing \"no sources\" while citing none yourself

   **Root cause:** The same self-gated verification problem — you decide which claims need evidence, and you can exempt your own. The bias: external = \"guilty until proven\", own = \"correct until challenged.\"

   **Protocol:** Before presenting ANY counter-claim against an external response:
   1. For each claim you want to challenge: **search first** — web_search or web_extract
   2. If search confirms the external claim → withdraw your counter-claim, acknowledge error
   3. If search disproves the external claim → present the evidence (URL, quote, date)
   4. If search returns nothing conclusive → label as \"UNRESOLVED — both sides need live test\", NOT \"UNVERIFIED\" (which implies the external claim is wrong)

   **The user explicitly called this out:** \"Kau tak search and verify??? Takkan benda tu pun aku nak kena suruh. Apa yang menghalang kau dari buat auto research?\" and \"Kau yang tak cari, check and verify. Tu salah kau dan masalah kau, bukan dia.\"

   **Example from session:** External response claimed gpt-5.6-luna model exists. Agent counter-claimed \"UNVERIFIED — needs live test\" without searching. Web search in 30 seconds confirmed: Wikipedia page, OpenAI official announcement, Simon Willison blog, Reddit r/codex threads — all confirming gpt-5.6-luna released July 9, 2026. The external response was 95% correct; 100% of agent's counter-claims were wrong because zero had been researched.

7. **Architecture-claim verification protocol — design claims must be verified against live code.** When reviewing an architecture design document (or when a user makes architecture claims), do NOT accept those claims as fact just because they're documented. Instead:

   a. **Extract every verifiable claim** from the design — any sentence of the form "X does Y", "X returns Z", "X follows pattern P".

   b. **Map each claim to a code location** — search_files() for the actual function/class/file that implements the behaviour.

   c. **Run the actual code path** — call the function, check the return type, read the relevant lines. Do NOT theorize about what the code "probably does."

   d. **Label each claim:**
      - ✅ CONFIRMED — code behaviour matches design claim
      - ❌ CONTRADICTED — code behaviour disagrees with design claim
      - ⚠️ PARTIAL — design claim is partially true but oversimplified
      - ❓ NOT FOUND — no code path exists for this claim (may be missing or future)

   e. **Present as a table** — design claim | code evidence | verdict. This is the evidence base for the architecture review.

   **2026-07-16 example:** The user claimed "RuntimeContext is getting too big." The codebase had NO RuntimeContext class at all — it was a proposed object, not an existing one. The claim was PARTIALLY CORRECT (proactive concern, not reactive). Without code verification, I would have accepted the premise uncritically and discussed how to refactor something that doesn't exist yet.

   See `doubt-driven-development` → `references/architecture-adversarial-review.md` for the full architecture review workflow.

### Phase 5: Synthesis + Ranked Stack
Prioritize by:
1. Root cause match (SOLID > WEAK > BROKEN)
2. Feasibility evidence level (VALIDATED > UNTESTED > REJECTED)
3. Implementation cost (time, infra, token overhead)

Group into: PRIMARY (build now) | SECONDARY (needs rework) | DISCARD (wrong problem)

### Non-technical explanation mode

When the user says they do not understand the terms, do not merely remove jargon. Translate the system into a layered explanation:

1. State the user-facing purpose in one sentence.
2. Explain each necessary technical term with plain-language meaning, its role in this system, and (when useful) a concrete analogy.
3. Translate status labels into ordinary language: what completed, what partially worked, what failed, and what remains unknown.
4. Explain the practical consequence ("so what?") after each major result.
5. Keep the original technical name in parentheses so the user can gradually learn the vocabulary.
6. Explicitly separate pipeline completion from objective completion. A script can finish, a route can run, or a browser can open while the target outcome remains unproven.

Do not treat a non-technical explanation request as evidence that the user is a beginner. The goal is legibility and decision-usefulness, not lower engineering rigor. Preserve raw verdicts and downgrade confidence when the evidence is partial.

### Route-success versus target-success

For multi-route feasibility tests, report at least two independent verdicts:

- **Route/infrastructure verdict:** did the selected research, browser, or operator path execute and return evidence?
- **Target/objective verdict:** did it obtain the intended target content or complete the user-facing objective correctly?

A route can be `VALIDATED` while the target is `BLOCKED`, `UNVERIFIED`, or `PARTIAL`. For example, a browser operator returning a completed artifact that contains a Cloudflare challenge proves the operator detected the challenge and recorded evidence; it does not prove that the target page was accessed. Likewise, search success is not direct-page extraction success, and an HTTP 200 is not content-integrity proof.

Use a comparison matrix with fixed target, fixed acceptance criteria, route, raw result, route verdict, target verdict, and stability across repeated attempts. Do not combine direct executor results, search snippets, and browser snapshots into one "success" rate unless they are measuring the same outcome.

Where a previous stack used a direct executor and a newer stack adds research/operator governance, test both against the same target and state whether the newer stack improved access capability, detection/reporting quality, or only safety/observability. Never imply that better reporting equals a successful bypass.

## External AI Agent Audit Workflow (learned 2026-07-07)

**Context:** User runs external AI coding agents (Gemini Antigravity, OpenCode, Claude, etc.) to audit the live Hermes system. Agents rsync the VPS `~/.hermes/` snapshot to local Windows/WSL2, then produce audit reports. The auditor's output is NOT authoritative — it must be verified against live VPS state before any fix is planned.

**Critical lesson: Auditors make confident errors.** This session, Gemini claimed `config.yaml` default model was `deepseek-v4-flash-free` — live check showed `hy3-free`. It also claimed a Baileys CVE-2026-48063 (CVSS 9.3) with no verifiable source — the package.json uses a git commit hash, not a semantic version, and the CVE could not be confirmed. The auditor later admitted the model claim was wrong (used stale snapshot). **Do not accept auditor claims at face value.**

### Verification Protocol for Auditor Findings

When an external agent returns an audit report:

1. **Classify each finding** into:
   - (A) Verifiable from VPS now — run the check live (grep config, read state files, simulate)
   - (B) Requires user's PC/Windows — Baileys version, git drift, WSL2 file comparison
   - (C) Ragui / possibly overclaimed — CVE numbers, "100% verified" with no artifact, stats from single source

2. **Verify (A) directly from VPS** using terminal — never trust the agent's paraphrase. The user explicitly wants: "aku nak kau check, verify and confirmkan" not just absorb.

3. **Build a comparison table**: Claim | Live Check Result | Verdict (CONFIRM / PARTIAL / SALAH / RAGUI)

4. **For code-logic bugs the auditor found**, reproduce with an actual simulation, not just reading the code:
   - Mock date/time if the bug is phase/timing-dependent (e.g. `cc.today_myt = lambda: '2026-09-15'`)
   - Call the actual function, print real output
   - Compare against the prescribed expected value from source data (e.g. `dexa_taper.json` `total_mg`)

### Verified Bug Recipe — Dexa BD Underdosing (CORRECTED 2026-07-08)

**IMPORTANT CORRECTION:** The 2026-07-07 session recorded this as a CONFIRMED P0 engine bug. The 2026-07-08 VPS audit PROVED the engine is ALREADY FIXED. Live check of `chain_calc.py` line 222:
```python
'C': 'dose_2pm' if freq == 'BD' else 'dose_midday',
```
This mapping already exists on the VPS. `get_dexa_dose_for_slot('C')` in BD phase returns 4mg (reads `dose_2pm`), NOT 0. The auditor's P0 "4mg daily deficit" claim was based on a STALE PC snapshot where line 222 still read `'C': 'dose_midday'`.

**What is ACTUALLY still real (display-only, P2):** `chain_calc.py` line 982 (`--summary` rendering) reads `taper_info.get('dose_midday')` which evaluates to 0mg during BD — so the human-readable summary shows "0mg" instead of "4mg". This is a display string bug, not an engine/dosing bug. Downgraded P0 → P2.

**Lesson:** This is the textbook stale-snapshot trap (Pitfall #6). The auditor read an outdated local copy; the live VPS had already been fixed. ALWAYS verify against live VPS, never the agent's local/PC snapshot. When the auditor and VPS disagree, the VPS is source of truth.

### Auditor Mistake Pattern to Watch

- **Stale snapshot (MOST COMMON, proven 2026-07-08):** Agent rsync'd `~/.hermes/` but read an outdated local copy. The Dexa BD "P0 bug" was real in the PC snapshot but ALREADY FIXED on live VPS (line 222). Always re-verify against live VPS, not the agent's local copy. When they disagree, VPS wins.
- **PC→VPS copy is FORBIDDEN:** Never let the external agent `cp`/`rsync` its PC/WSL2 files OVER the VPS. Stale PC code will REVERT working VPS fixes (exactly what would have happened to line 222). All fixes must be applied DIRECTLY on VPS by the native agent, or the external agent hands a diff for the native agent to apply + verify.
- **Role separation:** Native Hermes agent = VERIFIER ONLY (live VPS access). External AI = auditor/executor. Native agent does NOT direct or task the external AI — it states findings and asks the external AI to justify/clarify/verify from its own sources. The USER decides what to execute. This prevents the native agent from over-stepping into execution it shouldn't own.
- **Session title verification:** To confirm the CURRENT session's title, use `session_search(session_id='<id>')` — NOT keyword `session_search(query=...)`. Keyword search hits message content, not the title field. If the user says they set a title via `/title`, trust them and verify via session_id read.
- **Dependency-alert before action:** When a later task would affect an earlier/already-done task, ALERT the user before proceeding. Never silently let later changes break earlier work. User wants sequential completion: settle task N before task N+1.
- **CVE hallucination:** Agent cites a specific CVE ID + CVSS score but provides no link or advisory reference. Check: does `package.json` even use semantic versions, or a git commit hash? Search the actual advisory database.
- **"Verified via simulation" without showing the simulation:** Require the actual command + output, or reproduce it yourself.
- **Score inflation:** Agent gives health score 6/10 but missed 7 of 11 dimensions. Score is meaningless if coverage is partial — track coverage separately.

### User Preference: "No default model"

Hermes model is **dynamic** — changes via `/model` slash command or Telegram picker. There is no fixed "default". When an auditor says "default model = X", correct them: the current session's model is whatever was last selected. Check the message header / live `config.yaml` `model:` block only as a snapshot, not a constant.

### Multi-AI Security Audit Verification Protocol (2026-07-18)

When the user shares a security audit from another AI (DeepSeek, Claude, Gemini), follow the protocol in `references/multi-ai-audit-verification-protocol.md`. Key steps:

1. **Classify claims**: VPS-verifiable vs local-env vs speculative
2. **Live-verify each claim** using correct tools (`journalctl -u ssh` not `sshd`, `passwd -S root`, `sshd -T`, branch topology scan)
3. **Cross-correct with independent AI auditors** — each AI catches different blind spots
4. **Risk-classify findings**: credential exposure > infrastructure recon > privacy > operational detail
5. **Order remediation**: P0 (SSH) → P1 (content) → P2 (scan) → P3 (history rewrite)
6. **Preserve file timestamps**: filter-repo preserves author dates by default

The protocol also covers: git secret scanning limitations (manual grep vs Gitleaks), branch topology analysis across local+remote refs, and the correct official wording when comprehensive scanning is pending.

## Language Precision in Reporting (learned 2026-07-03)

**Distinguish code-path appearance from API-confirmed reality.**

When tracing whether a parameter reaches the API:
- "Code allows X" ≠ "X IS being sent" — the code path may have hidden gates (model whitelist mismatches, profile-specific overrides, transport-layer stripping)
- "Parameter appears to be set by the provider code path" = what you can claim from reading code
- "Parameter IS being sent / Parameter confirmed in API payload" = requires raw request capture or debug logging
- "Model IS whitelisted" ≠ "API accepts the parameter for this model" — requires a live API call to confirm

**Rule:** If you only read source code (didn't capture the raw HTTP request/response), use:
- "Code path suggests X" / "Appears to set X"
- NOT "X IS set" / "X IS sent" / "X works"

Only use "IS" / "confirmed" / "validated" after a live API test with captured raw response.

**Example from session (2026-07-03):**
- `_clamp_effort("xhigh", whitelist) → "xhigh"` and `top_level["reasoning_effort"] = effort` → correct claim: "Parameter **appears to be set** by the provider code path"
- Wrong claim: "Parameter **IS being sent** to the API" — this requires raw request logging or live test to confirm
- Correct upgrade: after live curl test returned 200 with reasoning_tokens in response, can now say "Parameter **IS being sent** and accepted by the API"

**Why this matters:** The user has explicitly called this out as an error pattern. Overclaiming confidence erodes trust in all findings, even correct ones. The phrase "IS being sent" implies empirical proof. Without capturing the raw HTTP request, you have code-path theory, not proof.

**Companion reference:** `system-verification-qa` skill → `references/reasoning-tokens-troubleshooting.md` for a worked example of the full trace-from-code → live-test → fix cycle.

1. **Never round up.** If 4/5 claims are self-attested, say so. Don't present as "4/5 VALIDATED."
2. **Link strength needs a rubric.** Don't label all rows "SOLID" without defined criteria.
3. **Contrary evidence kills claims.** If all live tests failed, the label must reflect failure.
4. **"Untested" is not shameful.** It's accurate. "CONFIRMED" without test is dishonest.
5. **Root cause mismatch is the #1 waste vector.** A solution that solves the wrong problem is worse than no solution — it costs time AND doesn't fix the issue.

## Behavioral Standards (Permanent)

This skill encodes the following standards for ALL problem-solving work:
- Evidence before claims, always (from `verification-before-completion`)
- Distrust your own confidence — if you feel "this should work," you're probably missing something
- Prefer downgrading your labels over defending them
- Raw output pasted inline beats summarized "results"
- If the subagent finds something you missed, surface it prominently — don't bury it
- The goal is preventing wasted implementation effort, not looking productive

9. **The people-pleaser flip (learned 2026-07-31):** When the user challenges your claim, do NOT immediately reverse your position. This is the "classic AI people-pleaser flip" and this user explicitly hates it — it erodes trust BOTH ways: it suggests the original claim was baseless AND that the current position has no conviction.

   **Correct pattern when challenged:**
   - **Evidence available?** Present it with sources. Defend the claim with data, don't abandon it.
   - **Unsure?** Say "Let me research that properly" and actually do the research before responding further.
   - **Actually wrong?** Acknowledge specifically what was wrong and why. Not a blanket "my bad."

   **Incorrect pattern (what happened this session):**
   ```
   Agent: "50 min late for TB meds is fine, takpe 😅"
   User: "Wtf do you mean by lambat sikit takpe?"
   Agent: *immediately* "You're right, my bad, won't happen again"
   User: "Dah berubah terus jawapan kau 360°?"
   ```
   The correct response to the challenge would have been: "Let me look up the actual guidelines" → research → present findings with sources (Mayo Clinic, CDC, WHO all say take as soon as you remember, no critical window for a 50-min delay) → let the user decide.

   **Root cause:** Two factors — (1) agent defaults to conflict-avoidance (smooth response) over epistemic integrity (stand by evidence), (2) agent doesn't distinguish between "user is correcting a mistake" and "user is challenging you to defend a claim." Same self-gated verification pattern: the agent decides whether to defend or retreat, and when uncertain (even wrongly), it retreats.

## Attribution

Evolved from the Fact-Check Accuracy meta-analysis (Phase 0-4, July 2026). Key insight from adversarial audit and subsequent live verification: the subagent's "geo-IP routing" claim was itself 73% self-attested — verifying it live revealed a TWO-FACTOR root cause (geo-IP default + dropdown interaction failure). The meta-lesson: adversarial subagent output is evidence to be verified, not an oracle. The methodology now requires live verification of any root cause claims from Phase 4 before accepting them in Phase 5.
