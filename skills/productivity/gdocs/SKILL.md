---
name: gdocs
description: "Create properly formatted Google Docs from a single Markdown source of truth. Deterministic pipeline: doc.md -> md2ops.py -> format_doc_v2.py -> verify_doc.py. Trigger: any message starting with /gdocs."
version: 2.0.0
author: Hermes
trigger: "/gdocs"
platforms: [linux, macos]
requires:
  - google_token.json (OAuth2 authenticated)
  - scripts/md2ops.py
  - scripts/format_doc_v2.py
  - scripts/verify_doc.py
supersedes: gdocs 1.0.0
---

# gdocs v2 -- Markdown is the document. Google Docs is a rendering.

## 0. What changed from v1 and why (read once)

v1 told the model to "plan content AND formatting together" and to hand-write
`ops.json`. Measured result on a real deliverable: **0 tables, 5 headings with no
content, one section body that was literally `.`, an unfilled `18:XX` placeholder,
a heading rendered as `## F`, and prose referring to tables that did not exist.**

Root cause was not model laziness. It was the toolchain:

| v1 defect (measured) | Real cause |
|---|---|
| 0 tables in a table-driven doc | `format_doc.py` v1 had **no table op**. Tables were impossible. |
| Numbers moved into prose | Same. No table -> the model paraphrased data. |
| Section body = `.` | `docs create --body "."` seed dot survived into the body. |
| `## F` broken heading | Hand-written ops + drifted index arithmetic. |
| Whole-paragraph bold only | v1 could not style a run inside a paragraph. |
| Empty headings shipped | "Verify" was an opinion, never a machine check. |

v2 removes the failure modes instead of asking for more discipline:

1. **One authoring artifact.** You write `doc.md`. Nothing else. `ops.json` is generated.
2. **The renderer can express the content**: tables, nested lists, inline runs, code blocks, callouts.
3. **A machine decides whether you are done.** `verify_doc.py` exits non-zero and you may not report success until it exits 0.

## 1. Pipeline (do exactly this, in this order)

```bash
SK="$HOME/.hermes/skills/productivity/google-workspace/scripts"
GAPI="python3 $SK/google_api.py"
WORK="$HOME/.hermes/tmp/gdocs/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$WORK"

# 1. WRITE the document as Markdown. This file is the deliverable and the archive copy.
#    (write_file to "$WORK/doc.md")

# 2. GENERATE ops + manifest mechanically. Never hand-write ops.json.
python3 $SK/md2ops.py "$WORK/doc.md" --manifest "$WORK/manifest.json" > "$WORK/ops.json"

# 3. SELF-CHECK the Markdown before spending API calls.
python3 $SK/lint_md.py "$WORK/doc.md"        # if present; else see section 3 gates

# 4. CREATE an empty doc. Note: --body "." is FORBIDDEN (it leaves a stray dot).
$GAPI docs create --title "TITLE"             # capture documentId

# 5. RENDER.
python3 $SK/format_doc_v2.py DOC_ID < "$WORK/ops.json"

# 6. GATE. You may not report success unless this exits 0.
python3 $SK/verify_doc.py DOC_ID --manifest "$WORK/manifest.json" \
        --json "$WORK/verify.json"; echo "exit=$?"

# 7. VERIFY PLACEMENT + DELIVER the .md file itself.
# Preserve existing owner-only ACL by default. Sharing (especially anyone/reader)
# is an external privacy change and requires explicit owner instruction.
# respond with: MEDIA:$WORK/doc.md  +  the Docs URL  +  the verify.json verdict line
```

### Placing the doc in a specific Drive folder (verified 2026-07-31)

`docs create` lands the doc in Drive root. The CLI has NO `move` subcommand, and
`drive search` rejects compound queries (`name contains X and mimeType='...'`)
with `Invalid Value` unless `--raw-query` is passed.

1. Find the target folder ID:
   `$GAPI drive search "mimeType='application/vnd.google-apps.folder' and name contains 'Folder Name'" --raw-query --max 10`
   or pull `parents` from an existing doc in that folder via `$GAPI drive get DOC_ID`.
2. Move using the module's service builder (one-liner, no new files, works even
   when the `gws` binary would reject the token's `type` field):

```bash
cd "$SK" && python3 -c "
import sys; sys.path.insert(0, '$SK')
from google_api import build_service
svc = build_service('drive','v3')
res = svc.files().update(fileId='DOC_ID', addParents='FOLDER_ID', removeParents='root', fields='id,parents,name').execute()
print('MOVED:', res.get('name'), '->', res.get('parents'))
"
```

