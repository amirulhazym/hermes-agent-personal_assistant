# PX-2 — Problem Intelligence System (PRD)

> **Document type:** Master PRD-like specification (human review / fill-in / handoff)  
> **Status:** DRAFT FOR HUMAN REVIEW — not implemented until explicit go in a PX-2 session  
> **Owner:** amirulhazym  
> **Authoring context:** OpenCode + human Q&A (2026-07-18) from overhaul chat  
> **Name (for now):** **PX** (Problem eXperience / Problem system — final name TBD)  
> **Track code:** **PX-2** = foundational build of the PX system itself  
> **Related:** PX-1 Research = CLOSED · P4 multi-agent OS = ON HOLD · PX-3 = Memory system (later)

---

## 0. How to use this document

| Audience | Use |
|----------|-----|
| **Human (you)** | Review, edit, fill `[FILL-IN]` sections, approve before any build session |
| **New OpenCode session** | Attach this file as **source of truth** for PX-2; do not invent alternate PX-2 goals |
| **Hermes / MJ** | After implementation: read/update knowledge files per rules below (no major system code under freeze) |

**Out of scope for this PRD (do not expand here):** billing, multi-tenant SaaS, paid cloud sync products, full P4 multi-agent OS build, reopening PX-1 acceptance without regression evidence.

---

## 1. Executive summary

### 1.1 Problem

Hermes and the overhaul process keep rediscovering the same classes of issues (wrong assumptions, incomplete renames, slang misreads, tool friction, cost surprises, architecture debates). Chat history is long; MEMORY.md is too small and wrong-shaped for a full problem/solution history. Without a durable, linked, deduplicated knowledge layer, the system (and agents) **repeat mistakes**.

### 1.2 Solution (PX system)

Build **PX** as a long-term **problem intelligence** knowledge layer:

1. **PROBLEMS.md** — registry of all identified problems (stable IDs)  
2. **SOLUTIONS.md** — all solution ideas/attempts, **only** linked to problem IDs  
3. **TRACKER.md** — lifecycle, status, next actions, recurrence, decisions  

These three files are **one ecosystem**, not three orphan docs. They must **actively influence** reasoning (check before propose), not sit as passive documentation.

### 1.3 Why “PX-2” builds the root (reverse order)

| Track | Role |
|-------|------|
| **PX-1** | First *major capability vertical* (Research) — already CLOSED |
| **PX-2** | **Root / body / head of PX itself** — the 3-file system + process + multi-place access |
| **PX-3** | Memory-system issues (compact MEMORY.md vs bulk knowledge) — later |
| **P4** | Multi-agent OS architecture (ON HOLD) — later consumes PX as platform habit / expert support |

**Strategic note:** We deliberately strengthen **PX-2 first** so later experts and sessions have a shared brain for failures and wins.

### 1.4 Success (one sentence)

After PX-2, Hermes + OpenCode + human can **log any issue once**, **trace solutions tried**, **see current status**, and **stop re-proposing failed approaches** unless context truly changed — across devices, with VPS as the primary live write surface for chat-discovered issues.

---

## 2. Goals and non-goals

### 2.1 Goals

| ID | Goal |
|----|------|
| G1 | Establish **canonical 3-file PX ecosystem** with stable IDs and bi-directional links |
| G2 | **Seed** from real history: recent Hermes sessions + known overhaul residuals (broad retrieval, not chat-only) |
| G3 | **Proactive update protocol**: detect → dedupe → write problems/solutions/tracker |
| G4 | **Multi-place availability**: VPS primary for live chat updates; sync path toward local repo + Google Docs (already integrated in Hermes) + Obsidian (no paid cloud extras) |
| G5 | **Influence behavior**: before important planning/debug/architecture answers, agents check TRACKER/PROBLEMS |
| G6 | Capture **patterns / root causes**, not only symptoms |
| G7 | Completeness over premature optimization (files may grow; archive later) |
| G8 | Preserve med runtime safety: knowledge work ≠ silent med code edits |

### 2.2 Non-goals (PX-2)

- Full Personal AI OS / multi-expert mesh (that is **P4**, held)  
- Rebuilding research stack (PX-1 closed)  
- Automatic client billing / invoicing systems  
- Paid third-party cloud storage beyond what Hermes already has (e.g. no new paid sync SaaS)  
- Deleting solution history when architecture changes (mark deprecated instead)  
- Treating “med bugfix sprint” as the definition of PX-2 (med is a **major seed source**, not the product boundary)

