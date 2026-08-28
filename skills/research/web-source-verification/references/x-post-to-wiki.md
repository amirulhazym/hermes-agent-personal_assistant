# X/social post → verified wiki capture

Use this reference when a user shares an X/social post and asks to read it, understand it, outline it, ideate from it, or save it into the local wiki.

## Provenance split

Keep three layers separate:

1. **Post evidence** — what the author literally said. A raw capture can prove this, but not that the product works.
2. **Primary-source evidence** — official README, repository/API metadata, docs, merged source/PR, or live configuration that supports or contradicts the claim.
3. **Local/live evidence** — commands or file reads from the current environment. Upstream main, a social post, and the installed runtime are different states.

Use explicit labels: `VERIFIED`, `UNVERIFIED`, `PARTIAL`, `NOT TESTED`, `[Legacy Context]`, or `Design inference`. Never upgrade a social claim to a product fact merely because the post is detailed or several AI summaries agree.

## Retrieval ladder for X posts

1. Fetch the original X URL first.
2. If the extractor returns a partial/truncated body, say so internally and preserve the original URL as the source of record. Do not call the capture complete.
3. Try a distinct read-only route that can return the note-tweet body, such as a syndication/mirror endpoint when available. In the 2026-08-18 Hermes capture, `https://api.fxtwitter.com/<user>/status/<id>` returned the complete body after direct X extraction stopped partway through. Treat the endpoint as a retrieval aid, not as the authoritative source.
4. Use oEmbed or search snippets for identity/link discovery only. A snippet is not evidence for the missing body.
5. Save the raw body to `~/wiki/raw/YYYY-MM-DD-<slug>.md` with complete vault frontmatter. Include:
   - original URL;
   - author and source timestamp if returned;
   - retrieval route(s), including a partial/direct extraction note;
   - a sentence saying the file captures what the post says and is not independent proof.
6. Reconcile every load-bearing product claim against the official primary source before calling it verified.

## Primary-source reconciliation

For a product/tool claim:

- Prefer the current official README/docs/source over a social post.
- If GitHub HTML extraction fails, recover the raw README and repository API metadata.
- Check for status changes such as archived repositories, bundled/default-on features, renamed paths, or legacy install instructions.
- If a PR describes validation numbers, label them maintainer-reported unless independently reproduced.
- If upstream main is newer than the installed runtime, record version skew. Do not infer that the local runtime has the upstream feature.

## Wiki synthesis shape

Update an existing canonical note when the topic already has one; do not create a duplicate capture note just because a new post appeared. Keep the raw capture separate under `raw/`.

A good canonical note contains:

1. **Verdict** — what is true, stale, misleading, or still untested.
2. **Source outline** — concise numbered summary of the post.
3. **Primary-source reconciliation** — what official sources confirm or correct.
4. **Live-environment boundary** — exact commands/results and explicit `NOT TESTED` gaps.
5. **Architecture fit** — separate product fact from design assessment.
6. **Ideation** — recommended roles/approaches, labelled as ideas rather than implementation.
7. **Guardrails/non-goals** — especially authority, provenance, delivery, state, and safety boundaries.
8. **Status boundary** — capture complete, synthesis complete, live test not done, side effects not performed.
9. **Sources** — generated from the citation ledger.

For the Hermes wiki, every written markdown file needs complete frontmatter; `raw/` is greppable but not indexed; every write must be followed by a git commit.

## Citation ledger workflow

Before drafting a cited note, register the URLs in the grounded-citations ledger:

```bash
S=~/.hermes/skills/research/grounded-citations/scripts/sources.py
python3 "$S" reset
python3 "$S" add <url> --title "<title>"
```

Use the returned `[n]` IDs while drafting, then generate and verify the Sources block:

```bash
python3 "$S" render --replace-in ~/wiki/<note>.md
python3 "$S" verify ~/wiki/<note>.md --strict
```

`citations OK` proves citation IDs and the Sources block are internally consistent; it does not prove the cited product claims are true.

## Completion evidence

Before reporting completion:

- re-read the saved canonical note and raw capture;
- run citation verification;
- run `git diff --check`;
- inspect `git show --stat --oneline HEAD` after committing;
- inspect `git status --short --branch` and report unrelated untracked artifacts instead of claiming the whole worktree is clean;
- distinguish committed files from candidate/live/deployed state.

If a vault-wide frontmatter scan finds a pre-existing cache artifact without frontmatter, report it as out-of-scope and do not silently delete it. Verify the files created or modified by the current task directly.
