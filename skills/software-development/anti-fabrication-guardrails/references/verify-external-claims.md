# Verify external-agent claims against live state

When an auditor / subagent / other AI claims a result, verify before trusting.
Built from the 2026-07-10 Hermes overhaul where 3 AI auditors reported sync
claims that had to be checked against the VPS.

## Checklist
1. **Files synced / byte-match?**
   `wc -c <file>` on BOTH sides, compare exact byte counts.
   Single source = flag, not fact.
2. **Path correct?**
   Case-sensitivity: `soul.md` ≠ `SOUL.md`. Check ACTUAL location
   (repo-root `~/mjay/sync/` vs `~/mjay/audits/sync/`). A wrong-path check
   = your error, not their falsehood.
3. **Committed or just scp'd?**
   `git status` — untracked (`??`) = scp copy, NOT version-controlled.
   `git log -1` — what's HEAD? `git cat-file -t <hash>` confirms if a claimed
   commit exists on THIS repo.
4. **Content claims?**
   `grep -c` the specific phrase in the actual file (watch case:
   "TARGET-STATE" uppercase won't match "target-state" lowercase).
5. **Old path removed?**
   `ls` / `search_files` the old path — confirm gone.

## Pitfalls hit this session
- Auditor claimed `sync/` "preserved". My `ls audits/sync/` said missing.
  Truth: it was at repo-root `~/mjay/sync/`. Wrong path = false alarm.
- First grep for "Section 8" returned 0 because doc wrote "TARGET-STATE"
  (uppercase); my lowercase pattern missed it. Claim was TRUE.
- Auditor claimed byte sizes 20000/37148/22499 — verified identical on VPS.
  Claim TRUE.
- Two reorg commits on different branches (Z.ai `c7c40e2` on main,
  OpenCode `62729fc` on hermes-live) + 2 folders untracked = mixed git state
  that needs reconciliation before push/merge.

## Command recipes
```bash
cd /home/ubuntu/mjay
git status --short                       # untracked? modified?
git log -1 --format="%H %an <%ae> %s"   # HEAD + author
git cat-file -t <hash>                   # does claimed commit exist here?
git show --stat <hash> | head -30       # what did a commit actually change?
wc -c path/to/file                       # byte-exact compare
grep -c "Phrase" file.md                 # content presence (mind case)
```
