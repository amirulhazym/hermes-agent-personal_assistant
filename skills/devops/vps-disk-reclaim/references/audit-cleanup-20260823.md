# Audit-cleanup session 2026-08-23 (63% → 56%)

Context: owner asked for a deep audit at moderate disk level — "yang boleh deleted, redundancies, stale files, any improvements" — not an emergency reclaim. Read-only audit first, then per-ID approval ledger, then batched execution.

## Ledger as approved and executed

| ID | Verdict | Size | What | Outcome |
|---|---|---|---|---|
| A1 | DELETE | 467 MB | `~/.npm/_cacache` | deleted, no issue |
| A2 | DELETE | 178 MB | `~/.cache/uv` + pip + typescript | deleted |
| A3 | DELETE | ~60 MB | `/var/cache/apt/archives` via `sudo apt-get clean` | 5 stale .deb incl. 2023 fonts-noto-cjk 59M |
| B1 | REVIEW→approved | 779 MB | old Chrome builds `.42`+`.151` (kept newest `.54`) | re-checked `/proc/*/cmdline`, deleted |
| C1 | DELETE (worktree-safe) | ~800 MB | 17 `/tmp/hermes-*` CI clones; **4 were registered worktrees** of source clone → `git worktree remove --force` + prune first, rest rm | all clean (`status --porcelain`=0 each) before removal |
| C2 | DELETE | 66 MB | `/tmp/pytest-of-*` sandboxes | deleted |
| C3 | MAINTENANCE | 0 B | runtime repo had 5 `prunable` worktree entries → `worktree prune` | cleared metadata only |
| E1 | REVIEW→approved | 605 MB | HF faster-whisper small+base caches; config uses `whisper-1` API | deleted, labeled UNVERIFIED for local-path usage |
| F1/F2 | BACKUP-FIRST→paused | 759 MB + 237 MB | gate2 incident tar.gz + preupdate overlay dir | NOT in source repo (find+grep = empty) → Drive upload required; **OAuth token revoked mid-flow → paused with auth URL to owner, never downgraded to plain delete** |
| D1/D2 | explained, undecided | 930 MB / 65 MB | journald uncapped / rotated btmp.1 | owner didn't understand purpose → plain-Manglish explanation in chat (see below); decision still open |

df progression: 63% → 61% (A) → ~58% (C) → 57% (B) → 56% (E).

## What worked

- Pre-delete evidence pass per class: du -sB1 exact bytes, `git status --porcelain | wc -l` = 0 on every worktree before `worktree remove --force`.
- Two independent repos held independent stale worktree registrations pointing at the same /tmp paths (source clone: registered CI worktrees; runtime repo: prunable ghosts of dirs already gone). Prune both.
- Chrome deletion guarded by `pgrep -a chrome` empty + no pinned-version config reference.
- Security finding surfaced alongside cleanup (6k failed SSH/24h + `passwordauthentication yes` + `permitrootlogin yes` + fail2ban absent) but NOT acted on during cleanup — separate recommendation with lockout warning (verify key login FIRST).

## Owner-comprehension lesson (D items)

Owner instantly approved cache/browser/model deletes but stalled on journald/btmp: *"aku tak berapa faham… kepentingan dia, kegunaan dia, pros and cons kalau delete (selain free disk usage)"*. System-component ledger rows need a four-part plain explanation in chat: apa dia / kenapa wujud / apa hilang kalau buang / apa kekal. For config-cap proposals, add why one-off delete regrows. Full explanations went in the chat reply, not just the attached report file.

## Drive backup-before-delete lane (F1/F2)

Sequence when a recovery artifact isn't represented in source repo: verify absence (find + git log --all -- path) → locate existing project /backup Drive folder by listing (never guess ID) → SHA-256 pre-upload → upload → download roundtrip hash compare → only then delete local. This run stopped at step 2: `$GSETUP --check` returned `TOKEN_REVOKED (invalid_grant)`. Correct handling: generate fresh `--auth-url`, send to owner, wait — do NOT proceed to delete without the verified upload, even though approval to delete was already given ("Once dah upload, boleh delete" is conditional on the upload actually happening).
