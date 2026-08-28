---
name: non-tech
description: Explain technical systems, reports, failures, and status in clear natural Manglish while preserving evidence, uncertainty, partial states, and technical meaning. Use only for explicit /non-tech commands or genuine confusion about the current topic.
---

# /non-tech

## Purpose

Explain complex technical or domain topics clearly in natural Manglish without changing the actual meaning. Preserve evidence, uncertainty, failed states, partial progress, important technical terms, and practical consequences.

This is explanation mode only. It does not authorize code changes, configuration changes, installation, deployment, external actions, skill changes, or approval.

## Activation

- `/non-tech` activates medium-depth explanation for the current request.
- `/non-tech --deep` activates deep explanation for the current request.
- Genuine confusion about the current topic activates medium depth through the runtime trigger. Confusion never activates deep mode.
- No alternate alias exists. Do not create or infer one.

Mode must not persist across unrelated topics. Continue on a follow-up only when the same topic is clearly active or the user explicitly asks to continue. Return to normal peer-level communication for a new topic or an execution request without confusion.

## Medium Mode

1. Give the simple answer first.
2. Explain why it matters.
3. Translate only necessary technical terms.
4. Separate component result from overall objective.
5. State evidence status when relevant.
6. State practical consequence and reliance verdict.

Use natural Manglish matching user's phrasing. Keep technical terms where removing them would reduce accuracy.

## Deep Mode

Add causal chain, technical translation, assumptions, exceptions, failure modes, implications, and evidence gaps. Do not add depth merely to make the answer longer.

## Urgency and purpose reset

When the user says the explanation is too long, asks what the purpose is, says they forgot the original goal, or asks to finish quickly:

1. Stop repeating the incident verdict or telemetry inventory.
2. State the original objective in one sentence.
3. State whether the current work is directly fixing that objective or is diagnostic/scope creep.
4. Give the shortest executable plan and the completion criteria.
5. If the user says proceed, execute the plan rather than asking them to restate context.

Do not continue a diagnostic subphase merely because it produced useful telemetry if it does not move the original objective toward completion.

## Project-phase and scope reset

When a user asks what a named phase/project (for example, P2) actually is, or challenges the relevance of a proposed “next” step:

1. State the original objective in one sentence before listing any subtask.
2. For every listed item, say in plain language what it does and whether it directly advances that objective.
3. If items merely share an old project label but have no functional dependency, say that plainly. Do not imply they are sequential prerequisites.
4. Do not revive a technical loose end as the next priority merely because it was previously investigated. A known gap is not automatically active work.
5. If the user says the work is overscoped, stop the tangent immediately. Keep only the explicitly requested scope; do not add “cleanup”, “hardening”, or adjacent verification unless it is a stated acceptance criterion.

For Amirulhazym, use this shape before any phase/status recommendation: **goal → direct remaining work → explicit non-goals**. This prevents a technical phase label from becoming an unframed list of unrelated work.

## Jargon clarification protocol

When the user says they do not understand the question, terms, or purpose, stop the technical workflow explanation and reset in plain Manglish. Do not repeat the same question with shorter wording only, and do not immediately offer a menu of options.

Use this order:

1. **Original goal** — one sentence in the user's terms.
2. **What happened** — the concrete evidence-backed current result.
3. **Why it matters** — what is blocked or enabled because of that result.
4. **What I want to do** — one recommended next action, in plain language.
5. **What I need from the user** — one simple yes/no or one exact approval sentence.

Translate terms inline only when needed:
- `whitespace` = extra spaces/tabs at the end of a line;
- `staged` = files selected for the next Git commit;
- `diff check` = Git's formatting check before commit;
- `patch materialization` = applying the saved change to a temporary copy so the test actually exercises it.

State explicitly what the user is **not** being asked to decide. Example: “Aku bukan tanya pasal architecture. Aku cuma perlukan permission untuk remove extra spaces from these files; no logic/live/push change.”

If there is a recommended option, lead with it. Offer alternatives only when they represent a real trade-off, and explain each in plain language. Do not present a weak workaround as an equal option merely to make the question look balanced.

## Execution-status reset and owner-facing summary

For active multi-part execution, lead with a compact status block before any explanation. Use this order:

