---
name: vps-audit-sync-handoff
description: "Multi-phase VPS audit + cross-platform (VPS ↔ WSL2/Windows ↔ GitHub) sync handoff to an external agent. Use when the user asks for a full system audit, a 100% sync snapshot, or to prepare artifacts for an external auditor/executor (e.g. OpenCode). Covers phase-gating, documentation-completeness standard, role-shift (native=verifier / external=executor), and VPS-specific query quirks."
version: 1.0.0
author: Hermes Agent (Jane/MJ)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [audit, sync, handoff, vps, snapshot, verification, external-agent]
    related_skills: [diagnosing-bugs, using-superpowers, system-verification-qa, gateway-restart]
---

# VPS Audit + Sync Handoff

Recurring class of work for this user: produce a complete, externally-verifiable record of the live VPS state so a second agent (OpenCode, Gemini, etc.) can audit/overhaul without guessing. The user runs a solo AI consulting business and treats the VPS as production.

## When this skill applies
- User says "audit", "sync 100%", "handoff to OpenCode/Gemini", "prepare artifacts for external agent", or references a prior audit-prep folder.
- User asks to verify alignment between what they told an external agent and what the VPS actually has.
- User wants a timeline of all changes across a date range for an auditor.

## Hard Rules (embedded from user corrections)

### 1. Phase-gating is mandatory
User explicitly requires: complete one phase → STOP → verify with live tool output → summarize → ask approval → proceed to next phase. Never batch all phases silently.
- If user pre-approves all phases ("proceed till phase C complete"), you still STOP-CHECK-VERIFY at each boundary and report before moving on. Pre-approval = permission to continue without re-asking, NOT permission to skip verification.

### 2. "Definitely ALL" = documentation completeness standard
When user says "definitely ALL" or "nothing missing", the deliverable is NOT done when the narrative is written. Every claim must be backed by a raw, copy-pasteable artifact an external agent can verify WITHOUT re-deriving:
  - cron list raw output (not just "6 jobs")
  - git status/log/diff (not just "uncommitted")
  - exact file:line for code edits (not just "added hy3-free")
  - .env VAR NAMES only (never values)
  - session IDs for cross-reference (full IDs, not just titles)
  - live config.yaml verbatim relevant sections
If you write a timeline but omit the evidence appendix, you have NOT met the standard.

### 3. Role-shift pattern (native vs external)
After handoff, the user's model is:
  - **Native agent (you, Jane/MJ)** = VERIFIER only. Check live VPS state, confirm external agent's changes are correct. Do NOT execute end-to-end fixes post-handoff.
  - **External agent (OpenCode etc.)** = EXECUTOR. Deep audit + overhaul end-to-end.
  - Access granted to external: rsync + read-only SSH (unless user says otherwise).
Encode this so post-handoff you don't accidentally start "fixing" things the executor owns.

### 4. Secrets handling in snapshots
- rsync snapshot MUST exclude: `.env`, `auth.json`, `whatsapp/session`, `*.db*`, `logs/`, `cache/`, `cron/output/`.
- In docs, list `.env` VAR NAMES only. User is security-conscious (called out API key in config.yaml on 8 Jul).
- If a Windows/PC snapshot already exists and is stale, SAY SO explicitly — do not let the external agent trust it. Fresh rsync from VPS is the source of truth.

### 5. Never create deliverable files inside the audit workspace (contamination rule)
User's standing rule (from 7/9 freeze): "never execute anything that can affect the audit." Creating .md deliverables inside the audit folder (e.g. `mjay/audits/`) violates this — auditors auto-discover and read those files, which contaminates their independence (they "find" your analysis instead of discovering it).
- **Deliverable pattern:** Provide the content IN THE CHAT RESPONSE, and send an isolated .md via MEDIA from a neutral path (e.g. `/tmp/`), NOT inside the audit project. The file is ephemeral — tell the user they can download + delete.
- When the user says "provide in response je, isolate and send .md tanpa create dalam vps" — this IS the rule. Don't write to `mjay/audits/`.

