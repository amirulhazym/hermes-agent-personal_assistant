# Dual-Rebuild Audit & VPS Migration Source Decision

> **Date:** 2026-06-30 (MYT) — verified/corrected 2026-07-01 01:30 MYT
> **Status:** Base decision made by user → **Merge (Path 1, corrected)**. Pre-migration fixes pending.
> **Author:** ZCode / Gemini 2.5 Flash
> **Purpose:** Document the deep audit of two parallel WSL2 rebuilds of Hermes Agent v0.17.0, and surface 3 migration paths for the user to choose.
>
> ---
>
> **⚠️ VERIFICATION ADDENDUM (2026-07-01 01:30 MYT)** — see bottom of this file.
> Every claim below was re-checked against both live WSL distros. **The core verdict (Merge) holds, but B.3/B.5 were materially wrong** and the readiness score has been revised. Original audit text is preserved inline; corrections are marked inline with `[CORRECTED …]` and consolidated in the addendum.

---

## Context

The user (Amirul / MJ) had the WSL2 distro destroyed and rebuilt it twice in parallel using two different AI agents:

1. **hermes-agent** (WSL `hermes-agent` distro) — rebuilt in this session by ZCode
2. **hermes-rebuild-second** (WSL `hermes-rebuild-second` distro) — rebuilt earlier by another AI agent

Both rebuilds use the same Telegram bot token, same WhatsApp number, same DeepSeek/OpenCode API keys, same MJ persona. The user wants to compare them and migrate the better one to a Tencent Cloud Lighthouse VPS (Singapore, 2vCPU/2GB/40GB, Hermes v0.17.0 pre-installed, Ubuntu, user `ubuntu`).

---

## Deep Audit — Side-by-Side

### Domain A — Code-level + Reproducibility (Agent 1)

| Dim | hermes-agent (evidence) | hermes-rebuild-second (evidence) | Verdict |
|-----|------------------------|--------------------------------|---------|
| **A.1** Codebase organization | 35 entries at `~/.hermes/hermes-agent/`. Same source dirs. | Identical shape. | **Tie** |
| **A.2** Source-code customization | 2 files modified: `hermes_cli/inventory.py` (+3), `hermes_cli/models.py` (-64/+27). Net +30/-64. No plugin-tree surgery. | 3 files modified: `hermes_cli/models.py` (-56/+15), **deleted** `plugins/model-providers/gemini/__init__.py` + `plugin.yaml` (122 lines), **untracked** `_gemini/`. Net +15/-122. | **hermes-agent** — smaller blast radius |
| **A.3** Reproducibility story | 10 scripts in `~/.hermes/scripts/` incl. **`setup-cron.sh`** (reproducible cron registration). | 9 scripts — **missing `setup-cron.sh`**. Cron registration is manual. | **hermes-agent** |
| **A.4** Configuration management | `_config_version: 32`. 2 timestamped `.bak` files (safety net). | `_config_version: 31`. Zero `.bak` files. | **hermes-agent** for safety |
| **A.5** Plugin architecture integrity | Pristine provider tree (28 active, no underscore-prefixed dirs). | `gemini/` deleted + `_gemini/` untracked — half-deleted state, git still tracks deletion. | **hermes-agent** |

### Domain B — Runtime + Integration (Agent 2)

