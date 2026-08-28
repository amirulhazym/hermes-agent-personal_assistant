---
name: external-agent-handoff
version: 1.1.0
description: Prepare complete, verifiable handoff documentation for an external auditor/executor agent (e.g. OpenCode on a different machine) to achieve 100% sync across VPS ↔ PC/WSL2 ↔ GitHub. Use when the user asks you to document system state for another AI, produce a sync snapshot, or verify completeness before delegating work to an external agent.
---

# External Agent Handoff — Sync Doc + Snapshot Prep

When the user wants to hand off system state to an external agent (auditor/executor on another machine), the deliverable is NOT a summary — it is a **verifiable artifact set** that the external agent can diff and trust without re-deriving.

## When to use
- User says "document for OpenCode reachability", "definitely ALL findings", "prepare handoff", "sync VPS/PC/GitHub", "verify before deliver to X".
- User is about to shift roles: you become VERIFIER (live VPS truth-check), external agent becomes EXECUTOR.

## Phased method (proven 2026-07-09)

### Phase A — Full timeline + evidence appendix
- Sweep ALL sessions in the date range via raw SQL on the session DB (see references/vps-session-db-quirk.md). `session_search` by ID fails for cron/empty-title sessions.
- Produce `07-FULL-TIMELINE-<range>.md`: table per day with Time | Event | Evidence (file path / session ID / git hash).
- Produce `08-EVIDENCE-APPENDIX.md` with RAW artifacts (not summaries): cron list output, git diff, exact code snippets + line numbers, `.env` VAR NAMES ONLY (never values), session-ID table, med-state pointers. User demands "definitely ALL" — include actual artifacts, a timeline summary alone is insufficient.

### Phase B — Fresh rsync snapshot
- `rsync -avz --exclude='.env' --exclude='auth.json' --exclude='whatsapp/session' --exclude='*.db*' --exclude='logs/' --exclude='cache/' --exclude='cron/output/' ~/.hermes/ ~/snapshot-<date>/`
- Write `README-SNAPSHOT.md` inside with integrity-check commands (grep line numbers, head config).
- Verify: `.env` absent, config.yaml + models.py + run.py present.

### Phase C — Master sync doc
- Combine Phase A docs + sync-update into ONE `09-MASTER-SYNC-DOC.md`.
- Sections: exec summary, platform state table (VPS=authoritative, Windows/GitHub stale + dates), config changes table (7/7→9/7 verified live), full timeline, evidence appendix condensed, OPEN ITEMS (explicitly flag unimplemented/known bugs — do NOT hide gaps), role split.

### Phase D — Skill-verified completeness
- Load `using-superpowers` + `diagnosing-bugs`. Build a feedback loop: for each artifact OpenCode needs, assert it EXISTS and matches LIVE state (grep models.py:389, run.py:1637, config.yaml head, cron count, med slots).
- Verdict: green = all claims verified against live; list any residual OPEN items as flagged, not hidden.

## Role split (critical)
- **Native agent (you):** VERIFIER only. Check live VPS state, confirm external agent's changes are correct. Do NOT execute fixes after handoff.
- **External agent:** EXECUTOR. Has rsync + read-only SSH (never write unless approved). Per AGENTS.md: git add/commit/push need explicit user approval; show commit message for approval before commit, ask before push.

## PITFALLS (user-correction signals — embed, don't forget)
1. **MIXING QUESTION + STATEMENT = "berterabur".** User explicitly rebuked unclear output: "struktur response kau berterabur, tak clear". Rule: when you need a decision from the user, ASK ONE CLEAR QUESTION in its own block. When informing, label it "Makluman:" or "Statement:" — never interleave so the user can't tell which is which. Separate sections with headers. Exact, not verbose.
2. **Don't over-highlight resolved sessions.** Daily med confirmations (e.g. "4am medication") are NOT audit findings. Only list UNRESOLVED gaps in open-items. If user says "dah resolve / redundant", REMOVE the item from docs immediately and tell them — don't keep stale open-items.
3. **Don't save redundant files.** If you already pasted the content in chat, a saved .md copy is redundant unless the user explicitly wants an attachment. Ask or skip.
4. **Session-search blind spots.** See references/vps-session-db-quirk.md — chat `session_search` misses cron/empty-title sessions; use raw DB query.
5. **VERIFY-ALL-REGISTRATION-POINTS before claiming a provider/dependency is removed.** User said "totally dismiss MiniMax" — but MiniMax was actively used by opencode-go (minimax-m3), novita, and hindsight memory plugin; the `.env` key, a `minimax_proxy.py`, and `provider_models_cache.json` all still registered it. A prior "fix" only commented one `config.yaml` line and falsely implied removal was complete — yet `/model` still listed MiniMax. Rule: when removing a provider/dependency, grep ALL registration points (`config.yaml`, `.env` key, proxy scripts, plugin model lists, model caches) BEFORE claiming done. A still-selectable model means registration persists elsewhere. If the user says "keep only what's tied to OpenCode/other live integrations," preserve those — don't blind-delete.

