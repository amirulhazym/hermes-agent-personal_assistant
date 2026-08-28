# Durable Source Preservation and Hunk-Port Checklist

Use for source overlays, test clones, dirty worktrees, and recovery artifacts before deletion or overwrite.

## Evidence layers

Keep these separate:

1. **Git provenance** — exact donor HEAD, commit object, and retained remote ref or verified bundle.
2. **Working-tree preservation** — archive of tracked-modified and untracked bytes plus a per-file SHA-256 manifest.
3. **Durable local copy** — outside `/tmp`, private permissions, hash-equal to the source archive.
4. **Off-device copy** — encrypted artifact uploaded to an independent destination; upload/size/hash evidence.
5. **Restore proof** — fresh isolated extraction/decryption and per-file hash comparison.

Do not collapse these into one `backup verified` status.

## Archive gate

- Record archive SHA-256 and manifest SHA-256.
- Record exact path list, type, mode, symlink/hardlink status, owner, and size.
- Reject absolute names and any member containing a `..` path component.
- Extract only into a fresh temporary directory.
- Compare all restored file hashes against the manifest.
- Re-hash the donor worktree status and preserved files after extraction to prove no source mutation.
- Create a private durable copy only after the verification gate passes.

## Git/hunk gate

For tracked modifications:

```bash
git diff --full-index --binary <donor-head> -- <paths> > donor-working-tree.patch
git diff --check <donor-head> -- <paths>
git apply --check --cached donor-working-tree.patch
```

`git apply --check` against a dirty donor worktree may fail because the current target already contains the patch. That is a verification-boundary error, not automatically a patch defect. `--check --cached` verifies applicability against the donor index without applying it. A clean check still proves only patch applicability, not combined behavior.

For untracked files, preserve full bytes and compare them semantically against the clean baseline and live tree. Record `ABSENT` explicitly where a comparison version does not exist.

## Privacy gate

Report categories/counts only during screening. Never print secret values, private medical content, tokens, or raw session/account data. Treat these as separate findings:

- credential-shaped value;
- PII/email/phone or absolute host path;
- private or medical operational content;
- runtime-only mutable state;
- ordinary source/config.

A size/hash match does not prove privacy safety. Do not upload plaintext sensitive material. If encryption custody is not known and owner-controlled, label off-device preservation `BLOCKED`, rather than inventing a key or storing a passphrase on the VPS.

## Disposition rule

Use one disposition per path and explain the evidence:

- `ALREADY REPRESENTED`
- `KEEP LIVE`
- `PORT SELECTIVE HUNKS`
- `PRESERVE AS EVIDENCE`
- `PRESERVE X3 LINEAGE`
- `OWNER DECISION`

A remote ref preserves the committed donor history, not uncommitted bytes. A local archive preserves bytes, not public source integration. A passing static parse or patch check is not a behavioral test.
