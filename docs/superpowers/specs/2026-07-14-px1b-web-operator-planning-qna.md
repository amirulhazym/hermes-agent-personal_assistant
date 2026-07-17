# PX-1b Web Operator — Sequential Planning Q&A (Doc A)

> **Role:** Primary decision workbook. Fill offline. Return when ready.  
> **Read first:** Doc B `2026-07-14-px1b-web-operator-audit-recap.md`  
> **Method:** `docs/superpowers/specs/PX-PLANNING-FRAMEWORK.md`  
> **No implementation until:** all critical Parts -> Status **locked** + joint step (4).
> **Date opened:** 2026-07-14  
> **How to fill:** Mark tables; write under Free text; set N.4 checkboxes.
> **2026-07-17 update:** Guided chat replaced offline table filling. The canonical
> locked answers are in Part 15 below and the approved design is
> `docs/superpowers/specs/2026-07-17-px1b-web-operator-design.md`. Blank fields in
> Parts 0-14 are historical prompts and are superseded by Part 15.

---

## How answers improve across Parts

```text
Part 0 Process  →  Part 1 Recap  →  Part 2 Goals  →  Part 3 Scope
        ↓
Part 4 Ladder  →  Part 5 Safety  →  Part 6 CUA  →  Part 7 Sessions
        ↓
Part 8 Product  →  Part 9 Runtime  →  Part 10 Integrations
        ↓
Part 11 Phasing →  Part 12 Acceptance →  Part 13 Risks →  Part 14 Sign-off
```

Later Parts may **override** earlier provisional answers — note changes in Part 14.

---

# Part 0 — Process lock

### 0.0 Earlier planning (NOT decided)

We use the five-step PX Planning Framework:

1. You receive docs → 2. You fill offline → 3. You return → 4. We lock → 5. We implement.

Package: Doc B (audit) + Doc A (this file). Linked and sequential.

### 0.1 Double-confirm

| # | Statement | YES / NO / CORRECT | Correction |
|---|-----------|--------------------|------------|
| 1 | No code until step (4) lock | | |
| 2 | I will fill this doc offline and return it | | |
| 3 | Framework may be reused for future PX tracks | | |
| 4 | Each git commit still needs explicit yes when AGENTS says so | | |

### 0.2 Your decisions

| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| 0.2.a | Preferred return format? | A) edit this file in place B) copy answers to chat C) both | | |
| 0.2.b | Language for free-text answers? | A) English B) Malay C) rojak OK | | |

Free text (process constraints):
> 

### 0.3 Your research / open questions
> 

### 0.4 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked

---

# Part 1 — Recap & verification (PX-1 foundation)

### 1.0 Earlier planning (NOT decided)

PX-1 Research is **COMPLETE** (Fasa 0–5 + 11-key Tavily pool). PX-1b must **compose** search/extract/research-expert, not rebuild them.

Residual honesty: full Telegram/WhatsApp “skill fire on research phrasing” was **not** fully proven in Fasa 5 (SSH E2E only).

### 1.1 Double-confirm

| # | Statement | YES / NO / CORRECT | Correction |
|---|-----------|--------------------|------------|
| 1 | Search cascade + hybrid-web + research-expert are live enough to build on | | |
| 2 | Account farming / Turnstile bypass stay PC ops, not agent default | | |
| 3 | We should not re-run Fasa 0–2 install/debug unless broken | | |
| 4 | Residual chat E2E for research-expert is optional pre-PX-1b or parallel | | |

### 1.2 Your decisions

| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| 1.2.a | Before PX-1b build, run Telegram research E2E? | A) Required gate B) Nice-to-have C) Skip | | |
| 1.2.b | If research tools break mid-PX-1b? | A) Pause PX-1b fix PX-1 B) Continue on stubs C) Decide case-by-case | | |
| 1.2.c | Journey anti-repeat playbook still binding? | A) Yes full B) Yes with edits (list) C) No | | |

Free text (what you believe is already “good enough” on Hermes for web research):
> 

### 1.3 Your research / open questions
> 

### 1.4 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked

---

# Part 2 — North star & success metrics