3. Verify placement: `$GAPI drive get DOC_ID` and confirm its `parents` contains the intended folder ID. Verify ACLs only when sharing was explicitly requested.

**Folder-name mismatch fallback:** Names are display labels, while folder IDs are authoritative. If an exact child-folder query returns no result, do **not** create a replacement folder. List folder children of the already verified parent ID, inspect returned names for whitespace/case differences, then use the returned child folder ID and read it back after moving. This avoids duplicate folders such as `Hermes Agent` versus an existing `Hermes Agent `.

**FORBIDDEN for /gdocs:** `docs create --body`, `docs append --text`, hand-written
`ops.json`, ad-hoc one-off Python formatting scripts, and dumping raw Markdown into
the Docs body. If a step fails, fix and re-run `format_doc_v2.py` -- it clears the
body first, so re-running repairs instead of duplicating.

## 2. Content contract (the part that decides quality)

These are not style preferences. Each one is checked by `verify_doc.py` or `lint_md.py`.

| # | Rule | Machine check |
|---|---|---|
| Q1 | Every heading has content before the next heading. Zero empty headings. | C1 |
| Q2 | Every number appears in a **table row together with its source and date**, never bare in prose. | lint: digit-density in paragraphs |
| Q3 | Every file the doc says must be created has its **literal full content** in an appendix code block. | lint: `create .*\.(md\|py\|sh\|json)` -> appendix fence exists |
| Q4 | Every exit gate / acceptance criterion has a **runnable command** that produces its evidence. | lint: gate section contains a fence |
| Q5 | Zero placeholders: `XX`, `TBD`, `TODO`, `FIXME`, `<fill>`, `...`. Unknown -> write `UNKNOWN` plus what would resolve it. | C4 |
| Q6 | Every `see Section N` resolves to a heading that actually contains data. | C5 |
| Q7 | Claims are tiered: `EVIDENCE` (command output / file quoted), `INFERENCE` (reasoning stated), `UNKNOWN`. Never present inference as evidence. | lint: tier tokens present when doc has findings |
| Q8 | Verdict first. Section 1 states the decision; detail comes after. | lint: first H2 is Verdict/Summary/Decision |
| Q9 | Self-sufficient: a fresh session with no chat history can execute from the doc alone. No "as discussed", "as above", "see chat". | lint: banned-phrase list |
| Q10 | Nothing declared is dropped: headings and tables in the doc == manifest. | C2, C8, C10 |

## 3. Markdown you may use (all of it renders natively)

```markdown
# Title            -> HEADING_1        | table -> real Docs table w/ shaded header row
## / ### / ####    -> HEADING_2/3/4    | ```fence``` -> Courier New + shaded paragraph
- item / 1. item   -> native bullets, 2-space indent = nested level
**bold** *italic*  -> inline runs (works mid-sentence)
`mono` [x](url)    -> inline mono / hyperlink
> quote            -> indented shaded callout
| a | b |          -> use <br> inside a cell for a line break, \| for a literal pipe
```

Unsupported on purpose: images, footnotes, HTML. Do not use them; they will be
dropped silently by the converter and caught as a manifest mismatch.

## 4. Failure handling

- `format_doc_v2.py` exit 2 -> the doc is **partially formatted = invalid deliverable**. Re-run it. If it fails twice, trash only the doc you created and start from step 4.
- `verify_doc.py` exit 1 -> read `defects[]`, fix `doc.md`, then re-run steps 2, 5, 6. Never fix the Doc by hand: Markdown is the source of truth.
- **OAuth preflight failure** (`TOKEN_REVOKED`, `invalid_grant`, or unauthenticated): do not attempt Docs creation, Drive placement, or sharing. You may still create and validate `doc.md`, `ops.json`, and `manifest.json` locally, then generate a fresh authorization URL with the supported bare command: `python3 $SK/setup.py --auth-url`. The user must complete consent and paste the complete localhost redirect URL; exchange it with `--auth-code`, then run `$GAPI drive ...` auth/read checks before resuming rendering. Report the document as **LOCAL SOURCE READY / DRIVE PUBLISH BLOCKED**, never as created or saved.
- Never report "created and verified" without pasting the `verdict` and `measured` block from `verify.json`.

### google_token.json `type` field stripped by write_file security redaction

