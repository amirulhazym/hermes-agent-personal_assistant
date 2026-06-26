# ADVANCED IDEAS — Hermes Agent Power Use Cases

> 10 unexpected and productive ways to use your Hermes AI assistant.
> Send any of these directly from WhatsApp or Telegram.
> Last updated: 2026-06-26

---

## 1. Auto-Improvement Loop (Self-Correcting Agent)

**Purpose**: Hermes creates a skill from its own mistakes — it learns from corrections.

**Prompt** (send once, let Hermes track for a week):
```
For the next 7 days, every time I correct you or say "wrong" or "bukan tu", log the correction silently. On next Sunday, review ALL corrections, find the top 3 mistake patterns, then create a skill called "self-corrections-week-N" that permanently fixes those patterns. Tell me what the skill contains.
```

**Expected outcome**: After 2-3 weeks, Hermes noticeably improves. Fewer repeated mistakes. A growing library of self-correction skills.

**Pro tip**: After a month, ask: "Combine all self-corrections skills into one master version."

---

## 2. Self-Refining Cron System

**Purpose**: Your scheduled jobs optimize themselves. No more "set and forget until annoyed."

**Prompt**:
```
/memory add: "Aku nak kau audit semua cron jobs setiap Ahad. Criteria: (1) job yang aku NEVER reply to — probably tak useful, (2) job yang aku selalu reply — keep and improve, (3) job yang timing dia off (aku selalu reply lambat) — suggest new time. Then present recommendation: [keep/modify/delete] for each."
```

**Expected outcome**: Cron system that self-tunes. Morning briefing time shifts if you consistently read it later. Check-ins adjust frequency based on engagement.

---

## 3. Parallel Sub-Agent Research (Isolated Context)

**Purpose**: Multiple research tasks run simultaneously, results compiled. No context pollution.

**Prompt**:
```
/background Research top 5 SSD enterprise suppliers in Malaysia: find pricing, warranty, and customer reviews. Format as comparison table.

/background Research hardware requirements for on-premise AI training (similar to aiDAPTIV+): minimum specs, GPU options, thermal considerations.

After both complete, combine into one report. Deliver to Telegram.
```

**Expected outcome**: Two independent research sessions run in parallel. Each gets its own context window. Result compilation in ~10-15 minutes instead of 30+ sequential.

**Pro tip**: Max 3 simultaneous `/background` tasks for best performance.

---

## 4. Memory Contradiction Detective

**Purpose**: Hermes audits its own knowledge base. Finds inconsistencies about you.

**Prompt**:
```
/memory add: "Setiap Isnin pagi, scan memory and USER.md for contradictions about me. Example: if memory says I wake at 5 AM but also says I'm not a morning person — flag it. If two entries contradict each other, tell me which to keep. Keep score of how many contradictions you found per week."
```

**Expected outcome**: Self-cleaning memory. Prevents "garbage in, garbage out" degradation over months. After a year, your memory is still accurate.

---

## 5. Voice Note → Action Chain (3-Step Pipeline)

**Purpose**: Send a rambling voice note in rojak. Hermes transcribes, understands intent, drafts output.

**Prompt** (as a SOUL.md rule or permanent instruction):
```
When I send a voice note starting with "Bos" or containing keyword "buatkan", "draft", "email", "message": (1) transcribe it, (2) understand what action I'm asking for, (3) draft the output in appropriate format (formal English email, casual WhatsApp message, technical spec). Show me the draft BEFORE sending. Wait for "send" to actually deliver.
```

**Example voice note**: "Bos, buatkan email utk supplier tu. Cakap shipment SSD delay 3 hari sebab port klang ada custom clearance issue. Offer discount 5% as goodwill. Tone professional tapi friendly. Thanks."

**Expected outcome**: Hermes drafts a professional email, you approve with one word ("send"), done. No typing needed.

---

## 6. Personal Style Cloning (Write Like You)

**Purpose**: Accumulate enough samples of your writing to mimic your tone, vocabulary, and patterns.

**Prompt**:
```
/skill create my-style: from now on, whenever I ask you to write something and I say "/style", write it in MY voice. Study all our past conversations to learn my: (1) typical sentence length, (2) Malay/English mixing ratio, (3) humor style, (4) formality level, (5) common phrases. Update this skill weekly.
```

**Expected outcome**: After 2-3 weeks, Hermes drafts emails, LinkedIn posts, and WhatsApp messages that sound like YOU — not generic AI. Game-changer for professional communication.

---

## 7. Seamless Context Switch (Cross-Platform)

**Purpose**: Start a task on WhatsApp, continue on Telegram, Hermes finds the context.

**Prompt**:
```
/memory add: "When I switch platforms mid-task and say 'sambung yang tadi' or 'continue previous' or 'mana tadi', ALWAYS use session_search to find the most recent conversation from ANY platform. Replay the last 3 messages as context before responding. If what I'm asking about is clear from search results, just answer. If not, ask me which task I mean."
```

**Example**: Start "Cari 3 supplier SSD di Malaysia" on WhatsApp. Later, open Telegram: "Sambung yang tadi — tunjuk pricing comparison." Hermes searches, finds the WhatsApp session, continues seamlessly.

**Expected outcome**: True multi-platform continuity. No "I don't remember, please remind me."

---

## 8. Chained Cron Pipeline (Context-From)

**Purpose**: 3 cron jobs that pass output to each other. Fully automated research → ranking → briefing.

