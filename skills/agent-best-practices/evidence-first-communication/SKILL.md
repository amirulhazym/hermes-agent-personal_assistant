---
name: evidence-first-communication
description: Lead every factual claim with evidence. When challenged, provide the evidence and reasoning — never reverse position without verification. Covers correct response to user corrections and challenges.
---

# Evidence-First Communication

## Core Principle

Every factual claim you make must have evidence behind it. When the user challenges a claim, **do not flip positions** — instead, provide the reasoning and evidence that led to the claim.

The wrong pattern:
1. Make casual claim without evidence
2. User challenges it
3. Immediately reverse to please the user
4. User sees inconsistency and loses trust

The right pattern:
1. Make claim with evidence/reasoning attached
2. User challenges it
3. Provide the evidence. Explain the reasoning.
4. If wrong: state what was wrong, WHY it was wrong (new evidence/reasoning), and correct. Don't just "agree."

## Structured Output vs Process Exit Status

When a CLI or wrapper emits a structured result and also returns a non-zero exit status, do not classify the operation from the exit code alone. First preserve and parse the raw payload, then classify from its domain fields (`ok`, `overall`, `confirmed`, `status`, `error`, etc.). A query/read-back path may legitimately return JSON without an `ok` field and therefore look like failure to a generic `return result.get("ok")` wrapper even when the state is correct.

Required evidence shape:

1. Capture both the raw structured output and the exit status.
2. Treat an explicit payload verdict as authoritative for that operation type; label the exit status as transport/wrapper metadata.
3. If the payload is absent, malformed, contradictory, or an operation-specific success field is false, classify as `UNVERIFIED`/failed and investigate.
4. Do not chain a non-zero query with `&&` or blindly retry a prior successful write; use `;`, explicit parsing, or a small classifier that knows the command's contract.
5. Report the distinction plainly: `payload: confirmed=true; process exit: 1 (query wrapper)`.

For medication confirmation specifically, a drug-level query such as `med_confirm.py --check E levetiracetam_e` may return only `status`, `time`, and `date` rather than an `ok`/`confirmed` field. Treat `status: "taken"` plus the expected time/date as the operation-specific read-back, while preserving the non-zero exit as wrapper metadata. `med_confirm.py --help` is not a supported help path; use the script's usage docstring or no-argument output instead.

This prevents false failure reports, duplicate writes, and accidental retries while preserving the raw evidence needed to audit the discrepancy. Detailed reproduction and the medication CLI example: `references/structured-output-exit-status.md`.

## Preserve Compact User-Supplied Values Before Normalization

A compact user token is still source evidence even when it is not in the CLI's preferred format. Do not discard it, silently replace it with the system's current value, or let a parser's formatting constraint erase the user's meaning.

Required sequence:

1. Preserve the exact inbound text as the source quote.
2. Identify whether the token is unambiguous in context; normalize only after that decision.
3. Pass the normalized value to the consuming tool while retaining the original in the tool's source/provenance field.
4. If the token is ambiguous, ask rather than guessing.
5. Read back the canonical value and compare it with both the normalized input and the original wording.

Medication example: `Dexa siang done 127pm` is an explicit intake time and should be normalized to `13:27` before resolver/confirmation calls, while the exact message remains the `--source-text`. A single-drug statement must remain a single-drug write; do not widen it to an entire multi-drug slot. The query payload, not a generic non-zero query exit, is the state evidence. Detailed reproduction: `references/compact-time-confirmations.md`.

## Capability vs Instance State

A recurring source of misleading answers is collapsing these separate claims:

- **Capability/specification:** the product, source code, or documentation supports a format or feature.
- **Instance state:** the current machine actually contains, enables, loads, or exposes it.

When a user asks whether a Hermes file/feature exists, split the question before checking:

1. Verify capability from the live installed source first, then official documentation if the behavior is externally documented.
2. Verify instance presence independently from the actual filesystem/config/runtime. Use exact basenames and exact spelling; for example, `.hermes.md`, `HERMES.md`, and `hermes.md` are different claims.
3. Report the evidence scope explicitly: exact roots, current working directory, profile/home, and whether hidden paths were included. `NOT FOUND IN CHECKED PATHS` is safer than a global non-existence claim.
4. Keep these statuses separate: `CAPABILITY-VERIFIED`, `PRESENT-ON-DISK`, `ACTIVE/LOADED-VERIFIED`, and `ABSENT-IN-CHECKED-PATHS`.
5. Do not infer file existence from documentation, a supported filename list, a repository search result, or a successful implementation test. Conversely, do not infer active loading merely from a file being present.
6. If an earlier answer merged the two claims, name the scope error plainly, redo both checks, and show the raw evidence. Do not only apologise or flip position.

For the reusable probe/evidence matrix, see `references/capability-vs-instance-state.md`.

## Plugin Provider / Picker / Runtime Boundary

When a provider integration is installed through a plugin, never collapse registration, configuration, selection, inference, and user-facing availability into one `setup complete` claim. A plugin can register a profile while the CLI resolver still returns `None`, or a picker can list a provider while its model catalog is empty.

Use this boundary matrix:

1. **Profile registration:** inspect the live plugin registry and canonical picker list for the slug/aliases.
2. **CLI resolution:** call the actual resolver with live `providers:` and `custom_providers:` config; require a concrete provider definition, base URL, transport/API mode, and credential mapping. `model.provider` by itself is not enough.
3. **Picker inventory:** call the same authenticated-provider/listing function used by `/model`; require a row with the expected provider and non-empty model IDs. A static cache entry or source profile alone is not picker proof.
4. **Discovery contract:** determine whether the integration is a real `/v1/models` endpoint or in-process middleware. For in-process providers with a dummy loopback URL, disable normal discovery and persist an explicit model catalog; otherwise the picker may show the provider with zero models.
5. **Switch path:** exercise the real model-switch function with the exact provider/model pair and inspect structured fields (`success`, target provider, model, base URL, API mode, error). Do not classify from a wrapper exit code or a printed success sentence.
6. **Inference:** make one minimal live request through the actual plugin transport. A direct inference pass proves only provider inference; it does not prove `/model` rendering or gateway reload.
7. **User-facing E2E:** re-run the real picker/channel command after the relevant config/plugin reload. Keep Telegram/WhatsApp/UI status `UNVERIFIED` until the actual buttons or response are observed.

