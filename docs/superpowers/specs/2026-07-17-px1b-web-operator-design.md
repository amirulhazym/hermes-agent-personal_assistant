# PX-1b Web Operator - Locked Design

> **Status:** APPROVED IN CHAT - awaiting written-spec review
> **Date:** 2026-07-17
> **Track:** PX-1b Web Operator
> **Method:** `docs/superpowers/specs/PX-PLANNING-FRAMEWORK.md`
> **Decision record:** `docs/superpowers/specs/2026-07-14-px1b-web-operator-planning-qna.md` Part 15
> **Audit:** `docs/superpowers/specs/2026-07-14-px1b-web-operator-audit-recap.md`

## 1. Purpose

PX-1b makes Hermes a phone-first web and desktop operator rather than a chat-only
assistant. Amirul commands, approves, takes over, cancels, schedules, and receives
results through WhatsApp or Telegram. The VPS remains the always-on brain and primary
executor. A Windows PC is an optional high-power worker when a task genuinely needs a
desktop application, protected UI, or capability unavailable on the VPS.

This is a complete V1 capability, not a reduced day-one MVP. Delivery remains phased
so every subsystem is independently testable and safety failures are contained. V1 is
complete only when all 20 frozen acceptance cases pass in one clean release-candidate
run. This does not promise universal success on every website, CAPTCHA, checkout, or
Windows application. Unsupported targets must fail closed with a useful minimal-human-
effort handoff.

## 2. Non-negotiable constraints

- PRD Section 7 and `AGENTS.md` override speed, convenience, and task completion.
- Maximize task completion only within the locked safety, cost, and stability rails.
- No paid browser cloud, paid bypass, or VPS upgrade. If current free infrastructure
  cannot pass acceptance, record the blocker for Overhaul V2 and do not claim success.
- Keep the live Hermes version. First inventory it; do not silently upgrade or deploy
  unreleased `main` behavior described by newer documentation.
- Fill proven native gaps through isolated project adapters. If a safe adapter is not
  feasible, stop and report the failed requirement rather than patching live core
  freely.
- Existing PX-1 search, extraction, and Research Expert are dependencies, not rebuild
  targets. A real Telegram Research Expert E2E is a pre-implementation gate.
- If a PX-1 dependency fails, pause PX-1b, repair only the failed contract, revalidate,
  and resume.
- The PX-1 anti-repeat playbook remains binding: no med-state changes, no account
  farming, no repeated hard bot-wall probing, depth=1/max=3 children, and no secrets in
  logs or documentation.
- Every phase ends with evidence and explicit human approval. Every commit separately
  requires explicit approval.

## 3. Architecture

```text
WhatsApp / Telegram
        |
        v
Web Operator expert
intent + risk classification + task/approval IDs
        |
        v
L0  policy decision: refuse or pause for approval
L1  bounded public HTTP compatibility fetch                 VPS
L2  search-cascade + hybrid-web + Research Expert           VPS
L3  native Hermes browser + isolated gap adapters           VPS
        |
        v only when the VPS cannot safely complete
L4  enrolled Windows worker + Computer Use                   PC
        |
        v only when automation must stop
L5  terminal human-operated task handoff                     PC/phone
```

### 3.1 Device roles

| Device/layer | Role |
|---|---|
| Phone | Universal command, approval, private takeover, cancellation, scheduling, status, and result surface. |
| VPS | Always-on brain and primary worker. Owns routing, queues, approvals, L1-L3, ordinary authenticated web operation, and run artifacts. |
| Windows PC | Optional enrolled worker for named desktop apps, protected UI, real-browser/CUA tasks, and workflows the VPS cannot safely finish. |
| GitHub/MJay | Durable source for code, docs, templates, and reproducible recipes. Never stores secrets, browser sessions, medical portal data, or runtime logs. |
| VPS runtime | Live state holder. Source/runtime drift is detected through the existing VPS-Windows/WSL2-GitHub sync discipline. |

The phone is the control surface, not necessarily the execution machine. The user sees
one Hermes task even when execution moves between VPS and PC.

### 3.2 Component boundaries

- `web-operator` is a separate expert with narrow natural-language triggers and an
  optional `/browse` override.
- Research Expert calls Web Operator only when research needs interactive navigation.
- A project-owned operator adapter insulates policy from the live Hermes browser API.
- Native Hermes browser tools are evaluated first. Raw Playwright or another isolated
  adapter is used only for a proven gap such as approval-bound file handling or mobile
  takeover. `browser-use` is trialed only if native acceptance fails.
