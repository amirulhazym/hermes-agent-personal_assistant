---
name: hermes-git-pr-flow
description: Hermes Git PR squash flow for protected main branches.
---

# Hermes Git PR Squash Flow

Use when branch protection on `main` is active. Default flow for docs/monitor/skills changes.

## Flow

1. **Branch**: `git checkout -b feat/<slug> origin/main`
2. **Commit**: conventional `type(scope): msg`; stage exact files only
3. **Gates** (before push):
   - `python3 scripts/guard/pii-review.py --diff 4a2bc51..HEAD` → PASS
   - `bash scripts/guard/secret-scan.sh --tree` → PASS
   - `bash scripts/guard/manifest-validate.sh docs/reconciliation/v3-source-coverage-manifest.json $(git rev-parse HEAD)` → 239 PASS
   - `bash scripts/run_contract_tests.sh` → 14 passed (~6s)
4. **Push**: `git -c url."git@example.invalid:".insteadOf="https://github.com/" push origin HEAD:refs/heads/feat/<slug>`
5. **PR**: deeplink `https://github.com/amirulhazym/hermes-agent-personal_assistant/pull/new/feat/<slug>` → Create PR
6. **CI**: poll `https://api.github.com/repos/amirulhazym/hermes-agent-personal_assistant/actions/runs?head_sha=<sha>` → `guards=success test=success`
7. **Merge**: GitHub UI → **Squash and merge** → **Delete branch** (protection blocks direct push)
8. **Sync**: `git fetch origin && git checkout main && git reset --hard origin/main`

## Rules

- No force-push, no history rewrite on `main`
- No merge commit (blocked by Require linear history)
- P1 med remains deferred unless owner says otherwise

## Proven

- `feat/m3-rollback-live 639b213d5` → CI 32484686104 → squash `d90046e86` 2026-08-21
- `feat/phase3-4-fork-migration cf1abe4a0` → CI 32468500767 → squash `4afe8671b`


## Finalize Trigger

- Owner reply `done` after squash = finalize trigger: sync main → verify CI → write receipt vN → send ONE receipt message → STOP. No repeated footers.
