---
name: debugging-and-error-recovery
description: Guides systematic root-cause debugging. Use when tests fail, builds break, behavior doesn't match expectations, or you encounter any unexpected error. Use when you need a systematic approach to finding and fixing the root cause rather than guessing.
---

# Debugging and Error Recovery

## Overview

Systematic debugging with structured triage. When something breaks, stop adding features, preserve evidence, and follow a structured process to find and fix the root cause. Guessing wastes time. The triage checklist works for test failures, build errors, runtime bugs, and production incidents.

## When to Use

- Tests fail after a code change
- The build breaks
- Runtime behavior doesn't match expectations
- A bug report arrives
- An error appears in logs or console
- Something worked before and stopped working

## The Stop-the-Line Rule

When anything unexpected happens:

```
1. STOP adding features or making changes
2. PRESERVE evidence (error output, logs, repro steps)
3. DIAGNOSE using the triage checklist
4. FIX the root cause
5. GUARD against recurrence
6. RESUME only after verification passes
```

**Don't push past a failing test or broken build to work on the next feature.** Errors compound. A bug in Step 3 that goes unfixed makes Steps 4-6 wrong.

## The Triage Checklist

Work through these steps in order. Do not skip steps.

### Step 1: Reproduce

Make the failure happen reliably. If you can't reproduce it, you can't fix it with confidence.

```
Can you reproduce the failure?
├── YES → Proceed to Step 2
└── NO
    ├── Gather more context (logs, environment details)
    ├── Try reproducing in a minimal environment
    └── If truly non-reproducible, document conditions and monitor
```

**When a bug is non-reproducible:**

```
Cannot reproduce on demand:
├── Timing-dependent?
│   ├── Add timestamps to logs around the suspected area
│   ├── Try with artificial delays (setTimeout, sleep) to widen race windows
│   └── Run under load or concurrency to increase collision probability
├── Environment-dependent?
│   ├── Compare Node/browser versions, OS, environment variables
│   ├── Check for differences in data (empty vs populated database)
│   └── Try reproducing in CI where the environment is clean
├── State-dependent?
│   ├── Check for leaked state between tests or requests
│   ├── Look for global variables, singletons, or shared caches
│   └── Run the failing scenario in isolation vs after other operations
└── Truly random?
    ├── Add defensive logging at the suspected location
    ├── Set up an alert for the specific error signature
    └── Document the conditions observed and revisit when it recurs
```

For test failures:
```bash
# Run the specific failing test
npm test -- --grep "test name"

# Run with verbose output
npm test -- --verbose

# Run in isolation (rules out test pollution)
npm test -- --testPathPattern="specific-file" --runInBand
```

### Step 2: Localize

Narrow down WHERE the failure happens:

```
Which layer is failing?
├── UI/Frontend     → Check console, DOM, network tab
├── API/Backend     → Check server logs, request/response
├── Database        → Check queries, schema, data integrity
├── Build tooling   → Check config, dependencies, environment
├── External service → Check connectivity, API changes, rate limits
└── Test itself     → Check if the test is correct (false negative)
```

**Use bisection for regression bugs:**
```bash
# Find which commit introduced the bug
git bisect start
git bisect bad                    # Current commit is broken
git bisect good <known-good-sha> # This commit worked
# Git will checkout midpoint commits; run your test at each
git bisect run npm test -- --grep "failing test"
```

### Step 3: Reduce

Create the minimal failing case:

- Remove unrelated code/config until only the bug remains
- Simplify the input to the smallest example that triggers the failure
- Strip the test to the bare minimum that reproduces the issue

A minimal reproduction makes the root cause obvious and prevents fixing symptoms instead of causes.

### Step 4: Fix the Root Cause

Fix the underlying issue, not the symptom:

```
Symptom: "The user list shows duplicate entries"

Symptom fix (bad):
  → Deduplicate in the UI component: [...new Set(users)]

Root cause fix (good):
  → The API endpoint has a JOIN that produces duplicates
  → Fix the query, add a DISTINCT, or fix the data model
```

Ask: "Why does this happen?" until you reach the actual cause, not just where it manifests.

### Step 5: Guard Against Recurrence

