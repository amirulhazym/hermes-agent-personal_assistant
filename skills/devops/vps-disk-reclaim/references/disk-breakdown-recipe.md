# Disk breakdown recipe (Hermes VPS)

Verified on 2026-08-13: 87% → 57% by reclaiming ~11 GB (steps 1–5 of the cleanup plan).

## Localize bloat (run in order)
```bash
df -h / /home
du -sh /home/ubuntu/.hermes/*/            # top-level .hermes dirs by size
find / -xdev -type f -printf "%s %p\n" 2>/dev/null | sort -rn | head -15 | awk '{printf "%.1f MB  %s\n", $1/1048576, $2}'
du -sh /tmp                                # agent scratch often lives here
```

## Known large items on a Hermes VPS (safe vs live)
| Path | Typical size | Disposition |
|---|---|---|
| `/tmp/state_test.db` | ~1.9 GB | Agent's own copy of state.db — DELETE (zero risk) |
| `/tmp/hermes-*`, `/tmp/a4-*` | 0.5–0.7 GB each | Investigation/overhaul checkouts — DELETE |
| `~/.hermes/state-snapshots/<ts>-pre-update/state.db` | ~1.6 GB | One-time pre-update copy — DELETE if other backups exist |
| `~/.hermes/hermes-agent/.git` (39 packs) | ~1.4 GB | `git gc --prune=now` → ~800 MB |
| `~/.hermes/backups/gate1/` (old .gpg sets) | 4.5 GB | Prune oldest, keep newest |
| `~/.hermes/state.db` | 1.8+ GB | REAL data (95k msgs + FTS) — VACUUM reclaims ~0; only shrinks via session purge |
| `hermes-agent/venv` | 1.6 GB | Runtime deps — KEEP |
| `/swap.img` + `/swapfile` | 5.9 GB | System swap, leave alone |

## Is state.db reclaimable via VACUUM?
```python
import sqlite3, os
p='/home/ubuntu/.hermes/state.db'
con=sqlite3.connect(p)
page=con.execute('PRAGMA page_size').fetchone()[0]
tot=con.execute('PRAGMA page_count').fetchone()[0]
free=con.execute('PRAGMA freelist_count').fetchone()[0]
print('RECLAIMABLE_VIA_VACUUM_MB=', free*page/1048576)
```
If ~0 → the size is genuine conversation volume, not free space.

## Safety
- Delete in approved batches; `df` is the authority after deletion (not `du`).
- Never create a big archive before deleting at 90%+ free space.
- Agent's own `/tmp` scratch is the most common silent bloat — clean it first.
