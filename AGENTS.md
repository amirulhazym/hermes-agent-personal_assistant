# AGENTS.md — Hermes Operator Constitution (v4)

This file is the durable policy for the application-source repository and the
Hermes runtime it governs. Operational command detail belongs in
`skills/operator/*`; deterministic enforcement belongs in `scripts/guard/*` and
CI. A procedure, ledger entry, stale document, task list, or reviewer report
cannot override this file or the latest explicit owner instruction.

## 1. Authority and evidence

Precedence, highest first:

1. Platform/system safety constraints.
2. The latest explicit owner instruction, including an explicit HOLD/PAUSE or
   exact release authorization.
3. This `AGENTS.md`.
4. A tested release procedure and exact release manifest.
5. Ledger/status/docs metadata.

Reviewer material is a lead or evidence pointer, not proof of live state.
Historical documents remain historical. Authorization is never inferred from a
branch existing, a stale ledger entry, a task list, or a previous plan.

Evidence labels must identify provenance:

- `REMOTE-VERIFIED`: returned by a direct remote/API query in this work item.
- `LOCAL-VERIFIED`: returned by local Git/filesystem inspection only.
- `LIVE-VERIFIED`: returned by direct read-only inspection of the live runtime.
- `INFERRED`/`UNVERIFIED`: not sufficient for a PASS or release claim.

## 2. Topology and Single Source of Truth (SSOT)

| Layer | Path | Role |
|---|---|---|
| **Personal App Repository (SSOT)** | `/home/ubuntu/hermes-agent-personal_assistant-work` | **The sole authoritative Git development repository** for all features, custom scripts, medical logic, tests, skills, governance, and upstream patch overlays. |
| **Public GitHub `main`** | `amirulhazym/hermes-agent-personal_assistant` | Durable remote application source and recovery lineage; the only permanent application-source branch (`origin/main`). |
| **Live Runtime Directory** | `/home/ubuntu/.hermes/` (`$HERMES_HOME`) | Live mutable state (databases, active configuration, secrets, live skills/scripts). |
| **Framework Runtime** | `/home/ubuntu/.hermes/hermes-agent` | **Deployment-managed / no-direct-development runtime**. Executes the live gateway service; updated only via deployment scripts or reconstructive patch application. Direct editing and branching here is forbidden. |
| **Official Upstream** | `NousResearch/hermes-agent` | External upstream framework reference (`upstream/main`). |

**Hard Invariant:** All code modifications, bug fixes, testing, and branch creation MUST take place exclusively in `/home/ubuntu/hermes-agent-personal_assistant-work`.

### Authoritative Git Workflow Rules (One Repository SSOT)
1. **One Sole Personal Development Repository:** `/home/ubuntu/hermes-agent-personal_assistant-work` is the ONE and ONLY personal development repository for this Hermes system. All personal code, tests, integrations, patches, deployment logic, and versioned customizations belong here.
2. **No Arbitrary Repos, Workspaces, or Worktrees:** Never execute `git init` to create another personal repo, `git clone` to build another personal development workspace, or `git worktree add` unless explicitly requested by the owner.
3. **Main-Branch Lifecycle:** Normal personal development stays on `main`. Do not create arbitrary feature branches (`git checkout -b`, `git switch -c`, `git branch <name>`).
4. **Protected Publication Exception:** Temporary publication branches (`nightly/publication-*`) are strictly reserved for the automated, deterministic protected-main publication executor and must be automatically pruned after merge or cleanup.
5. **Dependencies Are Not Publication Targets:** External Git checkouts (`~/.hermes/hermes-agent`, `~/.hermes/plugins/antigravity-provider`, etc.) are runtime dependencies only. Never treat them as personal development repos or publication targets.
6. **Provenance First:** Any required customization to a dependency must have authoritative source/patch representation in the personal repo before the task is complete. Direct live editing without representation is forbidden.
7. **Task Completion Contract:** A code task is never Git-complete while personal changes remain uncommitted/unpushed or stale temporary branches/worktrees remain.

## 3. Owner-ratified source-preservation rule

Every intentional human-authored Hermes customization created or changed on
the VPS must be represented in `main` of the SSOT repository as soon as practical:
code, features, fixes, skills, plugins, hooks, scripts/tools, tests, bridge code,
service and deployment definitions, config schemas/templates, and reconstructive
operator documentation. Dormant, unloaded, absent from a manifest, or
privacy-adjacent does not make custom source disposable.

