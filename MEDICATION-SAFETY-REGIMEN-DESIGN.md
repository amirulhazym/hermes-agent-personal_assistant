# Hermes Medication Safety & Regimen Management

Status: Design record + candidate implementation handoff
Owner: Amirulhazym
Date: 24 July 2026, MYT
Scope: Hermes personal medication intake logging, reminder interaction, anomaly holds, CC bundle handling, and future regimen changes.

## 1. Executive verdict

The live medication system has repeated a basic safety failure: it can treat a partial/automated state mutation as reliable clinical history, while its resolver does not encode a user-established compound alias.

`CC` is a user-specific compound alias. It always means the two separate medicines Calcium Carbonate plus Calcitriol, taken together. It never means Calcium Carbonate alone, never means the whole Slot C, and never includes Dexamethasone or B-Complex.

Current live state, verified 24 July:
- `med_resolve.py CC` returns UNKNOWN.
- Live resolver has individual Calcium and Calcitriol aliases only.
- `med-schedule.json` describes the CC pair in prose, but that is not executable compound-resolution logic.
- A user message naming both drugs caused Calcium to be auto-recorded before agent review; Calcitriol remained pending. The agent then incorrectly described the same-time Calcium record as a separate earlier intake.

Therefore current live behaviour is not safe enough to deploy as an automatic clinical logging system. Candidate Safety Gate work exists in an isolated workspace only. It is uncommitted, unpushed, and undeployed.

## 2. Stable terminology and non-negotiable rules

### 2.1 Drug identities

- `calcium`: Calcium Carbonate. Individual drug ID.
- `calcitriol`: Calcitriol. Individual drug ID.
- `CC`: compound alias expanding to both `calcium` and `calcitriol`.
- `Slot C`: scheduling grouping. It may include Dexamethasone #2 and, on relevant days, B-Complex. It is not synonymous with CC.

### 2.2 CC contract

1. When Amirul says `CC`, `cc`, or an equivalent established bundle phrase, parse it as both Calcium Carbonate and Calcitriol.
2. Record both component drug IDs at one stated intake time, after normal safety evaluation.
3. Do not interpret CC as Calcium alone.
4. Do not mark an entire Slot C completed only because CC was taken; Dexamethasone #2 and any other required Slot C components remain independently evaluated.
5. The two component drugs remain separately visible in medication status, audit, supply, reminders, and history.
6. A single-component report remains possible only when Amirul explicitly names that component or a clinician/hospital instruction establishes a temporary exception.

### 2.3 CC timing contract

CC is normally taken with lunch. Lunch timing varies. A static C window must not classify a clearly reported CC pair after a late lunch as suspicious solely because it falls outside an old fixed 11:30–12:30 window.

The clinical/scheduling model must represent this as a CC lunch-relative flexible timing rule, not an undocumented agent exception. Timing of CC must not shift Dexamethasone chain calculations. Dexamethasone remains higher priority.

## 3. Evidence ledger

### E-CC-01 — prior discussion was already resolved

Session evidence from 21 July:
- System statement recorded: `CC = Calcium Carbonate + Calcitriol ONLY`.
- It explicitly excluded whole Slot C, C+D, and B-Complex.
- Intended logging behaviour: confirm both component drugs, not slot-level shortcut.

Session evidence from 23 July:
- Amirul said: `both cc aku akan makan lepas lunch`.
- System treated CC as both components pending after lunch.

Session evidence from 24 July:
- Amirul said: `Cc belum lagi` after reporting Dexamethasone #2.
- System correctly described CC in chat as Calcium Carbonate + Calcitriol.

Conclusion: semantic requirement was known in conversation and skill/reference material. It was not represented consistently in live executable resolver code.

### E-CC-02 — live resolver gap

Verified 24 July:

```
python3 ~/.hermes/scripts/med_resolve.py CC --time 13:35
=> UNKNOWN: 'CC'
```

Live `med_resolve.py` has individual aliases for `calcium`, `kalsium`, `calcitriol`, and `vitamin d`; it has no compound alias mapping.

