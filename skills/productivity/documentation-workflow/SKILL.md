---
name: documentation-workflow
description: Create structured engineering documentation (findings, analysis, architecture decisions) as Markdown, then deliver it as a natively formatted Google Doc via the /gdocs pipeline. Owns WHAT goes in the document; /gdocs owns HOW it is rendered.
version: 2.0.1
author: MJ
tags: [documentation, google-docs, engineering, productivity]
supersedes: documentation-workflow 1.1.0
see_also: gdocs 2.0.0
---

# Documentation Workflow v2

## 0. Separation of duties (this fixes the biggest v1 problem)

v1.1 contained its own Docs-creation instructions (Step 3 plain text, Step 3B
"write your own Python script"). `gdocs` v1 simultaneously declared
`docs create --body` **FORBIDDEN**. Two skills, two mechanisms, opposite rules,
and one of them offered the lazy path and called it "acceptable". A low-tier model
resolves that conflict by taking the cheapest route, every time.

v2 rule, absolute:

> **This skill never calls the Docs API.** It produces `doc.md` and then hands off
> to `/gdocs` v2 (`md2ops.py` -> `format_doc_v2.py` -> `verify_doc.py`).
> There is exactly one rendering path in the whole system.

Deleted from this skill on purpose: Step 3 (plain text `--body`), Step 3B
(inline batchUpdate recipe), the Consolas font advice (Consolas is not a Google
Docs font -- use Courier New), and the "100 requests per batch" claim (the
renderer uses 50 for error localisation).

## 1. When to use

- "document findings/analysis/decisions in gdocs"
- session outcomes, architecture review, incident analysis, implementation prep
- any deliverable that a **different session, with no chat history, must be able to execute from**

## 2. Non-negotiable output shape

Engineering documentation, not a research paper. Verdict first, evidence in tables,
commands verbatim.

```
# <Title> -- <Scope>, <Date>
<metadata table: status | version | supersedes | owner | environment | "decisions changed: NONE/list">
> READ THIS FIRST: 3-5 line orientation for a fresh session.

## 0. How to use this document
   entry points per reader + evidence tiers (EVIDENCE / INFERENCE / UNKNOWN)
## 1. Verdict
   1.1 the decision, as a table   1.2 ranked justification   1.3 what is explicitly NOT being done
## 2. Principles / invariants
   each invariant Ix + the command that proves it holds
## 3..N Findings
   every finding: observed -> evidence (command + literal output) -> interpretation -> tier
## N+1 Decisions
   decided / rationale / alternatives rejected + why / who + when
## N+2 Plan
   per phase: IN scope, OUT of scope, exact commands, exit gates (each gate = a command), rollback command
## N+3 Risks, watch items, open items (Ox with what would resolve each)
## N+4 Change log (one row per version, with what changed)
## Appendix A Glossary  (every term used, no exceptions)
## Appendix B Templates (LITERAL full content of every file the plan says to create)
## Appendix C Verification (copy-paste command block that reproduces every number above)
```

## 3. Acceptance gates (Q1-Q10, identical to /gdocs v2 section 2)

A document is not "done", it is **PASS** or **FAIL**. The bar is mechanical:

| # | Gate | Enforced by |
|---|---|---|
| Q1 | zero headings without content | `verify_doc.py` C1 |
| Q2 | every number in a table with source + date | review of paragraph digit density |
| Q3 | every file to be created has literal content in Appendix B | lint |
| Q4 | every exit gate has a runnable command | lint |
| Q5 | zero placeholders (`XX`, `TBD`, `TODO`, `<fill>`) | C4 |
| Q6 | every `see Section N` resolves | C5 |
| Q7 | claims tiered EVIDENCE / INFERENCE / UNKNOWN | review |
| Q8 | verdict before detail | lint (first H2) |
| Q9 | self-sufficient: no "as discussed", "see chat", "as above" | lint banned phrases |
| Q10 | nothing declared is dropped (headings/tables == manifest) | C2, C8, C10 |

**Rule of thumb that replaces every style adjective:** if a sentence contains a
number, it belongs in a table. If a sentence tells the user to do something, it
belongs in a code block. Prose is only for *why*.

## 4. Evidence discipline (this user rejects unverified claims)

- Never write a number you did not read from output in this session. Quote the command.
- If two sources disagree, keep **both** in the table plus a `chosen value + why` column. Do not silently pick one.
- Corrections are first-class: when a number changes, add a change-log row (`old -> new`, why) rather than editing history away.
- Do not claim implementation, validation, or verification because the *document* is finished. Documentation / cleanup / code / tests / live canary are separate statuses.

## 5. Traceability IDs (incident + implementation prep)

`Finding (F) -> Evidence (E) -> Control (C) -> Action (A) -> Solution (S) -> Task (T) -> Verification (V)`

Every item needs a stable ID and at least one backward and one forward link.
No orphan bug lists, no orphan task lists.

## 5A. Canonical decision-record handoff