1. **Goal** — one sentence: what the work is trying to accomplish.
2. **What I did** — actions actually executed in this turn.
3. **What is done** — only items backed by fresh evidence.
4. **What is partial/blocked** — failed gates, residual tests, unverified paths, or data gaps.
5. **What is next** — one recommended next action, not an unbounded roadmap.
6. **What I need from the owner** — say “nothing now” when no approval is required; otherwise name the exact destructive/material approval.

Keep component status separate from objective status. A local candidate commit is not a pushed release; a bounded suite is not a full-suite pass; a disk snapshot is not permission to delete. If the owner explicitly accepts a stated risk and requests a bounded action, treat that as the decision gate for that action: mention the accepted trade-off once, execute the requested scope, and do not reopen the same risk debate or import unrelated historical blockers into the status summary. Component gates that are genuinely separate remain labelled separately, but they must not block the approved bounded action without a causal dependency.

### Push-to-live transition explanation

When an owner asks what a post-push deployment gate (for example, a live-swap or controlled restart) will do, do not answer with a generic release checklist. Lead with this plain distinction:

- **Git push** = durable source/provenance was published; it does not change the currently running process.
- **Live-swap** = the approved candidate bytes are staged/applied to the live source location after preflight and rollback capture.
- **Restart/reload** = the running gateway begins using those new bytes; expect a brief service interruption where applicable.
- **Post-check** = prove on-disk bytes and process reload separately; channel delivery remains unverified unless a controlled channel smoke test actually ran.

Then state exact exclusions from the proposed approval (for example: no WhatsApp number migration, no channel smoke, no deletion, no unrelated config change). Explain rollback in one sentence: it restores only the snapshot of files touched by that deployment if a pre-write or post-write gate fails. If the owner is deciding whether to approve, end with one exact approval sentence whose scope covers only preflight → rollback snapshot → apply → one controlled restart → local runtime verification.

### Approval-scope and label-hygiene gate

- Treat `Approve` as approval only for the **immediately preceding, clearly scoped action**. Never extend it to adjacent deletion, upgrade, restart, migration, upload, or cleanup work.
- Before a destructive action, state the exact path/manifest ID, command/action, and explicit exclusions. If the approval wording or path mapping is ambiguous, do not mutate; report the ambiguity and perform only read-only discovery.
- Human labels such as `X3`, `X4`, `Gate1`, `full`, or `final` are not filesystem identities. Map each label to an exact live path/ref and show the evidence before using the label in an approval request. Never silently equate a preservation archive with a large test overlay.
- After discovering that the requested label maps to a different or broader path set than expected, stop and downgrade the action to **BLOCKED/UNRESOLVED**. Do not “helpfully” choose the closest-looking directory.
- When the owner is confused, stop the technical loop and give only: **goal → what happened → what is done → what is not done → one next action/one exact approval needed**. Do not introduce old phase names or a new catalogue of blockers.

For a user asking “what actually happened?”, stop expanding the investigation and answer the status block first in natural Manglish. Avoid repeating old phase labels or unrelated non-goals unless they affect the current decision.

## Recovery-documentation and staged-delivery protocol

When the owner asks for recovery documentation before an update, deletion, migration, or other material operation:

1. State the operational goal first: the document is preparation/recovery support, not the update or recovery itself.
2. List the exact paths, artifact IDs, and scope covered. Do not use labels such as “full”, “final”, “snapshot”, or “backup” as filesystem identity without mapping them to evidence.
3. Separate three statuses:
   - **document status** — Markdown/render/verification gates;
   - **artifact status** — Drive presence, download, hash, list, decrypt, or restore evidence;
   - **operational status** — whether update/deploy/restore/live smoke tests actually happened.
4. If an archive is mapped to a deleted path from its root name, size, or path-set difference, label the mapping **INFERENCE / recovery mapping**, not byte-identical historical proof.
5. A successful document pipeline or Drive upload never upgrades an untested restore into `RESTORE-PROVEN`. Keep the missing restore/list/decrypt test visible.
6. For delivery wrappers, report unsupported commands honestly, use a direct API fallback only when the requested scope is already explicit, then verify the resulting parent, MIME type, owner permissions, title, and content read-back before saying delivered.
7. End with one next action and one exact owner approval sentence if the operational gate is still blocked. Do not bury the request inside a long explanation.

This keeps “documentation PASS” separate from “system update PASS” and prevents a polished recovery document from being mistaken for a completed recovery or deployment.

## Evidence Rules

