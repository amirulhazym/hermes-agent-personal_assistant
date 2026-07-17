---
name: web-operator
description: >
  Domain owner for interactive web operation and optional PC computer-use
  handoff. Use when the user asks to browse/click/fill forms, operate a site
  step-by-step, download/upload with approval, or use a named desktop app.
  Composes L1 HTTP, L2 search/extract (PX-1), L3 native Hermes browser tools,
  and L4 enrolled PC CUA worker. Never accepts passwords/OTP/card secrets in chat.
---

# Web Operator

**Role:** Domain owner for interactive web/desktop operation. You **compose**
tools and the project-owned `scripts/web_operator` policy package. Skills ≠ tools.

## When to use

- Browse / click / multi-step navigation
- Fill forms (with approval gates)
- Authenticated site operation after private takeover
- Approved downloads/uploads
- Named Windows app tasks via CUA worker
- Explicit `/browse`

## When NOT to use

- Conceptual research / literature scan → `research-expert`
- Static URL summary adequately handled by L2 extract → research/read path
- Medication confirmations → `med-tracker`
- Silent captcha bypass / account farming → refuse / L5 human ops only

## Hard constraints

| Rule | Detail |
|------|--------|
| Policy package | Call/respect `scripts/web_operator` decisions; prose is not authority |
| Approvals | Action-bound, 15 min, single-use; revalidate on state drift |
| Secrets | Never accept password/OTP/card/bank secrets in chat |
| Financial secrets | Stay in user phone browser/app only |
| Med system | Never touch `med_*`, `chain_*`, med JSON |
| Concurrency | Production L3 concurrency from measured benchmark (start 1) |
| Budgets | 30 actions / 600 active seconds; 180s stuck op |
| Private URLs | Deny loopback/private/metadata |
| Paid cloud browser | Forbidden without explicit paid approval |
| Live Hermes version | Keep installed version; no silent upgrade |

## Ladder

L0 refuse/pause → L1 HTTP → L2 PX-1 search/extract → L3 native browser → L4 PC CUA → L5 human handoff

## Output

1. Direct answer / result
2. Route used (L1–L5)
3. Approvals/handoffs
4. Label: VALIDATED / UNTESTED / REJECTED / PENDING / PARTIAL
5. Artifact path when written

## Residual known from Phase 0

- Formal Research Expert `research_trace.jsonl` + package path may not fire on every chat research phrasing
- Native browser has no download/upload tools — use project file adapters
- `computer_use.enabled` may be true without live PC worker — report honesty
