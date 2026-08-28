---
name: git-repository-reconciliation
description: Reconcile divergent Git histories across clones, branches, runtime repos, snapshots, and remotes without losing committed or uncommitted work. Use for multi-repo confusion, stale default branches, orphan/dangling commits, conflict forecasting, or source-of-truth recovery.
---

# Git Repository Reconciliation

## Core Principle

A safe local command is not the same as a safe end-to-end consolidation. Separate:

1. preserving every unique state;
2. proving repository and commit-graph relationships;
3. moving narrowly scoped changes into the correct source lineage;
4. forecasting textual conflicts;
5. validating semantic behavior after integration.

Never start with merge. Start with preservation and topology.

## Approval Boundary

Unless the user explicitly approves the exact operation, stay read-only. Require approval before `git add`, commit, fetch, merge, rebase, cherry-pick, push, branch/tag/ref creation, stash, worktree creation/removal, clean, GC/prune, or modifying ignore/config files.

A plan, “proceed,” or approval for implementation is not Git approval.

## Owner-specific default: application `main` only

For Amirulhazym, the normal application-source workflow is **direct work in the canonical application clone on `main`**. Do not create or reuse a linked worktree, staging branch, or temporary integration branch merely because isolation is a generic best practice.

Keep these layers separate:

- `/home/ubuntu/hermes-agent-personal_assistant-work` = the application-source repository and normal release target;
- `/home/ubuntu/.hermes/hermes-agent` = nested upstream/live-source witness, not the application-source lane;
- `/home/ubuntu/.hermes` = mutable runtime state, never a blanket application-source commit;
- `/tmp/*` candidate/worktree paths = temporary preservation or explicitly approved experiment lanes, not a default development surface.

Rules for this user:

1. The latest explicit owner instruction overrides the generic isolation default in this skill. Current default: no new worktree and no parallel development branch.
2. Create a branch or linked worktree only after explicit approval for that exact scope. Older “candidate construction” or reconciliation authorization is not standing permission for later work.
3. If an existing worktree is discovered during an audit, inventory and preserve it; do not extend, reuse, merge, rebase, or delete it under a read-only audit.
4. A merge or rebase does **not** close a linked worktree. Every explicitly approved worktree has a mandatory close-out gate: preserve uncommitted/untracked bytes, classify its commits, then remove it through the parent repository and verify that `git worktree list --porcelain` no longer registers it. Do not leave a temporary branch behind unless the owner explicitly retains it.
5. Report state with separate labels: `CANDIDATE`, `COMMITTED-LOCAL-ONLY`, `PUSHED`, `READY-TO-PUSH`, `DEPLOYED`, and `LIVE-VERIFIED`. A targeted test pass is not `READY-TO-PUSH`; unresolved full-suite, privacy, manifest, remote-target, or approval gates keep the candidate blocked.

## Phase 0 — Scope-Lock the Question

State both horizons:

- **Immediate:** can this exact command alter or conflict with current state?
- **Final:** can all wanted changes reach the intended source-of-truth without loss or semantic breakage?

Do not answer the first when the user is asking the second.

## Phase 1 — Read-Only Inventory

For every candidate directory, capture:

- top-level, git-dir, common-dir, and `.git` marker type;
- current branch, HEAD, local and remote-tracking refs;
- remote names and sanitized URLs;
- registered worktrees;
- staged, tracked-modified, untracked-all, and ignored classifications;
- commit count and object availability for reported SHAs.

Do not infer “worktree” from a folder name. A normal clone has its own `.git` directory and common-dir; a linked worktree has a separate git-dir pointing to a shared common-dir.

Do not fetch during discovery. Verify current remote heads separately with `git ls-remote`; fetching mutates refs and can complicate preservation.

### Snapshot and Overlay Comparison Rules

Treat every evidence set as timestamped. A count is not a stable identity: `--untracked-files` mode, ignored-directory collapsing, test-generated files, and runtime writes can change counts without the same paths changing—or leave counts equal while bytes differ.

For every current-vs-historical comparison:

