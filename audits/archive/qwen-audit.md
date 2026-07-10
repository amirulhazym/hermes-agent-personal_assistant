Faham. Saya akan pisahkan respon ini kepada dua bahagian yang sangat jelas seperti yang kau minta: **BAHAGIAN 1 (Tasks: Deep Audit)** dan **BAHAGIAN 2 (Vision & Business Strategy)**. Saya takkan campur adukkan technical audit dengan business advice.

Saya dah baca, analyze dan bedah siasat `CLAUDE_AUDIT_PROMPT.md`, `AUDIT.md`, dan `README.md` dari repo kau. Ini adalah audit teknikal yang *brutally honest* dan strategic blueprint untuk vision kau.

---

### BAHAGIAN 1: DEEP AUDIT & ANALYSIS (TASKS)

# Executive Summary
Sistem "MarryJane" (MJ) yang kau bina ini adalah satu *masterpiece* dari sudut *hacker/engineer mindset*. Dalam masa beberapa hari, kau dah berjaya setup satu *end-to-end AI agent* yang merentasi dual-platform (WhatsApp + Telegram), ada *durable memory*, proactive cron orchestration (27 jobs!), dan self-healing infrastructure (3-layer watchdog).

Walau bagaimanapun, dari sudut *production readiness* dan *long-term maintainability*, sistem ini agak "brittle" (rapuh). Kau banyak bergantung pada *dirty hacks* (seperti patch source code Hermes untuk model routing), bergantung 100% pada *free-tier APIs* tanpa fallback, dan ada isu *state management* yang memerlukan campur tangan manual. Untuk kegunaan peribadi, ia sangat berkuasa. Tapi kalau nak scale jadi bisnes atau servis, *technical debt* ini akan memakan kau.

# Critical Issues (Must fix immediately)
1. **Baileys WhatsApp Library Critical Vulnerability (GHSA-qvv5-jq5g-4cgg)**
   - **Issue**: Library Baileys ada *critical vulnerability* (message spoofing / state corruption via crafted protocolMessage) dan tiada upstream fix.
   - **Why it matters**: Memandangkan bot ini menggunakan nombor WhatsApp peribadi/Hotlink kau, *attack surface* agak terhad kepada orang yang ada nombor tu. Tapi, kalau ada yang hantar *crafted payload*, dia boleh crash-kan bridge WhatsApp atau *inject command* ke dalam sistem kau.
   - **How to fix**: Buat *strict validation* di layer Baileys message ingestion. Pastikan *allowlist* check dibuat SEBELUM message payload diproses oleh Hermes. Kalau nak lebih selamat untuk masa depan, pertimbangkan API berbayar macam Whapi.cloud / Twilio untuk *production* nanti.
   - **Priority**: CRITICAL

2. **Model Overrides via Source Code Patching**
   - **Issue**: Kau edit `hermes_cli/models.py` dan `agent/models_dev.py` secara manual untuk force OpenCode Zen/NVIDIA dan buang Gemini. Kau harap pada `fix-models.sh` bila ada update.
   - **Why it matters**: Hermes Agent update sangat kerap. Bila kau run `hermes update`, *source code patching* kau akan kena *overwrite*, dan sistem kau akan *down* serta-merta sebab model routing hilang. Ini *maintenance nightmare*.
   - **How to fix**: Jangan patch core library. Cuba setup **LiteLLM Proxy** di WSL2 untuk map nama model ke provider yang kau nak, atau tulis satu *wrapper script* yang monkey-patch model list tu di *runtime* sebelum Hermes start.
   - **Priority**: CRITICAL (Untuk long-term survival)

3. **Single Point of Failure: 100% Free-Tier API Dependencies**
   - **Issue**: Bergantung sepenuhnya pada OpenCode Zen dan NVIDIA free tier.
   - **Why it matters**: Free tier boleh tukar terms, block key, atau shut down bila-bila masa tanpa notis. Assistant kau akan jadi "brain-dead" tiba-tiba.
   - **How to fix**: Kau dah ada DeepSeek API key tapi tak guna. DeepSeek V4 Flash adalah sangat murah ($0.14/M tokens). Configure DeepSeek sebagai **Primary** atau sekurang-kurangnya **Fallback Provider** dalam config Hermes.
   - **Priority**: HIGH

