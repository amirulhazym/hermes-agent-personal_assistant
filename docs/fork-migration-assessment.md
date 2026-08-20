# Fork Migration Assessment

| Item | Detail |
|---|---|
| Upstream | `NousResearch/hermes-agent` — latest tag `v2026.8.3` |
| Our current head | `ca9927776d` (origin/main) |
| Patch count | 6 files in `patches/upstream-hermes/` |
| Patches | P1C-selected-model, VPS-overlays, A4-model-purge, C3-lineage, C4-identity, PR85505-reset |
| Estimated migration effort | **1-2 hours** (not 2-4h) — 6 patches, small conflict surface |

## Branch structure (proposed)

```text
origin/main          — durable app source (current)
upstream/main        — NousResearch/hermes-agent (fetch)
fork/migration-test  — throwaway rebase dry-run branch
```

## Rebase workflow

```bash
git remote add upstream https://github.com/NousResearch/hermes-agent.git  # if missing
git fetch upstream
git checkout -b fork/migration-test origin/main
git rebase upstream/main   # capture conflicts/diffstat
# resolve → test → abandon or preserve as migration PR
```

## Conflict estimate

- Low — patches touch vendored overlays + hermes_state.py + gateway/session.py
- Main risk: upstream hermes_state.py / gateway changes colliding with C3/C4

## Recommendation

**Defer rebase until you pull upstream** — don't pre-migrate. Use `fork/migration-test` throwaway for any rebase estimate before committing.