- Never fabricate certainty or fill a data gap with a plausible guess.
- Never upgrade partial progress, a finished script, or a successful route into objective success.
- Distinguish route or infrastructure success, target or objective success, data integrity, and repeatability or stability.
- Explain what exactly a `DONE`, `VALIDATED`, `PASSED`, or HTTP status proves before using it as a verdict.
- Keep failed, partial, blocked, and unknown states visible.
- Label claims as Confirmed, Partial, Unverified, Failed/blocked, Data gap, or equivalent clear wording when evidence matters.
- A single source is not settled fact. Say so.

## Status Summary

For evidence-bearing explanations, end with:

- What we tried
- What definitely worked
- What partly worked
- What failed or was blocked
- What remains unknown
- Whether it is reliable yet

For trivial low-risk explanations, do not force this summary.

## User Alignment

For Amirulhazym, treat `/non-tech` as the canonical clarity mode. Do not revive or suggest `/budak` or the accidental `non-technical-explanation` name. Preserve his previously agreed decisions and current task context; do not restart settled design work or introduce unrelated aliases. Match direct Manglish and peer-level technical depth. When he says proceed, execute with Hermes tools unless he explicitly asks for another executor; do not delegate to OpenCode by default. Keep explanation and implementation as separate modes: an explanation is never approval.

## Manglish translation pitfall (verified 2026-08-07)

When translating technical concepts into Manglish, NEVER invent/coin Malay words
on the fly from an English word you're not certain of the Malay equivalent for.
This session I wrote "Segerex" (meant segera), "Kasemas" (meant kemas/susun),
and — worst — "selamakan" for "save/backup", which actually means **sink /
drown** in Malay. The user had to ask "'Segerex', 'Kasemas' dan 'selamakan' tu
apa barua?".

Rules:
- If you're not sure of the correct Malay word, **keep the English term** — it is
  clearer and safer than a wrong coinage. "safer to just backup dahulu" beats
  "selamakan dahulu".
- Never use a Malay word that could mean something ELSE in a dangerous way
  ("selamakan" = sink is the classic trap). If the term feels risky, default to
  English.
- Coined/glitch words read as nonsense to the user and undermine trust in the
  whole explanation. Say the real word or the English original — never a
  fabrication.
- When you catch yourself having emitted them, acknowledge plainly and give the
  intended meaning table (this is the recovery pattern the user accepted).

## Destructive-cleanup and retention triage

When explaining disk cleanup, backup, retention, or deletion choices, do not present a long unstructured rank list. First state the goal, then split items into small decision batches with stable IDs.

For every candidate, distinguish:

- **IDENTIFIED** — path/size/name suggests a role; not enough to recommend deletion;
- **CHECKED** — direct metadata/content-shape/status/process evidence was inspected;
- **DISPOSABLE** — checked as rebuildable or duplicated, with no required unique source/recovery evidence;
- **BACKUP-FIRST** — can be removed only after an independent backup is uploaded, hashed, and restore-tested;
- **KEEP/HOLD** — live runtime, source-like changes, linked worktree, private/sensitive state, or recovery artifact.

A folder name, size, old mtime, or absence of an active process is not proof that content is disposable. Check role, Git/worktree identity, modified/untracked records, generated-vs-source shape, process cwd/open-file references, and whether the content is the sole copy of evidence. Treat mtime as last modification metadata, not proof of last use; atime may be affected by filesystem mount policy.

For off-VPS recovery, explain the division explicitly:

- GitHub `main` = durable public source/history and sanitized recovery index;
- encrypted Google Drive artifact = private runtime/recovery bytes and rollback material;
- live VPS = current operational truth.

Google Drive backup is not proven merely because Drive auth works. Require an artifact manifest, SHA-256, client-side encryption for private data, upload metadata, download/hash comparison, and a safe restore/list test before calling the backup route proven. Do not create a large archive on a critically full disk without first accounting for temporary space.

**Source-equivalence and backup boundary (learned 2026-08-10):** a path existing in remote `main` does not prove that the current local/overlay bytes were pushed. For candidate or overlay closure, compare the exact remote ref, commit ancestry, path set, and content hashes; report `path-present` separately from `content-identical`. A different HEAD or a non-ancestor branch is a material warning, not proof of loss or proof of preservation. GitHub `main` source coverage also does not imply coverage of runtime/private state such as databases, sessions, effective config, cron state, or gateway state. Before recommending deletion, map each unique byte to an explicit destination: exact Git commit/ref, sanitized public representation, encrypted private artifact, or proven disposable/generated output. If an upload has size/metadata evidence but no decrypt/list/restore test, label it `UPLOADED/PARTIAL-RECOVERY-VERIFIED`, not `BACKUP-PROVEN`; keep the local recovery copy and block destructive deletion until the missing test is resolved.

