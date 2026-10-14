# Spec: Remote Desktop Commander Independent Service

## Problem Statement

Remote Desktop Commander (RDC) was launched as a tmux session from a process inside `hermes-gateway.service`. The gateway unit has `ExecStopPost=-/home/ubuntu/.hermes/hermes-agent/venv/bin/python -m gateway.cgroup_cleanup`. Its live implementation reads the caller's cgroup-v2 path, enumerates that cgroup's `cgroup.procs`, and SIGKILLs every remaining PID except itself (`/home/ubuntu/.hermes/hermes-agent/gateway/cgroup_cleanup.py:24-72`). Prior controlled testing, as stated by the owner, established that a gateway restart killed the tmux/npx RDC transport and the device went offline. The cleanup scope is the gateway's own cgroup; a separate systemd user service gets its own service cgroup, so no gateway behavior change is indicated.

At this audit, `chatgpt-rdc.service` is not loaded or installed; the fresh process scan found zero matching RDC Node processes, there is no tmux server, and no RDC default-target symlink, autostart entry, or matching crontab line was found. The ubuntu user manager is lingering. A persisted RDC session file exists with mode `0600`; its values were not displayed or changed. The retained log is historical, not proof of current connectivity or current auth validity.

## Solution

Run RDC as a dedicated `ubuntu` systemd user service named `chatgpt-rdc.service`. Reuse the launch command recovered from the historical RDC log, with an absolute executable path and the original working directory. Give it its own systemd cgroup, enable it under `default.target`, and configure systemd restart recovery. Gate process startup on the RDC client's own public bootstrap endpoint because `network-online.target` is not loaded in the user manager; the system-scope target is active, but it cannot provide a user-manager ordering edge here.

The service will use the existing on-disk RDC authentication mechanism, without displaying, manually changing, logging out, or reauthorizing it. The retained historical log records an invalid-refresh-token message followed by a device-authorization flow that succeeded; current validity is unknown. Owner decision on 2026-10-14: allow only the installed client's normal persisted-session refresh/rotation. If the client reports that browser authorization is required, stop and ask the owner rather than completing auth. No agent-initiated token changes or re-pairing are authorized.

## User Stories

1. As the VPS owner, I want RDC supervised outside the Hermes gateway cgroup, so a gateway lifecycle action cannot terminate the RDC transport.
2. As the VPS owner, I want systemd to restart RDC after its process exits, so a crash does not require manual tmux relaunch.
3. As the VPS owner, I want RDC enabled in the lingering ubuntu user manager, so it starts after boot without a login session.
4. As the VPS owner, I want the existing persisted RDC authentication reused, so the migration does not require a new device pairing.
5. As the VPS owner, I want duplicate launch paths removed only after the new service is ready, so there is never an intentional overlap or accidental duplicate transport.
6. As the VPS owner, I want the service PID and cgroup recorded before and after one gateway restart, so lifecycle independence is demonstrated with live evidence.
7. As the VPS owner, I want no VPS reboot during this change, so boot persistence is checked from enablement and linger without an unapproved reboot.

## Implementation Decisions