### 2.0 Earlier planning (NOT decided)

Your stated direction: less PC dependence for web tasks; CUA remains favorite for true desktop; Hermes becomes powerful web-capable agent from chat — not a chatbot that only talks.

Suggested horizons (challenge freely):

| Horizon | Draft success |
|---------|----------------|
| Day-1 MVP | From Telegram: multi-step public browse task without opening PC |
| Day-30 | Gated login session for 1–2 known sites + extract |
| Day-90 | Clear auto ladder L2→L3→L4; CUA only when needed; ops L5 rare |

### 2.1 Double-confirm

| # | Statement | YES / NO / CORRECT | Correction |
|---|-----------|--------------------|------------|
| 1 | Primary access surface is Telegram + WhatsApp (not only SSH) | | |
| 2 | “Less PC” means most *web* tasks leave VPS; desktop apps stay PC/CUA | | |
| 3 | Free-tier / self-host preference still beats convenience paid tools | | |

### 2.2 Your decisions

| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| 2.2.a | Primary user of PX-1b day-1 | A) You only B) You + future team C) Productize later | | |
| 2.2.b | Day-1 MVP definition | A) Public multi-step browse only B) Browse + one login C) Full ladder incl CUA bridge | | |
| 2.2.c | Must-work example #1 (write your own if better) | A) “Open docs site, click section, summarize” B) “Login portal X, fetch Y” C) Custom → free text | | |
| 2.2.d | How measure “less PC dependence”? | A) % tasks no PC B) Feeling only C) Explicit checklist of task types | | |

Free text — **your** definition of POWERFUL web Hermes (3–10 bullets):
> 

Free text — success metric you care about most:
> 

### 2.3 Your research / open questions
> 

### 2.4 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked

---

# Part 3 — Goals / non-goals

### 3.0 Earlier planning (NOT decided)

**In scope (draft):** multi-step navigation, form fill (gated), authenticated scrape (gated), structured extract after browse, failure reports, compose with research-expert.

**Out of scope (draft):** silent captcha solve, mass account farming, paid browser cloud, full remote desktop OS, P4 multi-agent rewrite, med system changes.

### 3.1 Double-confirm

| # | Statement | YES / NO / CORRECT | Correction |
|---|-----------|--------------------|------------|
| 1 | PX-1b is not full P4 OS | | |
| 2 | Mass signup / key harvest is ops not product | | |
| 3 | “Bypass” as default chat behavior is forbidden | | |

### 3.2 Your decisions

| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| 3.2.a | Allow Hermes to attempt soft anti-bot (headers, slow human-like)? | A) Yes limited B) No ever C) Only on PC | | |
| 3.2.b | Allow Hermes to fill forms that submit data externally? | A) Always ask first B) Allow if non-destructive C) Never | | |
| 3.2.c | Public posting / commenting via browser? | A) Always ask B) Deny always C) Allow after once-trust | | |
| 3.2.d | Purchases / checkout? | A) Deny B) Ask always C) Allowed with hard confirm | | |
| 3.2.e | Relationship to research-expert | A) Separate web-operator expert B) Extend research-expert C) Both (operator tool + research composes it) | | |

Free text — add goals:
> 

Free text — hard non-goals (your red lines):
> 

### 3.3 Your research / open questions
> 

### 3.4 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked

---

# Part 4 — Architecture ladder

### 4.0 Earlier planning (NOT decided)

Draft ladder (cheapest / safest first):

| L | Name | Where | When |
|---|------|-------|------|
| **L0** | Refuse / ask human | — | Credentials, money, public post, unclear ToS risk |
| **L1** | HTTP / curl-impersonate | VPS | Simple GET, known static |
| **L2** | hybrid-web extract (+ search) | VPS | Public content / research (PX-1) |
| **L3** | Interactive browser (browser-use / Playwright) | VPS gated | Multi-step JS, clicks, public flows |
| **L4** | Computer Use (CUA) | **PC** | Desktop apps, visual UI, your favorite power |
| **L5** | CDP ops (signup/captcha harvest) | **PC ops** | Never default chat; human-gated ops only |