### 2.3 Human goals (fill if you want more personal framing)

```
[FILL-IN: Why PX matters to you in one paragraph — e.g. less repeated frustration,
 better consulting delivery, Hermes that learns across months]
```

```
[FILL-IN: Top 3 outcomes you want in 30 days after PX-2 ships]
1.
2.
3.
```

---

## 3. Background and decisions already locked

### 3.1 From overhaul + this PRD’s Q&A

| Topic | Decision |
|-------|----------|
| Name | **PX** (final branding later) |
| ID format (now) | **`P-YYMMDD-###`** global (e.g. `P-260713-001`). P4 may later use more specific IDs — do not over-design yet |
| PX-2 depth | **Full:** scaffold + broad seed + OC/protocol influence (Q1=C) |
| Seed breadth | **Wide:** VPS / hermes-live + recent chat sessions (Q2=C) |
| Canonical live write | **VPS first** (Q3=B) — Hermes can update when problems found on WA/TG |
| Sync priority | **All devices** — VPS + local git repo + GDocs (Hermes-integrated) + Obsidian (wanted, orchestration TBD) |
| Paid cloud | **No** new paid cloud options for PX storage |
| Who detects/creates first | **Native Hermes/MJ > human > OpenCode** by interaction frequency (Q5) — see tension with freeze in §6 |
| Code fixes | **Separate from knowledge write**: fix = own task + human go (Q6≈A); document clearly |
| Session model | Plan/docs here → **new session implements** (Q7=A) |
| Framework/template | **Undecided** — PRD provides candidate templates; human chooses |
| Obsidian | **Wanted**; how it maximizes PX still **open** — decision section §9 |
| P4 | ON HOLD; do not redefine multi-agent OS inside PX-2 execute |
| Wrong brief | Prior agent `CONTINUATION-BRIEF-PX2.md` with A–F goals was **wrong and removed** |

### 3.2 Freeze vs native updates (important)

| Actor | System code / med / gateway | PX knowledge files |
|-------|------------------------------|--------------------|
| **Hermes/MJ** | **Freeze:** no major system change, no overhaul execution | **Preferred first writer** for chat-discovered problems (append/update PX files) |
| **Human** | Approves major changes | Can request logs, edit PRD, approve fixes |
| **OpenCode** | Full executor for overhaul/code with human go | Seeds bulk history, scaffolds, sync tooling, protocol wiring |

If freeze and “MJ writes PX first” conflict in practice, **human resolves** (see open decision OD-1). Default intent: MJ may update **PX knowledge only**, not med/gateway code.

---

## 4. Product definition

### 4.1 What PX is

A **cross-domain problem intelligence layer** for Hermes + human + OpenCode:

- Any issue type: technical, UX, reasoning, cost, workflow, architecture, communication, security, hallucination, repeated debate, etc.  
- Keyword-dense entries preferred over essay reports  
- Stable identity per problem  
- Full solution history (including failures and rejections)  
- Lifecycle truth in TRACKER  

### 4.2 What PX-2 delivers

| Layer | Deliverable |
|-------|-------------|
| **Root** | Schemas + templates + ID rules + dedupe rules |
| **Body** | Seeded PROBLEMS / SOLUTIONS / TRACKER from real sessions |
| **Head** | Access paths (VPS primary) + sync plan + “check before propose” protocol |
| **Not yet full brain** | Perfect Obsidian orchestration, perfect GDocs sync, auto-archive — may be phased |

### 4.3 Relationship diagram

```
User (WA/TG/PC)
    │
    ▼
Hermes/MJ ──detect friction──► VPS px-knowledge/ (PRIMARY LIVE)
    │                              │
    │                              ├─ PROBLEMS.md
    │                              ├─ SOLUTIONS.md
    │                              └─ TRACKER.md
    │                              │
OpenCode ──scaffold/seed/sync──┘   │
    │                              ▼
    │                    Sync targets (policy TBD)
    │                    ├─ Local git repo (MJay)
    │                    ├─ Google Docs (Hermes-integrated)
    │                    └─ Obsidian vault (no paid cloud)
    ▼
Before propose fix/plan ── READ TRACKER + PROBLEMS (mandatory protocol)
```

