---
name: multi-auditor-git-coordination
description: Git/branch/sync coordination for multi-auditor Hermes audits under freeze — verification prompt + diagnosis recipes.
---

# Multi-Auditor Git / Branch / Sync Coordination

Companion to the SKILL.md "Multi-Auditor Git / Branch / Sync Coordination" section. Use when 2+ external auditors (OpenCode, Z.ai, Gemini/Antigravity) have committed audit work to a shared repo and the user wants to push/merge without conflicts.

## 1. Pre-merge verification prompt (send to EACH auditor, individually)

Copy-paste, adjust folder names to current structure:

> All audits are committed locally but NOT pushed to `origin` (<repo-url>). Before I approve push/merge, reply with:
> 1. **Branch + latest commit**: `git log -1 --format="%H %s"`.
> 2. **Your files' CURRENT local paths**: do they match the new structure (`<you>-audits-XXXX/`) or are you still at old paths?
> 3. **Did another auditor move YOUR files without OK?** If yes — do you accept the new location, or do you have local commits at the OLD path that'll now conflict?
> 4. **Push status**: confirm NOT pushed (`git log origin/<branch>..HEAD --oneline`).
> 5. **Conflict check**: any file you touched that another auditor also touched (root audit-01/02/03.md, PATTERN-G-*.md, fresh-context-prompt-v2.2.md, sync/*.sh)?
> 6. **VPS state**: VPS currently MIXED (one auditor's folder reorganized, others at old paths). Confirm your VPS mirror matches intended final state.
> 7. **Merge preference**: integration target branch + order to minimize conflicts (esp. root→`<you>-audits-XXXX/` rename).
> Do NOT push. Reply concisely.

## 2. Diagnosis recipes (run on VPS)

**Branch divergence + dirty state:**
```bash
cd <repo>
git status --short                       # untracked (??) / modified (M) / deleted (D)
git log -1 --format="%H | %ci | %s"     # HEAD
git log --oneline -5
git remote -v                           # confirm origin
```

**Confirm a claimed commit exists on VPS (local-PC commits won't):**
```bash
git cat-file -t <commit-hash>   # "commit" = present; "fatal: Not a valid object" = PC-only
```

**Folder-path reality check (don't trust folder names):**
```bash
search_files(pattern="*.md", path="<repo>/audits", target="files")   # actual paths on disk
ls -la --time-style=full-iso <folder>/                                # mtime reveals batch-dump vs hand-edited
```

## 3. Failure-mode playbook

| Mode | Signal | Mitigation |
|------|--------|------------|
| Branch divergence | auditors on `main` + `hermes-live` | Pick ONE integration target; rebase/merge in agreed order |
| scp-dirty-state | VPS `git status` shows `??`/`M` for "committed" files | Before pull: confirm scp'd content is superseded by a commit, then `git clean -fd` / commit-then-pull. Never blind-pull over scp'd state |
| Unilateral reorg | one auditor moved others' files + committed (e.g. `c7c40e2`) | Under freeze = UNAUTHORIZED. Revert the cross-auditor moves; let each auditor move OWN folder, then merge |
| Rename/delete-vs-add conflict | git: "deleted in ours, modified in theirs" | Each auditor owns a DISJOINT folder → no shared-file edits. Resolve rename-threshold manually if it occurs |

## 4. VPS re-verify mandate

External agents act outside your session. After ANY auditor commit/scp/reorg:
1. `search_files` audits dir — actual folder paths (not folder-name assumptions).
2. `git status --short` + `git log -1` — HEAD + dirty state.
3. `git cat-file -t <claimed-commit>` — confirm the commit is actually on VPS (PC-only commits won't be).
4. Only THEN report. Prior-turn checks go stale the moment an external agent acts.

## 5. Real example (2026-07-10)

- OpenCode committed on `hermes-live` (HEAD `5b5cb46`) with files at ROOT `audit-01/02/03.md`.
- Z.ai committed on `main` (`c7c40e2`) that MOVED those same root files to `opencode-audits-1007/`.
- Z.ai scp'd ONLY its own folder to VPS (`zai-audits-0907/`), leaving VPS with a MIX: new zai + old `antigravity-audit/` + old root `audit-01/02/03.md`.
- `git cat-file -t c7c40e2` on VPS → `fatal: Not a valid object` (PC-only).
- Result: merging `hermes-live` + `main` = rename/delete-vs-add conflict on the audit files. Fix = revert cross-auditor moves, each auditor moves own folder, single integration target.
