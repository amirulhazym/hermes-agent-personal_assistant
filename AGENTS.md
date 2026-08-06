# AGENTS.md — Hermes Agent Operator Constitution (v2)

> Always-on project policy. Loaded as project context whenever an agent works
> inside this repository or the live runtime it governs. This file is the
> canonical, always-present safety contract; operational procedures live in
> `skills/operator/*` (on-demand); deterministic enforcement lives in
> `scripts/guard/*` and CI. If a skill or procedure conflicts with this file,
> this file wins.

## 1. Topology — what is what

| Layer | Path | Role |
|---|---|---|
| GitHub `main` | source of truth | Sole permanent branch; release lineage only |
| Clean source clone | `/home/ubuntu/hermes-agent-personal_assistant-work` (VPS), PC clone | Where all work starts; never the live runtime |
| Live runtime | `/home/ubuntu/.hermes` | Runtime state, config, DBs, sessions, logs — never a Git worktree for application source |
| Nested upstream | `/home/ubuntu/.hermes/hermes-agent` | Upstream Hermes clone + VPS overlays; never merge its Git history into this repo |
| Archived donors | `~/mjay`, `~/.hermes/.git` (hermes-local), tags `archive/*`, `rescue/*` | Preservation only; not application source |

The running gateway executes from `/home/ubuntu/.hermes` (runtime) +
`/home/ubuntu/.hermes/hermes-agent` (code). Source-managed files reach the
runtime **only** through an explicit deployment manifest (see `docs/reconciliation/gate4-deployment-manifest.md`).

## 2. Branch policy

1. `main` is the **only permanent branch**.
2. All work starts from a **clean source clone** at `main`.
3. Never commit from `~/.hermes` or the nested upstream clone.
4. Temporary branches (`feat/*`, `docs/*`, `release/*-candidate`) are created
   automatically and deleted automatically after promotion or explicit abort.
5. No force-push, no rebase of published history, no deletion of
   `release/*`, `archive/*` or `rescue/*` tags.

## 3. Approval model — exactly one approval gate

- **Docs-only changes** (allowlist below) may be committed, tested, promoted to
  `main` and pushed **without repeated approval**, after verification:
  allowlist membership + link validation + secret scan + tests pass.
- **All other changes** (code, config, medical logic, skills, governance,
  deployment artifacts) require **one** approval for the whole release:
  `APPROVE RELEASE <exact-sha>`.
  No separate approval for `git add`, commit, push, or deploy steps — the single
  release approval covers the tested release candidate end-to-end.

### Docs-only allowlist
- `docs/**` (except deployment manifests and reconciliation ledgers under `docs/reconciliation/` which are governance artifacts)
- `README.md`, `PROGRESS.md`, `DECISIONS.md`, `RUNBOOK.md`, `CHANGELOG*`, `*.md` at repo root (except governance files below)

### Never docs-only (always release-gated)
`AGENTS.md`, `skills/**`, `.github/**`, `config/**`, `scripts/**`, `hooks/**`,
`patches/**`, deployment manifests, `sync/**`, `windows/**`, `tests/**`,
persona files, `operations/**`.

## 4. Secrets, PII and runtime state — never in Git

The following never enter Git, never leave the trusted device unencrypted, and
are covered by Gate 1 encrypted preservation:

- `.env*`, API keys, OAuth tokens, `auth.json`, private keys, credential exports
- WhatsApp/Telegram credentials and sessions
- `state.db` and all SQLite DB/WAL/SHM files
- `config.yaml` containing real values (sanitized templates only)
- `cron/jobs.json` containing live values
- `med-status.json`, `chain-state.json`, `med-*.json` medical state, holds, logs
- `memories/*` personal data
- logs, caches, `.pyc`, `__pycache__`, generated outputs, backup directories

Runtime secrets and state remain runtime-only. Reproducible behaviour is
documented via sanitized templates and deployment manifests with placeholders.

## 5. Deployment rules

1. Deployment happens **only** via an exact source→destination manifest
   (per-file SHA-256, explicit paths inside `/home/ubuntu/.hermes`).
2. No wildcard, no recursive directory sync, no delete action in manifests.
3. Before deployment: record live destination hashes; create a mode-700
   timestamped rollback snapshot (backup + rollback script + crontab copy).
4. Install atomically (temp file in destination dir + rename); preserve modes.
5. Arm a detached watchdog (restores gateway + crontab) and keep standby SSH
   before any gateway stop.
6. After deployment: verify all deployed hashes, gateway, WhatsApp + Telegram,
   crontab, journal, med-chain smoke, and isolated temp-HOME tests.
7. Owner performs benign E2E on WhatsApp and Telegram (reply within 5 min).
8. Any failure → restore from rollback snapshot, restart, verify, HOLD.

## 6. Live runtime guards

- Never edit live files directly for source changes; always source → test →
  release → deploy manifest.
- Never stop/restart the gateway without the watchdog + standby + rollback
  protections above and a heads-up.
- Never modify `~/.hermes` config, cron jobs, memories or med state via Git.
- `~/mjay` and `~/.hermes/.git` are archived donors: read-only.

## 7. Cross-channel operation ledger

Before starting long-running work, check the shared operation ledger
(`operations/ledger.json`) so Telegram and WhatsApp sessions never duplicate
the same task. Attach the session to the active task; on completion update the
ledger. Do not re-run an audit or task already recorded as active or complete.

## 8. Self-modification

Modification of `AGENTS.md`, `skills/**`, `.github/**`, guard scripts, or this
repository's own governance requires release approval
(`APPROVE RELEASE <sha>`). Staged skill changes are submitted for approval;
unrestricted self-editing is never allowed.

## 9. Safety floor (always applies)

- Stop and ask before: destructive/irreversible actions, credential access,
  paid services, deployment, external messages, public posts, commits/pushes
  outside the approved release flow.
- Never print, commit, upload or transmit secrets.
- Preservation artifacts (Gate 1, predeploy rollback snapshots) are never
  deleted without separate explicit approval.
