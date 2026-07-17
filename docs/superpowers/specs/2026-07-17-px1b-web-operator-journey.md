# PX-1b Web Operator — Journey (This Context Window)

> **Date span:** 2026-07-17 (single continuous planning → implementation → acceptance arc)  
> **Branch:** `overhaul/exec`  
> **Outcome:** Formal acceptance **20/20 PASS**  
> **Audience:** future agents and Amirul for continuation after this session

This document is the narrative of **what was done in this chat context**, from the earliest
status questions through design execution, live wiring, Telegram/WhatsApp smokes, L4 bridge,
commit readiness, and what comes next. It complements (does not replace) the locked design,
implementation plan, live contracts, findings, and acceptance evidence files.

---

## 0. Starting point (before this arc “felt” done)

### Already true entering the window

- Hermes personal assistant base on VPS was live (Telegram + WhatsApp).
- Overhaul **P0–P3** and **PX-1 Research** were treated as done/live.
- PX-1b had **design + plan approved** and a **software package unit-tested**, with an
  earlier deploy of package/skill/triggers to VPS.
- Phase 0 live inventory existed (`docs/px1b-live-contracts.md`).
- Formal Research Expert chat pipeline was only **PARTIAL** (tools work; formal
  `research_trace.jsonl` / standard artifact package not always written).

### What was *not* true yet

- Adapters still returned `needs_live` without injected Hermes callables.
- No clean claim of production Web Operator acceptance.
- PC CUA was scaffold/status only; `computer_use.enabled` honesty gap.
- Frozen **20/20** suite not completed.

---

## 1. Orientation questions (start of this window)

### “What did we do so far?”

Session summary reconstructed the arc: design lock → plan → package on `overhaul/exec` →
unit tests → deploy foundation → residuals listed. Emphasized: **package ≠ production done**.

### “Are P0–P3 until PX-1 fully done and live on VPS (WA + Tele)?”

Honest split:

| Track | Status |
|---|---|
| P0–P3 + base Hermes | Done & live (TG + WA) |
| PX-1 Research tools | Done & live (chat usable) |
| PX-1 formal package/trace | Residual PARTIAL |
| PX-1b | Deployed foundation, **not** acceptance-complete |

### “Apa planning supaya PX-1b consider as done?”

Wave plan locked:

1. Live wiring  
2. Public L1–L3 phone proof  
3. Auth/actions/privacy proofs  
4. PC CUA  
5. Clean 20/20 + docs  

Definition of done = design §9 **20/20**, no silent waiver.

Human approved: **execute all waves until DONE**, full access (VPS + PC + files).

---

## 2. Execution doctrine used

- Skills: executing-plans, verification-before-completion, systematic-debugging when stuck.
- AGENTS.md / PRD §7: no secret printing; ask before commit/push (later approved);
  no paid browser cloud; no Hermes silent upgrade (stay **v0.17.0**); no med_* touch.
- Branch discipline: **`overhaul/exec` only** (feature worktree abandoned earlier by choice).
- Honesty labels: VALIDATED / PARTIAL / PENDING / REJECTED — no fake 20/20.

---

## 3. Wave 1 — Live wiring (VPS)

### Problem

`ResearchExecutor` / `NativeBrowserExecutor` required injected callables; CLI built
unwired executors → `needs_live`.

### Work

| Addition | Purpose |
|---|---|
| `live_wiring.py` | Discover Hermes root; import `browser_*` + `web_search_tool` / `web_extract_tool` |
| `factory.py` | Build operator with live callables when not fixture mode |
| CLI `wire-status`, `run-live`, `write-default-config` | Ops surface |
| Coordinator multi-step L3 | navigate + snapshot; cleanup after task |
| Policy public URL / static fetch allow | L1 path not stuck on “unclear intent” |

### Proof

- VPS unit tests: **35–37 OK** (grew with new tests).
- `wire-status`: browser + search + extract **true**.
- L1 static `example.com` → HTTP 200, route `L1`, VALIDATED.
- L3 browse `example.com` → heading **Example Domain**, VALIDATED (~3–4s).
- Gateway remained **active** after L3; concurrency production stayed **1**.

---

## 4. Wave 2–3 — Public core + safety package proofs

### Automated / package-level

Acceptance suite covered:

