# Research Trace Log Format (Fasa 3)

Goal: auditable, machine-parseable record of every research pipeline run — analogous
to med_chain_trace for medication workflows.

---

## File

```
~/.hermes/logs/research_trace.jsonl
```

One JSON object per line. Append-only. Never delete.

## Schema

```json
{
  "schema": "research-trace/v1",
  "run_id": "uuid4",
  "started_utc": "2026-07-14T10:00:00Z",
  "completed_utc": "2026-07-14T10:03:45Z",
  "question": "user question text (first 200 chars)",
  "slug": "YYYY-MM-DD-short-slug",
  "pipeline_stages": ["plan", "search", "extract", "verify", "synthesize"],
  "stage_log": [
    {
      "stage": "plan",
      "started_utc": "...",
      "completed_utc": "...",
      "duration_ms": 1200,
      "max_sources_target": 6,
      "query_count": 2,
      "queries": ["q1", "q2"],
      "errors": []
    },
    {
      "stage": "search",
      "started_utc": "...",
      "completed_utc": "...",
      "duration_ms": 3200,
      "query_count": 2,
      "total_hits": 12,
      "backends_used": ["tavily"],
      "fallback_used": false,
      "errors": []
    },
    {
      "stage": "extract",
      "started_utc": "...",
      "completed_utc": "...",
      "duration_ms": 4800,
      "url_count": 5,
      "success_count": 4,
      "fail_count": 1,
      "backends_used": ["trafilatura", "crawl4ai"],
      "errors": [{"url": "...", "error": "timeout"}]
    },
    {
      "stage": "verify",
      "started_utc": "...",
      "completed_utc": "...",
      "duration_ms": 1500,
      "claims_total": 3,
      "validated": 2,
      "untested": 1,
      "rejected": 0,
      "pending": 0,
      "contradictions": 0,
      "stale_warnings": 0
    },
    {
      "stage": "synthesize",
      "started_utc": "...",
      "completed_utc": "...",
      "duration_ms": 2200,
      "confidence": "medium",
      "output_artifact": "~/.hermes/research/artifacts/YYYY-MM-DD-slug/report.md"
    }
  ],
  "outcome": {
    "confidence": "medium",
    "total_sources": 4,
    "labels": {"validated": 2, "untested": 1, "rejected": 0, "pending": 0},
    "contradictions_detected": 0,
    "backend_summary": {
      "search": ["tavily"],
      "extract": ["trafilatura", "crawl4ai"],
      "fallback_triggered": false
    }
  },
  "med_touch": false,
  "soul_grounding_violations": 0
}
```

## Writing Conventions

1. Write one entry per completed research pipeline run.
2. If a pipeline is abandoned mid-run, write the entry anyway with `"abandoned": true` and the last successful stage.
3. `stage_log[].errors` is always an array — empty if no errors.
4. `duration_ms` for each stage.
5. `soul_grounding_violations` = count of SOUL.md rule violations detected by self-audit (see verification.md §6).

## Querying (common patterns)

```bash
# Last 5 research runs
tail -5 ~/.hermes/logs/research_trace.jsonl | python -m json.tool

# Runs with contradictions
grep '"contradictions":' ~/.hermes/logs/research_trace.jsonl | grep -v ': 0'

# Confidence distribution
grep -Po '"confidence":\s*"\K[^"]+' ~/.hermes/logs/research_trace.jsonl | sort | uniq -c

# Failed extract URLs (last 20 runs)
tail -20 ~/.hermes/logs/research_trace.jsonl | grep -Po '"error":\s*"\K[^"]+'

# Average source count over time
python -c "
import json, sys
counts = []
for line in sys.stdin:
    d = json.loads(line)
    counts.append(d.get('outcome',{}).get('total_sources',0))
if counts:
    print(f'avg sources: {sum(counts)/len(counts):.1f} over {len(counts)} runs')
" < ~/.hermes/logs/research_trace.jsonl
```

## Rotation / Limits

- Max 10,000 lines (~5MB). If exceeded, rotate to `research_trace.jsonl.1` (keep 1 backup).
- Rotation cron: weekly (add to existing logrotate config).

## Integration

- The trace log is written by the research-expert skill when executing Stage 6 (artifact write).
- It is read by pipeline audit tools and the Fasa 5 quality-vs-baseline comparator.
- It is **not** required for Hermes to respond — it is an observability layer.
