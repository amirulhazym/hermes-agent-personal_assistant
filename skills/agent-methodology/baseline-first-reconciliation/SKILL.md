---
name: baseline-first-reconciliation
description: "Use before recovery or post-merge reconciliation plans."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [recovery, reconciliation, migration, provenance, baseline]
    related_skills: [evidence-first-feasibility-assessment, evidence-first-communication, planning-and-task-breakdown]
---

# Baseline-First Reconciliation

## Purpose

Use this skill when a task sounds like **recover the original setup**, **restore after a merge/update**, **reconcile live and source**, **rollback**, **port pre-change work**, or **fix drift after migration**.

The failure this prevents is a plan that starts from today's symptom, patches one consumer, and then incorrectly describes that patch as recovery of the original system. Recovery requires provenance. A plausible fix is not proof of restoration.

## Core rule

```text
owner-designated temporal target → classify design vs implementation artifacts → pre-change inventory → current live probe → four-layer matrix → objective classification → minimal plan
```

Do not reverse this order. Do not write an implementation plan from a compacted conversation summary when a canonical design document, handoff, or source artifact exists.

## Temporal-authority gate

Before calling any artifact the recovery baseline, establish **which artifact the owner means to recover**. A GDoc, wiki, or design record can be canonical for intent while being an intentionally older baseline that predates source access, a merge, deployment, or the owner-designated last known working version.

1. Record the owner’s temporal boundary exactly: date, timezone, and wording such as “latest working version before <event>.”
2. Classify the document: `BASELINE-DESIGN`, `CANDIDATE-BUILD`, `RELEASE-MANIFEST`, `RUNTIME-EVIDENCE`, or `HISTORICAL-CLAIM`.
3. Search for actual artifacts at or immediately before that boundary: commit/tree, preserved worktree, manifest, source hash, and runtime/service evidence.
4. Prove both **provenance** (it belongs to the requested period) and **behavior** (it contains or demonstrates the expected contract) before naming a candidate `latest`, `working`, or `recovery-ready`.
5. If the owner-designated artifact is not located, say `LATEST OWNER-DESIGNATED ARTIFACT NOT LOCATED`. Do not silently substitute an older design doc, a convenient branch, or a compatible patch.

A branch name, commit date, file mtime, or historical “deployed” statement is a lead—not recovery authority. A direct live probe proves present behavior, not which historical artifact should replace it.

## Objective vocabulary

Classify the work before selecting actions:

| Objective | Meaning | What it is not |
|---|---|---|
| **RECOVERY** | Restore a known prior artifact or behavior whose identity and content are proven | A new fix that merely seems compatible with the old design |
| **RECONCILIATION** | Determine what survived, was omitted, drifted, contradicted, or was never transferred | A blind rollback or wholesale merge |
| **ROOT-CAUSE REPAIR** | Correct a directly reproduced current defect at its causal boundary | A workaround applied before the dataflow is traced |
| **NEW DESIGN** | Introduce behavior not present in the original contract | “Recovering” a desired behavior that never existed |

A task may contain more than one objective, but each objective must have its own lane, evidence, acceptance criteria, and gate.

## Mandatory procedure

### 1. Freeze the question before touching implementation

Write a one-line statement:

> “This investigation is [RECOVERY / RECONCILIATION / ROOT-CAUSE REPAIR / NEW DESIGN] of [scope]. It will change [x] and will not change [y].”

If the owner asks “what are you actually trying to do?”, stop implementation and answer this scope question first. Do not respond with a list of fixes whose relationship to the original goal is unclear.

### 2. Read the canonical artifact completely

Read the supplied Google Doc, design record, handoff, spec, pre-change report, or release manifest before relying on:

- compacted session summaries;
- another agent’s synthesis;
- file names or branch names;
- a previous “done/deployed” statement;
- the first obvious live symptom.

For Google Docs, use a full structural read that walks paragraphs **and tables**. Paragraph-only extraction can silently omit the actual contract, evidence ledger, status table, or acceptance criteria.

Record:

- document identity and URL/path;
- document date/version and update date;
- stated scope and explicit exclusions;
- source-of-truth claims;
- acceptance criteria;
- candidate/live/deployment status claims;
- known data gaps and contradictions.

### 3. Inventory the pre-change boundary

Identify the exact boundary named by the owner: merge, update, migration, deployment, or date. Before that boundary, inventory the relevant:

- documentation and design records;
- source files and tests;
- configuration/data schemas;
- candidate branches and commits;
- runtime hooks and entry points;
- state stores, logs, and backups where relevant.