- File transfer, private takeover, and remote PC CUA are separate adapters behind the
  same policy and approval contract.
- Qwen/Sakana scripts remain old test references. After the real CUA path works, one
  optional comparison test may identify a reusable technique; they are not production
  dependencies.
- Private medical portals use a separate high-sensitivity mode and never write to the
  existing medication system.

## 4. Routing and task lifecycle

### 4.1 Routing

1. Classify intent and risk before opening a page.
2. Use L0 as a policy state: refuse a prohibited request or pause an otherwise allowed
   action for approval. An approved action resumes at its prior execution level. L0 is
   not an executor and does not consume a new execution budget.
3. Start at L1/L2 for reading, search, and extraction.
4. Escalate L2 to L3 automatically when content is empty, JavaScript interaction is
   required, or the request explicitly needs clicks/forms. Log the reason without
   interrupting the user.
5. After normal browsing fails, try only bounded self-hosted compatibility adapters
   that have passed controlled tests. Compatibility hardening is not promised stealth
   or permission to defeat access controls.
6. Suggest L4 only for a concrete desktop/native limitation, a named Windows app,
   protected UI, or a VPS failure that CUA can plausibly solve.
7. Use L5 only when Hermes cannot resume: transfer the remaining task to the human and
   end autonomous execution. A temporary challenge/secret takeover that resumes is not
   L5.

### 4.2 Run limits and capacity

- One unattended L3 execution budget ends at 30 browser actions or 10 active execution
  minutes, whichever comes first. An action is one state-changing or observing browser
  tool call (navigate, snapshot, click, type, key, scroll, back, vision, console/CDP,
  upload, or download operation). L1/L2 calls and L4 actions have separate traces and do
  not consume the L3 count.
- Any single stuck operation is cancelled after 180 seconds.
- One normal transient failure may receive one bounded retry inside the original action
  and time budget; it does not reset either budget.
- Anti-bot blocks, explicit prohibitions, and hard challenges do not receive repeated
  probing.
- Benchmark one, two, then at most three concurrent L3 jobs using the same frozen L3
  workload for at least 10 minutes per level. A level passes only if the systemd gateway
  remains active with no restart/OOM; Telegram and WhatsApp each answer a health request
  within 30 seconds; available RAM does not remain below 400 MiB for more than 30
  seconds; swap growth remains below 512 MiB during the level; and no browser job exceeds
  its budget. Optimize and lock production to the highest passing level. If no level
  passes, L3 acceptance fails.
- Queue work above the measured-safe concurrency limit.
- Kill a browser worker before allowing it to threaten the gateway.
- Waiting for approval/takeover pauses active execution time but never the 15-minute
  approval expiry. L2-L3 escalation remains inside the same task and starts the single
  L3 budget when the first L3 action occurs.
- There is no clock-based quiet-hours block for requested work; health limits and
  approval expiry apply at all times.

### 4.3 Human pauses and PC availability

- Ask in the originating chat, with owner-only Telegram fallback.
- Every approval/takeover request has a unique task/action ID and expires after 15
  minutes.
- Expiry aborts the pending action, closes the active task safely, and reports what was
  not done. A separately approved persistent login may remain.
- Postponing or scheduling preserves only task intent and non-sensitive prepared state.
  It never preserves or replays an action approval, takeover grant, or CUA grant. At
  execution time Hermes revalidates all material state and obtains a fresh owner-
  authenticated approval.
- After CUA approval, check whether the enrolled PC worker is online. If online,
  proceed. If offline, offer `Turn on and retry`, `Postpone`, `Schedule`, or `Cancel`.
- Do not implement Wake-on-LAN in PX-1b because the PC normally uses a mobile hotspot.
- Cancellation closes the browser/PC grant and leaves no external action half-approved.

## 5. Security and human control

### 5.1 Untrusted content

Website, document, message, and desktop content is data, never authority. It cannot
change policy, grant approval, choose secrets, authorize an external effect, or instruct
Hermes to disclose cookies, credentials, files, or internal endpoints.

L1-L4 deny loopback, private, link-local, metadata, local-file, browser-debug, router/
admin-console, and other non-public destinations before and after DNS resolution and
every redirect. Private/local target automation is out of scope for PX-1b V1. The
private PC control channel is transport infrastructure and cannot be navigated to or
repurposed by page content.

### 5.2 Action-bound approvals

Every approval is owner-authenticated, single-use, task-bound, action-bound,
parameter-bound, and time-limited. Material changes invalidate it.