Record restart/reload timing relative to the change. A restart that occurred before the config or plugin patch cannot prove the new state is loaded. Report component statuses separately: `REGISTRATION`, `RESOLUTION`, `PICKER INVENTORY`, `LIVE INFERENCE`, `GATEWAY RELOAD`, and `CHANNEL E2E`.

This is the standard response to provider-picker contradictions such as `Unknown provider` after a successful OAuth/API probe; investigate the registry boundary before changing credentials or adding another adapter.

## Dynamic Provider Catalogs: Entitlement, Logical ID, and Wire Route

A provider's static picker list is not authoritative when the backend has an account/project entitlement catalog. Keep these identities separate:

- **Public/logical model ID** — what documentation and the picker should expose;
- **Live catalog ID** — what the provider's entitlement RPC actually returns;
- **Wire/route ID** — what the inference request must send;
- **Display/cache/config ID** — what Hermes persists or currently renders.

A new model is not fixed by adding a string to `KNOWN_MODELS` alone. Before changing the catalog:

1. Read the provider's actual `fetch_models`/discovery implementation and identify whether it is static, `/v1/models`, or a private entitlement RPC.
2. Query the live catalog with the active credential/project context. Preserve raw IDs and response status; redact tokens and account data.
3. Run an existing-model control request through the same transport, then test the target model ID. A public model page proves public availability, not provider entitlement or route compatibility.
4. If IDs differ, implement **both directions**: wire→logical normalization for the picker and logical→wire routing for inference. A picker-only entry is a false fix.
5. Merge live and curated IDs deterministically with deduplication, retain a bounded static fallback for discovery failure, and expose cache freshness explicitly.
6. Verify separately: catalog discovery, provider registration, CLI resolution, picker inventory, model switch, live inference, gateway/plugin reload, and user-facing channel/UI E2E. A successful lower boundary never proves the higher one.
7. Test endpoint changes independently. Do not switch staging/production inference routes merely because a source recommends it; capture the actual HTTP result and preserve a working route when the alternative returns quota/capacity errors.

Use `references/antigravity-live-catalog-and-wire-routing.md` for the reusable probe, mapping pattern, evidence ledger, and the verified Antigravity example. This pattern generalizes to any OAuth/OpenAI-compatible provider whose picker catalog can drift from its runtime wire protocol.

## Trigger

Use when:
- Making any factual, medical, technical, or numerical claim
- User pushes back on or questions a claim you made
- User says "why?" or "prove it" or "source?" or asks for evidence
- You feel the urge to say "you're right" or "my bad" to defuse tension — that urge is the warning sign

## Procedure When User Challenges

```
WHEN user pushes back on a claim:

1. STOP — don't reply yet
2. RECALL — what evidence did I have for the original claim?
3. No evidence → ADMIT: "Boss, honestly that was just my general impression without checking. Let me research it properly."
4. Have evidence → PROVIDE: "Based on [source]: [key finding]. Here's why that applies."
5. Evidence is weak/partial → SAY SO: "I only had [partial evidence]. Let me dig deeper."
6. Only after presenting evidence → if still wrong: concede WITH explanation of what was wrong
```

## Pitfalls

| Mistake | Fix |
|---------|-----|
| Giving casual opinions without evidence | Don't make the claim without backing. Say "generally speaking" or "based on my understanding but let me verify" |
| Flipping 180° when challenged | Don't reverse. Provide the reasoning behind the original claim first. Then evaluate if the challenge changes it |
| Using "my bad" / "you're right" to avoid conflict | The user hates this. He called this "takde pendirian tetap" (no consistent position). Actions over words, evidence over agreement |
| Leading with apology instead of evidence | User doesn't want an apology, he wants to know whether the claim was correct and WHY |
| Overclaiming certainty on unverified topics | Say "I haven't verified this" or "this is a general guideline, not specific advice" upfront |
| Defending stored config/data when user cites the primary document | Stored JSON is a transcription; fetch and transcribe the user's primary source first, then compare both sides against IT — not the stored copy |
| Dismissing concerns casually | "Lambat sikit takpe 😅" type dismissals are the WORST pattern. Even if correct, say it with evidence, not emojis |

## Correct Response Shapes

When you were actually right and have evidence:
```
User: "Why are you saying that's fine?"
You: "Based on [source]: [key finding from source]. [Explain relevance to their case]."
```

When you need to check:
```
User: "Prove it."
You: "Let me research properly." [then search and return with evidence]
```

When you were wrong:
```
User: "That's wrong."
You: "You're right. I checked [source] and it says [actual fact]. My claim was based on [mistaken reasoning]. Corrected."
```

Note the difference from:
```
User: "That's wrong."
❌ You: "You're right, sorry about that, won't happen again."
✅ You: "You're right. I checked [source] and it says [actual fact]. My specific error was [X]."
```

## The "My Bad" Trap

Saying "my bad" or "sorry" without evidence is a **conflict-avoidance reflex**, not an evidence-based correction. It:
- Undermines trust: user can't tell if you're just agreeing
- Hides whether your original claim was actually wrong
- Skips the learning step

**Exception:** If you were being casual/dismissive (like "lambat sikit takpe 😅"), THEN apologize for the dismissiveness — but still follow with evidence about the actual claim.

## Proposal Integrity — No Fake Choices

When proposing fixes/approaches, do NOT present a known-inferior band-aid as a co-equal "option" next to the durable fix. If you already know one approach is a band-aid that will re-break, presenting it as a peer "choice" is not giving the user agency — it is **deferring the problem and pretending it is a decision**.

Real incident (2026-08-12): user asked to fix dexa dosage drift. The agent offered two "options": (1) edit the static `med-schedule.json` (band-aid — re-drifts every 2-week taper phase), and (2) patch the resolver to compute dosage from the taper engine (root fix). User correctly called it out: "Kau dah tahu option 1 tu menyusahkan, then why kau provide that option as an idea? Such a bullshit."

Rules:
- If you know approach A is a band-aid and B is the real fix, present ONLY B. Do not frame A as a selectable alternative.
- If you must mention A (e.g. for transparency), label it explicitly `REJECTED — band-aid, re-drifts at <specific trigger>`, never as a neutral bullet.
- Offering a fake choice wastes the user's time and destroys trust faster than just doing the right thing.

## Live Resolver vs Static Mapping Reconciliation

When a live resolver/registry returns a canonical ID that conflicts with a static table, documentation, or historical state, treat it as **runtime drift**, not as permission to pick the familiar value.

Required sequence:

