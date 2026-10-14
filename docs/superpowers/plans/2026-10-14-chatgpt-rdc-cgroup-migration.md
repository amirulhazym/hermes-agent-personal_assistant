# Remote Desktop Commander Independent Service — Implementation Plan

> **For agentic workers:** Use the `executing-plans` workflow to implement this plan task-by-task after the xcute owner gate. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Run the existing RDC device as a systemd user service with an independent cgroup, restart recovery, and boot activation, and prove it survives exactly one Hermes gateway restart.

**Architecture:** The service owns the existing recovered RDC npx command in its own user-unit cgroup. `HOME` points to ubuntu's existing private RDC device configuration. A startup preflight waits for the RDC bootstrap endpoint because the user manager has no `network-online.target`; systemd then supervises the process with a five-second restart delay.

**Tech Stack:** systemd user units, `/usr/bin/npx`, existing npm-cached `@wonderwhy-er/desktop-commander`, pytest static contract test, systemd journal.

## Global Constraints

- Service name is exactly `chatgpt-rdc.service`.
- Recovered historical launch is `npx -y @wonderwhy-er/desktop-commander@latest remote`; owner-selected service launch is `/usr/bin/npx -y @wonderwhy-er/desktop-commander@0.2.51 remote`, working directory `/home/ubuntu`.
- Do not show, copy, manually rotate, clear, or reauthorize RDC credentials. Owner decision on 2026-10-14 permits only the installed client's normal persisted-session refresh/rotation; if the client requests device authorization, stop and ask rather than re-pairing.
- Unit must have its own cgroup; `Restart=always`; `RestartSec=5`; `WantedBy=default.target`.
- Since `network-online.target` is `not-found` in the user manager, use the proven public RDC bootstrap endpoint for startup readiness instead of a dangling target dependency.
- Do not change the gateway unit, release/model/provider/Gemini work, unrelated tmux sessions, or the VPS reboot state.
- Enablement and existing `Linger=yes` are the reboot-persistence proof; do not reboot.
- Exactly one detached gateway restart is permitted, after RDC is proven ready. Do not retry.
- No GitHub publish/merge without the repo's exact-SHA owner release approval.

---

## Current Evidence and Locked Inputs

- Gateway unit: `/home/ubuntu/.config/systemd/user/hermes-gateway.service` runs `gateway.cgroup_cleanup` from `ExecStopPost`. The live function reads `/proc/self/cgroup`, enumerates that exact cgroup's `cgroup.procs`, then sends SIGKILL to each remaining PID except itself (`/home/ubuntu/.hermes/hermes-agent/gateway/cgroup_cleanup.py:24-72`); this is why the service-specific RDC cgroup addresses the cause without editing gateway behavior.
- Historical gateway status in the RDC log captured `tmux new-session -d -s chatgpt-rdc -c /home/ubuntu "exec npx -y @wonderwhy-er/desktop-commander@latest remote >> /home/ubuntu/.hermes/logs/remote-desktop-commander.log 2>&1"` under the gateway service cgroup.
- Cached package metadata is version `0.2.51`; its `desktop-commander` binary is `dist/index.js`, and that entrypoint dispatches argument `remote` to the remote-device launcher.
- Persisted auth path is derived from `os.homedir()` as `/home/ubuntu/.desktop-commander-device/device.json`; current mode is `0600`. Secret values were not printed.
- The retained log records an invalid-refresh-token message followed by device authorization, then channel subscription / device online / `Device ready`; later log entries record a channel socket close and device offline after the gateway event. These are historical events, not current auth/connectivity proof; the event date was not independently established in this audit.
- `network-online.target`: system manager `active`; user manager `not-found`. The RDC bootstrap endpoint returned HTTP 200 during the read-only audit; response body was suppressed.
- `Linger=yes`; no RDC user unit, active tmux server/session, target-wants entry, autostart entry, or matching crontab entry was found.
- Fresh live read-only check: gateway active (`MainPID=2500322`, `ControlGroup=/user.slice/user-1000.slice/systemd user manager for UID 1000/app.slice/hermes-gateway.service`); zero matching RDC Node processes; `chatgpt-rdc.service` `LoadState=not-found`; no tmux server; `Linger=yes`; user `network-online.target` `LoadState=not-found`. The current package metadata reports version `0.2.51` and binary entry `dist/index.js`.
- SSOT repository was clean on `main` at `621683be8cd9d851ecdd82b82cf3d9353c1c60a1` before these plan artifacts.

## Task 1: Add and test the source-controlled unit contract

**Files:**
- Create: `ops/systemd/user/chatgpt-rdc.service`
- Create: `tests/infra/test_chatgpt_rdc_service.py`