---

## 5. The three files (ecosystem rules)

### 5.1 PROBLEMS.md — source of truth for “what is wrong”

**Must include per entry (minimum):**

| Field | Description |
|-------|-------------|
| `id` | `P-YYMMDD-###` |
| `title` | Short keyword title |
| `type` | e.g. clinical-ux, reasoning, tooling, cost, architecture, workflow, security, memory, other |
| `status_hint` | open / investigating / mitigated / solved / recurring / wontfix (mirror TRACKER) |
| `summary_keywords` | Dense keywords, not essay |
| `symptoms` | What was observed |
| `impact` | Why it matters |
| `evidence` | Chat date, file path, command — no secrets |
| `related_problems` | Parent/child/duplicate-of IDs |
| `confidence` | high / medium / low (same vs new problem) |
| `first_seen` / `last_seen` | Dates |
| `recurrence_count` | Integer |
| `domain_tags` | e.g. med, research, gateway, overhaul, px, consulting |

**Rules:**

- No duplicate problems → search before create  
- Symptom of larger issue → link parent, don’t only spawn orphans  
- Low confidence “maybe same” → record confidence, don’t force merge  

### 5.2 SOLUTIONS.md — only exists because of problems

**Must include per entry:**

| Field | Description |
|-------|-------------|
| `id` | `S-YYMMDD-###` or `S-<problemId>-a/b/c` |
| `problem_id` | **Required** link to `P-...` |
| `title` | Short |
| `state` | proposal / accepted / in_progress / tested_ok / tested_fail / partial / rejected / deprecated |
| `summary` | Keywords + short how |
| `result` | What happened when tried |
| `reject_reason` | If rejected |
| `deprecated_reason` | If architecture moved on |
| `do_not_retry_unless` | Condition to allow retry after N failures |

**Rules:**

- No orphan solutions  
- Keep failed/rejected history  
- If same solution failed ≥3 times → do not re-propose without new context  

### 5.3 TRACKER.md — lifecycle (most important operationally)

**Must include per problem row/section:**

| Field | Description |
|-------|-------------|
| `problem_id` | Link |
| `status` | open / investigating / waiting_human / waiting_external / in_progress / solved / recurring / blocked |
| `active_solution_id` | Current approach or none |
| `failed_solution_ids` | List |
| `actions_log` | Dated actions (append-only) |
| `decisions` | Last human/agent decisions |
| `next_action` | Concrete next step |
| `blockers` | |
| `owner` | hermes / human / opencode / shared |
| `wrong_assumptions` | Proven false beliefs |
| `do_not_repeat` | Anti-patterns |

**Rules:**

- Status change on problem/solution → update TRACKER same change set  
- Before proposing new work on a recurring issue → **read TRACKER first**  

### 5.4 Entry templates (copy-paste)

#### Problem template

```markdown
### P-YYMMDD-### — <short title>
- type:
- status_hint:
- summary_keywords: []
- symptoms:
- impact:
- evidence:
- related_problems: []
- confidence: high|medium|low
- first_seen:
- last_seen:
- recurrence_count: 1
- domain_tags: []
```

#### Solution template

```markdown
### S-YYMMDD-### — <short title>
- problem_id: P-YYMMDD-###
- state: proposal|accepted|in_progress|tested_ok|tested_fail|partial|rejected|deprecated
- summary:
- result:
- reject_reason:
- deprecated_reason:
- do_not_retry_unless:
```

#### Tracker template

```markdown
### T — P-YYMMDD-###
- status:
- active_solution_id:
- failed_solution_ids: []
- owner: hermes|human|opencode|shared
- next_action:
- blockers:
- wrong_assumptions: []
- do_not_repeat: []
- actions_log:
  - YYYY-MM-DD: 
- decisions:
  - YYYY-MM-DD: 
```

### 5.5 Framework / template choice — HUMAN UNDECIDED

You want a good framework but are undecided (GDocs + local + effectiveness).

**Candidates (pick one or hybrid later):**

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **F1 Markdown triple** | Three `.md` files as specified | Simple, git-friendly, agent-readable | Can get long |
| **F2 Single index + shards** | `INDEX.md` + `problems/P-….md` | Scales | More files |
| **F3 Table-first TRACKER** | TRACKER as markdown table hub | Fast scan | Wide tables hard on phone |
| **F4 GDoc master + md mirror** | Human edits GDoc; agent mirrors md | Familiar UI | Sync conflict risk |
| **F5 Obsidian vault pack** | PX folder with wikilinks | Graph + local | Orchestration TBD |

