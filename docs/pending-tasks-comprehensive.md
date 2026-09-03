# ON HOLD / PENDING / UNRESOLVED — MASTER LIST
**Tarikh:** Wed 8 Jul 2026, 7:45 PM MYT
**Sumber:** Semua sessions (3 Jul - 8 Jul 2026)

---

## P0 — Sakit Kepala Sekarang Juga

| # | Item | Sejak | Notes |
|---|------|-------|-------|
| P0.1 | **Dexa BD Underdosing Defect** (P0 CLINICAL) | 7 Jul | chain_calc.py Slot C → dose_midday = 0 semasa BD phase. Starts 9 Sept. **Belum fix.** |
| P0.2 | **Vision 401 Error** — still broken | 3 Jul | api_key: '' dah buang dari config, tapi .env tak load ke process. Kena restart gateway dari EXTERNAL shell (SSH). |
| P0.3 | **Gateway .env not loaded** | 8 Jul | MINIMAX_API_KEY & OPENCODE_ZEN_API_KEY ada dalam .env tapi Hermes process tak nampak. Kena systemctl --user restart dari luar. |

---

## P1 — System Overhaul (yang kau maksudkan)

| # | Item | Sejak | Status | Details |
|---|------|-------|--------|---------|
| P1.1 | **FULL DEEP AUDIT — Phase 2 to 7** | 7 Jul | ❌ **Tergantung** | Gemini selesaikan Phase 1 (Security & Config). Phase 2-7 tak jalan langsung. |
| P1.2 | **Chain Integrity System (CIS) Spec v3** | 8 Jul | ❌ **Belum execute** | Spec dah 9.95/10 approved. Build order: rules.json → solve.py → conflict resolver → tests → validator → router → why.py → patch chain_calc. Tak satu baris pun ditulis. |
| P1.3 | **Cross-Platform Sync (VPS ↔ WSL2 ↔ GitHub)** | 7 Jul | ◐ **Separuh** | Gemini rsync VPS→PC done. Tapi compare SOUL.md, scripts, cron jobs, commit, PR — semua tak buat. |
| P1.4 | **Multi-Agent Audit Coordination** (Gemini + OpenCode + ZCode) | 7 Jul | ❌ **Belum start** | Prompt template dah sedia (03-AI-AUDIT-PROMPT-TEMPLATE.md). Agents tak pernah dihantar. |

---

## P2 — Infrastructure & Config

| # | Item | Sejak | Status |
|---|------|-------|--------|
| P2.1 | **Telegram "Broken Pipe" error** (Daily Health cron) | 7 Jul | ❌ **Belum diagnose** |
| P2.2 | **hello-world-watch cron interval** — every 1 min is too aggressive | 7 Jul | ❌ **Belum tukar** |
| P2.3 | **Baileys CVE verification** — kena check kat PC dulu | 7 Jul | ⏳ **Tunggu PC access** |
| P2.4 | **MiniMax provider / model setup** — dah add tapi belum testing penuh | 8 Jul | ⏳ **Tunggu gateway restart** |
| P2.5 | **cua-driver MCP path** — Gemini dah set mcp_servers: {} tapi belum proper fix | 7 Jul | ◐ **Band-aid je** |

---

## P3 — Unfinished Business (Jul 3-5)

| # | Item | Sejak | Status |
|---|------|-------|--------|
| P3.1 | **sakana-audit.md** — file exists, content empty | 28 Jun | ❌ **Belum start** |
| P3.2 | **Session Exploration Phase 2-3** (dari Jul 3) | 3 Jul | ❌ **Tergantung** — Phase 1 (explore) start je, Phase 2 (plan) & 3 (execute) tak jalan |
| P3.3 | **OpenCode dashboard / billing / cookie analysis** | 3 Jul | ❌ **Tak selesai** |
| P3.4 | **WhatsApp bridge issues** (link preview, reliability) | 3 Jul | ❌ **Tak selesai** |
| P3.5 | **no_agent cron architecture decision** (15-min vs single cron) | 3 Jul | ❌ **Undecided** |
| P3.6 | **Dexa BD dose_2pm missing slot** — architectural gap | 7 Jul | Known, takde slot F. |

---

## P4 — Small / Today-Only

| # | Item | Notes |
|---|------|-------|
| P4.1 | **E (Levetiracetam)** — belum confirm (~21:43) | Dalam window 19:00-21:00 |
| P4.2 | **DND Resume** — 9 cron jobs still paused | Kena kata "resume" / "DND off" |
| P4.3 | **Routine Analysis Weekend** cron — paused | Jadual Sabtu 11 Jul 8am |

---

## TOTAL COUNT: 20 pending items
- P0: 3 (need IMMEDIATE attention)
- P1: 4 (core system overhaul)
- P2: 5 (infra/config)
- P3: 6 (older unfinished biz)
- P4: 3 (today-specific)