Escalation rule (draft): try lower L first; escalate only with reason logged.

### 4.1 Double-confirm

| # | Statement | YES / NO / CORRECT | Correction |
|---|-----------|--------------------|------------|
| 1 | L2 already covers most “read this page” needs | | |
| 2 | L3 is the main “less PC” investment | | |
| 3 | L4 stays PC-first | | |
| 4 | L5 must not become a chat skill | | |

### 4.2 Your decisions

| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| 4.2.a | Accept L0–L5 ladder? | A) Accept B) Accept with edits C) Reject redesign | | |
| 4.2.b | Default start level for vague “browse X”? | A) L2 B) L3 C) Ask user | | |
| 4.2.c | Auto-escalate L2→L3 without asking? | A) Yes if extract empty B) Always ask C) Never auto | | |
| 4.2.d | Auto-escalate L3→L4 (need PC)? | A) Always ask B) Auto if L3 fails N times C) Never suggest CUA | | |
| 4.2.e | Where run L3 primarily? | A) VPS B) PC only C) VPS default, PC fallback | | |
| 4.2.f | Max parallel L3 jobs | A) 1 B) 2 C) 3 (match max children) | | |

Free text — redraw ladder if needed:
> 

### 4.3 Your research / open questions
> 

### 4.4 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked

---

# Part 5 — Safety & human-in-the-loop (EXPANDED)

### 5.0 Earlier planning (NOT decided)

PRD/AGENTS: ask before credential, cost, destructive, public, out-of-scope.

**Operator HITL matrix (draft):**

| Action class | Default |
|--------------|---------|
| Read public page | Allow |
| Multi-step public navigation | Allow (log) |
| Enter username/email | Ask first |
| Enter password / OTP | Ask first; prefer you type / vault |
| Submit form that changes account state | Ask first |
| Download file | Ask if executable/large |
| Upload file | Ask first |
| Payment / checkout | Deny or hard double-confirm |
| Post / comment / message third party | Ask first |
| Bypass captcha automatically | Deny as agent default |
| Store session cookies | Ask first time per site |

Runtime pattern: **draft plan → confirm → act → report evidence**.

### 5.1 Double-confirm

| # | Statement | YES / NO / CORRECT | Correction |
|---|-----------|--------------------|------------|
| 1 | Silent password entry by agent is unacceptable | | |
| 2 | Logging must never store raw passwords | | |
| 3 | “Looks automated / may violate ToS” → ask or refuse | | |
| 4 | Med system remains untouchable | | |

### 5.2 Your decisions

| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| 5.2.a | Confirm channel for HITL | A) Same chat B) Telegram only C) WhatsApp only D) Either | | |
| 5.2.b | Confirm timeout if you don’t reply | A) Abort B) Wait indefinitely C) Wait N minutes then abort | | |
| 5.2.c | Screenshots of pages in logs/artifacts? | A) Yes redacted B) Yes full C) No images | | |
| 5.2.d | Store URLs visited in trace log? | A) Yes B) Yes hashed C) No | | |
| 5.2.e | Agent may open only allowlisted domains day-1? | A) Yes allowlist B) Blocklist only C) Open web + HITL for risk | | |
| 5.2.f | If allowlist, who maintains it? | A) You B) Agent proposes C) Both | | |
| 5.2.g | Rate limit operator actions | A) Strict (e.g. 10/hour) B) Soft C) No limit | | |

Free text — situations that must **always** hard-stop:
> 

Free text — situations that may proceed without ask:
> 

### 5.3 Your research / open questions
> 

### 5.4 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked

---

# Part 6 — Computer Use (CUA) policy (EXPANDED — favorite feature)

### 6.0 Earlier planning (NOT decided)

You called CUA a favorite. Reality:

- CUA = desktop automation (windows, click, type, screenshot) via **cua-driver on Windows PC**.  
- VPS cannot run Windows `cua-driver.exe`.  
- browser-use ≠ CUA (browser-only vs whole desktop).  
- Config risk: `computer_use.enabled: true` with empty MCP = false confidence.

**Draft CUA policy:**

