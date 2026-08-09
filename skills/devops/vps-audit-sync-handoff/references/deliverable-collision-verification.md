# Pre-existing Deliverable Collision — decision flow (2026-08-06 reconciliation audit)

Scenario: target deliverable path already holds a report from a prior (expired) session.
This file is the step-by-step that worked.

## Why not just trust or overwrite
A prior agent's report is self-attestation, not evidence. It may contain real
verification results from a legitimate prior run, or fabricated/mislabeled detail.
Both possibilities need the SAME treatment: re-derive the load-bearing claims live.

## Decision flow
1. `read_file` the ENTIRE existing artifact (paginate; do not decide on first 60 lines).
2. Identify claims you did NOT personally observe. These are the re-verify targets.
3. Re-run each against live state, read-only. Batch them in one terminal call.
4. If all substance holds → KEEP + PATCH, deliver as validated.
   If any fails or is ambiguous → correct it in the .md (record correction + timestamp),
   then deliver.
   Never silently rewrite history — a correction is a change-log addition, not an edit-away.

## Commands that catch the common failure modes
```bash
# (1) hash-algorithm mismatch: value marketed as 'sha256' but 32 hex = MD5
crontab -l | sha256sum       # 64 hex — correct
crontab -l | md5sum          # 32 hex — the mislabeled value
# Rule: sha256 ALWAYS 64 hex chars. See the cell length before trusting the label.

# (2) patch present in worktree (exit 0 = already applied)
git apply --reverse --check <patch>
# isolate a single file claim:
git apply --reverse --check --include='path/to/file' <patch>

# (3) tags peel to expected commits
git cat-file -p <tagname-tagobject>   # 'object <sha>' line = peel target
git rev-list -n 1 <tagname>           # peeled commit

# (4) DB schema/counts, read-only, on large SQLite (avoid quick_check >180s)
python3 - <<'EOF'
import sqlite3
c = sqlite3.connect('file:/path/state.db?mode=ro', uri=True)
print(len(c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()))
EOF

# (5) nested clone dirty-line counts agree, no remotes
git status --porcelain=v1 | wc -l
git remote -v

# (6) GitHub auth probe (no ref created)
GIT_TERMINAL_PROMPT=0 timeout 40 git push --dry-run origin HEAD:refs/heads/temp/probe
git ls-remote --heads origin temp/probe   # must show 0 / absent
```

## Docs-build ordering
Fix the Markdown BEFORE building the Google Doc — the .md is source of truth, the
Docs render inherits its correctness. Then: md2ops.py → format_doc_v2.py → verify_doc.py
→ verify.json verdict === PASS. Correct .md, re-generate ops, re-render.

## Token side-effect audit (documentation-workflow §5B)
Stat google_token.json BEFORE and AFTER the Docs/Drive pipeline:
`stat -c '%y' ~/.hermes/google_token.json`
The API calls themselves (docs create, drive search, permissions) refresh the token
file even when setup.py --check was never run. If mtime changed, disclose the path and
downgrade any "only document artifact changed" claim.