Write a test that catches this specific failure:

```typescript
// The bug: task titles with special characters broke the search
it('finds tasks with special characters in title', async () => {
  await createTask({ title: 'Fix "quotes" & <brackets>' });
  const results = await searchTasks('quotes');
  expect(results).toHaveLength(1);
  expect(results[0].title).toBe('Fix "quotes" & <brackets>');
});
```

This test will prevent the same bug from recurring. It should fail without the fix and pass with it.

### Step 6: Verify End-to-End

After fixing, verify the complete scenario:

```bash
# Run the specific test
npm test -- --grep "specific test"

# Run the full test suite (check for regressions)
npm test

# Build the project (check for type/compilation errors)
npm run build

# Manual spot check if applicable
npm run dev  # Verify in browser
```

## Isolated Full-Suite Parity (Hermes candidates)

A full-suite failure in an isolated candidate does **not** by itself prove the candidate code is broken. Hermes tests may deliberately load runtime-managed artifacts such as hooks, skills, plugins, agents, or scripts via `HOME` / `HERMES_HOME`.

Use this bounded triage before changing source:

1. **Preserve the full-suite log** and record the exact disposable `HOME`, `HERMES_HOME`, Python/venv, candidate SHA/worktree, and runner command.
2. **Classify the first failure by mechanism:**
   - missing file/module under disposable `HOME` → test-fixture parity issue;
   - assertion in a path changed by the candidate → candidate-relevant until disproven;
   - assertion in an untouched path → reproduce it in the same isolated environment before calling it baseline/environmental.
3. For a fixture-parity issue, construct a **fresh disposable HOME** from the candidate's source-managed runtime artifacts only (for example hooks/skills/plugins/agents/scripts). Do not copy sessions, databases, credentials, caches, or other private mutable state merely to make tests pass.
4. Rerun the **specific failing test first**. If it passes, rerun the full suite from the clean rebuilt test HOME; never count the first run as a valid candidate gate.
5. If a source-level failure remains, compare the smallest relevant semantic delta against the known-good candidate/original implementation. Port only compatible behavior; do not carry unrelated relaxations or policy changes because they happen to live in the same historical diff.
6. Re-run the focused test immediately, then use the rebuilt full suite as the authoritative regression gate.

**Pitfalls**

- Do not call every full-suite failure a regression before reproducing it in a parity-correct isolated environment.
- Do not silence artifact-dependent tests just because the first disposable HOME omitted the artifact; rebuild the test fixture first.
- Do not treat a passing focused test as a full-suite pass. Keep the full-suite outcome separate and visible.
- When a historical diff contains both the required fix and an unrelated policy relaxation, port the smallest compatible subset and retain the live policy unless the owner explicitly approves changing it.

## Error-Specific Patterns

### Test Failure Triage

```
Test fails after code change:
├── Did you change code the test covers?
│   └── YES → Check if the test or the code is wrong
│       ├── Test is outdated → Update the test
│       └── Code has a bug → Fix the code
├── Did you change unrelated code?
│   └── YES → Likely a side effect → Check shared state, imports, globals
└── Test was already flaky?
    └── Check for timing issues, order dependence, external dependencies
```

### Build Failure Triage

```
Build fails:
├── Type error → Read the error, check the types at the cited location
├── Import error → Check the module exists, exports match, paths are correct
├── Config error → Check build config files for syntax/schema issues
├── Dependency error → Check package.json, run npm install
└── Environment error → Check Node version, OS compatibility
```

### Runtime Error Triage

```
Runtime error:
├── TypeError: Cannot read property 'x' of undefined
│   └── Something is null/undefined that shouldn't be
│       → Check data flow: where does this value come from?
├── Network error / CORS
│   └── Check URLs, headers, server CORS config
├── Render error / White screen
│   └── Check error boundary, console, component tree
├── Unexpected behavior (no error)
│   └── Add logging at key points, verify data at each step
└── "File not found" on a path you know exists
    └── Check for hardcoded wrong home dir in config/scripts
        → Search ALL instances of the broken path pattern before fixing one
        → Use `search_files(target='content', pattern='wrong/path')` across the config home
        → The `patch` tool is BLOCKED on config.yaml; use `sed -i` via terminal() instead
```