1. Keep CUA; invest in reliability on PC.  
2. Hermes on VPS **detects** need for CUA and **asks you** to enable PC path / approve.  
3. Do not fake CUA on VPS with half-broken tools.  
4. Prefer L3 for pure web; L4 when desktop UI, multi-app, or L3 insufficient.  
5. Sakana/Qwen drivers = optional PC skills, not VPS core.

**Handoff phrase (draft):**  
“This needs Computer Use on your PC (CUA). I can’t do it on VPS. Approve and ensure cua-driver/Brave ready?”

### 6.1 Double-confirm

| # | Statement | YES / NO / CORRECT | Correction |
|---|-----------|--------------------|------------|
| 1 | CUA remains strategically important to you | | |
| 2 | You accept CUA is PC-bound for now | | |
| 3 | False “CUA on VPS” claims without real runtime | | |
| 4 | Web-only tasks should try L2/L3 before CUA | | |

### 6.2 Your decisions

| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| 6.2.a | CUA investment level this quarter | A) High (polish PC path) B) Medium (docs + fix config) C) Low (document only) | | |
| 6.2.b | Future remote CUA bridge (PC agent reachable from VPS)? | A) Want later B) Want in PX-1b C) Never | | |
| 6.2.c | When L3 fails, auto-suggest CUA? | A) Yes B) Only if task desktop-like C) Never auto | | |
| 6.2.d | Fix `computer_use` flag vs MCP inconsistency as Fasa 0 chore? | A) Yes required B) Optional C) Leave | | |
| 6.2.e | Keep sakana/qwen automation skills? | A) Keep PC B) Archive C) Rebuild later | | |
| 6.2.f | CUA allowed apps day-1 | A) Browser only B) Browser + Office C) Any app after ask D) Any app free | | |
| 6.2.g | Screenshot storage for CUA | A) Temp only B) Artifact dir C) Never persist | | |

Free text — **your favorite CUA use cases** (ranked):
> 

Free text — when you would be unhappy if Hermes used CUA:
> 

### 6.3 Your research / open questions
> 

### 6.4 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked

---

# Part 7 — Sessions, credentials, identity

### 7.0 Earlier planning (NOT decided)

Session vault (draft): encrypted store of cookies/localStorage per site profile; path under `~/.hermes/secrets/sessions/` or PC equivalent; never in git; human creates first login or confirms storage.

Password policy (draft): Hermes does not store plaintext passwords long-term; prefer OS keychain / you paste once per session / app passwords.

### 7.1 Double-confirm

| # | Statement | YES / NO / CORRECT | Correction |
|---|-----------|--------------------|------------|
| 1 | Session cookies are sensitive secrets | | |
| 2 | Multi-account profiles may be needed later | | |
| 3 | Vault is out of git and backups must be careful | | |

### 7.2 Your decisions

| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| 7.2.a | Day-1 auth strategy | A) No login MVP B) Manual cookie import C) Agent login with HITL | | |
| 7.2.b | Where store sessions | A) VPS only B) PC only C) Both D) Decide later | | |
| 7.2.c | Password handling | A) You type always B) Env vars named per site C) One-time paste to agent memory ephemerally D) External password manager only | | |
| 7.2.d | Session TTL default | A) 24h B) 7d C) Until revoke D) Per site | | |
| 7.2.e | Max sites in vault day-1 | A) 0 B) 3 C) 10 D) Unlimited | | |
| 7.2.f | 2FA / OTP | A) You always provide B) Agent waits for you C) Out of scope day-1 | | |

Free text — sites you most want Hermes to access authenticated (names only, no passwords):
> 

### 7.3 Your research / open questions
> 

### 7.4 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked

---

# Part 8 — Product shape (skills / experts / triggers)

### 8.0 Earlier planning (NOT decided)

Draft productization:

| Piece | Draft |
|-------|--------|
| Expert skill | `skills/experts/web-operator/SKILL.md` |
| Composes | L1–L3 tools; escalates L4/L5 per policy |
| Research-expert | Calls web-operator when browse stage needed |
| Triggers | “browse”, “login to”, “click through”, “automate site”, “fill form” |
| Constraints | depth=1/max=3; HITL matrix; no med |