## Research Brief — Architecture/Design Review Handoff

When the user wants to hand off architecture decisions, design proposals, or technical analysis to a **fresh-context RESEARCH AI** (Grok, ChatGPT, Claude) for double-confirmation, the deliverable is a **self-contained briefing document** — NOT an execution brief or sync doc.

### When to use
- User says "I want to discuss this with Grok/ChatGPT/Claude too" or "get a second opinion"
- User wants another AI to challenge/verify architecture decisions made in this conversation
- The other AI has ZERO context about the conversation history

### What makes a good Research Brief vs Execution Brief

| Dimension | Research Brief | Execution Brief |
|-----------|---------------|----------------|
| Audience | Claude/Grok/ChatGPT (researcher) | OpenCode (executor) |
| Goal | Challenge assumptions, spot blind spots | Execute plan, verify state |
| Content | Questions + current analysis | Commands + state snapshot |
| Tone | "Here's what we think — challenge it" | "Here's what to build — verify it" |
| Length | ~2000-3000 words max | Full sync context |
| Format | Self-contained prose | Artifact set + diff evidence |

### Required structure

1. **Project Context** (1-2 paragraphs) — what the system is, who the user is, what the domain is
2. **Current State** — relevant architecture facts with code evidence, listed as bullet points
3. **Our Proposal** — what we're planning, link to planning doc if exists
4. **Open Questions** — list each question with: what's being asked, what MJ/Hermes already analyzed, what we want the external AI to verify
5. **What We Specifically Want** — numbered asks: challenge analysis, spot blind spots, bring outside patterns, latest solutions
6. **Key Constraint** — anything the external AI must respect (e.g., "reuse existing infrastructure, no new frameworks")

### Formatting guidelines
- Save as Google Doc AND local .md file
- Google Doc can be plain text (it's meant to be copy-pasted into another AI's chat, not read in Docs)
- Include both URLs to the doc + the .md file in your response
- Send the .md file as MEDIA: attachment so user can paste directly
- Brief user on how to use it: paste whole doc to Grok/Claude, follow up with specific ask

### Pitfall
- Research Brief must be SELF-CONTAINED — no "as we discussed earlier" or "per previous analysis". The target AI knows nothing.
- Don't mix Research Brief and Execution Brief content. Research briefs ask questions; execution briefs give commands.
- Keep under 3000 words. A research AI can't ingest a 13-section planning doc in one shot.

### Attachment delivery verification — especially Telegram/mobile

A handoff is **not delivered** merely because the reply contains a `MEDIA:/path` directive. Before saying an external reviewer has the evidence:

1. **Preflight each attachment:** record original filename, size, SHA-256, and whether it contains PII/secret-like metadata. Do not silently forward raw session/phone identifiers to an external reviewer.
2. **Send the exact artifact separately** from the explanatory chat text. Do not bury multiple `MEDIA:` directives after a long status message.
3. **Verify the user-visible result:** an attachment card/download box is proof of delivery. A literal visible `MEDIA:/…` path is a delivery failure, not a link and not a completed send.
4. **If native delivery fails, use a transparent wrapper rather than pretending it worked:** create `<original-name>.txt` with a short header containing the original filename and SHA-256, then append the original payload unchanged after a clear marker. Verify the appended payload SHA-256 equals the original before sending. State that the wrapper hash differs while its payload hash matches.
5. **Do not edit gateway/config just to solve a one-file delivery issue** unless the owner explicitly approves a separate fix scope. Diagnose the extraction/extension path first; use the verified wrapper for immediate delivery.

This preserves reviewability on mobile while keeping provenance and privacy explicit.

---

## Execution Brief — Self-Contained Prompt for Fresh-Context Agent