1. Record the exact command, timestamp, HEAD/ref, and status mode.
2. Compare exact path sets (`CURRENT-ONLY`, `BASELINE-ONLY`, `COMMON`); never infer deltas from counts.
3. For common files, compare content hashes and file mode/symlink metadata. Path equality is not byte equality. When comparing a filesystem file with a Git tree path, hash the raw bytes on both sides (for example, filesystem `sha256sum` versus bytes from `git cat-file blob <ref>:<path>`). A Git blob object ID is not the raw file SHA-256 and must never be compared directly to a filesystem hash.
4. Keep tracked modifications, untracked paths, and ignored paths in separate sets. Do not accidentally count `?` untracked rows as `!` ignored rows.
5. For `.git`, record marker type (`file` versus `directory`), `git rev-parse --git-dir`, `--git-common-dir`, and `git worktree list --porcelain` before calling something a clone, linked worktree, or disposable copy.
6. For bundle/recovery claims, separate `PRESENT`, correctly-scoped `VERIFY-PROVEN`, historical clone/checkout evidence, fresh clone/checkout, and dirty/untracked restore evidence. A historical tool result is not a fresh test; an encrypted archive's existence is not content or restore proof.
7. For disk projections, report apparent bytes and allocated bytes separately, timestamp the `df` snapshot, and calculate projected usage with the same denominator/rounding convention as the displayed `df`. Actual post-action `df` remains authoritative.
8. Before deleting a “clean” overlay, check active cwd/open file descriptors, unique refs/objects, registered worktrees, ignored content, and sole test/evidence files. Clean Git status is necessary but not sufficient.

See `references/snapshot-boundary-and-overlay-comparison.md` for the reusable procedure and evidence labels.
See `references/read-only-forensics-command-book.md` for exact commands.
See `references/read-only-worktree-push-audit.md` for the reusable "what is uncommitted / unpushed?" audit recipe.

### Read-only "uncommitted / unpushed" audit

When the owner asks whether work remains uncommitted or unpushed, inspect the complete Git surface before answering. The repository root is not the complete surface: registered linked worktrees, stashes, local-only branches, and ignored paths can carry separate state.

1. **Inventory every registered worktree first.** Run `git worktree list --porcelain`; for every existing path, run `git -C <worktree> status --porcelain=v2 --branch --untracked-files=all` and `git diff --name-status` plus `git diff --cached --name-status`. Report the exact path set per worktree. A clean root does not make a dirty linked worktree clean.
2. **Inspect stashes separately.** `git stash list` and `git stash show --name-status --stat <stash>` prove a preserved WIP snapshot, not a commit and not a pushed ref. Never collapse stash state into either clean or committed.
3. **Classify the layers separately:**
   - `UNCOMMITTED` = staged, tracked-modified, conflicted, or non-ignored untracked paths in any worktree;
   - `COMMITTED-LOCAL-ONLY` = commits reachable from a local branch but not from a current direct remote head;
   - `PUSHED-BUT-DIRTY` = branch tip is remote-reachable, while one or more worktrees on that commit have dirty overlays;
   - `CLEAN-BEHIND` = no proven local-only commits, but local ref is behind the remote; this is not pending local work;
   - `IGNORED / NOT CLASSIFIED` = excluded from normal Git status and requiring separate provenance review.
4. **Pin current remotes without fetching.** Run `git ls-remote --heads <remote>` for every configured remote and timestamp the result. Compare direct heads to local tracking refs; never call a stale `origin/<branch>` current merely because it exists locally. If the direct remote moves during the audit, retain both observations, pin the final one, and mark graph conclusions against missing remote objects `PARTIAL`/`UNVERIFIED`.
5. **Prove publication, not just branch-name similarity.** For each local branch, record full tip SHA, upstream, direct same-name remote branch, and whether the tip is an ancestor of a current remote head. A branch with the same name is not proof that its dirty overlay or every local commit was pushed. Conversely, a local branch with no upstream may still have its tip reachable from another remote branch; check exact ancestry before calling it unpublished.
   - **PR object is a separate publication boundary:** a pushed branch proves only remote reachability. A provider URL ending in `/pull/new/<branch>` is a PR-creation form, not proof that a PR exists. Query the actual PR API/CLI with the exact head owner and branch; an empty result is `NO PR FOUND`. Keep `PUSHED-BRANCH`, `PR-OPEN`, `REVIEWED`, and `MERGED` separate. If the feature depends on a separate plugin/provider repository, verify that dependency's direct remote head independently; an application PR does not publish it.
   - **Stale-ref cleanup is separate and mutating:** use `git remote prune --dry-run <remote>` only to enumerate stale local tracking refs. Do not run `git remote prune <remote>` in a read-only audit or as a PR prerequisite without approval. It does not remove remote or local branches. Keep `origin/*` and `upstream/*` namespaces separate and preserve the dry-run list as evidence before later cleanup.