When the document is intended to become the main reference for a future coding agent or multiple reviewers, do not produce a current-state summary only. Build a self-contained decision record that preserves the reasoning path:

1. State the final verdict and binding decisions first.
2. Record earlier competing claims, contradictions, and the evidence that resolved each one. Do not silently delete superseded recommendations.
3. Separate `DECIDED`, `HOLD`, `UNKNOWN`, `INFERENCE`, and `FORECAST` status. A complete document may still describe an incomplete project.
4. Include the operational baseline, repository topology, dirty/untracked coverage, runtime writers, preservation destinations, approval gates, rollback/acceptance criteria, and explicit out-of-scope items.
5. Include copy-paste prompts for each executor/reviewer and an exact approval string. A future agent must not infer permission from the existence of the document.
6. Keep a versioned change log. Later edits are additive or explicitly mark a prior decision as superseded; never silently rewrite evidence.
7. Verify the rendered Google Doc and its Drive parent metadata before delivery. Report the measured verification block, not merely that the document was created.

Use `references/canonical-decision-record-template.md` for the reusable section contract and handoff checklist.

## 5B. Revision-only and approval-boundary protocol

When revising an existing canonical decision record, treat the document artifact and the operational project as separate state machines:

1. Copy the prior Markdown source to a versioned revision path; preserve the prior version in the change log.
2. Record owner-ratified policy separately from direct evidence, inference, forecast, OPEN, UNKNOWN, and HOLD. A revised document does not grant execution approval.
3. Before rendering, perform only the narrowly requested read-only revalidation. If an old path-level snapshot was not retained, mark deltas UNKNOWN; never infer causes from changed counts.
4. Run `md2ops.py -> format_doc_v2.py -> verify_doc.py`, then verify the Google Docs container metadata separately: title/version, document ID, MIME type, parent folder, and web link.
5. A successful document verifier proves document structure only. Report project status independently: e.g. `document PASS; Gate 1 HOLD; ready for plan-only`.
6. Perform a side-effect audit around authentication and delivery tooling. `setup.py --check` may refresh an OAuth token file — and observed 2026-08-06, the Docs/Drive API calls themselves (docs create, drive search, permissions) also refresh `google_token.json` even when `setup.py --check` was never run; stat its mtime before/after the pipeline and disclose any change. If a refresh happens, disclose the exact file path and downgrade any literal “only document artifact changed” claim. Do not hide tool side effects behind a no-change statement.
7. Do not contact executors, push, upload backup artifacts, or execute an operational gate unless the user gives a separate, exact approval.

See `references/reconciliation-v1.1-audit-pattern.md` for the reusable evidence and verification pattern.

## 5C. Recovery and deletion runbooks

For recovery documentation created before a destructive operation or upgrade, the document must be executable by a fresh session without relying on chat history:

1. Define the exact removed/deleted path set and the corresponding artifact ID or destination for every path.
2. Separate `DOCUMENT-PASS`, `ARTIFACT-PRESENT`, `HASH-PASS`, `LIST-PASS`, `DECRYPT-PASS`, `RESTORE-PASS`, and `LIVE-SMOKE-PASS`; never collapse these into one `verified` label.
3. Record archive root names, member counts, hashes, and the command that produced each value. If a source archive is associated with a deleted path by naming or path-set comparison, label it `INFERENCE / recovery mapping` unless original path metadata or a byte-level manifest proves identity.
4. Make all restore commands stage into a new temporary directory first and refuse to overwrite an existing live target. Include an explicit safe-member check for absolute paths and `..` traversal.
5. State what the artifact does not contain, especially separate private runtime/session state such as WhatsApp authentication.
6. Verify the final Google Doc independently: document ID, title, MIME type, Drive parent, owner-only permissions, source marker, and rendered-document gate result.

A recovery runbook is complete when the document is structurally PASS and the limitations are explicit. It is not evidence that the system has been restored or upgraded.

Use `references/recovery-runbook-google-doc-delivery.md` for the reusable archive-mapping, safe-staging, Drive-parent verification, and C1 remediation pattern.

## 6. Drive delivery

```bash
SK="$HOME/.hermes/skills/productivity/google-workspace/scripts"
GAPI="python3 $SK/google_api.py"
python3 $SK/setup.py --check          # Drive + Docs scopes are enough
$GAPI drive search "OVIS" --max 5
$GAPI drive search "Hermes Agent" --max 5     # NOTE: trailing space in the name
$GAPI drive create-folder "<project>" --parent HERMES_AGENT_FOLDER_ID
```

Convention: `OVIS/Hermes Agent /<project>/`. Verify parent IDs from Drive
metadata and filter search results by `mimeType = application/vnd.google-apps.folder`.

Then hand off to `/gdocs` v2 for creation, rendering, and verification. For the full post-render closure gate — parent metadata, final export read-back, source/manifest hash round-trip, BOM handling, C1 repair and OAuth mtime disclosure — load `references/gdocs-delivery-closure.md`.
Deliver: Docs URL + Drive folder path + `verify.json` verdict + `MEDIA:` the `.md` file.