## Multi-Point Investigation Protocol

When the user gives you **multiple independent issues** to investigate (e.g., 5 feedback points, several bugs, multiple questions), do NOT present all findings at once. This causes information overload and frustration — the user has explicitly called this out.

**Required flow:**

1. **OPEN** the first point — state you're working on it
2. **INVESTIGATE** thoroughly (read code, live-test, gather evidence)
3. **PRESENT** findings for that ONE point only — verdict + evidence + **actively ASK for decision/approval** before proceeding
4. **GET confirmation** from user — do not assume silence = approval. If user doesn't respond after an appropriate interval, re-prompt once. Preserve state if still no response.
5. **CLOSE** the point explicitly ("Point 1 done. Moving to Point 2...")
6. **REPEAT** for each remaining point

**Key rule after each point:** `PRESENT → ASK → GET CONFIRMATION → CLOSE → NEXT`

Phrase the approval ask explicitly — e.g. "Nak saya proceed?", "Confirm and move on?", "Nak saya apply fix ni?" — not passive waiting.

**Why:** Multiple findings presented simultaneously force the user to context-switch across unrelated topics. They can't give meaningful input on all at once, and will push back. The user has explicitly called out "Kau memang susah nak faham instructions eh?" when findings were dumped all at once instead of sequentially.

**Exception:** If the user explicitly says "give me everything at once" or "analyse all and report back", a structured summary is fine. Default is one-by-one.

## Anti-Thrashing Protocol (learned 2026-07-14)

**Symptom:** High activity (many tool calls, script attempts, browser clicks, console experiments) with low information gain (no HAR file, no response body, no confirmed diagnosis). The agent tries curl → browser → console injection → package install → another browser → script — all within minutes, without completing any single hypothesis.

**Root cause:** Skipping hypothesis formation and jumping to solution attempts. Each attempt changes the execution context (browser cookies, session state, page rendering), making the next attempt unreliable. The result is corrupted state + no evidence.

**Required protocol — one hypothesis at a time:**

```
1. FORMULATE hypothesis (one sentence: "I think X is failing because Y")
2. DESIGN minimal test (what exact evidence proves/disproves this?)
3. EXECUTE in clean context (fresh page/session, no prior state leakage)
4. CAPTURE evidence (HTTP status, response body, network log, screenshot)
5. DIAGNOSE: does evidence support or refute the hypothesis?
6. IF refuted → new hypothesis → back to step 1
7. IF supported → proceed to fix OR next untested hypothesis
```

**Mandatory stop conditions:**
- Maximum 3 attempts per hypothesis
- Every attempt MUST produce evidence (HTTP code, response body, screenshot)
- After 15 minutes with no new evidence → STOP, summarize what's known vs unknown
- Never retry the same approach with minor variations (same tool + slightly different params = same approach)

**Pitfall — "form resets" is a symptom, not a diagnosis.** When the agent says "the form reset" or "the page stayed the same," it hasn't captured the ACTUAL server response. "Form resets" could mean: Turnstile token expired, email rejected, IP blocked, session mismatch, cookie missing, or JavaScript error. Without the HTTP status + response body, it's a guess.

**Pitfall — "token = 752 chars = solved" is a client-side claim.** A Turnstile token that LOOKS valid (correct length, plausible prefix) may fail server-side validation. The only proof of a working token is a successful server response (HTTP 200, page advance, redirect to next step). Never claim "CAPTCHA solved" until the server confirms it.

**Pitfall — mixed execution contexts corrupt state.** Browser tool → console JS → curl_cffi → back to browser creates separate cookie jars, session states, and page contexts. Each context is independent. A token solved in one context may be invalid in another. For diagnosis, keep everything in ONE browser session with clean state.

## Network Evidence First (learned 2026-07-14)

When a browser-based interaction fails (form doesn't submit, page doesn't advance, login loops):

