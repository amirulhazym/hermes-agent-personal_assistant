# Dry-Run Rebase Playbook Step

Add this before any upstream update that touches `hermes_state.py` or `gateway/session.py`.

## When to run

Before merging any upstream tag that postdates our last Gate 2 provenance (`2026-08-19`).

## Procedure

```bash
# 1. Throwaway branch from current origin/main
git fetch origin
git checkout -b rebase-estimate-$(date +%Y%m%d) origin/main

# 2. Fetch upstream
git fetch upstream --tags  # or: git fetch https://github.com/NousResearch/hermes-agent.git --tags

# 3. Attempt rebase
git rebase upstream/main 2>&1 | tee /tmp/rebase-estimate.log
git diff --stat HEAD@{1}..HEAD 2>&1 | tee -a /tmp/rebase-estimate.log

# 4. Capture
echo "conflicts: $(git status --short | wc -l) files" >> /tmp/rebase-estimate.log
git log --oneline origin/main..HEAD >> /tmp/rebase-estimate.log  # what rebased

# 5. Abandon throwaway (no push)
git checkout main
git branch -D rebase-estimate-$(date +%Y%m%d)
```

## Use the capture as

- **Scope estimate** before committing to the real rebase
- **Conflict inventory** for the real rebase plan
- Entry in `docs/reconciliation/` if the estimate changes Gate 2 provenance

## No live mutation

This is read-only — no push, no deploy, no restart.