## 7. Keep the Markdown

`doc.md` is the artifact, not a by-product:

```bash
cp "$WORK/doc.md" ~/wiki/decisions/NNNN-<slug>.md    # or runbooks/ , wiki/
```

Google Docs is the sharing surface. The repo copy is the source of truth, is
greppable, diffable, and is what future sessions read.

## 7A. Reading / ingesting an existing gdoc (user-supplied link or ID)

This skill also governs the READ path, not only authoring. When the user pastes a
`docs.google.com/.../d/<ID>` link, says "read this gdoc", or says "use our
gdocs/gdrive skills", do NOT hunt for the document via `session_search`,
`search_files`, or `find`. The user already gave you the ID and auth is live —
read it directly. (Verified correction 2026-08-14: agent wasted 3 turns on
session_search + filesystem grep before the user said "just use the skills".)

Steps (load `google-workspace` skill first via `skill_view(name="google-workspace")`):

```bash
SK="$HOME/.hermes/skills/productivity/google-workspace/scripts"
GAPI="python3 $SK/google_api.py"
DOC_ID="17QE-tOvMYn9jd6-IA-8UI6kgcU_YhvDDCpfYopgJy1w"   # the ID from the user's link

# Short doc (<~5KB body): docs get returns full JSON; body is a plain-text string.
$GAPI docs get "$DOC_ID" > /tmp/doc.json

# Long doc: docs get TRUNCATES the body string (~6-7KB cutoff, marked "[truncated]").
# Use Drive text export for the complete, reliable read:
$GAPI drive download "$DOC_ID" --export-mime text/plain --output /tmp/doc.txt
```

Pitfall — `docs get` body truncation (verified 2026-08-14): a 6.8KB doc came
back with `[truncated]` inside the body string via `docs get`; the same doc read
fully (79 lines, 6827 bytes) via `drive download --export-mime text/plain`. For
any doc longer than a few KB, prefer the Drive export. Tables are flattened to
text in the export — acceptable for reading/analysis; use the `walk_structural`
table walker from the google-workspace skill only when you need table structure
from `docs get`.

## 8. Pitfalls (each one has bitten this workflow):

1. Two rendering paths -> always the lazy one wins. There is now one path.
2. `docs create --body "."` leaves a literal `.` in the body. Create empty.
3. Google Docs never renders Markdown syntax. `#` stays visible. Use the pipeline.
4. API 200 != correct document. Read back with `verify_doc.py`.
5. Partial formatting = invalid deliverable. Re-run the renderer (it clears first).
6. Folder search is imprecise; filter by mimeType, prefer known folder IDs.
7. 1MB per Doc. If the Markdown exceeds ~700KB, split by top-level section.
8. Academic drift: if it reads like background -> methodology -> results, restructure to verdict-first.
9. Send the file with `MEDIA:` -- never tell the user where to find it.
10. Do not start implementing while the user asked for documentation and preparation.
11. **C1 false-positive on structural headings.** `verify_doc.py` C1 flags any heading with no body paragraph before the next heading. This catches report sections that are pure section-dividers (e.g. `## 7. Findings` followed by `### 7.1 Network`). Ensure every parent heading includes an intro sentence before child subheadings to pass `verify_doc.py` cleanly.
12. **When evaluating external document skills (e.g. anthropic `docx`), remember they are mechanical-only.** The docx skill (source-available, NOT open-source — port ideas, never code) contains zero content-structure guidance; our verdict-first/Q1-Q10 formatting is our own strength and is what the user wants kept. See `references/anthropic-docx-skill-analysis.md` for the full gap analysis + planned gdocs upgrade scope.
13. **Drive wrappers may not expose every Drive API action.** If a requested move/parent operation is explicitly authorized but the wrapper rejects the action as unsupported, report that failure and use the direct Drive API `files.update(addParents=..., removeParents=...)`; then re-read parent IDs, MIME type, title, link, and permissions. Do not claim the move from a command that never executed.
14. **Archive names are not original filesystem identities.** For deleted overlays or snapshots, preserve the exact archive root, hash, member count, and path-set comparison. Call the old-path association a recovery mapping/inference unless a manifest proves byte identity. Keep original-folder restoration and archive-equivalent reconstruction as separate statuses.
15. **Reading a gdoc the user sent: do NOT hunt, read directly.** When the user
pastes a `docs.google.com` link or says "use our gdocs/gdrive", load the
google-workspace skill and read via `$GAPI docs get DOC_ID` (short) or
`drive download DOC_ID --export-mime text/plain` (long — `docs get` truncates).
The user already supplied the ID; auth is live. `session_search` / `search_files`
/ `find` are the wrong tools for a document the user just handed you — that
detour wasted three turns on 2026-08-14 and drew a direct correction.
