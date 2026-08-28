# Recovery Evidence Boundaries

Use this reference whenever a VPS/Git audit involves backups, snapshot archives, patches, or an upgrade/recovery decision.

## Never collapse these into one claim

| Claim | Minimum evidence | What it does **not** prove |
|---|---|---|
| **Artifact exists** | Path, size, SHA-256 matches manifest | The artifact contains the intended files. |
| **Capture scope is documented** | Capture script shows included path classes; status/refs evidence | Encrypted/archive contents are byte-exact or restorable. |
| **Snapshot path coverage** | Snapshot status list matches paths that existed at capture time | Files added after the snapshot are covered. |
| **Content integrity** | Archive can be listed/extracted and per-file hashes match expected values | A full runtime restore works. |
| **Restore tested** | Isolated restore + loader/import/health checks pass | Future upgrades are safe unless the tested scope covers upgrade-sensitive work. |

Use the narrowest true label: `ARTIFACT-EXISTS`, `SCOPE-PROVEN`, `CONTENT-VERIFIED`, or `RESTORE-TESTED`.

## Snapshot versus current state

1. Record the snapshot timestamp and snapshot Git refs.
2. Compare the current tracked-modified and untracked path sets against the snapshot status list.
3. Split differences into:
   - existed at snapshot and path-recorded;
   - added after snapshot but represented by source/manifest;
   - added after snapshot and not represented anywhere;
   - content changed after snapshot (requires separate evidence).
4. Do **not** say “all current files are covered by the snapshot” unless the sets and content conditions are both proven.

Same `HEAD` proves a commit identity only. It does **not** prove the full Git object database or every untracked file is byte-identical to the earlier snapshot.

## Upgrade gate

A read-only reconciliation may continue with `SCOPE-PROVEN` evidence. An upgrade/reinstall decision needs an explicit owner gate when either condition exists:

- source-worthy files are only in encrypted/unlisted backup material;
- a patch does not apply/reverse-apply cleanly to the current target;
- source-like paths remain `UNKNOWN` or have unresolved source-of-truth decisions.

State the practical distinction plainly:

> “There is a recovery capture” is not the same as “we have tested restoration of this system.”

## Audit write discipline

- Before resuming after compression or a new chat, inspect prior report path, digest, mtime, and todo state.
- Do not rerun a completed write stage merely because historical context was replayed.
- If the scope permits report output only in a named directory, do not create helper scripts elsewhere unless that scratch path is explicitly authorised.
- Final no-change language must be exact: distinguish application/runtime/Git mutation from authorised report or temporary-analysis artifacts.

## Reviewer without VPS access

Give external reviewers a self-contained brief with four labels:

- `PROVEN-LIVE` — direct VPS command/path/hash evidence;
- `PROVEN-GIT` — public or local Git evidence;
- `PARTIAL` — meaningful evidence but a missing layer;
- `DATA GAP` — not verified.

Ask the reviewer to challenge inference and gates, not to overrule live facts they cannot inspect. Require their response to separate supported conclusions, contradictions, data gaps, minimum gates, and owner-only decisions.
