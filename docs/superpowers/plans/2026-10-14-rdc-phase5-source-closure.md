# RDC Phase 5 — Source reconciliation and local candidate (2026-10-14)

## Scope and owner gate
Owner approved A1–A4: reconcile live/source, create repeatable pinned RDC setup,
run non-disruptive tests and create one local candidate commit on an isolated
branch. **No push, PR, merge, publication, deployment, service restart or reboot.**
A5 publication needs explicit approval of the resulting exact commit SHA.

## Historical plan versus actual approved work
The earlier `2026-10-14-chatgpt-rdc-cgroup-migration.md`, spec and issue
tickets describe the original Phase 1 migration using `npx`, an infinite
endpoint wait and no full reboot. They are preserved as historical planning
artifacts, **not** the accepted live configuration after subsequent owner gates.
Subsequent approvals authorized Phase 2 (one gateway restart), Phase 3
(controlled RDC process-exit tests and hardening), and Phase 4 (one VPS reboot,
performed by owner via Tencent Lighthouse Console).

## Verified live outcome
- Dedicated user unit `chatgpt-rdc.service` runs outside Hermes gateway cgroup.
- Phase 2: RDC survived a gateway restart with unchanged RDC MainPID 512158
  and child PID 513045; Hermes gateway PID changed 2500322 -> 584156.
- Phase 3: replaced `npx` supervision with direct Node entry point. One
  SIGKILL recovery (587266 -> 587799) and one SIGTERM recovery
  (-> 588245) succeeded without manual rescue. `NRestarts=2`.
- Phase 4: boot ID changed from `28e6acc6-0b55-489d-b902-fdbbded35b1e`
  to `dbdfe588-c292-456e-bc3f-005de53fcd9e` at 16:12 MYT.
  RDC automatically started, restored session at 16:13:08 and reported
  `Device ready` at 16:13:09; the post-boot main PID was 1297.
- `Restart=always`, `RestartSec=8s`, `TimeoutStartSec=15s`, a bounded
  HTTP preflight, `WantedBy=default.target`, `Linger=yes`.
- No token was viewed, altered, copied or checked into source.
- The Hermes gateway took unusually long to initialize after reboot; this
  is a **separate follow-up**, not proof of full Hermes messaging readiness.

## Source-of-truth files
- `ops/systemd/user/chatgpt-rdc.service` is an exact copy of the live,
  post-Phase-3 unit (SHA256
  `9c0738e503c414bc2b6d2f681189e202a72049c1865bda79d78a6fd27ea0d762`).
- `ops/rdc/package.json` pins package version `0.2.51`.
- `ops/rdc/package-lock.json` locks 655 package entries from the
  **observed installed npx lockfile**. Registry URLs were normalized
  from the Tencent HTTP mirror to HTTPS npm registry; recorded package
  integrity hashes were preserved. A clean online `npm ci` is not yet tested.
- `ops/rdc/bootstrap.sh --check` validates manifests without changes.
  `--install` is **only for an inactive RDC service on a new host**;
  it refuses if RDC is active or a runtime folder already exists.
  It runs `npm ci` into the expected fixed path, then validates version.
  It never enables, starts, stops or restarts the service.
- Auth remains in the existing private client-owned home directory;
  none of these source artifacts depend on or replicate that file.

## Reinstall procedure (requires a separate owner-approved maintenance gate)
1. Confirm the original authenticated device state and recovery access.
2. Run `bash ops/rdc/bootstrap.sh --check`.
3. On a clean/inactive installation as `ubuntu`, run
   `bash ops/rdc/bootstrap.sh --install` (network/npm registry required).
4. Install `ops/systemd/user/chatgpt-rdc.service` to
   `~/.config/systemd/user/chatgpt-rdc.service`.
5. In a separately authorized maintenance window, activate/enable the unit.
6. Verify single client, new process/cgroup, `Device ready`, ping, and linger.
   Never reauthorize or rotate credentials through this procedure.

## Acceptance boundary
A1–A4 confirm source parity and local test/commit candidate only. The
new pinned-install pathway is untested on a clean machine and no live reload
or restart is allowed in this phase. Phase A5 requires explicit commit-SHA
approval, protected Git publication, and final source/deployment evidence.

## A3 candidate validation (local, no service changes)
- Focused RDC contract: **3 passed** after an expected initial RED against
  the outdated `npx` assertions.
- Selected independent regression checks
  (`tests/infra`, normalized-worktree and runtime-drift contracts):
  **8 passed**.
- `systemd-analyze --user verify`, shell syntax check and
  `bootstrap.sh --check`: **PASS**.
- Source/live unit `cmp` and SHA256 equality: **PASS**.
- `npm ci --dry-run --offline --ignore-scripts --no-audit --no-fund`
  using the source lockfile: **PASS**, 654 package entries resolved in
  dry-run; no source `node_modules` directory created. This is NOT a
  real clean-install verification.
- Broader `tests/gateway` collection: **BLOCKED**, two import errors from
  existing mixed Hermes source/runtime environment:
  `strip_codex_context_variant_suffix` absent from
  `agent.model_metadata` used during collection. Out of scope; no
  source/provider changes made to work around this.
- Live RDC PID `1297` and gateway PID `1210` stayed unchanged during
  A1–A3. No service restart, reboot, publication or deploy occurred.
