# Manifest Coverage Map — v3 Source Coverage Manifest

> **Purpose:** Faster diagnosis of guard false-positives. This document maps which directories are tracked by `docs/reconciliation/v3-source-coverage-manifest.json`, which are intentionally untracked, and which exist on disk but fall outside manifest scope.
>
> **Manifest:** `docs/reconciliation/v3-source-coverage-manifest.json` · **Base SHA:** `13baa13950223c090a9fc97e31baa748874c0edf` · **Entries:** 239 (156 `runtime-deploy`, 83 `source-only`) · **Generated:** 2026-08-20
>
> **Related:** `docs/reconciliation/hermes-runtime-source-lock.json` (runtime authority), `docs/reconciliation/hermes-runtime-tree-manifest.json`, `scripts/guard/manifest_recompute.py`, `scripts/guard/ci-base-sha.py`, `.gitignore`

---

## 1. Manifest Role and Scope

The v3 manifest is **non-authoritative for the Hermes runtime** — it is an application-source coverage ledger. The runtime authority is `hermes-runtime-source-lock.json`.

Each entry records:

| Field | Meaning |
|---|---|
| `source` | Repo-relative path of the source file |
| `source_sha256` | SHA-256 of the file at `base_main_sha` |
| `kind` | `runtime-deploy` — file is deployed to `~/.hermes` on the VPS · `source-only` — versioned in Git but not deployed to runtime |
| `destination` | Absolute VPS path for `runtime-deploy`, `null` for `source-only` |

**Invariant verified on 2026-08-20:** Every manifest entry is a `git ls-files` tracked file (0 orphan entries). The manifest covers 239 / 480 tracked files (49.8%).

---

## 2. Coverage by Top-Level Prefix

### 2.1 Entries per prefix

| Prefix | Total | `runtime-deploy` | `source-only` | Tracked on disk | Coverage |
|---|---|---|---|---|---|
| `skills/` | 101 | 76 | 25 | 112 | 90% |
| `scripts/` | 18 | 18 | 0 | 113 | 16% |
| `tests/` | 29 | 0 | 29 | 31 | 94% |
| `plugins/` | 29 | 29 | 0 | 32 | 91% |
| `agents/` | 26 | 26 | 0 | 26 | 100% |
| `hooks/` | 7 | 7 | 0 | 10 | 70% |
| `docs/` | 4 | 0 | 4 | 41 | 10% |
| `agent/` | 3 | 0 | 3 | 3 | 100% |
| `hermes_cli/` | 3 | 0 | 3 | 3 | 100% |
| `persona/` | 3 | 0 | 3 | 3 | 100% |
| `operations/` | 3 | 0 | 3 | 4 | 75% |
| `config/` | 1 | 0 | 1 | 3 | 33% |
| `gateway/` | 1 | 0 | 1 | 1 | 100% |
| `locales/` | 1 | 0 | 1 | 1 | 100% |
| `patches/` | 1 | 0 | 1 | 8 | 13% |
| `optional-skills/` | 1 | 0 | 1 | 1 | 100% |
| `hermes_state.py` | 1 | 0 | 1 | 1 | 100% |
| `.github/` | 1 | 0 | 1 | 1 | 100% |
| `AGENTS.md` | 1 | 0 | 1 | 1 | 100% |
| `README.md` | 1 | 0 | 1 | 1 | 100% |
| `PRD.md` / `PROGRESS.md` / `DECISIONS.md` / `RUNBOOK.md` | 4 | 0 | 4 | 4 | 100% |

### 2.2 Second-level breakdown (where it matters)

| Prefix | Entries | Notes |
|---|---|---|
| `agents/account-expert` | 26 | All runtime-deploy (reference, scripts/archive, tools/grok-register, tools/tavily-signup) |
| `plugins/lightclawbot` | 16 | |
| `plugins/model-providers` | 5 | |
| `plugins/hybrid-web` | 3 | |
| `plugins/google-workspace-commands` | 2 | |
| `plugins/search-cascade` | 3 | Not detailed above; included in 29 |
| `hooks/med-auto-confirm` | 3 | |
| `hooks/hello-world` | 2 | |
| `hooks/skill-trigger` | 2 | |
| `skills/med-tracker` | 41 | Largest skill; dominates coverage |
| `skills/software-development` | 21 | |
| `skills/devops` | 14 | |
| `skills/research` | 9 | |
| `skills/productivity` | 8 | |
| `skills/operator` | 4 | |
| `skills/computer-use` | 1 | |
| `skills/i-have-adhd` | 1 | |
| `skills/reference` | 2 | |
| `scripts/guard` | 5 | Only guard subset is in manifest |
| `docs/reconciliation` | 4 | `v3-config-schema-delta.md`, `v3-source-closure-ledger.*`, `v3-supersedes-gate4.md` |
| `tests/agent` | 10 | |
| `tests/hermes_cli` | 6 | |
| `tests/providers` | 4 | |