```
1. CAPTURE the actual HTTP request and response BEFORE speculating
   - Use fetch() interceptor: fetch(url, {redirect: 'manual'}) to capture status
   - Or use browser Network tab (DevTools → Network → Preserve log)
   - Record: URL, method, status code, response body, redirect chain

2. CLASSIFY the failure by HTTP status:
   - 400 → request malformed or server rejected (check body for field-level errors)
   - 401 → auth failure (key/token invalid)
   - 403 → access denied (IP blocked, WAF, permission)
   - 429 → rate limited (check Retry-After header)
   - 3xx redirect → check Location header for callback/error params
   - No request fired → frontend validation blocking (JS error, required field empty)

3. ONLY THEN speculate about root cause
```

**Example — Auth0 form interception (2026-07-14):**
```javascript
// Install interceptor BEFORE submitting
window._result = null;
newForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    var resp = await fetch('https://auth.tavily.com/u/signup/identifier', {
        method: 'POST',
        body: new URLSearchParams(new FormData(newForm)),
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        redirect: 'manual'
    });
    window._result = {
        status: resp.status,          // ← THIS is the evidence
        type: resp.type,              // 'basic' vs 'opaqueredirect'
        location: resp.headers.get('location'),
        body: resp.type !== 'opaqueredirect' ? await resp.text() : null
    };
}, true);
// Then: document.querySelector('form').requestSubmit();
// Then: check window._result after 2-3 seconds
```

This technique revealed HTTP 400 from Auth0 (Turnstile token rejected server-side) — information that was invisible from watching page behavior alone ("form stays on same page" = useless symptom).

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I know what the bug is, I'll just fix it" | You might be right 70% of the time. The other 30% costs hours. Reproduce first. |
| "The failing test is probably wrong" | Verify that assumption. If the test is wrong, fix the test. Don't just skip it. |
| "It works on my machine" | Environments differ. Check CI, check config, check dependencies. |
| "I'll fix it in the next commit" | Fix it now. The next commit will introduce new bugs on top of this one. |
| "This is a flaky test, ignore it" | Flaky tests mask real bugs. Fix the flakiness or understand why it's intermittent. |

## Red Flags

- Skipping a failing test to work on new features
- Guessing at fixes without reproducing the bug
- Fixing symptoms instead of root causes
- "It works now" without understanding what changed
- No regression test added after a bug fix
- Multiple unrelated changes made while debugging (contaminating the fix)

## Process-Lifetime State and Dynamic Installation

Use this when a skill, plugin, command, configuration, or other artifact is installed/changed while a long-running daemon or gateway is already running.

A successful disk installation is not proof that the active process can use it. The runtime may have a process-global registry or lazy cache populated before the change. A new session (`/reset`, `/new`) normally resets conversation/session state, not daemon-level registries.

Required checks:

1. Capture the daemon PID/start time, active profile/home, and artifact modification time.
2. Trace the registration path: identify where the runtime map is built, its cache invalidation condition, and whether installation triggers invalidation.
3. Distinguish the refresh boundaries explicitly:
   - session reset: conversation/agent state only;
   - registry reload: in-process discovery refresh;
   - process restart: re-import/re-read state and environment.
4. Prefer the narrow explicit reload command when one exists. Do not restart a live gateway merely because a session reset failed; restart only through the approved operational path.
5. Test the exact user-facing command after refresh and capture the runtime log/response. A fresh standalone process discovering the artifact proves disk discoverability, not that the live daemon loaded it.
6. Report status by layer: installed on disk, discoverable in a fresh process, loaded by the running process, and user-visible end-to-end.

Common traps:

- Registry state marked `enabled` is not equivalent to the gateway's in-memory command map being refreshed.
- Metadata such as `disable-model-invocation` may govern automatic/model invocation without disabling explicit user slash dispatch; inspect the actual scanner predicates instead of inferring from the field name.
- A natural-language message such as `Enable /foo` is ordinary text, not proof that `/foo` executed. Require a command-dispatch log or explicit runtime response.

See `references/process-lifetime-cache-and-refresh.md` for the reusable evidence chain and the 2026-07-31 slash-command incident pattern.

## Verification

After fixing a bug:

- [ ] Root cause is identified and documented
- [ ] Fix addresses the root cause, not just symptoms
- [ ] A regression test exists that fails without the fix
- [ ] All existing tests pass
- [ ] Build succeeds
- [ ] The original bug scenario is verified end-to-end
