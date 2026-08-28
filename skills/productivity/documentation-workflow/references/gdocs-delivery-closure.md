# `/gdocs` delivery closure and evidence gate

Use this reference for evidence-heavy engineering documentation that must be rendered as a Google Doc in a specific Drive folder and remain reproducible by a later session.

## Closure sequence

1. **Separate evidence boundaries before writing.** Re-audit live files/source/config/logs when available. Keep current counts, historical counts, owner decisions, inference and unknowns in separate rows. Do not silently promote a prior chat summary into current proof.
2. **Verify the destination by metadata, not its display name.** Read the target folder ID, MIME type, owner and parent chain. A display name can contain whitespace or duplicate folders; use the verified folder ID for all writes.
3. **Build the Markdown as the source artifact.** Include a provenance line, verdict-first structure, source register, command blocks, explicit evidence tiers, correction ledger, risks and open items. Run a local preflight for JSON conversion, empty structural headings, placeholders (`TBD`, `TODO`, `<fill>`, `To be filled`), and banned self-reference phrases before touching Docs.
4. **Create an empty Doc.** Do not use plain-text body/append shortcuts for a formatted deliverable. Create the blank Doc, then run `md2ops.py` → `format_doc_v2.py` → `verify_doc.py`.
5. **Treat verifier failures as source defects until proven otherwise.** C1 flags a heading with no body before the next heading. If a section heading is immediately followed by subsections, add a one-sentence orientation paragraph and rerun the full renderer; never hide or waive the defect.
6. **Move after the first structural PASS.** Read the Doc’s current parents, then call Drive `files.update(addParents=TARGET, removeParents=CURRENT)`. Re-read metadata and require exactly one target parent and the Docs MIME type.
7. **Add the actual publication record before the final render.** Record the real Doc ID, link, source marker, render counts, verifier result, parent ID and authentication side effects. Do not leave execution fields such as `TBD` or `To be filled` in the published source. Rerun the renderer after this edit.
8. **Read back the final Doc independently.** Export it as plain text and check H1, provenance marker, expected appendices and zero placeholders. Google exports may prepend a UTF-8 BOM; strip the BOM only for the assertion, not from the source. This is content read-back, not screenshot/pixel QA.
9. **Retain the source and manifest.** Upload the final Markdown and manifest to the same verified folder when the approved package includes them. For arbitrary uploaded files, use `googleapiclient.http.MediaIoBaseDownload` to fetch bytes for SHA-256 comparison; do not assume a wrapper’s media response is a byte buffer.
10. **Disclose OAuth side effects.** Record `google_token.json` mtime before and after the Docs/Drive pipeline. If it changes, state the exact path and time window; do not claim the document was the only filesystem artifact changed.

## Minimum final evidence block

The delivery message should show actual values for the Google Doc URL/ID, target folder and post-move parent list, verifier verdict and defects, native render counts and quota status, source/manifest IDs and SHA-256 round-trip, final export checks, and any failed attempt that was corrected.

## Proven pitfalls

- A structural verifier PASS is not proof of handset delivery, visual screenshot quality, runtime health, or source-to-process byte identity.
- A successful Docs API write is not proof that the Doc is in the requested folder; parent metadata must be re-read.
- A local source file is not proof that the Drive copy matches it; compare downloaded bytes and hashes.
- Do not retain an intermediate manifest after changing Markdown. Regenerate the manifest and ops from the final source before the last render.
- Keep exact historical and current numbers side-by-side when a repair changed the dataset; scope invariants such as `chat_id NULL = 0` to the relevant lane instead of the whole table.
