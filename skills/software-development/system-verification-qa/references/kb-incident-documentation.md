# KB Incident Documentation Pattern

## The Four-Table Structure

When documenting a multi-finding investigation or incident knowledge base, use this structured table format with cross-referencing IDs. Proven in session 2026-07-15 (HERMES-INCIDENT-KNOWLEDGE-BASE-v3.docx).

## Table 1: Problem Register (P-XXX)

| ID | Category | Problem | Severity | Status | Evidence | Impact |
|---|---|---|---|---|---|---|
| P-001 | Provider | hy3-free returns HTTP403 code30001 | Critical | Open | Runtime/API probe | Model unusable |
| P-002 | Runtime | Silent fallback masks actual effective model | Critical | Confirmed | Source + logs | User sees stored model, not runtime model |
| P-003 | UX | Fallback transparency weak | High | Open | Architecture review | User cannot see model substitution |

**Severity:** Critical / High / Medium / Low  
**Status:** Open / Confirmed / External/Open / Partial  
**Evidence:** What type of proof supports this finding

## Table 2: Solution Register (S-XXX)

| ID | Related Problems | Solution Idea | Source | Status |
|---|---|---|---|---|
| S-001 | P-001 | Add balance/billing credit to workspace | Hermes suggestion | Proposed |
| S-002 | P-001,P-013 | Expose effective runtime model explicitly in status | ChatGPT recommendation | Strong recommendation |

**Source:** Who proposed this (Hermes suggestion, ChatGPT recommendation, Joint recommendation, Engineering rule, Audit rule)  
**Status:** Proposed / Strong recommendation / Pending verification / Available/verified / Recommended / Implemented

## Table 3: Action / Decision Register (A-XXX)

| Action ID | Problem IDs | Solution IDs | Decision / Action Taken | Result |
|---|---|---|---|---|
| A-001 | P-001 | S-001,S-002 | Live API probes against hy3-free | HTTP403 code30001 reproduced repeatedly |
| A-002 | P-002 | S-004,S-010 | Reviewed fallback logs and runtime mutation source | Silent fallback confirmed; model substitution is real |

**Cross-reference:** Each action links back to the problems it addresses and the solutions it evaluates.  
**Result:** What actually happened when the action was taken.

## Table 4: Evidence Register (E-XXX)

| Evidence ID | Type | Content / Finding |
|---|---|---|
| E-001 | Runtime query | Five most recent WhatsApp sessions showed deepseek-v4-flash-free |
| E-002 | Session DB | 432 sessions: 26 NULL-model, 406 with model set |
| E-003 | Fallback code | agent.model = fb_model, agent.provider = fb_provider |

**Type:** Runtime query / Session DB / Fallback code / Status code / Persistence code / DB semantics / Update path / Reasoning config / Reasoning whitelist / Probe result / User-visible logs / Code path separation / State semantics / Audit quality

## Cross-Reference Naming Convention

- **P-001** to P-NNN = Problems
- **S-001** to S-NNN = Solutions  
- **A-001** to A-NNN = Actions / Decisions
- **E-001** to E-NNN = Evidence items
- **AF-001** to AF-NNN = Architecture Findings (factual descriptions, not problems)
- **RCA-001** to RCA-NNN = Root Cause Analyses

## When to use this format

- Any investigation that produces 5+ distinct findings
- When the user is building a Knowledge Base for an incident or audit
- When findings span multiple categories (problems, solutions, actions, evidence)
- When the user needs to track what's confirmed, what's inferred, and what's external

## When NOT to use it

- Quick Q&A sessions (1-3 findings)
- Simple config fixes or one-time corrections
- When the user explicitly says "jangan buat document, just explain"
