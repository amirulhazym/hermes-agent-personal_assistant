# Bidirectional Sync Mechanism — Hermes Agent (MarryJane / MJ)

> Phase 3 deliverable. Scaffold for three-way sync: VPS ↔ Windows/WSL2 ↔ GitHub.
> Jane (native VPS agent) = VERIFIER. OpenCode = EXECUTOR.
> Deployment of cron jobs / auto-push requires explicit user approval per AGENTS.md.

## Overview

| Direction | Method | Trigger | Security |
|-----------|--------|---------|----------|
| **VPS → WSL2** | rsync pull (WSL2 pulls from VPS) | User opens PC, runs pull script | SSH key auth, exclude .env/secrets |
| **WSL2 → VPS** | git push temp branch → VPS git pull | Explicit user action OR auto-cron (user must approve) | SSH key, no force push |
| **GitHub** | docs/code source of truth (main) | Temporary branches promoted to main only after tested approval | Standard GitHub auth |

## VPS → WSL2 (runtime state mirror)

### How it works
When the user opens their Windows PC and starts WSL2, run `pull-vps-to-wsl2.sh`.
This rsyncs the live Hermes state from VPS to a local WSL2 mirror, excluding
secrets, logs, sessions, and database caches.

### Excluded from sync (NEVER leave VPS)
- `.env`, `.env.bak`, `.env.*`
- `auth.json`
- `platforms/whatsapp/session/`, `platforms/telegram/session/`
- `logs/`, `cache/`
- `*.db`, `*.db-shm`, `*.db-wal`
- `gateway_state.json`, `processes.json`, `channel_directory.json`
- `__pycache__/`, `venv/`, `node_modules/`
- `cron/output/`, `cron/.tick.lock`, `cron/ticker_*`

### Included in sync (VPS → WSL2 local mirror ONLY — never commit/push these)
config.yaml, SOUL.md, memories/, scripts/, skills/, plugins/, hooks/, plans/,
cron/jobs.json, med-schedule.json, med-status.json, chain-state.json,
dexa_taper.json, med-supply.json, med-interactions.json, substitutions.json,
appointments.json

> ⚠️ The `med-*.json` / `chain-state.json` / `channel_directory.json` files above are
> HEALTH/PII data. They are mirrored locally for debugging only. They MUST NOT reach
> GitHub — `.gitignore` now excludes them. The PC `~/hermes-mirror/` is NOT a git repo;
> never copy these into `MJay/`.

### Pull script: `sync/pull-vps-to-wsl2.sh`
```bash
# Run from WSL2 terminal after PC starts
rsync -avz --delete \
  -e "ssh -i ~/.ssh/id_ed25519" \
  --exclude='.env' --exclude='.env.bak' --exclude='.env.*' \
  --exclude='auth.json' \
  --exclude='platforms/*/session/' \
  --exclude='logs/' --exclude='cache/' \
  --exclude='*.db' --exclude='*.db-shm' --exclude='*.db-wal' \
  --exclude='gateway_state.json' --exclude='processes.json' \
  --exclude='channel_directory.json' \
  --exclude='__pycache__/' --exclude='venv/' --exclude='node_modules/' \
  --exclude='cron/output/' --exclude='cron/.tick.lock' \
  --exclude='cron/ticker_heartbeat' --exclude='cron/ticker_last_success' \
  ubuntu@119.28.119.151:~/.hermes/ \
  ~/.hermes-mirror/
```

### Optional: Auto-trigger on PC start
Place a shortcut in `shell:startup` or add to `~/.bashrc` in WSL2.
User must approve before any automated deployment.

## PC → VPS (code/docs changes)

### How it works
OpenCode makes changes on local MJay repo → git commit to a temporary branch →
push to GitHub → VPS pulls from GitHub. Or rsync specific files directly.

### Git workflow (default path)
```bash
# On Windows (OpenCode or manual):
cd /mnt/f/AI\ Prep/OVIS/Hermes\ Agent/MJay/
git add -A
git commit -m "sync: <description>"
git push origin hermes-live

# On VPS (manual or cron):
cd ~/mjay
git pull origin hermes-live
```

### Direct rsync (for urgent config/script changes)
```bash
# From WSL2, push individual files:
scp -i ~/.ssh/id_ed25519 ~/.hermes/config.yaml ubuntu@119.28.119.151:~/.hermes/
scp -i ~/.ssh/id_ed25519 ~/.hermes/scripts/new_script.py ubuntu@119.28.119.151:~/.hermes/scripts/
```

## GitHub (source of truth)

### Branch strategy (owner-ratified workflow)
- **`main`** — the SOLE permanent source branch. Source of truth for application code and docs.
- **Temporary branches** — `rescue/*`, `integration/*`, `feat/*` — created only as safety/integration
  tooling and automatically removed after their work is tested and promoted to `main`.
- **Hermes works from clean source** — clean clone -> temporary branch -> tests -> `main`
  -> explicit deploy -> live verification. No agent pushes directly to `main`.

### What goes to GitHub
- MJay docs: PRD, PROGRESS, DECISIONS, RUNBOOK, AUDIT, AGENTS
- audit-prep/ files
- sync/ scripts and docs
- patches/ (source changes)
- integrations/, personas/, plugins/, config/

### What does NOT go to GitHub
- VPS runtime state (med-*.json, chain-state.json, etc.) — PII/health data
- `.env` secrets
- `platforms/` session data
- `logs/`, `cache/`, `*.db*`

## Jane Verifier Role
Jane (native VPS agent) checks daily:
- VPS config vs GitHub vs WSL2 mirror drift
- SOUL.md versions match across all 3
- Cron job parity
- Script file diffs
Alerts user via Telegram if any mismatch detected.

## Deployment Checklist (requires user "yes" for each)
- [ ] Enable cron on VPS for daily git push of docs to a temporary branch
- [ ] Enable cron on VPS for daily drift check (Jane verifier)
- [ ] Add Windows Startup shortcut for auto-pull on PC login
- [ ] Promote tested temporary branch to main (after audit fixes complete)

*End of sync mechanism doc. Do not deploy any cron/auto-script without explicit user approval.*