- Service name: `chatgpt-rdc.service`, installed as an ubuntu systemd **user** unit; its process tree therefore receives a service-specific cgroup separate from `hermes-gateway.service`.
- Recovered historical launcher: `npx -y @wonderwhy-er/desktop-commander@latest remote`; executable `/usr/bin/npx`; working directory `/home/ubuntu`. The cache contains version `0.2.51`, whose declared binary is `dist/index.js`. Owner selected a pinned service command, `/usr/bin/npx -y @wonderwhy-er/desktop-commander@0.2.51 remote`, to preserve that installed version rather than float to a different RDC release.
- Explicit runtime environment: `HOME=/home/ubuntu` (RDC source resolves auth via `os.homedir()`), and a PATH containing `/usr/bin` so Node is available. No token, secret, or environment-file value is added to the unit.
- Existing auth artifact: `/home/ubuntu/.desktop-commander-device/device.json`, mode `0600`, with persisted session fields. No credential values are copied into source or output. No logout, manual token refresh, or browser reauthorization is permitted by this plan.
- Process recovery: `Restart=always`, `RestartSec=5`, and no unit-level override disabling systemd's normal start-rate policy. Graceful stop uses `SIGTERM`; the client source's shutdown handler allows up to five seconds. `KillMode=control-group` ensures its child processes stop with this service, and `TimeoutStopSec=20` leaves a bounded shutdown window.
- Network readiness: `ExecStartPre` waits until `https://mcp.desktopcommander.app/api/mcp-info` returns a successful HTTP response; this is the same public bootstrap endpoint used by the installed RDC client. The endpoint returned HTTP 200 during the read-only audit. The user manager reports `network-online.target` as `not-found`, so the unit will not claim a dependency it cannot actually load.
- Boot activation: `WantedBy=default.target`; user linger is already `yes`, so no linger mutation is planned.
- Logs go to the user journal. The old RDC log is left untouched.
- No Hermes gateway unit/config/source changes, release/model-provider/Gemini changes, agent-initiated credential changes, forced re-pairing, or VPS reboot. The installed RDC client's own refresh/rotation is allowed as explicitly decided.

## Testing Decisions

- Add a static unit-contract regression test first and demonstrate RED before adding the unit source; then show GREEN and run `systemd-analyze --user verify` against the candidate unit.
- After the owner gate, verify the installed unit is loaded, enabled, and active; verify `Restart=always`, `RestartSec=5`, the explicit environment/working directory, and the startup readiness gate from systemd properties and the unit file.
- Verify one intended RDC transport instance is connected/ready from fresh service journal output. Record its PID and `/proc/<PID>/cgroup`; prove its cgroup contains `chatgpt-rdc.service` and not `hermes-gateway.service`.
- Retire only a positively identified obsolete RDC launcher after the service is ready. If no old launcher/autostart exists, record that no removal was needed. Do not kill or alter unrelated tmux sessions.
- Perform exactly one detached, controlled restart of `hermes-gateway.service`. Verify gateway recovery and the same RDC service/process remains active and connected/ready afterward. Do not repeat the restart as a retry.
- Verify persistent enablement and `loginctl` linger state. Do not reboot; actual post-reboot execution remains untested.
- Do not inject a deliberate RDC process kill solely to test `Restart=always`; validate that behavior through the live unit's configured properties without risking the persisted auth session. This task requires config proof, not a token-consuming crash experiment.

## Out of Scope

- Any modification to Hermes gateway behavior or its cleanup hook.
- Any change to release, model-refresh, provider, or Gemini work.
- Manual auth/token changes, logout, browser pairing, or exposing credential values.
- Removing or changing unrelated tmux sessions, systemd units, cron jobs, or scripts.
- Full VPS reboot or a claim that reboot persistence was behaviorally tested.
- GitHub push, merge, or publication without the repository's exact-SHA owner approval.

## Further Notes

- Evidence sources inspected: `/home/ubuntu/.config/systemd/user/hermes-gateway.service` (cleanup hook); `/home/ubuntu/.hermes/logs/remote-desktop-commander.log` (historical tmux/npx command and auth/ready/offline sequence); cached package metadata/source under `/home/ubuntu/.npm/_npx/4b4c857f6efdfb61/node_modules/@wonderwhy-er/desktop-commander/`; and the live persisted-config metadata only (no values).
- The historical command used the floating npm tag `@latest`; one direct npm registry response reported `0.3.0` while the installed cache contained `0.2.51`. Owner explicitly selected `0.2.51`; the service will not use `@latest`. The pinned package is available from the registry (`HTTP 200`, version `0.2.51`). If npm cache is later evicted, startup may need registry access to restore this exact version; it will not silently select a newer version.
- Approval boundary: Phase 4 was explicitly authorized on 2026-10-14 for the pinned `0.2.51` service/source changes and exactly one gateway restart after RDC reaches ready state. Client-owned session refresh is accepted; device reauthorization and reboot are not. GitHub push/PR/merge remain held by owner choice.
