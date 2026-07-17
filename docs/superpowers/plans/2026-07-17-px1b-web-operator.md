# PX-1b Web Operator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved phone-first Web Operator: VPS-primary L1-L3 execution, action-bound human control, isolated authenticated sessions, and an optional secure Windows CUA worker, accepted through one clean 20/20 run.

**Architecture:** A project-owned `scripts/web_operator` package is the policy and orchestration boundary. Existing PX-1 search/extraction and live native Hermes browser tools are reached only through adapters; the Windows worker connects outbound to the VPS and independently verifies signed per-task grants. Phase 0 records the exact live APIs and paths before any runtime code or config is changed.

**Tech Stack:** Python 3.11+, stdlib `unittest`, `asyncio`, `sqlite3`, `http.server`, `ipaddress`, `urllib`, `pathlib`, `dataclasses`; PyYAML only if already present; `cryptography` only after explicit dependency approval; PowerShell 7 for thin Windows launch/status scripts; existing Hermes Agent runtime and native browser/CUA surfaces.

## Global Constraints

- Read `PRD.md` fully and read Section 7 twice before every implementation phase.
- Fetch current official documentation before setup, config, provider, model, browser, CUA, or service commands.
- Keep the live Hermes version; do not silently upgrade, deploy unreleased `main`, or patch live core freely.
- No paid browser cloud, paid CAPTCHA/bypass service, VPS upgrade, or new paid dependency.
- No implementation may modify `med_*`, `chain_*`, med JSON, medication memory, or existing medical automation.
- PX-1 search, hybrid extraction, and Research Expert are dependencies; compose them and do not rebuild healthy components.
- Depth=1 and max=3 children remain the hard agent default.
- Never print, log, transmit, commit, or place secret values in test fixtures.
- Do not expose public VNC, CDP, MCP, browser, CUA, or PC-worker ports.
- Every action approval expires after 900 seconds and is owner-, task-, action-, parameter-, state-, and nonce-bound.
- One L3 budget ends at 30 browser actions or 600 active seconds; one operation times out after 180 seconds; a retry does not reset either budget.
- Detailed redacted evidence expires after 14 days; raw frames have zero retention.
- Every phase stops for human review. Every `git add`, commit, push, deploy, service action, secret access, real message/file/portal/CUA action, package install, and config write requires its own explicit approval.
- The implementation agent must not execute a commit command merely because this plan contains a commit checkpoint. At each checkpoint, report the exact intended files and ask `Commit these changes?`.

## Plan Decomposition

This master plan contains seven independently gated phases. Phase 0 discovers live-only contracts. Phases 1-6 must not guess around missing Phase 0 evidence; if a required extension point is absent, stop that capability and report it as `UNTESTED` or `REJECTED` rather than changing Hermes core.

This document is the executable plan for Phase 0 and the locked task/acceptance roadmap
for Phases 1-6. Before starting each later phase, invoke `writing-plans` again and create
`docs/superpowers/plans/YYYY-MM-DD-px1b-phase-N-<name>.md` from the approved evidence of
the prior phase. That phase plan must provide exact discovered imports, signatures,
commands, complete implementation snippets, and expected test output. The roadmap below
defines required files, interfaces, tests, and gates; it is not permission to invent or
guess a live integration that Phase 0 did not validate.

## Planned File Structure

```text
scripts/web_operator/
  __init__.py              public package exports
  __main__.py              operator CLI for tests and approved admin use
  contracts.py             immutable enums/dataclasses and canonical serialization
  config.py                strict project-owned config loader
  storage.py               SQLite tasks, approvals, nonces, devices, session metadata
  policy.py                PRD Section 7.5 action taxonomy and fail-closed decisions
  approvals.py             issue/consume/expire/revoke action approvals
  network.py               URL normalization, DNS/redirect destination guard
  artifacts.py             ordinary artifacts, medical audit, retention purge
  coordinator.py           L0-L5 routing, queue, budgets, cancellation
  crypto.py                Ed25519/AES-GCM wrapper after dependency gate
  sessions.py              encrypted profile enrollment, lease, expiry, revocation
  files.py                 two-stage download quarantine and upload descriptors
  takeover.py              observation suspension and phone takeover state machine
  grants.py                signed PC task grants and device revocation
  pc_protocol.py           transport-neutral outbound worker message protocol
  adapters/
    __init__.py
    base.py                Executor protocol
    http.py                bounded L1 HTTP executor
    research.py            thin PX-1 L2 composition adapter
    native_browser.py      sole native Hermes L3 integration
    pc_worker.py           VPS side of L4 worker connection
  tests/
    support.py
    test_cli.py
    test_contracts.py
    test_config.py
    test_policy.py
    test_approvals.py
    test_network.py
    test_artifacts.py
    test_routing.py
    test_budgets.py
    test_sessions.py
    test_files.py
    test_takeover.py
    test_grants.py
    test_pc_protocol.py
    test_medical_mode.py
skills/experts/web-operator/
  SKILL.md
  README.md
  references/{routing,approvals,private-takeover,session-policy,medical-mode,artifact-contract}.md
  templates/handoff.md
tests/web_operator_fixture/
  __init__.py
  server.py
  static/{injection.html,unsafe-download.txt}
config/web-operator.yaml.template
config/web-operator-config.patch.template
windows/web-operator-worker.ps1
windows/web-operator-status.ps1
sync/deploy-web-operator.sh
docs/px1b-live-contracts.md
docs/px1b-acceptance-evidence.md
CONTINUATION-BRIEF-PX1B.md
```

---

## Phase 0 - Live Truth and PX-1 Gate

### Task 1: Verify PX-1 through the real phone path

**Files:**
- Create after the test: `docs/px1b-live-contracts.md`
- Modify after the test: `PROGRESS.md`

**Interfaces:**
- Consumes: allowlisted owner Telegram chat, deployed Research Expert, `search-cascade`, `hybrid-web`, research trace log.
- Produces: one sanitized evidence row proving trigger, search/extract use, trace creation, and owner-visible response.

- [ ] **Step 1: Prepare the exact non-sensitive test request**

Use this request from Amirul's allowlisted Telegram account:

```text
Research the current official Hermes Agent browser automation options. Use official sources, cite them, state what you could not verify, and create the normal research trace/artifact.
```

Do not send it until the human separately approves the real Telegram message.