### 8.1 Double-confirm

| # | Statement | YES / NO / CORRECT | Correction |
|---|-----------|--------------------|------------|
| 1 | Skills ≠ experts; expert composes tools | | |
| 2 | User-facing name can be simpler than skill path | | |

### 8.2 Your decisions

| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| 8.2.a | Packaging | A) New web-operator expert B) Only tools no expert C) Fold into research-expert only | | |
| 8.2.b | Chat command prefix? | A) none B) /browse C) /web D) other | | |
| 8.2.c | Default language of operator reports | A) Match user B) English always C) Malay | | |
| 8.2.d | Artifact output for browse runs? | A) Yes like research B) Trace only C) Chat only | | |
| 8.2.e | skill-trigger patterns — aggressiveness | A) Broad B) Narrow keywords C) Explicit invoke only | | |

Free text — example user messages that **must** trigger operator:
> 

Free text — messages that must **not** steal from med/research wrongly:
> 

### 8.3 Your research / open questions
> 

### 8.4 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked

---

# Part 9 — Runtime limits (VPS / PC)

### 9.0 Earlier planning (NOT decided)

VPS ~1.9Gi RAM. Interactive Chromium is heavy. Draft limits:

- Max 1 L3 browser at a time  
- Hard timeout 120–300s per job  
- Kill on OOM / gateway pressure  
- Preflight `free -h` before L3  
- Prefer L2 when possible  

### 9.1 Double-confirm

| # | Statement | YES / NO / CORRECT | Correction |
|---|-----------|--------------------|------------|
| 1 | Gateway stability > fancy browser jobs | | |
| 2 | Swap is safety net not free performance | | |

### 9.2 Your decisions

| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| 9.2.a | L3 timeout | A) 60s B) 180s C) 300s D) Custom | | |
| 9.2.b | If RAM available < X, refuse L3 | A) 400MB B) 600MB C) 800MB D) No check | | |
| 9.2.c | Headless only on VPS? | A) Yes B) Allow headed if possible C) N/A PC only L3 | | |
| 9.2.d | Night-time heavy jobs | A) Allowed B) Quiet hours block C) Ask | | |
| 9.2.e | Upgrade VPS RAM later? | A) Consider if needed B) Never paid C) Discuss when blocked | | |

Free text — stability fears:
> 

### 9.3 Your research / open questions
> 

### 9.4 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked

---

# Part 10 — Integrations: adopt / kill / defer

### 10.0 Earlier planning (NOT decided)

| Integration | Draft verdict |
|-------------|----------------|
| hybrid-web / crawl4ai / Playwright extract | **Keep** (PX-1) |
| search-cascade / Tavily free pool | **Keep** |
| browser-use self-hosted | **Adopt** as L3 candidate after verify |
| browser-use cloud | **Deny** without paid yes |
| curl-impersonate | **Defer** L1 optional |
| Scrapling | **Defer** anti-bot research later |
| Firecrawl | **Stay killed** |
| cua-driver | **Keep PC** |
| sakana/qwen drivers | **Defer/archive** per Part 6 |

### 10.1 Double-confirm

| # | Statement | YES / NO / CORRECT | Correction |
|---|-----------|--------------------|------------|
| 1 | Self-hosted > paid cloud for browser | | |
| 2 | “Installed in docs” ≠ productized | | |

### 10.2 Your decisions

| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| 10.2.a | browser-use as L3 engine | A) Primary B) Trial only C) Skip use Playwright raw D) Skip L3 | | |
| 10.2.b | curl-impersonate | A) Fasa early B) Later C) Never | | |
| 10.2.c | Scrapling | A) Later B) Never C) Research spike only | | |
| 10.2.d | Paid browser cloud if free fails hard | A) Never B) Ask case-by-case C) Pre-approve budget | | |
| 10.2.e | Fresh VPS verify browser-use import | A) Required Fasa 0 B) Optional | | |

Free text — other tools you want considered:
> 

### 10.3 Your research / open questions
> 