- Network fail-closed (loopback/private/metadata/file/js)
- Approvals single-use + mutation
- Form double approval
- External send / file quarantine policy
- Takeover observation suspend (canary not emitted)
- Medical artifact isolation + no med_* package touchpoints
- CAPTCHA/farming not auto-allowed
- Budget hard-stop
- L2→L3 escalation logging

### Config honesty

- `computer_use.enabled` set **false** when no real Hermes MCP CUA path
  (project L4 bridge later is separate — still not “native MCP CUA”).

---

## 5. Phone smokes — WhatsApp PASS, Telegram root-cause fix

### WhatsApp (first try)

Message: `click through https://example.com and tell me the page title`  
Result: `browser_navigate` → title **Example Domain** → **case 2 PASS**.

### Telegram (first try failed)

`/browse open https://example.com...` →  
`Unknown command /browse. Type /commands...`

**Root cause (systematic debugging):**  
Gateway treats leading `/` as **slash command**. `/browse` was neither built-in, plugin,
nor skill command key (`/web-operator` existed; `/browse` did not). Message never reached
agent or skill-trigger.

**Fix:**

1. `quick_commands.browse` = **alias → `web-operator`**
2. skill-trigger patterns for plain `browse open …` / `open https://…`
3. Gateway restart; TG + WA reconnected

### Telegram re-smoke (after fix)

- `/browse open https://example.com and summarize the main heading`  
  → L3, heading Example Domain, Label VALIDATED  
- `/web-operator ...` re-verify OK  
→ **case 3 PASS**.

---

## 6. Wave 4–5 — L4 bridge to true 20/20

Human chose **B**: finish formal 20/20, not “L1–L3 only residual L4”.

### Architecture chosen

Design required: PC **outbound-only**, no public CUA/VNC/CDP ports; VPS issues signed
grants; PC revalidates before acting.

**Implemented transport:** filesystem **mailbox** under  
`~/.hermes/web-operator/bridge/{devices,inbox,outbox,status,keys,consumed}`  
synced **PC → VPS / VPS → PC** via existing **SSH/SCP** (outbound from PC).

| Component | Role |
|---|---|
| `bridge.py` | VPS `BridgeControlPlane`: enroll, post grant, wait result, offline postpone |
| `pc_worker_runtime.py` | PC worker: heartbeat, verify/consume grant, allow-listed apps, `cua-driver call` |
| `adapters/pc_worker.py` | L4 executor wired to bridge |
| `windows/web-operator-bridge-sync.ps1` | SCP sync once/loop |
| `windows/web-operator-worker.ps1` | Enroll / Run / Stop |

### PC prerequisites fixed mid-stream

- Started `cua-driver serve` (daemon running); autostart registered.
- Local Windows Python lacked `cryptography` → installed free package (required for Ed25519 grants; already on VPS).

### Live L4 proofs

| Test | Result |
|---|---|
| Enroll device | `pc-7633a84681a0` on VPS |
| Heartbeat online | bridge-status online true |
| `open notepad named app via computer use` (VPS run-live) | L4 VALIDATED, grant nonce, Notepad launched |
| Wrong app `EvilAdminTool` | fail-closed `app not allowed` |
| Stale/offline heartbeat | `pc_offline` + **postpone** |
| L3 then L4 sequential | both completed VALIDATED |

### Acceptance suite final

VPS:

```text
PASS: 20  FAIL: 0  PARTIAL: 0  PENDING: 0
```

Manual live markers (TG/WA owner smokes + L4) recorded in  
`~/.hermes/web-operator/acceptance-manual.json` so suite does not under-claim proven phone paths.

Evidence file: `docs/px1b-acceptance-evidence.md`.

---

## 7. Issues encountered (journey log)

| # | Issue | Resolution |
|---|---|---|
| 1 | `needs_live` without wiring | `live_wiring` + `factory` + `run-live` |
| 2 | “static fetch” paused as unclear intent | Policy public-URL / static fetch allow |
| 3 | Telegram `/browse` unknown command | quick_command alias → web-operator |
| 4 | Acceptance over-claimed TG/WA on patterns alone | Tightened to PARTIAL until real chat; then manual live markers |
| 5 | PC crypto missing | `pip install cryptography` on Windows Python 3.13 |
| 6 | L4 not production without bridge | Mailbox + signed grants + worker loop |
| 7 | CUA doctor WinSta0 warning in some contexts | Daemon still ran list_apps/launch_app successfully from this session |
| 8 | SSH/PowerShell quoting hell for remote Python | Prefer scp of scripts then `python3 /tmp/...` |
| 9 | `computer_use.enabled` honesty | Left **false**; project bridge ≠ Hermes MCP CUA claim |
| 10 | Formal Research Expert package residual | Documented; not blocking PX-1b compose path |