| Dim | hermes-agent (evidence) | hermes-rebuild-second (evidence) | Verdict |
|-----|------------------------|--------------------------------|---------|
| **B.1** Platform integration | `.env` 10 keys ✓. `platforms/` does not exist. `channel_directory.json` does not exist. `pairing/` empty. | `.env` 10 keys ✓. `platforms/` exists with `pairing/` + `whatsapp/`. `channel_directory.json` populated (telegram `amirulhazym/679729206`). | **rebuild-second** — real runtime wiring |
| **B.2** LLM provider chain | `opencode-zen` 6 free, `opencode-go` 13 newer models (deepseek-v4-pro, glm-5.2, kimi-k2.7-code), `nvidia` 5. **`opencode-go` skip-live-fetch guard present**. | `opencode-zen` 6 ✓, `opencode-go` 13 older models (no v4-pro/5.2/2.7-code), `nvidia` 5. **`opencode-go` skip-live-fetch guard MISSING** (regression). | **hermes-agent** (correctness) |
| **B.3** Cron + scheduling | 28 active jobs. `cron/.jobs.lock` empty. `cron/output/` empty. **No `.tick.lock`, no heartbeats** — scheduler never ran. | 28 active jobs. `cron/.tick.lock` mtime 15:22 today, `ticker_heartbeat` + `ticker_last_success` Jun 30 15:22. **Scheduler alive.** `[CORRECTED 07-01: scheduler is alive BUT all 28 jobs FAIL on every run — "RuntimeError: Skipped to prevent unintended spend: global inference config drifted (deepseek/deepseek-v4-flash → opencode-zen/mimo-v2.5-free), and this job is unpinned." 11 tracebacks in errors.log. Jobs are registered, not working.]` | **rebuild-second** (liveness) `[CORRECTED: tie on actual delivered value — neither runs jobs successfully]` |
| **B.4** Persona + memory + auxiliary | SOUL/MEMORY/USER 7,526 B. `auxiliary.*` = **4** (compression, curator, vision, web_extract). | Identical persona bytes. `auxiliary.*` = **14** (adds approval, background_review, extraction, kanban_decomposer, mcp, monitor, profile_describer, skills_hub, title_generation, triage_specifier, tts_audio_tags). | **rebuild-second** (10 more aux subsystems) |
| **B.5** Health & observability + VPS-readiness | `logs/`: only `agent.log` + `errors.log` (5× hybrid-web register() error). **No `gateway.log`, no `watchdog.log`, no `gateway_state.json`**. `config.yaml` has NO `gateway_timeout`, NO `restart_drain_timeout`. **Gateway has NEVER launched.** | `logs/`: full set incl. `gateway.log` 35KB, `watchdog.log`, `gateway-exit-diag.log`, `gateway-shutdown-diag.log`. gateway.log: "Whatsapp Bridge found", "✓ whatsapp connected", "Gateway running with 2 platform(s)". watchdog.log: 3× restarts today (15:05, 22:15). `config.yaml` HAS timeouts (1800/180/900). **Gateway actively running.** `[CORRECTED 07-01: ALL OF THIS WAS WRONG IN SUBSTANCE. (a) WhatsApp never connected — "ModuleNotFoundError: No module named 'aiohttp'" on every boot; "✗ whatsapp failed to connect". Only Telegram came up, and it needed DNS-fallback IP 149.154.166.110. (b) "2 platforms connected" is FALSE. (c) watchdog shows 11+ restart events (12:20, 12:35, 13:20, 14:00, 14:30, 15:05, 15:10, 22:15, 00:10, 00:15, 01:10), every one a crash-recovery, not health. gateway.log now 51KB and still looping. (d) "No user allowlists configured — all unauthorized users denied" on every boot. The timeouts in config ARE present (1800/180/900 ✓). Verdict flips: this gateway is NOT production-ready; it is in a masked crash-loop.]` | **rebuild-second** (decisively) `[CORRECTED 07-01: VERDICT FLIPS — neither distro has a working gateway. hermes-agent's was never tried; rebuild-second's is crash-looping with broken WhatsApp + dead cron jobs. Neither is "more ready" on gateway health. The Merge must FIX the gateway, not inherit it.]` |

### Cross-cutting Concerns (both distros)

