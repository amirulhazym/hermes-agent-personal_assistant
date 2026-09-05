---
name: xcute
description: Disciplined 5-phase engineering pipeline for Hermes: Investigation -> Grilling -> Matt Pocock Spec/Tickets -> Owner Gate -> Superpowers TDD -> Protected Git PR Flow.
---

# `xcute` — Autonomous Disciplined Engineering Pipeline

Use when executing non-trivial features, fixes, or architectural modifications in the Hermes ecosystem. Enforces strict fact-finding before questioning, formal specification before coding, an explicit human approval gate, test-driven development, and autonomous publication to protected `main`.

## The 5-Phase Execution Contract

```
[Phase 1: Investigation & Grilling]
         │
         ▼
[Phase 2: Spec & Tracer-Bullet Tickets (Matt Pocock)]
         │
         ▼
[Phase 3: Owner Approval Gate (MANDATORY STOP)]
         │
         ▼ (Approved)
[Phase 4: Superpowers TDD Execution]
         │
         ▼
[Phase 5: SSOT Git & Protected PR Flow]
```

---

### Phase 1: Deep Investigation & Grilling (`grill-me` / `grilling`)

1. **Fact-Finding First**:
   - Inspect codebase, DB state, runtime logs, and platform adapters to locate root cause *before* asking questions.
   - **Rule**: Finding facts is agent work, never user work. Never ask the user for something discoverable on the VPS.
2. **Design Tree Interview**:
   - Identify decision frontiers where implementation genuinely branches.
   - Format each decision as:
     ```text
     ❓ **Q<N>** - **<Decision Title>**: <Context and choices>
     ➡️ <Recommended Option (Reasoning)>
     ```
3. **Decision Lock**:
   - Wait for the owner's explicit confirmation (e.g. `Q1:A, Q2:D, Q3:B`).
   - Do NOT proceed to planning with unverified assumptions.

---

### Phase 2: Specification & Tracer-Bullet Tickets (Matt Pocock Skills)

1. **Repository Alignment (`setup-matt-pocock-skills`)**:
   - Ensure `docs/agents/issue-tracker.md` and `docs/agents/domain.md` exist.
2. **Formal Specification (`to-spec`)**:
   - Author `.scratch/<feature-slug>/spec.md` with sections:
     - Problem Statement
     - Solution
     - User Stories (numbered, format: *As an <actor>, I want <feature>, so that <benefit>*)
     - Implementation Decisions (interfaces, models, state changes)
     - Testing Decisions
     - Out of Scope
3. **Tracer-Bullet Vertical Slices (`to-tickets`)**:
   - Author markdown tickets under `.scratch/<feature-slug>/issues/<NN>-<slug>.md`.
   - Each ticket must cut a narrow vertical slice through all relevant layers (schema, logic, formatting, tests) and declare its explicit `Blocked by:` dependencies.
4. **Implementation Plan (`writing-plans`)**:
   - Author `docs/superpowers/plans/YYYY-MM-DD-<feature-slug>.md` with bite-sized TDD tasks (failing test, run fail, minimal implementation, run pass, commit).

---

### Phase 3: Owner Approval Gate (Human Gate)

**CRITICAL GATING STEP — STOP AND WAIT**:
Present a concise **Review Brief & Architecture Lock** before executing any code:

```text
### Review Brief & Architecture Lock

- Root Cause: <one clear sentence>
- Selected Values: <exact options chosen by owner>
- Output Preview: <sample of real output or behavior>
- Artifacts: <links to spec, tickets, and plan>
- Status: plan only (Ready for execution)
```

- Ask for explicit owner permission to begin Phase 4 execution.
- **NEVER** start implementation until the user explicitly says to proceed.

---

### Phase 4: Superpowers Execution (`executing-plans` / TDD)

1. **TDD Cycle (Red-Green-Refactor)**:
   - For every component or ticket:
     - **Step 1**: Write the failing unit test (e.g. `tests/gateway/test_<feature>.py`).
     - **Step 2**: Execute via `pytest` to confirm failure (Red).
     - **Step 3**: Implement minimal code change.
     - **Step 4**: Re-run `pytest` to confirm pass (Green).
2. **Platform Formatting Verification**:
   - If user-facing text is rendered across messaging platforms (Telegram vs WhatsApp):
     - **Telegram**: Test escaping for MarkdownV2 (`*italic*`, `**bold**`, `\`code\``, unindented `>` blockquotes).
     - **WhatsApp**: Test `WhatsAppBehaviorMixin.format_message` (`*bold*`, `_italic_`).
     - Verify no stray unescaped markdown syntax leaks to the user.
3. **Full Regression Suite**:
   - Run relevant module test suites (e.g. `tests/gateway/test_resume_command.py`) to guarantee zero regressions.

---

### Phase 5: SSOT Git & Protected PR Flow (`hermes-git-pr-flow`)

All changes must be captured into the personal development SSOT (`/home/ubuntu/hermes-agent-personal_assistant-work`):

1. **Patch Generation & Source Representation**:
   - If framework dependencies (`~/.hermes/hermes-agent`) were updated, generate unified patch in `patches/upstream-hermes/YYYY-MM-DD_<feature>.patch`.
   - Keep SSOT repository clean and structured.
2. **Deterministic Quality & Security Gates**:
   - `bash scripts/guard/secret-scan.sh --tree` → **PASS**
   - `python3 scripts/guard/pii-review.py --diff origin/main..HEAD` → **PASS**
   - `python3 scripts/guard/manifest_recompute.py docs/reconciliation/v3-source-coverage-manifest.json HEAD`
   - `bash scripts/guard/manifest-validate.sh docs/reconciliation/v3-source-coverage-manifest.json $(git rev-parse HEAD)` → **PASS**
   - `bash scripts/run_contract_tests.sh` → **PASS** (100% of contract tests green)
3. **Autonomous GitHub PR Publication**:
   - Resolve `GITHUB_PERSONAL_ACCESS_TOKEN` / `GITHUB_TOKEN` from `~/.hermes/.env`.
   - Push commit to deterministic remote branch `feat/<feature-slug>`.
   - Create PR via GitHub REST API (`POST /repos/{owner}/{repo}/pulls`).
   - Poll CI status checks (`GET /commits/{head_sha}/check-runs`) until all checks complete with `conclusion=success`.
   - Merge PR via squash merge (`PUT /pulls/{pr}/merge` with `merge_method: squash`).
   - Delete remote publication branch (`DELETE /git/refs/heads/{branch}`).
   - Sync local `main` with `origin/main` (`git fetch origin main && git reset --hard origin/main`).
4. **Final Receipt**:
   - Confirm local working tree is clean and 0 ahead / 0 behind `origin/main`.
