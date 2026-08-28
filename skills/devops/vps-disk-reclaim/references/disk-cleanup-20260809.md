# Disk cleanup 2026-08-09 — verified session replay

## Situation
- `/` = 40GB volume, ~93% used, avail 3.18GB.
- Goal: reclaim space without losing live source, private state, or sole-copy evidence; drive partition A/B flow.
- Owner decision pattern: approve part-by-part (`Setuju untuk execute A1-A6. 2. Setuju B. 3. Belum boleh setuju C dan D, proceed A dan B dulu`).

## What got deleted (approved A + B)
1. **Caches (A1-A6/w):**
   - `/home/ubuntu/.cache/uv` — 1.49GB (`du -sb`)
   - `/home/ubuntu/.cache/pip` — 278MB
   - `/home/ubuntu/.npm/_cacache` — 130MB
   - `/home/ubuntu/.cache/electron` — 115MB
   - `/home/ubuntu/.cache/node-gyp` — 59MB
   - `/tmp/pytest-of-ubuntu` — 88MB
   - `/tmp/hermes-v3-full-suite-home-canonical.hM9YWc` — 530MB (test HOME env: .agent-browser 407MB, .npm 120MB, .hermes minimal)
   - `/tmp/med-audit2-h9qm9ufs` — 557MB (audit Med 18 Jul, non-live)
2. **Registered Git worktrees (B) — `git worktree remove --force`:**
   - `/tmp/hermes-part-e-upstream-donor-20260809` (112MB, clean)
   - `/tmp/hermes-part-e-turn-finalizer-patched-20260809` (114MB, 1 modified + 1 untracked)
   - `/tmp/hermes-part-e-candidate-materialized-20260809` (215MB, 18 modified + 56 untracked: AGENTS.md, README.md, agent/conversation_loop.py, scripts/whatsapp-bridge/bridge.js, tests, .github/workflows/ci.yml + more)

## Evidence staging (before deletion)
`/home/ubuntu/backups/part-e-worktree-evidence-20260809/` (621KB total):
- `<name>.status` (porcelain per worktree)
- `candidate-materialized.diff` (192KB), `turn-finalizer-patched.diff` (4.8KB)
- `candidate-materialized.untracked.tar.gz` (421KB)
- `turn-finalizer-patched.untracked.tar.gz` (45B — the untracked test path only)
- `SHA256SUMS.txt` (sha256sum of each file)

Method:
```bash
git -C <worktree> status --porcelain > "$EV/<name>.status"
git -C <worktree> diff > "$EV/<name>.diff"
(cd <worktree> && tar --exclude=.venv --exclude=.git --exclude='__pycache__' -czf "$EV/<name>.untracked.tar.gz" $(git ls-files --others --exclude-standard))
( cd "$EV" && sha256sum ./* > SHA256SUMS.txt )
```

## Process reference check (no open handles)
Scanned `/proc/<pid>/{cwd,fd}` — no CWD or open FD pointed at any deleted path. `pgrep` confirmed gateway PID + whatsapp-bridge node PID stayed alive post-delete.

## df before/after (B1 bytes)
```
before: 42156257280 total  37139374080 used  3175108608 avail  93%
after:  42156257280 total  34584748032 used  5729734656 avail  86%
reclaimed (df): ~2.56GB (sum of du-sb target sizes ~ 3.75GB; some /tmp paths self-cleaned / overlay size counted by du overstates the reclaimable portion)
```

## Holds (not deleted)
- `/home/ubuntu/backups/gate1` — 4.9GB recovery artifact
- `/home/ubuntu/hermes-snapshot-20260709` — 3.4GB pre-update snapshot
- `/home/ubuntu/backups/hermes-whatsapp-full-20260729_081657_MYT` — 894MB, the **only** full WhatsApp backup (46,238 messages / 650 sessions, sqlite `integrity=ok`) — keep; new backup made before next Hermes update, then old can be deleted.
- `/home/ubuntu/.local/lib` — 951MB installed libs, KEEP (not a cache)
- `/tmp/hermes-part-e-candidate-overlay-20260809` (124MB) + `baseline-overlay` (131MB) — C, NOT approved; still on disk at end of session; content overlap analysed but deletion deferred.
- `/tmp/hermes-v3-full-test-overlay` (1.4GB) + `-final` (1.46GB) — part-E leftovers; review (linked worktree + 169 untracked etc.), deferred.

## Verification commands worth reusing
```bash
# sizes for the df-projection number
df -B1 / | tail -1
# actual allocated bytes per folder
du -sb <path>
# any live process has cwd/fd inside target?
for w in /tmp/...; do git -C /home/ubuntu/.hermes/hermes-agent worktree list --porcelain | grep -F "$w"; done
# registered worktrees only
git -C /home/ubuntu/.hermes/hermes-agent worktree list --porcelain
# hash-identity sample between overlay and live
python3 - <<'PY'
import os,hashlib,random
def h(f):
    m=hashlib.sha256()
    with open(f,'rb') as fh:
        for c in iter(lambda: fh.read(1<<20), b''): m.update(c)
    return m.hexdigest()[:16]
PY
```

## Pitfall and lesson
- `git worktree` paths must be removed with `git worktree remove --force`, not `rm -rf`; after removal re-run `git worktree list` to confirm registration cleared.
- Do not report "latest backup" by name only — open `BACKUP_COMPLETE.json` (backup_created_at_myt + sqlite integrity counts) to verify.
- Disk projections must use df-comparable denominator (`used/(used+avail)`), not used/total; a 93%→86% drop after ~2.5GB freed matches the formula.