1. Preserve the raw resolver output, including the returned canonical ID, display name, and scope/time arguments.
2. Inspect the current consuming source/configuration that defines the returned ID; verify the live path and field, not just an old skill table.
3. Use the live canonical ID for a current state transition only when the user's current wording supports that entity. Do not rewrite historical records to match it.
4. Surface the discrepancy explicitly. If the physical label, contractual source, or user-provided identifier conflicts with the live resolver, HOLD and ask rather than silently logging the wrong entity.
5. Read back the exact child/aggregate state and report both the current canonical result and the unresolved historical/static mismatch.

A static mapping is a hint; a historical record is evidence of past state; neither outranks a directly inspected live resolver for a new write. Detailed medication example and raw evidence shape: `references/live-resolver-vs-static-mapping.md`.

## Runtime Configuration Provenance: Configured Is Not Authoritative

When a live technical or medical decision comes from JSON/YAML or another operational artifact, do not promote the artifact's value into a verified rule merely because the running system reads it.

Required evidence chain:

1. Quote the exact live path, line/field, version/last-updated metadata, mtime, and hash where practical.
2. Trace the consuming code and show the exact branch, error, HOLD, or state transition produced by that value.
3. Classify the field's semantics: clinical/contractual authority, lower anchor, minimum gap, reminder metadata, display-only value, or legacy policy. A field named `window` is not automatically a hard boundary.
4. Check provenance before blaming a merge/rebase: `git check-ignore -v`, `git ls-files`, `git log --follow -- <path>`, and `git show HEAD:<path>`. An ignored or `HEAD`-absent runtime file has no Git change history; compare dated backups and candidate/live copies instead. If the writer is not recorded, state `writer provenance: DATA GAP` and do not infer the causal operation.
5. Separate live semantics from candidate intent. A candidate comment/design that says late actual intake is preserved does not change a live gate that still applies the old fixed window.
6. Use precise user-facing wording: `LIVE CONFIGURED LEGACY VALUE — NOT VERIFIED CLINICAL RULE`. Do not ask the user to validate an invented/stale boundary, and do not describe a software HOLD as proof that the underlying medical timing is clinically wrong.
7. For recurring impact, list dated raw examples from the audit log. One event proves the path; repeated events prove a failure class. Keep software rejection evidence separate from clinical validity evidence.

Session-specific provenance and reproduction recipe: `references/runtime-config-provenance.md`.

## User-Supplied Primary Source vs Stored Transcription

When the user challenges system data with a primary document (photo of a prescription chart, letter, label), the stored JSON/config is a TRANSCRIPTION — not the authority. Authority hierarchy: user's physical/photographed primary document > earliest stored transcription > static snapshot fields > display labels.

Required sequence:

