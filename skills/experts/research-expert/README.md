# Research Expert (PX-1 Fasa 2)

Hermes skill pack: deep research domain owner.

## Install (VPS)

```bash
mkdir -p ~/.hermes/skills/experts
cp -a skills/experts/research-expert ~/.hermes/skills/experts/
mkdir -p ~/.hermes/research/artifacts
cp scripts/research_stage6.py ~/.hermes/scripts/research_stage6.py
```

## Trigger

- Skill description keywords (research, investigate, sources, …)
- Optional: `skill-trigger` patterns → `experts/research-expert` or `research-expert`

## Stage 6 writer

The skill's final packaging step is deterministic rather than model-dependent. Deploy
`scripts/research_stage6.py` to `~/.hermes/scripts/research_stage6.py`; the skill
passes the completed Stage 1–5 JSON payload to it. The runner creates the standard
artifact package and appends `~/.hermes/logs/research_trace.jsonl`.

## Related

- Search: `search-cascade` plugin (Tavily → DDGS)
- Extract: `hybrid-web` plugin
- Plan: `PX1-RESEARCH-TRACK-PLAN.md` Fasa 2