```
[FILL-IN: Chosen framework now — F1 / F2 / F3 / F4 / F5 / hybrid: ________]
[FILL-IN: Why:]
[FILL-IN: Revisit date:]
```

**Default for first implementation if you leave blank:** **F1** on VPS + git mirror, GDoc/Obsidian as Phase B sync targets.

---

## 6. Roles and permissions

| Actor | Detect problems | Write PX files | Change Hermes code/config | Push git |
|-------|-----------------|----------------|---------------------------|----------|
| Hermes/MJ | **Primary** (most chat time) | **Yes** (knowledge only; preferred first) | **No** major (freeze) | No |
| Human | High | Yes (or request) | Approve | Approve push |
| OpenCode | Bulk seed, audit, tooling | Yes (scaffold/seed/sync) | Yes with go | Only on “go push” |

**Priority for “who should catch issues first”:**  
`Hermes/MJ > Human > OpenCode` (by time-on-system).

**Priority for “who executes overhaul/code”:**  
`OpenCode > Human approval > MJ never major`.

---

## 7. Multi-place sync strategy

### 7.1 Priority order (intent)

1. **VPS** `~/.hermes/px-knowledge/` — **primary live** (WA/TG → Hermes update)  
2. **Local git repo** `MJay/px-knowledge/` — versioned backup / OC handoff  
3. **Google Docs** — Hermes already integrated; human-friendly review  
4. **Obsidian** — long-term personal knowledge graph (no paid cloud add-ons)

### 7.2 Sync principles

- One **write-primary** at a time for live chat updates = **VPS**  
- Other locations = **mirrors** with clear “last synced” stamp  
- Never sync secrets, `.env`, WhatsApp session, raw med PII dumps into public git  
- Conflict rule: `[FILL-IN: if VPS and GDoc diverge, winner is: ________]`  
  **Suggested default:** VPS wins for machine-written entries; human edit on GDoc wins until next pull with merge note

### 7.3 GDocs (undecided effectiveness)

```
[FILL-IN: Do you want one GDoc per file (3 docs) or one GDoc with 3 sections?]
[FILL-IN: Hermes skill/tool already used for GDocs — name if known:]
[FILL-IN: Sync frequency: on every PX write / daily / manual only]
```

### 7.4 Obsidian — wanted but orchestration undecided

**Why Obsidian can help PX (explanation for decision):**

| Benefit | How it helps your goal |
|---------|------------------------|
| Local, no new paid cloud | Fits constraint |
| Wikilinks / graph | See clusters of related problems |
| Long-term personal SSOT | Survives agent session loss |
| Separates bulk knowledge from MEMORY.md | MEMORY stays small prefs; PX/Obsidian holds history |
| Mobile vault apps (your choice) | Read problems offline |

**What Obsidian is *not* automatically:**

- A replacement for TRACKER discipline  
- Auto-fix of bugs  
- Free multi-agent chat  

**Orchestration options (choose later):**

| Option | Description |
|--------|-------------|
| O1 | Vault folder `PX/` mirrors the 3 md files only |
| O2 | One note per Problem ID + MOC index |
| O3 | PX md on VPS; Obsidian sync via your existing vault sync tool (Syncthing/etc., not paid SaaS) |
| O4 | Defer Obsidian until after VPS+git+GDoc stable |

```
[FILL-IN: Obsidian choice for PX-2 v1 — O1/O2/O3/O4 / other:]
[FILL-IN: Vault path if known:]
[FILL-IN: What “maximizing Obsidian for PX” means to you in one sentence:]
```

---

## 8. Seeding strategy (Q2=C)

### 8.1 Sources (in priority for first bulk seed)

1. Recent Hermes chat sessions on VPS (last several days — configurable)  
2. Overhaul-known residuals (examples below — not exhaustive)  
3. This chat’s 13/7 clinical/UX day (as multi-domain examples)  
4. PX-1 closeout residuals **as problems only** (do not reopen PX-1 acceptance)  
5. Human-added items anytime  

### 8.2 Example seed candidates (illustrative — implement session will validate live)