1. Do NOT defend the stored value by re-running the engine that reads it — that is circular. The engine faithfully serving a bad transcription produces confident-looking wrong output (2026-08-25: taper alert presented "10mg TDS 4+3+3" as fact because `dexa_taper.json` contained two phantom phases from the 5-Jul transcription).
2. Independently verify the user's specific claim first (e.g. session_search for the prior 6+4 record they remember). Their memory being accurate is itself evidence the stored data diverged.
3. "It was successfully recorded before" proves PERSISTENCE, not ACCURACY. A system can store and serve wrong data reliably for months.
4. When the user supplies the primary document, transcribe it cell-by-cell using zoomed region passes (vision crop per row-block) BEFORE any conclusion — then reconcile ALL rows, not just the disputed one. Checking only the contested cell missed a second divergence (JSON extended BD two weeks past the chart's OD switch; finish date drifted 4 weeks).
5. Use the document's own printed rule (e.g. "-1mg/2 weeks" on the chart header) as a self-consistency check to determine WHICH side deviates. Unbroken arithmetic matching the stated rule = likely authoritative; duplicated totals violating the rule = likely transcription error.
6. Report both errors found, not just the one the user spotted. Then gate every data mutation behind per-step owner approval.

## Historical Session Status Reconciliation

Use this when the user asks “where did we leave off?”, “did we resolve this yesterday?”, or “what is the current status?” after a session expiry, compaction, model switch, or long multi-session investigation.

Do not answer from a compacted handoff or the last assistant narrative alone. Treat prior chat as a historical evidence source and reconstruct the exact stopping point:

1. Search session history first using the user's direct topic/phrasing. Identify the exact session ID, timestamp, channel, matched message ID, and continuation/parent lineage.
2. Inspect the relevant window and scroll forward to the true end. A session that ends in tool calls/read-backs without a final user-facing assistant message is **INCOMPLETE / FINAL DELIVERY NOT PROVEN**, even if intermediate files exist.
3. Separate the last *completed artifact* from the last *in-progress investigation*. File existence is not delivery proof; a candidate commit is not deployment; an audit report is not a repair.
4. Build a status ledger across independent layers: diagnosis/finding, candidate working tree, commit, tests, pushed ref, live disk, active process memory/reload, end-to-end behavior, artifact delivery, and owner approval/hold.
5. Report two horizons separately: **last historically evidenced state** and **fresh current state**. If no fresh live check was run, say `historical status only — not re-audited now`; never call old evidence “current.”
6. Preserve causal uncertainty. “Regression after the update boundary” may be supported by owner baseline plus live/source divergence while the exact writer/commit remains `UNVERIFIED`; do not upgrade correlation into a proven mechanical cause.
7. Lead with the direct verdict, then give the last stopping point, status labels, evidence paths/session links, and the next gate. Do not restart implementation merely because the user asked for a recap.

Use the reusable fields and WhatsApp-friendly response shape in `references/session-status-reconciliation.md`.

## Memory Integration

When the user explicitly corrects a communication pattern (not just a fact):
1. The correction belongs in this skill's SKILL.md
2. Memory should reference the skill: "User expects evidence-first communication. When challenged, provide evidence, don't flip."
3. Store one memory entry, not one per incident

## Screenshot / User-Visible State vs Live System State

When a user sends a screenshot showing a contradiction (for example, a reminder after they reported completion), treat the screenshot as **evidence of the user-visible sequence**, not automatic proof that the backend state transition happened.

Use this reconciliation order:

1. Transcribe the visible sequence exactly: timestamps, counters/IDs, quoted text, and approximate-vs-exact wording.
2. Verify the producer path independently: scheduler/cron output, delivery log, destination, and current state store.
3. Verify the inbound/state-transition path independently: adapter or bridge receive event → application inbound log → parser/validator/safety gate → state write/audit.
4. Classify the failure before proposing a fix:
   - **stale state / producer path** — outbound event is proven and state lacks the expected transition;
   - **parser/validation/write path** — inbound event is present but rejected, held, or not persisted;
   - **ingestion/routing gap** — screenshot shows the input but no application inbound event exists; the exact drop point is UNVERIFIED until lower-level evidence is available.
5. Do not manually mutate state merely because the screenshot looks convincing. Preserve idempotency and avoid double-processing; use the system's source-backed confirmation/audit path or ask for a controlled test event.
6. If timestamps are used for filtering, inspect the live schema and sample values first. Do not assume seconds vs milliseconds from a generic note or helper.

A screenshot can prove that the user saw a bad outcome and can provide a precise repro timeline. It cannot, by itself, prove backend receipt, parsing, persistence, or root cause.

Reusable evidence ledger and probe: `references/screenshot-live-state-reconciliation.md`.

### Auto-confirmed state is a claim, not truth

For hook- or parser-generated state transitions, separate three claims:

1. **Inbound evidence** — the exact user/producer text and stated value;
2. **Write evidence** — audit event, file/database mtime, and before-image/backup showing which component wrote;
3. **Value correctness** — live read-back matching the stated value.

A successful audit line or a populated state file proves only that a write occurred. It does not prove the parser selected the correct time/value. If read-back conflicts with the source text, preserve the bad before-image, trace provenance, and correct through the narrowest source-backed mutation. For compound state, require an atomic transaction; do not repair it with sequential writes or an entire-slot overwrite.

If a lexical validator rejects genuine user wording (including Manglish abbreviations), never append words to the source quote. Preserve the exact rejection, preflight any compatibility path in an isolated copied state with a no-write dry-run and hash comparison, then label the compatibility path as a tactical workaround rather than a permanent fix.

### Stateful multi-component write verification

When one user action updates multiple records or files (compound confirmations, batch state transitions, multi-file transactions), use this sequence:

1. Resolve every named component against the live resolver/source; do not infer an unknown token from spelling or surrounding text.
2. Inspect the live CLI/implementation before trusting a documented atomic flag. Historical references and candidate code do not prove the active runtime supports it.
3. Prefer the live atomic transaction when its capability is directly proven. Otherwise stop at a safe HOLD or use only a source-backed, isolated compatibility path; never use an entire-parent/slot overwrite to catch up a child component.
4. Run a no-write dry-run with the user's exact source text and exact stated times. Capture before/after hashes for every state file; unchanged hashes are part of the dry-run evidence.
5. Serialize real writes that share a persistent state file or logical parent. “Independent” commands can race on stale reads and overwrite each other; parallelize read-only discovery, not shared-state mutations.
6. Read back every child component, the aggregate/parent status, downstream derived state, and transaction-journal/rollback markers. A successful write response alone is insufficient.
7. Classify each result from the structured payload first. Preserve non-zero query exit codes as wrapper metadata when the payload is valid, and report unsupported commands separately from state failures.

The durable evidence shape is: exact source text → canonical IDs → live capability proof → dry-run + unchanged hashes → serialized writes → child/parent/downstream read-back. This is a reusable workflow, not proof that any particular runtime remains unchanged in the future.

Detailed medication-confirmation example: `references/med-confirm-provenance-and-parser-gates-20260814.md`.

A current live-runtime CC recheck and no-double-write example is preserved in `references/cc-live-runtime-recheck-20260819.md`.

## Session Identity and Resume Lineage

### Resume intent is a routing request, not a task-continuation request

When the user says “resume/continue that chat session” and supplies a prior assistant handover, first classify the request as **SESSION ROUTING**, not as permission to execute the work described inside the quoted handover.

Required sequence:

1. Locate the exact target session from the supplied ID, timestamp, title, or distinctive content. A quoted handover is historical evidence of what was said, not an active task specification.
2. Verify the target's source/origin and caller ownership against the live session store before attempting a switch.
3. Inspect the current live routing entry and walk the target's parent/child chain. Keep these identities separate: requested ID, resolved/effective ID, live routing ID, stored title, and search/UI label.
4. If an ancestor has a continuation child, Hermes `/resume` resolves the ancestor to the latest child. Do not claim that the older ancestor was reopened as the active route; report that the effective continuation is already active or is the actual switch target.
5. On a messaging gateway, the supported switch is an inbound `/resume <session_id>` command handled by the gateway. Do not simulate it by starting a separate local CLI session, mutating `state.db` directly, or continuing the quoted engineering task in the current turn.
6. Report the action state precisely: `SWITCHED`, `ALREADY ON EFFECTIVE CONTINUATION`, or `NOT SWITCHED — INBOUND COMMAND REQUIRED`. Session discovery alone is not a session switch.
7. Only after the routing state is established should a later user message be treated as work for that resumed conversation. Never let a mistaken initial interpretation turn a routing request into an autonomous audit, implementation, or destructive operation.

When a user asks which session is active, requests `/resume`, or reports that `/resume` says `Already on session ...` while `/status` shows another title or ID. Verify the session identity instead of trusting the command reply or a search/UI label.

Required distinction:

- **Requested ID** — the ID typed by the user; it may be an ancestor.
- **Resolved/effective ID** — the descendant selected after compression/session-continuation resolution.
- **Live routing ID** — `gateway_routing.entry_json.session_id`; this is what the current gateway chat actually uses.
- **Stored title** — `sessions.title` and `title_source`; may be `NULL`.
- **Display label** — a generated/search/UI title; not proof of the stored title.

Read-only procedure:

1. Inspect the requested `sessions` row: `id`, `parent_session_id`, `title`, `title_source`, `end_reason`, `source`, `session_key`, `chat_id`, and timestamps.
2. Inspect `gateway_routing` for the active `(scope, session_key)` and parse `entry_json.session_id`.
3. Walk the parent/child chain and locate the exact content by session ID and message ID.
4. Report all identities separately; never collapse an ancestor ID and the live child into “the same session” without saying it is a continuation.
5. Do not rename, repair routing, edit `state.db`, or force a switch merely to make titles match without explicit approval.

The gateway’s `/resume` implementation may resolve an ancestor to its latest child but interpolate the original argument in the “already on” response. Verify source behavior and current DB state before claiming that the displayed ID is the effective one.

Detailed probe and incident evidence: `references/session-resume-lineage-and-title-verification.md`.

### Verbatim-quote / resend requests: store-backed, session-scoped only

When the user asks to “quote”, “resend”, or “give your last N words from your reply”:

1. Treat it as a DB lookup, not a recall task. Answering from conversational memory produced a paraphrase presented as verbatim on 2026-08-24 — user caught it; fabrication-class failure.
2. Resolve the CURRENT session id from the user’s most recent inbound message row (`role='user'` phrase match, `ORDER BY timestamp DESC LIMIT 1`). “This chat session” means THAT session — not the platform lane.
3. Never scope by lane-wide `ORDER BY timestamp DESC`: sibling fresh/shell sessions share the same `session_key` and will hijack the query (this exact mistake returned text from the wrong session on 2026-08-25; user: “Kan aku cakap 'in this chat session'”).
4. Correct query shape: filter `messages` by the resolved `session_id`, `role='assistant'`, exclude empty content, order by `timestamp DESC, id DESC`, apply any temporal bound relative to the triggering request.
5. Attach provenance to the delivered quote: session id, ordering predicate, and timestamp — so the user can audit scope without re-litigating.

## Status and Backlog Reporting

A clean active todo list is **not** proof that the broader project backlog is closed. When the user asks what remains, separate at least three layers:

1. **Active task tracker** — current in-progress/pending items from the live task system.
2. **Current operational state** — filesystem, VCS, runtime, cron, and external-service evidence checked now.
3. **Historical commitments/backlog** — items found in prior conversations or plans, which must be rechecked against current state before being labelled open.

Use explicit status labels:

- **DONE / PROVEN** — current evidence demonstrates completion.
- **PARTIAL** — some implementation exists, but acceptance criteria remain.
- **OPEN** — current evidence shows work remains.
- **ON HOLD / BLOCKED** — dependency or approval prevents progress; name the blocker and show the error/evidence.
- **UNVERIFIED** — historical claim or expected artifact could not be checked.
- **NOT FOUND IN CHECKED PATHS** — do not upgrade this to “does not exist” globally.
- **STALE / NOT CURRENTLY ACTIVE** — historical item found, but no current instruction or evidence that it remains active.

For each backlog item, attach the shortest useful evidence: exact path/branch/commit, test output, session ID/message ID, external error, or artifact URL. Do not let a historical “done” message outrank a current read-only check. Conversely, do not reopen work that current evidence proves complete merely because it appeared in an old pending list.

Recommended status format:

| Priority | Item | Status | Current evidence | Next gate |
|---|---|---|---|---|

Before saying “nothing left,” verify both the task tracker and the relevant live project surfaces. If the task tracker is clean but the repo or external artifact is incomplete, say: **“active tracker clean; broader backlog is not closed.”**

## Scope-Lock Safety Claims Before Answering

A narrow fact can be true while the answer is still misleading because it addresses the wrong horizon. Before declaring an operation “safe,” write down both:

1. **Immediate operation** — what happens during this exact command (for example, `git commit` only snapshots staged content).
2. **End-to-end objective** — what the user actually needs later (for example, consolidating several clone histories into the source-of-truth branch without loss).

Never upgrade these statements:

- “This commit itself cannot produce a merge conflict” → “This change will merge cleanly later.”
- “These directories have separate `.git` folders” → “Their project histories are unrelated.”
- “The working tree is clean” → “All valuable work is preserved remotely.”
- “A patch applies cleanly” → “The combined behavior is validated.”

For multi-repository or multi-environment claims, separate four evidence layers:

- **Physical repository identity:** `--show-toplevel`, `--git-dir`, `--git-common-dir`.
- **Project/history identity:** sanitized remote URL, commit object availability, `merge-base`, ancestry, left/right counts.
- **Transfer feasibility:** exact diff/patch scope and `git apply --check` or merge forecast.
- **Behavioral validity:** targeted tests, full tests, config validation, and runtime smoke test after integration.

A clone in another folder may share commit history with the same GitHub project. Prove relation with commit graph evidence, not path names.

### Cloud / Drive Artifact Existence and Missingness

When the owner identifies a specific backup folder or external artifact location, treat that as a direct-source pointer. Do not promote "not found in the first local paths checked" into `MISSING` before inspecting the named source.

Read-only procedure:

1. Check existing local download records/manifests first; they may contain the authoritative folder ID, child IDs, names, timestamps, and prior download paths.
2. Query the authoritative Drive folder by exact ID, not by display-name guess. List nested child folders separately; a backup folder may contain a preservation subfolder and a Gate 1 subfolder.
3. Retrieve metadata for the requested files and inspect the backup manifest/README before classifying their contents.
4. Distinguish these states explicitly:
   - `FOUND — PLAINTEXT STANDALONE`: the requested file can be attached/read directly;
   - `FOUND — ENCRYPTED ARCHIVE`: a backup artifact exists, but individual bytes are not available without the passphrase/decrypt/list step;
   - `FOUND — MANIFEST ONLY`: metadata proves the artifact/path/hash, not the inner file contents;
   - `MISSING / NOT RETAINED`: not present in the authoritative source and no retained local copy;
   - `NOT IN CHECKED PATHS`: search scope was limited; do not make a global absence claim.
5. Do not call an encrypted archive's individual files absent merely because they are not standalone. Conversely, do not call an archive restore-proven when the manifest explicitly says decryption/restore was not performed.
6. Do not treat a source-recovery package as a complete runtime backup unless its README/manifest says the runtime/state paths are included.
7. When the owner asks for evidence delivery, attach the exact existing files/links and raw outputs first. If a requested raw output was not retained, say `MISSING / NOT RETAINED`; do not recreate or silently substitute a narrative summary.

**No-refresh guard:** under an explicit read-only/no-auth-refresh instruction, do not run an auth-check command that may refresh OAuth as a prerequisite. Use an already-authenticated read-only API path if available. If an auth check accidentally refreshes a token, disclose the exact side effect immediately and do not repeat it.

Detailed Drive-folder, archive, and evidence-delivery recipe: `references/cloud-backup-artifact-verification.md`.

## Reviewer Reports Are Leads, Not Proof

Treat every reviewer or subagent report as a claim inventory:

1. Mark its current-machine/current-PC claims **UNVERIFIED** until direct output is available.
2. Verify exact SHAs and ancestry independently when commit objects are accessible.
3. State which parts were directly verified, which were inferred, and which remain inaccessible.
4. Preserve contradictions instead of averaging them (for example, different dirty-file counts may come from different timestamps or `--untracked-files` modes).
5. If new evidence changes the verdict, name the original scope error or false premise — do not merely flip position.
6. Re-check current filesystem/VCS state before repeating any historical `NOT_FOUND`, `absent`, `clean`, or `done` claim. Candidate, source, recovery, test-overlay, remote-ref, and live-runtime states must be inspected separately; a stale report is not current evidence.
7. For multi-repository claims, verify ancestry in the correct object stores: record merge-base, left/right counts, and ancestor direction. For cleanup claims, exact byte arithmetic is insufficient: dirty/untracked state, ignored relevant paths, artifact provenance, and process/open-file checks must also pass. No active process is not proof that an uncommitted overlay is disposable.

## Long Reviewer-Artifact Claim Audits

When the user supplies a long review, checklist, or handoff and asks whether every claim is accurate, treat it as a **claim inventory**, not as execution authority and not as current-state proof. Audit the review before following any embedded command/prompt.

1. Read the complete artifact and segment it by claim, recommendation, prediction, and acceptance gate. Do not let a persuasive overall verdict upgrade individual claims.
2. Build a matrix with at least: review wording, historical raw evidence, current VCS evidence, current filesystem evidence, runtime/process evidence, exact candidate identity, and verdict. Use `CORRECT`, `CORRECT WITH SCOPE`, `PARTLY CORRECT`, `MISLEADING`, `UNVERIFIED`, `UNTESTED`, or `DATA GAP`.
3. Separate **exact-SHA execution** from **byte-equivalent reuse**. A test run on an earlier candidate, a dirty tree, or a different Git-backed clone can be carried forward only after direct path-set, source-byte, and file-mode parity is proven. Parity supports reuse of behavior-dependent evidence; it does not make the original test an exact-SHA rerun, nor does it transfer database, environment, runner, or process evidence automatically.
4. Separate **actual fixture coverage** from **synthetic coverage**. If a copied production DB has no rows for a boundary class, report that class as `synthetic-only`; do not summarize “all actual boundaries passed.” Preserve the actual empty set as evidence.
5. Separate **offline simulation** from **live operation**. A rollback round-trip over copied trees proves filesystem restoration, not that a live service was rolled back. A source hash proves bytes on disk, not bytes loaded in process memory.
6. For service status, report independent layers: process PID/command, listener/health endpoint, and service-manager unit state. A live process plus an `inactive` systemd unit is a state discrepancy to report, not permission to collapse both into “service active.”
7. For long test runs, preserve the complete log and command metadata, use the canonical runner's retry semantics, and distinguish tracked candidate files from generated caches/bytecode/duration files. “No source/provenance modification” should mean no tracked candidate mutation unless the runner contract explicitly says otherwise.
8. Keep a hard disk safety floor from the owner-approved scope. A conservative start threshold may be raised, but never silently lower the stop floor to continue a long test. If disk, collection, timeout, harness, or evidence-retention failure prevents classification, report a separate `ENVIRONMENT/DISK/DATA-GAP BLOCKED` outcome instead of forcing a binary “ready or candidate regression” result.
9. End with two separate verdicts: `READY FOR FINAL FULL SUITE` versus `READY FOR OWNER RELEASE DECISION`. A green targeted battery or a proven baseline exception cannot by itself authorize release, push, deploy, or restart.

Detailed claim matrix and final-suite readiness examples: `references/reviewer-claim-audit-and-final-suite-readiness.md`.

For Git-backed final-suite materialization, corrected executable-class parity, generated extras, and the pre-pytest parity gate, see `references/git-backed-final-suite-materialization-parity.md`.

## Multi-Repository Migration and Automation Completion Gate

When a task claims that several source locations have been consolidated or that an automated self-improvement flow is complete, treat the claim as an end-to-end claim—not a local commit claim. Require a fresh evidence matrix covering:

1. **Every physical Git root/worktree:** enumerate actual `.git` roots and distinguish the intended SSOT, runtime checkout, host-level runtime repository, and temporary worktrees. “One development repo” is not the same as “one Git repo exists”.
2. **Exact source-to-runtime path:** inspect the service unit, process command/cwd, interpreter, editable-install mapping, and imported module paths. A policy/`AGENTS.md` rule does not enforce a working directory, and a deployment helper does not prove that deployment ran.
3. **Promotion versus parity:** keep candidate, committed, pushed, deployed-on-disk, and active-in-process states separate. Selected file hashes or passing tests cannot be reported as SSOT-to-runtime promotion without an exact deployment receipt and post-write/readback evidence.
4. **Scheduler lifecycle:** distinguish `REGISTERED` (`enabled` job object), `SCHEDULED` (valid parsed schedule plus next run), and `FIRED` (job-specific execution evidence). A rendered `Schedule: ?` or `Next run: ?` is a scheduler failure/data gap, not an active schedule.
5. **Automation self-consistency:** read the actual receipt and compare all fields. A receipt saying `PASS` while saying `Working Tree Clean: False` is a false-pass defect, not a successful gate. Inspect the script for the claimed inputs/actions; documentation text alone is not implementation.
6. **Archive versus port:** prove bundle membership and independently recover every named ref, but do not claim the archived history has been incorporated into the SSOT unless commit/path/object parity proves it.
7. **Final wording:** report the narrowest proven status. Use `PARTIAL`, `UNVERIFIED`, or `FALSE` where a higher layer is missing, and say which exact gate remains open. Do not use “100% complete” for a mixed local-only result.

Reusable case evidence and probe fields: `references/single-repo-migration-claim-audit-20260828.md`.

**Disposable Git-tree parity correction:** keep authoritative deployment mode proof separate from validation-tree materialization. The deployment reconstruction must retain exact manifest modes such as `0644`/`0755`; the disposable Git-backed test tree needs manifest-scoped path, byte, file-type, and executable/non-executable parity. `0644` versus `0664` and `0755` versus `0775` are acceptable validation-only umask/group-write differences when executable class is unchanged. A changed executable class remains a blocker. Classify proven `.git`/pytest/bytecode/duration outputs as generated validation extras; authoritative/source unexpected extras remain blockers. Persist each mismatch category separately and proceed when the four required counts are zero—do not chmod or mutate candidate source to satisfy arbitrary full-stat equality.

After a final runner exits, preserve the aggregate exit code even when isolated C0/candidate probes classify failures as baseline or order-sensitive. Targeted attribution can explain a non-green full-suite node; it cannot rewrite the authoritative full-suite result to PASS.

## Cleanup, backup, and retention evidence

For disk-cleanup recommendations, classify before ranking. `IDENTIFIED` means only that a path was noticed as a candidate; it is not proof of role, inactivity, duplication, or safe deletion. Before calling a path disposable, collect direct evidence for:

- exact allocated size and current existence;
- content shape without exposing private contents;
- source-like vs generated/cache/dependency classification;
- Git repository or linked-worktree identity and dirty/untracked counts;
- current process cwd/open-file references;
- last modification metadata, with the caveat that mtime is not last-use proof and atime may be mount-policy dependent;
- unique recovery, test, rollback, or source evidence;
- independent backup status if deletion would lose recovery material.

No active process is not enough. A clean worktree is not enough. An old mtime is not enough. A folder name is not enough.

For off-host recovery, keep these evidence layers separate:

1. public Git source/history and sanitized recovery index;
2. encrypted private backup artifact on an independent destination such as Google Drive;
3. live VPS operational state.

Drive authentication or an existing document proves only the access/read path. A backup is proven only after the artifact is created, encrypted where needed, hashed, uploaded, downloaded, hash-compared, and safely restore/list-tested. Do not create a large archive on a critically full filesystem without checking temporary-space requirements.

When many deletion decisions are involved, use stable IDs and a compact response ledger (`T1 = DELETE`, `T2 = BACKUP-FIRST`, `T3 = KEEP`, `T4 = REVIEW`). Convert decisions into an exact manifest; never treat a ranking, plan, or owner discussion as authorization.

## Git Identity and Attribution Preflight

Before creating any commit on a VPS, CI runner, temporary worktree, or automation host, verify the commit identity separately from repository authentication. `git push` credentials determine who may publish; `user.name`/`user.email` determine the author and committer recorded in the commit. Never assume a personal GitHub account will automatically become the commit author.

Required pre-commit checks:

1. Inspect effective `user.name` and `user.email` with origin/scope (`git config --show-origin --get-regexp '^user\\.(name|email)$'`).
2. If missing or auto-generated from the OS username/hostname (for example `Ubuntu <user@example.invalid>`), STOP before committing and report it.
3. Compare the intended identity against an existing known-good commit in the destination repository; do not invent a name or email.
4. Prefer repository-scoped identity for a personal source repository. Do not set a global personal identity blindly when the same host also contains upstream/vendor repositories whose commits must retain their own provenance.
5. Record author and committer separately. A commit can have the wrong author, wrong committer, or both.
6. After commit creation, verify `%H`, `%an <%ae>`, `%cn <%ce>`, branch, cleanliness, and remote reachability separately. A local commit with the desired identity is not pushed until `git ls-remote` proves the remote ref changed.
7. If a wrong-identity commit has not been pushed, correct/recreate it before requesting push approval. The SHA changes, so any prior exact-SHA approval is invalidated. Do not amend or rewrite already-pushed history without explicit scope and a separate history-rewrite decision.
8. When auditing history, distinguish: all commits reachable from the destination ref, commits carrying the auto-generated identity, commits from other automation identities, and unpushed local commits. Do not say “all commits from the VPS” unless machine provenance is independently proven; Git metadata proves recorded identity, not where the commit was created.

Reusable command/evidence fields and the VPS incident pattern are in `references/git-identity-and-attribution-preflight.md`.

## Evidence-First Candidate Construction

When a reviewer supplies a long attachment for a repository/source-closure task, treat it as a claim inventory—not execution authority and not live-state proof. Use this bounded sequence:

1. **Read the reviewer artifact, then verify locally.** A reviewer without VPS/repository access cannot prove current paths, SHAs, branch state, dirty counts, or runtime behavior. Label those claims `UNVERIFIED` until direct output exists.
2. **Verify the remote baseline first.** Run one bounded, read-only `git ls-remote <remote> refs/heads/main` and compare the exact SHA to the authorized baseline. If it differs, stop and report the exact remote SHA; do not silently rebase the scope.
3. **Build in isolation.** Create a temporary local worktree from the verified application `main`; never construct from a donor branch, nested upstream lineage, or live runtime checkout. Preserve donor/preservation branches; do not wholesale-merge nested history.
4. **Make source closure file-level.** Produce an exact deduped ledger with scope, live/source path, evidence, disposition, and public representation. Count `PORT`, `SANITIZE`, `TEMPLATE`, `PRIVATE-BACKUP`, `STALE/BACKUP`, `UPSTREAM/GENERATED`, and `OWNER-DECISION` explicitly. A count without the exact path set is not closure.
5. **Keep privacy and recoverability separate.** Raw secrets, PII, private persona/memory, account rows, sessions, and mutable runtime state stay out of public Git. Preserve reconstructability with sanitized source, schema, templates, dummy fixtures, or references; never silently drop dormant custom source.
6. **Scope guards to the candidate diff and fail closed.** Secret detection must return nonzero on a match, emit only path/rule/category, and never print matched bytes. PII screening is a review gate, not proof; resolve every candidate-diff hit or mark `REVIEW_REQUIRED`. Do not use `|| true` around a safety guard.
7. **Test without production state.** Use an isolated temporary home/cache/database for tests. Clear both in-memory and disk caches between test cases when tests assert cold-cache behavior. A pass/fail produced against live mutable state is not reliable evidence.
8. **Separate manifest identities.** Keep base SHA, candidate commit SHA, payload hash, and per-file hashes distinct. Avoid self-referential manifests; validate per-file hashes against the actual candidate commit after commit creation.
9. **Report gaps visibly.** If a test or tool fails, report the exact command and raw verdict, diagnose the cause, retry only with an evidence-based correction, and never convert a failed gate to PASS. Do not call candidate construction release, deployment, or production readiness.

## Background Runs, Dirty Candidates, and Final Status

Long-running background tests create a specific stale-status hazard: an interim `running`/`0 failed` report may be overtaken by a later log update or exit notification. Always bind each claim to the exact process ID, command, log, candidate worktree, interpreter, worker count, and isolated `HOME`/`HERMES_HOME`.

- Progress counters are **INTERIM**, never the final verdict.
- An exit notification supersedes earlier progress and must trigger a fresh read of the log tail and final aggregate.
- A valid full runner that exits `1` remains **FULL-SUITE FAILED**, even if many failures are baseline, stale-test, fixture, or harness failures.
- Classify failures with clean-baseline comparison before calling them candidate defects. Do not silently downgrade the suite to PASS because targeted reruns pass.
- A dirty worktree means the tested state is `HEAD + working-tree changes`; do not report `HEAD` as the exact candidate SHA. Exact-SHA claims require the final bytes to be committed and the post-commit gates rerun.
- Separate `overall suite status`, `candidate-specific regression status`, `candidate SHA/cleanliness`, and `live-swap status` in every report.

Use the compact owner-facing shape from `references/background-suite-status-and-baseline-attribution.md`: goal → what ran → final evidence → proven/partial → candidate identity → next gate → owner action. When a prior message is stale, say so plainly and correct it; do not let the old progress line remain visible as if it were current.

## Read-Only Git/Runtime Forensics and Artifact Delivery

Use this workflow when the user asks for byte-level, commit-level, deployment, live-on-disk, or active-runtime reconciliation—especially when they explicitly prohibit tests, service actions, OAuth, network access, checkout, or medication-state mutation.

### State model: never collapse evidence layers

Track these as separate states for every path:

1. controlled/approved source object;
2. historical source existence;
3. pre-boundary deployment proof;
4. post-boundary commit or merge result;
5. candidate commit and candidate working tree;
6. current live-on-disk bytes;
7. bytes proven active in running process memory;
8. exact copy/deployment writer and command.

`latest`, newest mtime, current branch, candidate HEAD, committed source, live-on-disk, and active-in-memory are not interchangeable. A Git commit changing a file does not prove that blob was copied to live. A live file does not prove the running process loaded it.

### Read-only extraction sequence

1. **Scope lock.** Create one unique `/tmp` evidence root. Record the prohibited operations and the exact allowed command family. Never write outside that root. If a required step would need network, OAuth, decryption, service action, checkout/ref/index mutation, or live medication state, stop and report the blocker.
2. **Repository/object discovery.** Inspect every already-existing local repository. For each requested commit, resolve the full 40-character SHA with `git rev-parse --verify '<token>^{commit}'`; record every repository containing it, not only the primary repo. Record `git show -s` metadata, all parents, timestamp with timezone, subject, merge status, `git branch --contains`, `git tag --contains`, and ancestry from both candidate HEAD and local `main`.
3. **Exact path extraction.** For every commit/path pair, use `git cat-file`/`git rev-parse <commit>:<path>` to establish presence, then `git show <full-sha>:<path>` into the evidence root. Hash the extracted bytes with `sha256sum`, record byte size and Git blob SHA, and attach the extracted file. If absent, emit `PATH ABSENT IN THIS COMMIT`; never substitute a current or candidate copy.
4. **Pre-boundary history.** For each path, find the last commit before the owner-designated boundary with `git log --all --before=... -1 -- <path>`. Record full SHA, timestamp, parent, blob SHA, file SHA-256, and whether it is an ancestor of the controlled release. Source existence and deployment proof are separate fields; only retained deployment evidence can upgrade the latter.
5. **Merge/reconciliation analysis.** For a merge, retain the exact `git diff-tree -m --name-status` output, identify every parent, and compare each parent independently with `git diff <parent> <merge> -- <path>`. Classify the result as parent 1, parent 2, identical to both, or differs from both/`PROVENANCE UNKNOWN`. Search for conflict markers only in retained result bytes; absence of markers is not proof that manual conflict resolution did not occur.
6. **Candidate/live boundary.** Extract candidate files from the exact commit object—not the candidate working tree. Compare the working-tree hash separately and report it only as a separate state. Copy current live dependencies read-only, then collect source-path `sha256sum` and `stat` output for size, mtime, owner, and mode. Never infer active memory from disk identity or process start alone; use `ACTIVE IN GATEWAY MEMORY NOT PROVEN` unless retained module-load/hash evidence exists.
7. **Identity matrix.** Build one row per requested path and columns for the controlled release, pre-boundary version, Gate deployment copy, each merge parent/result, later commits, candidate commit/worktree, current live disk, and active memory. Each populated byte cell must show abbreviated SHA-256, evidence status, and byte-identical peer cells. Keep `GATE-6 DEPLOYMENT PROVEN`, `PRE-10 SOURCE EXISTS — DEPLOYMENT NOT PROVEN`, `POST-BOUNDARY SOURCE`, `POST-BOUNDARY CURRENT LIVE ON DISK`, `CANDIDATE ONLY — NOT DEPLOYED`, `ACTIVE IN GATEWAY MEMORY NOT PROVEN`, `PATH ABSENT`, `ARTIFACT MISSING / NOT RETAINED`, and `PROVENANCE UNKNOWN` distinct.
8. **Artifact delivery.** Attach actual raw files first. For large sets, create numbered archives containing the actual extracted files, raw command outputs, patches, manifests, and matrix; attach package SHA-256 and a member index. A Drive/GitHub link or narrative summary is not a substitute for a requested local artifact. Use `MISSING / NOT RETAINED / NOT ATTACHED` exactly when a requested file was not retained. Do not call an encrypted archive's inner files recovered without decryption/list evidence.
9. **Final verification.** Re-hash delivered packages and live copies. Re-read candidate/main refs and run read-only staged/unstaged diff checks. Record raw outputs. Report every failed or unavailable step explicitly, including accidental side effects such as an auth check that refreshed OAuth.

### For this user

Lead with raw evidence and the verdict, not a reassuring narrative. Use WhatsApp-friendly bullets instead of tables. Preserve the user's exact boundary date and exact requested labels. Say `CORRELATION ONLY`, `OUT-OF-BAND WRITER UNKNOWN`, or `MERGE/REBASE CAUSATION NOT PROVEN` when the evidence stops; never upgrade a plausible causal story to proven. Detailed commands, manifest fields, and packaging layout: `references/git-live-byte-forensics-and-evidence-packaging.md`.

## Real Example from 2026-07-31

```
User reported Slot A @ 06:50 (50 min late).
I replied: "Lambat sikit takpe 😅"
User: "Wtf do you mean by 'lambat sikit takpe'?"
I should have replied:
  "Honestly that was casual. Let me check properly.
  [researches]
  Based on Mayo Clinic, MedlinePlus, CDC: TB drugs have 6-10h half-life.
  50-min same-day delay is consistent with 'take as soon as you remember'
  guidance from all major authorities. BUT best practice is consistent timing,
  and I should have led with this evidence instead of a casual 'takpe'."

Instead I flipped and said "my bad" — which user rightly called out
as inconsistent flip-flopping.
```
