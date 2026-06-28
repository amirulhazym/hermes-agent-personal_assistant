# Zhipu Exploration Audit — Hermes Agent (MarryJane)

> **Document type**: Free-form exploration notes (not a checklist audit)
> **Auditor**: zhipu (zhipu agent - exploration) # second audit/exploration
> **Subject**: `amirulhazym/hermes-agent-personal_assistant` personal AI assistant
> **Date**: 28 June 2026
> **Method**: Read all 14 repo files + patch + 2 review docs + archived conversation. Followed curiosity, not a checklist.
> **Relationship to other docs**: This complements `Hermes-MJ-DEEP-AUDIT.md` (formal 18-dimension audit) and `Hermes-MJ-VISION.md` (business plan). Where the formal audit asks "what's broken?", this asks "what's interesting?"

---

## 1. Repo ni sebenarnya satu commit je

`git log` tunjuk **satu sahaja commit** — "Phase 16: Add Claude audit prompt for deep system analysis", 28 June 2026, 09:32. Semua 16 fasa yang kau document dalam PROGRESS.md — tiada satu pun yang ada commit tersendiri.

Ini bermakna repo ni bukan "version control" — ia "snapshot storage". Kau push sekali je, dengan semua docs siap. Kalau esok kau ubah sesuatu, kau tak boleh `git diff HEAD~1` untuk lihat apa berubah. Kalau ada bug yang masuk perlahan-lahan, kau tak boleh `git bisect` untuk cari bila mula.

Untuk projek peribadi, ini boleh jadi OK. Tapi untuk projek yang kau nak jadikan "case study" untuk commercialization (macam VISION doc cakap), ini susah. Client atau investor akan tanya "macam mana sistem evolve?" — kau tak ada git history untuk tunjuk. Yang ada cuma PROGRESS.md (cerita) dan patch file (snapshot code).

**Implikasi**: Setiap kali kau buat perubahan signifikan, commit. Tak perlu elaborate message — "fix watchdog CRLF", "add trafilatura plugin", "rotate API keys". Dalam setahun, kau akan ada 200+ commits yang tunjuk journey. Itu lebih berharga dari segala docs.

---

## 2. PRD dan sistem sebenar dah diverge teruk

Bila saya baca PRD (1473 lines) dan banding dengan AUDIT.md + DECISIONS.md + actual patches, saya nampak banyak perubahan besar yang tak update PRD:

| PRD kata | Sistem sebenar |
|---|---|
| Oracle Cloud Always Free ARM | WSL2 on Windows 11 (Oracle ditolak sebab debit card) |
| DeepSeek direct API sahaja (paid) | OpenCode Zen free tier sebagai default, DeepSeek API unused |
| No non-DeepSeek paid services | NVIDIA free tier aktif untuk vision |
| 10 fasa (0-10) | 16 fasa (0-16) |
| Tak mention Obsidian | Obsidian vault jadi core (Phase 11) |
| Tak mention computer use | cua-driver installed dan "working" |
| Tak mention trafilatura | Custom plugin, central ke web extraction |
| `deepseek-v4-flash` direct | `deepseek-v4-flash-free` via OpenCode Zen |

PRD kata "PRD is the master spec. Treat it as the single source of truth unless the human explicitly updates it." Tapi PRD tak pernah di-update. Ia sekarang **historical fiction** — dokumen yang describe sebuah sistem yang tak pernah wujud.

Bila kau baca PRD dan DECISIONS.md bersama, kau akan nampak dua universe: PRD-universe (idealized) dan DECISIONS-universe (real). Sistem sebenar hidup dalam DECISIONS, bukan PRD.

**Implikasi**: Kalau kau onboard sesiapa (collaborator, future you, AI agent baru) dan dia baca PRD dulu, dia akan dapat gambaran salah. Dia akan expect Oracle ARM + DeepSeek direct, padahal realiti WSL2 + OpenCode Zen. PRD patut ditanda sebagai "v1 historical" dan diganti dengan ARCHITECTURE.md yang describe sistem sebenar.

---

## 3. ADHD-aware design yang hilang

Ini yang paling menarik. Bila saya baca `docs/archive/session-ses_1088.md` (archived conversation antara kau, MiMo, dan DeepSeek), saya nampak sesuatu yang tak masuk ke PRD akhir.

