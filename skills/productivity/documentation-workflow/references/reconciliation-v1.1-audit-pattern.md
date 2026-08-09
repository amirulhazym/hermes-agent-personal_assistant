# Canonical Decision-Record Revision Audit Pattern

Reusable pattern for revising a verified Google Doc without accidentally converting documentation work into operational approval.

## 1. State separation

Track four independent states:

- Document artifact: Markdown source, rendered Google Doc body, container metadata.
- Read-only baseline: timestamped runtime/repository observations.
- Operational gate: preservation/integration/deployment approval, normally HOLD until separately approved.
- Tool side effects: authentication refreshes, local caches, or metadata writes caused by the documentation pipeline.

Never infer that `verify_doc.py: PASS` means the operational gate passed.

## 2. Revision sequence

1. Copy the prior Markdown source to a versioned path.
2. Add a change-log row; do not silently erase superseded evidence.
3. Add the owner-ratified policy changes and label each item by evidence tier: OWNER-RATIFIED, EVIDENCE, INFERENCE, FORECAST, OPEN, UNKNOWN, or HOLD.
4. Run only narrowly necessary read-only refreshes. Use the current timestamp in MYT.
5. If historical path-level output was not retained, report count changes as UNKNOWN; do not invent the cause.
6. Render with `md2ops.py`, `format_doc_v2.py`, then `verify_doc.py`.
7. Verify container metadata independently: title contains the new version, document ID is unchanged or explicitly recorded, MIME type is Google Docs, parent folder is correct, and a reachable link exists.
8. Deliver the Markdown source as an attachment and report both document verdict and project gate status.

## 3. Mutation audit

Before final wording, inspect all tool output for side effects. Authentication checks can refresh credential files. If a refresh occurs:

- name the exact path without exposing credential values;
- state that the literal “only document artifact changed” claim is not supportable;
- distinguish this from application code, runtime database, process, Git ref, deployment, backup, and external-upload mutations;
- record the exception in the decision record itself.

Do not silently rerun the authentication check to make the side effect disappear from the report.

## 4. Safe final status language

Use a two-axis conclusion:

- `Document: PASS` means the rendered document matched its manifest and had zero verifier defects/blockers.
- `Operational gate: HOLD` means execution still requires its own checkpoint and exact approval.
- `READY FOR OPENCODE PLAN-ONLY` means the document may be shared for plan drafting; it does not authorize preservation, Git changes, pause/restart, upload, push, merge, or deployment.

## 5. Evidence minimum

For every current proof claim, retain:

- exact command/method;
- timestamp;
- raw result or a sanitized result with the limitation stated;
- expected-vs-observed interpretation;
- whether the check was read-only.

For repository state, include HEAD, branch, staged count, tracked-dirty count, untracked count, stash status, worktree status, and the distinction between the live runtime repository and the clean application-source clone.