### 2.3 File-extension profile

| Extension | Count | Notes |
|---|---|---|
| `.md` | 110 | Skills and docs heavy |
| `.py` | 90 | |
| `.yaml` | 18 | Skills/plug hook manifests, ops ledger schema |
| `.sh` | 6 | |
| `.mjs` | 1 | `tests/providers` |
| `.ps1` | 1 | Tavily signup |
| `.js` | 2 | Turnstile patch |
| `.json` / `.jsonl` | 5 | Config, ledgers |
| `.txt` | 2 | Requirements |
| `.template` | 1 | `config.yaml.template` |
| `.patch` | 1 | Upstream model purge |
| `.yml` | 1 | CI |

---

## 3. What Exists on Disk

### 3.1 Top-level directories on disk

```
/home/ubuntu/hermes-agent-personal_assistant-work/
├── .githooks/            # tracked (2) — NOT in manifest
├── .github/              # tracked, in manifest
├── .git/                 # VCS internals (never in manifest)
├── .vscode/              # tracked (1) — NOT in manifest
├── __pycache__/          # gitignored
├── agent/                # tracked, in manifest
├── agents/               # tracked, in manifest (100%)
├── audio_cache/          # gitignored (TTS cache, on-disk only)
├── audit-prep/           # tracked (16) — NOT in manifest
├── audits/               # tracked (24) — NOT in manifest
├── cache/                # gitignored
├── config/               # partially in manifest
├── cron/                 # on-disk only, empty, NOT tracked, NOT in manifest
├── docs/                 # partially in manifest (10% of tracked docs)
├── gateway/              # tracked, in manifest
├── hermes_cli/           # tracked, in manifest
├── hooks/                # partially in manifest (70%)
├── image_cache/          # gitignored (image cache)
├── integrations/         # tracked (9) — NOT in manifest
├── locales/              # tracked, in manifest
├── logs/                 # gitignored
├── memories/             # NOT tracked (0 files), NOT in manifest
├── operations/           # mostly in manifest (75%)
├── optional-skills/      # tracked, in manifest
├── pairing/              # gitignored
├── patches/              # partially in manifest (13%)
├── persona/              # tracked, in manifest
├── plugins/              # mostly in manifest (91%)
├── scripts/              # partially in manifest (16%)
├── sessions/             # NOT tracked, NOT in manifest (DB-backed)
├── skills/               # mostly in manifest (90%)
├── sync/                 # tracked (5) — NOT in manifest
├── tests/                # mostly in manifest (94%)
└── windows/              # tracked (6) — NOT in manifest
```

### 3.2 Directories intentionally absent from manifest

These directories exist on disk but have **zero manifest entries** by design:

| Directory | Tracked files | `.gitignore`? | Reason not in manifest |
|---|---|---|---|
| `audit-prep/` | 16 | No | Historical audit evidence; superseded after Gate 5/7. Preserved in Git but outside deployment coverage. |
| `audits/` | 24 | No | Historical audit archives (`antigravity-1007`, `opencode-1007`, `zai-0907`, `archive/`). Read-only evidence, not deployed. |
| `integrations/` | 9 | No | Integration READMEs (`browser-use`, `crawl4ai`, `curl-impersonate`, `hybrid-web`, `markitdown`, `scrapling`, `skills`). Doc-only, not deployed. Guard classifies as `docs/integration` allowed-list. |
| `sync/` | 5 | No | Deployment plumbing (`SYNC-MECHANISM.md`, `deploy-hermes-runtime.sh`, `deploy-web-operator.sh`, `drift-check.sh`, `pull-vps-to-wsl2.sh`). Not deployed to runtime via manifest. |
| `windows/` | 6 | No | Windows host scripts (`gateway-start.ps1`, `web-operator-*`). Host-specific, not VPS runtime. |
| `.githooks/` | 2 | No | Git hooks (`README`, `pre-push-manifest-refresh`). Local dev infra, not deployed. |
| `.vscode/` | 1 | No | Editor config (`settings.json`). Dev-only. |
| `cron/` | 0 tracked | No | Empty directory; no source files to cover. Cron jobs are defined elsewhere if active. |
| `memories/` | 0 tracked | Partially | Session memories. Private mutable state; never in public Git manifest. |
| `sessions/` | 0 tracked | No (DB) | Session DB state; runtime-private. |