| Example ID | Title keywords | Domain |
|------------|----------------|--------|
| P-260713-001 | reminder-copy still Akurit-4 in chain_calc/med_report | med, clinical-ux |
| P-260713-002 | empty-stomach rule misapplied (2h after drug) | med, reasoning |
| P-260713-003 | GG slang over-medicalized | communication, reasoning |
| P-260713-004 | aggressive 15m nag vs off-day | product, ux |
| P-260713-005 | Malay alias dexa siang weak | med, tooling |
| P-260713-006 | multi-drug slot partial confirm UX | med, ux |
| P-260713-007 | confirm time wall-clock vs user stated | med, data |
| P-260713-008 | tool approval / VS false positive friction | tooling |
| P-260713-009 | phone cannot open json export dance | ux |
| P-260713-010 | chain shift education (late A → noon≠C) | med, ux |
| P-260713-011 | paid model switch mid-day cost | cost |
| P-260713-012 | MEMORY headroom creep after trim | memory → also PX-3 |
| … | (from VPS session search) | … |

### 8.3 Dedup algorithm (mandatory)

```
on_detect(issue):
  1. keyword + semantic scan PROBLEMS.md (and TRACKER open/recurring)
  2. if match confidence high → update last_seen, recurrence_count, evidence
  3. if match medium → note possible_duplicate_of + confidence
  4. if new → allocate next P-YYMMDD-### , create problem + tracker stub
  5. never create solution without problem_id
  6. if pattern repeats across domains → create/link pattern parent problem
```

---

## 9. Behavior protocol — “influence reasoning”

### 9.1 When agents MUST read PX first

Before:

- Proposing architecture or multi-step plans  
- Proposing a fix for a recurring class of bug  
- Claiming “never seen this”  
- Recommending a solution that sounds familiar  

### 9.2 Minimum checklist

1. Search TRACKER for open/recurring related IDs  
2. Read PROBLEM entry  
3. Read linked SOLUTIONS — skip deprecated/failed×3 unless new context  
4. Propose with explicit `problem_id` reference  
5. After attempt → append actions_log + update solution state  

### 9.3 Code / system fixes (Q6)

| Step | Who |
|------|-----|
| Log problem + solution proposal | Hermes and/or OC |
| Status `waiting_human` if fix needs code | TRACKER |
| Human `go fix P-…` | Human |
| OpenCode implements fix | OC |
| Verify + mark solution tested_ok / problem solved | OC + evidence |
| If rejected | keep solution with reject_reason |

**PX-2 does not mean silent production fixes.** Knowledge first; execution gated.

---

## 10. Phased implementation plan (for next PX-2 session)

> Execute only after human says go on this PRD (possibly after edits).

### Fasa 0 — Scaffold (VPS primary)

- [ ] Create `~/hermes-overhaul-backup/pre-px2/`  
- [ ] Create `~/.hermes/px-knowledge/{PROBLEMS,SOLUTIONS,TRACKER}.md` with headers + templates  
- [ ] README in folder: rules + ID format + “read before propose”  
- [ ] Ensure `.gitignore` does not block px-knowledge; does block secrets  
- [ ] Smoke: files readable; gateway unaffected  

**Gate:** human confirms schema OK.

### Fasa 1 — Broad seed

- [ ] Search recent Hermes sessions (last N days — `[FILL-IN: N=____ default 7]`)  
- [ ] Extract issues → dedupe → write PROBLEMS/SOLUTIONS/TRACKER  
- [ ] Include illustrative overhaul residuals after live confirm  
- [ ] Produce seed report: counts by type, top recurring  

**Gate:** human spot-checks 5–10 entries.

### Fasa 2 — Local git mirror

- [ ] Mirror `px-knowledge/` into `MJay/px-knowledge/`  
- [ ] Commit on `overhaul/exec` (no push unless go)  

### Fasa 3 — Protocol wiring

- [ ] Document protocol in skill or `px-knowledge/PROTOCOL.md`  
- [ ] Optional: skill-trigger / SOUL one-liner for MJ: update PX on friction  
- [ ] OC session brief: mandatory PX check  

**Gate:** dry-run “propose fix” cites a P-ID.

### Fasa 4 — Sync targets (as decided)

- [ ] GDocs mirror procedure `[FILL-IN]`  
- [ ] Obsidian procedure if O1–O3 chosen  
- [ ] Write `LAST_SYNC.md` stamps  

