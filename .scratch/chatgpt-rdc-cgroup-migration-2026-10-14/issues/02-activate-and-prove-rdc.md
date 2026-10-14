# 02 — Activate the isolated RDC service

**What to build:** The existing authorized RDC device is served by exactly one active systemd-supervised process tree outside the gateway cgroup, without tmux, duplicate launchers, or credential re-pairing.

**Blocked by:** 01 — Define the dedicated RDC service contract.

**Status:** ready-for-agent

- [ ] Install and enable the user unit under `default.target`; preserve the current RDC authentication artifact without displaying or manually modifying it.
- [ ] If the client requests browser authorization or reports an invalid persisted session, stop and ask the owner; do not reauthenticate.
- [ ] Prove `chatgpt-rdc.service` active/enabled, one intended RDC transport instance, and its normal connected/ready log state.
- [ ] Record its PID and `/proc/<PID>/cgroup`; prove it is in the RDC service cgroup and outside `hermes-gateway.service`.
- [ ] After the new service is ready, inspect for the old tmux/autostart path and remove only a positively identified duplicate. If none exists, record no removal required.
- [ ] Prove Restart policy and user-manager linger/enablement; do not reboot.