### E-CC-03 — same-event partial write misread as prior dose

Amirul reported both Calcium Carbonate and Calcitriol at 13:35. Before agent review, live state showed Calcium taken at 13:35 and Calcitriol pending. The earlier agent dry-run output therefore reflected a partial write from the same message, not an earlier Calcium event. It was wrongly framed as a potential second Calcium dose.

This proves status projection alone cannot be used as provenance. Agent must inspect source event/audit, raw message, timestamp, and component completeness before asking a correction question.

## 4. Root-cause chain

### F-01: conversational knowledge was not compiled into source of truth

Known CC meaning lived in session/skill prose, but the live resolver only accepts one drug ID. An auto-confirm path cannot safely depend on a model remembering a conversation-specific multi-drug alias.

Required correction: canonical compound alias registry with exact expansion and test coverage.

### F-02: auto-write occurs before semantic complete-pair validation

A message can cause one component to be recorded while its explicitly co-reported companion remains pending. Later logic sees a partial state and wrongly infers separate history.

Required correction: parse all mentions and compound aliases before any medication mutation. One event must either pass complete validation and atomically record all expected components, or create a HOLD with zero med-state/supply mutation.

### F-03: fixed clock window conflicts with lunch-relative CC reality

Current C window reflects old schedule timing, while CC timing depends on lunch. A hard time-window gate would false-HOLD valid late-lunch CC intake.

Required correction: encode formal flexible lunch-relative CC rule. Do not use agent memory or ad-hoc override.

### F-04: agent read status as truth rather than tracing provenance

`med-status.json` is a current projection, not a full medication-event ledger. Without immutable source event and before/after data, a same-time partial write can look like an earlier independent intake.

Required correction: append-only event/audit records, source text or source hash, parsed IDs, action actor, timestamps, decision, and correction linkage.

## 5. Architecture decision

### 5.1 Phase 1 — deterministic Intake Safety Gate

Input flow:

```
inbound message
  -> quoted-history guard
  -> detect clinician/hospital change language
  -> canonical resolver parses every explicit drug and compound alias
  -> active schedule + active taper evaluation
  -> ALLOW or HOLD
  -> only ALLOW invokes med_confirm write path
```

ALLOW requires all of:
- exact parse of every medicine/compound mentioned;
- one valid event type;
- compatible slot/timing policy;
- all expected compound components present for a compound alias;
- no clinician/hospital regimen-change language;
- active schedule and taper data available;
- write target consistent with canonical parser output.

HOLD applies to:
- incomplete or ambiguous parse;
- cross-slot combination not formally approved;
- unexpected pairing or timing;
- CC component mismatch;
- source configuration unavailable/malformed;
- inactive Dexamethasone taper slot;
- clinician/hospital/clinic/ward/discharge/specialist treatment-change language;
- unslotted/PRN medication needing agent handling.

HOLD invariants:
- no `med_confirm.py` subprocess;
- no med-status/supply/schedule/taper/chain-state mutation;
- one structured OPEN hold record;
- append-only safety audit;
- agent receives a trigger to ask a natural clarification.

### 5.2 Structured HOLD record

Every HOLD records:
- unique hold ID;
- raw inbound text and source metadata where available;
- parsed drug mentions and compound expansion;
- stated and evaluation timestamps in MYT;
- risk rule IDs, expected rule, observed fact, and human-readable reason;
- active schedule version/hash;
- active taper phase/hash;
- status OPEN/RESOLVED;
- resolution outcome, note, timestamp, and any linked corrected event.

A hold is not an intake. Resolving a hold cannot itself mutate medication state. Corrected intake requires a new explicit source-backed confirmation event.

### 5.3 Agent conversation after HOLD

Agent must read latest OPEN hold before replying. It asks one natural question at a time and never retries original wording automatically.

