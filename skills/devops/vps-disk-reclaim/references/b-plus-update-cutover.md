# B+ update cutover reference

Use this reference when a Hermes updater has already placed a newer upstream source on disk, the old custom overlay is preserved, and the owner wants a short controlled cutover instead of a wholesale merge/full-suite loop.

## Decision boundary

`Drive source backup` and `restore custom overlay` are separate actions:

- Drive backup preserves recoverable source bytes off-VPS.
- Overlay restore changes the behaviour of the new runtime.
- A successful Drive hash round-trip does not prove restore usability.
- A clean upstream cutover intentionally leaves custom behaviour coverage open; restore only a function whose absence is observed and reproduced.

## Artifact package

Upload only the source-recovery package:

- working-tree archive of modified/untracked source-like paths;
- exact manifest with path, type/mode/symlink status where relevant, and SHA-256;
- binary-capable tracked patch;
- old-source Git bundle/ref provenance;
- SHA-256 records;
- minimal restore instructions;
- bounded screening result containing categories/filenames only, never secret values.

Exclude raw runtime/private material:

- `.env`, `auth.json`, API keys, tokens, private keys;
- session/authentication data and databases;
- raw runtime state snapshots;
- caches, virtual environments, generated output.

## Drive evidence ladder

1. Check auth and locate the exact owner backup folder.
2. Search exact artifact names before upload; do not infer duplicates from a similar filename.
3. Create a timestamped child folder when several artifacts belong to one recovery package.
4. Upload each artifact with the exact parent ID.
5. Read back owner, parent, size, MIME type, and permissions. `PUBLIC_OR_DOMAIN=0` is the relevant owner-only check; do not add link/domain sharing.
6. Download each uploaded file to a temporary directory and run the local SHA-256 manifest against the downloaded bytes.
7. Remove only the temporary round-trip directory.

Report statuses independently:

- `UPLOADED`
- `OWNER-ONLY PERMISSION VERIFIED`
- `HASH-ROUNDTRIP VERIFIED`
- `DECRYPT/LIST/RESTORE NOT TESTED` unless it was actually exercised.

## Clean-tree gate

Before removing an active overlay from the new source tree:

```text
current untracked path set ⊆ preserved manifest path set
SHA-256(current path) == SHA-256(manifest path) for every current path
old stash/ref/bundle/snapshot still present and independently checkable
```

Only after all assertions pass may the archived overlay bytes be removed from the active tree. Keep the archive, stash, bundle, and snapshot. Verify `git status --short --untracked-files=all` afterward; a clean tree proves source consistency, not behavioural completeness.

## Cutover gate

Check an executable rollback route using existing material only:

- old commit object/ref exists;
- stash resolves and remains retained;
- Git bundle verification passes;
- existing pre-update snapshot/manifest exists;
- rollback target/service path is known.

Do not repeat a broad backup audit or perform a rollback rehearsal merely because the owner approved the bounded lane. Stop if no executable rollback route exists.

Restart once into the clean upstream tree. Prefer the gateway's supported restart procedure or the maintained `clean-restart-gateway` skill. When a command is being run inside the gateway process and the runtime blocks self-restart, use a detached systemd/user-shell wrapper; do not repeatedly retry the same in-process command.

## Targeted smoke checks

Capture fresh evidence for each component:

- service `active/running`, new PID, and no restart loop;
- Telegram connection plus one basic owner interaction;
- WhatsApp bridge connection plus one basic owner interaction when available;
- selected model/provider/identity resolution;
- only already-known critical custom behaviours.

Do not turn channel connection into user-level interaction proof. Do not turn a targeted smoke pass into a full-suite pass. Do not turn a clean new source tree into proof that every old custom behaviour survived.

## Failure and recovery rule

If the new runtime cannot start, crash-loops, or breaks a core channel:

1. stop further patching;
2. execute the prepared rollback;
3. restart the previous runtime;
4. verify basic gateway/channel health;
5. report the failure and rollback evidence.

If the new runtime is healthy but one non-core custom function is missing, keep the new runtime live and record the exact missing behaviour. Build a minimal isolated patch for that function only. Never mass-restore the old overlay as a reaction to one missing feature.

## Cleanup gate

Only clean after runtime stability is evidenced. For each deletion batch record:

- exact path;
- allocated bytes and apparent bytes separately;
- role (`clean test workspace`, `rebuildable cache`, `source/evidence`, `rollback`);
- registered worktree status;
- active CWD/open-file check;
- retained evidence path.

Remove registered worktrees via Git, then prune metadata. Keep dirty/source-like, rollback, candidate, and sole-evidence paths even when their mtime is old. Use post-delete `df` as the filesystem result; never promise reclaimed bytes from `du` alone.