State the search boundary in the report. Use `NOT FOUND IN CHECKED PATHS` when the inventory is incomplete; never upgrade that to “does not exist.” Do not claim “all related files were reviewed” without an explicit path set or search method.

### 4. Probe the current system directly

A historical document is evidence of what was recorded at that time, not proof of current runtime behavior. Run the smallest read-only probe that tests each important capability.

Examples:

- resolver: invoke the actual resolver with the canonical alias;
- safety gate: run a dry-run/isolated test and inspect whether the write subprocess is called;
- reminder: freeze the date/time and render the exact output;
- source: inspect current branch, commit, diff, and file presence;
- deployment: compare live destination hashes to the manifest;
- channel: separate scheduler success, script output, state mutation, and transport receipt.

Code reading creates a hypothesis. The live probe upgrades it to a finding—or falsifies it.

### 4a. Runtime reload boundary

For a long-lived gateway/daemon, the current file is not proof of the loaded implementation. Before attributing a regression to the current source:

1. Capture the live PID/start time and the hook/module-load timestamp.
2. Capture current runtime/source hash and mtime, plus the commit/change time that produced it.
3. Run a direct probe against the current file and compare it with live audit output.
4. If the process predates the fix and logs still show old behavior, classify the runtime row as `CONTRADICTED: stale loaded code`; classify the file only as `SOURCE/FILESYSTEM-PROVEN`.
5. Treat reload/restart as a separate operational gate. Do not report a file fix as live until the process has loaded it and the active path is re-tested.

### 5. Build the four-layer evidence matrix

Never collapse these layers:

| Layer | Question | Allowed status labels |
|---|---|---|
| **Original contract/design** | What was intended? What invariants were specified? | DOCUMENTED / PARTIAL / CONTRADICTED |
| **Historical candidate** | What was implemented and tested then? | HISTORICAL / TESTED-THEN / UNVERIFIED-NOW |
| **Current source/worktree** | What is versioned, modified, staged, or merely present? | PROVEN / DIRTY / MISSING / UNVERIFIED |
| **Current live runtime** | What does the running path do now? | PROVEN / CONTRADICTED / PARTIAL / UNVERIFIED |

For every major claim, attach the shortest direct evidence: quoted document text, exact path, commit, command, raw output, test result, or URL.

### Closure audit: negative confirmation is a valid result

When an owner challenges an audit with “if you cannot confirm, that is not an audit,” do not stop at a vague `UNVERIFIED` merely because the historical completion claim is contradictory. Continue the reconciliation until the evidence supports a concrete status:

1. Reconstruct the exact owner acceptance criteria from the original goal. Do not use the previous assistant’s summary, a task-list state, or a goal row’s free-text `last_reason` as the requirements.
2. Build one row per criterion across independent layers: filesystem/config, source and candidate identity, local ref, pushed remote ref, PR/merge state, test result, running process, logs, and user-visible behavior where applicable.
3. If any required row has a direct failure—such as an unmerged target ref, remote/local divergence, a failing regression test, or a missing required path—return **CONFIRMED NOT COMPLETE / FAIL**. That is a confirmed audit result, not an inability to audit.
4. Reserve `UNVERIFIED` for a criterion that the available evidence genuinely cannot decide. A confirmed failure and an undecided row must not be collapsed into one soft disclaimer.
5. Reconcile exact sets and identities, not labels. “16 files synced” requires the requested 16-path manifest, destination-ref presence, byte/hash comparison where relevant, and proof that the destination is the required `main`/release ref. A different 16-file diff is not equivalent evidence.
6. Query moving targets directly (`git ls-remote`, remote API/PR state, live service state). A local tracking ref, “up to date” display, local branch, green component test, or successful CI run cannot override contradictory direct evidence.
7. Treat DB `done`/`cleared`, `last_verdict`, `last_reason`, empty contract fields, and empty gates as metadata. They do not close external acceptance criteria, and state must not be mutated merely to make the goal appear complete.
8. Derive the parent verdict mechanically: all required rows `PROVEN` → `COMPLETE`; any row `FAIL` → `CONFIRMED NOT COMPLETE`; any undecided row with no failure → `PARTIAL/UNVERIFIED`. Report what passed, the exact failing evidence, the remaining unknowns, and what was not changed.

Reusable ledger and command pattern: `references/standing-goal-completion-audit.md`.

### 6. Preserve contradictions instead of averaging them

When documentation says “deployed” but a fresh live probe shows the capability missing, report both:

```text
Historical documentation: CLAIMED deployed (date/source)
Fresh live probe: current behavior = [raw result]
Verdict: CONTRADICTED / current status UNVERIFIED until lineage is reconciled
```