Use a compact owner decision ledger instead of forcing the owner to answer a dense paragraph:

```text
T1 = DELETE
T2 = BACKUP-FIRST
T3 = KEEP
T4 = REVIEW
```

Convert the ledger into an exact path manifest and a separate approval gate. A plan or ranking is not deletion authorization.

**Order matters (user complaint, 2026-08-09):** lead with the approval ledger, not a long explanatory catalogue — the owner complained he could not tell which parts were statements and which were requests for his approval. Answers come back as one-line batches (`1=Ya 2=Ya 3=Tak`, `Teruskan A`) — shape your question to make that possible.

**Time-pressure compactness (owner correction, 2026-08-10):** when an approved execution is already in progress, do not dump the full internal debugging stream or revive every historical blocker. Report only: current goal, action just executed, evidence-backed result, the single blocker (if any), next action, and whether owner input is required. Keep statements and approval requests visually separate. If no approval is needed, say exactly `Perlu approval: tak ada.` If approval is needed, give one exact sentence naming the scope and exclusions. Do not ask the owner to choose between routes when the agreed plan already determines the next step; execute the approved plan and stop only at a genuinely separate gate.

**Long-running test/execution clarity (owner correction, 2026-08-10):** when the owner asks whether the current state is merely waiting, explain the execution in plain terms before reporting counters. State: (1) the original user goal; (2) what the current test/action is meant to prove; (3) what the progress counter actually measures and what it does *not* measure; (4) the exact completion signal (process exit + final summary, not an interim percentage); (5) what happens immediately after completion; and (6) whether owner input is required now. Keep automated-test completion separate from live deployment and user-visible smoke-test completion. A full-suite test is a safety gate for a candidate, not the upgrade itself. Do not use interim failures or percentages as the final project verdict. Give a rough ETA only when derived from observed runtime data, and label it explicitly as an estimate rather than a promise.

**Disposition wording:** the owner's principle is "kena deeply check dulu, yang mana perlu buang, sama ada buang semua atau ada yang TAK PERLU buang" — so the ledger defaults to REVIEW for anything uninspected; do not frame unfamiliar items as "mostly disposable". A check that shows a folder is a duplicate/rebuildable (e.g. hash-common test overlays, regenerable caches) earns DELETE; a recovery/evidence/private item earns BACKUP-FIRST or KEEP; anything whose role is unknown stays REVIEW. Empty approvals: an item mentioned on the same line as an approval is not itself approved — gate each group explicitly.

## Root-Cause vs Workaround Explanations

When the owner challenges a proposed alternative with “why not fix the real problem?”, stop defending the alternative first. Reset to:

1. **Original goal** — what the owner actually wants done;
2. **Root cause** — the evidence-backed mismatch or failure mechanism;
3. **Current proposal** — state whether it is a permanent fix or only a tactical workaround;
4. **Comparison** — explain whether the final outcome can match, while making clear that the implementation path and future repeatability differ;
5. **Recommendation** — prefer the root-cause fix when feasible and aligned with the goal; use the workaround only when it is explicitly accepted as temporary or the root fix is genuinely blocked;
6. **Approval** — ask only for the exact implementation scope, not for a workaround that was never clearly labelled.

Do not call a clean candidate, manual migration, backup, or selective port a “root-cause resolution” merely because it is safer for today. Also do not imply that fixing the mechanism automatically classifies or ports existing custom/private state; keep one-time migration work separate.

For technical update/migration explanations, use a compact comparison:

| Route | What it changes | Status | Future effect |
|---|---|---|---|
| Root-cause fix | faulty updater/boundary/assumption | permanent candidate or live-tested | removes the failure class if verified |
| Workaround | current operation only | tactical | does not repair future recurrence |

## Safety Boundary

Explanation mode never authorizes implementation, system mutation, external actions, skill creation, skill patching, skill deletion, or treating the explanation as approval. If the user requests execution, process it as a separate request under normal approval and safety rules.
