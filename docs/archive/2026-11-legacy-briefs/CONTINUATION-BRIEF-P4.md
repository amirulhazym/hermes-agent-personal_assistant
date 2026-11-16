# Hermes Agent Overhaul — CONTINUATION BRIEF P4 (ON HOLD)

> **Attach with `OVERHAUL-EXECUTION-PROMPT.md` if resuming P4.**  
> **P4 STATUS: ON HOLD (2026-07-13).** Do **not** execute multi-agent OS build.  
> **Next executable track: PX-1** → open `CONTINUATION-BRIEF-PX1.md` + `PX1-RESEARCH-TRACK-PLAN.md`.
>
> Full architecture freeze (vision, layers, depth/fan-out, P4 vs P5/P6, decisions):  
> `docs/superpowers/specs/2026-07-11-phase4-os-vision-HOLD.md`

---

## 0. ROLE & MANDATE

You are strategic advisor + executor for Hermes overhaul (`amirulhazym`).  
Med/gateway P0–P3 are done. P4 multi-agent OS is **architecture-held**.  
**MJ = verifier only. OpenCode = executor. Local commits yes; push NO.**

## 1. WHY HOLD

First P4 draft = three experts wrapping existing work (too narrow).  
User vision = **Personal AI OS** (many domain experts, handoffs, knowledge layer,
self-improve, personal + OVIS consulting). Correct but too large to force-ship now.  
**Decision:** freeze discussion; run **PX-1 Research vertical** next.

## 2. COMPLETED BEFORE P4 (do not re-do)

| Phase | Result |
|---|---|
| P0 | Pattern G, paths, MiniMax plugin, session 700, PII gitignore |
| P1 | med_chain v3, 21 tests, freeze-safe chain_calc + hook |
| P2 | Akurit-2 + med-status date rule |
| P3 | Versioning, restart reliability, memory trim, skill report, verify |
| P3 cleanup | Niche skills dropped; MINIMAX_API_KEY env line removed |
| P4 draft | Narrow design/plan written then **rejected as under-scoped**; OS vision discussed; **HOLD** |

## 3. LOCKED DECISIONS (P4 when resumed)

- Expert ≠ skill ≠ tool ≠ hook ≠ delegate ≠ memory ≠ knowledge ≠ router ≠ planner ≠ orchestrator  
- depth=1 / max=3 **hard default**; route 9+ experts via **staged + artifact handoff**  
- Connect, don’t rebuild Hermes runtime  
- Design skills (gsap/creative/UI) **keep**  
- Med regression **21/21** hard gate on any execute that could affect runtime  
- Push blocked  

## 4. WHAT TO OPEN WHEN RESUMING P4

1. `docs/superpowers/specs/2026-07-11-phase4-os-vision-HOLD.md` (primary)  
2. User redesign feedback (chat / saved notes)  
3. Z.ai `audits/zai-audits-0907/zai-audit-03-execution-plan.md` §8  
4. Live: `orchestrator_enabled`, max_spawn_depth, max_concurrent_children  

**Do not** treat the old “Med/Research/Ops wrapper” plan as the target architecture.

## 5. NEXT TRACK (not P4)

**PX-1 Research Capability Track** — separate from med; fix extract/search; Research Expert pipeline.  
Handoff: **`CONTINUATION-BRIEF-PX1.md`**.

## 6. ENVIRONMENT (unchanged)

- VPS: `ubuntu@119.28.119.151`  
- Hermes: `~/.hermes/` · gateway `systemd --user hermes-gateway`  
- Windows repo branch: `overhaul/exec` · VPS hermes git: `hermes-local`  
- Backups: `~/hermes-overhaul-backup/`

## 7. SESSION DISCIPLINE

- No P4 execute until explicit `go execute P4` after redesign approval.  
- hy3-free 60% hard stop.  
- No secrets in files; no push.

---

*P4 brief frozen ON HOLD. Prefer PX-1 for next work.*