# High Priority (Fix this week)
1. **`gateway_state.json` Stale State Bug**
   - **Issue**: Bila gateway kena SIGTERM, file `gateway_state.json` tak clear, block restart.
   - **Fix**: Tambah `rm -f ~/.hermes/gateway_state.json` di baris pertama dalam `gateway-start.ps1` dan `watchdog.sh`. Biar script yang tolong bersihkan sebelum start.
2. **Remote Restart from Phone**
   - **Issue**: Kalau gateway mati dan watchdog fail, kau kena buka PC.
   - **Fix**: Buat satu Telegram command (contoh: `/mj_restart`) yang trigger PowerShell script. Command ini mesti ada 2-layer security (Admin allowlist + Secondary PIN code) sebab ia sangat berbahaya kalau orang lain jumpa.
3. **Medication Cron Hardcoding (20 Jobs)**
   - **Issue**: 20 cron jobs untuk medication adalah *anti-pattern*. Susah nak maintain dan nama ubat sebenar ada dalam cron list.
   - **Fix**: Consolidate jadi SATU cron job (contoh: "Medication Dispatcher" yang jalan setiap 15 minit). Dispatcher ni akan baca satu file `meds_schedule.json` (guna alias macam "Med A") dan decide kalau perlu hantar reminder based on current time. Ini kurangkan 20 jobs jadi 1.

# Medium Priority (Worth doing)
1. **State DB Bloat (`state.db` ~50MB)**: 50MB untuk 5 hari (86 sessions) agak besar. Jalankan `sqlite3 ~/.hermes/state.db "VACUUM;"` dan `PRAGMA wal_checkpoint(TRUNCATE);` untuk reclaim space.
2. **`cua-driver` (Computer Use) Subprocess Stability**: Pastikan MCP server `cua-driver.exe` ada strict memory limits dan timeout dalam config. Kalau satu task computer-use hang, ia takkan hang-kan seluruh gateway Python kau.
3. **Log Rotation**: Gateway log dah 4.7MB. Pastikan `logrotate` di WSL2 dikonfigurasi untuk rotate log Hermes setiap hari atau bila cecah 10MB.

# Low Priority / Nice-to-Have
1. **Obsidian Vault Synergy**: Buat cron job "Daily Auto-Note" yang auto-create nota hari ini dalam Obsidian dan sumbat Morning Briefing + Task list terus ke dalam nota tu.
2. **Node.js on PATH**: Tak perlu letak dalam PATH kalau venv entry point dah jalan. Tapi kalau rajin, letak dalam `.bashrc` untuk senang manual debug WhatsApp bridge.

# Quick Wins (<30 min each)
1. Pergi rotate API key NVIDIA dan OpenCode Zen sekarang sebab kau pernah paste plaintext dalam chat.
2. Tambah command `/ping` di Telegram untuk quick health check dari phone.
3. Run `VACUUM` pada SQLite database.
4. Add `rm` state file dalam startup scripts.

# Long-Term Recommendations
1. **VPS Migration**: WSL2 bagus untuk dev, tapi untuk 24/7 reliability, migrate VHDX ke cheap Linux VPS (Hetzner / RackNerd). Structure F: drive kau translate perfectly ke `/opt/hermes`.
2. **RAG Integration**: Jangan harap pada `MEMORY.md` sahaja. Setup local Vector DB (ChromaDB / LanceDB) di WSL2 untuk index Obsidian Vault kau. Ini bagi Hermes "semantic search" yang sebenar.

# Final Verdict
- **Overall system health score**: 7.5/10
- **Biggest risk**: Source code patching + Baileys vulnerability + Free-tier dependency.
- **Biggest strength**: Extreme resilience (3-layer watchdog) dan UX yang sangat thoughtful (medication escalation logic, quiet hours, cross-platform memory).

---

### BAHAGIAN 2: VISION, EXPLORATION & BUSINESS STRATEGY