Only proven generated/cache/dependency material, unchanged upstream material,
pure private mutable runtime state, raw secrets/PII that cannot be published,
or a genuine obsolete/backup duplicate may be omitted. The omission reason
must be recorded. If the classification is ambiguous, preserve the evidence
and ask the owner rather than silently dropping it.

## 4. Privacy and safe representation

Raw secrets, credentials, private keys, sessions, databases, logs, account
exports, private persona/memory contents, medical state, and other private
mutable runtime bytes never enter public Git. This does not mean discarding
source behavior: use a sanitized source file, schema, template, dummy fixture,
redacted documentation, migration, or reconstructive reference where that is
needed to recreate the feature. Keep raw bytes in private/encrypted backup.

A sanitized representation is not proof by itself. Secret scanning, PII-risk
review, tests, and owner review are separate evidence layers. Public stale
persona files are cleaned or replaced with safe structural placeholders; raw
live persona is never copied into them. `SOUL.md` remains untracked.

## 5. Change, capture, and release flow

Planned work is source-first:

```text
SSOT clean source -> isolated tests/scans -> exact candidate SHA -> one owner
release approval -> promote/deploy/verify
```

A bounded live-first fix is allowed only when the active task genuinely
requires it. Preserve readable pre-change state/diffs first, make the bounded
fix, then capture the exact intentional change into clean source, sanitize as
needed, test it, and close that capture within the same work item before
starting unrelated work. Live-first is not permission to leave source drift.

`main` promotion—including docs, governance, tests, and deployment metadata—
requires one tested exact-SHA approval: `APPROVE RELEASE <full-sha>`. There is
no docs-only auto-promotion and no approval-per-Git-command loop. No
force-push or rebase of published history.

Temporary branches/worktrees are local by default (`candidate/nightly-YYYYMMDD`).
Push a temporary remote branch only when separately justified for preservation/review;
delete it only under the approved cleanup flow.

## 6. Deployment and synchronization to live runtime

Deployment is exact-manifest, per-path, hash-checked, rollback-protected, and
never wildcard/recursive/delete-based.
- **Custom scripts/skills/hooks:** Synchronized from SSOT to `~/.hermes/` via `scripts/deploy_hermes_runtime.py` matching hashes in `docs/reconciliation/v3-source-coverage-manifest.json`.
- **Core framework patch overlays:** Materialized into `~/.hermes/hermes-agent` via `scripts/reconstruct_hermes_runtime.py` based on `docs/reconciliation/hermes-runtime-source-lock.json`.
- **Drift verification:** `scripts/monitor/drift_check.sh` ensures live files match deployed references and flags unmanaged mutations.

## 7. Nightly Git Self-Improvement & Hygiene Protocol

Every night at **23:55 MYT**, an automated audit job executes `scripts/nightly_git_hygiene.py`:

1. **Daily Delta Discovery:** Inspects `git status`, `git log` for changes created that day.
2. **Quality & Security Gates:**
   - Secret scan via `scripts/guard/secret-scan.sh`.
   - PII review via `scripts/guard/pii-review.py`.
   - Reconciliation & contract tests via `pytest tests/reconciliation/ tests/guard/`.
3. **Branch & Remote Classification:**
   - Detects merged local branches and prunes them safely.
   - Detects unmerged stale branches (>7 days) and flags them in the report (no auto-delete).
   - Fetches `origin` and `upstream` to verify sync state (`ahead`, `behind`, `diverged`).
4. **Self-Improvement Analysis:**
   - Reviews daily failure logs and recurring tool blocks.
   - Formulates improvement proposals in `docs/proposals/` if structural lessons emerge.
   - **Safety Boundary:** Governance (`AGENTS.md`) and core policy are NEVER auto-mutated; proposals require owner review.
   - **Push Gate:** Automated jobs NEVER push to protected `origin/main` without explicit human authorization.
5. **Receipt & Audit Delivery:**
   - Generates `/home/ubuntu/.hermes/logs/git-nightly-receipt.md`.
   - Delivers a concise 1-bubble status summary to the owner's Telegram channel.

## 8. Stop conditions

Stop and report exact evidence for: data-loss risk; public secret/PII exposure;
unrecoverable runtime/deployment risk; unauthorized mutation; or a false-PASS
guard. Do not convert a failed, skipped, malformed, or unparsed check into
PASS. Keep raw private values out of all output.
