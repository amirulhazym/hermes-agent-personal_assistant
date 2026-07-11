# AUDIT & SYSTEM OVERHAUL — Panduan Lengkap End-to-End

> **Tarikh:** Selasa, 7 Julai 2026
> **Versi:** 1.0
> **Untuk:** Amirulhazym
> **Tujuan:** Guide lengkap dari mula sampai habis — selesaikan audit yang tertangguh

---

## KANDUNGAN

- [Phase 0: Background / Apa Dah Berlaku Hari Ini](#phase-0-background--apa-dah-berlaku-hari-ini)
- [Phase 1: Baca & Sahkan Audit-Prep Files](#phase-1-baca--sahkan-audit-prep-files)
- [Phase 2: Hantar ke AI Coding Agents](#phase-2-hantar-ke-ai-coding-agents)
- [Phase 3: Kumpul & Compare Semua Findings](#phase-3-kumpul--compare-semua-findings)
- [Phase 4: Prioritise & Plan Fixes](#phase-4-prioritise--plan-fixes)
- [Phase 5: Execute Fixes](#phase-5-execute-fixes)
- [Phase 6: Cross-Platform Sync (VPS ↔ WSL2 ↔ GitHub)](#phase-6-cross-platform-sync-vps--wsl2--github)
- [Phase 7: Maintenance & Follow-Up](#phase-7-maintenance--follow-up)

---

# Phase 0: Background / Apa Dah Berlaku Hari Ini

## 0.1 Ringkasan

Hari ni, kita dah buat beberapa benda penting sebelum saya kena context compaction (memory full). Benda yang **dah selesai**:

| Item | Status | Notes |
|------|--------|-------|
| Gateway restart (via `at`) | ✅ **Siap** | Pukul 13:48. Running sejak tu. |
| Day-boundary reset untuk reminder counts | ✅ **Siap** | Fix dalam `chain_monitor.sh` — reset counts setiap hari baru |
| Audit-prep files (4 files) | ✅ **Siap** | Kat `~/mjay/audit-prep/` |
| Morning Briefing cron terminated | ✅ **Siap** | Yang kau tak pernah request tu |

## 0.2 Apa Yang Belum Selesai (Benda Gantung)

| # | Benda | Sebab Tertangguh |
|---|-------|-----------------|
| 1 | Kau belum **baca & confirm** 4 audit-prep files tu | Lepas saya hantar, kau cuma "Okay thanks" |
| 2 | Kau belum **hantar ke AI coding agents** | Masih tunggu confirm dari kau |
| 3 | Kau belum **collect findings** dari agents tu | Belum start langsung |
| 4 | Kau belum **prioritise fixes** | Takde data lagi |
| 5 | Kau belum **sync VPS → WSL2 → GitHub** | Belum start |
| 6 | **SOUL.md** dalam git repo masih outdated (61 lines vs live 132 lines) | Sync gap |

## 0.3 Apa Itu 4 Audit-Prep Files?

| File | Isi | Saiz |
|------|-----|------|
| `01-VPS-BASELINE.md` | Semua info pasal VPS — system, cron jobs, scripts, plugins, state files, known issues | 19KB, 370 lines |
| `02-SYNC-GAP-ANALYSIS.md` | Cara nak compare VPS vs WSL2/Windows vs GitHub — apa yang berbeza dan kena sync | 7KB, 193 lines |
| `03-AI-AUDIT-PROMPT-TEMPLATE.md` | Prompt siap pakai — copy-paste ke mana-mana AI agent untuk audit sistem | 7KB, 185 lines |
| `04-EXECUTION-GUIDE.md` | Step-by-step guide untuk beginner (versi awal, sebelum guide ni) | 6KB, 233 lines |

## 0.4 Audit-Audit Terdahulu (Jun 28)

Ada 7 audit report dari hari tu:

| File | Auditor | Status |
|------|---------|--------|
| `zhipu1-audit.md` | Zhipu Chat | ✅ Complete (30KB) |
| `zhipu2-audit.md` | Zhipu Agent | ✅ Complete (90KB) |
| `zhipu-exploration-audit.md` | Zhipu (free-form) | ✅ Complete (30KB) |
| `qwen-audit.md` | Qwen | ✅ Complete (10KB) |
| `qwen-exploration.md` | Qwen (exploration) | ✅ Complete |
| `sakana-audit.md` | Sakana | ❌ **Not started** (75B — empty) |
| `claude-audit.md` | Claude | ✅ Complete (13KB) |
| `opencode-go-addendum.md` | MJ (saya) | ✅ Complete (4KB) |

**Masalah:** Audit ni dah lama (Jun 28). Banyak benda dah berubah — med system v2, SOUL.md overhaul, chain_llm.py baru, etc. So findings dia mungkin **outdated**. Tapi masih boleh guna sebagai reference.

---

# Phase 1: Baca & Sahkan Audit-Prep Files

**Anggaran masa:** 15-30 minit

## 1.1 Baca Ringkasan Setiap File

### File 1: `01-VPS-BASELINE.md`

Apa dalam ni:
- **System specs** — OS, RAM, disk, uptime, IP
- **Model & provider config** — opencode-go (paid), opencode-zen (free), NVIDIA (free), DeepSeek (CNY)
- **14 active cron jobs** — jadual penuh, status, deliver to mana
- **27 scripts** — semua `.py` dan `.sh` dalam `~/.hermes/scripts/`
- **2 plugins** — hybrid-web, lightclawbot (WhatsApp)
- **16 state files** — med-status.json, med-schedule.json, chain-state.json, etc.
- **110 skills** — 67 builtin + 43 local
- **16 known issues** — P0 sampai P3
- **mjay/ git repo state** — cabang hermes-live, last commit Jul 1

### File 2: `02-SYNC-GAP-ANALYSIS.md`

Ini framework untuk compare VPS dengan WSL2/Windows dan GitHub.
- Platform A: VPS (Singapore) — live production
- Platform B: WSL2/Windows (F:\AI Prep\OVIS\Hermes Agent\MJay\) — original dev environment
- Platform C: GitHub — version control

### File 3: `03-AI-AUDIT-PROMPT-TEMPLATE.md`

Prompt siap pakai. Bagi kat AI coding agent, dia akan audit sistem kau dari 11 dimensi:
1. Architecture
2. Security
3. Config & Models
4. Cron Jobs
5. Scripts
6. State Files
7. Documentation
8. Backup & Recovery
9. Cost
10. Medication System (critical!)
11. Cross-Platform Sync

### File 4: `04-EXECUTION-GUIDE.md`

Step-by-step versi ringkas. Guide ni (FULL-GUIDE-END-TO-END.md) adalah versi lengkap yang menggantikan file 4.

## 1.2 Confirm

Lepas baca, saya akan tanya: **"Confirm content ok? Nak adjust apa-apa?"**

Baru proceed ke Phase 2.

---

# Phase 2: Hantar ke AI Coding Agents

**Anggaran masa:** 30-60 minit

## 2.1 Pilih AI Agents

Guna **2-3 agents** untuk cross-reference. Cadangan:

| AI Agent | Kelebihan | Cara Guna |
|----------|-----------|-----------|
| **OpenCode** | Boleh baca files direct dari VPS | CLI/open in browser |
| **Claude** | Paling teliti untuk code analysis | Chat — upload files |
| **ZCode (Z.AI)** | Free-form exploration | Copy-paste prompt + files |
| **Qwen** | Cross-reference | Paste prompt |
| **Gemini** | Architecture review | Upload files |

Saya recommend: **OpenCode + Claude + 1 lagi** (pilihan kau).

## 2.2 Cara Hantar

Ada 2 cara:

### Cara A: AI Agent Ada Akses VPS

Kalau agent boleh access VPS direct:

```
Bagi path ni:
/home/ubuntu/mjay/audit-prep/01-VPS-BASELINE.md
/home/ubuntu/mjay/audit-prep/02-SYNC-GAP-ANALYSIS.md
/home/ubuntu/mjay/audit-prep/03-AI-AUDIT-PROMPT-TEMPLATE.md
```

Prompt guna dari **File 3 (03-AI-AUDIT-PROMPT-TEMPLATE.md)** — copy bahagian "Quick Start".

### Cara B: Upload Manual

1. Buka AI agent
2. Copy prompt dari file 3
3. Upload file 1 dan file 2 sebagai attachment/context
4. Run

## 2.3 Prompt Yang Nak Guna

Prompt dah sedia dalam File 3. Tapi secara ringkas, suruh AI agent:
1. Baca semua files
2. Audit dari 11 dimensi
3. Guna evidence-first approach — jangan kata "kelihatan ok" tanpa bukti
4. Output ikut format: Critical → High → Medium → Low → Quick Wins
5. Bagi health score /10

## 2.4 Apa Kata Pada Setiap Agent

| Agent | Arahan Tambahan |
|-------|----------------|
| **Agent 1 (primary)** | "Do a DEEP AUDIT. Read ALL files. Check every claim with evidence." |
| **Agent 2 (adversarial)** | "Find what Agent 1 MISSED. Assume the first audit was overconfident." |
| **Agent 3 (optional)** | "Compare findings of Agent 1 and 2. Where do they agree? Disagree?" |

## 2.5 Simpan Semua Response

Lepas setiap agent selesai:
1. Copy paste response dia
2. Simpan dalam `~/mjay/audit-findings/agent1-opencode.md`
3. Atau simpan dalam chat — nanti saya tolong organize

---

# Phase 3: Kumpul & Compare Semua Findings

**Anggaran masa:** 1-2 jam

## 3.1 Buat Comparison Table

Guna format ni:

| Finding | Agent 1 | Agent 2 | Agent 3 | Consensus? | 
|---------|---------|---------|---------|------------|
| Gateway stale-state bug | ✅ Found | ✅ Found | ✅ Found | **Strong** — all agree |
| API keys not rotated | ✅ Found | ❌ Missed | ✅ Found | **Partial** — 2/3 |
| ... | ... | ... | ... | ... |

## 3.2 Tanda Priority

| Label | Maksud | Contoh |
|-------|--------|--------|
| **P0** | Boleh rosakkan sistem atau health | Med reminder fails, data loss, security breach |
| **P1** | Perlu settle dalam minggu ni | Sync gap, fragile scripts, broken pipe error |
| **P2** | Bulan ni | Cost optimisation, cleanup |
| **P3** | Boleh simpan dulu | Nice-to-have, refactoring |

## 3.3 Verifikasi Findings

Untuk setiap finding, tanya:
1. **Boleh saya verify sekarang?** — check VPS, check files, run command
2. **ATAU kena verify nanti?** — bila kau buka WSL2/PC
3. **ATAU just hyped/overclaimed?** — AI agent confident tapi actually takde masalah

**Yang dah sedia untuk verify terus dari VPS (tanpa PC):**
- Cron job errors — `hermes cron list`
- Gateway status — `systemctl --user status hermes-gateway`
- File content — saya boleh baca mana-mana file
- Script correctness — saya boleh baca scripts
- State files — saya boleh check med-status.json, chain-state.json

**Yang kena verify dari PC/WSL2:**
- Sync gap antara VPS dan WSL2
- WSL2 ada scripts yang VPS takde?
- SOUL.md version berbeza?

## 3.4 Buat Final List

Lepas verify, kita akan ada **Final Fix List**:

```
## P0 (Fix Hari Ni)
- [ ] Finding 1: ...
- [ ] Finding 2: ...

## P1 (Fix Minggu Ni)
- [ ] Finding 3: ...
```

---

# Phase 4: Prioritise & Plan Fixes

**Anggaran masa:** 30 minit

## 4.1 Uruskan Ikut Priority

| Priority | Bila Fix | Contoh |
|----------|----------|--------|
| **P0** | **Sekarang jugak** | Med system ada bug? Security hole? Data loss risk? |
| **P1** | **Hari ni / esok** | Cron errors, broken pipe, sync gap, doc outdated |
| **P2** | **Minggu ni** | Cost optimisation, cleanup, non-critical bugs |
| **P3** | **Simpan dulu** | Nice-to-have, refactor, design improvements |

## 4.2 Satu Fix Satu Masa

**Jangan try fix semua sekali.** Ikut cara ni:

```
1. Pilih 1 finding (P0 dulu)
2. Saya analyze — apa punca, apa perlu ubah
3. Kau confirm approach
4. Saya execute fix
5. Saya verify — run test, check output
6. Kau confirm fix ok
7. Repeat untuk finding seterusnya
```

**Rule:** Selesai satu, baru proceed seterusnya.

## 4.3 Guna --dry-run Untuk Semua Perubahan

Untuk apa-apa yang touch state files (med-status.json, chain-state.json, etc.):
```bash
python3 ~/.hermes/scripts/med_confirm.py --dry-run --reset ...
```
**Jangan terus touch production.** Always test dulu.

---

# Phase 5: Execute Fixes

**Anggaran masa:** bergantung pada jumlah finding (2-4 jam)

## 5.1 Sebelum Mula

1. Backup everything dulu:
```bash
cp ~/.hermes/med-status.json ~/.hermes/med-status.json.bak-$(date +%Y%m%d_%H%M)
cp ~/.hermes/chain-state.json ~/.hermes/chain-state.json.bak-$(date +%Y%m%d_%H%M)
cp ~/.hermes/med-schedule.json ~/.hermes/med-schedule.json.bak-$(date +%Y%m%d_%H%M)
```

2. Confirm dengan saya apa nak fix
3. Saya execute guna `--dry-run` dulu
4. Lepas ok, baru apply for real

## 5.2 Contoh Flow Fix

```
1. Kau: "MJ, fix [finding X]"
2. Saya: Analyze punca → propose fix → guna --dry-run → tunjuk result
3. Kau: "Proceed"
4. Saya: Apply fix → verify → confirm ok
5. Kau: "Next"
```

---

# Phase 6: Cross-Platform Sync (VPS ↔ WSL2 ↔ GitHub)

**Anggaran masa:** 1-3 jam

## 6.1 Apa Yang Kena Sync

| Platform | Peranan |
|----------|---------|
| **VPS (Singapore)** | Live production — 24/7 running |
| **WSL2/Windows** | Development environment — original source |
| **GitHub** | Version control — source of truth selepas sync |

## 6.2 Bila Nak Buat

**Sync hanya lepas semua P0 dan P1 fixes selesai.** Jangan sync broken state.

## 6.3 Langkah-Langkah

### Step 1: Buka PC & WSL2
- Turn on Windows
- Open WSL2 terminal
- Navigate ke project: `cd /mnt/f/AI\ Prep/OVIS/Hermes\ Agent/MJay/` (atau path sebenar)

### Step 2: Bandingkan SOUL.md
```
VPS (live): ~/.hermes/SOUL.md — 132 lines
WSL2: ??? (check)
GitHub (mjay/persona/SOUL.md): 61 lines (OUTDATED)
```

Keputusan: **VPS live adalah yang paling baru.** Guna VPS version sebagai source of truth.

### Step 3: Bandingkan Scripts
```
Check satu-satu:
- med_confirm.py — VPS ada drug-level tracking (Jul 7)
- chain_llm.py — VPS ada version baru (Jul 7)
- fix_models.py — VPS version (Jul 5)
- etc.
```

**Yang VPS lebih baru** → copy dari VPS ke WSL2
**Yang WSL2 lebih baru** → copy dari WSL2 ke VPS (saya boleh terima via git/SCP)

### Step 4: Bandingkan Cron Jobs
```
VPS: 14 active jobs (list dalam 01-VPS-BASELINE.md)
WSL2: ??? (check)
```

### Step 5: Sync ke GitHub
```bash
cd ~/mjay  # atau path WSL2
git add -A
git commit -m "sync: unified VPS + WSL2 state post-audit"
git push origin hermes-live
```

### Step 6: Create PR ke main
```
GitHub → Open pull request hermes-live → main
Review changes
Merge
```

---

# Phase 7: Maintenance & Follow-Up

## 7.1 Daily (5 minit)

- [ ] Check cron errors: `hermes cron list` — tengok ada yang error tak
- [ ] Confirm med reminders fire correctly

## 7.2 Weekly (15 minit)

- [ ] Check disk: `df -h /`
- [ ] Check memory: `free -h`
- [ ] Check gateway: `systemctl --user status hermes-gateway`
- [ ] Review sessions: ada apa-apa yang tertangguh?

## 7.3 Monthly (30 minit)

- [ ] Rotate API keys (NVIDIA, DeepSeek, OpenCode)
- [ ] Check Baileys WhatsApp library for updates
- [ ] Review MEMORY.md usage — ada yang boleh padam?
- [ ] Review USER.md — still accurate?

## 7.4 Selepas `hermes update` (15 minit)

```bash
python3 ~/.hermes/scripts/fix_models.py   # Restore curated model list
hermes doctor --fix                        # Auto-fix apa yang boleh
systemctl --user restart hermes-gateway    # Restart gateway
# Verify kedua-dua platform connected
```

---

# REFERENCE: Command Cheat Sheet

## System
```bash
# Current time
date '+%Y-%m-%d %H:%M:%S %Z'

# System health
df -h /
free -h
uptime

# Gateway
systemctl --user status hermes-gateway
hermes gateway status

# Cron jobs
hermes cron list
```

## Medication System
```bash
# Check status
python3 ~/.hermes/scripts/med_confirm.py --status
python3 ~/.hermes/scripts/chain_calc.py --display

# Confirm med (guna --dry-run dulu!)
python3 ~/.hermes/scripts/med_confirm.py B dexamethasone_2 --at 12:15 --dry-run

# Check state files
cat ~/.hermes/med-status.json
cat ~/.hermes/chain-state.json
cat ~/.hermes/med-schedule.json
```

## Git
```bash
# VPS
cd ~/mjay
git status
git log --oneline -5

# Compare with GitHub
git diff origin/hermes-live..origin/main --stat
```

## Files & Scripts
```bash
# List scripts
ls ~/.hermes/scripts/

# List audit files
ls -la ~/mjay/audit-prep/
ls -la ~/mjay/audits/

# Read file (guna ni instead of cat)
# guna saya — just cakap "MJ, baca file [path]"
```

---

# CHECKLIST MASTER — Boleh Tandakan Lepas Siap

## Phase 1: Baca & Sahkan Files
- [ ] Baca ringkasan 4 files
- [ ] Confirm content ok / minta adjust
- [ ] **Proceed?**

## Phase 2: Hantar ke AI Agents
- [ ] Pilih 2-3 AI agents
- [ ] Hantar prompt + files
- [ ] Simpan semua response

## Phase 3: Kumpul Findings
- [ ] Buat comparison table
- [ ] Tanda priority (P0/P1/P2/P3)
- [ ] Verify findings yang boleh verify dari VPS
- [ ] Buat Final Fix List

## Phase 4: Plan Fixes
- [ ] Uruskan ikut priority
- [ ] Confirm approach dengan saya
- [ ] Backup state files

## Phase 5: Execute Fixes
- [ ] Fix P0 items
- [ ] Fix P1 items
- [ ] Fix P2 items (optional untuk hari ni)

## Phase 6: Cross-Platform Sync
- [ ] Buka PC/WSL2
- [ ] Bandingkan SOUL.md
- [ ] Bandingkan scripts
- [ ] Bandingkan cron jobs
- [ ] Sync ke GitHub
- [ ] Create PR ke main

## Phase 7: Maintenance
- [ ] Confirm med system still running
- [ ] Confirm gateway healthy
- [ ] Set reminder untuk weekly checks

---

*Habis. Panduan ni akan dikemaskini berdasarkan findings dari AI agents nanti.*

**Next step:** Confirm Phase 1 — nak proceed baca files ke saya ringkaskan terus?
