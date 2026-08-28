# Deployment & updater truth — verified 2026-08-12 (v0.20.0 live tree)

Source: bounded live-truth pass during the /resume + WhatsApp + update-safety planning session.
All facts LIVE-VERIFIED against `/home/ubuntu/.hermes/hermes-agent` (systemd user unit,
ExecStart `venv/bin/python -m hermes_cli.main gateway run`). Companion plan:
`~/.hermes/plans/2026-08-12-update-safe-execution-plan.md`.

## Remote layout is INVERTED on this box — verify before claiming update semantics

- `origin` = `https://github.com/NousResearch/hermes-agent.git` — the CANONICAL upstream repo
  (inverted from the normal fork convention).
- `origin-vps` = SSH personal fork (`amirulhazym/hermes-agent-personal_assistant`).
- `upstream` remote: does NOT exist (the updater's fork layout expects it).

## Updater behavior (from `hermes_cli/update_cmd.py` source)

- Default `hermes update`: probes for an `upstream` remote; if present fetches `upstream/main`,
  else falls back to `origin/main`, then `git pull --ff-only <that>/main`. On this box that means
  plain `hermes update` pulls NousResearch main directly and autostashes local changes
  (`non_interactive_local_changes='stash'`, `pre_update_backup=False`, `backup_keep=5`).
- `hermes update --branch X`: fetches `origin/<X>` ONLY (never upstream); merge
  `--ff-only origin/<X>`; fallback `reset --hard origin/<X>`.
- `updates.branch` config key: **NOT supported in v0.20.0** (grep-confirmed) — in-band `/update`
  spawns `hermes update --gateway` detached via setsid with no branch passthrough
  (`gateway/slash_commands.py` `_handle_update_command` ~L5584).
- Post-pull guards exist: syntax validation + critical-module import validation + auto-rollback
  via captured head SHA (`_capture_head_sha`).

## Update-safe architecture decision (Option 2, ratified in plan)

Live checkout should track a **personal release branch on the FORK**, promoted via
`hermes update --branch <release>`:

1. Swap remotes (git config, not source): `origin` → fork, add `upstream` → NousResearch;
   remove/alias `origin-vps` (dedupe).
2. Release branch `release/personal-0.20.x` on the fork = live's checked-out branch; `main`
   keeps tracking fork main.
3. Small core patch: honor a new `updates.branch` config key so `/update` and plain
   `hermes update` default to the release branch (without it `/update` would pull fork main —
   acceptable but loses SHA pinning).
4. Upstream intake lives ONLY in the worktree: `git fetch upstream main` → rebase release
   branch → contract tests + targeted suite + bounded critical suite → push fork → live ff only.
5. Live promotion requires a CLEAN tree (refuse otherwise); record candidate SHA + previous
   SHA as rollback boundary; post-deploy clean-tree verification.
6. Patch retirement: during upstream rebase check whether upstream already contains an
   equivalent fix; drop the local patch but keep its contract test.

Why NOT "personal commits on main" (Option 1): every upstream pull becomes non-fast-forward
(fixes on main diverge) → `hermes update` hard-fails; autosync would bypass any test gate.
Undo boundary: current live = `a31be48030` (clean), rollback = checkout previous release SHA
+ clean restart (see clean-restart-gateway skill).

## State DB facts (re-affirmed)

- `~/.hermes/state.db` is the ONLY meaningful DB. `~/.hermes/sessions.db` = empty shell;
  `~/.hermes/sessions/default.db` and `~/.hermes/sessions.json` do NOT exist.
- `sessions` table columns use `last_activity_at`, NOT `last_active`.
- `end_reason` values seen in production: `session_reset`, `compression`, `cron_complete`,
  `session_switch`, `orphaned_compression`, `idle`, NULL. Only `compression` is a legitimate
  resume-continuation boundary (see resume-session-redirect-bug.md).
- Routing index: `~/.hermes/sessions/sessions.json` keyed by channel, e.g.
  `agent:main:telegram:dm:<chat-id>`.