When the user wants an EXTERNAL AGENT (e.g. OpenCode on PC) to **EXECUTE** an overhaul (not just audit/sync), the handoff is a **self-contained prompt file** dropped into a fresh context window — not a sync doc. Proven pattern 2026-07-10.

### Required structure
1. **MODE** — strategic advisor + executor; freedom to expand/improve the plan with own research; MUST ask before any system change. Don't be a robot that follows blindly.
2. **SKILLS & METHODOLOGY REQUIREMENT (mandatory)** — embed a mandate to use installed skills at max capability: `using-superpowers` + `superpowers` (skill-first), `mattpocock` systematic-debugging + planning-and-task-breakdown, `evidence-first-feasibility-assessment`, `incremental-implementation`. `gsd` (Get-Shit-Done): if NOT installed as a literal skill, embed as a REQUIRED MINDSET (decisive execution, ship increments) and flag it honestly. Apply these when the agent CREATES its master plan (use `writing-plans` 11-section format).
3. **Current State** — git HEAD/branch, untracked folders, remote, push status (all verified live, not assumed).
4. **File Inventory** — exact paths + byte sizes; flag PC↔VPS mismatches (byte-verify with `wc -c`).
5. **Execution Mandate** — role split, approval rules, working discipline.
6. **🔒 WORKING METHOD — HARD RULES** (governs HOW, not WHAT — preserves agent freedom):
   - R1 Context monitoring: report % context every checkpoint; >70% → STOP.
   - R2 Checkpoint: after each task (or 2-3), STOP, report, ASK OWNER to confirm next; if >70% signal owner to spawn subagent (if supported) or start FRESH context.
   - R3 File-reading: NEVER load all files at once; subagent per folder → summary, else batched targeted reads.
   - R4 Per-phase fresh context (each overhaul phase = new window).
   - R5 Q&A gate before execution (correction ≠ approval).
   - R6 VPS read-only via `ssh ubuntu@<ip>` read-only commands; never modify without "go".
   - R7 Freedom preserved (rules constrain mechanics, not conclusions).
7. **Verification Strategy** — sandbox/`--dry-run` only until "go"; evidence-first labels.
8. **Hard Constraints** — skills mandatory, evidence-first, single-source-flagged, partial≠done, secrets-in-.env-only, MJ=verifier-only, sequential, stop-for-destructive, Manglish OK.

Starter skeleton: `templates/execution-brief-skeleton.md`.

### Critical pitfalls (learned 2026-07-10)
- **FREEZE-SCOPE:** The OVERHAUL FREEZE applies ONLY to the native Hermes agent (MJ), NOT to the external executor (OpenCode). Do NOT write "no execution until OVERHAUL V1.0 DAH SELESAI 100%" into the executor's prompt — that blocks phased execution. Use **per-phase/per-step explicit user "go"** approval instead. (Agent error: applied freeze to OpenCode; user rebuked "freeze tu terpakai dekat sini je barua".)
- **VERIFY-BEFORE-TRUST prior analysis:** if a review/audit claims facts (git HEAD, file counts, paths), VERIFY against live VPS via terminal before embedding in the brief. Don't round up a review's claims. (Session: verified c7c40e2 doesn't resolve, archive=8 not 13, cron path is `~/.hermes/cron/jobs.json` not `~/.hermes/jobs.json`, audit-prep VPS=12 missing 5 files.)
- **BYTE-VERIFY sync:** claim "synced" only after `wc -c` comparison PC↔VPS. Untracked git folders (scp'd, not committed) must be flagged as "file-synced but NOT in git".
- **USER FORMATTING:** this user demands clear structured output. Explain any status symbols used (✅/⚠️/❌ = done/warn/blocked). Write in natural Malaysian Manglish. State the PURPOSE of each recommendation. Avoid messy mixed formatting. (Reinforced: "kau taktau status tu... macam lancau. mengarut kau punya formatting.")
- **"ask MJ" mechanism must be defined:** the executor can't DM the native agent directly. Specify: self-verify via `ssh` read-only, or user-relays to native for independent check.

## Deliverable checklist
- [ ] 07-TIMELINE (all sessions, verified)
- [ ] 08-EVIDENCE (raw artifacts, .env names only)
- [ ] 09-MASTER-SYNC-DOC (unified)
- [ ] ~/snapshot-<date>/ (rsync, secrets excluded, README inside)
- [ ] Skill-verified: every claim grep-checked against live
- [ ] Open items explicitly flagged, none hidden