6. **Map branch-to-worktree multiplicity.** Multiple worktrees or branch refs can point at the same commit while carrying different uncommitted overlays. Report each overlay independently and never merge their status by commit SHA.
7. **Use structured argv in probes.** When scripting `git log`, `rev-list`, or `merge-base`, pass the revision and flags as separate arguments (for example `['log', branch, '--not', '--remotes']`), not as one concatenated revision string. Preserve non-zero output, fix only the probe construction, and rerun; a malformed audit command proves nothing about repository state.
8. **Do not round up ignored/private files.** `!` ignored records are not automatically disposable or safe to publish. Use `git check-ignore -v`, path classification, and the repository's privacy policy before suggesting commit/push. A private `SOUL.md`, runtime database, log, or credential-shaped file is an owner-review item, not a normal source candidate.
9. **Separate remote ownership from credential identity.** A remote namespace such as `owner/repository` proves the configured destination, not which human owns it. A different owner name from the canonical application repo is `UNVERIFIED`, not evidence that it is a third-party repository; one person may operate multiple GitHub handles or accounts. Conversely, a push denial proves that the current credential/key lacks permission, not that the repository is not owner-controlled. Before changing a remote, creating a fork, or selecting an alternate destination, inspect the exact configured remote and direct repository metadata; preserve the ownership relationship as `UNVERIFIED` unless it is actually proven. Never silently switch destinations to make a push work.
10. **Stop at the failed publication boundary.** In an approved multi-step sequence, a failed push/auth/API operation is a hard stop for dependent PR creation, merge, or cleanup unless the owner explicitly authorizes a new route. Re-read the local HEAD, direct remote head, PR object, and working-tree status after the failed attempt. Do not report partial publication as success, do not prune refs after a blocked publication gate, and do not request or print secrets as an ad hoc workaround.

### Cross-channel identity and publication gate

When a plugin/provider repository and an application repository are both involved:

1. Record the exact remote URL for each repository; do not infer ownership from the fact that the path names differ.
2. Verify each repository's direct remote head independently. Application branch reachability does not publish a provider commit.
3. Treat credential layers separately: HTTPS prompt/helper, SSH key/deploy-key identity, API token, and browser session. Successful SSH authentication to one repository does not prove write access to another repository.
4. For a failed publication attempt, capture the exact error and run a read-back. If the remote SHA is unchanged, classify the operation `NOT-PUBLISHED`; do not continue to PR/cleanup merely because those commands might be independently possible.
5. An alternate fork/destination is a new source-of-truth decision, not a fallback implementation detail. Require explicit owner scope before creating or switching to it.

See `references/cross-channel-identity-and-publication-gates.md` for the reusable owner-vs-credential matrix, raw-byte comparison gate, and failed-publication stop procedure.

The user-facing result must include: audit timestamp, repositories/worktrees checked, uncommitted path counts, committed-local-only branch tips, stash state, current direct remote heads, contradictions/moving-target observations, and an explicit no-mutation statement. Use `DIRECTLY VERIFIED`, `PARTIAL`, `UNVERIFIED`, and `DATA GAP` labels rather than a binary "clean/dirty" conclusion.

Reusable cross-channel branch-sprawl procedure, raw-byte equivalence checks, upstream-mirror separation, nested-live overlay classification, PR publication boundaries, and cleanup gates: `references/cross-channel-branch-sprawl-closure.md`.

### Canonical clone vs live-runtime reconciliation

Use this gate whenever the owner asks whether “the live VPS is synced with GitHub `main`,” especially after a cross-channel workday or a historical assistant report says “nothing to commit/push.” A canonical application clone and the live runtime are separate evidence lanes; parity in one lane never upgrades the other.

1. **Name the lanes before checking status:** canonical application source; nested/upstream/live source checkout; provider/plugin repositories; mutable runtime/config/state; wiki or documentation repositories; registered worktrees; stashes; and the intended remote. Do not let a root-level clone stand in for every lane.
2. **Report two independent verdicts:**
   - `CANONICAL-CLONE ↔ REMOTE` — exact local branch tip versus a fresh direct `git ls-remote` result, plus tracked/untracked status;
   - `LIVE-SOURCE/RUNTIME ↔ REMOTE` — live checkout/plugin/runtime dirty paths, exact HEAD/remote topology, and whether each change is source-worthy, runtime-only, private, generated, or unknown.
