---
name: job-role-research
description: End-to-end research of a job posting — verify company legitimacy from the company's OWN site, clarify buzzword titles (e.g. "vibe coding") as the tool/method not a misnomer, hunt salary/payment across role sub-pages when job boards are blocked, and assess fit + give a strategic "rush or not" call. Use when the user shares a job URL/JD, asks "legit ke? / gaji? / fit for me?", or wants a resume tailored to a specific role.
---

# Job Role Research — legitimacy + salary + fit

## When to use
- User pastes a job link / JD and asks: legit ke? gaji berapa? fit for me? nak apply? resume macam mana?
- User wants to reposition/repackage their profile for one specific role.

## Core discipline (restated from SOUL — non-negotiable)
- NO self-attestation without evidence. Label UNVERIFIED / PARTIAL / THEORETICAL.
- Salary / payment method NEVER guessed. If not published → declare DATA GAP; offer a clearly-labeled industry benchmark ONLY as an anchor.
- Live-data persistence: try multiple distinct routes before giving up; state exactly what was tried.

## Phase 1 — Get the posting
- Job boards (Indeed, JobStreet, etc.) are often Cloudflare/403-blocked from this VPS datacenter IP. DO NOT stop there.
- Fall back to the COMPANY'S OWN DOMAIN (usually reachable even when the board isn't):
  - `/about`, `/terms` (legal entity + jurisdiction), `/contact-us` (HQ, locations), `/careers` or `/work-from-home-opportunities` (role pages).
  - Extract ALL hrefs, fetch every role sub-page, parse for pay keywords.
  - Exact curl + parse recipe: `references/research-pattern.md`.
- Reader proxies (r.jina.ai) and Google webcache also frequently return CF challenges from this IP — don't rely on them; go to the source domain.

## Phase 2 — Legitimacy check (verify, don't assume)
Collect from the company's own site:
- Legal entity in ToS (e.g. "Agents Only Technologies Inc.") — must MATCH the JD poster.
- HQ address + operating locations.
- Real clients / case studies / named leadership.
- Proper ToS + Privacy + data-protection (BCR) docs.
- A payroll/billing function ("Global Billing & Payments").
STATE SEPARATELY: Legit ≠ good pay or good fit.

## Phase 3 — Role nature (PITFALL: buzzword titles)
- Read the responsibilities literally first.
- PITFALL — a title with a trendy buzzword that seems MISMATCHED with the listed duties is often NOT a misnomer. The buzzword usually names the TOOL/METHOD used to PERFORM the responsibilities.
  - "Vibe coding" (Karpathy, 2025) = building WITH AI coding tools (Cursor/Claude/Copilot) from natural-language intent, not hand-writing code.
  - So "Productivity Tool AI Trajectory Specialist (Vibe Coding)" = use vibe-coding tools to BUILD the trajectories (which then become training data). That is BUILD-leaning, not evaluator-only.
  - Do NOT over-label it "misnomer / just an eval gig." Consider a hybrid build + eval reading.
- If still ambiguous, present both readings and let the user decide; don't force one.

## Phase 4 — Salary & payment hunt
- Check: JD, company role pages, ALL role sub-pages for any published rate.
- Parse pay keywords; DISTINGUISH real numbers from boilerplate:
  - "competitive compensation based on experience" = no number.
  - "cadence" ≠ CAD currency. "pay structure" / "response rate" = not a wage.
  - Real signal = an actual figure ("RM 3,000", "$20/hr", "USD 15–50"). Absent on every page → no published salary.
- If nothing published after ≥3 distinct methods → DATA GAP. State exactly what was tried (see research-pattern.md template).
- Industry benchmark (e.g. AI-contributor / "vibe coding" gigs ~USD $15–50/hr reported on OTHER platforms) ONLY labeled "unverified for this company, anchor only."
- Payment method (PayPal/Wise/Deel/bank) + currency: check ToS ("payroll processors"), billing-team mentions. Note foreign currency + independent-contractor tax reality for a MY remote worker (no EPF/SOCSO; self-file foreign-sourced income).

## Phase 5 — Fit analysis
- Establish the user's current profile from evidence before assigning a fit label. Prefer, in order: latest user-confirmed facts, latest resume/CV artifact, public portfolio/GitHub/LinkedIn, then older memory/context.
- If the user says a prior profile statement is wrong, stop using it immediately and correct the baseline before continuing. Do not preserve a title such as "lead" when the user says it is not formal; describe the actual reporting/ownership structure instead.
- Separate evidence classes explicitly: formal employment, personal project, prototype, planned architecture, completed, deployed, and production operation. Portfolio breadth is not equivalent to commercial production tenure.
- Do not infer framework experience from stated preferences. Treat tools such as LangGraph/CrewAI as interests unless a repository, resume artifact, or direct project evidence shows hands-on use.
- Map the evidenced skills to the JD. Note differentiators (e.g. bilingual Malay+English when JD lists Malay as "preferred").
- Use calibrated labels: "strong technical overlap" is not the same as "high overall fit." Overall fit must also account for seniority, formal experience duration, work authorization/relocation, and unverified requirements.
- Flag strategic mismatch: contributor/eval gig vs user's build/consulting trajectory.
- Be honest about over/under-qualification.

## Phase 6 — Strategic call
- Legit ≠ rush. Gate any commitment on the real pay rate.
- Don't restructure the user's roadmap around a side-stream contractor gig unless leverage is high.
- If applying: mirror JD language; lead with exact tools + bilingual + independent track record; ASK compensation / method / currency directly in the application — never accept blind.

## Verification
- Show fetched URLs + exact evidence (entity name, HQ, "no salary published on any of N role pages").
- Label every claim UNVERIFIED / PARTIAL / THEORETICAL where no direct proof exists.

## References
- `references/research-pattern.md` — curl + href-extract + pay-keyword parse recipe; Data Gap declaration template; notes on blocked job boards from this VPS.