### 10.4 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked

---

# Part 11 — Phasing (execution order after lock)

### 11.0 Earlier planning (NOT decided)

| Fasa | Theme | Depends on |
|------|--------|------------|
| **0** | Truth: inventory browser-use, fix computer_use/MCP honesty, docs sync | Parts 1,6,10 |
| **1** | Policy freeze: HITL matrix + ladder in SOUL/skill docs | Parts 4,5 |
| **2** | L3 MVP: public multi-step browse skill, no login | Parts 2,8,9 |
| **3** | Session vault + gated login (if you chose auth) | Parts 5,7 |
| **4** | CUA PC path polish + handoff | Part 6 |
| **5** | E2E from Telegram/WhatsApp + failure drills | Part 12 |

Gates: evidence after each Fasa; user go if AGENTS requires.

### 11.1 Double-confirm

| # | Statement | YES / NO / CORRECT | Correction |
|---|-----------|--------------------|------------|
| 1 | One Fasa at a time | | |
| 2 | No med touch in any Fasa | | |

### 11.2 Your decisions

| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| 11.2.a | Accept Fasa 0–5 map? | A) Accept B) Reorder C) Merge/split | | |
| 11.2.b | Skip Fasa 3 (auth) initially? | A) Yes skip B) No include C) Depends Part 7 | | |
| 11.2.c | Skip Fasa 4 (CUA polish) initially? | A) Yes B) No C) Docs-only Fasa 4 | | |
| 11.2.d | Max calendar pace | A) Aggressive B) Steady C) Slow careful | | |

Free text — reorder phases:
> 

### 11.3 Your research / open questions
> 

### 11.4 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked

---

# Part 12 — Acceptance tests (definition of done)

### 12.0 Earlier planning (NOT decided)

**Draft PASS criteria for PX-1b “MVP done”:**

1. From Telegram: task “browse public multi-step and summarize” succeeds without PC.  
2. Ladder logs show L2 tried before L3 when appropriate.  
3. HITL fires on simulated login request (no silent password).  
4. VPS remains healthy (gateway up) after browser job.  
5. Captcha/signup still not exposed as default skill.  
6. CUA handoff message correct when L4 required.  
7. Trace/artifact exists for operator run.  

### 12.1 Double-confirm

| # | Statement | YES / NO / CORRECT | Correction |
|---|-----------|--------------------|------------|
| 1 | Done means evidenced, not claimed | | |
| 2 | Labels VALIDATED/UNTESTED/REJECTED apply | | |

### 12.2 Your decisions

| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| 12.2.a | Must-pass demos (pick all that apply) | A) public multi-step B) gated login C) CUA handoff D) fallback L2 E) custom | | |
| 12.2.b | Who runs final acceptance? | A) You on phone B) Agent SSH + you C) Both | | |
| 12.2.c | Minimum confidence to call VALIDATED | A) 1 demo B) 3 demos C) 1 week daily use | | |

Free text — your personal acceptance script:
> 

### 12.3 Your research / open questions
> 

### 12.4 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked

---

# Part 13 — Risks & anti-patterns

### 13.0 Earlier planning (NOT decided)

| Risk | Mitigation draft |
|------|------------------|
| VPS OOM | Single L3, preflight, timeout |
| IP ban / bot detect | Escalate to PC/human; don’t thrash |
| Secret leak | No passwords in logs; redaction |
| Skill not firing | Triggers + E2E chat test |
| Rebuild PX-1 | Part 1 anti-repeat |
| Scope creep to P4 | Explicit non-goal |
| Fake CUA on VPS | Config honesty Fasa 0 |
| Bypass culture | Part 5 policy |

### 13.1 Double-confirm

| # | Statement | YES / NO / CORRECT | Correction |
|---|-----------|--------------------|------------|
| 1 | Kill paths in Doc B stay killed | | |
| 2 | Paid cloud not sneaked in mid-build | | |

### 13.2 Your decisions

| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| 13.2.a | Highest risk you fear | A) OOM B) Secrets C) ToS/ban D) Scope creep E) Other | | |
| 13.2.b | Abort PX-1b if? | Free text | | |