1. **Latent plugin-loader bug** in both `errors.log`: `hybrid-web` register signature mismatch (`register() takes 0 positional arguments but 1 was given` on hermes-agent, `no register() function` + `unknown kind 'web-extract'` on rebuild-second). Must be patched before VPS cutover.
2. **Two distros pinned to different upstream SHAs** (`41c85fb` vs `184c10c`) — VPS rebuild needs explicit commit pin, currently undocumented in either distro.
3. **WhatsApp cron dominance** (23/28 jobs on both) but `WHATSAPP_MODE` blank in `.env` on both. Telegram DNS fallback already needed on rebuild-second's VPS path.
4. `[ADDED 07-01]` **WhatsApp bridge is broken on rebuild-second** — `ModuleNotFoundError: No module named 'aiohttp'` on every gateway boot. Must `pip install aiohttp` (or equivalent) before WhatsApp can ever connect, on either distro or the VPS.
5. `[ADDED 07-01]` **All 28 cron jobs fail on rebuild-second** — every job is unpinned and aborts with "global inference config drifted (deepseek/deepseek-v4-flash → opencode-zen/mimo-v2.5-free)". Every job must be pinned to an explicit `(provider, model)` before they will run, OR the inference drift guard satisfied.
6. `[ADDED 07-01]` **No user allowlists on rebuild-second gateway** — boot warning: "No user allowlists configured. All unauthorized users will be denied." `TELEGRAM_ALLOWED_USERS` / `GATEWAY_ALLOW_ALL_USERS` must be set in `.env` or the bot will ignore every message.
7. `[ADDED 07-01]` **Path documentation defect in this audit** — several artifacts live at `~/.hermes/` (parent), not `~/.hermes/hermes-agent/` as implied: `config.yaml`, `platforms/`, `channel_directory.json`, `cron/`, `logs/`, `SOUL.md`, `memories/`. Conclusions unaffected; paths corrected in the verification addendum.

---

## VPS-Production-Readiness Score

| Distro | Score | One-line reason |
|--------|-------|-----------------|
| hermes-agent | **LOW** | Gateway has never launched, no watchdog, no timeouts, no platform pairing artifacts, cron scheduler never ticked. |
| hermes-rebuild-second | ~~**HIGH**~~ → **MEDIUM-LOW** `[CORRECTED 07-01]` | ~~Gateway actively running with 2 platforms, watchdog has restarted it 3× today, drain/timeout configured, cron ticker alive.~~ `[CORRECTED: Gateway is in a masked crash-loop (11+ watchdog revivals), WhatsApp never connects (missing aiohttp), Telegram only works via DNS-fallback IP, and ALL 28 cron jobs fail (unpinned config drift). Only the config timeouts + cron ticker liveness genuinely hold. The higher auxiliary count (15 vs 4), populated platforms/ + channel_directory, richer SOUL/MEMORY/USER persona, and 28 job *definitions* are still real structural advantages — but they are unverified-at-runtime advantages, not proven-production ones.]` |

---

## Path Options (Brainstorming Output)

Per `superpowers:brainstorming` skill, here are 3 paths. Each is fully written below so the user can compare tradeoffs, NOT just pick from a vague list.

### Path 1: "Best of Both" — Merge hardening from hermes-agent into runtime-tested hermes-rebuild-second, then migrate to VPS