---

## 4. Intentionally Untracked (`.gitignore`)

These patterns are **never committed** and therefore never appear in the manifest. The manifest correctly excludes them — a guard flagging them as "missing" would be a false positive.

### 4.1 Secrets and credentials

```
.env
*.key / *.pem
auth.json
session/  platforms/
.hermes/
web-operator/state/  web-operator/profiles/  web-operator/quarantine/
web-operator/artifacts/  web-operator/takeover/  web-operator/medical-audit/  web-operator/keys/
```

### 4.2 Health / PII data (PDPA — public repo)

```
med-status.json  chain-state.json  med-schedule.json  med-supply.json
med-interactions.json  dexa_taper.json  substitutions.json  appointments.json
channel_directory.json  audit-prep/med-status.json
*.db  *.db-shm  *.db-wal
med-*.json
```

Live artifacts on disk that match this category (and are therefore correctly absent from Git and manifest): `med-schedule.json`, `dexa_taper.json`, `state.db`, `pairing/`.

### 4.3 Runtime caches, logs, and generated state

```
cache/  jobs.json  gateway_state.json  pairing/  med-*.json
*.log  logs/
audio_cache/  image_cache/  (on-disk caches, ignored)
```

On-disk evidence: `cache/`, `audio_cache/`, `image_cache/`, `logs/curator/`, `logs/`, `state.db`, `pairing/`.

### 4.4 Build / environment artifacts

```
__pycache__/  *.pyc  .pytest_cache/  .mimocode/
.DS_Store  Thumbs.db
.worktrees/
*.db
```

Observed on disk: `__pycache__/`, `agent/__pycache__/`, `hermes_cli/__pycache__/`, `scripts/__pycache__/`, `.pytest_cache/`, etc.

### 4.5 Summary rule

> If a path matches `.gitignore`, it is **expected** to be absent from both `git ls-files` and the manifest. No guard should flag it.

---

## 5. Tracked but NOT in Manifest — Detailed Gap Inventory

241 tracked files are not in the manifest. They fall into three buckets:

### 5.1 Bucket A — Intentionally out-of-scope (not a bug)

These are tracked in Git but deliberately excluded from the v3 coverage manifest because they are not part of the deployment/source-closure scope. A guard should **not** flag them as missing.

| Group | Files | Count | Why out-of-scope |
|---|---|---|---|
| Historical audit docs | `audit-prep/**`, `audits/**` | 40 | Superseded evidence; `docs/reconciliation/v3-supersedes-gate4.md` documents succession. |
| Root continuation briefs | `CONTINUATION-BRIEF*.md` (5), `ADVANCED-IDEAS.md`, `AUDIT.md`, `CLAUDE_AUDIT_PROMPT.md`, `MEDICATION-SAFETY-REGIMEN-DESIGN.md`, `NEW_AUDIT_PROMPT.md`, `OVERHAUL-EXECUTION-PROMPT.md`, `PX1-RESEARCH-TRACK-PLAN.md`, `PX2-PROBLEM-INTELLIGENCE-PRD.md` | 13 | Planning artifacts; not deployed. |
| Integration docs | `integrations/**` | 9 | External integration READMEs; standalone reference. |
| Deployment plumbing | `sync/**` (5), `windows/**` (6), `provision.sh`, `opencode.json` | 13 | Host/deploy scripts outside `~/.hermes` runtime tree. |
| Doc archives and reviews | `docs/archive/**`, `docs/plans/**` (SUPERSEDED), `docs/reviews/**`, `docs/superpowers/**`, `docs/px1b-*.md`, `docs/migration/**`, `docs/monitor-*.md`, plus `docs/reconciliation` extras (`gate4-*`, `gate5-*`, `governance-v2-*`, `hermes-runtime-source-lock.json`, `hermes-runtime-tree-manifest.json`, `manifest-receipts/**`, `post-gate7-*`, `hermes-runtime-source-authority.md`) | 33 | Docs outside the 4-file v3 closure scope; reconciliation history preserved but not v3-covered. |
| Extra configs | `config/web-operator-config.patch.template`, `config/web-operator.yaml.template` | 2 | Web-operator host configs. |
| Patch history | `patches/2026-06-27_*`, `patches/upstream-hermes/2026-08-06_*`, `2026-08-19_*` (5), `patches/upstream-hermes/README.md` | 7 | Previous upstream patches; only the `2026-08-11` purge is v3-covered. |
| Git/dev infra | `.githooks/**` (2), `.vscode/settings.json`, `.gitignore` | 4 | Dev tooling. |
| Ledger instance | `operations/ledger.json` | 1 | Private mutable instance; only `ledger.example.json` + `ledger.schema.json` are templated in manifest. |