### Fasa 5 — Validation

- [ ] No med_* accidental edits  
- [ ] Gateway healthy  
- [ ] ID consistency check script (simple)  
- [ ] Human accepts PX-2 v1  

---

## 11. Success metrics

| Metric | Target (v1) |
|--------|-------------|
| Three files exist on VPS | Yes |
| Seeded problems | ≥ `[FILL-IN: e.g. 15]` from real sources |
| Every solution has problem_id | 100% |
| Tracker covers every problem | 100% |
| Duplicate rate on spot-check | Low (human judgment) |
| Agent cites P-ID when proposing related fix | Observed in dry-run |
| Med regression | No intentional med edits; if any shared surface touched, 21 tests still green |
| Sync | At least VPS + local git; GDoc/Obsidian per fill-in |

---

## 12. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Files become huge | Accept for v1; later archive/index (not now) |
| Duplicate noise from MJ+OC | Dedupe protocol; confidence field |
| Freeze vs MJ writes | Knowledge-only path; no code |
| PII in session extracts | Redact names/ids; no raw med dumps in git |
| GDoc sync fights VPS | Single write-primary; LAST_SYNC |
| Scope creep into P4/OS | Explicit non-goals |
| Scope creep into endless fixes | Q6: fixes gated |
| Wrong agent invents PX-2 again | This PRD is canonical; no A–F substitute |

---

## 13. Open decisions (human fill-in)

| ID | Decision | Your answer |
|----|----------|-------------|
| OD-1 | If MJ freeze blocks PX file writes, exception? | `[FILL-IN: yes knowledge-only / no / other]` |
| OD-2 | Framework F1–F5 | `[FILL-IN]` |
| OD-3 | GDoc shape + sync frequency | `[FILL-IN]` |
| OD-4 | Obsidian O1–O4 | `[FILL-IN]` |
| OD-5 | Session search window N days | `[FILL-IN: default 7]` |
| OD-6 | Minimum seed count | `[FILL-IN: default 15]` |
| OD-7 | Conflict winner VPS vs GDoc | `[FILL-IN]` |
| OD-8 | Final product name beyond “PX” | `[FILL-IN: later OK]` |

---

## 14. Acceptance checklist (human signs off)

- [ ] I understand PX-2 is the **PX system foundation**, not med-only and not full P4  
- [ ] I accept VPS as primary live write for chat-discovered problems  
- [ ] I accept code fixes remain **gated** separate tasks  
- [ ] I filled or deferred OD-1…OD-8  
- [ ] I approve this PRD for a **new session to implement Fasa 0+** (or request edits first)  

**Signature / date:**

```
[FILL-IN: name]
[FILL-IN: date]
[FILL-IN: APPROVED FOR IMPLEMENTATION / NEEDS REVISION]
```

---

## 15. Handoff pack for new PX-2 session

Attach at minimum:

1. **This file:** `PX2-PROBLEM-INTELLIGENCE-PRD.md`  
2. `OVERHAUL-EXECUTION-PROMPT.md`  
3. `CONTINUATION-BRIEF-P4.md` (ON HOLD context only)  
4. `docs/superpowers/specs/2026-07-11-phase4-os-vision-HOLD.md` (OS north star only)  
5. Optional: `docs/superpowers/specs/2026-07-18-px1-family-closeout-handoff.md` (do not invent PX-2 from it)  
6. Optional: `probsolimp.txt` if still in workspace (origin idea of 3 files)

**Starter prompt (after you approve PRD):**

```
Execute PX-2 per PX2-PROBLEM-INTELLIGENCE-PRD.md only.
Do not redefine PX-2. Do not use removed A–F brief.
Start Fasa 0 scaffold on VPS px-knowledge/, then stop for gate.
No med_* edits. No push unless I say go push.
```

---

## 16. Document control

| Version | Date | Notes |
|---------|------|-------|
| 0.1 | 2026-07-18 | Initial PRD from human Q&A (Q1=C, Q2=C, Q3=B, Q4=undecided/Obsidian wanted, Q5=MJ>human>OC, Q6=A gated fixes, Q7=A + this PRD) |

---

*End of PX2-PROBLEM-INTELLIGENCE-PRD.md — review and fill [FILL-IN] before implementation session.*
