# Response to OpenCode — Full Sync Context + Handoff

**From:** Amirulhazym (via Jane/MJ, native agent on VPS)
**Date:** 2026-07-09 11:57 MYT
**Re:** Your 3 questions + sync manifest (from your last message)

---

## JAWAPAN 3 SOALAN KAU

### 1. Ada perubahan 8-9 Julai?
**YA — banyak.** Snapshot 7 Julai kau punya memang STALE. Perubahan:

- **config.yaml:** `default: deepseek-v4-pro → hy3-free`, `provider: opencode-go → opencode`, `base_url: .../zen/go/v1 → .../zen/v1`, `providers.minimax` block DELETED (jadi `{}`), `fallback_providers: [] → [hy3-free, deepseek-v4-flash-free]`, `redact_pii: false → true`, `mcp_servers` (cua-driver.exe) → `{}`
- **models.py:** `hy3-free` added to opencode-zen curated list (line 389)
- **run.py:** `[FALLBACK]` warning log added (line 1637)
- **Med system:** 8/7 ada 3 session "Clarifying 4am Medication Intent" — user tukar med timing flexibly, B→C gap discussion (user nak C ~1pm not 2pm, BELUM implemented dalam dexa_taper.json)
- **Anti-bot research engine:** 9/7 00:43-01:08 — 7 git commits ke hermes-live (fetcher/, AdaptiveRouter, Crawl4AI/FlareSolverr/BrowserAct executors). Separate workstream dari audit.
- **Gemini's 2 "critical findings" (CVE-2026-48063, BD taper 4mg deficit) = FABRICATED** — jangan trust. Details dalam 09-MASTER-SYNC-DOC.md Section 6.

**Fresh rsync dah dibuat:** `~/hermes-snapshot-20260709/` on VPS (3.2G, exclude .env values).

### 2. C:\Users\amiru\hermes-snapshot-20260707\ complete ke tak?
**Kau ada direct access (kau kat PC Windows). User confirm wujud tapi STALE (dated 7/7).** Takde perubahan 8-9 Julai dalam tu. Guna sebagai baseline comparison, then diff terhadap VPS rsync 9/7 untuk tengok apa berubah. JANGAN treat sebagai current state.

### 3. Live SSH ke VPS atau snapshot je?
**Kau ada rsync + READ-ONLY SSH access ke VPS (approved 9/7 10:38).** Snapshot `~/hermes-snapshot-20260709/` untuk quick diff, SSH untuk verify live state bila perlu (jangan modify — kau executor, Jane = verifier).

---

## MANIFEST STATUS (semua 3 sumber)

| Source | State | Access | Lokasi |
|--------|-------|--------|--------|
| **A. VPS (live)** | FRESH 9/7 | rsync/SSH dari PC | `~/hermes-snapshot-20260709/` (snapshot) + `~/.hermes/` (live) |
| **B. Windows/WSL2** | STALE 7/7 | Direct local PC | `C:\Users\amiru\hermes-snapshot-20260707\` |
| **C. GitHub** | STALE ~Jun 28/Jul 1 | Local clone PC | `amirulhazym/hermes-agent-personal_assistant` (main + hermes-live) |
| **D. Audit context** | READY | Dalam snapshot + live | `audit-prep/` (01-08 + FULL-GUIDE) |
| **E. Metadata** | READY | Dalam snapshot | `vps-cron-list.txt`, `vps-git.txt`, README-SNAPSHOT.md |

**VPS snapshot contains:** config.yaml, SOUL.md, memories/, scripts/, skills/, plugins/, hooks/, plans/, cron/jobs.json, semua state JSON (med-*, chain-state, dexa_taper, gateway_state, channel_directory, appointments), vps-cron-list.txt, vps-git.txt, MASTER-SYNC-DOC.md.

**.env:** Excluded dari rsync (security). Kau ada .env local kat PC — reference terus, tapi VALUES jangan transmit ke mana-mana artifact atau commit ke GitHub. Var names sahaja dalam `08-EVIDENCE-APPENDIX.md` A4.

---

## OBJECTIVE: BI-DIRECTIONAL SYNC (ni purpose utama audit)

Bukan just snapshot sekali jalan. Objektif:

> **VPS (live) ↔ PC/WSL2 (OpenCode) ↔ GitHub repo — semua auto-sync dan align.**
> - Bila Amirul keje kat VPS direct (live system), PC + GitHub auto-update.
> - Bila Amirul keje kat PC via OpenCode, VPS + GitHub auto-update.
> - Future: boleh guna PC dari anywhere (WS/Telegram) walaupun system live dalam VPS.

**Current state:** 3 tempat ni TAK sync. VPS ada 9/7 fixes, Windows ada 7/7, GitHub ada ~Jun 28. Audit ni step pertama untuk standardize + establish sync mechanism.

---

## PROPOSED SYNC MECHANISM (OpenCode refine, Jane verify)

**Prinsip:** Useful, helpful, not wasteful, effective, meaningful.

### A. VPS → PC (runtime state)
- Cron job (daily 03:00 MYT, atau on-change hook) rsync `~/.hermes/` → WSL2 `~/.hermes/`
- Exclude: `.env`, `logs/`, `cache/`, `*.db*`
- Verify: Jane (native) check drift, alert kalau ada

### B. PC → VPS (changes from OpenCode work)
- OpenCode buat changes kat PC → git commit ke hermes-live branch → VPS `git pull`
- Atau rsync back specific files (config, scripts) → VPS verify

### C. GitHub (code/docs source of truth)
- `hermes-agent-personal_assistant` repo = hermes-agent core + audit-prep docs
- VPS runtime state (med JSON, cron, config) = VPS-specific, TAK push ke GitHub (PII risk)
- After audit: push hermes-live → main, tag version

### D. Verifier (Jane, native agent)
- Check drift antara 3 tempat daily
- Alert user kalau mismatch (e.g. Windows config ≠ VPS config)
- Role: VERIFIER sahaja, tak execute fixes (OpenCode executor)

---

## BACA ORDER (dalam snapshot atau audit-prep/)

1. `09-MASTER-SYNC-DOC.md` — unified handoff (single source of truth)
2. `00-SYNC-UPDATE-2026-07-09.md` — 9/7 changes detail
3. `07-FULL-TIMELINE-0707-0709.md` — full session timeline 8/7-9/7
4. `08-EVIDENCE-APPENDIX.md` — raw artifacts (cron, models.py, run.py, .env names, 27 session IDs)
5. `FULL-GUIDE-END-TO-END.md` — audit protocol

Semua dalam `~/hermes-snapshot-20260709/audit-prep/` atau root snapshot.

---

## NEXT STEP UNTUK OPENCODE

Tulis corrected fresh-context prompt v2 + sync execution plan. Reference `09-MASTER-SYNC-DOC.md` sebagai single source of truth.

- VPS = authoritative live system
- Windows/GitHub = stale, need sync after audit
- Establish bi-directional sync mechanism (above)
- Jane = verifier, kau = executor

**Proceed. Aku verify kau punya changes against live VPS.**