**Subtotal Bucket A: ~122 files** — tracked, intentionally not covered.

### 5.2 Bucket B — Partial coverage (subdirectories of covered prefixes)

These prefixes **are** partially in the manifest, but some files within them are not covered. Whether this is a gap or intentional depends on per-file review.

| Prefix | Tracked | In manifest | Not in manifest | Not-covered files |
|---|---|---|---|---|
| `scripts/` | 113 | 18 | 95 | `scripts/__init__.py`, `scripts/chain_calc.py`, `scripts/chain_llm.py`, `scripts/chain_monitor.sh`, `scripts/deploy_hermes_runtime.py`, `scripts/dexa_taper_lookup.py`, `scripts/gateway-start.backup.ps1`, `scripts/guard/ci-base-sha.py`, `scripts/guard/docs-allowlist-check.sh`, `scripts/guard/manifest_recompute.py`, `scripts/qwen_driver.py`, `scripts/reconstruct_hermes_runtime.py`, `scripts/research_*.py`, `scripts/sakana_driver.py`, `scripts/taper_alert.py`, `scripts/test_*.py`, `scripts/med_*.py` (hold/safety/state_lock), plus entire subtrees `scripts/med_chain/**` (~20 files), `scripts/monitor/**` (4), `scripts/web_operator/**` (~30 files) |
| `skills/` | 112 | 101 | 11 | `skills/experts/research-expert/**` (7), `skills/experts/web-operator/**` (2), `skills/med-tracker/references/safety-gate-and-regimen-protocol.md` |
| `hooks/` | 10 | 7 | 3 | `hooks/med-auto-confirm/handler.py`, `hooks/med-auto-confirm/test_safety_gate.py`, `hooks/med-auto-confirm/test_time_parse.py` |
| `plugins/` | 32 | 29 | 3 | `plugins/trafilatura/**` (3) — provider not yet in v3 deployment set |
| `docs/` | 41 | 4 | 37 | See Bucket A doc list above |
| `config/` | 3 | 1 | 2 | `config/web-operator-config.patch.template`, `config/web-operator.yaml.template` |
| `operations/` | 4 | 3 | 1 | `operations/ledger.json` |
| `tests/` | 31 | 29 | 2 | `tests/reconciliation/test_hermes_runtime_reconstruction.py`, `tests/test_research_stage6.py` |
| `patches/` | 8 | 1 | 7 | See Bucket A patch list |

**Key callout — `scripts/web_operator` and `scripts/med_chain`:** These are substantial subsystems (30+ and 20+ files) that are tracked but not in the v3 manifest. If guard scope is meant to include "all application-source must be covered," these are the highest-signal candidates for manifest expansion or explicit allow-listing in `scripts/guard/manifest_recompute.py`.

### 5.3 Bucket C — Empty or runtime-only dirs (correctly absent)

| Directory | State | Action |
|---|---|---|
| `cron/` | 0 tracked files, empty on disk | Nothing to cover. If cron jobs are added, add them to manifest. |
| `memories/` | 0 tracked files | Private runtime state; correctly absent. |
| `sessions/` | 0 tracked files, DB-backed | Runtime state; correctly absent. |
| `cache/`, `audio_cache/`, `image_cache/`, `logs/`, `pairing/` | Gitignored | Correctly absent per §4. |

---