3. **Keep Git vocabulary exact:** a dirty working tree is `UNCOMMITTED`, not an “unpushed commit.” A branch tip matching its remote can still be `PUSHED-BUT-DIRTY`. “No local-only commits” does not mean “no work remains.”
4. **Block ordinary ahead/behind claims when histories are unrelated:** record `merge-base`, both-direction counts, and ancestry. `merge-base = NONE` means do not call the tree “ahead,” force-push, or blanket-merge; switch to selective source classification/reconciliation.
5. **Cross-check historical claims independently:** if chat says “no code changes,” inspect the relevant session/message evidence and current file mtimes/diffs. One clean canonical clone cannot refute same-day patches in a nested source or plugin repository.
6. **Treat broad runtime roots as non-commit candidates by default:** exclude credentials, databases, sessions, logs, memory, caches, generated files, and private state until exact provenance and intended destination are proven. Never blanket-stage a mutable `.hermes` root.
7. **Show the evidence boundary in the conclusion:** state which lane is exact-match, which is dirty, which is divergent, which is local-only, and which is not comparable. Do not collapse these into a single “clean/synced” sentence.

Reusable evidence schema and the 2026-08-25 cross-channel incident pattern: `references/live-vs-canonical-chat-repo-audit.md`.

## Phase 2 — Canonical Live Baseline and Preservation Barrier

Before changing refs or histories, produce one timestamped, read-only live baseline. Reuse fresh evidence already collected; run only missing or stale checks. The baseline must separate:

- live operational files/state;
- the intended application source lineage;
- nested upstream/fork source;
- archives/snapshots;
- external machines that are outside direct access.

Capture at minimum:

1. runtime process provenance: PID, command, executable, working directory, service manager, interpreter/venv, imported module paths, and actual health endpoint;
2. each repo's exact HEAD/branch, staged count, tracked-modified count, untracked-all count, remote names, refs, git-dir/common-dir, and purpose;
3. dirty-state classification by top-level path and category, retaining an `uncertain` bucket rather than guessing;
4. all mutable databases, WAL/SHM companions, current open-file writers, transient/potential writers, and the externally controlled stop/start order;
5. encryption capability separately from off-device decrypt/recovery capability;
6. reproducible per-file and combined hashes with exact inputs and algorithm;
7. runtime acceptance checks needed after restore/deployment;
8. facts inaccessible from the current machine as explicit `UNVERIFIED` items.

Then establish the preservation barrier:

1. Snapshot each repository including `.git`, permissions, tracked, untracked, and ignored files.
2. Back up runtime state, credentials, logs, and PII through an encrypted non-Git channel.
3. Identify dangling commits and orphan branches. Do not run GC/prune.
4. After approval, make valuable dangling objects reachable with clearly named rescue refs **before** creating `--all` bundles; a rescue tag created after the bundle is not inside that bundle.
5. Create bundles only after refs are pinned, then run `git bundle verify` and `git bundle list-heads`.
6. Transfer artifacts to a genuinely independent device/location, compare source/destination SHA-256, and temporary-clone every bundle to prove practical recoverability.
7. Preserve dirty/untracked/ignored state separately; Git bundles contain reachable objects/refs, not the index, worktree, Git config/hooks, or uncommitted files.
8. For live runtime state, inventory every writer. Use a coherent capture method: provider/filesystem snapshot, SQLite Online Backup API, or bulk copy followed by an externally controlled pause and final delta. Do not assume stopping one named process covers every writer.
9. Validate restored SQLite copies (`quick_check`, `integrity_check`, expected tables/counts), then restart services externally and verify runtime health.
10. Prefer new private rescue branches/bundles over force-updating existing branches.

A Git branch cannot preserve secrets, runtime state, or ignored data safely. “Everything is in Git” is not a valid preservation strategy. A simple filesystem copy on the same disk is not an independent backup.

See `references/live-runtime-preservation-baseline.md` for the reusable manifest and Gate-1 acceptance template.
See `references/current-working-tree-checkpoint.md` for the bounded checkpoint, ignored-record classification, and overlay-cleanup procedure.

### Bounded current-working-tree checkpoint

When cleanup or reset is being considered but the live repository has uncommitted work, create a narrow checkpoint before any destructive action. This is a preservation barrier, not a release or public-source decision.