---

## 8. Final state snapshot

### Code / docs (repo)

- `scripts/web_operator/` — full package including bridge, acceptance suite, live wiring
- `skills/experts/web-operator/` — skill + invocation docs
- `windows/web-operator-worker.ps1`, `windows/web-operator-bridge-sync.ps1`
- `docs/px1b-live-contracts.md`, `docs/px1b-findings.md`, `docs/px1b-acceptance-evidence.md`
- Design/plan under `docs/superpowers/specs|plans/2026-07-17-px1b-web-operator*`
- This journey: `docs/superpowers/specs/2026-07-17-px1b-web-operator-journey.md`

### VPS runtime

- Package at `~/.hermes/scripts/web_operator`
- Config `~/.hermes/web-operator/config.yaml` (`pc_worker.enabled: true`, transport mailbox)
- Bridge dirs + enrolled PC device
- skill-trigger patterns for browse / computer use / notepad
- Gateway active; Telegram + WhatsApp connected after restarts

### PC runtime

- `cua-driver` 0.7.1 daemon can run; autostart registered
- Local bridge under `%USERPROFILE%\.hermes\web-operator\bridge`
- Worker must be **Run** (sync loop) for L4; offline postpones by design

### Acceptance

**PX-1b formal 20/20 PASS (2026-07-17).**

---

## 9. What “next” means (planning after this journey)

PX-1b acceptance is closed. Natural next tracks (pick explicitly; do not invent paid scope):

### A. Ops hardening (recommended short follow-up)

1. Document/runbook: “how to start PC worker after reboot”
2. Optional Windows Task Scheduler for `web-operator-worker.ps1 -Action Run`
3. Retention purge cron for web-operator artifacts (14-day policy)
4. One more owner phone smoke after any gateway restart (TG `/browse`, WA click-through)

### B. PX-1 residual repair (narrow)

- Formal Research Expert chat path writing `research_trace.jsonl` + standard artifact package
- Only if still painful in daily use

### C. Overhaul / product next (outside PX-1b bar)

- Deeper private takeover real-site drills (owner-approved low-risk only)
- Medical portal isolated real flow (owner-only, no med_* writes)
- Qwen/Sakana comparison only after CUA path stable (design optional)
- Do **not** silent-upgrade Hermes to 0.18.x without explicit decision

### D. Process

- Commit/push this RC (requested)
- Update CONTINUATION brief if starting a new session for Overhaul V2 / next PX

---

## 10. Timeline (compressed)

```text
Status check → “what is done?”
     ↓
Define DONE = 20/20 waves
     ↓
Approve full execution
     ↓
Wave 1 live wiring (L1–L3 VALIDATED on VPS)
     ↓
Safety suite + honesty config
     ↓
WA PASS; TG /browse bug → fix → TG PASS
     ↓
Choose B: finish L4 for 20/20
     ↓
Mailbox bridge + PC enroll + Notepad L4
     ↓
Fail-closed + offline postpone + L3/L4 workflow
     ↓
Acceptance 20/20 PASS
     ↓
Journey doc + commit/push + next plan
```

---

## 11. Key file index for future agents

| File | Why open first |
|---|---|
| `docs/superpowers/specs/2026-07-17-px1b-web-operator-design.md` | Locked product rules |
| `docs/px1b-acceptance-evidence.md` | 20/20 evidence |
| `docs/px1b-live-contracts.md` | Live Hermes API truth (v0.17.0) |
| `docs/px1b-findings.md` | Residuals / honesty |
| `scripts/web_operator/bridge.py` | L4 control plane |
| `scripts/web_operator/live_wiring.py` | How tools attach |
| `windows/web-operator-worker.ps1` | PC side entry |
| `PROGRESS.md` | Tracker checkboxes |

---

**End of journey record.**  
Status at close of this document: **PX-1b DONE (20/20).** Next work is ops hardening or a new track, not re-opening PX-1b acceptance without regression evidence.