Free text — risks we missed:
> 

### 13.3 Your research / open questions
> 

### 13.4 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked

---

# Part 14 — Final sign-off table

Copy your **locked** answers here when ready for step (4). Leave blank until then.

| ID | Topic | Locked answer | Date |
|----|-------|---------------|------|
| 1.2.a | Telegram research E2E gate | | |
| 2.2.b | Day-1 MVP | | |
| 3.2.e | Expert packaging | | |
| 4.2.a | Ladder | | |
| 4.2.e | L3 where | | |
| 5.2.a | HITL channel | | |
| 5.2.e | Allowlist | | |
| 6.2.a | CUA investment | | |
| 6.2.b | Remote CUA bridge | | |
| 7.2.a | Auth day-1 | | |
| 8.2.a | Product packaging | | |
| 9.2.a | L3 timeout | | |
| 10.2.a | browser-use role | | |
| 11.2.a | Phase map | | |
| 12.2.a | Must-pass demos | | |
| 13.2.a | Top risk | | |

### 14.1 Global lock

| Statement | YES / NO |
|-----------|----------|
| I have read Doc B | |
| I accept residual UNTESTED items listed | |
| I want step (4) final discussion now | |
| I authorize design freeze after discussion | |

### 14.2 Free text — anything else for implementation agent
> 

### 14.3 Status
- [ ] unanswered
- [ ] provisional
- [ ] locked — ready for joint final decision

---

## Agent defaults summary (for your challenge — not binding)

| Topic | Default draft |
|-------|----------------|
| MVP | Public multi-step L3 on VPS; no login |
| Expert | New `web-operator` |
| Ladder | L0–L5 as written |
| CUA | PC favorite; handoff; fix config honesty |
| Auth | Phase after MVP; always HITL |
| Captcha ops | Stay L5 PC |
| browser-use | Trial as L3 after VPS verify |
| Paid cloud | No |
| Concurrency | 1 browser job |
| Chat E2E research | Nice-to-have parallel, not hard block |

---

## Return instructions

1. Save this file with your answers (or reply with filled sections).  
2. Optional: notes in Doc B §9.  
3. Message: **“PX-1b Q&A returned”** (or similar).  
4. We run step (4): resolve conflicts → lock design → then implementation plan.  

**Do not start implementation until Part 14.3 is locked and we confirm.**

---

*End Doc A — Sequential Planning Q&A for PX-1b Web Operator.*

---

# Part 15 - Guided-chat locked decision addendum (2026-07-17)

This addendum is the authoritative answer record for Parts 0-14. It preserves the
original workbook as planning history without pretending its blank tables remain open.

## 15.1 Process and foundation

- [x] No implementation before design lock and implementation plan.
- [x] Read-only VPS inspection and safe verification are allowed during planning.
- [x] Guided chat is the Q&A return format; language may match Amirul/rojak.
- [x] Every commit and push still requires separate explicit approval.
- [x] Telegram Research Expert E2E is a required pre-implementation gate.
- [x] A failed PX-1 dependency pauses PX-1b; repair only the failed contract.
- [x] The full PX-1 anti-repeat playbook remains binding.

## 15.2 Product and architecture

- [x] V1 is complete L1-L4 plus a secure VPS-to-PC CUA worker and human L5 handoff;
  there is no reduced day-one MVP.
- [x] Amirul is the only user.
- [x] Phone-first means WhatsApp/Telegram are universal command/control surfaces, VPS
  is the 24/7 primary worker, PC is an optional high-power worker, and GitHub is the
  durable source layer.
- [x] Both Telegram and WhatsApp are release requirements.
- [x] Use a separate `web-operator` expert, narrow natural-language triggers, and
  optional `/browse`; Research Expert composes it when interaction is required.
- [x] Start with L1/L2 and automatically escalate to L3 with a logged reason.
- [x] Evaluate native Hermes browser tools first. Fill proven gaps with isolated
  adapters; trial browser-use only if native acceptance fails.
- [x] Keep the live Hermes version. Do not silently upgrade or patch live core freely.
- [x] Paid browser cloud and extra VPS spending are not allowed.