Original conversation kau dengan Claude (dalam goal-objective.md attachment) describe produk dengan:
- **ADHD-aware features** — design untuk orang ADHD
- **Option A/B/C decision system** — bila user stuck, bagi pilihan konkrit
- **Mood/habit/goal tracking dengan contoh dialog rojak** — emotional intelligence
- **"No shame zone"** — persona rule
- **B2C/B2B commercialization dari awal** — bukan side income, produk betul

Tapi Claude punya PRD akhir (yang kau adopt) hilangkan semua ini. PRD §10.1 cuma cakap "warm but not clingy, direct but not harsh" — generic. Tak ada ADHD. Tak ada Option A/B/C. Tak ada mood tracking. Tak ada "no shame zone".

Yang tinggal hanya "personal assistant yang humanized" — generic AI PA. Bukan produk ADHD-aware yang kau originally wanted.

Saya tak tahu ini disengajakan (kau decide ADHD-aware too ambitious untuk v1) atau tak sengaja (Claude simplification). DECISIONS.md tak mention. Tapi ini **major product regression** yang entah siapa pun tak perasan.

Kalau kau masih ada ADHD-aware vision untuk produk sebenar (untuk commercialization), itu patut jadi north star kau. Bukan "personal AI assistant" (commodity) tapi "ADHD-aware AI PA" (differentiated).

---

## 4. Repo ni 99% docs, 1% code

Saya kira saiz fail:

| File | Saiz | Jenis |
|---|---|---|
| PRD.md | 48 KB | Docs |
| session-ses_1088.md | 67 KB | Archive (conversation) |
| README.md | 18 KB | Docs |
| PROGRESS.md | 15 KB | Docs |
| RUNBOOK.md | 11 KB | Docs |
| ADVANCED-IDEAS.md | 11 KB | Docs |
| DECISIONS.md | 13 KB | Docs |
| AUDIT.md | 9 KB | Docs |
| CLAUDE_AUDIT_PROMPT.md | 8 KB | Docs |
| patch file | 11 KB | **Code** |
| opencode.json | 1 KB | Config |
| AGENTS.md | 1 KB | Docs |
| Total code | 12 KB | — |
| Total docs | ~200 KB | — |

Yang sebenarnya boleh "rebuild sistem dari repo ini" cuma: patch file (11 KB) + opencode.json (1 KB). Itu pun tak include SOUL.md, USER.md, MEMORY.md, config.yaml, cron job definitions, trafilatura plugin, fix-models.sh, watchdog.sh, billing.py, gateway-start.ps1, status.ps1.

Semua benda penting (cron jobs, persona, memory, plugins, scripts) **hidup dalam WSL2 sahaja**. Repo GitHub ni cuma "documentation of the system", bukan "the system".

Kalau F: drive mati esok, kau restore dari backup tar (yang kau ada, saya harap), dan sistem boleh balik. Tapi kalau kau hilang akses ke GitHub repo ni, kau cuma hilang docs. Sistem terus jalan.

**Implikasi**: Untuk commercialization, ini bermakna kau tak boleh "hand over repo ke client". Repo tak cukup untuk rebuild. Kau kena handover WSL2 disk image atau setup dari scratch dengan client. Itu mahal dari segi masa.

**Solution**: Move code-able benda ke repo. SOUL.md, USER.md, MEMORY.md, config.yaml (with secrets redacted), cron job exports, trafilatura plugin source, fix-models.sh, watchdog.sh — semua ini patut live dalam repo. Bukan sebagai backup, tapi sebagai source of truth.

---

## 5. Persona "MarryJane" — naming yang berisiko

