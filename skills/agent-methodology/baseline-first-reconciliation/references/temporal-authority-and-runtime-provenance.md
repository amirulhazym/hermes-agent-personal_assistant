# Temporal Authority and Runtime Provenance

## Pattern key

`temporal-authority-over-document-baseline`

## Problem

A supplied GDoc, wiki, or design record can be **canonical for intent** yet still be only a baseline snapshot. It may predate Git access, a later merge, deployment, or a known-working runtime implementation. Treating it as the recovery payload can overwrite newer, intended behavior with older information.

A branch or worktree is not automatically the “latest recoverable source” either. Its name, HEAD date, or presence on disk does not prove it is the owner-designated working version.

## Authority model

| Role | What it proves | What it does not prove |
|---|---|---|
| Baseline documentation | Intended invariants, original design, historical scope | Latest implementation or live deployment |
| Owner-specified cutoff | Which period/artifact must be recovered | That the artifact has been located |
| Git commit/tree | Versioned source bytes at a point in time | That those bytes reached runtime |
| Deployment manifest/hash | Intended destination bytes | That the process loaded/reloaded them |
| Direct runtime probe | Current observed behavior | Historical lineage or which artifact caused it |
| Chat/log statement | Lead for search and expected behavior | Source/deployment proof by itself |

## Procedure

1. Record the owner’s temporal boundary exactly: date, timezone, and wording such as “latest known working version as of <cutoff>.”
2. Classify every document before relying on it: **baseline-design**, **candidate-build**, **release manifest**, **runtime evidence**, or **historical claim**.
3. Search for artifacts at or immediately before the cutoff: Git commits/trees, preserved worktrees, deployment manifests, source hashes, service logs, and runtime outputs.
4. For each candidate, prove two independent links:
   - **time/provenance:** it belongs to the requested period;
   - **behavior:** it contains the expected working contract or passes an isolated probe.
5. If neither link is proven, label the candidate `POSSIBLE DONOR — UNVERIFIED`; do not call it newest, correct, or recovery-ready.
6. If the targeted artifact cannot be located, report `LATEST OWNER-DESIGNATED ARTIFACT NOT LOCATED`. Continue only with an owner-approved reconstruction or a bounded current-defect repair.
7. Keep repair lanes separate. A proven current defect may justify a minimal isolated patch, but it is not evidence that the patch restores the requested historical version.

## Minimum report row

| Artifact | Role | Relation to cutoff | Direct evidence | Status |
|---|---|---|---|---|
| `<doc/path>` | baseline-design | predates cutoff | document metadata + owner statement | intent only |
| `<commit/tree>` | candidate-build | at/before cutoff | commit time + tree/hash | provenance pending/confirmed |
| `<runtime probe>` | current runtime | after cutoff | raw command/test output | current behavior only |

## Red flags

- “The doc says deployed, so it is the version to restore.”
- “This worktree is newer, therefore it is the desired latest source.”
- “The current runtime fails, therefore the old doc caused the regression.”
- “A candidate test passes, so it must be what ran live.”
- “We found a compatible patch, so recovery is complete.”

Each is a provenance gap, not a conclusion.