**Problem:** `write_file` parses JSON files and security-redacts sensitive values (`token`, `refresh_token`, etc.) with `***`. During this redaction, the parser may **silently drop the `type` field** (required value: `"authorized_user"`). After this, `$GAPI drive ...` commands fail with:
```
error[auth]: Authentication failed: Failed to parse authorized user credentials from /home/ubuntu/.hermes/google_token.json: missing field `type`
```

The Docs API calls (`docs create`, `format_doc_v2.py`, `verify_doc.py`) work fine because `google_api.py`'s `_normalize_authorized_user_payload()` adds the field. Only **drive operations** (`drive share`, `drive create-folder`, `drive search`) fail because they route through `gws` binary which strictly validates.

**Fix:** Never use `write_file` to modify `google_token.json`. Use terminal + Python instead:
```bash
python3 -c "
import json
with open('/home/ubuntu/.hermes/google_token.json') as f:
    data = json.load(f)
data['type'] = 'authorized_user'
with open('/home/ubuntu/.hermes/google_token.json', 'w') as f:
    json.dump(data, f)
"
```

**Prevention:** After any `write_file` to `google_token.json`, check with:
```bash
python3 -c "import json; d=json.load(open('/home/ubuntu/.hermes/google_token.json')); print('Has type:', 'type' in d)"
```
If `Has type: False`, apply the terminal fix above before running drive commands.

### C1 false positive: structural headings (heading → immediate sub-heading)

C1 ("heading has no content") fires when a heading has no body paragraph between it and the next heading. This is intentional for **structural section dividers** — headings that introduce a group of sub-sections (e.g. `# 7. Findings` immediately followed by `## 7.1 Network`). The content IS the sub-headings.

**If you can edit the doc.md:** Add a one-sentence intro paragraph between the structural heading and its first sub-heading to satisfy C1.

**If the user explicitly forbids content changes:** Acknowledge the FAIL verdict transparently in your delivery — paste the verify.json `defects[]` array, explain the false-positive reason, and deliver the doc anyway. C1 structural-heading blockers alone do not make the doc invalid for the reader; they only mean the automated gate cannot certify it. Do NOT modify the doc content against the user's instruction.

Note: this pattern cannot be silenced by editing the Markdown alone if `verify_doc.py`'s C1 check does not understand heading hierarchy. A future `verify_doc.py` fix could allow structural headings at the cost of weakening the "zero empty headings" invariant — patch the script rather than the skill when that decision is made.

## 5. Updating an EXISTING doc in place (same DOC_ID)

The pipeline is also the update path: `doc.md` is the source of truth and the
Doc is a rendering, so updating = editing `doc.md`, regenerating ops, and
re-rendering the SAME `DOC_ID` (format_doc_v2 clears the body first — no
duplicate content, no second doc).

1. Locate the existing doc: `$GAPI drive search "<title fragment>" --max 5` or
   read `create.json` in the doc's workspace dir for its `documentId`.
2. Read the full existing `doc.md` FIRST (paginate with offset/limit). Never
   blind-overwrite a doc that may contain history.
3. Edit additively for living reference docs (user convention 2026-08-09:
   "almost everything been logged", docs are additive-only — never remove
   content). Pattern that works: bump Version row, update Document status row,
   append a Change log row (version/date/change/reason), then INSERT new
   sections immediately BEFORE `## Change log` via patch — not by rewriting.
4. Re-run the same pipeline: `md2ops.py` → (lint if present) →
   `format_doc_v2.py DOC_ID < ops.json` → `verify_doc.py DOC_ID --manifest`.
   Verify must exit 0 before reporting success.

Pitfalls (verified 09 Aug 2026):
- Large doc.md additions: patch in chunks (~6KB per call), not one giant
  write_file — oversized tool calls stream-timeout before delivery.
- `ops.json` is single-line JSON: `wc -l` reports 0 even at 100KB+. Check
  `wc -c` instead before assuming the generation failed.
- `lint_md.py` may be absent from `google-workspace/scripts`; that is fine —
  `verify_doc.py`'s gates (C1/C2/C4/C5/C8/C10 + manifest equality) cover the
  content contract. A missing lint script is not a failure.
- Numbered tables in new sections must be present in the regenerated
  manifest, or C2/C8 fails. md2ops regenerates it — just don't reuse the old
  manifest.

## 6. Final response format

```
Title: <doc title>
URL: https://docs.google.com/document/d/DOC_ID/edit
Verify: PASS (headings 70/70, tables 34/34, mono lines 297)
Summary: <one paragraph>
MEDIA:/abs/path/doc.md
```

Do not paste the whole document into chat unless asked.