1. Pin the boundary: record local timestamp, exact HEAD/ref, branch, git-dir/common-dir, porcelain status mode, and counts for tracked-modified, staged, untracked-all, and ignored records.
2. Capture tracked modifications with `git diff --binary`; capture non-ignored untracked paths with `git ls-files --others --exclude-standard -z` and a null-delimited tar using `--null --verbatim-files-from`. Do not silently include all ignored data.
3. Write a per-record manifest containing path, kind, mode, lstat size, and SHA-256 (hash symlink targets as metadata; do not dereference arbitrary symlinks). Record the archive and patch hashes in a separate checksum file.
4. Use a restrictive same-device fallback when encrypted/off-device handling is not yet available: directory `0700`, artifacts `0600`, and an explicit limitation that this is not independent recovery. Never describe it as immutable/off-device without proof.
5. Post-check the live repository. The checkpoint is stable only if HEAD and the complete porcelain output are byte-identical before and after capture. If they changed, label the artifact inconsistent and do not round it up to a valid snapshot.
6. Verify independently: checksum exit `0`, tar listing/test exit `0`, exact untracked-member set, unique manifest path count, current file hashes, and unchanged source-repository status.

### Ignored-record and disk-measurement pitfalls

- Parse ignored records from porcelain rows beginning with `! ` only. Rows beginning with `? ` are untracked; accidentally combining them produces inflated ignored counts.
- **Do not pipe status into `python3 - <<'PY'`.** A heredoc owns Python's stdin, so the piped `git status` bytes are discarded and a false zero-record/"clean" result can follow. For programmatic parsing use `subprocess.check_output(...)`, `python3 -c`, or a temporary status file; then capture status twice and compare the raw outputs before reporting a stable count.
- For each ignored path, use `git check-ignore -v -- <path>` and parse its first tab-separated field as `source:line:pattern` with a maximum-two-colon split. Store rule provenance, type, allocated size, apparent size, source-like/runtime-affecting status, sensitivity, and disposition.
- Count alone never proves source risk. Generated caches, dependencies, build output, docs/plans, examples, runtime data, and source-like files can all be ignored under the same repository.
- For overlay cleanup, compare exact tracked diff hashes, untracked path sets, common-file content hashes, ignored sets, refs, registered worktrees, active cwd/open file descriptors, and sole test/evidence files. “Clean” is necessary but not sufficient.
- **Copied/stale worktree metadata trap:** `git worktree list` inside a disposable clone can contain a path that looks live but is merely copied metadata. Do not infer dependency from that list. Inspect the referenced worktree itself: its `.git` marker type, `git rev-parse --git-dir`, and `git rev-parse --git-common-dir`. A real external worktree depends on the clone only when its actual common Git dir resolves under that clone’s `.git`; otherwise label the listed registration stale/copy metadata.
- **Object-store preservation gate:** refs are not the entire Git recovery universe. Before deleting a clean overlay, run `git fsck --full --no-reflogs --unreachable`; separately count reachable refs and unreachable objects by type. Check every candidate object with `git -C <preservation-repo> cat-file -e <oid>`. Only call the overlay non-unique when both (a) every reachable ref and (b) every reported unreachable object exists in the intended preservation repository. If objects merely exist but remain unreachable in that preservation repository, disclose that deletion reduces same-disk redundancy and does not create durable recovery.
- Measure each candidate directory directly at the same snapshot. Report apparent and allocated bytes separately. When estimating reclaim, reconcile `(st_dev, st_ino)` across candidate roots so hardlinked blocks are not counted as reclaimable twice. Do not reuse a prior size when the measurement scope or directory state differs. Also record the candidate and preservation artifacts’ `st_dev`: same-device copies are not off-device or independent recovery.

## Phase 3 — Prove the Commit Graph

For every pair that may consolidate, record:

- exact full SHAs;
- merge base or `NONE`;
- left/right commit counts;
- ancestor direction;
- whether the same objects exist in another clone.

Key interpretations:

- Different directories can share project history because clones carry the same commit graph.
- A stale branch pointer does not imply its commits are missing; they may already be ancestors of a newer branch.
- `merge-base = NONE` means ordinary history integration is unrelated. Do not reach for `--allow-unrelated-histories` by default; classify and manually port source-worthy changes.

### Push-boundary check (before pushing to ANY remote branch)

Proven 2026-08-07: a user's GitHub `main` was a **different repo lineage** (89 Phase-based snapshot commits) while local `main` carried full upstream history (~12,205 commits). `git merge-base HEAD origin-vps/main` returned empty → the two histories share NO commit. Symptoms: push rejected as non-fast-forward even though the local branch was ahead, and `git log --oneline HEAD..<remote>/<branch>` shows commits that have never existed locally.

