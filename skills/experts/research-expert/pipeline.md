# Research Expert — Staged Pipeline

Hard defaults: **depth=1**, **max=3 parallel children** per stage.

## Stage 1 — Plan

Produce a short plan (internal or user-visible for large tasks):

```yaml
question: "<user question>"
scope: "<in / out of scope>"
success_criteria:
  - "..."
max_sources: 6
queries:
  - "<q1>"
  - "<q2>"
  - "<q3>"   # ≤3 primary queries first wave
priority_domains: []   # optional allowlist
exclude: []            # optional
```

Do not start search until plan exists (even if only 5 lines).

## Stage 2 — Search

- Tool: `web_search` (backend: **search-cascade** = Tavily → DDGS)
- Wave size ≤3 queries
- Capture per hit: title, url, snippet, backend tag if present
- If wave 1 weak: one more wave (≤3), then stop (no infinite loops)

## Stage 3 — Extract

- Select top URLs (≤3 per batch, depth 1)
- Tool: `web_extract` / hybrid-web
- Prefer: primary docs, official blogs, papers, standards
- Store: url, title, backend (trafilatura|crawl4ai|playwright), content excerpt

## Stage 4 — Verify

Apply rules from `references/verification.md`:

For each material claim:

1. Supported by ≥1 extracted source?  
2. Date/freshness acceptable for the domain? (see verification.md §2)  
3. Contradicted by another source? (see verification.md §3)  
4. Source passes quality gate? (see verification.md §4)  
5. Label: VALIDATED | UNTESTED | REJECTED | PENDING

Drop or demote sources that are pure SEO spam or empty extract.

### Contradictions
If two sources disagree on a material claim:
- Surface both, label CONTRADICTED
- Confidence → low
- Do not silently pick one

### Self-audit
Before moving to Synthesize, run verification.md §6 checklist:
- Count VALIDATED vs UNTESTED — if UNTESTED > VALIDATED, flag in report
- Spot-check 2 random claims against source excerpts
- No fabricated URLs/titles/numbers → if found, discard and re-do

## Stage 5 — Synthesize

Structure:

1. Answer  
2. Evidence table (claim → source → label)  
3. Confidence (high/medium/low) + gaps  
4. Optional next research steps

## Stage 6 — Artifact package

Pass the completed Stage 1–5 result to the deterministic writer, which writes files under:

`~/.hermes/research/artifacts/YYYY-MM-DD-<slug>/`

Required files: see `artifact-format.md`. The standard runner is:

```bash
python3 ~/.hermes/scripts/research_stage6.py < stage6-payload.json
```

Treat a non-zero exit, invalid JSON response, missing `artifact_dir`, or missing
`trace_path` as a failed pipeline. Do not claim a completed research package until
both returned paths exist.

Write research trace log entry at:

`~/.hermes/logs/research_trace.jsonl`

Format: see `references/trace-log.md`. The runner appends one JSON line per pipeline run.

## Parallelism sketch

```
Stage N:  up to 3 parallel tool calls (depth 1)
          → write intermediate notes to artifact dir
Stage N+1: read artifacts only (no sibling chat dependency)
```

Never spawn deep delegate trees. Never touch med state.