## 6. Runtime-Deploy vs Source-Only Split

| Kind | Count | Top prefixes |
|---|---|---|
| `runtime-deploy` | 156 | `skills` (76), `plugins` (29), `agents` (26), `scripts` (18), `hooks` (7) |
| `source-only` | 83 | `tests` (29), `skills` (25), root docs (6), `agent` (3), `persona` (3), `hermes_cli` (3), `operations` (3), `docs/reconciliation` (4), `locales`/`config`/`gateway`/`patches`/`optional-skills` (1 each), `hermes_state.py` |

All `runtime-deploy` entries have a `destination` under `~/.hermes/` (e.g., `~/.hermes/skills/med-tracker/SKILL.md`, `~/.hermes/plugins/lightclawbot/src/adapter.py`). Deployment is exact-per-path via `scripts/deploy_hermes_runtime.py` / `sync/deploy-hermes-runtime.sh` — no wildcard deploy.

Verification note: `destination` paths were not individually verified on live VPS in this pass. For live verification, compare `hermes-runtime-source-lock.json` against VPS `~/.hermes`.

---

## 7. Diagnosing Guard False-Positives

### 7.1 "File X is tracked but not in manifest" alert

1. Check §4 — does `X` match `.gitignore`? If yes, it should never be in manifest. Guard is misconfigured if it flags it.
2. Check §5.1 — is `X` in Bucket A (historical docs, integration READMEs, sync/windows, patch history)? If yes, it is intentionally out-of-scope. Either expand the guard's allow-list or accept the exclusion.
3. Check §5.2 — is `X` inside a covered prefix (e.g., `scripts/web_operator`)? This is a real coverage gap. Decide: add to manifest or add to an explicit `intentionally_untracked` list in `scripts/guard/manifest_recompute.py`.
4. If none of the above, the file likely post-dates `base_main_sha` (13baa13) and needs a manifest refresh. Run `scripts/guard/manifest_recompute.py` (triggered by `.githooks/pre-push-manifest-refresh` on push).

### 7.2 "Untracked file on VPS not in Git" alert

Not a manifest issue — the manifest only covers `git ls-files` entries. Check `sync/drift-check.sh` and `hermes-runtime-source-lock.json` for runtime drift.

### 7.3 "Docs file flagged but docs-allowlist says OK" alert

`scripts/guard/docs-allowlist-check.sh` and `docs/reconciliation/hermes-runtime-source-authority.md` govern docs allow-listing separately from the source coverage manifest. The manifest's 4-file `docs/reconciliation` scope does not grant or deny docs allow-list status.

### 7.4 Quick triage checklist

```
Is the file gitignored?         → Expected absent. (§4)
Is it in audit-prep/audits?      → Historical, out-of-scope. (§5.1)
Is it in sync/windows/.githooks? → Deploy/dev infra, out-of-scope. (§5.1)
Is it in scripts/web_operator    → Real gap — needs manifest entry or explicit exclusion.
  or scripts/med_chain?
Is it in integrations/ ?         → Doc-only, out-of-scope. (§5.1)
Is it a new file since 13baa13?  → Manifest needs recompute.
```

---

## 8. Maintenance

| Action | Command / file |
|---|---|
| Recompute manifest | `python scripts/guard/manifest_recompute.py` (also via `.githooks/pre-push-manifest-refresh`) |
| Check docs allow-list | `bash scripts/guard/docs-allowlist-check.sh` |
| Drift check (VPS) | `bash sync/drift-check.sh` |
| Runtime source authority | `docs/reconciliation/hermes-runtime-source-authority.md` |
| Closure ledger | `docs/reconciliation/v3-source-closure-ledger.md` + `.jsonl` |
| Supersession note | `docs/reconciliation/v3-supersedes-gate4.md` |

When adding new source files that should be deployed or source-covered, add entries via the recompute tool rather than hand-editing the JSON (hashes are SHA-256 over file bytes at `base_main_sha`).

This doc itself (`docs/manifest-coverage-map.md`) is not yet in the manifest — it is a reconciliation aid. Add it to the manifest if it should be source-covered in the next recompute.

---

*Generated from `v3-source-coverage-manifest.json` (239 entries) vs `git ls-files` (480) vs `.gitignore` vs on-disk `ls` on 2026-08-20. Total tracked-but-not-covered: 241.*
