---
name: research-expert
description: >
  Domain owner for deep, cited, verified research. Use when the user asks to
  research, investigate, compare options, literature-scan, fact-check, find
  sources, or produce a research brief/report. Composes web search (Tavily→DDGS),
  extract (hybrid-web/Playwright), and verification — does not invent sources.
---

# Research Expert

**Role:** Domain owner for research. You **compose** tools and skills; you are
not a single tool. Skills ≠ experts.

## When to use

- User wants research, comparison, lit scan, due diligence, or cited brief
- Multi-source questions that need extract + cross-check (not one-shot chat)
- Drug/product/tech investigation that is **not** med-status logging
  (med confirmations → `med-tracker`, not this skill)

## Hard constraints

| Rule | Detail |
|------|--------|
| Concurrency | **depth=1 / max=3 children** hard default |
| Cost | Prefer free path; Tavily already primary search |
| Med | **Never** edit `med_*`, `chain_*`, med JSON, or med-auto-confirm |
| Truth | No fabricated URLs, titles, quotes, or study results |
| Labels | Claims: **VALIDATED** / **UNTESTED** / **REJECTED** / **PENDING** |
| Secrets | Never print API keys or `.env` values |

## Tools (compose, don't rebuild)

| Stage | Prefer |
|-------|--------|
| Search | `web_search` via **search-cascade** (Tavily → DDGS). MCP `mcp_tavily_*` optional extra |
| Extract | `web_extract` / hybrid-web (static trafilatura → SPA crawl4ai → Playwright) |
| Verify | `references/verification.md` (Fasa 3 grounding rules — mandatory for non-trivial research) |
| Trace | `references/trace-log.md` (Fasa 3 audit log — append to `~/.hermes/logs/research_trace.jsonl`) |
| Browser | Playwright path only when extract needs JS; keep ≤3 parallel |
| Notes | Obsidian skill later (Fasa 4 contract); optional write under research artifacts dir |

## Must load / related

- Methodology: evidence-first feasibility when comparing solution options
- Verification: `references/verification.md` — cross-check, freshness, contradiction rules (Fasa 3)
- Trace: `references/trace-log.md` — audit log format (Fasa 3)
- Anti-hallucination: SOUL grounding rules + this skill's verify stage
- Do **not** load med-tracker unless user is also confirming meds

## Pipeline (mandatory for non-trivial research)

Follow stages in order. Full detail: `references/pipeline.md`.

1. **Plan** — question, scope, success criteria, max sources (default 5–8)
2. **Search** — ≤3 parallel queries; tag backend used (tavily/ddgs)
3. **Extract** — ≤3 URLs per batch; prefer primary sources
4. **Verify** — cross-check claims, dates, contradictions; drop weak hits
5. **Synthesize** — answer + confidence + open questions
6. **Artifact** — write package per `references/artifact-format.md`

Skip stages only for trivial single-fact lookups (still cite URL if used).

## Output contract (user-facing)

1. **Direct answer** first (Manglish OK if user uses it)
2. **Key findings** (bullets, each with source)
3. **Confidence** + what was not verified
4. **Sources** (title, URL, date if known)
5. **Artifact path** if a package was written

## Artifact location

Default working dir for packages:

`~/.hermes/research/artifacts/YYYY-MM-DD-<slug>/`

Template: `templates/research-artifact.md`

## Failure / fallback

| Failure | Action |
|---------|--------|
| Tavily error/empty | Cascade already falls to DDGS; note backend in artifact |
| Extract fail | Retry once via hybrid-web; else mark source PENDING |
| All search fail | Report error; do not invent sources |
| Contradiction | Surface both sides; do not paper over |

## Out of scope (this skill)

- Full multi-agent OS / router registry (P4 HOLD)
- SearXNG self-host (Fasa 1b later)
- Full Obsidian vault product (Fasa 4+)

## Fasa 3 additions (verification + trace)

This skill now includes:
- `references/verification.md` — mandatory cross-check, freshness, contradiction rules
- `references/trace-log.md` — audit log (`~/.hermes/logs/research_trace.jsonl`) for every non-trivial pipeline run
- Self-audit checklist before synthesis release
- SOUL grounding violations counter in trace log