### 6. Self-verify file states — never delegate checks to the user
When unsure about file provenance, completion, or content, verify yourself with `terminal` + `grep`/`ls`. Do NOT ask the user to "check" something you can check. Delegating verification to the user is a lapse (user fired this on 7/10).
- Provenance: `ls -la --time-style=full-iso <files>` reveals authorship/completion. Identical mtime across 3 files = batch dump (rate-limited / incomplete). Smaller files + missing deep-dives = truncated audit.
- Coverage: `grep -rl "needle" <dir>/` confirms which auditor's files actually contain a finding. Use before claiming coverage.

### 7. OVERHAUL FREEZE gate (extends role-shift)
When the user declares an OVERHAUL FREEZE (signal phrase: "OVERHAUL V1.0 DAH SELESAI 100%"), the role-shift rule tightens to a HARD gate:
- Native agent = VERIFIER ONLY. No system change of ANY size (fix / create / modify / execute / delete) without explicit approval.
- Pre-approval of ONE item (e.g. user said "soul.md→SOUL.md aku approve") is NOT blanket permission for others. Each distinct change needs its own confirm.
- Even trivial doc edits / orphan-file deletions need explicit double-confirm under freeze — the user wants to know before anything touches their system. A clear interpretation choice ("A vs B") is NOT execution approval.
- After ANY external-agent change (commit, scp, reorg), RE-VERIFY live VPS state before reporting. State shifts; prior checks go stale.

## Multi-Auditor Git / Branch / Sync Coordination (merge-complexity failure mode)

The fairness section above handles AUDIT CONTENT independence. This section handles STRUCTURAL git/sync coordination — a different failure class that bit us on 2026-07-10.

### Failure modes observed
| Mode | What happened | Why it breaks |
|------|---------------|---------------|
| **Branch divergence** | OpenCode committed on `hermes-live`; Z.ai/Gemini on `main`. VPS HEAD = opencode's commit. | No shared integration target → push/merge needs an explicit plan. |
| **scp-to-VPS dirty state** | Auditors scp'd files straight to VPS (bypassing git). VPS working tree became untracked/modified, inconsistent with their local commits. | `git status` on VPS shows `??`/`M` for files the auditor "committed" on PC. Pulling later clashes with scp'd state. |
| **Unilateral reorg** | One auditor (Z.ai) did a repo-wide folder reorganization + commit that MOVED OTHER auditors' files, then "informed" them after. | Freeze breach (no explicit approval) + merge conflict: opencode's `hermes-live` ADDs root `audit-01/02/03.md`, zai's `main` DELETEs/moves them → rename/delete-vs-add conflict. |

### Mandatory pre-merge coordination
Before the user approves any push/merge, send the verification prompt in `references/multi-auditor-git-coordination.md` to EACH auditor individually. Do NOT trust the user's summary of "all committed, not pushed" — verify branch + commit + path state per auditor.

