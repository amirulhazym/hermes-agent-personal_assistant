---
name: hermes-release-deploy
description: Exact-SHA, manifest-driven promotion and deployment after one explicit owner release approval.
---

# Hermes Release & Deploy

This procedure is forbidden until the owner provides the exact approval:
`APPROVE RELEASE <full-sha>`. Candidate construction alone does not authorize
promotion, deployment, restart or channel verification messages.

## 1. Distinguish the hashes

Keep these fields separate:

- `base_main_sha`: verified source base;
- `candidate_sha`: tested Git commit to approve;
- `payload_hash`: optional hash of a generated manifest/package payload;
- per-file `source_hash`: Git-object content hash/hash algorithm as documented;
- `deployed_hash`: observed live destination hash after deployment.

A payload hash is not a candidate SHA and must not be used as one.

## 2. Validate the complete manifest

Every intentionally source-managed destination in the release must have an
explicit manifest row. Validate source existence at `candidate_sha`, source
hash, explicit safe destination under `/home/ubuntu/.hermes`, mode/ownership,
and no wildcard/recursive/delete action. Reject secret, database, session,
private-memory, log and credential destinations.

Before overwrite, compare the live destination against the manifest and check
for newer live customization. Preserve readable newer state/diffs before any
write. Never silently overwrite a newer live source-like file.

## 3. Controlled deployment

Create and verify a mode-700 rollback snapshot, stage atomically, deploy only
manifest rows, preserve modes, and keep a rollback path. Any failure is HOLD
and triggers rollback only through the approved recovery procedure.

## 4. Verify and finalize

Verify every deployed hash, gateway/channels/cron/DB invariants and isolated
smoke tests. Record candidate/payload/deployed hashes distinctly. Only after
all checks and owner approval may `main` be promoted and the runtime changed.
Temporary branches/artifacts are cleaned only under the approved post-release
flow; never force-push or delete preservation evidence.
