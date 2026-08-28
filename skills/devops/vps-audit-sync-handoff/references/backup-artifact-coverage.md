# Backup-Artifact Coverage Verification (nested content preservation)

Verified 2026-08-07 on the Hermes VPS. This is the correction to a costly
overclaim: during a live↔source census I concluded that nested `hermes-agent`
post-patch untracked files (petdex UI, reconnect-controller, extra tests,
custom skills) "would be LOST on upgrade" because they weren't in the plaintext
`staging-runtime` dir nor in any tracked patch. **That conclusion was WRONG**
— the Gate-1 backup preserves the nested repo separately via encrypted
artifacts, so every one of those files was already recoverable. A reviewer
(no VPS access) caught it, and live verification confirmed it.

## Core rule (never skip)

**Before EVER concluding "content will be lost / not recoverable", check the
backup artifact set.** A file being ABSENT from a plaintext staging dir or from
a tracked patch proves NOTHING about whether its bytes survive — it may be
preserved in a separate encrypted backup artifact (or in the git object db).

## Where the nested repo is actually preserved (this VPS's Gate-1)

`/home/ubuntu/backups/gate1/` — the nested `~/.hermes/hermes-agent` is NOT in
`staging-runtime` (that dir, and its `runtime` tar, EXCLUDE `/hermes-agent/`
via `runtime-excludes.txt`). Instead the nested repo has its OWN artifact set
under `bundles/ gitdirs/ dirty/ env/`:

| Artifact kind | Path pattern | What it preserves |
|---|---|---|
| gitdir (full `.git/`) | `gitdirs/hermes-agent-gitdir-<TS>.tar.gpg` | ENTIRE `.git/` dir (~1 GiB) incl. object db + all refs/HEAD. HEAD == live HEAD proves bit-fidelity. |
| git bundle (history) | `bundles/hermes-agent-<TS>.bundle` | Full git history (can `git clone` the repo back). |
| dirty tracked-mod | `dirty/hermes-agent-dirty-<TS>.patch.gpg` | `git diff --binary` of the 11 modified tracked files. |
| untracked-files | `dirty/hermes-agent-untracked-<TS>.tar.gpg` | `git ls-files --others --exclude-standard` — the COMPLETE untracked set (petdex UI, tests, bridge files, custom skills, `patches/`, `.install_method`). |
| env (deps, not source) | `env/hermes-agent-{venv,node_modules}-<TS>.tar.gpg` | Runtime deps — reproducible, not source-worthy but preserved. |

All `.gpg` are AES256 symmetric, owner-passphrase-encrypted. The plaintext
evidence MANIFEST (`.txt` files, e.g. `status-hermes-agent-*.txt`) lists the
pathnames/state but NOT file contents.

## How gate1a.sh actually captures each (read these — don't guess)

- `gitdir`: `tar -C $(dirname $repo) -cf - "$repo/.git" | gpg …` → full `.git/`.
- `dirty tracked`: `git diff --binary > <name>-dirty.patch` (one per repo).
- `untracked`: `git ls-files --others --exclude-standard -z | tar --null -T - -cf - | gpg` → genuinely ALL untracked paths.
- `status evidence`: `git status --porcelain=v2 --untracked-files=all` → full path list, plaintext.

Verify these exact commands exist by reading `gate1a.sh` / `gate1b.sh` — the
artifacts then inherit their scope.

## The git-object-db recovery matrix (second independent layer)

Even WITHOUT decrypting the untracked tar, a file is recoverable from the
gitdir tar IF its blob exists in git objects. Check the LIVE nested repo (which
is bit-identical to what the gitdir archived when HEAD matches the recorded
HEAD):

```bash
h=$(git hash-object "$path")                 # live file's blob hash
git cat-file -t "$h"                          # exists in object db?
git log --all --find-object="$h" --oneline    # committed/referenced?
git count-objects -v                          # loose vs packed, garbage
```

Classify each path one of:
- **IN-COMMIT**: blob referenced by a commit/tree → recoverable from gitdir object db.
- **ORPHANED-BLOB**: blob exists loose in `.git/objects/` but no commit/tree references it (added-then-reset) → STILL in gitdir tar's `.git/objects/`, recoverable.
- **NOT-IN-GIT-OBJ**: neither → relies on the untracked tar only.

Then cross the blob-existence result with the untracked-tar coverage. Every
nested path this VPS has is covered by at least TWO independent layers (gitdir
object db + untracked tar), and custom skills additionally exist in the runtime
staging (plaintext).

## Correctness of the "46KB untracked tar" — verify size is self-consistent

A small compressed tar CAN hold many small source files. Don't assume
"subdirectory missing" from size. Sum the live untracked contents: if the total
is ~305KB uncompressed and the tar is ~46KB gpg-compressed, that's plausible
(highly compressible text). To be rigorous, confirm the capture command uses
`git ls-files --others` (all of them) rather than an explicit path list.

## Honest labels (owner-passphrase gates)

If artifacts are encrypted and you lack the passphrase, you CANNOT list/decrypt
them. Do NOT infer ABSENT. Label each:
- **PATH-RECORDED-BUT-CONTENT-UNPROVEN** — the plaintext status/refs file proves
  the path existed but the encrypted artifact's contents are not byte-verified.
- **EXISTS-BUT-CONTENT-UNVERIFIED** — encrypted artifact exists (size/mtime/SHA
  recorded in MANIFEST) but contents can't be confirmed without decrypt.

If a fixture decrypt round-trip PASSED during backup creation
(`gate1b-*.log`: `gpg: encrypted with 1 passphrase` on both encrypt+decrypt),
that validates the encryption toolchain, but NOT each artifact's content.

## Stopping decision (give the user exactly one)

- **A. GATE1-NESTED-COVERAGE-SUFFICIENT** — every path has ≥1 backup layer → no emergency checkpoint; proceed normally.
- **B. CURRENT-NESTED-CHECKPOINT-REQUIRED** — coverage absent/incomplete → checkpoint immediately.
- **C. CURRENT-NESTED-CHECKPOINT-PRUDENT** — artifacts exist but contents can't be proven (encrypted) → offer optional small plaintext checkpoint, DON'T force it.

## No-change proofs to gather
Same as census: work-clone HEAD+dirty, nested HEAD (must equal gate1 refs-hermes-agent HEAD → bit-fidelity), gateway PID, OAuth token mtime. All checks here are read-only (`git hash-object`, `cat-file`, `verify-pack`, `stat`, `sha256sum`).

## Why the overclaim happened (prevent recurrence)
1. I checked ONLY the plaintext `staging-runtime` manifest → concluded nested files "not in backup".
2. I treated `git apply --check --reverse` failing (patch not byte-exact) as "content not represented → lost".
3. I hadn't read `gate1a.sh`'s capture scope, so I didn't know `gitdirs/`, `dirty/`, `bundles/`, `env/` separately preserve the nested repo.
Lesson: **read the backup script to learn the capture scope, check every artifact kind, verify blob existence in git objects — only THEN conclude coverage.**