## 15.3 Runtime and integrations

- [x] Benchmark one, two, then at most three browser jobs and lock the highest optimized
  concurrency that preserves gateway health.
- [x] Limit an unattended run to 30 actions or 10 minutes; cancel a single stuck
  operation after 180 seconds.
- [x] Bounded self-hosted compatibility adapters may be adopted only after measured
  benefit; no automatic collection of every candidate tool.
- [x] No arbitrary cap on enrolled site profiles; each site/account is separately
  approved, isolated, expiring, and revocable.
- [x] Qwen/Sakana are historical test references with one optional comparison after the
  real CUA path works.
- [x] PC availability: after CUA approval, proceed if online; if offline ask to turn it
  on, postpone, schedule, or cancel. No Wake-on-LAN.

## 15.4 Safety and privacy

- [x] Personal form data requires approval before entry and again before submission.
- [x] Every external message, comment, or post requires exact final approval.
- [x] Every file download and upload requires action-bound approval.
- [x] Checkout may finish only after transaction-bound final approval; banking/card/
  payment secrets remain in the user's normal phone browser or official app.
- [x] Ordinary passwords/non-financial OTPs use private phone takeover with all agent
  input, observation, capture, clipboard/keystroke capture, and logging suspended.
- [x] Approvals originate in the same chat with owner-only Telegram fallback and expire
  after 15 minutes.
- [x] Public HTTPS browsing is allowed with SSRF/private-network and dangerous-target
  controls.
- [x] CAPTCHA flow: permitted normal attempt, minimal human challenge completion,
  resume, then full human L5 only as last resort. No bypass services/account farming.
- [x] Private medical portals are allowed only in isolated high-sensitivity mode and
  never touch existing med code/state, durable memory, or normal artifacts.
- [x] Web/UI content is untrusted. Approvals are owner-only, single-use, task/action/
  parameter-bound, and invalidated by material change.
- [x] Maximum task completion applies only within safety, cost, and gateway rails.

## 15.5 Evidence, acceptance, and phasing

- [x] Keep minimum selected redacted browser/CUA evidence for 14 days; raw frames are
  deleted immediately and capture is disabled during takeover/high-sensitivity screens.
- [x] Store normalized redacted URLs, not tokens, query strings, account IDs, or
  sensitive path sections.
- [x] Acceptance uses controlled fixtures plus real phone workflows.
- [x] All 20 frozen cases must pass; no waived or partial cases.
- [x] Execute steady evidence-gated phases, one approved phase at a time.
- [x] The PX Planning Framework may be reused, but decisions never carry forward as
  automatic approval.

## 15.6 Global lock

- [x] Doc B was read and its residual `UNTESTED` items are accepted as the planning
  baseline, not as completed capability claims.
- [x] Joint final discussion completed.
- [x] Design sections 1-5 approved in guided chat on 2026-07-17.
- [x] Design freeze authorized for the written specification.
- [x] Status: **locked - awaiting written-spec review before implementation planning**.

## 15.7 Written-spec self-review clarifications

These safety-preserving details close ambiguities found after the guided design review:

- [x] Scheduled/postponed work preserves intent only and requires fresh approval at
  execution time.
- [x] Downloads use two stages: approve quarantine receipt, validate actual hash/type/
  size, then approve release/open/move/share separately.
- [x] VPS control plane owns grants; PC connects outbound-only and revalidates grants;
  phone/worker disconnect stops input fail-closed.
- [x] Private takeover canary tests prove model/capture/log channels are suspended.
- [x] Runtime policy explicitly covers every reachable PRD Section 7.5 action class.
- [x] L4 inherits public-destination restrictions; private/local target automation is
  outside V1.
- [x] Medical portal runs create only a separate encrypted metadata audit, never a
  normal artifact.
- [x] Session state is encrypted with host-local key custody and revocation deletes all
  derived state.
- [x] Resource/concurrency and run-budget pass criteria are objective and testable.
- [x] The Phase 0 Telegram gate is rerun as case 1 of the clean final 20/20 suite.