**Prompt**:
```
Create 3 linked cron jobs for my "AI Storage Daily Brief":
1. Job "fetch": at 06:00 daily, scrape 5 sources for latest AI storage/on-premise AI news. Save to memory.
2. Job "rank": at 06:30, use context_from="fetch" to rank them by relevance to my work (MaiStorage, enterprise SSD, edge AI).
3. Job "brief": at 07:00, use context_from="rank" to deliver a 3-bullet briefing to WhatsApp with topic, why-it-matters, action-if-any.
```

**Expected outcome**: Fully automated research pipeline. You wake up at 7 AM to a curated industry briefing. Zero manual effort after setup.

---

## 9. Deadline Intelligence System

**Purpose**: Hermes tracks deadlines AND learns your completion patterns. Predicts which deadlines you'll miss.

**Prompt**:
```
/memory add: "Whenever I mention a deadline, automatically save: (1) task name, (2) due date, (3) priority level (ask if unclear), (4) estimated effort (ask if unclear). Create a /cron "every morning 07:30" that shows today and tomorrow deadlines sorted by urgency. After 1 month of tracking, analyze my completion rate by task type and day-of-week. Tell me: which types of deadlines do I consistently miss? What day am I most productive? Suggest scheduling changes based on data."
```

**Expected outcome**: Not just reminders — behavioral analytics. You learn that you're 90% reliable on Tuesday deadlines but 40% on Friday. Hermes suggests: "Move Friday deadlines to Thursday or let me remind you 3 days earlier."

---

## 10. Weekly Personal Retrospective (Self-Audit)

**Purpose**: Every Sunday, Hermes runs a deep retrospective on YOUR patterns — productivity, mood, habits, goals.

**Prompt**:
```
/cron add "every sunday 19:00" "Run a comprehensive personal retrospective for Amirul. Check: (1) last week goals vs completion, (2) habit streaks (which habits were maintained/broken), (3) open loops from memory, (4) emotional tone of conversations this week (were there stressful periods?), (5) most productive day/time pattern, (6) top 3 wins and 1 thing to improve. Deliver as structured report to Telegram. End with ONE suggested focus for next week. Be honest but kind. Bahasa rojak OK."
```

**Expected outcome**: Weekly mirror. You see patterns you didn't know existed. After 4 weeks: "You're 3x more productive on mornings when you exercise. Your stress peaks on Wednesday afternoon. You finish 80% of tasks started on Monday, but only 20% of tasks started on Thursday."

---

*End of 10 ideas — see next page for Vision & Live API bonus section.*

---

## Bonus: Vision-Powered Desktop (Gemini + Computer Use)

**Needs**: `GOOGLE_API_KEY` in .env + `auxiliary.vision.provider: gemini` + cua-driver running.

### 11a. Desktop Overseer (On-Demand)

```
Tengok screen aku sekarang — apps apa yang terbuka? Apa yang patut aku buat next?
```
Computer use captures screenshot → Gemini 3.1 Flash Lite analyzes → describes what's on screen. Useful when you're away but want MJ to check if something is open.

### 11b. Visual Code Review

```
Screenshot VS Code error ni. Baca error tu and suggest fix.
```
Gemini reads error messages from screenshots, DeepSeek suggests fixes.

### 11c. Document Scanner → Obsidian Pipeline

Send photo of any physical document to WhatsApp:
```
Ambil gambar whiteboard meeting tadi. Ekstrak semua task items. Simpan dalam Obsidian.
```
Gemini extracts text → MJ reformats → auto-saves to vault.

### 11d. Periodic Desktop Logging (Cron)

```bash
/cron add "every 2h 10:00-18:00" "Capture my screen. Check if I'm working on 
something productive. If I look stuck, suggest next action."
```
Runs 10AM-6PM, captures screen every 2 hours. MJ uses Gemini to understand context and nudge.

---

## Bonus: Gemini Live API (Unlimited Free — Future Research)

**Status**: Not implemented. Needs Hermes support for Live API transport.

You discovered these models with **unlimited** free tier on Gemini Live API:

| Model | Free Tier | Potential Use |
|---|---|---|
| Gemini 3 Flash Live | **Unlimited** | Real-time voice conversations with MJ through WhatsApp voice notes |
| Gemini 2.5 Flash Native Audio Dialog | **Unlimited** | Native audio — MJ speaks without text-to-speech conversion |
| Gemini 3.5 Live Translate | **Unlimited** | Real-time voice translation. Speak Malay, she translates to English live |

**When this could work:**
1. Hermes adds Live API support (check future releases)
2. WhatsApp voice note → Gemini Native Audio processes directly
3. MJ responds in voice, no STT/TTS pipeline needed

**For now**: Stick with Gemini 3.1 Flash Lite for vision (screenshot analysis). Live API is monitored for future Hermes releases.

---

## Bonus: One-Liners Worth Knowing

| Prompt | What it does |
|---|---|
| `/usage` | Show current session token usage + cost |
| `/insights 7` | Weekly analytics report |
| `/compress` | Manually compress long conversation |
| `/sethome` | Set current chat as cron delivery channel |
| `/platform list` | Show gateway health (adapter states) |
| `/approve` / `/deny` | Approve/deny pending dangerous commands |
| `/reasoning show` | Show model's thinking process |
| `/topic` | Enable multi-session DM mode (ChatGPT-style) |
| `/new` | Reset session (fresh memory snapshot) |
| `/skills` | List all available skills |
| `/obsidian search <query>` | Search all notes in the Obsidian vault |
| `/obsidian save "title"` | Save a quick note to the vault inbox |

---

*Pick one idea. Try it this week. Let Hermes learn.*