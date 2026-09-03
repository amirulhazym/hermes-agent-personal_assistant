# Hermes Agent (VPS) — Git Workflow

> Branch strategy for the agent writing to MJay docs from the VPS.

## Branch Strategy

- **`main`** — human-reviewed, stable. Only you (the human) merge into main.
- **`hermes-live`** — agent-pushed, working branch. The agent on the VPS writes here.

## Workflow

```
Windows MJay/
    ├── (you work here, edit PROGRESS/DECISIONS/RUNBOOK)
    ├── git push origin main
    ↓
GitHub repo
    ↓ (you or cron syncs)
VPS ~/mjay/  (hermes-live branch)
    ├── (agent writes here: status updates, cron results, daily summaries)
    ├── git push origin hermes-live
    ↓
GitHub PR (hermes-live → main)
    ├── (you review on phone via GitHub mobile)
    ├── merge to main
```

## Daily Cycle

1. **Morning (07:00)**: Morning Briefing fires → agent updates `PROGRESS.md` with overnight status
2. **Throughout day**: Agent records notable events in `DECISIONS.md`
3. **Evening (21:00)**: Evening Check-in → agent updates `RUNBOOK.md` with ops notes
4. **Manual**: User reviews `hermes-live` branch on phone, merges to `main` via GitHub mobile

## Files Agent Can Edit (hermes-live)

- `PROGRESS.md` — append-only daily log
- `DECISIONS.md` — append decisions with rationale
- `RUNBOOK.md` — append ops notes, not rewrite existing sections
- `docs/superpowers/specs/*.md` — create new audit/spec docs

## Files Agent CANNOT Edit (human-only)

- `PRD.md` — product requirements
- `AGENTS.md` — agent rules (read-only for the agent)
- `RUNBOOK.md` Section 1-11 (existing operational sections)

## Security

- No secrets in git (.env excluded by .gitignore)
- No session data in git
- No logs in git
- VPS branch `hermes-live` is a draft — never auto-merge to main

## Setup Commands

```bash
# Already done (Step 1 of post-migration plan):
cd ~/
git clone https://github.com/amirulhazym/hermes-agent-personal_assistant.git mjay
cd mjay
git config user.email "hermes@amirulhazym.framer.ai"
git config user.name "Hermes Agent (VPS)"
git checkout -b hermes-live

# Daily push (cron, 21:00):
cd ~/mjay
git add -A
git commit -m "hermes: daily status update $(date +%Y-%m-%d)"
git push origin hermes-live
```

## Conflict Resolution

If the user and agent both edit the same file:
1. Agent's edit wins on `hermes-live`
2. User's edit on `main` triggers a merge conflict
3. User resolves via GitHub PR
