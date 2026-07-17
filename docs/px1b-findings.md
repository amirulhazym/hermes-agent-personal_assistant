# PX-1b Findings Log

> Accumulated residuals and issues during full PX-1b build on `overhaul/exec`.
> Final summary filled when implementation package + local tests complete.

## Open / residual issues

1. **Telegram formal Research Expert pipeline residual (Phase 0 PARTIAL)**  
   Chat trigger + Tavily + hybrid-web work, but `research_trace.jsonl` and standard `research/artifacts/YYYY-MM-DD-*` package were not written for the 2026-07-17 chat E2E. Alternate file written instead.

2. **Live Hermes version lag**  
   Live is v0.17.0 while docs/releases describe 0.18.x. Policy: keep live version; adapters must not assume unreleased APIs without discovery.

3. **`computer_use.enabled: true` honesty gap**  
   Flag true without enrolled outbound PC worker / live MCP cua path in config.

4. **Native browser has no download/upload tools**  
   Project file adapters implemented; live browser wiring still needs approved deploy + live callable injection.

5. **Native browser / research callables not wired in local unit environment**  
   Executors return `needs_live` until VPS deploy injects live functions.

6. **CUA daemon not running / autostart not registered**  
   Local status scaffold only; production enroll/run requires explicit PC operator steps.

7. **Worktree abandoned mid-stream**  
   Human chose `overhaul/exec` only; feature branch/worktree not used for final line.

## Closed in this package

- Project-owned policy/approvals/network/artifacts/coordinator package with unit tests
- Session/file/takeover/grant/protocol modules
- Web-operator skill pack + config templates + deploy dry-run script
- Windows status/worker scaffolds (outbound-only posture)
- Local verification: 32 tests OK, 3 skipped (no local cryptography)

## Still not “live production complete”

These require separate explicit human approvals and/or live environment actions:

- Deploy package to VPS (`sync/deploy-web-operator.sh --apply`)
- Gateway restart after deploy
- Wire live `web_search_tool` / `web_extract_tool` / `browser_*` callables into adapters on VPS
- skill-trigger pattern additions for web-operator
- computer_use honesty config fix
- PC worker enroll + cua-driver daemon/autostart decisions
- Measured L3 concurrency benchmark on live RAM
- Frozen 20/20 acceptance cases on real phone/PC paths

## Final status (package line)

**PX-1b software package on `overhaul/exec` is implemented and unit-tested.**  
**PX-1b production acceptance is NOT complete** until the live items above pass.