| Action | Required behavior |
|---|---|
| Personal form data | Ask before entering it, show intended fields/values, then ask again before final submission. |
| Message/comment/post | Show exact account, recipient/audience, final content, and attachments before every send. |
| Download | First approve receipt into an isolated quarantine using expected filename/type/size/source/purpose. After receipt, compute actual hash/type/size, reject mismatches or unsafe content, and require a second approval before opening, moving, sharing, or uploading it. |
| Upload | Ask before transfer and bind approval to the existing file's hash, type, size, destination, account, and purpose. Revalidate immediately before upload. |
| Checkout | Prepare the flow, but re-read seller, items, quantity, currency, total, shipping destination, account, and recurring-charge status immediately before a fresh final approval. Any drift requires reapproval. |
| Named Windows app | Limit approval to the named app/window and stated task. Other apps/files, elevation, shell, installs, security settings, and external effects need separate approval. |

Financial credentials, bank login, card number, CVV, PIN, banking OTP, and equivalent
payment secrets remain entirely in the user's normal phone browser or official app.
Hermes may perform the final approved order action only after the local financial step
and final transaction revalidation.

### 5.2.1 Complete runtime action taxonomy

All reachable PRD Section 7.5 actions use draft-confirm-act. Actions not explicitly
implemented are denied, not inferred as allowed.

| Action class | V1 rule |
|---|---|
| Delete or overwrite data | Show exact target and consequence; fresh approval immediately before action. Bulk or irreversible deletion is denied in V1. |
| Infrastructure or security change | Denied through Web Operator/CUA in V1; requires a separate administration task and build-time approval. |
| Shell/terminal side effect, elevation, install | Denied through Web Operator/CUA in V1; no approval inside a browser task can authorize it. |
| Secret exposure | Denied. Secret entry follows private takeover; disclosure to model/chat/artifact is never approvable. |
| Purchase or paid service | Transaction-bound approval is required; enabling a new paid service remains out of scope and needs separate human authorization. |
| Calendar/event change | Show calendar/account, exact event fields, invitees, notifications, and conflicts; fresh approval before create/update/delete. |
| Third-party contact or public post | Exact-action approval per Section 5.2. |
| Group join/reply or audience change | Fresh approval naming group/audience and exact content; group access is otherwise disabled. |
| Expensive-model switch | Never automatic. Owner-only explicit model action outside the browser approval flow. |

### 5.3 Private mobile takeover

Ordinary passwords and non-financial OTPs use a short-lived owner-only takeover:

1. Pause all agent input.
2. Suspend screenshots, video, DOM/accessibility observation, clipboard and keystroke
   capture, logs, and queued observations.
3. The VPS takeover controller grants exclusive control of the active VPS browser tab
   through a private authenticated phone path. A PC-hosted browser uses the same policy
   but its PC worker terminates the local stream. Never expose a public VNC, CDP,
   browser, or CUA port.
4. The user enters the secret directly; it never traverses chat or model context.
5. Resume only after the user explicitly returns control and the secret field is masked
   or no longer present.
6. If the phone path disconnects, freeze input immediately, keep capture disabled, and
   close the takeover/browser after the remaining grant timeout unless the owner
   reconnects and reauthenticates.
7. Expire after 15 minutes and destroy abandoned active sessions safely.

The central VPS control plane issues signed, nonce-bound grants and verifies the owner
identity from the allowlisted messaging session. Each endpoint verifies task, device,
browser/profile, action class, nonce, and expiry. Enrollment identities and revocation
state live in a service-owned non-Git state store on the relevant host; private keys
never leave that host. The PC creates an outbound-only connection to the control plane,
so mobile-hotspot CGNAT requires no inbound PC port.

Tests prove capture suspension with synthetic canary values entered during takeover:
the canaries must be absent from model input, queued observations, screenshots, video,
DOM/accessibility output, clipboard/keystroke events, logs, and artifacts.

This minimizes risk but does not make an impossible zero-breach guarantee. The design
and tests must state residual host/browser risk.

### 5.4 Session isolation

- Key browser identity by `(site, account, profile, execution device)`.
- Enroll each identity as one-time or persistent with user-chosen expiry and revoke.
- Do not impose an arbitrary number of enrolled sites.
- Never copy a session between VPS and PC automatically.
- Treat cookies/local storage as credentials: encrypt at rest with a host-local key
  readable only by the operator service account, apply restrictive filesystem
  permissions, exclude from Git/logs/artifacts/routine backups, and lock concurrent use.
  Revocation closes active contexts, deletes the encrypted profile and derived caches,
  clears the registry entry, and records metadata-only proof. Suspected compromise
  revokes before any reuse.