**Interfaces:**
- The unit's executable is `/usr/bin/npx` with pinned arguments `-y @wonderwhy-er/desktop-commander@0.2.51 remote`.
- The unit sets only `HOME=/home/ubuntu` and a PATH containing `/usr/bin`; it does not contain auth material.
- The startup preflight probes `https://mcp.desktopcommander.app/api/mcp-info` and suppresses the response body.

- [ ] **Step 1: Write the failing contract test**

Create `tests/infra/test_chatgpt_rdc_service.py` with this focused contract test:

```python
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIT = REPO_ROOT / "ops/systemd/user/chatgpt-rdc.service"


def test_chatgpt_rdc_unit_contract():
    assert UNIT.is_file(), f"missing unit file: {UNIT}"
    unit = UNIT.read_text(encoding="utf-8")
    required = (
        "ExecStart=/usr/bin/npx -y @wonderwhy-er/desktop-commander@0.2.51 remote",
        "WorkingDirectory=/home/ubuntu",
        "Environment=HOME=/home/ubuntu",
        "Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "https://mcp.desktopcommander.app/api/mcp-info",
        "TimeoutStartSec=infinity",
        "Restart=always",
        "RestartSec=5s",
        "KillMode=control-group",
        "KillSignal=SIGTERM",
        "TimeoutStopSec=20s",
        "StandardOutput=journal",
        "StandardError=journal",
        "WantedBy=default.target",
    )
    missing = [directive for directive in required if directive not in unit]
    assert not missing, f"missing service directives: {missing}"

    forbidden = (
        "tmux",
        "hermes-gateway.service",
        "ACCESS_TOKEN",
        "REFRESH_TOKEN",
        "API_KEY",
        "PASSWORD",
        "StartLimitIntervalSec=0",
    )
    found = [value for value in forbidden if value.lower() in unit.lower()]
    assert not found, f"forbidden service coupling/credential references: {found}"
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `python3 -m pytest -q tests/infra/test_chatgpt_rdc_service.py`
Expected before the unit source exists: collection succeeds and the test fails because the declared service file is absent.

- [ ] **Step 3: Add the minimal unit declaration**

Create `ops/systemd/user/chatgpt-rdc.service` with this candidate declaration. It uses the recovered launcher verbatim, waits for the client's public bootstrap endpoint because the user manager lacks `network-online.target`, and does not include authentication values:

```ini
[Unit]
Description=Remote Desktop Commander

[Service]
Type=simple
WorkingDirectory=/home/ubuntu
Environment=HOME=/home/ubuntu
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStartPre=/bin/sh -c 'until /usr/bin/curl --fail --silent --output /dev/null --max-time 5 https://mcp.desktopcommander.app/api/mcp-info; do /usr/bin/sleep 2; done'
TimeoutStartSec=infinity
ExecStart=/usr/bin/npx -y @wonderwhy-er/desktop-commander@0.2.51 remote
Restart=always
RestartSec=5s
KillMode=control-group
KillSignal=SIGTERM
TimeoutStopSec=20s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

Do not add a system-level `network-online.target` dependency because the user manager does not load it. Do not install this candidate until Phase 3 approval.

- [ ] **Step 4: Run the focused test and unit parser**

Run: `python3 -m pytest -q tests/infra/test_chatgpt_rdc_service.py`
Expected: all focused unit-contract assertions pass.

Run: `systemd-analyze --user verify ops/systemd/user/chatgpt-rdc.service`
Expected: exit code `0` with no unit syntax error.

- [ ] **Step 5: Review source diff and stop at the runtime owner gate**

Run: `git diff --check` and `git status --short`.
Expected: only the planned RDC unit source, static test, and plan/spec/ticket artifacts are present. Do not install or start the live service unless Phase 3 execution approval is recorded.

## Task 2: Install, enable, and prove the independent RDC service

**Files:**
- Source: `ops/systemd/user/chatgpt-rdc.service`
- Live unit: `/home/ubuntu/.config/systemd/user/chatgpt-rdc.service`
- Live systemd enablement symlink under `/home/ubuntu/.config/systemd/user/default.target.wants/`

**Interfaces:**
- `systemctl --user daemon-reload`
- `systemctl --user enable --now chatgpt-rdc.service`
- `systemctl --user show chatgpt-rdc.service` for properties and cgroup.

- [ ] **Step 1: Capture a bounded pre-change snapshot**

Record whether the live unit exists, its hash if present, the exact tmux session/process path if present, and the current `device.json` metadata (path/mode only). Do not read or print token values. Do not stop/remove any process yet.

- [ ] **Step 2: Install and start the unit**

After explicit Phase 3 approval, install the source unit with mode `0644` at the live unit path, reload the user manager, and enable/start `chatgpt-rdc.service`.

- [ ] **Step 3: Handle auth fail-closed**