- [ ] **Step 2: Ask approval for the external test message**

State the exact message, destination (owner's Telegram DM), expected DeepSeek/free-tool use, possible failure (skill may not trigger), and revert (none; it is one owner-only test message). Wait for explicit yes.

- [ ] **Step 3: Run the test and collect sanitized evidence**

Record only:

```markdown
| Check | Evidence |
|---|---|
| Telegram response | received / not received |
| Research Expert trigger | verified by skill/trace marker |
| Search backend | backend name only |
| Extract backend | backend name only |
| Trace | path + byte count, no contents containing private data |
| Artifact | path + expected files, no copied page content in Git |
```

- [ ] **Step 4: Apply the dependency gate**

Expected: all six checks pass. If any check fails, stop PX-1b and create a narrowly scoped repair note naming only the failed contract. Do not reinstall or reconfigure healthy PX-1 components.

- [ ] **Step 5: Update the tracker**

Add the date, result label, sanitized evidence paths, and any failed contract to `PROGRESS.md`. Do not claim PX-1b implementation has started.

- [ ] **Step 6: Commit checkpoint**

Report the changed tracker/evidence files and ask `Commit these changes?`. Commit only after a new explicit yes.

### Task 2: Inventory live Hermes, browser, trigger, gateway, and CUA contracts

**Files:**
- Create: `docs/px1b-live-contracts.md`
- Modify: `DECISIONS.md`
- Modify: `PROGRESS.md`

**Interfaces:**
- Consumes: read-only VPS/PC inspection and current official docs.
- Produces: a versioned contract ledger that every adapter task must use.

- [ ] **Step 1: Fetch current official pages**

Recheck at minimum:

```text
https://hermes-agent.nousresearch.com/docs/user-guide/features/browser
https://hermes-agent.nousresearch.com/docs/user-guide/features/computer-use
https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp
https://hermes-agent.nousresearch.com/docs/user-guide/security
https://hermes-agent.nousresearch.com/docs/user-guide/messaging/
https://github.com/NousResearch/hermes-agent/releases
```

Record access date and whether each fact is tagged-release or unreleased `main` behavior.

- [ ] **Step 2: Ask approval for credential-adjacent read-only VPS inspection**

The inspection reads version/config names and filesystem metadata but must not print `.env`, auth values, tokens, session contents, cookies, private keys, or message bodies. Explain commands and wait for explicit yes.

- [ ] **Step 3: Run a redacted VPS inventory**

Use read-only commands equivalent to:

```bash
hermes --version
python --version
node --version
systemctl --user is-active hermes-gateway
systemctl --user show hermes-gateway -p User -p ExecStart -p ActiveState
free -m
df -h
python -c "import importlib.util; print('yaml', bool(importlib.util.find_spec('yaml'))); print('cryptography', bool(importlib.util.find_spec('cryptography'))); print('pytest', bool(importlib.util.find_spec('pytest')))"
find ~/.hermes/hooks ~/.hermes/plugins ~/.hermes/skills/experts -maxdepth 3 -type f -printf '%p\n'
```

For config, query only named non-secret keys with `hermes config get` where supported. Never print the complete config.

- [ ] **Step 4: Inspect source signatures without changing source**

Locate and record exact paths/signatures for:

```text
native browser tool registration and callable functions
browser cancellation/cleanup and capture paths
skill discovery and agent:start hook payload
slash-command registration or supported alternative
gateway private API/plugin extension points
search-cascade and hybrid-web callable contracts
computer_use registration and driver invocation
```

Copy only signatures and non-sensitive schema facts into the ledger; do not copy runtime state.

- [ ] **Step 5: Ask approval for read-only PC/CUA inspection**

Inspect current CUA binary location/version, Windows account context, supported CLI/MCP modes, window identity behavior, local stop capability, and whether capture can be suspended. No driver execution or desktop control yet.

- [ ] **Step 6: Write the contract ledger**

Use this exact section structure in `docs/px1b-live-contracts.md`:

```markdown
# PX-1b Live Contracts
## Runtime Identity
## Native Browser Adapter Contract
## Research/Extract Adapter Contract
## Trigger and /browse Contract
## Gateway Control-Plane Contract
## CUA Driver Contract
## Dependency Inventory
## Filesystem and Service Account
## Resource Baseline
## Supported / Missing / Rejected Matrix
## Adapter Decisions
```

Every contract row must include source path, symbol/config key, observed version, label, and implication. Missing extension points are `REJECTED` blockers, not invitations to patch core.

- [ ] **Step 7: Validate the ledger**

Run:

```bash
rg -n "T[B]D|T[O]DO|F[I]XME|secret|token=|password=|api[_-]?key=" docs/px1b-live-contracts.md
```

Expected: no placeholders and no secret values. Legitimate policy words such as “secret” may appear only in explanatory prose; inspect every match.

- [ ] **Step 8: Commit checkpoint**

Report the exact ledger/tracker diff and ask `Commit these changes?` before staging.

---

## Phase 1 - Policy, Contracts, and Deterministic Fixtures

### Task 3: Create typed contracts and strict config

**Files:**
- Create: `scripts/web_operator/__init__.py`
- Create: `scripts/web_operator/contracts.py`
- Create: `scripts/web_operator/config.py`
- Create: `scripts/web_operator/tests/__init__.py`
- Create: `scripts/web_operator/tests/test_contracts.py`
- Create: `scripts/web_operator/tests/test_config.py`
- Create: `config/web-operator.yaml.template`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `ExecutionLevel`, `ActionClass`, `TaskState`, `ApprovalState`, `OutcomeLabel`, `SensitivityMode`, `TaskRequest`, `ActionIntent`, `ApprovalBinding`, `PolicyDecision`, `SessionIdentity`, `FileDescriptor`, `TaskGrant`, `OperatorResult`, `OperatorConfig`, `load_config(Path)`.

- [ ] **Step 1: Write failing serialization tests**

```python
import json
import unittest
from datetime import UTC, datetime

from scripts.web_operator.contracts import ActionClass, ActionIntent, canonical_json


class ContractTests(unittest.TestCase):
    def test_canonical_json_is_stable(self):
        action = ActionIntent(
            schema="web-operator/action/v1",
            task_id="task-1",
            action_id="action-1",
            owner_id="owner-1",
            action_class=ActionClass.EXTERNAL_SEND,
            target="https://example.com/send",
            parameters={"recipient": "fixture-owner", "content": "hello"},
            state_digest="a" * 64,
            created_at=datetime(2026, 7, 17, tzinfo=UTC),
        )
        encoded = canonical_json(action)
        self.assertEqual(encoded, canonical_json(action))
        self.assertEqual(json.loads(encoded)["action_class"], "external_send")
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python -m unittest scripts.web_operator.tests.test_contracts scripts.web_operator.tests.test_config -v
```

Expected: import failure because package/contracts/config do not exist.

- [ ] **Step 3: Implement immutable contracts and canonical JSON**

Use string enums and frozen dataclasses. `canonical_json()` must serialize enums and UTC datetimes, sort keys, and use compact separators. Every security-bound object includes a fixed schema string.

- [ ] **Step 4: Write strict config tests**

Tests must assert defaults: 30 actions, 600 active seconds, 180 operation seconds, 900 approval seconds, 14 retention days, private destinations denied, raw-frame retention 0, fixture mode false, production concurrency 1. Unknown keys and `fixture_mode: true` in production validation must raise `ConfigError`.

- [ ] **Step 5: Implement config and template**

If Phase 0 confirms PyYAML, use `yaml.safe_load`; otherwise use JSON syntax in the `.yaml.template` only after renaming it to `.json.template` in this task. Do not add a dependency to preserve the filename.

- [ ] **Step 6: Add runtime-state exclusions**

Add these exact patterns to `.gitignore`:

```gitignore
# PX-1b Web Operator runtime credentials/state
web-operator/state/
web-operator/profiles/
web-operator/quarantine/
web-operator/artifacts/
web-operator/takeover/
web-operator/medical-audit/
web-operator/keys/
```

- [ ] **Step 7: Run tests and verify GREEN**

Run the full package discovery command:

```bash
python -m unittest discover -s scripts/web_operator/tests -p "test_*.py" -v
```

Expected: all contract/config tests pass.

- [ ] **Step 8: Commit checkpoint**

Ask before staging these new package/config/test files.

### Task 4: Implement transactional state, policy, and approvals

**Files:**
- Create: `scripts/web_operator/storage.py`
- Create: `scripts/web_operator/policy.py`
- Create: `scripts/web_operator/approvals.py`
- Create: `scripts/web_operator/tests/support.py`
- Create: `scripts/web_operator/tests/test_policy.py`
- Create: `scripts/web_operator/tests/test_approvals.py`

**Interfaces:**
- Consumes: contracts/config from Task 3.
- Produces: `StateStore`, `PolicyEngine.classify_action()`, `PolicyEngine.authorize()`, `ApprovalStore.issue()`, `consume()`, `expire()`, `revoke_task()`.

- [ ] **Step 1: Write failing action-taxonomy tests**

Cover every PRD Section 7.5 class: external send, public post, delete/overwrite, infrastructure/security change, shell/elevation/install, secret exposure, purchase/paid service, calendar create/update/delete, group join/reply, expensive model switch, upload, download, form personal-data entry, and form submission.

Expected decisions:

```text
ALLOW: public read/navigation within an approved task
PAUSE: personal data, submission, exact send/post, transfer, purchase, calendar, group action
DENY: unknown class, secret disclosure, infrastructure/security, shell/elevation/install, automatic model switch, bulk/irreversible deletion
```

- [ ] **Step 2: Write failing approval lifecycle tests**

Test exact 900-second expiry, atomic one-time consume, wrong owner, wrong task, wrong action, changed parameter digest, changed state digest, replay, task revoke, and scheduled-task non-reuse.

- [ ] **Step 3: Run targeted tests and verify RED**

```bash
python -m unittest scripts.web_operator.tests.test_policy scripts.web_operator.tests.test_approvals -v
```

- [ ] **Step 4: Implement SQLite schema and transactions**

Tables must be limited to metadata:

```sql
CREATE TABLE tasks(task_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE approvals(approval_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, owner_id TEXT NOT NULL, binding_digest TEXT NOT NULL, state TEXT NOT NULL, expires_at TEXT NOT NULL, consumed_at TEXT);
CREATE TABLE nonces(nonce TEXT PRIMARY KEY, scope TEXT NOT NULL, expires_at TEXT NOT NULL);
CREATE TABLE devices(device_id TEXT PRIMARY KEY, public_key BLOB NOT NULL, fingerprint TEXT NOT NULL, revoked_at TEXT);
CREATE TABLE sessions(identity_digest TEXT PRIMARY KEY, metadata_json TEXT NOT NULL, expires_at TEXT, revoked_at TEXT);
```

Use `BEGIN IMMEDIATE` for approval consumption and nonce insertion.

- [ ] **Step 5: Implement policy and approval digesting**

The binding digest must hash canonical action JSON including task, owner, target, parameters, state digest, and action class. A plain chat “yes” is accepted only when the messaging adapter maps it to one outstanding owner/task/action ID.

- [ ] **Step 6: Run package tests and verify GREEN**

```bash
python -m unittest discover -s scripts/web_operator/tests -p "test_*.py" -v
```

- [ ] **Step 7: Commit checkpoint**

Ask before staging policy/state/approval files.

### Task 5: Implement destination guard and evidence sinks

**Files:**
- Create: `scripts/web_operator/network.py`
- Create: `scripts/web_operator/artifacts.py`
- Create: `scripts/web_operator/tests/test_network.py`
- Create: `scripts/web_operator/tests/test_artifacts.py`

**Interfaces:**
- Produces: `DestinationGuard.validate_url()`, `validate_redirect()`, `normalize_for_artifact()`, `ArtifactSink.record_event()`, `finalize()`, `purge_expired()`, `MedicalAuditSink`.

- [ ] **Step 1: Write failing network tests**

Test rejection of `file:`, userinfo hosts, loopback, RFC1918, link-local, multicast, reserved, IPv6 loopback, metadata addresses, router/admin hosts, and a public-to-private redirect. Mock `socket.getaddrinfo`; do not access the internet.

- [ ] **Step 2: Write failing artifact tests**

Assert query strings, fragments, tokens, account IDs, entered values, cookies, and headers never appear. Assert raw-frame deletion is immediate, ordinary detail expires at 14 days, and medical audit contains only owner/task/origin/action/approval/time/outcome/deletion fields.

- [ ] **Step 3: Run targeted tests and verify RED**

```bash
python -m unittest scripts.web_operator.tests.test_network scripts.web_operator.tests.test_artifacts -v
```

- [ ] **Step 4: Implement network validation**

Use `urllib.parse`, `socket.getaddrinfo`, and `ipaddress.ip_address`. Validate every resolved address and every redirect. Return a resolved immutable target; adapters must not connect to a host that differs from the validated target without revalidation.

- [ ] **Step 5: Implement artifact invariants**

Store JSONL metadata and selected already-redacted evidence references. If a redaction invariant fails, raise `SensitiveEvidenceError`, quarantine the artifact directory, and signal a project stop.

- [ ] **Step 6: Verify GREEN and run placeholder/secret scan**

```bash
python -m unittest discover -s scripts/web_operator/tests -p "test_*.py" -v
rg -n "T[B]D|T[O]DO|F[I]XME|password=|token=|api[_-]?key=" scripts/web_operator config/web-operator.yaml.template
```

- [ ] **Step 7: Commit checkpoint**

Ask before staging network/artifact changes.

### Task 6: Build deterministic fixture server

**Files:**
- Create: `tests/web_operator_fixture/__init__.py`
- Create: `tests/web_operator_fixture/server.py`
- Create: `tests/web_operator_fixture/static/injection.html`
- Create: `tests/web_operator_fixture/static/unsafe-download.txt`
- Create: `scripts/web_operator/tests/test_fixture.py`

**Interfaces:**
- Produces: loopback-only `FixtureServer` with deterministic endpoints for all controlled acceptance actions.

- [ ] **Step 1: Write the failing fixture smoke test**

Start `FixtureServer` on `127.0.0.1` with port 0, fetch `/health` and `/form`, and assert synthetic-only responses. Assert binding to `0.0.0.0` raises `FixtureSafetyError`.

- [ ] **Step 2: Implement the server with stdlib only**

Use `ThreadingHTTPServer`. Implement routes for static, JS state, form/review mutation, message, checkout drift, calendar, group, reversible delete, safe/substituted/unsafe download, upload descriptor, prompt injection, synthetic CAPTCHA, login/OTP, medical synthetic record, two-account sessions, redirects, hang, and one-time transient failure.

- [ ] **Step 3: Add fixture-mode isolation**

Production config validation must reject fixture mode. Tests inject a dedicated fixture destination policy; production destination guard remains fail-closed for loopback.

- [ ] **Step 4: Run fixture and package tests**

```bash
python -m unittest scripts.web_operator.tests.test_fixture -v
python -m unittest discover -s scripts/web_operator/tests -p "test_*.py" -v
```

- [ ] **Step 5: Commit checkpoint**

Ask before staging fixture files.

---

## Phase 2 - VPS Public L1-L3 Core

### Task 7: Implement executor protocol, coordinator, and budgets

**Files:**
- Create: `scripts/web_operator/__main__.py`
- Create: `scripts/web_operator/adapters/__init__.py`
- Create: `scripts/web_operator/adapters/base.py`
- Create: `scripts/web_operator/coordinator.py`
- Create: `scripts/web_operator/tests/test_cli.py`
- Create: `scripts/web_operator/tests/test_routing.py`
- Create: `scripts/web_operator/tests/test_budgets.py`

**Interfaces:**
- Produces: `Executor` protocol and `WebOperator.submit()`, `resume()`, `cancel()`, `status()`.

- [ ] **Step 1: Write failing fake-executor routing tests**

Test L1/L2 first, automatic L3 on empty/interactive result, logged escalation reason, L4 suggestion only on concrete desktop limitation, L0 pause/resume without new budget, and terminal L5 handoff.

- [ ] **Step 2: Write failing budget tests with a fake clock**

Test 30th action allowed and 31st blocked, 600 active seconds, approval wait excluded from active time, 900-second approval expiry still advances, 180-second operation cancellation, and retry staying in original budget.

- [ ] **Step 3: Implement protocol and coordinator minimally**

```python
class Executor(Protocol):
    @property
    def level(self) -> ExecutionLevel: ...
    def capabilities(self) -> frozenset[str]: ...
    async def execute(self, context: TaskContext, step: ExecutionStep) -> StepResult: ...
    async def cancel(self, task_id: str) -> None: ...
```

No adapter may call another adapter directly; all transitions go through `WebOperator` so policy, budget, and artifacts cannot be bypassed.

- [ ] **Step 4: Implement the bounded CLI**

`python -m scripts.web_operator` supports only `status`, `cancel <task-id>`,
`purge-expired`, and fixture-only `run --config <path> --request <json>`. It must refuse
fixture mode unless the strict test config enables it and must never accept secret values,
raw approval grants, arbitrary shell, or arbitrary Python expressions.

- [ ] **Step 5: Write and run CLI tests**

Test unknown command, fixture refusal, status, cancel, purge, and sanitized errors. Then
run targeted and full tests:

```bash
python -m unittest scripts.web_operator.tests.test_routing scripts.web_operator.tests.test_budgets scripts.web_operator.tests.test_cli -v
python -m unittest discover -s scripts/web_operator/tests -p "test_*.py" -v
```

- [ ] **Step 6: Commit checkpoint**

Ask before staging coordinator files.

### Task 8: Implement L1 and live-discovered L2/L3 adapters

**Files:**
- Create: `scripts/web_operator/adapters/http.py`
- Create: `scripts/web_operator/adapters/research.py`
- Create: `scripts/web_operator/adapters/native_browser.py`
- Create: `scripts/web_operator/tests/test_http_adapter.py`
- Create: `scripts/web_operator/tests/test_live_adapter_contracts.py`

**Interfaces:**
- Consumes: exact symbols in `docs/px1b-live-contracts.md`.
- Produces: L1 bounded fetch, L2 PX-1 composition, L3 native browser translation.

- [ ] **Step 1: Write failing L1 tests**

Mock HTTP transport. Assert GET/HEAD only, byte/time/redirect limits, destination validation before every request, no credentials, no file write, and response normalization.

- [ ] **Step 2: Implement L1 with injectable transport**

Use stdlib by default. Add `curl-impersonate` only if a frozen fixture demonstrates a required capability and its installation/use receives separate approval.

- [ ] **Step 3: Generate contract tests from the Phase 0 ledger**

For every L2/L3 symbol recorded in the ledger, write an import/signature test. The test must fail with a clear `LiveContractMismatch` when version/path/signature differs. Do not use dynamic best-effort symbol guessing.

- [ ] **Step 4: Implement thin L2 adapter**

Call existing search/extract tools exactly as discovered. Return normalized source/result metadata. Do not copy backend logic or key rotation.

- [ ] **Step 5: Implement sole native L3 adapter**

Map generic steps to the exact native browser calls. Count every call listed by the design as one action. Enforce observation suspension before snapshot/vision/console/CDP. On cancel/expiry/resource pressure, invoke the exact discovered cleanup path.

- [ ] **Step 6: Run unit and read-only contract tests**

```bash
python -m unittest scripts.web_operator.tests.test_http_adapter scripts.web_operator.tests.test_live_adapter_contracts -v
```

Expected: unit tests pass locally; live contract tests pass only in the approved VPS test environment.

- [ ] **Step 7: Commit checkpoint**

Ask before staging adapters.

### Task 9: Package Web Operator skill and trigger integration

**Files:**
- Create: `skills/experts/web-operator/SKILL.md`
- Create: `skills/experts/web-operator/README.md`
- Create: `skills/experts/web-operator/references/routing.md`
- Create: `skills/experts/web-operator/references/approvals.md`
- Create: `skills/experts/web-operator/references/private-takeover.md`
- Create: `skills/experts/web-operator/references/session-policy.md`
- Create: `skills/experts/web-operator/references/medical-mode.md`
- Create: `skills/experts/web-operator/references/artifact-contract.md`
- Create: `skills/experts/web-operator/templates/handoff.md`
- Create: `config/web-operator-config.patch.template`
- Modify: `skills/experts/research-expert/SKILL.md`
- Create or modify only as discovered: local durable copy of the live trigger hook.

**Interfaces:**
- Produces: narrow natural-language trigger plus `/browse` equivalent from Phase 0; bounded Research Expert handoff.

- [ ] **Step 1: Write skill contract checks**

Create a small unittest that parses frontmatter/required phrases and asserts the skill requires policy/coordinator use, never accepts secrets in chat, never treats `/browse` as approval, and does not trigger for conceptual research/static extraction.

- [ ] **Step 2: Write the skill pack**

Positive trigger examples: click through a site, fill a form, log in and navigate, approved download/upload, use a named Windows app. Negative examples: research a topic, summarize a static URL, medical advice, coding question, search/find sources.

- [ ] **Step 3: Add one narrow Research Expert handoff rule**

Research Expert may request bounded interactive navigation when L2 extraction proves insufficient. It consumes the returned material as untrusted evidence and retains no external-action authority.

- [ ] **Step 4: Integrate the discovered trigger/command path**

Use the exact hook/command mechanism in the live ledger. If `/browse` cannot be registered safely, document and test the supported explicit phrase instead; do not patch Hermes command routing.

- [ ] **Step 5: Write the minimal live config patch template**

Include only keys verified in the live ledger. Keep private destinations disabled, remove
the stale VPS Windows CUA path if the approved live diff requires it, and do not raise
global gateway concurrency to match browser concurrency. The template contains env-var
names and file paths only, never secret values.

- [ ] **Step 6: Run trigger and config-diff tests**

Test at least five positive and five negative utterances, including no collision with Research Expert and no medical-system trigger.

- [ ] **Step 7: Ask approval before deployment and gateway reload**

Show exact copied files, config/hook diff, downtime, failure mode, and rollback. Deploy/reload only after explicit yes, then verify both messaging platforms reconnect.

- [ ] **Step 8: Commit checkpoint**

Ask before staging skill/hook/research changes.

### Task 10: Benchmark measured-safe concurrency

**Files:**
- Create: `scripts/web_operator/tests/benchmark_concurrency.py`
- Modify after evidence: `config/web-operator.yaml.template`
- Modify: `docs/px1b-live-contracts.md`
- Modify: `PROGRESS.md`

**Interfaces:**
- Produces: production L3 concurrency of 1, 2, or 3 based on the locked criteria.

- [ ] **Step 1: Implement benchmark harness**

Run the same frozen L3 fixture workload for 10 minutes at each level. Sample gateway state, Telegram and WhatsApp health response latency, available RAM, swap growth, process exit/OOM, and task budgets.

- [ ] **Step 2: Ask approval for live browser load and owner-only health messages**

Explain resource risk and that testing stops immediately on gateway degradation.

- [ ] **Step 3: Run level 1, then conditionally 2 and 3**

Do not run the next level unless the prior level passes. Stop browser workers before the gateway at every failure.

- [ ] **Step 4: Lock measured production concurrency**

Write evidence and set `production_l3_concurrency` to the highest passing level. If level 1 fails, stop Phase 2 as `REJECTED`; no paid upgrade is allowed.

- [ ] **Step 5: Commit checkpoint**

Ask before staging benchmark evidence/config.

---

## Phase 3 - Authentication, Files, Actions, and Medical Mode

### Task 11: Add approved cryptography dependency and encrypted sessions

**Files:**
- Create: `scripts/web_operator/crypto.py`
- Create: `scripts/web_operator/sessions.py`
- Create: `scripts/web_operator/tests/test_crypto.py`
- Create: `scripts/web_operator/tests/test_sessions.py`
- Create after Phase 0 confirms environment convention: `scripts/web_operator/requirements.txt`

**Interfaces:**
- Produces: `HostKeyStore`, Ed25519 sign/verify, AES-GCM encrypt/decrypt, `SessionStore.enroll/acquire/release/revoke`.

- [ ] **Step 1: Ask approval to add `cryptography` if absent**

Provide exact pinned version selected from the live Python/platform compatibility check, install target (Hermes venv and Windows worker environment), free/open-source status, wheel availability, rollback, and disk impact. Wait for explicit yes.

- [ ] **Step 2: Write failing crypto tests**

Test signature verification, tamper rejection, AES-GCM round trip, wrong AAD rejection, unique nonces, key file mode/ACL validation abstraction, and fingerprint stability. Test keys are generated in temporary directories.

- [ ] **Step 3: Implement cryptography wrappers**

Use Ed25519, AES-GCM, canonical JSON, random 96-bit AES-GCM nonces, and AAD containing schema/task/device/profile/action. Never implement custom ciphers.

- [ ] **Step 4: Write failing session tests**

Test `(site, account, profile, execution_device)` isolation, one-time/persistent mode, expiry, exclusive lease, no financial persistence, revoke deleting encrypted blob and derived cache, and no automatic device copy.

- [ ] **Step 5: Implement encrypted session store**

Store metadata in SQLite and encrypted browser profile/storage blob under runtime state. The host-local data key is readable only by the service account. A session lease must be exclusive and released on cancellation/disconnect.

- [ ] **Step 6: Run tests and scan artifacts**

```bash
python -m unittest scripts.web_operator.tests.test_crypto scripts.web_operator.tests.test_sessions -v
rg -n "BEGIN .*PRIVATE KEY|password|otp|cookie" scripts/web_operator/tests
```

Expected: tests pass; matches are policy/test labels, never values.

- [ ] **Step 7: Commit checkpoint**

Ask before staging dependency/session files.

### Task 12: Implement two-stage files and action revalidation

**Files:**
- Create: `scripts/web_operator/files.py`
- Create: `scripts/web_operator/tests/test_files.py`
- Extend: `scripts/web_operator/tests/test_policy.py`

**Interfaces:**
- Produces: `QuarantineStore.receive/inspect/release`, `describe_existing_upload`, transaction/form/message/calendar/group mutation revalidation.

- [ ] **Step 1: Write failing quarantine tests**

Test first approval before receipt, actual SHA-256/type/size calculation, expected/actual mismatch, unsafe fixture rejection, second approval before release, and upload hash/destination/account/purpose binding.

- [ ] **Step 2: Implement quarantine**

Write into a non-executable runtime directory with restrictive permissions and randomized internal filename. Trust neither extension nor remote content type. Use the Phase 0-discovered local type scanner; if none is available without a new dependency, support only an explicit safe text/PDF/CSV allowlist and mark other types rejected.

- [ ] **Step 3: Add action state-drift tests**

Cover changed form content, recipient, attachment hash, seller, item, quantity, currency, total, address, subscription flag, calendar fields/invitees, group/audience, and deletion target.

- [ ] **Step 4: Run tests**

```bash
python -m unittest scripts.web_operator.tests.test_files scripts.web_operator.tests.test_policy -v
```

- [ ] **Step 5: Commit checkpoint**

Ask before staging file/action changes.

### Task 13: Implement private takeover and high-sensitivity medical mode

**Files:**
- Create: `scripts/web_operator/takeover.py`
- Create: `scripts/web_operator/tests/test_takeover.py`
- Create: `scripts/web_operator/tests/test_medical_mode.py`

**Interfaces:**
- Produces: `ObservationGate.suspend/resume/assert_suspended`, `TakeoverController.grant/return_control/disconnect/expire`, medical metadata-only audit.

- [ ] **Step 1: Write failing observation-gate tests**

Register fake screenshot, video, DOM, accessibility, clipboard, keystroke, log, and queued-observation producers. During suspension, every producer must reject or emit no payload.

- [ ] **Step 2: Write canary leak test**

Enter synthetic canaries during takeover and assert they are absent from model-input sink, queue, captures, logs, artifacts, SQLite metadata, and returned result.

- [ ] **Step 3: Implement takeover state machine**

States: `REQUESTED -> SUSPENDING -> EXCLUSIVE -> RETURNING -> CLOSED`, with `DISCONNECTED` and `EXPIRED` terminal paths. Disconnect freezes input and capture; reconnection requires owner reauthentication before expiry.

- [ ] **Step 4: Integrate the Phase 0-discovered phone path**

The path must be private and authenticated, have no public listener, and control only the active task/profile. If the native browser cannot prove complete observation suspension, mark private takeover `REJECTED` and stop authenticated VPS acceptance.

- [ ] **Step 5: Implement medical audit exception**

Only encrypted metadata fields from the design are permitted, with 14-day purge. Test that medical values/page text/files/screenshots cannot be passed to ordinary artifacts, memory, Research export, or med state paths.

- [ ] **Step 6: Run tests**

```bash
python -m unittest scripts.web_operator.tests.test_takeover scripts.web_operator.tests.test_medical_mode -v
```

- [ ] **Step 7: Commit checkpoint**

Ask before staging takeover/medical files.

---

## Phase 4 - Secure Outbound Windows CUA Worker

### Task 14: Implement signed grants and transport-neutral protocol

**Files:**
- Create: `scripts/web_operator/grants.py`
- Create: `scripts/web_operator/pc_protocol.py`
- Create: `scripts/web_operator/tests/test_grants.py`
- Create: `scripts/web_operator/tests/test_pc_protocol.py`

**Interfaces:**
- Produces: `GrantIssuer.issue/verify/revoke_device`; protocol messages `hello`, `challenge`, `authenticate`, `heartbeat`, `availability`, `grant`, `grant-accepted`, `grant-rejected`, `step-event`, `result`, `stop`, `revoke`.

- [ ] **Step 1: Write failing grant tests**

Test device enrollment fingerprint, issuer/worker double verification, unique nonce, replay, expiry, wrong owner/device/app/window/action/parameter/state, revoked device, signed result tampering, and scheduled-task fresh grant.

- [ ] **Step 2: Implement grants using Task 11 crypto**

Canonical signed payload fields are fixed by the design. Nonce insertion is atomic in SQLite. A grant authorizes no shell command and no app/window outside its exact scope.

- [ ] **Step 3: Write protocol state-machine tests**

Test outbound worker authentication, heartbeat timeout, network loss, control-plane loss, stop, revoke, wrong sequence, duplicate message, and result signature validation.

- [ ] **Step 4: Implement transport-neutral protocol**

Keep socket/WebSocket details outside protocol parsing. Enforce size limits and reject unknown message types/fields.

- [ ] **Step 5: Run tests**

```bash
python -m unittest scripts.web_operator.tests.test_grants scripts.web_operator.tests.test_pc_protocol -v
```

- [ ] **Step 6: Commit checkpoint**

Ask before staging grant/protocol files.

### Task 15: Implement the VPS connection adapter and thin Windows worker

**Files:**
- Create: `scripts/web_operator/adapters/pc_worker.py`
- Create: `windows/web-operator-worker.ps1`
- Create: `windows/web-operator-status.ps1`
- Create: `scripts/web_operator/tests/test_pc_worker.py`

**Interfaces:**
- Consumes: Phase 0 gateway extension and CUA contracts.
- Produces: outbound-only enrolled worker, availability, grant delivery, signed results, local/phone stop.

- [ ] **Step 1: Write failing fake-transport worker tests**

Test no inbound listener, availability state, approved named app/window, wrong window stop, privilege/sensitive-content stop, network loss releasing input, visible indicator assertion, and local kill switch not remotely suppressible.

- [ ] **Step 2: Implement the approved outbound transport**

Use only the exact private gateway extension in the live ledger. If no safe extension exists without a public port or core patch, mark L4 `REJECTED` and stop this task.

- [ ] **Step 3: Implement PowerShell launch/status wrappers**

Both scripts use `Set-StrictMode -Version Latest` and `$ErrorActionPreference = 'Stop'`. Worker script supports only `Enroll`, `Run`, and `Stop`; status prints device fingerprint, connectivity, task ID, approved app/window, expiry, indicator, and stop instructions. It never prints keys, grants, sessions, page contents, or secrets.

- [ ] **Step 4: Integrate exact CUA contract**

The worker validates the grant locally before invoking CUA and validates stable app/window identity before every action. It must stop on protected surfaces, elevation, unrelated app/file, secret manager, banking app, or ambiguous screen.

- [ ] **Step 5: Ask approval for local enrollment and controlled CUA test**

Explain local key creation, fingerprint, outbound connection, named benign app, exact actions, visible indicator, kill switch, and rollback. Wait for explicit yes.

- [ ] **Step 6: Run deterministic CUA tests**

Use a benign local fixture app/window. Verify unknown/replayed grant rejection, expiry, disconnect, wrong window, kill switch, and one approved named-app task.

- [ ] **Step 7: Commit checkpoint**

Ask before staging PC-worker files/evidence.

### Task 16: Validate offline-PC and optional historical-driver comparison

**Files:**
- Create: `scripts/web_operator/tests/test_pc_availability.py`
- Modify: `PROGRESS.md`

**Interfaces:**
- Produces: `online -> fresh approval -> run`; `offline -> turn on/retry, postpone, schedule, cancel`; no Wake-on-LAN.

- [ ] **Step 1: Write availability tests**

Assert schedule/postpone stores intent only, discards grants/approvals, revalidates material state, and asks fresh approval at execution.

- [ ] **Step 2: Run one controlled offline/online drill**

Ask approval before stopping/starting any local worker. Do not stop unrelated services. Verify no Wake-on-LAN packet or router configuration is used.

- [ ] **Step 3: Optionally compare Qwen/Sakana historical scripts**

Only after the supported CUA path passes, run one non-production comparison with explicit approval. Record reusable technique only; do not route production through the old scripts or modify them unless a separate reviewed task is approved.

- [ ] **Step 4: Commit checkpoint**

Ask before staging availability evidence.

---

## Phase 5 - Integrated Hardening, Deployment, and Operations

### Task 17: Complete adversarial and failure drills

**Files:**
- Create: `scripts/web_operator/tests/test_integration.py`
- Create: `docs/px1b-acceptance-evidence.md`

**Interfaces:**
- Produces: deterministic evidence for prompt injection, CAPTCHA/L5, mutation, session isolation, failures, cleanup, and project-stop conditions.

- [ ] **Step 1: Write integrated fixture tests**

Cover prompt content requesting cookie disclosure/policy bypass, public-to-private redirect, CAPTCHA minimal takeover then resume, hard-wall terminal L5, browser crash one retry, session corruption quarantine, partial form/message/checkout unsent state, and medical non-retention.

- [ ] **Step 2: Write project-stop tests**

Synthetic secret in an artifact, unauthorized external action, unexpected med-state write attempt, and unredacted personal value must stop the coordinator and prevent further actions.

- [ ] **Step 3: Run all deterministic tests**

```bash
python -m unittest discover -s scripts/web_operator/tests -p "test_*.py" -v
```

Expected: zero failures/errors/skips.

- [ ] **Step 4: Populate evidence template**

For each frozen case record build/commit, config fingerprint, fixture/real classification, preconditions, expected result, actual result, label, retries, redacted evidence path, and reviewer.

- [ ] **Step 5: Commit checkpoint**

Ask before staging integration tests/template.

### Task 18: Harden sync, deployment, and runtime cleanup

**Files:**
- Modify: `sync/pull-vps-to-wsl2.sh`
- Modify: `sync/drift-check.sh`
- Modify: `sync/SYNC-MECHANISM.md`
- Create: `sync/deploy-web-operator.sh`
- Modify: `.gitignore`
- Modify: `RUNBOOK.md`

**Interfaces:**
- Produces: dry-run deployment, source/runtime separation, retention purge operations, no runtime credential sync.

- [ ] **Step 1: Write shell safety checks**

Use `bash -n` plus a dry-run test tree. Assert deployment excludes `.env`, auth, keys, sessions, DBs, profiles, quarantine, artifacts, takeover, medical audit, captures, logs, caches, venv, and node modules.

- [ ] **Step 2: Implement deploy script dry-run by default**

Require explicit `--apply`, host, user, source root, destination root, and expected source hash. Copy only approved source/config templates. Never restart services automatically.

- [ ] **Step 3: Update sync exclusions and drift checks**

Drift checks compare source hashes and non-secret config keys only. Encrypted profiles remain excluded because encryption does not make credentials safe to sync.

- [ ] **Step 4: Update runbook**

Document status, queue, purge, session revoke, device revoke, local/phone stop, offline-PC choices, fixture prohibition, rollback, and incident response. Remove no existing unrelated runbook content in this task.

- [ ] **Step 5: Verify scripts**

```bash
bash -n sync/deploy-web-operator.sh sync/pull-vps-to-wsl2.sh sync/drift-check.sh
git diff --check
```

- [ ] **Step 6: Ask deployment approval**

Show dry-run diff, exact destination paths, config delta, dependencies, expected downtime, rollback, and test commands. Wait for explicit yes before `--apply`, config writes, or gateway restart.

- [ ] **Step 7: Verify deployment and rollback readiness**

After approved deployment/reload, verify gateway active, both platforms connected, native adapters import, state permissions, no secret paths in Git/source sync, and rollback package available.

- [ ] **Step 8: Commit checkpoint**

Ask before staging operational files.

---

## Phase 6 - One Clean 20/20 Release Candidate

### Task 19: Run controlled acceptance cases

**Files:**
- Modify: `docs/px1b-acceptance-evidence.md`
- Modify: `PROGRESS.md`

**Interfaces:**
- Produces: cases 4-19 deterministic pass evidence before real phone flows.

- [ ] **Step 1: Freeze candidate identity**

Record source commit, deployed file hashes, live Hermes version, operator config hash, dependency versions, PC device fingerprint, production concurrency, and fixture version. Any source/config change invalidates the run and requires restart from case 1.

- [ ] **Step 2: Run full unit/integration suite**

```bash
python -m unittest discover -s scripts/web_operator/tests -p "test_*.py" -v
```

Expected: zero failures/errors/skips.

- [ ] **Step 3: Run controlled cases in frozen order**

Exercise static L1/L2, JS L3, route trace, destination/prompt injection, concurrency/budgets/health, personal form double gate, message mutation, file two-stage gate, takeover canary, financial-local boundary, sessions/revoke, synthetic medical mode, CAPTCHA/L5, grants/fail-safe, and named-app boundaries.

- [ ] **Step 4: Apply no-waiver rule**

Any failed, skipped, partial, or provisional case fails the release candidate. Fix in the relevant earlier phase, obtain required commit/deploy approvals, and rerun all 20 from case 1.

### Task 20: Run real owner phone flows and finalize handover

**Files:**
- Modify: `docs/px1b-acceptance-evidence.md`
- Modify: `PROGRESS.md`
- Modify: `DECISIONS.md`
- Modify: `RUNBOOK.md`
- Create: `CONTINUATION-BRIEF-PX1B.md`

**Interfaces:**
- Produces: frozen cases 1-3 and 20 plus real low-risk login, isolated medical portal, and named-app evidence; final 20/20 decision.

- [ ] **Step 1: Ask separate approvals for each real flow**

Real flows are owner-only, minimum-data, reversible/no-op where possible. Never send to a third party, place a real order, alter a medical record, or transfer a real sensitive file. Obtain fresh approval immediately before Telegram, WhatsApp, login/takeover, medical portal, and CUA flows.

- [ ] **Step 2: Run case 1 Telegram Research Expert E2E again**

Use the unchanged Phase 0 request so the final suite is reproducible.

- [ ] **Step 3: Run WhatsApp and Telegram Web Operator triggers**

Use the same benign public multi-step target and compare task IDs, routing, results, and redacted artifacts.

- [ ] **Step 4: Run one low-risk ordinary authenticated flow**

Use private takeover with synthetic canary verification and a separately enrolled non-financial site/account. Perform no external state change unless a controlled no-op action is available and freshly approved.

- [ ] **Step 5: Run one isolated private medical portal read-only flow**

Use minimum necessary data. Verify no screenshots/page values/medical details enter normal artifacts, memory, Research export, Obsidian, or med paths. Verify metadata audit purge schedule.

- [ ] **Step 6: Run one named-app CUA flow and offline-PC branch**

Verify PC-online execution, exact app/window scope, local indicator, kill switch, and one offline choice (`Postpone` or `Schedule`) followed by fresh approval. Perform no external send or privileged action.

- [ ] **Step 7: Verify all 20 cases and retention/security invariants**

Count exactly 20 PASS entries, zero waiver/skip/partial entries, no secret canary matches, no med-state diff, gateway active, both platforms connected, and purge jobs configured but not silently deployed without prior approval.

- [ ] **Step 8: Update handover documents**

Record actual commands, paths, versions, status/stop/revoke/recovery procedures, residual risks, rejected capabilities, and Overhaul V2 issues. Do not call a failed capability complete.

- [ ] **Step 9: Final commit and push checkpoint**

Show `git status`, `git diff`, `git log --oneline -10`, verification output, and exact intended files. Ask `Commit these changes?`. After an explicit yes, commit. Ask separately before push unless the same user response explicitly authorizes both operations for this final unit.

---

## Plan Self-Review Checklist

### Design Coverage Matrix

| Locked design requirement | Implemented/verified by |
|---|---|
| Phone-first single task across WhatsApp/Telegram | Tasks 7, 9, 20 |
| L0-L5 semantics and Research composition | Tasks 4, 7-9, 17 |
| Native browser first; no guessed live API | Tasks 2, 8 |
| 30 actions / 600 active seconds / 180-second operation | Tasks 7, 10, 19 |
| Measured concurrency 1-3 with gateway protection | Task 10 |
| Owner/action/state-bound approvals and scheduling reapproval | Tasks 4, 12, 16 |
| Full PRD Section 7.5 taxonomy | Tasks 4, 12, 17 |
| SSRF, redirects, prompt injection, L1-L4 destination policy | Tasks 5, 8, 17 |
| Two-stage downloads and bound uploads | Task 12 |
| Private takeover and canary non-observation | Task 13 |
| Encrypted isolated sessions and revocation | Task 11 |
| Isolated medical portal mode | Tasks 13, 17, 20 |
| Bounded CAPTCHA then minimal human/L5 | Tasks 6, 17, 19 |
| Outbound enrolled PC worker and kill controls | Tasks 14-16 |
| Redacted evidence and 14-day purge | Tasks 5, 13, 17-20 |
| No paid service, VPS upgrade, silent version/core change | Global constraints, Tasks 2 and 8 |
| Source/runtime sync and deployment safety | Task 18 |
| One clean no-waiver 20/20 release run | Tasks 19-20 |

- [ ] Every design section maps to at least one task.
- [ ] Every frozen acceptance case maps to Task 19 or 20.
- [ ] No task invents a live Hermes/browser/CUA symbol; Task 2 ledger supplies them.
- [ ] No placeholder markers or deferred implementation instructions remain.
- [ ] Contract type and method names are consistent across tasks.
- [ ] Every external/risky operation has an explicit human approval step.
- [ ] Every phase has a test gate and commit checkpoint.
- [ ] Runtime credentials/state are excluded from Git and ordinary sync.
- [ ] No paid service, VPS upgrade, med-system write, or silent core/version change is planned.