Run before pushing:
```bash
git merge-base HEAD <remote>/<branch>   # empty output = unrelated lineages
git rev-list --count HEAD..<remote>/<branch>   # remote-only commits
git rev-list --count <remote>/<branch>..HEAD   # local-only commits
```
Interpretation:
- Empty merge-base + large both-direction counts = snapshot/archive repo of different lineage. **Never force-push or `--allow-unrelated-histories` without an explicit user decision** — remote work (reconciliation docs, med-tracker ports, etc.) would be orphaned from the default ref.
- Present options instead of deciding: (a) push work as a NEW branch (always safe, never destroys remote state), (b) force-replace remote default (destructive — user must understand), (c) merge remote lineage into local first (creates a mixed unrelated history — not recommended).
- **Push branch ≠ push main.** A rejected main push does not block branch pushes; pushing the feature branch to the same remote succeeds independently and is the safe first move while the user decides about main.

## Phase 3.5 — Deterministic upstream-plus-patch source closure (Model B)

Use this when the canonical repository intentionally does not vendor the full upstream runtime, but the deployed runtime still must be reproducible exactly. The goal is one authoritative path:

```text
approved application SHA
  → official upstream repository + exact base SHA
  → ordered hash-pinned patch series
  → reconstructed source tree
  → explicit per-file deployment manifest
  → live destination hashes
```

### Authority rules

1. Store the official repository URL, full base commit SHA, patch order, patch SHA-256 values, reconstruction script, runtime destination root, and explicit file manifest in the canonical repository.
2. Existing tracked copies of upstream files must be moved into patch/source artifacts, clearly marked `reference-only`/generated, or removed from release authority. A README alone is insufficient if a deployment script can still source the old copy.
3. Mark the application-source coverage inventory as non-authoritative for the upstream runtime and point it to the runtime source lock. There must be one deterministic deployment input path, not “root copy versus reconstructed output.”
4. Treat the live/nested upstream clone as a witness and source-inspection aid, not as an implicit source input. A reconstruction test that uses only that local clone proves local materialization; it does **not** prove disaster recovery from a fresh official clone.

### Materialization protocol

1. Build in a disposable plain directory; do not create a Git branch/worktree merely to materialize a runtime candidate.
2. Fetch/clone the official repository at the exact locked commit, archive/checkout it, verify the resolved commit, and apply patches in lock order.
3. Run `git apply --check` before applying every patch. A patch artifact plus a regression test is not behavior until the patch is applied to a fresh base and the test runs against that materialized tree.
4. Generate/verify an explicit manifest containing source path, destination path, content SHA-256, and file mode. Do not use recursive deployment wildcards when the release contract requires exact files.
5. Reproduce Git modes, not host-umask modes: `git archive` can extract a Git `100644` file as filesystem `0664`. Restore/verify `100644` versus `100755` from the Git tree before hashing the manifest. Content-only equality is insufficient.
6. Exclude runtime state, credentials, databases, WAL/SHM, logs, caches, and platform sessions from deployment inputs. Normal runtime metadata writes from an approved application fix are not a schema migration or bulk historical repair; test them separately and never rewrite the historical DB as part of source closure.
7. Test the reconstruction from a fresh official clone before calling Model B complete. If only a local nested clone was used, label the result `PARTIAL / LOCAL-BASE-EXERCISED`, not exact disaster-recovery proof.

### Patch-generation and test gates

- Generate custom patches with standard `diff --git`, `---`, `+++`, and hunk headers plus correct line terminators; run `git apply --check` against a clean locked-base tree before adding the patch to the series.
- Valid unified-diff context blank lines may appear as `+ ` to an outer `git diff --check`. Do not corrupt the patch to silence that diagnostic; run whitespace checks on reconstructed/source files separately and keep patch applicability as the authoritative patch gate.
- Write regression tests RED against the clean base, GREEN after the materialized implementation, then run the affected broader suite. Compare any full-suite failure against the exact clean baseline in an isolated process before attributing it to the candidate.
- A failure reproduced on baseline and candidate is `BASELINE`, not a candidate defect; it still prevents a claim that the full suite is green. Report targeted pass, broader pass, baseline failure, and release status separately.

### Commit/release boundary

Commit logical slices (source closure, official semantic patch, custom behavior patches, shared identity patch) only after each slice's materialized tests and manifest/hash checks pass. Keep `COMMITTED-LOCAL-ONLY`, `PUSHED`, `DEPLOYED`, and `LIVE-VERIFIED` distinct. If the owner names a release stop gate, do not push/deploy/restart before that gate even when local candidate tests pass.

