# 03 — Prove RDC survives one gateway restart

**What to build:** The owner has direct before/after evidence that exactly one controlled Hermes gateway restart recovers the gateway while the separate RDC service and its connected transport remain alive.

**Blocked by:** 02 — Activate the isolated RDC service.

**Status:** ready-for-agent

- [ ] Capture gateway and RDC service/process/cgroup state immediately before the restart.
- [ ] Schedule exactly one restart outside the gateway process tree; do not retry it.
- [ ] Prove the gateway returned active/healthy with a new process start, and the RDC service remained active without its recorded transport PID being killed.
- [ ] Prove RDC remains connected/ready after the gateway restart and no duplicate tmux launcher exists.
- [ ] Report boot persistence from enabled user-unit state plus `Linger=yes`; explicitly leave full-reboot behavior untested.