### VPS re-verify after any external change
External agents change state outside your session. After any auditor commit/scp/reorg:
1. `search_files` the audits dir — confirm actual folder paths (not folder-name assumptions).
2. `git -C <repo> status --short` + `git log -1` — confirm HEAD + dirty state.
3. `git cat-file -t <commit>` — confirm a claimed commit actually exists on VPS (local-PC commits won't).
4. Only THEN report. Prior-turn checks go stale the moment an external agent acts.

## VPS-Specific Query Quirks (verified 2026-07-09)

### Session DB `started_at` is corrupted
`state.db` sessions table `started_at` column returns 1970 timestamps (epoch garbage). Do NOT filter by timestamp. Use the **session ID prefix** for date range:
```python
# WRONG: WHERE started_at >= 1751913600000  → returns empty
# RIGHT:
c.execute("SELECT id, title FROM sessions WHERE id LIKE '20260708%' OR id LIKE '20260709%' ORDER BY id")
```
Session IDs are formatted `YYYYMMDD_HHMMSS_hex`. The hex suffix varies — store FULL IDs when cross-referencing.

### Cron diff technique
`hermes cron list` output count vs a baseline doc (e.g. `01-VPS-BASELINE.md`) IS the finding. If baseline had 14 jobs and live shows 6, jobs were terminated — list which are missing. Don't assume "same as before."

### Chat-search blind spots and title/tag enumeration
`session_search(query=...)` with FTS5 misses sessions that have empty titles, punctuation-only tags, renamed titles, or cron jobs. A successful FTS result is not proof of a complete title/lineage inventory.

When the user asks for **all sessions matching a title or numbered/tagged lineage**:

1. Use `session_search` first to recover narrative context and verify candidate session IDs.
2. Then query the local SQLite database read-only for exact `sessions.id` and `sessions.title` matches. Use `file:/path/state.db?mode=ro`; never open the database in write mode.
3. Match both the literal requested spelling and likely observed variants (for example, title word order or `#N` suffixes), but report the mismatch instead of silently normalizing it.
4. Enumerate the complete returned ID/title set, including the unnumbered base record and gaps in numbering. A base title plus `#2`–`#13` is 13 records, not 14; do not invent a missing `#1`.
5. Treat title enumeration as metadata evidence only. It proves which records exist, not that every message body has been read or that every claim in those sessions is true.
6. Separate FTS narrative coverage, DB title coverage, and full-body transcript coverage in the final report. Never describe one as the other.

Do not query or print message bodies when IDs/titles are sufficient. Session IDs are formatted `YYYYMMDD_HHMMSS_hex`; store FULL IDs when cross-referencing.

## Pre-existing Deliverable Collision

When the deliverable path already contains a report written by a PRIOR (expired) session — e.g. the expected report MD exists, authored just before the session died — neither trust it uncritically nor overwrite it.

1. **Read the whole existing artifact first.** You cannot decide overwrite/merge/keep without knowing what it claims.
2. **Never report it as yours or as verified without re-deriving the load-bearing claims.** A prior agent's report is self-attestation, not evidence. Independently re-run the commands that would make it wrong if wrong: patch reverse-check, tag peel, DB schema/counts, hash recomputation, auth probe.
3. **Treat hash-length as a validity check.** A value labeled `sha256` that is only 32 hex chars is an MD5 (`md5sum`) mislabeled, not a sha256. Real sha256 = 64 hex. Recompute with `sha256sum` and correct the report with a note (record the correction + timestamp), don't silently edit history.
4. **Keep the verified prior report; patch it rather than rewrite.** The substantive claims holding up under fresh live evidence = you can deliver it as validated. A pre-existing report that cross-checks clean is still the deliverable — you're certifying it against live state, not generating from your own session.
5. **Resolve collisions before building a Google Doc** — the .md is the source of truth; the Docs render inherits its correctness. Correct .md first, then md2ops → format → verify.
6. **Token/Auth side-effect audit:** stat `google_token.json` mtime before/after the Docs pipeline; the API calls (not just setup.py --check) can refresh it — disclose any change, don't claim "no artifact changed" blindly.

Full command recipes: `references/read-only-audit-techniques.md`.

## Read-Only Audit Techniques (verified 2026-08-06 reconciliation audit)

When the audit must verify deployment/overlay/patch state WITHOUT mutating anything:

- Verify an applied patch: `git apply --reverse --check <patch>` (exit 0 = changes present); isolate diverged files per-path with `--include=<file>`.
- Attribute file changes by mtime clustering (`stat -c '%y %n'`): same-second mtimes = one write batch → distinguishes pre-existing vs deploy-introduced drift.
- Light read-only DB checks for large SQLite (`mode=ro` URI + journal_mode + sqlite_master counts); `PRAGMA quick_check` on 1 GB+ DBs can exceed 180 s — skip it.
- Prove what code a running service loads from unit file + `/proc/<pid>/exe|cwd` + runtime argv state (triple-source; user units need `systemctl --user`).
- GitHub capability probe without creating refs: credential.helper/ssh/gh checks, then `GIT_TERMINAL_PROMPT=0 git push --dry-run ...`; confirm `ls-remote --heads | wc -l` unchanged afterwards.
- Manifest SHA provenance: recompute source SHAs at the RELEASE commit and compare recorded-vs-release-vs-live in one table; locate reference-type mappings by SHA search before calling MISSING.

Full command recipes: `references/read-only-audit-techniques.md`.
Step-by-step collision decision flow + re-verify commands: `references/deliverable-collision-verification.md`.

## Deliverable Structure (class-level)
Produce these artifacts in `~/mjay/audit-prep/` (or user-specified audit folder):
| File | Contents |
|------|----------|
| `0X-SYNC-UPDATE-<date>.md` | Corrects any stale baseline; live config vs old |
| `0Y-FULL-TIMELINE-<range>.md` | Chronological table of all sessions + changes |
| `0Z-EVIDENCE-APPENDIX.md` | Raw artifacts: cron list, git diff, file:line snippets, .env var names, session ID table, med state |
| `0W-MASTER-SYNC-DOC.md` | Unifies the above into ONE handoff doc |

Plus a fresh rsync snapshot at `~/hermes-snapshot-<YYYYMMDD>/` with a `README-SNAPSHOT.md` inside (integrity-check commands).

## Verification Loop (adapt diagnosing-bugs Phase 1)
Before declaring handoff ready, run a feedback loop: for each artifact OpenCode needs, does it EXIST and is the claim VERIFIED against live state? Paste the verification command + output. If any claim is memory-based (not tool-verified), downgrade it.

## Pitfalls
- **Don't trust Windows snapshot dates.** User confirmed `C:\Users\amiru\hermes-snapshot-20260707\` existed but was 2 days stale. Always note "fresh rsync available on VPS" as the real source.
- **Don't hide open items.** If B→C med gap is discussed but NOT implemented, list it as OPEN in the master doc. Hiding gaps = the exact failure mode user fired you for on 7/7 ("membongak je kau").
- **Gemini/AI-audit outputs may be fabricated.** In this user's history, an external audit claimed a CVE + a med dosage deficit that were both false. Strike fabricated claims from any handoff record and note "verify independently."
- **MiniMax provider:** user instructed to IGNORE minimax API key issue entirely (9/7). Don't revive it unless user asks.

## Multi-Auditor Fairness, Provenance & Contamination (verified 2026-07-10)

When the user runs 2+ AI auditors (OpenCode, Z.ai, Gemini/Antigravity) on the same system, a fair comparison requires each to be an INDEPENDENT source. Contamination (one auditor reading another's or your output) breaks this.

### Provenance tracking (who wrote what, when)
- `ls -la --time-style=full-iso` + cross-check against the user's stated timeline.
- **Folder names lie.** A folder named `opencode-audit/` may contain Gemini's output (user pasted an OpenCode-context prompt, so Gemini labeled itself "Auditor: OpenCode"). Verify by content + mtime, not folder name.
- **Incomplete audit signature:** all 3 files sharing one identical mtime (batch write) + smaller size + missing a finding another auditor has = rate-limited/truncated. Grep to confirm: `grep -rl "med-auto-confirm" ./`.

### Statement vs request — don't propose undoing completed work
If the user STATES a fact ("Gemini's audit is complete and already included my file"), that is NOT a request to block/stop/isolate it. Do not propose to undo what they said is already done.
- Statement (fact) → acknowledge + build on it.
- Request ("how do I make this fair?") → answer the actual question (e.g. provenance labeling), don't suggest blocking/stopping.

### Aligned post-audit addition (fairness fix)
When a post-audit finding must be added to ALL auditors' outputs:
- Instruct each auditor to **ADD only, never MODIFY** existing content/version. End-result must be identical across all.
- Give a UNIFIED instruction (same substance) per platform, with platform-specific file paths. See `references/multi-auditor-fairness.md` for the template.
- Label system-provided info as "transparent info direct from system" — user confirmed this is sound, not speculative.
- If one auditor already included the finding (read your doc), mark it as derived/confirmed, not independent discovery — preserves honest comparison.

## Current-state and capacity gates before reconciliation

A prior session's candidate SHA, PASS output, clean branch, or "no mutation" report is historical evidence only. Before reusing it:

1. Re-read current filesystem/VCS state: exact worktree path, branch, full HEAD, staged/unstaged/untracked status, and whether the candidate worktree still exists.
2. Re-query remote heads read-only; do not infer that an old `main`-only topology still holds.
3. Reconcile application-source clone, nested source repository, live runtime, candidate artifacts, and deployment manifests as separate surfaces.
4. Downgrade any candidate result whose worktree, source bytes, manifest, or runtime donor no longer exists to `HISTORICAL / NOT CURRENTLY REPRODUCIBLE`; never carry its PASS forward silently.

Disk capacity is part of the audit preflight, not an afterthought:

- Measure filesystem free bytes and inode usage before creating snapshots, overlays, bundles, or candidate worktrees.
- Attribute large directories by role: live runtime, active source/dependency tree, recovery backup, historical snapshot, disposable test artifact, cache, or unknown.
- A large directory is not automatically safe to delete. Check active processes, required evidence, retention, and recovery dependency first.
- Never delete Gate-1/recovery artifacts, source trees, runtime state, or branches to make the disk graph look clean without explicit approval.
- If test overlays or temporary homes are the likely consumers, preserve required logs/manifests, classify exact paths, then request a separate deletion approval and post-delete verification.
- If free space is insufficient for one candidate plus rollback/preservation artifacts, stop candidate construction and report `CAPACITY-BLOCKED` rather than creating a partial snapshot.

## Live↔Source Census (read-only, 2026-08-07)
When the user wants main↔live alignment proven ("record/track everything so nothing is lost on crash", pre-upgrade baseline), run the full census:
- **Reframe first**: live≠main is BY DESIGN for runtime state (memories/, real config, cron, DB, sessions, upstream skill packs) — NOT a gap. Only untracked source-worthy customizations are real gaps (custom skills/plugins/hooks, scripts drift, patch-gap nested code, stale docs, obsolete persona with privacy risk). Don't push runtime into git.
- **Inventory with a script** (write to /tmp, outputs to `<reports>/live-source-census-<date>/`): git ls-tree manifest, nested `status --porcelain` split M/??, bounded walk of skills/plugins/hooks/scripts/agents/plans/design/platforms with sha256 → census.jsonl + census.csv + meta breakdown. Overlay classification by judgement: bulk skills/platforms = UPSTREAM-OWNED (only ~8-10 custom skills are source-worthy); UNKNOWN-DECISIONS.md = ONLY genuinely ambiguous paths.
- **Patch boundary check**: `git -C <nested> apply --check --reverse <patch>` — exit 0 = byte-exact; "does not apply" = post-patch drift (report PATCH-REPRESENTED-with-drift, never "fully defined"). Cross-check `git show <main>:<patch> | grep '^diff --git'` targets vs live; files in live not in any patch = PATCH GAP — **BUT ONLY if the content is NOT preserved by a backup artifact. Gate-1 archives the nested repo separately and can make a patch gap NON-lossy. NEVER conclude "will be lost on upgrade" before the backup-artifact coverage check (see `references/backup-artifact-coverage.md`).**
- **Verdict**: PARTIAL if any source-like path unclassified — never upgrade to COMPLETE. Deliverables: census.jsonl/.csv, SUMMARY.md (verdict + reverse-audit of stale main docs), UNKNOWN-DECISIONS.md, no-change proof.

### Convergence review after a census / preservation branch
A later Git-closure review must not narrow itself to only the newest committed branch. Reconcile four independent surfaces together:
1. the application-source baseline (`main` / release commit);
2. every candidate commit range on a preservation branch;
3. the current nested working-tree delta (`git status --porcelain`); and
4. the prior census / audit inventory.

For each source-like path, classify exactly once as `PORT`, `ALREADY-REPRESENTED`, `RUNTIME-ONLY`, or `OWNER-DECISION`, attaching path-level evidence. A branch existing remotely proves **preservation**, not source representation or technical validity. Require an exact source commit/patch mapping; same pathname alone is not representation. For patch-backed paths, use per-path `git apply --reverse --check` and label historical/byte-exact representation separately from later drift.

### Bounded file-set closure protocol

When a reviewer supplies a final-looking arithmetic formula, treat it as a claim inventory—not a release scope. Before accepting the union:

1. Normalize every input to an exact **file path set**. Do not count directories, skill groups, plugin manifests, prose labels, or Git status records as source files.
2. Separate `SOURCE-MATCH` / `ALREADY-REPRESENTED`, backup/stale files (`*.bak*`, archived copies), runtime/private files, and genuine source candidates before counting.
3. Keep three counts distinct: raw census records, known changed/source-like files, and owner-approved release candidates. Never call the first two `Y`.
4. Reconcile known drift classes independently: hooks, skills, plugins, scripts, config templates, persona tip remediation, agents/private data, and nested preservation paths.
5. For each class, return exact paths plus one disposition: `PORT`, `SANITIZE`, `PRIVATE-RUNTIME`, `STALE/BACKUP`, `ALREADY-REPRESENTED`, or `OWNER-DECISION`.
6. Deduplicate using normalized source-relative paths and report the intersection explicitly. If the nested path set is not available, state a data gap; do not infer zero overlap from different directory names.
7. A current-live set check is allowed only for a named bounded set (for example, plugin source files excluding `__pycache__`); it must not silently become a census rerun.
8. Stop at `UNION-PARTIAL` when any source-like path remains owner-ambiguous. A formula such as `42 + 118 = 160` may be a bounded affected/action union, but it is not final candidate `Y` until owner decisions are resolved.

Reusable command/report pattern: `references/bounded-source-closure.md`.

**Count-delta rule:** Never explain a difference such as “33 untracked → 28 untracked” from a plausible story. Locate the two timestamped path inventories and compute `added`, `removed`, and `unchanged` sets. If the older count has no raw path set, report `DATA GAP: exact path delta cannot be computed; historical count unsupported`—do not invent the missing paths or treat the numeric claim as evidence.
- Pitfalls: `git log -1 --format=%ad --date=short -- "$f"` — `--` MUST precede the path (else "fatal: bad revision"); don't put regex inline in bash heredoc python (bash mangles `[`/backticks) — write /tmp/*.py first.
Full technique: `references/live-source-census.md`.

## References
- `references/session-db-queries.md` — exact SQL patterns for session inventory on this VPS (corrupted started_at workaround).
- `references/handoff-checklist.md` — pre-delivery checklist template.
- `references/multi-auditor-fairness.md` — provenance commands + aligned ADD-only instruction template for multi-auditor comparisons.
- `references/multi-auditor-git-coordination.md` — pre-merge verification-prompt template + branch-divergence/scp-dirty-state diagnosis recipes + unilateral-reorg conflict playbook.
- `references/read-only-audit-techniques.md` — read-only verification recipes: patch reverse-check, mtime attribution, light DB checks, process identity proof, GitHub capability probe, crash-loop forensics, manifest SHA provenance.
- `references/deliverable-collision-verification.md` — decision flow when the deliverable path already holds a prior-session report: re-derive load-bearing claims, hash-algorithm check (sha256=64hex vs MD5=32hex), patch-vs-rewrite, docs-build ordering, token side-effect audit.
- `references/live-source-census.md` — full live↔source census technique: expected-runtime-vs-real-gap framing, inventory script design, patch boundary check, verdict honesty, command pitfalls, reviewer-claim cross-check pattern.
- `references/backup-artifact-coverage.md` — prove whether nested/untracked content is preserved by the Gate-1 backup artifact set (gitdir/dirty/untracked/bundle/env) before ever concluding "will be lost"; git-object-db recovery matrix; honest UNKNOWN labeling when artifacts are owner-passphrase-encrypted.