Examples:
- Potential typo: `Boss saya nampak Dexa + Pyridoxine 6:08am. Ini betul-betul pills yang diambil, atau tersalah sebut? Saya HOLD dulu supaya log tak salah.`
- CC partial mismatch: `Boss CC means Calcium Carbonate + Calcitriol bersama. Saya nampak hanya one component/ambiguous statement. Dua-dua diambil sekali ya?`
- Late lunch CC: no warning merely due to clock. Confirm only if drug components/source wording are unclear.

### 5.4 Clinician/hospital regimen-change candidate

Doctor, hospital, clinic, ward, discharge, consultant, or specialist instruction is not a normal intake event.

Phase 1 response:
- HOLD and preserve message;
- ask one missing detail at a time;
- do not modify schedule/taper automatically.

Required detail sequence:
1. Source: doctor, hospital, clinic, ward, discharge instruction, or specialist.
2. Exact medicines affected.
3. Old rule to new rule.
4. Dose/form/route.
5. Timing, frequency, minimum gap, relation to food.
6. Effective start date/time.
7. End date, review date, temporary/permanent status.
8. Related medicines added/stopped/substituted.
9. Optional document/photo/screenshot.
10. Evidence label: documented or self-reported, document unavailable.
11. Full impact preview.
12. Final explicit approval.

Lack of document must not block urgent safe handling. It must remain honestly labelled self-reported.

### 5.5 Phase 2 — versioned atomic regimen update

This is not implemented in Phase 1.

Phase 2 requirements:
- immutable regimen versions;
- draft proposal linked to clinician/hospital HOLD;
- validation of schedule, taper, resolver aliases, pairings, reminders, chain rules, supply assumptions, and active day impact;
- before/after diff visible to Amirul;
- explicit final approval;
- atomic switch of active regimen pointer;
- rollback to prior version;
- historical intake records never rewritten;
- change audit records source/evidence/approval text and effective time.

No agent should casually edit `med-schedule.json`, `dexa_taper.json`, resolver logic, and reminders separately in response to one message.

## 6. Candidate implementation status

Candidate workspace:
`/home/ubuntu/hermes-agent-personal_assistant-work`

Candidate branch:
`feat/med-safety-gate-phase1`

Candidate contains:
- deterministic `med_safety_gate.py`;
- structured `med-holds.json` ledger and JSONL audit;
- `med_hold.py` resolution utility that cannot write medication state;
- hook boundary preventing confirmation subprocess on HOLD;
- schedule/taper-based safety evaluation;
- clinician/hospital change report HOLD even without completion words;
- tests for original Dexa + Pyridoxine error, same-slot expected pairs, missing schedule/taper, taper STOP phase, structured hold, no subprocess/state write, clinician report, and unslotted PRN.

Candidate now partially implements CC contract in isolated workspace:
- canonical resolver has `CC -> [calcium, calcitriol]` compound result;
- gate expands CC into both individual component mentions;
- explicit `Calcium Carbonate + Calcitriol` receives same CC bundle semantics;
- late-lunch CC skips static Slot C clock-window rejection;
- CC excludes Dexamethasone, B-Complex, and whole-slot completion.

Candidate still does not yet meet full CC write contract:
- compound write atomicity absent;
- handler still invokes component confirmation writes sequentially after ALLOW;
- candidate source scope includes ported untracked files, so it is not yet clean Git-ready feature history.

Candidate test evidence at 24 July before CC additions:
- Safety/hook suite: 20 passed.
- Standalone chain hook: passed.
- Full repository suite: 40 passed.
- These prove only current candidate tests. They do not prove live deployment or full Phase 2 regimen management.

## 7. CC implementation tasks and acceptance tests

### T-CC-01: canonical compound alias

Implement in canonical resolver data model:

```
cc -> [calcium, calcitriol]
```

Resolver result must return:
- `compound: true`;
- ordered `all_drug_ids: [calcium, calcitriol]`;
- component names and Slot C association;
- no single misleading primary drug result unless explicitly documented as display convenience.

Acceptance:
- `resolve('cc')` produces both IDs;
- `resolve('CC')` produces same result;
- Calcium and Calcitriol explicit names still resolve individually;
- CC never expands to Dexa, B-Complex, or whole Slot C.

