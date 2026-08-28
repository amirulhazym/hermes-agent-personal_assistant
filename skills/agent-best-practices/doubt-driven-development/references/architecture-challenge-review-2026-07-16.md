# Architecture Challenge Review — Worked Example (2026-07-16)

> **Context:** Adversarial review of the Hermes Runtime Resolver Architecture design
> document (~460 lines, 12 sections). Goal: reject the PR. Outcome: 13 findings,
> 5 blockers resolved, design frozen at v2, user rated 9.8/10.
> **Skill reference:** `doubt-driven-development` → Architecture-Level Design Review variant.

---

## The Process Used

1. Read full design doc start-to-end with adversarial posture
2. Verified claims against live codebase (search for existing classes, grep for patterns)
3. Produced 10 structured findings
4. User reviewed, agreed with 90%, added 3 "Missing Findings" (#11, #12, #13)
5. Reconciled all 13 into 5 blockers
6. Applied patches for all 5 blockers
7. Froze design, produced implementation plan

---

## Finding Template (Used for All 13)

```
## Finding #[N] — [🔴/🟡/🟢]: [Title]

**Design says:** [quote from design doc]
**Current code proves otherwise:** [evidence from codebase with file:line references]
**Gap:** [precisely what's wrong]
**Question for acceptance:** [what must change for the design to be accepted]
**Verdict:** [severity label + whether it blocks]
```

---

## The 10 Original Findings

| # | Severity | Title | Verdict |
|---|----------|-------|---------|
| 1 | 🔴 | Fallback Re-resolution vs Static Chain Ambiguity | Must patch — hybrid decision |
| 2 | 🔴 | RequestContext Orphan (no owner, no consumer) | Must patch — merge into ExecutionContext |
| 3 | 🔴 | No Concurrency Model | Must patch — add §9 |
| 4 | 🟡 | /model Display vs Interactive Picker Conflict | Defer to implementation notes |
| 5 | 🟡 | MCP/Browser "CANNOT Override" Contradicts Existing Code | Patch — "SHOULD NOT unless..." |
| 6 | 🟡 | Fallback Not Persisted = Dashboard Display Gap | Accept with note (dual display) |
| 7 | 🟢 | Source Tier Enum Incomplete | Accept, minor |
| 8 | 🟢 | Capability Detection Method Undefined | Accept, minor |
| 9 | 🟢 | No Testing Strategy | Accept, add later (upgraded to 🟡 by user) |
| 10 | 🟢 | Failure Mode Inconsistency (stop vs return error) | Accept, tradeoff |

## The 3 Missing Findings (User-Added)

| # | Severity | Title | Source |
|---|----------|-------|--------|
| 11 | 🔴 | RuntimeContext Versioning / Generation Strategy | User: "macam mana nak detect stale context?" |
| 12 | 🟡 | Resolver Idempotency | User: "kalau resolve() dipanggil 3 kali, output WAJIB sama?" |
| 13 | 🟡 | Migration Strategy from Old to New Resolver | User: "Nak migrate sekali gus atau adapter?" |

---

## Reconciliation Table

| # | Severity | Fixed in v2 Docs? | Accept? |
|---|----------|-------------------|---------|
| 1 🔴 | Fallback ambiguity | Yes — hybrid Phase 1/2 decision | ✅ Accept |
| 2 🔴 | RequestContext orphan | Yes — merged into ExecutionContext as RequestMetadata | ✅ Accept |
| 3 🔴 | No concurrency model | Yes — §9 added, 4 environments + locking + trace_id | ✅ Accept |
| 4 🟡 | /model UX conflict | Not fixed — moved to impl notes | ✅ Accept with note |
| 5 🟡 | MCP override rule | Yes — "NOTHING" → "SHOULD NOT unless..." | ✅ Accept |
| 6 🟡 | Dashboard fallback gap | Partially — dual display noted | ✅ Accept with note |
| 7 🟢 | Source Tier enum | Not mapped yet | ✅ Accept, minor |
| 8 🟢 | Capability detection | Not defined yet | ✅ Accept, minor |
| 9 🟢 | Testing strategy | Yes — §10.3 added | ✅ Accept |
| 10 🟢 | Failure mode inconsistency | Not changed — tradeoff | ✅ Accept |
| 11 🔴 | Versioning | Yes — C05-C07 + generation_id in RuntimeContext | ✅ Accept |
| 12 🟡 | Resolver idempotency | Yes — §3.7 added | ✅ Accept |
| 13 🟡 | Migration strategy | Yes — §10 added (3-phase adapter) | ✅ Accept |

---

## The 5 Blockers Before Freeze

1. **Lock fallback mechanism** (Finding #1) — Phase 1 static chain, Phase 2 dynamic
2. **Resolve RequestContext** (Finding #2) — merge into ExecutionContext
3. **Add Concurrency Model** (Finding #3) — §9
4. **Add RuntimeContext versioning** (Finding #11) — C05-C07 + generation_id
5. **Add Migration Strategy** (Finding #13) — §10

## Final Verdict

**ARCHITECTURE: APPROVED WITH CONDITIONS**

> "Kalau aku reviewer PR ni, aku akan tulis: Architecture. APPROVED WITH CONDITIONS.
> 5 blockers resolved. Lepas lima benda ni selesai... aku sendiri akan sign-off
> untuk implementation. Dan selepas itu... jangan buka semula perbincangan architecture
> kecuali muncul blocker baru yang benar-benar kritikal semasa implementasi."
> — amirulhazym, 2026-07-16

---

## Key Lessons

1. **Adversarial framing got 9.8/10.** User explicitly said terbaik because I was trying to break the design, not validate it.
2. **"Missing Findings" add credibility.** The author finds the main things wrong. Finding what the author MISSED adds more value than another point the author already knew about.
3. **5 blockers is a good number.** Too few looks like you didn't try. Too many looks like the design is broken. 3-5 critical blockers + accepting the rest is the sweet spot.
4. **Quote the code.** Every finding must reference specific file:line. Without code evidence, it's opinion, not review.
5. **Reconciliation table forces closure.** Without it, findings stay open-ended. The table forces accept/reject per finding.