Do not silently pick the more convenient source. Do not “repair” the contradiction by editing the live state, rewriting history, or updating the document before the source of truth is established.

### 7. Separate work lanes

At minimum, split these when they coexist:

1. **Baseline/recovery lane** — establish what the original system was.
2. **Reconciliation lane** — map candidate/source/live differences.
3. **Root-cause repair lane** — fix a proven defect only after the dataflow is known.
4. **Release/deployment lane** — source closure, tests, commit/push, manifest, deployment, restart, and live verification.

Do not put a medical/runtime fix and an unrelated release cleanup under one “next steps” heading. A release candidate can be incomplete even when the medical investigation is correct, and vice versa.

### 8. Derive the minimal plan from evidence

A proposed change is admissible only when it traces to one of:

- a documented invariant that is missing from the current path;
- a direct contradiction between the intended contract and current runtime;
- a reproducible regression introduced at a known change boundary;
- a required migration/adapter needed to preserve the original contract.

For each proposed change, state:

- objective classification;
- causal boundary being changed;
- exact files/components in scope;
- what remains untouched;
- RED test or reproduction;
- GREEN acceptance test;
- rollback or non-mutation boundary;
- approval/deployment gate.

Do not change a static snapshot merely to make today’s output look correct when the contract says the value is date/version-dependent. Fix the consumer/source-of-truth boundary and test the transition points.

### 9. Report the owner-facing verdict

Lead with:

1. **Verdict:** recovery, reconciliation, repair, or new design;
2. **What was actually checked:** canonical artifact, path set, probes;
3. **What is proven now;**
4. **What is historical or contradicted;**
5. **The actual goal of the next plan;**
6. **What is explicitly not being changed;**
7. **The next gate.**

Use “I checked these paths” rather than “I checked everything.” Use “historical claim” rather than “confirmed” when the only evidence is an old document or transcript.

## Medical/runtime safety boundary

When the reconciled system handles medication or other high-stakes state:

- reconciliation is read-only unless the owner explicitly authorizes a state operation;
- do not alter regimen, dosage, taper, timing, or history to make layers agree;
- treat a live projection as current state, not complete provenance;
- separate source event, parser/validation decision, safety hold, write, and delivery evidence;
- if a historical design and current live behavior disagree, fix the implementation boundary only after the discrepancy is reproduced;
- never call a candidate’s tests proof of live protection without current deployment and live-path evidence.

## Medication stale-state reconciliation

When a reminder contradicts an owner’s latest medication statement, treat it as a four-layer reconciliation problem, not a request to ask the owner again:

1. preserve the exact source statement and stated/derived time provenance;
2. resolve every named drug or compound before any write (`CC` is one atomic Calcium Carbonate + Calcitriol event);
3. inspect the inbound/audit path to distinguish parser rejection, genuine pre-report pending state, quoted reminder text, and successful persistence;
4. preflight the native confirmation writer in dry-run mode, write through the supported path, then read back every drug, time, and slot overall state;
5. report the causal chain and final state briefly when the owner asks for findings—do not substitute a long artifact for the answer.

### Owner-corrected adherence analytics

Never equate a persisted medication state file with physical adherence. Keep two views separate:

1. **Raw-record view** — exactly what the state file says.
2. **Owner-corrected adherence view** — the owner's direct correction of what was actually taken, with uncertainty preserved.

An owner correction may change the adherence classification used for analysis, but must not silently overwrite raw medical history. Preserve the raw artifact and record the correction/provenance separately. Use explicit labels such as `TAKEN_RECORDED`, `EXPLICITLY_SKIPPED`, `UNRECORDED`, `OWNER_CONFIRMED_TAKEN_TIME_UNKNOWN`, `OWNER_CORRECTED_TAKEN`, and `CONFLICT_UNRESOLVED`. A missing time is a data-quality limitation; never infer one from neighbouring slots.

Do not infer that every schedule window has identical clinical strictness. Use the owner-confirmed regimen contract to identify strict-time medicines versus late-tolerant companions. Conditional/optional drugs are not missed required doses when their condition is inactive. Historical metrics must keep today outside the denominator and should report both owner-corrected adherence and raw logging completeness when they differ.

Reusable classification vocabulary, metric rules, and the 2026-08-16 correction fixture: `references/owner-corrected-adherence-analytics.md`.

### Out-of-window confirmation exception

A resolver result answers *which canonical drug and slot* a phrase maps to; it is not a safety-gate `ALLOW`. Run the deterministic gate separately. If it returns `HOLD / SCHEDULE_TIME_WINDOW`, preserve the exact source/time and ask one targeted question about whether this exact late intake is allowed by the existing doctor/protocol rule. An explicit owner answer to log that time authorizes that one event only—not a schedule, window, taper, or routine change.