Reusable recipe and evidence fields: `references/model-b-runtime-source-closure.md`.

### Evidence reuse after patch/provenance regeneration

A regenerated patch, test contract, source lock, or tree manifest creates a new candidate representation even when the intended runtime behavior may be unchanged. Before carrying historical behavioral evidence forward:

1. Apply the previous and final patch representations to equivalent copies of the same pinned base/C3 source files; compare the actual runtime bytes and modes. Do not infer runtime change from patch-file text differences, and do not infer identity from a tree hash covering a different path set.
2. If runtime bytes/modes are identical, reuse only the unaffected behavioral evidence and rerun the affected static/provenance/applicability gates against the new exact SHA. If any runtime byte/mode differs, invalidate the relevant evidence and rerun it.
3. Keep `READY FOR FINAL FULL SUITE` distinct from `FULL SUITE PASS`; a deliberate full-suite deferral is an incomplete gate, not a pass.
4. Reconstruct the production rollback set from the complete ordered patch/deployment manifest. In a temporary destination validate exact file set, all bytes, all modes, and no extra/missing files when rolling back to the exact pre-release C0. Keep development C4→C3 rollback separate.
5. Keep actual copied-data boundary coverage separate from synthetic coverage. Use actual stored production reason literals; a missing copied-data row is a data gap, not permission to substitute undocumented aliases.

Reusable checklist and evidence fields: `references/ordered-patch-evidence-closure.md`.

## Phase 4 — Classify Changes Before Porting

Separate every dirty path into:

- source-worthy code/docs/tests;
- runtime/config state;
- credentials/PII;
- generated/cache/vendor files;
- backups/snapshots;
- unknown, requiring review.

Reject blanket staging in a dirty runtime repository. Verify secret and PII paths with `git check-ignore` before any staging proposal.

For a narrowly implemented fix:

1. identify the true pre-change artifact (backup, parent blob, or patch base);
2. hash the base and current files;
3. derive the exact fix delta, not whole-file working-tree diff;
4. run `git apply --check` against the intended clean source lineage;
5. inspect tests for unrelated older content.

`git apply --check` proves placement only. It does not prove behavior, file-mode correctness, or complete scope.

## Phase 5 — Forecast Conflicts Safely

Use modern two-commit `git merge-tree --write-tree` for rename-aware conflict forecasting, but isolate its object writes in a temporary object database. Do not run it against the real object database under a read-only contract.

Distinguish:

- **Textual forecast:** paths current Git marks conflicted.
- **Auto-merge review:** overlapping paths merged automatically but still need inspection.
- **Semantic validation:** tests/config/runtime checks after integration.

A clean textual forecast is not a validated integration.

## Phase 6 — Integration Order

Default no-loss order:

1. preservation barrier;
2. rescue unique committed histories;
3. reconstruct narrowly scoped changes on the clean source lineage;
4. commit logical units separately after approval;
5. run targeted, full, and isolated E2E tests;
6. push a new feature/rescue branch, not the default branch;
7. create a fresh integration branch;
8. merge divergent related history with a real merge commit when history preservation matters;
9. resolve textual conflicts and review auto-merges;
10. compare manifests and run semantic validation;
11. only then update the source-of-truth/default branch.

Keep unrelated runtime and upstream-source clones as separate reconciliation lanes.

## Reporting Contract

Every conclusion must carry one label:

- **DIRECTLY VERIFIED** — raw current command output.
- **FORECAST** — merge/patch simulation, not an actual integration.
- **PARTIAL** — some layers proven, semantic or remote state still open.
- **UNVERIFIED** — reviewer/user report not independently accessible.
- **DATA GAP** — exact missing evidence and attempted route.

Report contradictions explicitly. Different dirty counts may reflect different timestamps or `--untracked-files` modes; do not average them.

## Pitfalls