- Never persist financial sessions under Hermes control.

### 5.5 Medical portal mode

Private medical portals are in scope under an isolated high-sensitivity mode:

- Never modify or feed `med_*`, `chain_*`, med JSON, medication memory, or existing
  medical automation.
- Do not retain portal screenshots, page contents, medical values, or normal artifacts.
- Do not export portal data to durable memory, Research artifacts, or Obsidian.
- Use private takeover for authentication.
- Require normal explicit approvals for every download, upload, appointment, message,
  form, account change, or other external effect.
- Expose only the minimum transient information needed for the approved task and discard
  it at completion.

Medical mode writes only an encrypted metadata audit record in a separate restricted
store: task ID, owner ID, portal origin without path/query, action classes, approval IDs,
timestamps, outcome label, and deletion proof. It contains no medical value, page text,
entered field value, file content, or screenshot and is deleted after 14 days.

Public medical research remains a Research Expert task.

### 5.6 CAPTCHA and blocking

- Hermes may use normal, permitted interaction and bounded compatibility hardening.
- Do not use solver farms, paid bypass, account farming, stolen sessions, exploit paths,
  or repeated attempts against a hard wall.
- On a challenge, ask the user to solve only the challenge through private takeover,
  then resume the approved task.
- Use full human L5 handoff only after minimal assistance fails.
- Stop on explicit automation prohibition, repeated blocking, or unclear high-impact use.

## 6. Secure Windows worker

The PC worker is an enrolled executor, not an open remote desktop endpoint. It creates
an outbound-only connection to the VPS control plane and uses a mutually authenticated,
encrypted, replay-protected private channel established without public CDP, VNC, MCP,
or CUA ports.

Every CUA run requires:

- exact enrolled PC identity;
- a fresh short-lived per-task grant;
- named app/window and intended task;
- a visible local activity indicator;
- exclusive input ownership while Hermes acts;
- immediate local and phone-accessible stop controls;
- fail-closed stop on network loss, expiry, wrong window, uncertain screen state,
  unexpected sensitive content, privilege request, or identity failure.

The VPS control plane issues and validates task grants. The PC worker validates the
grant again before acting and reports a signed result. Enrollment is an explicit local
PC action that records a device public key and owner-approved fingerprint; revocation on
either endpoint blocks new grants. On phone-path, control-plane, or worker disconnect,
the PC immediately releases input ownership and stops CUA. The visible indicator and
local kill switch remain PC-local and cannot be suppressed remotely.

CUA may attempt an approved task in any named application that is locally available and
automatable. Unsupported or protected surfaces produce a minimal human handoff, not a
false success claim.

## 7. Evidence and retention

Each ordinary run creates one compact artifact containing:

- task ID, timestamps, and originating channel;
- redacted request summary;
- L1-L5 transitions and reasons;
- action classes and approval IDs, never approval secrets or entered values;
- normalized redacted URLs: safe origin/path only, without query strings, fragments,
  tokens, account IDs, or sensitive path sections;
- outcome label, failures, retries, handoffs, and next option;
- only the minimum selected redacted browser/CUA screenshots needed to prove key
  transitions.

Raw frames are deleted immediately after processing. Capture is disabled during private
takeover and high-sensitivity portal screens. Detailed traces and selected redacted
evidence are deleted automatically after 14 days. High-level outcome records may remain
without page content, entered data, or personal values.

Medical mode uses only the separate metadata audit defined in Section 5.5 and is exempt
from the ordinary artifact. Private takeover produces only start/end/expiry metadata and
the canary-based proof that observation channels remained empty.

## 8. Failure handling

- Wrong identity, stale/replayed approval, changed action state, prompt injection,
  internal-network target, secret-exposure risk, executor disconnect, unexpected
  privilege request, or policy uncertainty stops the action.
- Browser crash: close safely, preserve only redacted diagnostics, and retry once only
  if policy allows.
- Resource pressure: terminate browser work before the gateway.
- Session corruption: quarantine it and require a fresh login; never silently choose a
  different account.
- Partial form, checkout, or message: leave it unsent/unsubmitted and report the state.
- Secret or unredacted personal data in an artifact is a project-level stop.
- Unauthorized send, submission, purchase, transfer, CUA action, or existing-med-system
  write is a project-level stop.

## 9. Frozen acceptance suite

