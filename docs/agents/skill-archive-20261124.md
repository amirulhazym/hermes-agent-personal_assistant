# Skill archive — 2026-11-24

Owner instruction: remove bundles 9-10, 15-18, 23-25, 33-39, and 55-60 of the
60-candidate list (55-60 only if confirmed duplicate/redundant).

Basis for candidacy: `state.db` — 170 skills indexed, only **54** loaded in the
30 days before 2026-11-24.

Live action: 20 directories moved from `~/.hermes/skills/` to
`~/.hermes/skills-archive/2026-11-24/` with `manifest.json` and a per-skill
`ORIGINAL_PATH.txt`. Indexed skills 170 -> 150. Nothing deleted; restore by
moving the directory back.

## Removed (20)

| # | Bundle | Reason |
|---|---|---|
| 9 | creative/pretext | 0 loads; DOM-free text demo |
| 10 | creative/touchdesigner-mcp | 0 loads; needs desktop TouchDesigner |
| 15 | mlops/evaluation/weights-and-biases | 0 loads; no experiment tracking here |
| 16 | mlops/models/audiocraft | 0 loads; audio generation unused |
| 17 | mlops/models/segment-anything | 0 loads; no segmentation work |
| 18 | data-science/jupyter-live-kernel | 0 loads; terminal + execute_code covers it |
| 23 | productivity/box | 0 loads; Drive/Git used instead |
| 24 | productivity/nano-pdf | 0 loads |
| 25 | productivity/petdex | 0 loads; mascot, not work function |
| 33 | research/polymarket | 0 loads |
| 34 | research/blogwatcher | 0 loads |
| 35 | research/job-role-research | 0 loads |
| 36 | research/malaysia-telco-research | 0 loads |
| 37 | research/research-paper-writing | 0 loads |
| 38 | research/web-research-benchmark | 0 loads |
| 39 | research/web-source-verification | 0 loads; covered by research-expert verification stage |
| 56 | operator/hermes-session-troubleshooting | duplicate: same root cause + same routing-backfill fix as hermes-session-diagnostics (14 KB, more complete) and hermes-session-store-repair |
| 57 | software-development/github | duplicate: 2.4 KB router into the github/ bundle that is already indexed |
| 58 | software-development/tdd | duplicate: subset of test-driven-development (10.3 KB, Iron Law + RGR + red flags) |
| 59 | productivity/grill-me | duplicate: 147-byte stub whose body is "Run a `/grilling` session" |

## Kept from the 55-60 group (evidence contradicted the candidate label)

- `hermes/hermes-session-store-repair` — carries a runtime-drift check the other two lack.
- `productivity/grilling` — the substantive skill; `grill-me` was the stub, so the stub went.
- `software-development/external-agent-handoff` — **not** a duplicate of `productivity/handoff`:
  16 KB audit-handoff contract vs 1.2 KB session-handoff note, different purpose.

## Restore

```bash
mv ~/.hermes/skills-archive/2026-11-24/<category>/<name> ~/.hermes/skills/<category>/
```
