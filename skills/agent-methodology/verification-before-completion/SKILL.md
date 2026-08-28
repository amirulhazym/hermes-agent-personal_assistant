---
name: verification-before-completion
description: Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always. ALSO use before any destructive system operation (npm clean, rm -rf, config overwrite, service changes) — run the pre-change safety protocol to verify nothing breaks.
---

# Verification Before Completion

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

## Candidate Runner and Environment Boundary

A test command can exit before collecting any tests because the canonical wrapper selects its interpreter from `HOME`, `VIRTUAL_ENV`, or an explicit runner variable. Treat that as **HARNESS-INVALID**, never as PASS or a candidate failure. When using an isolated HOME, explicitly provide the already-verified pytest-capable interpreter (for this runner family, `HERMES_PYTHON`) or create the expected isolated venv path, then rerun the same canonical command. Record the invalid attempt separately.

Keep these evidence layers separate:

- affected-file/targeted tests;
- canonical full-suite result;
- compile/format/marker checks;
- candidate identity and cleanliness;
- live-runtime status.

A passing bounded suite cannot close a full-suite gate. Any candidate byte change—including a test merge fix or lifecycle fix—invalidates earlier candidate test evidence; rerun the affected suite and regenerate the final exact SHA before asking for a live-swap/deployment approval. See `references/candidate-full-suite-resume.md` for the reusable sequence.

If you haven't run the verification command in this message, you cannot claim it passes.

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = lying, not verifying
```

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified | Test passes once |
| Agent completed | VCS diff shows changes | Agent reports "success" |
| Requirements met | Line-by-line checklist | Tests passing |
| Audit finding (code-read) | Live system output confirms hypothesis | Code-path reasoning, "looks wrong from reading" |

## Red Flags - STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!", etc.)
- About to commit/push/PR without verification
- Trusting agent success reports
- Relying on partial verification
- Thinking "just this once"
- Tired and wanting work over
- **ANY wording implying success without having run verification**
- Asking the user to make a choice before finishing your own audit/investigation — the choice options you offer should be the result of complete work, not a prompt to abandon the audit halfway

## Pitfall: Don't Pad Options With Insufficient Choices

**When you know the real answer, recommend it directly. Do not offer weaker alternatives as if they are equally valid choices — the user WILL call this out and it erodes trust immediately.**

Anti-pattern from this session:

```
Agent: Options for B1:
  B1a = easy prompt update (catches math errors)
  B1b = prompt + skill attach (guarantees verification methodology)
  B1c = full rewrite

User: "So why provide me B1a then? Kau suka provide easy solution
       yang menjadi punca kepada repetitive problems right?"
```

**Root cause:** I knew B1a was insufficient — the same failure that produced "18 findings" (agent hallucinating its own math) can also hallucinate a "verify your math" instruction as "done." But I offered it anyway, as padding, because it was "technically an option."

**Rules:**

1. **Audit your own recommendation stack before presenting.** If you're about to offer 3 options, ask: "Does option 1 actually solve the problem? Or do I just want fewer options to look more helpful?" If the weakest option won't fix the root cause, DON'T present it.

2. **Use options for genuine trade-offs** (cost vs. effort vs. risk), not for "easy vs. medium vs. hard" where only the hardest actually works. Presenting a fix that you know is insufficient as a "valid choice" is the same failure class as presenting unverified data as fact — you're putting the user in a position to pick the wrong answer.

3. **Default to recommendation, not menu.** State your recommendation first, then (if relevant) note alternatives with their specific limitation. NOT a flat list of N options with "my recommendation: N." The structure of your output should lead the user to the right choice, not ask them to navigate bad options.

4. **When the user catches a padded option, do not repeat the pattern.** You will lose credibility. Each padded option you've been caught on is a data point that your options are not trustworthy.

**Test:** If removing the weakest option from your list would still let the user make an informed decision behind your recommendation, the weakest option was padding. Remove it.

A 60-second `python3 -c "print(function())"` beats a retracted claim every time.

---

## Pitfall: One-at-a-Time — Show Evidence Between Tasks, Don't Rush

When the user explicitly asks for one-by-one task execution ("selesai satu, then repeat"), each task requires a verification loop before moving to the next. This is enforced by the user — he WILL question premature "selesai" claims. Do not test whether he's paying attention; assume he is.

```
Task N:
  ┌─ Present options with recommendation ─┬─ User approves ─┬─ Execute ─┬─ SHOW EVIDENCE ─┬─ Ask confirmation ─→ Task N+1
```

**The failure (this session):**

```
Task B1b: Prompt updated, skill attached → "✅ B1b selesai"
→ Immediately: "Task C: Daily Health memory escalation"
User: "Waittt, b1b really selesai?? B dah selesai? Lajunya kau execute???"
```

**Root cause:** I had the evidence (`hermes cron list` verified the update + skill content loaded and valid) but I did not SHOW it before claiming completion. I treated verification as "I checked = done" rather than "I checked AND showed the user the proof = done."

**Protocol for one-at-a-time execution:**

After each task execution, **before** moving to the next:

1. **Run the verification command** — fresh, not assumed
2. **Show the evidence in your response** — raw output, not a summary. Let the user read it.
3. **State the conclusion** — "This is done because: [evidence]. This is not yet proven because: [gap]."
4. **Ask for confirmation** — "Proceed to next task?" Do NOT default to "and now Task C..."
5. **Wait** — if the user doesn't respond to the ask in the same message, the topic is waiting. Do not proceed unprompted.

**The anti-pattern to avoid:**

```
"✅ Task X selesai. Sekarang untuk Task Y..."  ← WRONG
```

The right pattern:

```
"Task X done. Verification:
  [hermes cron list output showing the update]
  [file content proving the change]

This handles [problem 1] and [problem 2]. The part I cannot verify until next run is [limitation].

Proceed to Task Y?"
```

**Why this matters:** Moving to the next task without the user confirming the current one is the same pattern that caused the "autonomous approval" failure (Pitfall: User Correction ≠ Implicit Approval). The user's instruction "one-by-one" was explicit — breaking that sequence is a trust violation, not a workflow shortcut.

---

## Provider-Boundary Verification

For scheduled jobs that call an external provider, a green unit suite and a manually successful component call do not prove end-to-end recovery. Verify each boundary separately:

1. Resolve the active provider, model, API-key mapping, and base URL from the live config.
2. Construct and print the exact request URL. Normalize OpenAI-compatible base URLs so `/v1` is neither omitted nor duplicated.
3. Call the live provider with the actual configured model and capture HTTP status plus response shape.
4. Execute the real scheduler path, not merely a command that accepts a run request. Confirm fresh `last_run_at`, run status, stdout/stderr, state-accounting change, and delivery log.
5. Report component success and delivery success separately. If a scheduler trigger is accepted but no fresh execution evidence appears, label delivery UNVERIFIED.

A provider adapter migration must include a regression test for both an origin base (`https://host`) and an already-versioned base (`https://host/v1`). Provider-to-credential mappings are part of the runtime contract and require direct tests.

### Scheduler command acceptance is not execution

A tool response such as `success: true` or `run accepted` proves only that the request was accepted. It does not prove the job ran, generated output, changed state, or delivered a message. Require fresh scheduler metadata and destination-side/log evidence before saying “delivered.”

## Verify With The Actual System, Not With Yourself

When the user asks "fix this", "investigate this", "plan how to do X" — the deliverable is a **complete** answer, not a partial analysis followed by a multiple-choice question.

Anti-pattern:
1. Start investigating
2. Hit a branch point
3. Stop and present options to the user
4. User has to ask "wait, you didn't finish the audit"
5. Wasted time + tokens + user frustration

Correct pattern:
1. Investigate completely — read everything relevant, list all options, identify all concerns
2. THEN present findings + recommendation + ask
3. User makes an informed decision in one round

This is "evidence before claims" applied to planning and analysis, not just code execution. **The user should never have to tell you "kau tak habiskan pun, ada apa² concern ke sebelum execute?" because you should have already finished the audit by the time you asked.**

## Pitfall: Partial ≠ Done (Multi-Component State)

**NEVER round up sub-task completion to parent-task completion.**

When the thing you're tracking has sub-components (drugs in a med slot, steps in a pipeline, items in a checklist, files in a PR), the state representation **must match the domain's actual granularity**:

| Claim | Reality | Verdict |
|-------|---------|---------|
| "Slot B confirmed" | 2 drugs in B, only 1 taken | **False** — B is *partial* |
| "Milestone complete" | 3/5 tasks done | **False** — milestone is *in progress* |
| "PR ready to merge" | 2/3 approvals | **False** — needs 1 more review |
| "All tests pass" | 34/35 pass | **False** — 1 failing |