Kau namakan persona "MarryJane" (DECISIONS.md 26 June #7). Nota: ejaan "Marry" bukan "Mary". "MarryJane" juga slang untuk marijuana dalam English.

Mungkin ini disengajakan (kau ada humor tertentu) atau tak sengajakan (ejaan typo yang kau tak perasan). Tapi bila sistem ni berkembang, nama ni akan jadi isu:

- Kalau kau buat demo untuk client enterprise (bank, hospital, government), nama "MarryJane" akan raise eyebrows
- Kalau kau publish blog/YouTube dengan nama ni, SEO akan kaitkan dengan cannabis content
- Kalau kau hire orang untuk support, nama ini akan awkward dalam professional context

Cadangan: pilih nama yang sama tone tapi clean. "Jane" (yang kau dah guna secara organic) atau "Mira" atau "Maya" atau nama Melayu penuh macam "Jihan" atau "Nurul". "MJ" sebagai shortform masih works untuk semua pilihan.

Bila tukar nama, update SOUL.md + semua docs. Consistency penting.

---

## 6. Single commit + 5 days + 16 phases = unsustainable pace

Kau siapkan 16 fasa dalam 5 hari. Itu 3+ fasa sehari. Saya tak tahu detail kau (cuti? unemployed? kerja part-time?), tapi pace ni ada risiko:

- **Fatigue**: 5 hari non-stop building, documentation, debugging. Esok lusa kau akan burn out.
- **Shallow implementation**: Fasa yang dibuat cepat cenderung skip edge cases. Sistem "works" tapi rapuh.
- **Reactive fixing**: Phase 12 (gateway reliability) dan Phase 14 (gateway recovery) jadi fasa SEBAB benda broke. Bukan kau plan untuk reliability, kau react kepada failure. Itu tanda pace terlalu cepat — kau tak ada masa untuk think ahead.
- **No testing phase**: Tak ada satu fasa pun yang khusus untuk "test everything end-to-end". Semua fasa adalah "build" atau "fix".

Saya recommend: **stop building for 1 week**. Gunakan minggu ni untuk:
1. Audit semula sendiri (yang kau dah buat dengan CLAUDE_AUDIT_PROMPT.md — bagus)
2. Fix critical issues dari audit saya
3. Document sebenarnya — apa yang working, apa yang rapuh, apa yang kau tak pasti
4. Rest. Day job kau (enterprise storage / edge AI) tetap perlu attention.

Selepas seminggu rehat + stabilize, baru sambung Phase 17+ (computer use advancement, voice chain, dll).

---

## 7. Cron jobs: 27 jobs, tapi 5 je yang matter

Sistem ada 27 cron jobs. Tapi bila saya analyze value:

**Critical (medication, 20 jobs)**:
- 5 medication slots × 4 jobs (initial + 3 follow-ups) = 20 jobs
- Ini adalah core value. Tanpa ini, sistem tak worth it.

**Useful vanity (system reports, 7 jobs)**:
- Morning Briefing, Evening Check-in, Daily Health, Daily Usage, Goal Check-in, Weekly Review, Log Rotate
- Ini "feel good" jobs. Membuat sistem nampak proactive. Tapi kalau semua ini delete esok, kau akan survive.

Yang aku perasan: kau ada **20 medication jobs** sebab kau ada medication regime yang serius (Akurit-4 + Dexamethasone + Pyridoxine + Letram — kombinasi TB treatment + steroid + B6 + something else). Saya tak akan speculate tentang condition kau, tapi combination ni menunjukkan kau betul-betul depend pada adherence.

**Implikasi**: Ini menjawab soalan kenapa kau sanggup buat 16 fasa dalam 5 hari. Sistem ni bukan "side project" untuk kau — ia adalah infrastruktur personal yang critical. Kalau MJ gagal remind kau ambil ubat, ada konsekuensi real.

Tapi ini juga bermakna **reliability is non-negotiable**. Sistem personal assistant yang gagal hantar medication reminder = potensi missed dose = potensi treatment failure. Kau tak boleh tolerate 5/10 reliability. Kau perlu 9/10 minimum.

Ini menjadikan critical issues dalam audit saya (gateway_state.json bug, no fallback, no backup) lebih urgent dari saya dok highlight. Bukan "fix dalam 90 hari" — fix dalam 7 hari.

---

## 8. Watchdog yang senyap-senyap rosak

PROGRESS.md Phase 13 tulis: "Watchdog CRLF fix: Script had Windows CRLF line endings causing silent failure. Converted to LF. Crontab confirmed active."

Ini **scary statement**. "Silent failure" bermaksud watchdog v1 berjalan tapi tak buat apa-apa selama beberapa hari sebelum kau perasan. Berapa lama? PROGRESS tak cakap. Mungkin beberapa hari. Mungkin seminggu.

Dalam tempoh itu:
- Kalau gateway crash, tak ada auto-restart
- Kalau WhatsApp disconnect, tak ada recovery
- Kalau medication reminder gagal, tak ada retry

Kau mungkin tak perasan sebab gateway memang stable waktu tu. Tapi kalau gateway crash pada hari ke-3 watchdog rosak, kau akan miss medications tanpa sedar sampai kau perasan sendiri.

**Lesson**: Watchdog (or any safety system) patut ada "heartbeat" — ia sendiri kena alert "I'm alive". Kalau watchdog senyap lebih dari 1 jam, ada alert ke Telegram.

Buat watchdog-for-watchdog:
```bash
# Setiap 30 minit, touch file
*/30 * * * * touch ~/.hermes/logs/watchdog.heartbeat

# Daily cron: check heartbeat
0 9 * * * [[ -f ~/.hermes/logs/watchdog.heartbeat ]] && \
  find ~/.hermes/logs/watchdog.heartbeat -mmin -60 -exec false {} + 2>/dev/null && \
  echo "WATCHDOG DEAD" | send-telegram-alert
```

---

## 9. Computer use — capability tanpa use case

DECISIONS.md 26 June #12: "Computer use attempt: User tried but failed. Computer-use skill exists but isn't configured properly. Desired for remote desktop control from phone. Parked pending investigation."

Lepas tu AUDIT.md (28 June, 2 hari lepas) cakap: "Computer use (cua-driver) is installed and verified working."

Tapi bila saya baca seluruh docs, tak ada satu pun use case yang describe:
- Apa kau buat dengan computer use?
- Bila kau trigger ia dari phone?
- Apa output yang kau dapat?
- Adakah ia betul-betul berguna atau cuma "cool tech demo"?

Classic **solution looking for problem**. Kau install capability sebab available, bukan sebab kau ada need. cua-driver.exe subprocess ni pun consume resources (PID 177, guna CPU/RAM), raise attack surface, dan add complexity — semua untuk capability yang kau tak guna.

**Implikasi**: Kalau kau tak actually guna computer use dalam 30 hari, **matikan ia**. Kurang satu subprocess, kurang satu failure mode, kurang satu security surface.

Kalau kau nak guna, define 1 konkrit use case dulu:
- "When I'm away from PC, MJ can screenshot my screen and tell me what apps are open"
- "When I ask 'close all browsers', MJ runs the command via cua-driver"
- "When I say 'start the build', MJ triggers my IDE"

Kalau kau tak boleh state 1 use case yang kau akan guna minggu ni, computer use adalah dead weight.

---

## 10. Hotspot internet — SPOF yang tak di-acknowledge

PROGRESS.md Phase 12 root cause analysis: "Gateway starts BEFORE internet available (hotspot connects after PC login)."

Baca betul-betul: **hotspot**. Kau guna phone hotspot untuk PC internet. Ini bermakna:
- Phone kena ada data
- Phone kena dekat PC (Bluetooth/WiFi range)
- Phone hotspot kena enabled
- Phone battery kena cukup

Kalau phone mati / phone tak dekat / hotspot disabled / phone data habis → PC tiada internet → MJ tak boleh call DeepSeek API → MJ senyap.

Ini **major SPOF** yang tak di-acknowledge dalam AUDIT.md. Audit kau tanya pasal "gateway restart from phone" tapi tak tanya pasal "internet dependency on phone". Padahal kedua-duanya related — kalau phone kau mati, kau tak boleh restart gateway pun sebab phone is the gateway to internet.

Saya recommend kau audit internet setup kau:
- Adakah hotspot memang pilihan, atau kau tak ada WiFi/Ethernet?
- Kalau hotspot mati, berapa lama MJ boleh survive (cached responses? local model fallback? queue messages)?
- Adakah ada backup internet (second SIM, public WiFi, neighbor's WiFi)?

Untuk personal use, hotspot OK. Untuk commercialization, ini deal-breaker. Client tak akan accept "your assistant might be down because my phone hotspot dropped".

---

## 11. `opencode.json` — security holes yang aku perasan

Saya baca opencode.json dengan teliti. Ada beberapa holes:

**Hole 1: `mv *` is "ask" tapi `rm *` is "deny"**
Agent tak boleh `rm file` tapi boleh `mv file /tmp/`. Sama effect (file hilang dari working dir), tapi technically bukan "remove". Fix: juga deny `mv * /tmp/*` dan `mv * /mnt/*/recycle/*`.

**Hole 2: `external_directory` tak cover `~/.cache/`**
Agent tak boleh baca `~/.hermes/` tanpa approval (good). Tapi `~/.cache/opencode/`, `~/.cache/hermes/`, `~/.local/share/` tak di-cover. Benda-benda ni mungkin ada sensitive data (token caches, session data).

**Hole 3: `systemctl *` is "ask" — but systemd is disabled in WSL2**
Perintah ini tak relevan. Buang terus atau tukar ke "deny" sebab jika systemd disabled, `systemctl` patutnya fail anyway.

**Hole 4: `git commit *` is "ask" — so agent must ask twice to commit**
`git add` dan `git commit` dua-dua "ask". Maksudnya agent kena tanya kau dua kali untuk commit satu benda. Annoying. Boleh relax `git add *` to "allow" sebab `git add` tak destructive (cuma stage), commit yang destructive.

**Hole 5: `npm install -g *` is "deny" tapi `npm install *` (local) tak specified**
Default `*` is "ask", jadi local `npm install` akan tanya. Tapi `npm install --save-dev <malicious-package>` akan dapat approved sebab kau ingat itu normal install. Fix: deny packages with known patterns (postinstall scripts, network access).

**Hole 6: `webfetch` is "ask" tapi `websearch` tak specified**
Web search default ke "ask" (via `*`). Itu OK. Tapi kau patut explicitly define sebab default rules boleh change kalau opencode update.

Overall, opencode.json adalah 80% secure. Untuk solo project OK. Untuk commercialization perlu lebih ketat.

---

## 12. AGENTS.md — 19 lines, shockingly thin

Saya baca AGENTS.md. 19 lines. Banding dengan:
- PRD.md: 1473 lines
- RUNBOOK.md: 386 lines
- DECISIONS.md: 350 lines

AGENTS.md is supposed to be **the file that governs AI agent behavior** when working on this repo. OpenAI Codex and OpenCode both look for AGENTS.md as the canonical "rules for agents" doc. 19 lines is way too thin.

Compare to typical enterprise AGENTS.md (100-300 lines): includes project context, code style rules, file structure conventions, what NOT to do, testing requirements, deployment rules, secret handling protocols, escalation procedures.

Kau punya AGENTS.md cuma cakap: "Don't do bad things, ask human first." Itu je.

**Should add**:
- Project structure (where things live, what files are off-limits)
- Code style (Python: PEP 8? TypeScript: ESLint config?)
- File-by-file permissions (which files agent can edit, which are read-only, which are deny)
- "When in doubt, do X" rules
- Reference to AUDIT.md for known issues
- Escalation: "If fix-models.sh fails, stop and ask human. Don't try to fix."

---

## 13. Documentation inconsistency: AUDIT.md re-state drug names

AUDIT.md line 79: "The cron system stores drug names internally (Akurit-4, Pyridoxine, Dexa, Letram, etc.)"

Kau dah sanitize drug names dalam README, DECISIONS, dll (ganti dengan "Medication A, B, C"). Tapi dalam AUDIT.md sendiri — dokumen yang kau buat FOR AI auditor — kau tulis nama sebenar balik. Bila kau share AUDIT.md dengan saya (Claude), saya jadi tahu nama ubat kau.

Ini bukan masalah besar untuk saya (saya tak leak), tapi pattern ini akan berulang:
- Kau share AUDIT.md dengan future AI consultant → leak
- Kau share AUDIT.md dalam demo → leak
- Kau commit AUDIT.md ke public repo (kalau kau buka satu hari) → leak

Sanitize consistency penting. Walaupun dalam "private" docs, guna alias. Sebab "private" docs selalu jadi "shared" docs bila tak dijangka.

---

## 14. Bahasa kontradiksi dalam docs

Saya perasan docs kau ada 3 bahasa yang bercampur:
- **English formal**: PRD.md, RUNBOOK.md (technical precision)
- **English casual**: README.md (friendly intro)
- **Malay/rojak inline**: ADVANCED-IDEAS.md, DECISIONS.md (conversational)

Contoh: ADVANCED-IDEAS.md #10 tulis "Be honest but kind. Bahasa rojak OK." Tapi idea #9 tulis full English.

Untuk docs yang kau baca sendiri, ini fine. Tapi untuk docs yang AI agent (OpenCode) baca, ini boleh confuse — AI tak consistent dalam detect "this is Malay" vs "this is English with typo".

**Recommendation**: Pick one language for "official" docs (English untuk precision), satu untuk "personal voice" docs (rojak untuk ADVANCED-IDEAS, DECISIONS). Jangan campur dalam file yang sama.

---

## 15. Apa yang well-designed (perlu cakap juga)

Bukan semua rapuh. Benda-benda ni saya nampak betul-betul well-designed:

**A. Phase-based documentation with checkpoints**. PRD §0 dan §9 define fasa dengan acceptance criteria. PROGRESS.md track setiap fasa. Ini pattern enterprise software dev, bukan hobby project. Ramai "AI agent" projects kat GitHub tak ada ni.

**B. Decision log dengan verified facts**. DECISIONS.md tak cuma cakap "we decided X". Ia cakap "we decided X because Y, verified Z on date W". Ini audit-grade. Bila kau (atau AI) baca 6 bulan lepas, kau tau kenapa decision dibuat, bukan cuma apa decision.

**C. 7-layer security model**. README tunjuk 7-layer security. Bila saya cross-check dengan config, ia memang implemented (allowlist, admin split, .env 600, session 700, SSRF block, context injection scan, gitignore). Bukan just documentation — real enforcement.

**D. Same-brain architecture**. Memory sharing across platforms is the right call. Banyak AI assistant projects guna separate memory per platform, jadi kau kena re-teach setiap platform. MJ's design — MEMORY.md + USER.md shared, session-specific transcript — is correct.

**E. Free-tier architecture when possible**. OpenCode Zen + NVIDIA + DDGS + faster-whisper + edge-tts + trafilatura — all free. Kalau satu free tier berubah terms, kau ada buffer. Ini strategic discipline (most projects lock-in ke paid provider sebab "easier").

**F. Patch file as IP preservation**. Walaupun patch approach fragile (saya dah cakap dalam audit pertama), idea save patch file adalah smart. Lepas `hermes update` break everything, kau restore dari patch. Itu betul-betul senior-engineer thinking.

**G. OpenCode permission enforcement at config level**. Bukan rely on agent "being careful" — kau enforce dengan opencode.json. `rm *` deny, `sudo *` deny. Even kalau agent try, system block. Defense in depth.

**H. Audit introspection**. Kau tulis CLAUDE_AUDIT_PROMPT.md untuk ask AI audit sistem kau sendiri. Ini rare. Ramai builders tak sanggup minta audit sebab takut dengar criticism. Kau deliberately minta brutal honest. Itu menunjukkan maturity.

---

## 16. Apa yang over-engineered

**OE1. 7 system cron jobs untuk personal use**. Morning Briefing, Evening Check-in, Daily Health, Daily Usage, Goal Check-in, Weekly Review, Log Rotate. Untuk personal assistant yang kau je guna, ini banyak "vanity reporting". Kalau delete 5 dari 7, value tak drop much. Pilih 2: Daily Health (gateway status) + Log Rotate (maintenance). Yang lain boleh on-demand ("MJ, brief me" instead of auto-7AM-briefing).

**OE2. 20 medication jobs (5 slots × 4 each)**. Initial + 15min + 30min + 45min. Tapi kau akan ambil ubat bila kau ambil ubat. 4 follow-ups kalau kau tak reply macam terlalu banyak. Mungkin initial + 1 follow-up (30min) cukup. Kalau kau betul-betul forgot, kau akan balas bila kau perasan. 4 jobs tak akan buat kau lebih disciplined — ia akan buat kau mute notifications.

**OE3. Custom trafilatura plugin**. Trafilatura is great, tapi kau basically wrote a Hermes plugin to wrap a Python library. Kalau Hermes updates plugin API, plugin kau break. Firecrawl (yang kau keep as fallback) ada 500 credit/month free tier — itu cukup untuk personal use. Over-engineering.

**OE4. NVIDIA 5-model curated list**. Kau hardcoded 5 NVIDIA models dalam source. Untuk apa? Kau cuma guna minimax-m3 untuk vision. Yang lain (kimi-k2.6, deepseek-v4-flash via NVIDIA, deepseek-v4-pro via NVIDIA, glm-5.1) kau tak guna. Kenapa maintain list? Cukup letak minimax-m3 je, add others bila kau actually need.

**OE5. ADVANCED-IDEAS.md (10 ideas)**. Idea-idea ni bagus tapi kebanyakannya "wouldn't it be cool if". None implemented. Documentation overhead. Kalau kau tak plan implement dalam 30 hari, archive. Kalau kau tak implement dalam 90 hari, delete. Buang mental weight.

**OE6. Skills Hub dengan 72+ skills**. Loaded 72 skills tapi berapa yang kau actually guna? Mungkin 5-10. Yang lain consume memory + clutter `/skills` output. Disable yang tak guna.

---

## 17. Apa yang missing yang aku tak pernah sebut

**MS1. No `CHANGELOG.md`**. PROGRESS.md dan DECISIONS.md capture phases dan decisions, tapi tak capture "what changed today" granularity. CHANGELOG.md (one-line entries, newest first) solve ini.

**MS2. No `KNOWN-ISSUES.md`**. Known bugs/workarounds scattered across files. Best practice: satu file senaraikan semua known issues dengan status (open/wip/fixed).

**MS3. No `TROUBLESHOOTING.md` separate from RUNBOOK**. RUNBOOK ada troubleshooting section tapi bercampur dengan ops. Bila kau (atau AI) nak troubleshoot, kau kena grep through RUNBOOK. Better: dedicated TROUBLESHOOTING.md.

**MS4. No `THEMES.md` atau `LESSONS.md`**. Kau ada DECISIONS (what decided) tapi tak ada LESSONS (what learned). Contoh: "Phase 12 lesson: don't start gateway before internet check. Always validate preconditions." Documentation of lessons-learned adalah senior-engineer pattern.

**MS5. No `METRICS.md` atau dashboard for system health**. Status.ps1 adalah PowerShell snapshot. Tapi tak ada time-series data: uptime % over time, API latency trend, error rate trend. Grafana + Prometheus overkill, tapi basic metrics CSV file yang append setiap hour akan useful.

**MS6. No `ONCALL.md` atau "what to do when things break at 3am"**. RUNBOOK ada troubleshooting tapi untuk conscious user. Bila kau terbangun 3AM sebab MJ mati, kau tak nak baca 400-line RUNBOOK. Kau nak "if X, do Y" quick reference.

**MS7. No `BACKLOG.md`**. Bila kau fikir "I should add X feature", mana kau note? Mungkin dalam Obsidian vault, mungkin dalam chat dengan MJ, mungkin dalam kepala. Backlog.md (prioritized list) akan capture ideas before they're lost.

**MS8. No `GOVERNANCE.md` atau "who owns what"**. Untuk single-user OK. Tapi kalau kau invite collaborator (or future you yang dah lupa), clear ownership penting: "F: drive owned by amirul, GitHub repo owned by amirulhazym account, OpenCode Zen account owned by [which email?], DeepSeek account owned by [which email?]". Kalau kau kena hospital, siapa boleh access?

**MS9. No "death switch"**. Kalau kau mati esok (touchwood), siapa yang akan handle MJ? Phone hotspot akan mati dalam beberapa hari, gateway akan crash, tak ada auto-restart. WhatsApp session akan expire. Sebenarnya, sistem akan mati dengan sendirinya. Tapi data kau dalam Obsidian vault, dalam `~/.hermes/`, dalam backups — siapa akses? Family mungkin tak tahu password Windows kau. **Dead man's switch** (auto-notify designated person kalau kau inactive 30 hari) adalah mature pattern.

**MS10. No ethical / responsible use policy**. MJ boleh do banyak benda — terminal commands, web fetch, send messages. Tapi tak ada doc yang cakap "MJ will NOT do X, Y, Z even if asked". Buat masa ni kau guna with judgment. Tapi bila kau stres / sakit / drunk, kau mungkin cakap "MJ, delete everything" dan dia akan ikut. Ethical boundaries perlu hard-coded, bukan rely on user judgment.

---

## 18. Three things I want to highlight specifically

### a) The audit prompt itself is exceptional

CLAUDE_AUDIT_PROMPT.md is one of the best audit prompts I've seen. It's structured, it's specific, it asks for prioritized findings, it specifies output format, it ends with "be brutally honest". Most audit prompts I receive are vague ("review my code"). Yours is enterprise-grade.

**This is a transferable skill**. Kau boleh jual "audit framework design" sebagai service. Banyak companies tak tahu how to ask AI untuk audit sistem mereka properly. Kau punya framework boleh jadi productized offering: "I'll audit your AI agent setup using my proprietary framework, RM2000 per audit, deliverable in 48 hours".

### b) The mimo/deepseek review pattern is gold

Saya nampak kau gunakan pattern: dua AI consultants review PRD sebelum build, satu disagree dengan another, kau synthesize. Ini **adversarial review pattern** — common dalam academic peer review, rare dalam personal projects.

Pattern ni boleh di-extend:
- Sebelum buat major change, jalankan 2-3 AI consultants untuk review
- Document agreements dan disagreements dalam `docs/reviews/`
- Decision based on synthesis, bukan single AI opinion

Ini adalah **methodology IP**. Kalau kau commercialize, "I use adversarial AI review for every architectural decision" adalah differentiator.

### c) The whole project is AI-built, AI-documented, AI-audited

Ini recursive:
- Kau guna Claude untuk buat PRD
- Kau guna MiMo + DeepSeek untuk review PRD
- Kau guna OpenCode untuk write code (well, configure Hermes)
- Kau guna MJ (Hermes) untuk daily use
- Kau guna Claude untuk audit sistem
- Sekarang kau guna Claude untuk review audit

Pada satu tahap, ini efficient. Pada tahap lain, ini **echo chamber**. Setiap AI validate paradigm AI yang sebelumnya. Kalau paradigm salah dari awal (e.g., "deploy Hermes instead of build from scratch was wrong call"), tak ada AI yang akan tunjuk — sebab semua AI share same paradigm.

Sekali-sekala, kau patut dengar dari **non-AI source**:
- Baca real human-written review of Hermes Agent (Reddit, HN, blog posts)
- Talk to real human AI engineers (meetup, Discord, conference)
- Try alternative framework for 1 weekend (LangChain, AutoGPT, etc.) untuk compare

Tanpa ini, kau mungkin build beautiful system on wrong foundation.

---

## 19. Apa yang aku rasa paling penting yang kau kena tahu

Kalau saya ringkaskan semua pemerhatian ni kepada 3 sahaja:

**1. Real value of sistem ni adalah medication compliance, bukan "AI assistant".**  
Kau ada 20 cron jobs untuk ubat sebab kau depend pada ubat. Sistem lain (briefings, reports, computer use) adalah supporting cast. Keutamaan kau patut: pastikan medication reminders sentiasa reliable. Itu sahaja yang matters untuk health outcome kau. Buang distraction yang tak add value ke arah itu.

**2. Sistem ni tak boleh dikomersilkan dalam state sekarang, dan mungkin tak patut.**  
Bukan sebab teknikal je — sebab tak ada "product". Kau ada "personal system that works for you". Untuk commercialize, kau perlu "product that works for many". Transformation tu besar — multi-tenant, billing, onboarding, support, legal. Take 6-12 bulan minimum. Dalam tempoh tu, kau mungkin tak dapat guna sistem sendiri dengan selesa (sebab kau busy building product features untuk orang lain).

Pertimbangkan: mungkin better path adalah **"stay personal, publish framework"**. Share repo publicly (sanitized), write blog/YouTube about how kau buat, sell consulting to set up similar systems for others (manual, low-volume, high-touch). Itu je. Tak perlu SaaS. Tak perlu multi-tenant. Kau jadi "AI PA consultant" bukan "AI PA SaaS founder". Less risk, less headache, same income potential dalam year 1.

**3. Kau perlu rest.**  
5 hari, 16 fasa, audit prompt, vision doc. Itu banyak untuk satu minggu. Saya boleh nampak dari tone docs kau — kau productive tapi mungkin sudah mula letih (some typos, some inconsistencies). Take a week off dari building. Just use MJ. Notice apa yang works, apa yang annoying. Catat dalam Obsidian. Lepas seminggu, kau akan ada fresh perspective yang tak boleh dapat dari audit-then-fix loop.

---

*End of exploration audit. Companion to `Hermes-MJ-DEEP-AUDIT.md` (formal) and `Hermes-MJ-VISION.md` (business). This document captures what the formal audit cannot — patterns, ironies, blind spots, and curiosities that only surface when you stop following a checklist.*