- **Git Stash Reflog Bundling Pitfall:** Running `git bundle create ... --all refs/stash` only preserves `stash@{0}` because `refs/stash` is a single ref pointer and older stashes (`stash@{1}`, `stash@{2}`, etc.) live strictly in the reflog, which `git bundle` rev-list traversal does not walk. To safely archive all stashes in a Git bundle, parse each stash commit SHA (`git rev-parse stash@{N}`) and create explicit named refs/branches (e.g. `git branch archive/stash-N <SHA>`) before creating the bundle with `--branches`.
- **Two-Folder Divergence Trap (Engine vs Application Repo):** In setups where `~/.hermes/hermes-agent` is the active runtime clone of upstream Hermes, and `~/hermes-agent-personal_assistant-work` is the personal customization repository, emergency live fixes in the engine folder create dirty files that get stranded. When an upstream update is needed (`hermes update`), the agent panics about dirty files and creates endless temporary branches (`feat/*`) that never get pushed to `main`. **Fix:** Port verified live fixes back to the single personal canonical repo (`hermes-agent-personal_assistant`), retire the redundant second clone, and follow the single-repo topology. See `references/single-repo-vps-consolidation-and-nightly-hygiene.md`.
- Saying “commit cannot conflict” when the user asked whether future consolidation is safe.
- Calling repositories unrelated because their directories differ.
- Treating remote-tracking refs as current remote state.
- Calling a normal clone a worktree without checking git-dir/common-dir.
- Committing whole dirty files under a narrow fix message.
- Using deprecated/trivial merge simulation and reporting its conflicts as current merge behavior.
- Running `merge-tree --write-tree` against the real object database during a read-only audit.
- Cleaning object databases, dangling commits, worktrees, or backups before preservation.
- Declaring a clean merge "working" without semantic tests.
- Pushing to a remote default branch without first checking lineage (`git merge-base` empty = unrelated repo, not a stale branch — see Push-boundary check).
- **False 'No Unpushed Code' from narrow clone scan:** Inspecting only the canonical work clone (`hermes-agent-personal_assistant-work`) and declaring that "nothing needs commit/push" while live code changes occurred in nested core (`~/.hermes/hermes-agent`), plugins (`~/.hermes/plugins/*`), or local-only documentation vaults (`~/wiki`). Always check file mtimes and cross-session tool calls across all active repositories.
- **SSH Remote fallback on Headless VPS:** When pushing to personal GitHub repos fails with `fatal: could not read Username for 'https://github.com': No such device or address` (due to lack of interactive credential helper or `gh` CLI), check `ssh -T user@example.invalid` and switch remote URL from HTTPS to SSH (`git remote set-url origin user@example.invalid:owner/repo.git`) before retrying the push.
- **Upstream Plugin vs Personal Remote Push Boundary:** Installed plugins under `~/.hermes/plugins/<name>` often clone directly from third-party upstream repositories (e.g. `jaeyeopme/antigravity-provider`). A VPS deploy key is typically scoped only to the user's personal organization (`amirulhazym/*`). Attempting to push to a third-party upstream origin will fail with `Permission denied to deploy key`. Check remote URL and owner before attempting a push; keep upstream plugins local-only or push to an explicitly configured personal fork.
- **Pushed-Branch vs PR-Created Conflation:** Pushing a branch (`git push origin <branch>`) only publishes the ref to the remote; it does NOT open a Pull Request. The URL ending in `/pull/new/<branch>` printed by git is a web UI creation prompt, not an existing PR. Never report that a PR exists until verified against the GitHub API or CLI.
- **Upstream Tracking vs Fork Update Fatigue:** When checking if Hermes can be updated (`hermes update`), `git status` in `~/.hermes/hermes-agent` tracks upstream `origin/main` (often thousands of commits ahead) while custom user fixes live on `origin-vps/main` (personal fork). If dirty files are present, immediately distinguish whether they are recent local verified patches vs throwaway edits, explain why upstream differs from the personal fork in one concise breakdown, and avoid repeated alarmist warnings. The direct fix is: commit verified changes to the personal fork (`origin-vps`), verify tests, then cleanly rebase/stage rather than stalling with generic git blockers.

## Verification Checklist

- [ ] No mutation occurred without explicit approval.
- [ ] Every candidate directory was classified as repo/clone/worktree/snapshot/non-repo.
- [ ] Current remote heads were checked without mutating local refs.
- [ ] Exact graph relationships and ancestor direction were recorded.
- [ ] Unique commits, uncommitted paths, ignored data, secrets, and PII have preservation destinations.
- [ ] Narrow changes were isolated from older WIP.
- [ ] Conflict forecast used current rename-aware behavior in an isolated object store.
- [ ] Auto-merges received semantic review.
- [ ] Tests ran in the intended source lineage before any source-of-truth claim.
- [ ] Candidate, committed, pushed, integrated, deployed, and live states remain distinct.