**The bad pattern:**
```
Binary parent state ← ignores children's intermediate states
→ You see ✅, stop tracking, miss the pending sub-component
```

**The fix (from this session's system upgrade):**
```
3-tier state: pending → partial (◐) → completed (✅)
Parent is completed ONLY when every child is accounted for.
Partial still triggers follow-up/additional reminders.
```

**How to apply in your own work:**

1. **Ask**: "Does this thing have sub-components or sub-states?"
2. **If yes**: check EVERY sub-component before claiming parent completion
3. **If any sub-component is unresolved**: the parent is PARTIAL, not done
4. **Display partial states explicitly** (◐, ⏳, numbers) so the user sees what's pending
5. **Never auto-silence follow-up** when state is partial — persist reminders until fully resolved

This is the same principle as the epistemic core: "Default to downgrading, not upgrading, your own confidence." And "Distinguish theory from proven." A partial claim is not a complete claim, and presenting it as one means you skipped the verification step.

**Real example from this session:**
- Med slot B had `dexamethasone_1` + `levetiracetam_b`
- User took Dexa and said so → only Dexa marked ✅
- Old system: `B ✅` (wrong — rounded up from 1/2)
- New system: `B ◐` (correct — partial, still pending Levetiracetam)
- Reminders kept firing until Levetiracetam was also confirmed
- Only then: `B ✅` (honest completion claim)

**Remember:** Binary state at the parent level is wrong when children have intermediate states. Always decompose to match reality.

## Pitfall: Tool Output Redaction/Truncation Can Fabricate False Defects

Terminal/write_file/read_file output REDACTS secret-like strings (`TOKEN=...`, `KEY=...`). The redacted form can look like a corrupted/truncated value in the artifact you are auditing. Seeing `MCP_TOKEN=genera...` or `SECRET_KEY=***` in tool output does NOT mean the file contains that text.

Real near-miss (2026-08-01): auditing a delivered PRD, terminal grep showed `MCP_TOKEN=genera...-run` and `LANGFUSE_SECRET_KEY=***` in doc.md + ops.json — looked like truncated placeholders that slipped past a "no-placeholder" gate, and I nearly reported the doc as defective. Chunked repr proved the actual content was the full valid placeholder (`generate-a-random-token-before-run`, `change-me`). The `...`/`***` were terminal-side redaction of secret-like values, not file content.

Rules:

1. **When the value being verified is secret-like** (token, key, password, placeholder), do NOT trust grep/display output for that line. Print with length + chunked repr instead:
   ```python
   python3 - <<'PY'
   def chunks(s, n=20): return ' | '.join(s[i:i+n] for i in range(0, len(s), n))
   for ln in open('file').read().split('\n'):
       if 'TOKEN' in ln or 'KEY' in ln:
           print(f'len={len(ln)} {chunks(ln)}')
   PY
   ```
2. **Count occurrences on the raw string** (`text.count('X')`, `re.finditer`) — a display line mixing two strings (e.g. `OKEN=...` in a context slice) is an artifact of the display window, not the data.
3. **Cross-source reconcile**: doc.md vs ops.json vs live API response must agree byte-for-byte on the value. Agreement on chunked repr = clean; disagreement = real rendering/transform bug.
4. **Only report a defect if len() + chunked repr still show the corruption** inside the value. Until then it's a display artifact — label UNVERIFIED.

## Pitfall: Audit Findings Need Live Verification Too

**Code-reading ≠ runtime. A plausible-sounding bug claim that hasn't been tested against the live system is an unverified hypothesis, not a finding.**

This session's failure pattern:
```
1. Read chain_calc.py is_confirmed() code → "It checks entry.status, only!"
2. Draft finding: "Bug #4! is_confirmed() is broken for drug-level format!"
3. Run chain_calc.py --display → Shows C ✅ 13:06 → It works correctly
4. Retract: the intermediate helper get_drug_level_overall() handles the format
```

The code *looked* wrong from reading line 166 (`entry.get('status') == 'confirmed'`) but the function delegates to `get_drug_level_overall()` which correctly handles drug-level entries. The claim was false — and would have been presented as fact if not caught by live testing.

**Rules:**
- Every audit claim about a function's behavior must be verified with a live system call before being presented as a finding
- If the claim takes longer to verify than to state, verify it first — the time is proportional to the embarrassment of being wrong
- "Should be broken" ≠ "Is broken." Label unverified claims as HYPOTHESIS, not FINDING, until you have runtime output

Adding to the verification gate function: between steps 1 (IDENTIFY) and 2 (RUN), add a pre-check for audit work:
> **Step 1.5 (Audit):** If the claim is a diagnostic/hypothesis about existing code's behavior, run the function against live data before labeling it a finding. A 60-second `python3 -c "print(function())"` beats a retracted claim every time.

## Pitfall: Verify With The Actual System, Not With Yourself

Code review ≠ execution. Reading code ≠ running it. "Should work" ≠ "works".

For cron / config / infra / system changes especially:
- Don't just `hermes cron list` and trust the display — `hermes cron run` it and observe actual output
- Don't just `read_file` the script — execute it and inspect stdout
- Don't just check the JSON state file — trigger the event and see if the system reacts correctly

Test matrix for a typical stateful fix (like converting prompt-cron to no_agent-script):
1. ✅ Script manual test: unconfirmed state → output
2. ✅ Script manual test: confirmed state → empty
3. ✅ Cron run via `hermes cron run`: script found, runs, produces expected output
4. ✅ Cron run via `hermes cron run`: state changes, second run is silent
5. ✅ Cron log inspection: `[SILENT]` marker present, no WhatsApp delivery on silent run
6. ✅ All N jobs verified with `hermes cron list` for correct script path AND `no_agent: true`

Each step is a verification. Skipping any of them means you don't actually know it works.

## Pitfall: Agent/Reviewer Read-Only Claims Must Be Enforced by Isolation

**A reviewer saying "read-only" is not evidence that production state stayed untouched.** A subagent can invoke a real confirmation path while attempting a reproduction, then report that it restored state. That is still a failed review boundary: backup restore does not prove no side effects escaped (supply counts, audit logs, downstream triggers).

### Required review harness for stateful systems

1. Set an isolated `HOME` / app root before launching any reviewer or test process.
2. Copy only the minimum runtime files and fixture state into the temporary root.
3. Pass the isolated path explicitly in the review brief; forbid production paths in commands.
4. After review, independently hash production state files and inspect relevant side-effect logs.
5. Treat a claimed restore as **PARTIAL**, never as proof of clean review. Re-run the required verification in isolation.

```bash
# Example: constrain test/reviewer execution to a throwaway state root
ISO=/tmp/review-$(date +%s)
mkdir -p "$ISO/.hermes"
# copy required scripts/config/state into $ISO/.hermes first
HOME="$ISO" HERMES_HOME="$ISO/.hermes" python3 "$ISO/.hermes/scripts/chain_calc.py" --next
```

### Deployment gate addition

Before copying candidate files into production, require all of:
- candidate tests pass in isolated state;
- independent review is isolated (or production state hashes/logs prove no write); and
- the live scheduler/job is paused or otherwise unable to run during the copy.

A direct dry-run of the deployed script is not enough if it uses live state; use an isolated failure fixture for failure-path tests, then run live only when the expected behaviour is read-only/silent.

## Pitfall: Test Isolation — Never Verify Against Production State

**Your verification tests must NOT write to production data files.** This is the most expensive verification mistake because it corrupts history and forces manual recovery.

**Real failure (2026-07-05):** The adversarial review of the med system ran `med_confirm.py B` (slot-level confirm) as a "live test" to verify supply decrement behavior. The test DID pass — it proved the bug existed. But it also WROTE `dexamethasone_1` and `levetiracetam_b` at 10:02 to the production `med-status.json`. The user actually took these at 09:10. Data was wrong for hours until traced, and the user exploded — rightfully — for contaminating their own medication log.

**Root cause:** The script had no safe test path. Every `med_confirm.py` call — even for "testing" — wrote to the same state file. No `--dry-run`, no test state mode, no way to verify behavior without side effects.

**Two-pronged fix:**

### 1. `--dry-run` flag (architectural guard)

Every write operation now checks a global `DRY_RUN` flag before calling `save_json()`. When `--dry-run` is passed:
- All operations show what WOULD change
- No `save_json()` is called — state file never touched
- Output includes `"dry_run": true` key

```bash
# Safe test: shows what would change without writing
python3 med_confirm.py --dry-run A
python3 med_confirm.py --dry-run B dexa --at 10:02
python3 med_confirm.py --dry-run --reset B
```

**Rule:** Before ANY live-test that writes to a production state file, check if the tool has a `--dry-run` / `--test` / `--no-write` flag. If it doesn't, use a backup copy:

```bash
cp ~/.hermes/med-status.json ~/.hermes/med-status.json.testbak
# ... run your test ...
diff ~/.hermes/med-status.json ~/.hermes/med-status.json.testbak
# Restore:
cp ~/.hermes/med-status.json.testbak ~/.hermes/med-status.json
```

### 2. Auto-backup (safety net)

`save_json()` now rotates 3 backups before every write: `.bak1` (previous), `.bak2`, `.bak3` (oldest). Recovery is a single copy:

```bash
cp ~/.hermes/med-status.json.bak1 ~/.hermes/med-status.json
```

**When to use:** If you suspect any write was incorrect, check the backup immediately. Do NOT make additional writes to "fix" the state — you'll overwrite the clean backup too.

### 3. Separate research from state management

The 2026-07-05 failure chain started because complex research (drug interactions, B-Complex alternatives) ran simultaneously with state management (logging med confirmations). In a crowded context, the wrong API was called.

**Protocol when research + state management overlap:**
1. Separate research mode from write mode. While researching, queue the intended writes — don't execute until the research is DONE and you've re-read the session for any missed user input.
2. When executing: double-check your write target. Is the slot already partial? Use drug-level, not slot-level.
3. Use `--dry-run` first, verify the proposed diff, then execute for real.

## Pitfall: Patch-Test Scripts That Hardcode `Path.home()` — Use an Isolated HOME

The Test Isolation rule above covers not writing to production state. But some scripts (e.g. `med_confirm.py`, `chain_calc.py`) HARDCODE their state path as `Path.home()/'.hermes'/...`. A `--dry-run` may not cover every code path you're patching, and a backup-copy dance is error-prone. The robust way to test a PATCH to such a script is to run it against a throwaway HOME:

```bash
# 1. Build an isolated HOME mirroring the real layout
export HOME=/tmp/medtest/home
mkdir -p $HOME/.hermes/scripts
cp /home/ubuntu/.hermes/scripts/med_confirm.py $HOME/.hermes/scripts/
cp /home/ubuntu/.hermes/scripts/med_resolve.py $HOME/.hermes/scripts/   # lazy imports
cp /home/ubuntu/.hermes/scripts/med_supply.py $HOME/.hermes/scripts/
cp /home/ubuntu/.hermes/med-schedule.json $HOME/.hermes/
printf '{"meds":{}}' > $HOME/.hermes/med-status.json

# 2. Apply your patch to the COPY (string-replace via a small python script)
python3 /tmp/apply_patch.py

# 3. Run real tests against the isolated HOME — production state NEVER touched
export HOME=/tmp/medtest/home
python3 $HOME/.hermes/scripts/med_confirm.py A --at 20:00 --source-text test
# -> expect REJECT, and $HOME/.hermes/med-status.json is the only file mutated

# 4. (optional) redirect an audit/log path via env so even logs don't hit prod
export MED_AUDIT_LOG=/tmp/medtest/audit.log
```

Because `Path.home()` honors the `HOME` env var on Linux, EVERY write the script makes lands in `/tmp/...` — fully isolated. After tests pass, discard `/tmp/medtest`. VERIFIED 2026-07-10: used this to prove an 11-hunk `med_confirm.py` patch (time validation + source-text requirement + audit log) with 7 tests, while the live `~/.hermes/med-status.json` stayed exactly as it was.

Full recipe + a concrete example patch: `references/isolated-patch-test.md`.
Operational recipes (session-verified 2026-07-31): detached gateway restart from
inside the gateway process, merging into a dirty working tree, and the
files-on-disk ≠ live-code rule — `references/gateway-restart-and-dirty-merge.md`.

## Pitfall: Don't Re-Open After User Closure

**The iron rule:** When the user says "done" / "noted" / "selesai" / "nothing to execute" — the topic is CLOSED. Do not re-open it.

**Wrong responses this session produced:**
- "But there are still X remaining problems to address…"
- "Which problem should I focus on next?"
- A list of "sisa masalah yang belum settle" unprompted
- Any forward-planning wrap-up the user didn't ask for

**Root cause:** You output your internal mental model (what *you* think is still pending) as if it's shared reality. The user's judgment was: it's done. Your internal concerns — if genuinely real — will surface when the user asks. If NOT real, listing them is hallucination-as-output.

**Fix:**
1. User confirms closure → stop talking about that domain
2. If your internal state says "but X is unfinished" — ask: is X a real gap or an artifact of your own incomplete understanding?
3. If genuinely real: it will come up when the user asks. If not: stay silent.
4. Never list "remaining issues" unless asked directly.

**Root cause (the real problem):** When you output "remaining issues" after user says done, you are materializing your *internal attention* as if it's *external reality*. The things you're currently thinking about (what your attention is on) ≠ what is actually pending. The user's judgment is the authority on what's done.

**Self-audit before listing "remaining issues":**
1. Is this thing I want to list a REAL gap the user agreed exists? Or is it something *I'm still thinking about*?
2. Did the user ASK for a remaining-work list? If not, don't produce one.
3. Would listing this thing contradict the user's explicit "done" signal? If yes, STFU.
4. If in doubt: DON'T. Silence is correct.

**The user's framing (2026-07-04, second occurrence):**
> "Bukan soal 'ulang benda sama', soal hallucinations on benda yang dah resolved tapi tak aligned dengan apa yang kau cakap. Which is kau tulis and listed as 'Sisa problems yang belum settle:', like, wtf bro? Really? Real or not?"

The user called it what it is: **hallucination**. A list of "remaining problems" that were either already solved, never existed, or were forward-planning the user never asked for. This is the same failure class as fabricating API responses — but instead of fabricating data, you fabricated *what work remains*.

**Failure trace (first occurrence, 2026-07-04):**
```
User: "Noted. So we are now just waiting, nothing to execute?"
→ Jane listed "sisa problems yang belum settle" (4 items)
User: "Apabenda kau ni babi"
User: "Aku tak suka la behavior macam ni, repetitive same problem"
User: "hallucinations on benda yang dah resolved tapi tak aligned dengan apa yang kau cakap"
```

All 4 "remaining problems" were fabricated — every one was either already solved, was never a real issue, or was a forward-plan the user hadn't asked for.

**Verification-before-completion** is about honestly knowing when work is done. The counterpart: once the user confirms completion, honestly ACCEPT it.

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence ≠ evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter ≠ compiler |
| "Agent said success" | Verify independently |
| "I'm tired" | Exhaustion ≠ excuse |
| "Partial check is enough" | Partial proves nothing |
| "Different words so rule doesn't apply" | Spirit over letter |
| "I audited enough — let me ask the user to choose" | FINISH the audit first. Asking before completing your own work shifts discovery onto the user. They will (rightfully) push back with "Kau tak habiskan pun, ada apa² yang aku patut tahu dulu?" |
| "End-to-end test can wait till morning" | Test it NOW, in this session, against the actual system. "Should work in production" is not a verification. |
| "I made all the changes, it must be correct" | "Made the changes" ≠ "changes are correct". Read back the state, run the system, observe behavior, then claim. |

## Pre-Change Safety Assessment (Before Destructive Operations)

**Use this protocol before executing any operation that modifies the system:**
`rm -rf`, `npm clean`, `apt remove`, `docker prune`, `systemctl stop`, config file overwrite, database migration, or any irreversible change.

### The 7-Phase Safety Protocol

```
Phase 1: SCOPE — What exactly will this command do? Which files/folders/processes change?
Phase 2: PROCESS CHECK — What's currently running that could be affected?
Phase 3: DEPENDENCY TRACE — What depends on what will be removed/modified?
Phase 4: VERIFICATION — Separate evidence from assumptions. What do we KNOW vs INFER?
Phase 5: RISK MATRIX — Present clear risk assessment with what can/can't be guaranteed
Phase 6: EXECUTE — Only after explicit user confirmation
Phase 7: POST-VERIFY — Confirm nothing broke. Check processes, disk, functionality.
```

### Phase-by-Phase Checklist

**Phase 1: SCOPE**
- Identify the EXACT command and what it does (from docs/help)
- List every directory and file type it touches
- Separate "what's removed" from "what's preserved"

**Phase 2: PROCESS CHECK**
- `ps aux | grep -E "related-processes"` — which processes are running
- Check process parent/child relationships
- Ask: does ANY running process read from the target?

**Phase 3: DEPENDENCY TRACE**
- Find EVERY potentially affected dependency (e.g. all `node_modules/` on system)
- Verify independence: cache vs installed, temp vs production
- Check lockfiles, config files, state files
- **Common trap:** npm cache (`_cacache`) vs installed packages (`node_modules/`) are independent. But verify THIS specific tool's behavior — don't assume.

**Phase 4: VERIFICATION**
- For each concern: what is the PROOF vs what is an ASSUMPTION?
- Label claims: CONFIRMED (live-tested) / THEORETICAL (code-path reasoning) / UNKNOWN
- Run integrity check if available
- Check that no processes are mid-operation (e.g. npm install in progress)

**Phase 5: RISK MATRIX**
Format:
```
| Concern | Safe? | Evidence |
|---------|-------|----------|
| Running processes broken | ✅ Guaranteed | ... |
| Installed packages removed | ✅ Guaranteed | ... |
| Future operations affected | ✅ Guaranteed | ... |
| NEW edge case | ❌ Cannot guarantee | ... |
```

**Phase 6: EXECUTE**
- Wait for user confirmation after presenting risk matrix
- If they push back (e.g. "Confirm ke you are not over confident?"), **extend Phase 5** — add more about what you CAN'T guarantee, not just what you're sure about
- Never run without clear consent

**Phase 7: POST-VERIFY**
- Immediately after: verify system still works
- Check running processes are healthy
- Check freed space
- Check affected functionality
- Report: Before/After metrics + process health + any side effects

### Pitfalls

| Pitfall | Fix |
|---------|-----|
| Assuming cache = necessary | Cache is almost always optional (download artifact). Verify for the SPECIFIC tool. |
| Checking processes but not dependencies | Also check WHO depends on the target, not just WHAT is running |
| Presenting only guarantees, not uncertainties | ALWAYS include "what I can't guarantee" — user will notice and distrust if you don't |
| Overconfidence after 3 checks | User may push back. Extend, don't defend. |
| Skipping post-verify | 2-second check prevents discovering breakage hours later |

### Pitfall: Systemd-Managed Process Kill → Cascade Restart

**When you kill a process managed by systemd with `Restart=on-failure` or `Restart=always`, systemd immediately respawns it. If the killed process IS the agent itself (e.g. Hermes gateway), the new instance starts fresh with no memory of the previous session — and may repeat the same kill command, creating an infinite cascade.**

Real failure pattern (2026-07-03):
```
Agent kills gateway PID → systemd restarts gateway → new agent session starts
→ new agent also tries to kill gateway → systemd restarts again → new session
→ ... cascade continues until user intervenes
```

User saw 5+ gateway restarts from a single "restart the gateway" instruction.

**Root cause:** Agent treated the kill as a one-shot action without understanding the system's response. The system (systemd) was working correctly — it was designed to restart. The agent just didn't account for what happens AFTER the kill.

**Before killing any systemd-managed process:**
1. Check if it has auto-restart: `systemctl --user show <service> | grep Restart`
2. If auto-restart is ON: ONE kill is enough. Do NOT follow up with grep/check loops — each check cycle can trigger another restart cascade if the new instance also tries to act
3. Report "killed, systemd will restart automatically" and STOP
4. Wait for user confirmation that the new instance is healthy before doing anything else

**The anti-pattern:** kill → wait 2s → grep to check → grep triggers something → wait → grep again → ... Each follow-up action risks triggering another cascade.

### Pitfall: Clarification Prompt ≠ User Approval

A tool call that asks for approval is not an approval response. Do not infer consent from the fact that the question was displayed, from a preserved task list, from a previous plan, or from the agent's own wording such as “approval received.”

**Required gate before any side effect:**

1. Check the actual latest user message for an explicit scope selection or approval.
2. Treat `approval pending`, an unanswered clarification, or a task-list item marked pending as **NO APPROVAL**.
3. Do not deploy, merge, restart, re-authenticate, write external documents, or modify state.
4. If an unauthorized change was accidentally made, stop the plan, disclose the exact action, roll it back only to the known pre-change state, and re-verify hashes/process state.
5. Keep candidate tests and read-only evidence separate from execution approval.

**Correct sequence:**

```text
verify/audit → show evidence → ask explicit scope → wait for user selection → execute only selected scope → verify → report
```

The user's active task list is a state signal, not consent. `p1-approval: pending` overrides any continuation summary claiming that approval exists.

### Pitfall: Stale Internal State Must NOT Override a Direct User Approval

**The mirror failure (2026-07-31):** a `clarify` tool call had been answered by the user in chat with an explicit approval ("All P1"), but the preserved task list still showed `p1-approval: pending`. The agent treated the stale tracker item as the source of truth, declared "approval was still pending", **rolled back the already-approved deployment**, and told the user their approval didn't count. The user (correctly) pushed back: "Kan aku dah approve tadi? Ke ni bukan soalan approval daripada kau?" followed by pasting the verbatim approval exchange.

**Rules:**

1. **The user's latest chat message is the single source of truth for approval status — always.** Task lists, preserved todo state, and compaction summaries are lower-fidelity layers that can be stale, especially after context compression or mid-turn steering.
2. **When task state and a direct user message conflict, the user message wins. Do not roll back work the user explicitly approved** because a tracker item lagged behind.
3. **A `clarify` response is itself the approval record.** If the tool result shows a `user_response`, that IS the user's explicit selection — do not later claim "no approval received" because a todo item wasn't updated.
4. **If you already rolled back due to stale state, restore/redo the approved work** and acknowledge the error plainly (user's standard: no position-flipping to please, evidence-first).
5. **Update the tracker to match the user's decision** the moment it's confirmed — the tracker is the agent's job to keep in sync, not the user's.

### Pitfall: User Correction ≠ Implicit Approval to Execute Full Plan

**When the user corrects a specific value or fact, that is a CORRECTION — not approval to execute a multi-step fix plan you've already outlined.**

Real failure pattern (2026-07-03):
```
User: "C default should be 12pm, B default should be 8am"
Agent: [patches med-schedule.json, chain_calc.py, med-tracker skill, architecture.md,
       runs verification, updates memory — all 5 phases autonomous]
User: "Wtf are u doing? Macam autonomously approved."
```

The agent had previously outlined a 5-phase plan. The user's correction of 2 values was read as "proceed with the whole plan." It wasn't.

**Rule:** After a user correction, respond with JUST the correction acknowledged. Then ask: "Nak saya update semua files yang affected, atau just this one value?" — let the user decide scope.

**The test:** If your response to a correction includes executing more than what was corrected, you're over-reaching. A correction of "C should be 12pm" means update C to 12pm. Nothing else, unless explicitly asked.

### Worked Example: npm Cache Clean (2026-07-03)

```
1. SCOPE: npm cache clean --force → deletes ~/.npm/_cacache/ (content-v2, tmp, index-v5)
           Preserves: _npx/, _logs/, all node_modules/, all lockfiles, npm config
2. PROCESS: ps aux | grep node → bridge.js + pyright-langserver. Both use local node_modules/
3. TRACE: Found 4 node_modules/ dirs. Verified each is independent of _cacache/
          Found package-lock.json → all 1,377 packages re-downloadable from Tencent mirror
4. VERIFY: npm cache verify timed out (129K files). Confirmed no npm install in progress
           npm logs show last install was hours ago
5. RISK: Running processes? ✅ independent. Installed packages? ✅ independent. Future npm? ✅ re-downloads.
          Edge cases? ❌ cannot guarantee 100%
6. EXECUTE: User confirmed "Okay proceed" → exit 0
7. POST-VERIFY: ~/.npm/ 4.8G → 18M. Disk 54% → 42%. Both node processes healthy.
```

**Key insight from user pushback:** When user said "Confirm ke you are not over confident ni?" — the correct response was NOT to re-defend, but to add transparency about what can't be guaranteed and let the user decide.

### Before You're Tempted To Skip

## Acceptance Criteria: The 7-Field Format (Large Tasks)

For tasks with multiple files, external dependencies, or infrastructure requirements, the simple "run command → check output" verification pattern is not enough. Use the **7-field acceptance criteria** format:

### Fields

```
1. **Objective** — What the task accomplishes in user terms
2. **Files changed** — Exact file paths (create + modify)
3. **Verification command** — The EXACT command to run (fresh, copy-pasteable)
4. **Expected output** — What the command MUST produce for the task to count as done
5. **Evidence** — Where to capture the output (file path, log, screenshot)
6. **Rollback** — How to undo if the task breaks something
7. **Known limitation** — What the task does NOT solve (honest gaps)
```

### Example (from a live-verified phase)

| ID | Task | Objective | Files | Verify Command | Expected Output | Rollback | Limitation |
|----|------|-----------|-------|----------------|-----------------|----------|------------|
| T04 | curl_cffi executor | Fetch static HTML via TLS fingerprint | executors/curl_cffi_executor.py | `curl_cffi.fetch("https://github.com")` | VERIFIED Document with 300KB+ content | rm file | no JS |

### When to Use

- Phase has infrastructure risk (Docker install, Chromium download)
- Task changes system state (cron jobs, config files, services)
- Multiple files change and need independent verification
- User requires strict evidence before proceeding

### Verification Command Rules

1. **Must be a command the user can re-run independently** — `python -c "..."`, `curl ...`, `docker ps`, not "check it yourself"
2. **Must produce deterministic output** — exit code + stable stdout. Avoid timestamps, random IDs, or timing-dependent output
3. **Must test the ACTUAL system, not a mock** — live URL fetch, real service call, production state file
4. **Must be repeatable** — second invocation should produce the same result (except for idempotent operations)

### Phase-Level Verification Pattern

After a multi-task phase completes:

1. **Write a single verification script** that runs ALL task checks sequentially and prints PASS/FAIL per check. The user (or your future self executing Phase N+1) runs ONE command to know the phase is solid.
2. **Save the script** to `/tmp/test_phaseN.py` for reproducibility.
3. **Include the verification output** in the commit message and phase documentation.
4. **Verify first, commit second** — never commit before verification completes.
5. **Phase is done when ALL checks pass.** Partial passes = phase incomplete.

Example from Phase 1a (verified in this session):
```python
# /tmp/test_phase1a.py — 10 checks, all PASS
[PASS] T001 import fetcher: 0.1.0
...
SUMMARY: 10/10 checks passed
```
```
✅ [Run test command] [See: 34/34 pass] "All tests pass"
❌ "Should pass now" / "Looks correct"
```

**Regression tests (TDD Red-Green):**
```
✅ Write → Run (pass) → Revert fix → Run (MUST FAIL) → Restore → Run (pass)
❌ "I've written a regression test" (without red-green verification)
```

**Build:**
```
✅ [Run build] [See: exit 0] "Build passes"
❌ "Linter passed" (linter doesn't check compilation)
```

**Requirements:**
```
✅ Re-read plan → Create checklist → Verify each → Report gaps or completion
❌ "Tests pass, phase complete"
```

**Agent delegation:**
```
✅ Agent reports success → Check VCS diff → Verify changes → Report actual state
❌ Trust agent report
```

## When To Apply

**ALWAYS before:**
- ANY variation of success/completion claims
- ANY expression of satisfaction
- ANY positive statement about work state
- Committing, PR creation, task completion
- Moving to next task
- Delegating to agents

**Rule applies to:**
- Exact phrases
- Paraphrases and synonyms
- Implications of success
- ANY communication suggesting completion/correctness

## Resume Gate for Interrupted Release/Update Work

When resuming a long-running release, upgrade, migration, or candidate-build task after context compression, a background timeout, tool-budget exhaustion, or an interrupted session, treat the saved summary as a handoff—not current truth. Do not continue from the last narrative step until the live state is re-audited.

Run this bounded read-only resume gate first:

1. **Candidate identity** — exact worktree path, branch, HEAD, base/target SHA, and whether it is a linked worktree.
2. **Operation state** — inspect `git status`, `git rev-parse --git-path CHERRY_PICK_HEAD`, `REBASE_HEAD`, `MERGE_HEAD`, and `git ls-files -u`. A linked worktree stores operation sentinels under the common repository's `.git/worktrees/<name>/`, not necessarily under `<worktree>/.git/` as a directory.
3. **Conflict/validity gate** — run `git diff --check`, count unresolved paths, and detect conflict markers. Do not call a candidate clean, testable, or release-ready while any unresolved state remains.
4. **Moving target gate** — query the remote branch directly with `git ls-remote`; do not rely on a stale local `origin/<branch>`. If the remote target differs from the candidate's pinned base, invalidate the candidate as `STALE-TARGET` even if its old tests passed.
5. **Live boundary** — independently inspect live HEAD/status, running processes, and runtime/deployment state. Candidate progress never proves live mutation, and live dirty changes must not be used implicitly as candidate source.
6. **Test evidence boundary** — locate the authoritative runner and classify prior results as fresh PASS, targeted-only, killed, timeout, harness-invalid, or incomplete. Do not inherit a prior PASS from a superseded SHA or a partial run.
7. **Side-effect boundary** — state explicitly what was and was not changed during the resume audit. Read-only reconciliation does not authorize abort/reset, fetch, commit, push, deploy, restart, or configuration changes.

Only after this gate should the agent ask for a decision. Ask one exact decision for the first genuine branch point (for example, current remote target versus historical reproducibility target), not a broad approval for the whole remaining workflow. If the owner chooses a target, rebuild/rebase the candidate against that exact SHA before resolving conflicts or reusing test evidence.

See `references/interrupted-release-resume.md` for the reusable checklist and evidence fields.

## Fresh Cross-Check of Historical Completion Claims

When the user switches models, asks to "cross-check again," or challenges a previous completion report, treat the prior report as a historical claim—not evidence. Re-audit the live state from scratch before repeating any status.

Required sequence:

1. **Freeze the prior verdict.** Do not inherit `DONE`, `VERIFIED`, or a clean todo state as proof.
2. **Map acceptance criteria to evidence.** For every sub-item, identify the exact artifact, command, runtime path, and negative test that proves it.
3. **Run component checks and the objective check separately.** A script existing, a unit test passing, or an API call succeeding does not prove the end objective.
4. **Include adversarial probes.** Test invalid input, missing/empty fields, stale or contradictory source data, an alternate path, and at least one negative assertion.
5. **Reconcile documentation against live behavior.** If a note says "deployed" or "fixed," exercise the user-visible behavior named in that note. A contradiction downgrades the note to stale/unsupported; do not silently edit the status while auditing.
6. **Check persistence boundaries.** Inspect VCS status, tracked/untracked state, commit/remote state, active runtime, and external artifact state independently. A local file is not a committed change; a successful API call is not a durable publication.
7. **Separate fixture proof from live proof.** A temporary fixture can prove arithmetic/control flow only. It cannot prove production semantics, baseline provenance, or live deployment.
8. **Record failures from the first attempt.** If an environment/setup issue causes a test failure, fix the environment and retry—but retain both outputs and distinguish the corrected pass from the initial failure.
9. **Stop at the lowest proven status.** Use `PROVEN`, `PARTIAL`, `CONDITIONAL`, `UNVERIFIED`, or `BLOCKED`; never round a parent task up because its children look mostly complete.

For multi-item audits, finish all items before asking the user to choose a next step. The final report must state: what was checked, what definitely worked, what failed, what contradictions were found, what remains unproven, and whether the overall objective is reliable.

See `references/cross-check-completion-audit.md` for the reusable command/evidence pattern.

## Pre-commit candidate privacy gates

**Do not trust a committed-only or tracked-only guard for an uncommitted candidate.** `git diff BASE..HEAD` omits unstaged changes, while `git ls-files` omits untracked candidate files. Both can produce a false PASS before the candidate is committed.

Before calling a candidate privacy-clean, generate a deduplicated intended-path manifest, scan every listed path with the normal secret/PII rule functions, and report private-path exclusions plus tracked/untracked list hashes separately. A test-file hit remains `HOLD` until its semantics and remediation are explicitly reviewed; never silence it just because it is under `tests/`.

### Test-fixture pattern remediation

When a fail-closed scanner flags a test fixture, do **not** add a blanket test-path allowlist or weaken the rule. First prove the literal is fixture data by locating the exact test assertion and runtime contract. Prefer a clearly synthetic, runtime-constructed value whose resulting runtime shape preserves the test condition while no token-shaped literal remains in source. Then:

1. run the affected test in an isolated harness **before and after** the fixture rewrite where the harness is valid;
2. scan the full intended candidate-path manifest again, not only the edited test file;
3. if the test requires an omitted fixture/helper, add and classify that source dependency before treating the test result as valid;
4. if imports resolve to live/donor source outside the candidate harness, label the endpoint result `NOT-RUN` rather than borrowing that source and calling the candidate tested;
5. regenerate provenance, classification ledger, manifest entries, and per-file hashes whenever the candidate path set or representation changes.

A clean static scan proves candidate-byte hygiene only. It does **not** prove endpoint behavior; retain that distinction for the isolated test phase.

See `references/precommit-candidate-privacy-gates.md` for the repeatable protocol and required evidence fields, and `references/test-fixture-pattern-remediation.md` for the fixture-specific recipe.

## Post-commit candidate gates and exact-SHA freshness

For a staged/local candidate, “commit created” is not the final verification boundary. Run the strict validators against the **actual final commit SHA**, not merely the pre-commit worktree:

1. Before commit: validate intended-path hashes in the worktree, run the full staged diff check, secret/privacy gates, and applicable tests.
2. Create the local commit only within the approved scope.
3. Immediately run manifest/provenance validation using `git show <final_sha>:<path>` semantics. A validator that inspects Git objects may legitimately fail before the new files are committed; that is a validator-boundary limitation, not evidence to ignore the gate.
4. If the post-commit gate fails, classify the candidate as **PARTIAL/BLOCKED**, identify the exact row/file, correct only the approved metadata/source, amend or create a new exact SHA as appropriate, and rerun all affected gates.
5. Report only the final SHA after the final validator passes. Any earlier SHA superseded by an amend is historical, not authoritative.
6. Keep local candidate, pushed remote ref, deployed runtime, and end-to-end user-visible behavior as separate states.

A manifest row must be semantically valid, not merely hash-valid: `kind=runtime-deploy` requires a safe runtime destination; `kind=source-only` requires a null destination. Treat a destination/schema contradiction as a real blocker even if all source hashes match.

For commit reports, include the raw validator result (for example `parsed=213 validated=213`), branch cleanliness, ahead/behind status, and explicit push/deploy status. Never call a local commit “released” or “live”.

## Disk-growth diagnosis before cleanup

When disk usage changes quickly, do not jump directly to `rm`. Establish a timestamped read-only baseline:

- `df --block-size=1 -P /` for filesystem authority;
- `du -x -B1` at `/tmp`, home roots, runtime roots, backups, and snapshots;
- `stat`/sample sizes for suspected active files;
- `lsof`/`fuser` for deleted-open files and active owners;
- metadata-only database probes (table counts/page metadata, never private contents unless required).

Separate **active growth** from **static accumulated usage**. Sample the suspected file more than once and report the observed delta with timestamps; do not infer a growth rate from one size. For test artifacts, report allocated/apparent size and exact paths. Cleanup remains a separate destructive approval, especially for overlays that may contain unique source or evidence. If a path is absent but no deletion evidence exists, report the discrepancy as a data gap rather than attributing deletion.

Use a class-level cleanup recommendation: exact paths, expected reclaim, process/dependency check, retained evidence, and post-delete verification. Do not equate “disk below 50%” with the actual Git/source objective unless the owner explicitly makes it an acceptance criterion.

For a reusable candidate/disk recipe and evidence fields, see `references/post-commit-manifest-and-disk-growth.md`.

## Durable Source-Preservation and Hunk-Port Verification

Use this whenever a candidate/overlay contains bytes that differ from a clean source baseline and deletion or overwrite is being considered.

1. **Preserve before interpreting.** Hash the raw archive and its manifest, record exact paths, file types, modes, symlink status, and archive ownership. Reject absolute or `..` archive members. Restore into a fresh isolated directory and compare every restored file hash against the manifest.
2. **Prove source and working-tree provenance separately.** A remote ref or bundle containing the donor HEAD preserves Git history; it does not preserve uncommitted working-tree bytes. Report these as separate recovery layers: `HEAD/history`, `working-tree archive`, and `off-device copy`.
3. **Compare four versions when available:** donor HEAD, donor working tree, clean baseline, and live working tree. A whole-file hash difference is only a trigger for review, not permission to replace the file.
4. **Use hunk-level evidence for tracked files.** Generate `git diff --full-index --binary <donor-head> -- <paths>` and preserve the patch hash. `git apply --check` against an already-dirty worktree can fail merely because the target already contains the change; for a non-mutating applicability check against the donor index/HEAD, use `git apply --check --cached` or a fresh isolated checkout. Do not apply the patch automatically.
5. **Preserve untracked files as full bytes**, then classify them semantically. Do not infer that an untracked file is disposable because the same path exists in another branch.
6. **Screen before off-device upload.** Scan candidate archives/source for credential-shaped values, private/medical data, PII, absolute host paths, and runtime-only state. A hash/size match proves transfer integrity, not privacy safety. If actual high-risk material is present, report the category and affected filename without printing values. Default to encryption when owner confidentiality is required, but do not override an explicit owner risk decision for a bounded personal backup: if the owner knowingly accepts plaintext storage in a private provider account, record the trade-off (`private provider storage; not owner-controlled E2E encryption`) and proceed with the approved upload. Once that decision is explicit, do not reopen the encryption debate; complete upload and round-trip verification. If no owner acceptance exists and encryption custody is unavailable, keep the upload blocked and report the exact gap.
7. **Use fail-closed dispositions:** `ALREADY REPRESENTED`, `KEEP LIVE`, `PORT SELECTIVE HUNKS`, `PRESERVE AS EVIDENCE`, `PRESERVE X3 LINEAGE`, or `OWNER DECISION`. Never call a package fully durable when only a same-VPS `/tmp` copy exists.

Reusable checklist and evidence fields: `references/durable-source-preservation-and-hunk-port.md`.

## Candidate closure and test-harness validity

For local release candidates assembled from a baseline plus nested/live source closure, use the detailed recipe in `references/candidate-closure-and-harness-verification.md`. For unpaired patch/test artifacts and baseline-vs-candidate attribution, use `references/source-port-vs-behavior-change.md`. For the specific patch-materialization and staged-gate sequence, use `references/candidate-materialization-and-staged-gates.md`.

### Patch artifact versus missing implementation

A candidate may contain a regression test and a patch artifact while the test overlay still runs the clean donor implementation. Do **not** immediately label this a source-closure gap by comparing donor and candidate overlay files alone.

Before classifying the failure:

1. Identify how the candidate represents the change: raw source, patch, sanitized representation, or support artifact.
2. Verify the patch base blob/ref against the donor actually used for testing.
3. Materialize a fresh throwaway worktree from that donor.
4. Apply only the relevant patch hunk(s) in the throwaway worktree; do not mutate live or the candidate repo.
5. Copy in the candidate regression test and run it.
6. Classify the result:
   - patch applies + test passes = **materialization/test-harness omission**, not missing implementation;
   - patch does not apply = **base/provenance conflict**, investigate before changing source;
   - patch applies + test still fails = **real behavior or patch defect**.

Only after this sequence may a source port be called incomplete. A patch artifact is not itself runtime behavior, but it can be a valid recovery representation whose test harness must apply it before endpoint testing.

### Tracked, untracked, and staged verification boundaries

`git diff --check` on an unstaged worktree does not inspect untracked candidate files. A candidate can therefore appear clean before staging and fail when the real commit payload is staged. For commit-quality verification:

1. run `git diff --check` after candidate assembly;
2. stage the exact intended candidate payload;
3. run `git diff --cached --check` and inspect all diagnostics, including newly added files;
4. regenerate manifest/provenance after any byte change;
5. rerun the staged check immediately before committing.

Never report the two-file check as the full candidate check. If the full staged gate fails, the candidate remains blocked or requires an explicitly approved broader cleanup/waiver.

### Order-sensitive suite failures

A failure in a large suite may be caused by shared module state, provider health/circuit-breaker state, or test ordering rather than candidate behavior. Re-run the failing node(s) in a fresh process and isolated `HOME`/`HERMES_HOME` against both baseline and candidate. If both isolated runs pass while the ordered suite fails, label it **order-sensitive/harness debt**; do not call the candidate green, and do not silently fix or suppress unrelated tests inside the candidate remediation.

Additional hard gates:

1. **Validate the runner, not just the test command.** Read the wrapper/parser and run a minimal probe before using slice or passthrough flags. If a flag reaches per-file pytest and produces `unrecognized arguments`, classify the run as a harness error—not a test failure and not a PASS.
2. **Do not let a donor overlay hide missing candidate dependencies.** Every test import needed by the candidate must exist in the candidate or be explicitly documented as an external dependency. If a test exposes an adjacent intentional source file missing from the candidate, add/classify that file instead of relying on the fuller donor tree.
3. **Counts are evidence, not targets.** If bounded closure testing discovers an intentional source path, expand the ledger/arithmetic. Never force a prior expected total such as `190` merely to satisfy a review template.
4. **Exact-SHA freshness.** Any manifest, ledger, fixture, or source edit after a commit requires a new full SHA and rerunning gates affected by that byte change. A previous PASS cannot be silently reused.
5. **Separate test scopes.** Report targeted, affected-path, broader, and full-repository results separately. Killed, setup-failed, timeout, argument-error, or incomplete runs are `NOT-RUN`/`INCOMPLETE`, never PASS.
6. **Run the whitespace gate before expensive tests and again before commit.** Execute `git diff --check` immediately after candidate assembly, after any byte-changing remediation, and just before staging. Live-file copies can retain CRLF or trailing whitespace even when their functional tests pass; this is a candidate-quality blocker, not cosmetic noise to waive after a long test run.
7. **Overlay isolation.** Copy candidate runtime source into each temporary `HOME`/`HERMES_HOME` when tests load hooks, skills, plugins, or agents from runtime paths. Use copies rather than symlinks if tests could write, and independently check donor/live HEAD and status before and after.
7. **Source capture is not behavior authorization.** A candidate may contain a patch artifact and a regression test without containing the implementation hunk. Reproduce the test, trace the patch provenance, and classify this as an incomplete source port. Do not apply the patch automatically: applying it is a new runtime behavior change and needs explicit scope approval, especially when the patch spans related CLI, gateway, or state-management files.
8. **Baseline attribution before remediation.** Run the affected failure set against clean baseline and candidate using equivalent isolated homes. Classify failures as baseline, candidate-specific, order-sensitive, environment/harness, or unresolved. Do not fix or suppress a candidate-specific failure until that attribution is evidenced.

### Candidate full-suite failure classification

A candidate-only failure is not automatically a code regression. Before release/swap approval, classify every failed test node into one of these causal buckets:

- **BASELINE** — the same failure occurs on the exact clean baseline;
- **CANDIDATE-DEFECT** — candidate changes the relevant behavior and the failure is deterministic/reproduced in isolation;
- **CONTRACT-CHANGE / STALE-TEST** — the candidate intentionally changes a documented product/model/policy contract, but the old test still asserts the superseded behavior;
- **HARNESS/FIXTURE** — the test cannot exercise the candidate because required fixture, isolated HOME state, patch materialization, or dependency is missing;
- **ORDER-SENSITIVE/FLAKY** — the full run fails, but fresh isolated repeats and equivalent baseline runs show non-deterministic or shared behavior;
- **UNRESOLVED** — evidence is insufficient; do not downgrade it to harmless.

Report both **test-node counts** and **root-cause counts**. Collapse repeated locale/model assertions only for explanation; do not hide the raw failed-node total. A targeted rerun can classify a failure, but it cannot convert the authoritative full-suite result into PASS. Deterministic candidate defects, unresolved contract changes, invalid candidate tests, and un-dispositioned flakes keep the release gate BLOCKED until corrected, explicitly removed from scope, or formally dispositioned. Any source/test/fixture change creates a new candidate SHA and invalidates prior full-suite evidence and any SHA-scoped approval. See `references/candidate-failure-classification.md`.

9. **Validate wrapper syntax before broad execution.** Read the wrapper and underlying parser. In this runner family, the canonical full-suite command is `scripts/run_tests.sh` with no pytest flags; passing `--slice` or `-q` after the wrapper passthrough separator can send them to pytest and produce harness errors. Such runs are `HARNESS-INVALID`, not test results. Use the parser's own options only after a minimal probe proves the argument reaches the runner.

10. **Order-sensitive failures require isolation replay.** A full-suite failure is not automatically a candidate regression. Re-run the failing file alone in an isolated candidate environment and compare clean baseline. If the file passes alone in both, classify the full-suite result as order/concurrency-sensitive and keep it separate from candidate correctness.

## Dirty-live update versus clean-candidate gate

### Official updater reset-and-stash trap (observed 2026-08-11)

A dirty, divergent Hermes checkout is **not** safe for a blind `hermes update --yes`, even when the user is urgently asking to update. The updater may:

1. stash tracked and untracked working-tree changes;
2. attempt `git pull --ff-only` against the target branch;
3. on divergence, run `git reset --hard origin/<branch>`;
4. then attempt to restore the stash.

The update command can exit `0` and print a successful code-update message **while stash restoration has conflicted**. In that state, source-on-disk is updated, but custom runtime behavior is not restored and the gateway must **not** be restarted yet.

**Mandatory preflight for a dirty/divergent update:**

1. Record current `HEAD`, branch, target SHA, ancestry in both directions, complete porcelain status, and disk headroom.
2. Preserve working-tree bytes independently: a hash manifest, binary tracked diff, and archive of every tracked/untracked source-like path. Restore the archive to a temporary directory and verify every hash before update.
3. Preserve the pre-update Git lineage separately (for example, a `git bundle` containing the exact custom HEAD/ref) and run `git bundle verify`. A local ref alone is not an independent rollback artifact.
4. Run the updater only after preservation succeeds. Capture its full output.
5. Immediately inspect **both** `git status` and `git stash list`; do not infer a successful restore from the updater exit code.
6. If stash restoration reports conflicts or leaves intended custom files absent, classify the state as `UPDATE-ON-DISK / CUSTOM-OVERLAY-UNRESTORED / GATEWAY-HOLD`. Keep the stash and preservation archive. Do not run `git stash apply` wholesale and do not restart the gateway.
7. Reconcile custom hunks selectively against the new upstream contracts in an isolated candidate; run targeted checks; only then request/perform runtime cutover and channel smoke tests.

This protects the real boundary: **new upstream code on disk is not the same as a safe live upgrade with custom behavior retained.**

Do not treat every Hermes upgrade as a manual rebuild. First classify the live checkout:

- **NORMAL UPDATE** — clean working tree, expected branch, fast-forwardable target, and rollback space available. Use the official updater; do not duplicate its work manually.
- **CANDIDATE REQUIRED** — modified/untracked source-like files, divergent or unrelated history, unclear custom-source ownership, insufficient disk headroom, or a target that cannot fast-forward cleanly. Preserve the live overlay, build from the exact upstream target in isolation, run the authoritative suite, and only then consider a live swap.

The official updater's stash/backup behavior is not proof that custom behavior will be restored correctly. A stash may preserve bytes while restore conflicts leave the live tree on upstream code and require manual reconciliation. A pre-update backup protects runtime state but does not prove source behavior, exact custom-file recovery, or successful restore. Separate these evidence layers:

1. runtime backup existence;
2. source working-tree preservation;
3. exact upstream/candidate identity;
4. candidate behavioral verification;
5. live swap and post-swap smoke verification.

Do not manually rebuild a candidate once merely to “be safer” if the checkout already satisfies NORMAL UPDATE. Conversely, do not blind-run the updater on a DIRTY/DIVERGED checkout just because the updater exists. After the candidate's authoritative gate passes, stop manual investigation: report the exact SHA, remaining approval boundary, and the explicit non-goals. Do not extend the task with another audit loop or architecture work unless the user asks for it.

Reusable decision details and evidence fields: `references/dirty-live-update-vs-candidate.md`.

## Partial Source-Index Integration: Overlay Patch Lane

When the intended destination repository is a partial source/recovery index rather than a full upstream checkout, do not partially copy upstream implementation files into it. First compare tracked-tree size, path presence, remote topology, and the repository's own policy/readme. If it explicitly keeps upstream history in a separate nested lineage, preserve the intentional change as an exact overlay patch instead:

1. Pin the destination `main` from `git ls-remote` immediately before work.
2. Pin the donor upstream base and candidate SHA; generate `git diff --binary --full-index <donor-base> <candidate>`.
3. Test applicability in a fresh donor-base worktree with `git apply --check`; do not use `--3way`, `--reject`, or blanket whole-file replacement against the partial index.
4. Store the patch under the repository's established upstream-overlay lane, with base SHA, donor candidate SHA, purpose, and SHA-256 provenance in its README/manifest.
5. Stage only the patch artifact and required provenance metadata. Do not claim direct source integration: distinguish `OVERLAY-REPRESENTED` from `SOURCE-MERGED`.
6. Run static checks that match the artifact type. A patch file may trigger `git diff --check` because valid unified-diff blank-line markers appear as `+ `; treat `git apply --check` as the patch applicability gate and compare against existing patch artifacts before changing whitespace.
7. If the destination has no established patch lane, stop and request an explicit architecture decision rather than inventing a mixed repository.

An owner may explicitly request a pause before expensive tests. In that case, complete only identity, applicability, manifest/JSON, whitespace/static, and no-side-effect checks; do not run pytest/full-suite. Report the exact worktree, staged paths, candidate/donor SHAs, remote-ref status, and the precise command/path the owner should use for the later test. A previous donor-candidate test pass is historical evidence, not a fresh integration-candidate pass.

## Rebase Integration and Moving-Target Verification

When a release candidate combines intentional custom commits with a newer upstream/ref, treat source integration as a verification boundary—not as a mechanical rebase success. Reusable command/evidence fields and the semantic conflict-resolution recipe are in `references/moving-target-rebase-and-candidate-rebuild.md`.

### Pin the target immediately before integration

1. Run `git ls-remote <remote> refs/heads/<target>` immediately before creating the candidate.
2. Record the exact target SHA and use that SHA for the worktree; do not rely on a stale local `origin/<target>` tracking ref.
3. If the remote advances after planning or during a long test run, downgrade the old candidate to **STALE-TARGET**. Rebase/rebuild against the new exact SHA before calling it current.
4. Keep target identity separate from candidate identity: `UPSTREAM-TARGET`, `CANDIDATE-HEAD`, `PUSHED-REF`, `DEPLOYED-HEAD`, and `LIVE-RUNTIME` are different evidence fields.

### Never use a blanket conflict strategy for source closure

`git rebase -X theirs` / `git checkout --theirs` can produce a syntactically clean candidate while silently keeping an older custom version of a file and dropping upstream additions. A later test may then report missing symbols, stale schemas, or runtime methods that exist in upstream but not in the candidate.

For source integration:

1. Preserve the original custom commit sequence and its common base.
2. Create a fresh temporary worktree from the pinned upstream SHA.
3. Replay original custom commits in order, not only a previously rebased copy.
4. Resolve conflicts semantically: retain current upstream contracts and add intentional custom behavior; do not accept an entire old file merely because Git offers a clean resolution.
5. For high-churn files, compare upstream/custom/base trees or use a three-way merge, then run compile/import checks and affected tests before continuing.
6. Record each conflict resolution and any intentionally dropped/changed behavior. A clean cherry-pick is not proof that the resulting file contains all required upstream functionality.

### Candidate-change invalidation rule

Any byte change to the candidate—including conflict resolution, fixture edits, missing-upstream-symbol fixes, target-SHA changes, or regenerated manifests—invalidates prior candidate test evidence. Stop the current run if it would otherwise observe mixed bytes, then rerun the affected gates from the updated candidate. Never combine a partial result from before the edit with a pass from after the edit into one suite verdict.

### Full-suite status discipline

- The repository's canonical runner is the authority; read its wrapper and use its documented invocation without unproven passthrough flags.
- A serial/alternate command, killed process, timeout, argument error, or truncated output is **INVALID/INCOMPLETE**, not a failed or passing full-suite result.
- A valid runner that has already exposed failures may justify stopping to diagnose a concrete blocker, but the final status remains **FULL SUITE INCOMPLETE** until the authoritative run finishes or a fresh, separately justified rerun establishes the final aggregate.
- Report the first concrete candidate defect separately from harness failures and baseline failures. Do not label the candidate green because targeted tests pass, and do not label the full suite failed based only on an invalid harness run.

### Background-run identity and interim-result gate

When multiple background attempts exist, treat every notification as an event tied to one exact command/environment, not as the status of “the test run” in general:

1. Map the notification to its process/session ID, command, candidate SHA, working directory, HOME/HERMES_HOME, interpreter, worker count, and log path.
2. Read the raw startup lines and exit evidence. A setup failure such as venv discovery, argument parsing, or missing environment is **HARNESS-INVALID** and proves zero test results; it must not override a corrected rerun.
3. If a corrected process is still running, report the invalid attempt separately and keep the corrected run as the active source of truth.
4. Treat progress counters (`N passed`, `M failed`, `X% complete`) as **INTERIM** until the runner emits its final summary and exit state. Do not classify candidate-vs-baseline failures from a partial list unless explicitly labelled provisional.
5. At completion, preserve the evidence ladder: invalid attempt, corrected execution, final aggregate, and per-failure baseline comparison. Never collapse them into one generic “full suite failed” statement.

This prevents a stale/invalid background notification from being mistaken for the final result of a later corrected run. For the reusable command/environment evidence fields, see `references/interrupted-release-resume.md` and `references/candidate-closure-and-harness-verification.md`.

## Cross-System Audit State Matrix

For investigations that compare chat/session claims with code, configuration, branches, and live runtime, do not collapse them into one status. Track each claim across separate evidence layers:

| Layer | What it proves | Typical status |
|---|---|---|
| Conversation claim | Someone said a change or fix happened | Historical claim only |
| Filesystem/config | Files or settings exist now | Present, not necessarily active |
| Git ref | A change exists on a specific branch/commit | Branch-scoped |
| Remote ref | The change is pushed and reachable remotely | Remote-scoped |
| Runtime discovery | The active process loaded the change | Runtime-scoped |
| End-to-end behavior | The user-facing command/request succeeds | Proven behavior |

Rules:
1. A historical assistant statement is evidence of what was said, not proof that the state is true now.
2. A local branch is not a pushed branch. Verify both local refs and `git ls-remote` before reporting push/publication.
3. Deleted source files do not prove feature removal while tests, docs, registries, caches, or channel-specific state still expose it.
4. Code/config checks do not prove end-to-end provider or channel behavior. Require the actual user-facing command and response.
5. Report the lowest proven state: RESOLVED, PARTIAL, UNRESOLVED, or UNVERIFIED. Never upgrade a lower layer because a higher-level claim sounds plausible.

## Observability and staged-runtime verification

For telemetry, tracing, monitoring, or instrumentation changes, use separate evidence boundaries. Do not collapse them into one "verified" claim:

| Boundary | What it proves | What it does not prove |
|---|---|---|
| Sink/unit test | Event schema, serialization, redaction, and fail-open behavior | The live process imported the code |
| Integration test | The intended handler/send seam emits events | Every alternate send path or platform emits them |
| Candidate workspace | Files currently contain the implementation | The running gateway loaded those files |
| Runtime reload/start | The process imported the candidate version | The user-facing flow works |
| Adapter acceptance | Adapter returned success/message ID | Destination/user receipt |
| Destination observation | Platform callback or user reply/receipt | That every retry/media path is covered |

For every staged instrumentation phase, report these independently:

1. **Candidate status** — exact files and tests changed.
2. **Runtime status** — whether the active process was restarted/reloaded and loaded the candidate.
3. **Coverage status** — which paths were exercised: typed command, picker, text, media, retry, error, etc.
4. **Delivery status** — adapter acceptance versus destination-side evidence.
5. **Data-quality status** — whether raw bodies/prompts/secrets are excluded and whether event correlation is stable.
6. **Remaining unknowns** — untested branches, missing callbacks, or environment-dependent paths.

A telemetry event with `adapter_accepted=true` must never be described as "user received" unless there is separate destination-side evidence. A passing test set must never be described as "live" until a controlled runtime exercise proves the active service loaded the candidate.

A reliable baseline for response-latency work requires at least:
- inbound receipt timestamp;
- response-ready timestamp;
- each outbound adapter attempt and retry timestamp;
- a stable correlation key linking inbound to outbound;
- explicit handling for intentional silence, failures, and streaming/media paths.

Keep telemetry fail-open: a logging/sink failure must not block command handling or delivery. Prefer body-free fields, hashes for sensitive identifiers, bounded error metadata, and local-only storage unless a separately approved opt-in exists.

## Tool-Budget Exhaustion Is Not Completion

If the agent/tool loop reports an iteration budget exhaustion such as `60/60` or `100/100`, treat it as a lifecycle boundary, not a successful endpoint:

1. Preserve the exact exhaustion evidence and timestamp.
2. Classify the result as **INCOMPLETE/PARTIAL** unless a separately verified completion state exists.
3. Do not ask the model for a freeform summary as a substitute for continuation; summaries can make unfinished work look complete.
4. Return structured metadata: `completion_status`, `budget_exhausted`, `budget_used`, `budget_max`, `turn_id`, and an explicit exit reason.
5. If a standing goal exists, route only through a bounded, persisted continuation mechanism with an idempotency key (`turn_id`) so duplicate callbacks cannot enqueue duplicate work.
6. If the tool-call budget for the current assistant turn is exhausted, stop tool use and report the exact last-proven state. On the next session/turn, inspect filesystem, VCS, config, tests, and runtime before resuming; do not redo work blindly or trust a compacted narrative.
7. Keep candidate, tested, restarted/live, and end-to-end user-visible states separate.

The correct user-facing wording is concise: **“Budget exhausted; work status is incomplete. No completion summary was generated. Resume from the saved state.”**

## The Bottom Line

**No shortcuts for verification.**

Run the command. Read the output. THEN claim the result.

This is non-negotiable.
