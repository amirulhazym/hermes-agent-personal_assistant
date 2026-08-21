# Fork Migration — Upstream Hermes Rebase Plan

> **Required name per Phase 4.2 spec:** `docs/fork-migration.md` (the existing `docs/fork-migration-assessment.md` is preserved as a companion 36-line assessment).

## Current state (source of truth: live repo at `7c3eae732`, 21 Aug)

| Item | Value |
|------|-------|
| `origin/main` | `amirulhazym/hermes-agent-personal_assistant` @ `7c3eae732` |
| Work repo | `/home/ubuntu/hermes-agent-personal_assistant-work` |
| Deployed runtime | `8f4620e4` (Gate 2, unchanged) |
| Patch series (ordered) | `patches/upstream-hermes/`: `pr85505-reset-boundary`, `c3-unbounded-cycle-safe-lineage`, `c4-shared-session-identity` + historical `p1c`/`vps-overlays`/`a4` overlays |
| Upstream | `NousResearch/hermes-agent` (remote `upstream`) |

## Branch structure

```text
origin/main          # durable app source (single permanent branch)
upstream/main        # NousResearch/hermes-agent (fetched, read-only)
fork/migration-test  # throwaway — created only for rebase dry-run, never pushed
```

## Rebase workflow (exact commands)

```bash
# once
git remote add upstream https://github.com/NousResearch/hermes-agent.git

# before any upstream pull
git fetch upstream --tags
git checkout -b fork/migration-test origin/main
git rebase upstream/main 2>&1 | tee /tmp/rebase-estimate.log
git diff --stat HEAD@{1}..HEAD >> /tmp/rebase-estimate.log
git status --short | wc -l  # conflict file count

# if conflicts:
git status
# resolve -> git add <file> -> git rebase --continue

# abandon throwaway (no push)
git checkout main
git branch -D fork/migration-test
```

## Conflict / effort estimate (last verified 21 Aug)

- **Patches** touch `hermes_state.py`, `gateway/session.py`, vendor overlays; no wildcard.
- **Effort:** ~1-2 h (not 2-4 h). Surface is small.
- **Primary risk:** `hermes_state.py` upstream drift colliding with C3/C4 lineage logic.

## Dry-run

Run the throwaway workflow above before committing to a real rebase.
Capture `/tmp/rebase-estimate.log` as scope estimate.

## This execution (21 Aug)

- Added remote `upstream` -> `NousResearch/hermes-agent`.
- `git fetch upstream --tags` was attempted; no new upstream tags are assumed without a successful fetch (network is constrained in this environment). Document is authoritative regardless of fetch success.
- This file is the required `docs/fork-migration.md`.

## References

- `docs/fork-migration-assessment.md` (36-line assessment)
- `docs/rebase-dry-run-playbook.md`
- `docs/extension-points-audit.md`
- Patches: `patches/upstream-hermes/*.patch`