Kau dah nyatakan dengan jelas: Ada 2 matlamat. 1. Self-exploration (belajar end-to-end). 2. Jadikan ini peluang bisnes/side income (short-term hype & long-term gain). Kita pisahkan dan bedah satu-satu.

#### 1. Self-Exploration (Learning Hermes 101 & End-to-End)
Apa yang kau buat sekarang (PRD.md, RUNBOOK.md, DECISIONS.md, troubleshooting WSL2 systemd, Baileys bridge) adalah **exactly** apa yang company cari untuk role "AI Agent Engineer" atau "AI Solutions Architect".
- **Cara maximize**: Jangan sekadar code. Document *mengapa* kau buat sesuatu keputusan (macam yang kau dah buat dalam `DECISIONS.md`). Portfolio GitHub yang ada *Architecture Diagram*, *Risk Register*, dan *Runbook* adalah 10x lebih bernilai dari repo yang cuma ada `main.py`. Ini prove yang kau faham *System Design*, bukan sekadar pandai call API.

#### 2. Short-Term Hype (Quick Cash, Side Income & Personal Branding)
Untuk dapatkan side income dengan cepat dan bina nama (hype):
- **Viral Tech Content (TikTok/Reels/Twitter)**: Setup "Medication Escalation" kau (15 minit follow-up sampai user reply) adalah *killer feature*. Buat video tunjuk macam mana AI kau "bebel" kat kau sampai kau makan ubat. Tajuk: *"I built an AI that nags me to take my meds and won't stop until I reply."* Content macam ni sangat viral di kalangan tech community dan productivity hack audience.
- **Sell the "Hermes WSL2 Blueprint" (Digital Product)**: Ramai developer nak buat personal AI tapi give up bila kena setup WSL2, fix Baileys, dan configure Cron. Package `config.yaml`, `watchdog.sh`, `cron templates`, dan setup guide kau jadi satu eBook atau Gumroad product. Jual dalam RM50 - RM150. Ini pure profit dan passive income.
- **SME WhatsApp Automation Agency (Freelance)**: Guna exact stack MJ ini untuk buat bot klinik (appointment reminder) atau ejen hartanah (lead qualification). Kau white-label MJ, charge setup fee (RM2k - RM5k) + maintenance bulanan. Kau dah ada proof-of-concept yang hidup di phone kau sendiri.

#### 3. Long-Term Gain (Sustainable Business & Career Asset)
Ini untuk masa depan yang berpanjangan (bukan sekadar hype):
- **Edge AI & Enterprise On-Prem Consultant**: Kau minat *enterprise storage*. Gabungkan dengan Hermes. Sekarang, company besar takut hantar data depa ke cloud OpenAI (privacy risk). Kau boleh tawarkan servis deploy "Hermes Local Agent" pada server on-premise company. Guna local LLM (Qwen/Llama 3 via Ollama) + Vector DB. Kau jual *Privacy & Edge AI Infrastructure*. Rate consultant untuk ini sangat tinggi.
- **Managed SaaS (Productized Service)**: Bila kau dah migrate ke VPS, kau boleh host multiple instances of Hermes. Buat niche specific SaaS. Contoh: "ElderlyCare AI" – anak-anak subscribe RM50/bulan, AI akan WhatsApp mak bapak diaorang tanya khabar, ingatkan makan ubat, dan report balik ke anak kalau ada emergency (detected via NLP sentiment).
- **Open Source Bounties & Reputation**: Contribute balik solusi kau (macam model routing wrapper atau Baileys security patch) ke Hermes Agent community. Bila nama kau dikenali di circle NousResearch / Hermes, tawaran consulting dari luar negara akan datang sendiri.

**Kesimpulan untuk Vision Kau:**
Guna MJ sebagai **sandbox** untuk test use cases yang ekstrem (macam medication escalation). Lepas tu, **extract** logic yang berjaya tu, **package** jadi solusi untuk orang lain (content / digital product / agency), dan **scale** ke enterprise level bila kau dah mahir dengan Edge AI deployment.

Kau ada *foundation* yang sangat kuat. Jangan berhenti explore, tapi mula fikir macam mana nak *productize* penat lelah kau setup sistem ni.