For an approved one-off exception: dry-run the exact source-backed confirmation, write through the native drug-level path with the canonical `drug_id` (never bare-slot confirm for a partial/multi-drug slot), then read back drug status, exact time, slot overall state, and recalculated chain. If approval is absent, the resolver is ambiguous, dry-run fails, or read-back disagrees, do not write. A successful native write proves the writer recorded the event; it does not prove the gateway hook/runtime is repaired.

Relative times such as `~15 minutes ago` must remain approximate after deriving an `HH:MM` from the live clock. Query output is stronger than a query process exit code when the query schema does not expose an `ok` field. A compound is atomic internally; distinct same-slot intake events may be written separately only with a read-back after each write. Do not claim future reminder suppression until the producer/read path is actually exercised.

Reusable probe, provenance fields, and the stale-reminder decision matrix: `references/medication-stale-state-reconciliation.md`.
Out-of-window exception transcript/protocol: `references/medication-out-of-window-exception.md`.

## Candidate artifact parity and interrupted verification

For a release/recovery candidate materialized from a pinned Git base plus ordered patch artifacts, keep provenance layers separate:

1. Restore Git-recorded modes after patch application; host umask is not evidence of source change.
2. If a test family requires `.git`, build a fresh detached disposable clone, apply the exact same series, and compare relevant file bytes and modes to the non-Git candidate **before** running tests. A tested clone may contain generated files or mutations and is not a valid parity witness.
3. Derive production rollback paths from the deployment manifest's actual runtime entries. Separate byte changes from mode-only differences caused by extraction.
4. Prove temporary base → candidate copy → rollback artifact → base equality for every touched runtime path using both SHA-256 and mode.
5. After all tests, rebuild a clean candidate tree and regenerate its manifest/tree hash; do not promote a tree containing test caches, duration files, or bytecode artifacts.
6. A wrapper's outer exit code is not proof when it masks the inner test return code. If decisive output is truncated or the inner RC is lost, mark that gate UNVERIFIED and rerun with raw output preserved.

An iteration/tool-budget exhaustion is an interrupted workflow, not completion. On resume, re-audit live VCS/filesystem/process state before trusting the handoff narrative, and report candidate, tested, committed, pushed, deployed, and live states separately.

An executable checklist and evidence fields for this flow: `references/candidate-artifact-parity.md`.

## Pitfalls and anti-patterns

| Anti-pattern | Corrective action |
|---|---|
| Patch today’s symptom, call it “restore original” | Classify it as ROOT-CAUSE REPAIR unless restoration provenance is proven |
| Read the canonical document after drafting the plan | Stop, read it first, then re-derive scope |
| Treat “deployed” in a document as current proof | Run a fresh live probe and report contradiction if needed |
| Blind rollback to an old snapshot | Reconcile design/candidate/source/live first; preserve current state |
| Mix medical repair with release cleanup | Split lanes and gates |
| Claim exhaustive pre-change review from a few files | State exact search boundary and use PARTIAL/UNVERIFIED |
| Assume a candidate commit is in current main or live | Prove ancestry, reachability, file presence, deployment hash, and runtime behavior separately |
| Edit a static config snapshot to hide date/version drift | Repair the source-of-truth consumer and test phase/version transitions |
| Report a plan without stating its goal | Lead with the one-line objective and non-goals |

## Verification checklist

Before presenting or executing the plan:

- [ ] Canonical document/spec was read completely, including tables.
- [ ] Pre-change search boundary and relevant path set are recorded.
- [ ] Original contract, historical candidate, current source, and live runtime are separate rows.
- [ ] Contradictions are visible, not averaged away.
- [ ] Objective is explicitly classified.
- [ ] Recovery/reconciliation/repair/new-design lanes are separated.
- [ ] Each proposed change has direct evidence and a reproduction/acceptance test.
- [ ] No state, regimen, config, or history mutation is implied by a read-only reconciliation.
- [ ] Candidate/test/deployed/live statuses are not collapsed.
- [ ] The owner-facing goal and next gate are clear.

## References

- `references/baseline-first-reconciliation.md` — worked evidence matrix, wording templates, and the medical/A4 reconciliation example that motivated this workflow.
- `references/temporal-authority-and-runtime-provenance.md` — distinguishes baseline documentation from the owner-designated latest working implementation; includes provenance checks and red flags.
- `references/runtime-reload-and-config-contract.md` — live PID/module-load reconciliation, ignored-config provenance, anchor-vs-window semantics, and the minimum regression corpus for post-update daemon drift.