### T-CC-02: atomic compound event

For a valid explicit CC confirmation:
- parse CC before write;
- create one source-backed event with both component IDs and same stated time;
- apply both component updates under one lock/transaction strategy;
- if either component cannot be recorded, commit neither and HOLD/error with evidence;
- do not write one component first and infer rest later.

Acceptance:
- `Dah makan CC 1:35pm` records Calcium and Calcitriol at 13:35.
- No intermediate partial state exposed to agent/cron.
- Duplicate replay is idempotent: no second dose/supply decrement.

### T-CC-03: flexible lunch-relative timing

Represent CC timing as lunch-relative/flexible under explicit policy.

Acceptance:
- valid late-lunch statement `CC 1:35pm` does not HOLD solely due to static C clock window;
- CC timing does not shift Dexamethasone #3 chain calculation;
- unclear timing or unexpected component pair still HOLDs;
- old timing rules remain explicit and testable.

### T-CC-04: provenance-first readback

Before asking whether a duplicate dose occurred, system must compare:
- exact source text/event ID;
- stated intake timestamp;
- component IDs;
- write timestamp;
- existing event identity/deduplication key.

Acceptance:
- same message causing partial processing is recognised as same event, not described as `sekali lagi`.
- agent can show source-backed cause of existing status.

### T-CC-05: regression coverage

Required isolated-HOME tests:
- `CC` parses both components.
- Explicit `Calcium Carbonate + Calcitriol` parses same compound event.
- Valid late-lunch CC ALLOW.
- Calcium-only explicit statement remains individual event/hold based on policy.
- Calcitriol-only explicit statement remains individual event/hold based on policy.
- CC does not auto-complete Dexamethasone/B-Complex or whole Slot C.
- Component write failure yields zero component state changes.
- duplicate/retry gives no extra supply decrement.
- concurrent reminder/confirmation cannot observe an inconsistent one-component CC state.

## 8. Git and deployment plan

Current candidate work must be cleaned before commit.

1. Identify exact source files required for Safety Gate plus CC capability.
2. Exclude runtime state, logs, secrets, backups, and copied unrelated sources.
3. Establish clean source baseline from correct branch/repository history.
4. Add focused tests first.
5. Implement T-CC-01 through T-CC-05 in isolated workspace.
6. Run candidate test suite and inspect diff.
7. Ask Amirul explicitly before `git add` and commit.
8. Push/review only after separate approval.
9. Create deployment plan with backup, exact copied files, gateway hook reload/restart requirement, isolated/live read-only verification, and rollback.
10. Ask separately before live deployment.

Git-ready, committed, pushed, deployed, and live-verified are separate states. Never merge wording across them.

## 9. Current open risks

- Live resolver still cannot parse CC.
- Live auto-confirm path may still auto-write before full compound validation.
- Live status file is projection-style history, not proven append-only event ledger.
- Candidate is not live and must not be described as protecting current medication logging.
- Phase 2 regimen update transaction remains a design requirement, not built capability.
- No end-to-end handset delivery receipt proof exists; scheduler success is not WhatsApp receipt.

## 10. Resume instructions for fresh chat

Read this document first. Then verify live filesystem and Git state before stating progress.

Mandatory first checks:

```
python3 ~/.hermes/scripts/med_resolve.py CC --time HH:MM
python3 ~/.hermes/scripts/med_confirm.py --check C
Git status in live and candidate workspaces
Check whether candidate safety files exist in live runtime
Run candidate tests only in isolated HOME/workspace
```

Do not claim CC support until resolver output shows compound result and integration tests prove both components are handled atomically. Do not deploy or commit without Amirul’s explicit approval.

## 11. Change log

24 Jul 2026
- Reconfirmed CC semantic contract from prior sessions.
- Found live executable resolver gap despite prior conversational/skill documentation.
- Identified same-event partial write misread as prior Calcium dose.
- Rebuilt candidate safety gate around schedule/taper source of truth and structured holds.
- Candidate remains isolated and undeployed.
- Added CC-specific implementation requirements to close remaining gap.
