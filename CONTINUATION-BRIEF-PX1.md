# Hermes Agent Overhaul — CONTINUATION BRIEF PX-1 (Research Track)

> **Attach this file.** Also open: `PX1-RESEARCH-TRACK-PLAN.md`
> + `docs/superpowers/specs/2026-07-14-px1-research-journey.md`.
> P4 is **ON HOLD** — see `CONTINUATION-BRIEF-P4.md`.
> **Do not touch med logic** (`med_*`, `chain_*`, `med-auto-confirm`, med JSON).

---

## 0. ROLE & MANDATE

You are executor for **PX-1 Research Capability Track** (post-P3, parallel to held P4).

**Current state:** Fasa 0–2 + Multi-Key Capacity **DONE** on VPS. Next = Fasa 3+.
Search, extract, research expert skill, and 11-key Tavily pool are all live.
Do **NOT** re-install deps, re-configure search, or re-debug Turnstile paths.

**Goal:** Advance the Research Expert from "skill deployed" to "verified, traced, proven
end-to-end in user chat" — then open the Web Operator track (PX-1b).

**Principles:** evidence-first · incremental · per-step user go · zero/low cost ·
compose don't rebuild · Research Expert composes skills/tools (skills ≠ expert).

## 1. HARD CONSTRAINTS

| Rule | Detail |
|---|---|
| No med touch | Never modify med_*, chain_*, med-auto-confirm, med JSON |
| Concurrency | depth=1 / max=3 children **hard default** |
| Cost | Prefer free/self-host; **Tavily needs key + user OK** before enable |
| Paid | No paid service without explicit yes |
| Push | **No git push** unless user says so |
| Secrets | Never print API key values; env names only |
| Context | hy3-free 60% hard stop — fresh session if near limit |
| MJ | Verifier only; only OpenCode changes VPS |

## 2. WHY PX-1 NOW (not full P4)

- P4 multi-agent OS redesign is **held** (too large; vision captured in HOLD doc).  
- PX-1 is a **shippable vertical**: Research Expert + tools — feeds later P4 patterns.  
- Not redundant with P0–P3 med work; does not require finished OS spine to start Fasa 0.

## 3. LIVE STATE (validated 2026-07-14)

| Item | State |
|---|---|
| `web.backend` / search | **`search-cascade`** (Tavily → DDGS, 11 keys in pool) |
| `web.extract_backend` | **`hybrid-web`** (ABC-compliant, trafilatura→crawl4ai→Playwright) |
| Plugin | `~/.hermes/plugins/hybrid-web/` + `~/.hermes/plugins/search-cascade/` |
| trafilatura in venv | **True** (installed via uv) |
| crawl4ai in venv | **True** (installed via uv) |
| playwright in venv | **True** (+ Chromium) |
| Chromium | Installed on VPS (~300MB) |
| 11 Tavily keys | In VPS `.env` (free tier pool) |
| Research Expert | Deployed: `~/.hermes/skills/experts/research-expert/` |
| Usage log | `~/.hermes/logs/tavily_key_usage.jsonl` |
| Gateway | Active, Telegram + WhatsApp connected |

## 4. USER DECISIONS (2026-07-14)

| Topic | Decision |
|---|---|
| Sequence | Freeze P4 → PX-1 Fasa 0–2 + multi-key done |
| Tavily | **Yes — 11 free keys in pool** (multi-account, no paid) |
| SearXNG | **Later** — not needed with 11-key Tavily pool |
| Playwright + Chromium | **Installed and working** |
| Multi-key | **11 keys in VPS .env + rotating pool + usage log** |
| Signup pipeline | **PC ops only** (not agent skills) |
| Next | **Fasa 3** (platform verification + trace log) |
| P4 | ON HOLD |

## 5. PHASED PLAN (Fasa 0–2 done; execute Fasa 3 next)

### Fasa 0 — Foundation fix — DONE (2026-07-13)
Deps installed via `uv pip`, Chromium installed, hybrid-web extract working. Backups created.