Inspect only service journal status lines. If startup requests device authorization or reports an invalid persisted session, stop/disable this service and ask the owner. Do not open a browser, run `--logout`, alter `device.json`, or expose credential values.

- [ ] **Step 4: Verify live service and exactly one instance**

Require `ActiveState=active`, `SubState=running`, `UnitFileState=enabled`, `Restart=always`, and `RestartUSec=5s`. Require fresh service output showing channel subscription and `Device ready`. Count RDC launch instances by process ancestry/cgroup and require exactly one intended transport instance.

- [ ] **Step 5: Prove cgroup isolation and retire only a proven old path**

Record the actual transport PID and `/proc/<PID>/cgroup`. Require a service-specific cgroup containing `chatgpt-rdc.service` and no `hermes-gateway.service` component. Once the service is ready, check the exact old tmux session/autostart sources again; remove only a positively identified duplicate launcher. If the old path is absent, make no deletion and record `no obsolete live launcher to remove`.

- [ ] **Step 6: Verify boot configuration without reboot**

Require the user unit enabled under `default.target` and `loginctl show-user ubuntu -p Linger` to return `Linger=yes`. Do not reboot.

## Task 3: One controlled gateway-restart regression

**Files:**
- Temporary one-shot wrapper: `/tmp/chatgpt-rdc-gateway-regression-once.sh` (created only after approval; not committed)
- No gateway source/config file changes.

**Interfaces:**
- The wrapper schedules one detached systemd user-manager job outside the gateway cgroup.
- The scheduled job calls `systemctl --user restart hermes-gateway.service` exactly once, then records post-start service/process evidence.

- [ ] **Step 1: Capture pre-restart proof**

Record gateway active state, MainPID/start timestamp, RDC ActiveState/MainPID, RDC transport PID, transport cgroup, and latest connected/ready journal markers.

- [ ] **Step 2: Schedule exactly one detached restart**

Create `/tmp/chatgpt-rdc-gateway-regression-once.sh` only after approval with exactly one gateway restart invocation:

```bash
#!/usr/bin/env bash
set -euo pipefail
systemctl --user restart hermes-gateway.service
systemctl --user show hermes-gateway.service -p ActiveState -p MainPID -p ExecMainStartTimestamp
systemctl --user show chatgpt-rdc.service -p ActiveState -p MainPID -p ControlGroup
```

Schedule it once as a separate transient user service, not as a child process expected to survive the gateway restart:

```bash
systemd-run --user --unit=chatgpt-rdc-gateway-regression-once --collect --no-block /usr/bin/bash /tmp/chatgpt-rdc-gateway-regression-once.sh
```

Expected: the transient unit is accepted by the user manager; its script executes one `systemctl --user restart hermes-gateway.service`, then records the safe gateway/RDC properties. Do not retry or queue another unit.

- [ ] **Step 3: Verify gateway recovery and RDC survival**

Require a new gateway PID/start timestamp and healthy active state. Require `chatgpt-rdc.service` remains active and the pre-restart transport PID is still alive (not killed/replaced), remains in its RDC-only cgroup, and has no offline/disconnect event. Require the service remains in its connected/ready state. Preserve raw command outputs.

- [ ] **Step 4: Report persistence and limitations**

Report enabled unit plus `Linger=yes` as boot-persistence configuration evidence. State plainly that a full reboot was not run, so post-reboot behavior was not live-tested.

## Rollback and stop conditions

- If the RDC service cannot reach ready state or auth fails, stop and disable only `chatgpt-rdc.service`; preserve the existing auth file and ask the owner. Return to the pre-change state (no RDC process) rather than reviving tmux automatically.
- If duplicate launchers are found, do not terminate a process until its exact owner/cgroup is identified; only retire the obsolete RDC launcher after the new service is ready.
- If the gateway restart does not recover normally or the RDC PID/service changes unexpectedly, stop validation. Do not issue a second restart; report `PARTIAL` or `FAILED` with raw evidence.
- Do not reboot the VPS.
- After test/source work, any public Git promotion remains blocked until the exact candidate SHA receives the repository-required `APPROVE RELEASE <full-sha>`.

## Completion Checklist

- [ ] Unit syntax/static contract passes.
- [ ] Dedicated RDC user service active and enabled.
- [ ] Exactly one intended RDC transport instance; connected/ready.
- [ ] RDC PID/cgroup recorded and proven outside the gateway unit.
- [ ] Old tmux dependency absent; only proven obsolete launcher retired.
- [ ] Restart policy and 5-second restart delay observed from unit properties.
- [ ] Exactly one gateway restart completed; gateway healthy and RDC remained connected/ready.
- [ ] `Linger=yes` plus `default.target` enablement proven; no reboot performed.
- [ ] No credential value exposed, manually rotated, cleared, or reauthorized.
- [ ] No gateway or release/model-provider/Gemini change.