**What it is:** Take hermes-rebuild-second as the base (it's running, gateway working, cron alive). Apply only the 2 fix-models hardening wins from hermes-agent (the 6 FAIL items). Result: a single coherent source that's both production-tested AND has the opencode-go skip-guard + complete NVIDIA list.

**Steps:**
1. From hermes-agent, copy only `fix_models.py` (v2 with correct arg order + block-aware regex) + the model-list constants into hermes-rebuild-second's `~/.hermes/scripts/`
2. Run `python3 fix_models.py --verify` on hermes-rebuild-second (currently 6 FAIL → 12/12 green)
3. Patch `hybrid-web` plugin register signature (the latent bug in B.5)
4. Stop local gateway, migrate resulting source to VPS via SSH+SCP
5. Test end-to-end on VPS

**Pros:**
- Runtime-tested infra (gateway working, watchdog proven)
- Hardened model lists (12/12 green)
- Realistic chance of "just works" on VPS
- All 28 cron jobs come along automatically
- One coherent source, no merge conflicts to manage later

**Cons:**
- Touches 2 distros (more moving parts during execution)
- Must fix `hybrid-web` plugin before VPS cutover
- Slightly longer migration (~30 min extra for the merge)

**Risk:** Low — we're building on what already works.

---

### Path 2: "Pure hermes-agent" — Migrate my work to VPS as-is, build everything fresh

**What it is:** Take hermes-agent exactly as it is, migrate to VPS, set up everything from scratch on the VPS. Don't use rebuild-second at all.

**Steps:**
1. Stop both local gateways (hermes-agent was never running, hermes-rebuild-second is running — stop the latter)
2. SCP all hermes-agent files to VPS
3. Apply fix_models.py (already 12/12 green)
4. Add 4GB swap, disable STT
5. Pair WhatsApp (fresh scan)
6. Start gateway (first time ever)
7. Test end-to-end

**Pros:**
- Single coherent source
- All my decisions intact (timezone, vision on mimo-v2.5-free, etc.)
- No merge work

**Cons:**
- **Gateway has never launched** — unknown how stable it will be on first start
- No watchdog currently configured → restart on crash is manual
- Need to fix 2 latent bugs (hybrid-web, no gateway timeouts) before first start
- Higher risk: untested deployment going onto a fresh VPS
- 28 cron jobs scheduled but never ticked before — possible scheduling bugs

**Risk:** Medium-High — first-time deployment of an untested config onto a real VPS.

---

### Path 3: "Pure hermes-rebuild-second" — Migrate the working distro to VPS, add my hardening

**What it is:** Take hermes-rebuild-second (already running) as-is, migrate to VPS, then add my 2 hardening wins (opencode-go skip-guard + NVIDIA override list). Don't keep the auxiliary config in hermes-agent.

**Steps:**
1. Stop hermes-rebuild-second gateway
2. SCP rebuild-second files to VPS
3. Add 4GB swap, disable STT (or keep default — rebuild-second may already be configured)
4. Apply 2 fix_models wins to bring it to 12/12 green
5. Fix hybrid-web plugin bug
6. Pair WhatsApp (fresh scan — session was local)
7. Start gateway (now has all production hardening)
8. Test end-to-end

**Pros:**
- Runtime-tested base (already proven)
- Hardening applied (12/12 green)
- 14 aux blocks (vs my 4) come along — more features

**Cons:**
- Timezone empty (not `Asia/Kuala_Lumpur`) — must be set
- Vision on `nvidia/minimax-m3` (vs my `opencode-zen/mimo-v2.5-free`) — must change if user wants mimo
- base_url is `None` (vs my explicit `https://opencode.ai/zen/v1`) — must set
- Reasoning effort is `xhigh` (tie) but idle is 240 (tie) — only the above 3 need config edits
- 1 file deleted in plugin-tree (gemini) — git tree dirty

**Risk:** Low — working base, additive changes only.

---

## My Recommendation

**Path 1 (Best of Both) — MERGE.** `[User-confirmed 07-01.]` Reasons:

1. ~~**It's the lowest-risk path to a working VPS.** The hard part of any deployment is the gateway actually running. rebuild-second has proven it runs (3 watchdog restarts today, 2 platforms connected, cron ticker alive). Starting fresh with hermes-agent on a fresh VPS is asking for problems.~~ `[CORRECTED 07-01: this reasoning was built on B.5, which is false. rebuild-second's gateway has NOT proven stable — it crash-loops 11+×, WhatsApp is broken, cron jobs all fail. Revised reason below.]`
2. **Revised reason 1:** rebuild-second still carries real *structural* value that hermes-agent lacks and that is expensive to rebuild by hand — the 15 auxiliary blocks, populated `platforms/` + `channel_directory.json`, the richer SOUL/MEMORY/USER persona, and the 28 cron job *definitions*. These are config/data, not runtime behavior, so their value survives even though the runtime was broken.
3. **Revised reason 2:** hermes-agent carries the *correctness* wins — `_config_version: 32` + 2 `.bak` safety files, `setup-cron.sh`, the `opencode-go` skip-live-fetch guard + updated opencode-go model list, `Asia/Kuala_Lumpur` timezone, `mimo-v2.5-free` vision, explicit opencode base_urls. These are surgical to merge.
4. **The hybrid-web bug is already in both distros** — must be fixed regardless of path chosen.
5. **Single coherent source at the end.** No future "which one was that" confusion.

`[CORRECTED 07-01 — the merge is NO LONGER "inherit a working gateway." It is "take the better config+data skeleton, then FIX the gateway from scratch as part of the merge": install aiohttp, set user allowlists, pin all 28 cron jobs, patch hybrid-web, set base_urls per OpenCode docs, remove gemini/google.]`

---

## Pre-Migration Tasks (for ALL paths)

These must happen before going to VPS, regardless of which path:

1. **Fix `hybrid-web` plugin register signature** (latent bug in both distros)
2. **Document the upstream commit SHA** each source was built against (`41c85fb` agent / `184c10c` rebuild-second — confirmed 07-01)
3. **Backup current state** before any merge
4. **Set timezone = `Asia/Kuala_Lumpur`** (rebuild-second has empty — confirmed 07-01)
5. **Decide: STT local vs cloud on VPS** — `[User decision 07-01: STT permanently OFF. Not used.]`
6. **Add 4GB swap** on VPS (Tencent ships with 2GB swap only)
7. **Stop local `hermes-rebuild-second` gateway** before starting VPS gateway (TG 409 conflict)
8. `[ADDED 07-01]` **Install `aiohttp`** in the VPS Python env — WhatsApp bridge hard-fails without it.
9. `[ADDED 07-01]` **Set user allowlists** — `TELEGRAM_ALLOWED_USERS=<user_id>` (and/or `GATEWAY_ALLOW_ALL_USERS`) in `.env`, else the bot denies every message.
10. `[ADDED 07-01]` **Pin all 28 cron jobs** to an explicit `(provider, model)` so the inference-drift guard stops aborting them. Decide target provider/model per job (most should follow the default model).
11. `[ADDED 07-01]` **Permanently remove gemini/google** — delete `_gemini/` plugin dir, remove `gemini:` block (line ~364) + `google_chat` ref (line ~689) from `config.yaml`. `[User decision 07-01: never using Gemini again.]`
12. `[ADDED 07-01]` **Fetch OpenCode docs and set correct base_urls** for the two-key setup (zen = free models, go = specific paid models). Currently every `base_url` is `''` on rebuild-second. Do NOT guess — read the docs first. `[User decision 07-01.]`

---

## What I Need From You

1. **Pick a path** (1, 2, or 3) — or propose your own modification
2. **Confirm pre-migration tasks** I'm right about
3. **Authorize the next step** — write the formal implementation plan (`superpowers:writing-plans` skill), then ExitPlanMode for approval, then execute

If you pick Path 1, I will also need your approval to do a small "fix the plugin bug" task on hermes-rebuild-second before migrating.

---

## VERIFICATION ADDENDUM (2026-07-01 01:30 MYT)

A full read-only audit was run against both live WSL2 distros (`hermes-agent`, `hermes-rebuild-second`) plus the local Windows repo at `F:\AI Prep\OVIS\Hermes Agent\MJay\`. Every numerical and structural claim above was re-checked. The original audit text is preserved inline; this addendum is the consolidated record.

### What was verified — exact match

| Claim | Verified evidence |
|---|---|
| A.2 hermes-agent customization | `git diff --stat`: 30 insertions, 64 deletions on `models.py` + `+3` on `inventory.py` |
| A.2 rebuild-second customization | `15 insertions, 122 deletions`; `D plugins/.../gemini/__init__.py + plugin.yaml`; `?? plugins/model-providers/_gemini/` |
| A.3 scripts | hermes-agent: 10 incl `setup-cron.sh`; rebuild-second: 9 missing it |
| A.4 agent config | `_config_version: 32`; `config.yaml.bak.20260630_130500` + `config.yaml.bak.unnamed` |
| A.5 plugin tree | agent: 28 dirs, no `_`-prefixed; rebuild: gemini gone, `_gemini/` present (2275B + 136B) |
| B.1 agent lacks platforms/ | `platforms/`, `channel_directory.json` absent at `~/.hermes/` on hermes-agent |
| B.1 rebuild has them | both present at `~/.hermes/` on rebuild-second |
| B.2 opencode-go skip-guard | agent: 6 MJ-override guards incl `opencode-go`; rebuild: 4 guards, **missing `opencode-go`** ✓ spec was right |
| B.2 opencode-go curated list | rebuild's `opencode-go` block has older models (k2.6, k2.5, glm-5.1, mimo, minimax, qwen) — no v4-pro/k2.7-code/glm-5.2 |
| B.4 aux keys count | agent: `[curator, vision, web_extract, compression]` = 4 ✓; rebuild: 15 keys |
| B.5 agent logs gap | only `agent.log` (16KB) + `errors.log` (2.7KB) with exactly 5 hybrid-web hits; no gateway.log |
| B.5 rebuild config timeouts | `gateway_timeout: 1800`, `restart_drain_timeout: 180`, `gateway_timeout_warning: 900` ✓ |
| Cross-cutting 1 | `hybrid-web register()` errors confirmed in both errors.log |
| Cross-cutting 2 | git SHAs: `41c85fb9469bbde7c5446cc5386b2e2438936fb5` (agent) vs `184c10cf97002c95b233830d62d6fb355a82708a` (rebuild) ✓ |
| Cross-cutting 3 | `WHATSAPP_MODE` var name present in both `.env` (value not inspected) |
| D4 timezone | agent: `Asia/Kuala_Lumpur`; rebuild: `''` (empty) |
| D4 vision (agent) | `vision.model: mimo-v2.5-free`, `base_url: https://opencode.ai/zen/v1` |
| D4 gemini footprint | `_gemini/` plugin dir + `gemini:` config block (line 364) + `google_chat` ref (line 689); no GEMINI/GOOGLE env vars set |
| D5 project age | first commit 2026-06-24; 41 commits total; both distros freshly cloned Jun 30 |
| D5 persona richer on rebuild | `SOUL.md` 3672B, `memories/MEMORY.md` 2523B, `memories/USER.md` 1331B (agent's were 0 bytes) |
| D5 Windows docs | `FINDINGS-analysis.md`, `Hermes-MJ-VISION.md`, `PRD.md`, `PRD-bysakana.md`, `PRD-1.md` exist in `F:\AI Prep\OVIS\Hermes Agent\` |
| New: rebuild `_config_version` | `31` ✓ spec was right |
| New: jobs.json count | exactly **28 jobs** confirmed (Morning Briefing, Evening Check-in, 5× Medication + 15 Follow-ups, etc.) |
| New: rebuild watchdog.log | 11+ crash-recovery events, every one is a "down" or "stale" → restart |

### What was WRONG in the original audit (corrections applied inline above)

1. **A.1 "35 entries"** — actual is **71** top-level entries on both. Counting-method mismatch; shape claim ("identical") still holds.
2. **B.5 "watchdog has restarted it 3× today"** — actually **11+ events**, all crash-recoveries, not health-checks.
3. **B.5 "2 platforms connected"** — only **Telegram** connects; WhatsApp fails every boot with `ModuleNotFoundError: No module named 'aiohttp'`.
4. **B.5 "Gateway actively running"** — masked crash-loop. The gateway goes down or stale every 30-60 min and the watchdog revives it. gateway.log grew from 35KB → 51KB during the audit window.
5. **B.3 "28 active jobs" liveness = positive** — scheduler is alive but **all 28 jobs fail** on every run with `RuntimeError: Skipped to prevent unintended spend: global inference config drifted … job is unpinned`. 11 tracebacks in errors.log.
6. **B.5 "✓ whatsapp connected"** — never happened. The WhatsApp bridge binary is missing its `aiohttp` dependency.
7. **Path documentation defect** — multiple artifacts implied to be at `~/.hermes/hermes-agent/` actually live at `~/.hermes/`. Conclusions unaffected; paths corrected in the fix.

### What could NOT be verified (honest gaps)

- The full "28 jobs" semantic correctness — names confirmed; whether each job's `(provider, model)` was the *intended* pair requires cross-referencing your original setup intent, which lives only in your head + the pre-destruction git history (no longer available). **Easily pinned by your call once the merge starts.**
- VPS state — everything about the Tencent VPS (2vCPU/2GB, Hermes pre-installed, swap size) is taken on trust from the spec; no SSH access verified in this turn.
- `WHATSAPP_MODE` value (env var name confirmed; value not inspected per secrets policy).

### D7 + D8 — strategic answers

**D7 — Cross-device GitHub sync workflow (the professional standard for your situation):**
- `F:\AI Prep\OVIS\Hermes Agent\MJay\` is the single source of truth for **docs, scripts, and config templates**. Git-tracked.
- `~/.hermes/` on the VPS is the **runtime** — contains secrets, sessions, live state. NOT git-tracked.
- Flow: changes made on VPS → diff back into `MJay/scripts/` or `MJay/docs/` → commit + push from PC (or via SSH on the VPS). The MJay repo holds the *recipes*; the VPS holds the *running kitchen*.
- After moving to VPS, you work with me by opening this ZCode session on your PC (where the git repo lives) — I SSH into the VPS to apply changes, we commit the resulting config/script updates back to MJay. Your phone handles Hermes *as a user* (Telegram/WhatsApp); your PC handles *Hermes administration* via me.

**D8 — Phone-only operation after VPS is live:**
- **Yes.** The gateway running 24/7 on the VPS is the whole point. You message MJ via Telegram (and WhatsApp once `aiohttp` is installed) from your phone → it responds using the LLM.
- You do NOT need your PC for daily Hermes use. The PC is only for *admin / deploy / commits*.
- **Tonight's critical path to make that real:** get ONE platform (Telegram) actually stable on the VPS, with the 28 cron jobs pinned so they stop failing. WhatsApp is a fast-follow once `aiohttp` is installed.

### User decisions captured 2026-07-01

- **D1** (gateway comparison trap): acknowledged — don't compare "tested" vs "untested" gateway; rebuild-second's gateway has its own problems, and it is not the same as the pre-destruction original.
- **D2** (base): **Merge** (Path 1, corrected).
- **D3** (this doc): **fix definitely now** — done in this turn.
- **D4** (config): keep KL timezone; vision = `opencode-zen/mimo-v2.5-free` (or user chooses via `/model` at runtime); read OpenCode docs for correct two-key base_urls; STT permanently off; **permanently remove gemini/google**.
- **D5** (archaeology): pre-destruction session history is **not recoverable** (no backups, no other WSL distros). Best-practices source = the richer `SOUL.md`/`MEMORY.md`/`USER.md` on rebuild-second + the Windows docs (`FINDINGS-analysis.md`, `Hermes-MJ-VISION.md`, `PRD*.md`).
- **D6**: A.
- **D7** (workflow): see D7 section above.
- **D8** (phone-only): see D8 section above.

### Tonight-vs-tomorrow honest scoping

Given gateway is crash-looping, "fully live on VPS tonight" is **not realistic**. "Set up tomorrow to be easy" IS realistic tonight.

**Tonight (must-do, ~1 hr):** ~~fetch OpenCode docs for base_urls~~ deferred to tomorrow (needs careful doc reading); ~~write corrected spec doc + full implementation plan~~ spec doc corrections are complete in this turn; implementation plan to be written tomorrow. **All execution deferred.**

**Tomorrow (execution):** build the clean merged source on the local Windows repo; fix `aiohttp`, `hybrid-web`, pin the 28 cron jobs, remove gemini, set base_urls per OpenCode docs, set user allowlists; migrate to VPS; pair WhatsApp fresh; bring Telegram up stable; first phone-only test.

---

*End of decision document with verification addendum. Saved to `docs/superpowers/specs/2026-06-30-dual-rebuild-audit-decision.md`.*
