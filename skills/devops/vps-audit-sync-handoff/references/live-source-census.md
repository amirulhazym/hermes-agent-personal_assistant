# Live↔Source Census (read-only) — technique & verdict framing

Verified 2026-08-07 on the Hermes VPS for the FULL LIVE↔SOURCE CENSUS (the
reviewer's "prove every source-worthy live path is represented in main" task).
Reuse when the user wants to prove main↔live alignment, find what of their
daily live changes is NOT reposited, or prep a clean baseline before an
upgrade/re-deploy.

## The reframing that matters (answer the user's confusion first)

User's recurring worry: *"lots of live changes via WS/Tele don't align on main
after merge — is that mine not committing?"*

Answer pattern (proven correct): **live≠main is BY DESIGN for runtime state**
— `memories/*`, real `config.yaml`, `cron/jobs.json`, `state.db`/WAL/SHM, med
state, sessions, logs, caches, the upstream `hermes-agent` code, and upstream
skill packs are SUPPOSED to be private/runtime/upstream and never enter main.
This is enforced by the AGENTS.md constitution + Gate 4 classification. So
"not aligned on main" is NOT automatically a gap — do NOT push it all into git.

The REAL gaps are only: **source-worthy customizations that exist live but are
not tracked/patched** (custom skills, plugins, hooks, scripts drift, post-patch
nested additions, config template drift, stale docs, obsolete persona files
with privacy risk). Distinguishing "expected runtime" from "real gap" is the
whole value of the census.

## Inventory approach (script, not manual)

Write a `census_inventory.py` in `/tmp` (never in the audit workspace /
reports dir — contamination rule) that:

1. **Source manifest**: `git ls-tree -r <MAIN> --name-only` → tuple of hashes of
   every tracked file (hash the WORKTREE bytes, not git show, for speed —
   compare the worktree at the pinned commit).
2. **Nested upstream**: `git -C <nested> status --porcelain` → split ` M`/`M `
   (modified) vs `??` (untracked); `git rev-list --count @{u}..HEAD` for local
   commits.
3. **Live source-like dirs to walk** (bounded, EXCLUDE venv/node_modules/.git/
   __pycache__): `skills/ plugins/ hooks/ scripts/ agents/ plans/ design/
   platforms/`. Hash each file; classify per-path:
   - path also tracked in main → **SOURCE-MATCH** (hashes equal) or
     **LIVE-NEWER-DRIFT** (hashes differ)
   - live-only → **LIVE-ONLY-UNTRACKED**
4. Emit one JSONL per record + a CSV (sortable) + a `_inventory_meta.json`
   (nested state + per-dir breakdown counts + total).

Output classifications you then OVERLAY by judgement (the script can't decide):
- **UPSTREAM-OWNED**: skill packs / platform adapters that ship with Hermes
  (e.g. `creative/*`, `mlops/*`, `productivity/*`, agent-methodology/*,
  `platforms/`). Probe find: live `skills/` has ~130 SKILL entries but ~95% are
  upstream packs — only ~8–10 are genuinely custom (med-tracker, vps-audit-
  sync-handoff, malaysia-telco-research, medication-safety-research,
  documentation-workflow, wiki-vs-gdocs-hybrid, i-have-adhd, google-oauth-vps-
  setup, whatsapp-bridge-maintenance). Don't flag the whole skills dir as drift.
- **SOURCE-WORTHY CANDIDATE** = custom skills, custom plugins (plugin.yaml),
  active hooks, scripts drift. These are the reproducible-by-crash gap.
- **PATCH-REPRESENTED** vs **PATCH GAP** — see patch check below.
- **UNKNOWN/OWNER-DECISION** — only genuinely ambiguous paths go here. Surface
  ONLY those to the user (Decision 1..N). NOT a bucket for bulk.

## Patch coverage / boundary check (read-only)

To prove whether a tracked patch (e.g. `patches/upstream-hermes/*.patch`) is
BYTE-EXACT with the live nested state:
```
git -C <nested> apply --check --reverse <patch>
```
- exit 0 → patch fully present/reversible (byte-exact).
- error "patch does not apply" at a file → that file has POST-PATCH edits /
  drift → the patch is the durable record but NOT byte-replay. This is the
  "variant suggests a partial/malformed recovery patch" case: report it as
  PATCH-REPRESENTED-with-drift, never as "fully defined".
Cross-check coverage by listing the patch's `diff --git` targets
(`git show <main>:<patch> | grep '^diff --git'`) vs the files present live.
Post-patch additions NOT in any patch (e.g. a new UI module, extra tests,
bridge additions) = PATCH GAP → not reproducible across an upstream upgrade.

## Deliverable set (class-level shape)

`<reports>/live-source-census-<YYYYMMDD>/`:
1. `census.jsonl` — machine-readable full ledger (1 JSON per path)
2. `census.csv` — sortable ledger
3. `SUMMARY.md` — COVERAGE verdict (COMPLETE / PARTIAL + exact missing paths),
   per-dir counts, topology table, reverse-audit (stale main docs with
   last-commit dates), no-change proof, recommended next actions
4. `UNKNOWN-DECISIONS.md` — ONLY owner-decision paths (probe each with a small
   count so the user knows the scope)
5. `no-change` proof (HEADs/dirty/PIDs/OAuth mtime untouched, only reports dir
   + /tmp written)

Verdict honesty: if any source-like path remains unclassified, verdict is
**PARTIAL**, never COMPLETE. Don't upgrade "audit covered most paths" to
"full coverage".

## Reverse audit (stale main files)

For root-level docs, get last commit per tracked file:
```bash
git ls-files | grep -E '^[^/]+\.(md|sh|yml|json)$' | while read f; do
  d=$(git log -1 --format=%ad --date=short -- "$f")
  printf "%-46s %s\n" "$f" "$d"
done | sort -k2
```
stale = last commit weeks before the "current" marker (e.g. all reconciliation
docs fresh 08-06 vs PROGRESS/DECISIONS/RUNBOOK/README 06-24→07-18). Flags the
user's "documentation outdated" complaint directly.

## Command pitfalls (verified this run)

- **`git log -1 --format=%ad --date=short -- "$file"` **MUST** have the `--`
  BEFORE the path.** If you write `--date=short "$f" --`, git parses `$f` as a
  revision → `fatal: bad revision`. Fix: `--date=short -- "$f"`.
- **Don't check bash-heerdoc inline python with regex containing backslashes or
  `[`** — bash mangles backtick/`[` before python sees it ("syntax error near
  unexpected token `['"/ subtree commands failed). Write the parse to a
  `/tmp/*.py` file with `write_file`, then run it.
- `git diff --name-status A..B` on a rev that doesn't exist → silent empty.
  Verify revs with `git cat-file -t` first.

## The "reviewer-independent feedback" pattern

When asked to review a third party's plan for THIS system, adopt the
cross-check role: verify each plan claim against live evidence rather than
reporting its claims. A reviewer that says "Hermes can be sole auditor after X"
— two things: PARTIAL/aspirational (external agent still touching the worktree
today); the "X" human steps (add deploy key in GitHub UI, set branch
protection) are NOT automatable. Only say "this is the current state" when you
have reflog/`ls-remote` proof; otherwise label it a design goal, still.

## Authority hierarchy when reviewer challenges your live-system claim (verified 2026-08-07)

When the user feeds a reviewer's critique back at you — and that reviewer has NO
VPS access — a clean authority hierarchy prevents both over- and under-claiming:

| Authority layer | Who owns it |
|---|---|
| Live VPS facts (processes, files, loaders, cron, runtime behavior) | **YOU (native agent, live evidence)** |
| GitHub/public evidence (branches, commits, tracked content) | Anyone who can `ls-remote` / read the public repo |
| Reasoning / risk / consistency review | The reviewer (or you) — but only as RECOMMENDATION, not correction |
| Final intent, privacy choice, approval | The user |

A reviewer WITHOUT VPS access CAN legitimately:
- challenge claims on **GitHub-verifiable** facts (public branch contents, commits);
- flag **logical/principled** inconsistencies (e.g. "active/newer ≠ source-worthy" — a source-management principle);
- point out **faulty reasoning** (e.g. "mtime 08-04 is BEFORE Gate-1 capture 08-06, so it IS likely in the backup — you drew the wrong temporal inference").

A reviewer WITHOUT VPS access CANNOT claim:
- which files are actually loaded/active;
- whether a config key set is exact;
- whether an artifact's encrypted contents are truly absent;
- "correct the report" on any LIVE state — that requires your verification.

**When the reviewer is RIGHT:** verify their claim against live evidence, then
RETRACT your overclaim explicitly and correct the record with the evidence
(e.g. "I was wrong, Gate-1 does preserve these via untracked/dirty/gitdir
artifacts — here's the proof"). This session's overclaim ("custom skills/plugins/
hooks would need rebuilding from scratch") was refuted live. Admitting it with
the evidence is exactly the user's evidence-first standard (never flip-flop to
please, but never defend a claim live evidence refutes).

**Do NOT re-run a full census** because the reviewer questioned one conclusion.
Only drill into the specific contested claim (exact artifact-location check).
The stopping rule: reopen the audit only if a concrete contradiction could cause
data loss / PII exposure / upgrade-not-revertible / live corruption. Otherwise
record as refinement and continue.