Release requires all cases to pass in one clean release-candidate run. No skipped,
waived, provisional, or partial cases. Fixes require rerunning the full suite.

1. Telegram triggers existing Research Expert end-to-end as the Phase 0 gate and is
   rerun unchanged in the final release-candidate suite.
2. WhatsApp triggers Web Operator and returns a result.
3. Telegram triggers Web Operator and returns a result.
4. A public static task remains at L1/L2 and does not launch L3.
5. A public multi-step JavaScript task auto-escalates and completes through L3 on VPS.
6. The L2-L3 route and escalation reason are recorded correctly.
7. Public/private-network, redirect, unsafe-scheme, and prompt-injection controls fail closed.
8. Measured concurrency, 30-action/10-minute budget, 180-second stuck-operation limit, and gateway health all hold.
9. A personal-data form asks before typing.
10. The form asks again before final submission, and changed content invalidates approval.
11. One exact external message/post sends only after approval; changed target/content/attachment requires reapproval.
12. Every file transfer receives action-bound approval; substitution and unsafe-file cases stop.
13. Ordinary login/OTP uses private takeover; canary secrets appear nowhere in model context, logs, captures, traces, or artifacts.
14. Financial-secret handling remains entirely in the normal phone browser or official app.
15. Multiple site/account/device sessions remain isolated; persistence choice and revocation work.
16. A private medical portal task completes without writing to existing med state, memory, normal artifacts, or retained screenshots.
17. CAPTCHA handling uses only permitted behavior, minimal human completion, safe resume, and correct L5 handoff when blocked.
18. The PC worker rejects unknown/replayed grants and stops on network loss, expiry, wrong window, and kill switch.
19. An approved named-app CUA task completes; an unapproved app, privilege request, or external action is blocked.
20. A full phone-first workflow routes across VPS and, only when required, PC CUA, with redacted evidence and correct offline-PC postpone/schedule behavior.

Controlled fixtures with synthetic accounts/data cover checkout, messages, calendar and
group actions, deletion/overwrite policy, files, prompt injection, CAPTCHA, approval
mutation, and session isolation. Real phone flows cover both chat platforms, one low-risk
authenticated website, one isolated private medical portal task, and one named-app CUA
task. Real flows are owner-only, separately approved immediately before execution, use
the minimum data needed, and must be reversible or no-op where possible. They never send
to a third party, place a real order, alter a real medical record, or transfer a real
sensitive file. Amirul initiates and approves from the phone; the implementation agent
gathers redacted technical evidence.

## 10. Delivery phases

| Phase | Scope | Gate |
|---|---|---|
| 0 - Preflight truth | Required Telegram PX-1 E2E; read-only live-version, browser, CUA, resource, and runtime inventory | Repair only failed PX-1 contract; no PX-1b work until pass |
| 1 - Policy/contracts | Web Operator expert, L0/L5 state semantics, complete PRD Section 7.5 action taxonomy, untrusted-content rules, action-bound approval schema, artifact schema, deterministic fixtures | Policy tests and user phase approval |
| 2 - VPS public core | L1/L2 composition, native L3 adapter, bounded compatibility adapters, queue, 1-to-3 concurrency benchmark, WhatsApp/Telegram triggers | Public E2E and gateway health evidence |
| 3 - Auth/actions | Isolated sessions, private takeover, forms, files, messages/posts, checkout, medical portal mode | Secret-canary and action-approval tests |
| 4 - PC execution | Enrolled bridge, actual CUA driver, named-app scope, PC availability, postpone/schedule, kill controls | Authentication/fail-safe and named-app tests |
| 5 - Integrated hardening | Prompt injection, CAPTCHA/L5, session isolation, resource/network failures, cleanup, optional Qwen/Sakana comparison | Integrated drills pass |
| 6 - Release acceptance | One clean 20/20 run; tracker, runbook, and continuation updates | Written evidence and final human acceptance |

Every phase is implemented, tested, reported, and explicitly approved before the next.
No capability is silently deferred for convenience. A failed capability remains an
honest blocker or Overhaul V2 issue, not a success claim.

## 11. Documentation and source discipline

- Update `PROGRESS.md`, `DECISIONS.md`, `RUNBOOK.md`, and the continuation brief as each
  implementation phase changes the live system.
- Keep secrets, sessions, raw captures, portal content, and runtime state outside Git.
- Record official documentation and exact live-version evidence before setup or config.
- Ask separately before every stage/commit/push/deployment/service/secret-touching action.
