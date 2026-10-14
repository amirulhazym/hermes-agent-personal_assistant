# 01 — Define the dedicated RDC service contract

**What to build:** The owner can inspect a source-controlled `chatgpt-rdc.service` declaration whose recovered launch, authentication boundaries, network gate, cgroup isolation, restart policy, and boot activation are covered by a focused regression test.

**Blocked by:** None — can start immediately after xcute Phase 3 approval.

**Status:** ready-for-agent

- [ ] Pin the launch to `/usr/bin/npx -y @wonderwhy-er/desktop-commander@0.2.51 remote` (owner-selected), use the observed ubuntu working directory, and do not invent CLI flags or expose auth values.
- [ ] Provide a dedicated service cgroup, `Restart=always`, `RestartSec=5`, bounded SIGTERM shutdown, and `WantedBy=default.target`.
- [ ] Gate startup on the observed public RDC bootstrap endpoint, because `network-online.target` is absent from the user manager.
- [ ] Add a static regression test and demonstrate RED before adding the unit, then GREEN plus systemd unit verification.
- [ ] Keep gateway, model/provider/release/Gemini, and persisted auth bytes out of the source diff.