### Fasa 1 — Search backend + fallback — DONE (2026-07-13)
`search-cascade` plugin active: Tavily primary (11 keys), DDGS fallback. MCP Tavily tools.

### Fasa 2 — Research Expert + pipeline — DONE (2026-07-13)
`~/.hermes/skills/experts/research-expert/` deployed. Pipeline + artifact format + smoke test. Commit `ce3d593`.

### Multi-Key Capacity — DONE (2026-07-14)
10 new Tavily accounts via CDP Chrome + QRYPTY. 11 keys total in VPS pool. Usage log active.

### Fasa 3 — Platform verification + logging (START HERE)
Cross-check, freshness, contradictions; research trace log (like med_chain_trace). Leverage SOUL grounding rules. **Full detail:** `PX1-RESEARCH-TRACK-PLAN.md`.

### Fasa 4 — Knowledge layer contract (Obsidian prep)
Read/write policy + artifact format; stub Knowledge interface. **Not** full Obsidian product.

### Fasa 5 — E2E validation
One full research workflow; fallback under failure; quality vs baseline.

## 6. REORIENTATION (run first in new session)

```bash
# Local
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" status
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" log --oneline -5

# Open these files
# CONTINUATION-BRIEF-PX1.md (this file)
# PX1-RESEARCH-TRACK-PLAN.md
# docs/superpowers/specs/2026-07-14-px1-research-journey.md (journey + anti-repeat)
# CONTINUATION-BRIEF-P4.md (HOLD only)

# VPS: verify live state
ssh -o ConnectTimeout=10 ubuntu@119.28.119.151 'systemctl --user is-active hermes-gateway'
ssh ubuntu@119.28.119.151 'grep -nE "backend|extract|search-cascade|hybrid" ~/.hermes/config.yaml | head -20'
ssh ubuntu@119.28.119.151 'grep TAVILY_API_KEYS ~/.hermes/.env | tr "," "\n" | wc -l'
ssh ubuntu@119.28.119.151 'ls ~/.hermes/plugins/ ~/.hermes/skills/experts/research-expert/'
ssh ubuntu@119.28.119.151 'tail -3 ~/.hermes/logs/tavily_key_usage.jsonl'
```

## 7. ENVIRONMENT

- VPS: `ubuntu@119.28.119.151` · home `/home/ubuntu`
- Hermes: `~/.hermes/` · venv: `~/.hermes/hermes-agent/venv`
- Gateway: `systemctl --user restart hermes-gateway` (only if needed; verify after)
- Local branch: `overhaul/exec` · VPS hermes git: `hermes-local`
- Backups: `~/hermes-overhaul-backup/pre-px1/` already created
- Journey doc: `docs/superpowers/specs/2026-07-14-px1-research-journey.md`

## 8. DELIVERABLES (end of PX-1)

- [x] hybrid-web extract works (+ Playwright where needed)
- [x] Search: Tavily + DDGS fallback (11-key free pool)
- [x] `skills/experts/research-expert/` deployed
- [x] Deep-research pipeline + artifact handoff
- [ ] Platform verification + research trace log
- [ ] Knowledge layer contract doc
- [ ] One E2E documented example (from Telegram/WhatsApp)

## 9. RISKS

| Risk | Mitigation |
|---|---|
| VPS disk/RAM (Playwright) | 5.9Gi swap; monitor before heavy extract |
| Tavily key exhaustion | DDGS fallback; 11 keys in pool; watch usage log |
| Context blowup | Fasa-per-session if needed |
| Accidental med edit | Explicit path denylist; never open med files |
| Skill trigger not firing | Verify E2E from actual chat (Fasa 5) |

## 10. FIRST ACTIONS IN NEW SESSION

1. Read `docs/superpowers/specs/2026-07-14-px1-research-journey.md` first.  
2. Run reorientation commands (section 6).  
3. Do **NOT** re-install deps, re-configure search, or re-debug Turnstile.  
4. **Fasa 3 only** → evidence → STOP for user gate.  
5. The winning CDP signup pipeline is on PC only (Section 6.10 of Journey).

---

*End CONTINUATION-BRIEF-PX1.md — start here for next context window.*
