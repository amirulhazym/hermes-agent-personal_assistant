# PX-1b Live Contracts

> **Date:** 2026-07-17  
> **Branch:** `overhaul/exec` (feature worktree abandoned per human choice)  
> **Scope:** Phase 0 read-only inventory + official docs refresh  
> **Labels:** VALIDATED / UNTESTED / REJECTED  
> **Secrets policy:** names/paths/fingerprints only — no secret values

## Runtime Identity

| Item | Observed | Label | Implication |
|---|---|---|---|
| Live Hermes CLI version | `Hermes Agent v0.17.0 (2026.6.19)` via `python -m hermes_cli.main --version` | VALIDATED | Keep live version. Do not upgrade silently. Official docs may describe newer unreleased behavior. |
| Upstream report | CLI says `upstream d0dcb9a5`, `3738 commits behind` | VALIDATED | Docs on website can be newer than installed runtime. |
| Git describe | `v2026.6.19-dirty` | VALIDATED | Local dirty tree on VPS; local patches exist. |
| Git HEAD | `2bd1977d8fad185c9b4be47884f7e87f1add0ce3` | VALIDATED | Pin adapters against this tree unless Phase 0 is re-run. |
| Gateway unit | `systemctl --user is-active hermes-gateway` → `active` | VALIDATED | Production gateway is live. |
| Gateway ExecStart | `/home/ubuntu/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main gateway run` | VALIDATED | Use venv python entrypoint; bare `hermes` not on PATH. |
| Host Python (system) | 3.12.3 | VALIDATED | System python differs from hermes venv. |
| Hermes venv Python | 3.11.15 | VALIDATED | Prefer venv for imports/tests against Hermes APIs. |
| Node | v22.23.1 | VALIDATED | WhatsApp bridge / agent-browser stack possible. |
| Config version | `_config_version: 31` | VALIDATED | Schema is v31-era. |
| Default model | `opencode-go` / `deepseek-v4-flash` | VALIDATED | Cost path is free/paid mix; no model change in Phase 0. |
| Fallback | `opencode-zen` | VALIDATED | Present. |
| Timezone | `Asia/Kuala_Lumpur` | VALIDATED | Matches PRD default. |

## Native Browser Adapter Contract

| Item | Observed | Label | Implication |
|---|---|---|---|
| Source | `~/.hermes/hermes-agent/tools/browser_tool.py` | VALIDATED | Sole L3 integration target. |
| Public tools | `browser_navigate(url, task_id)`, `browser_snapshot(full, task_id, user_task)`, `browser_click(ref, task_id)`, `browser_type(ref, text, task_id)`, `browser_scroll(direction, task_id)`, `browser_back(task_id)`, `browser_press(key, task_id)`, `browser_console(clear, expression, task_id)`, `browser_get_images(task_id)`, `browser_vision(question, annotate, task_id)` | VALIDATED | Map operator steps to these names exactly. |
| Cleanup | `cleanup_browser(task_id)`, `cleanup_all_browsers()` | VALIDATED | Cancel/timeout must call cleanup. |
| SSRF helper | `_url_is_private(url)`, `_allow_private_urls()` | VALIDATED | Live browser already has private URL checks. |
| Config browser | `engine: auto`, `allow_private_urls: false`, `auto_local_for_private_urls: true`, `record_sessions: false`, `inactivity_timeout: 120`, `command_timeout: 30`, `dialog_policy: must_respond`, `dialog_timeout_s: 300` | VALIDATED | Private destinations denied. Recording off. |
| Camofox | configured keys present; `managed_persistence: false`; empty `user_id` | VALIDATED | Not productized as persistent session vault. |
| CDP tool | `tools/browser_cdp_tool.py` → `browser_cdp(method, params, target_id, frame_id, timeout, task_id)` | VALIDATED | Only when CDP endpoint exists. |
| Dialog tool | `tools/browser_dialog_tool.py` → `browser_dialog(action, prompt_text, dialog_id, task_id)` | VALIDATED | Needs CDP supervisor path. |
| Supervisor | `tools/browser_supervisor.py` `CDPSupervisor` | VALIDATED | Dialog/frame/console supervision. |
| Native downloads | Official docs + live tool surface: no download/upload tools | VALIDATED | Project-owned file adapter required. |
| `/browser connect` | CLI-only per official docs; not gateway/Telegram | VALIDATED | Cannot rely on chat `/browser connect` for phone-first. |
| Playwright package | venv import True | VALIDATED | Available for extract fallback and possible adapter support. |
| browser-use package | venv import False | VALIDATED | Not installed; not primary path. |

## Research/Extract Adapter Contract

| Item | Observed | Label | Implication |
|---|---|---|---|
| Search backend config | `web.backend: tavily`, `web.search_backend: search-cascade` | VALIDATED | Compose, do not rebuild. |
| Extract backend config | `web.extract_backend: hybrid-web` | VALIDATED | Compose, do not rebuild. |
| search-cascade | `~/.hermes/plugins/search-cascade/provider.py` class `SearchCascadeProvider` with `search(self, query, limit)` | VALIDATED | Tavily multi-key + DDGS fallback. |
| hybrid-web | `~/.hermes/plugins/hybrid-web/provider.py` class `HybridWebSearchProvider` with `extract(self, urls)` | VALIDATED | trafilatura → crawl4ai/JS → Playwright. |
| Plugin register | both plugins `register(ctx)` | VALIDATED | User plugin registration works. |
| web_tools API | `tools/web_tools.py` `web_search_tool(query, limit)`, `web_extract_tool(urls, format, use_llm_processing, model, min_length)` | VALIDATED | Preferred call surface for L2 adapter. |
| Research Expert skill | `~/.hermes/skills/experts/research-expert/` present | VALIDATED | PX-1 skill deployed. |
| Research artifacts | dirs under `~/.hermes/research/artifacts/` including 2026-07-14 E2E samples | VALIDATED | Artifact path exists. |
| Research trace | `~/.hermes/logs/research_trace.jsonl` size 5231 bytes | VALIDATED | Trace logging present. |
| skill-trigger research patterns | `research`, `investigat(e|ion)`, `literature scan`, `fact-check`, `cited sources`, `deep research`, `compare options/vendors/...`, `due diligence` → `research-expert` | VALIDATED | Chat trigger for research exists. |
| Telegram Research E2E (this Phase 0) | Owner inbound DM 2026-07-17 | PARTIAL | Response received; skill-trigger wrote `research-expert`; Tavily search + hybrid-web extract used. Formal `research_trace.jsonl` append and standard `research/artifacts/YYYY-MM-DD-*` package did **not** fire; agent wrote `~/.hermes/research-hermes-browser-automation.md` instead. |

## Trigger and /browse Contract

| Item | Observed | Label | Implication |
|---|---|---|---|
| skill-trigger hook | `~/.hermes/hooks/skill-trigger/HOOK.yaml` event `agent:start` | VALIDATED | Fail-open design. |
| Handler | `handle(event_type, context)` reads `context["message"]`, writes `~/.hermes/triggered_skills.txt` | VALIDATED | Web-operator can be added as new patterns later. |
| Med patterns | present and must not be disturbed | VALIDATED | No med path edits. |
| Slash commands | `gateway/slash_commands.py` has many handlers; no native `/browse` found in inspected mixin methods | VALIDATED | `/browse` may need skill-trigger phrase or future command registration discovery. |
| quick_commands | `billing`, `qwen`, `restart`, `sakana` exec commands | VALIDATED | Historical CUA scripts still registered as exec quick commands. |
| Platform toolsets | telegram/whatsapp present in config | VALIDATED | Messaging surfaces available. |

## Gateway Control-Plane Contract

| Item | Observed | Label | Implication |
|---|---|---|---|
| Gateway active | yes | VALIDATED | Do not restart without explicit approval. |
| CLI send | `hermes send --to telegram "..."` exists | VALIDATED | Outbound-only; cannot synthesize inbound owner Research E2E. |
| CLI oneshot | `hermes -z "..."` exists | VALIDATED | Local agent loop, not messaging route. |
| Approvals | `approvals.mode: manual`, timeout 60 | VALIDATED | Dangerous shell approvals manual. |
| Security | `security.allow_private_urls: false`, tirith enabled | VALIDATED | Aligns with PX-1b private-destination deny. |
| MCP servers | `tavily` remote MCP URL via env var | VALIDATED | No live `cua-driver` MCP entry in config dump. |
| computer_use.enabled | `true` | VALIDATED | Flag true, but no MCP cua-driver path in live config → capability honesty issue. |
| Delegation limits | `max_spawn_depth: 1`, `max_concurrent_children: 3` | VALIDATED | Matches hard depth/max rule. |
| Dirty source tree | many modified/deleted files under `~/.hermes/hermes-agent` | VALIDATED | Adapters must not assume clean upstream checkout. |

## CUA Driver Contract

| Item | Observed | Label | Implication |
|---|---|---|---|
| Primary binary | `C:\Users\amiru\AppData\Local\Programs\Cua\cua-driver\bin\cua-driver.exe` version `0.7.1` | VALIDATED | Use this, not stale F:\ path alone. |
| Historical binary | `F:\hermes\cua-driver\cua-driver.exe` present (older) | VALIDATED | Keep as historical reference only. |
| MCP invocation | `cua-driver mcp` | VALIDATED | Stdio MCP child pattern. |
| Daemon | `status` → not running; autostart `not-registered` | VALIDATED | Need explicit start/enroll design for worker. |
| Doctor | binary ok; interactive session warn `OpenWindowStationW Access denied` in some contexts | VALIDATED | Session/desktop availability must be checked before CUA grants. |
| Tools (list-tools) | includes `list_apps`, `list_windows`, `click`, `type_text`, `page`, `get_window_state`, `start_session`, `end_session`, recording tools, etc. | VALIDATED | Map named-app grants onto these tools. |
| Brave | installed and multiple processes running | VALIDATED | Desktop browser available for CUA/browser hybrid. |
| Chrome/Edge | installed | VALIDATED | Available. |
| Local Hermes CLI | not on Windows PATH | VALIDATED | VPS is the Hermes host. |

## Dependency Inventory

| Package/tool | VPS Hermes venv | Label |
|---|---|---|
| PyYAML | True | VALIDATED |
| cryptography | True | VALIDATED |
| pytest | True | VALIDATED |
| playwright | True | VALIDATED |
| browser_use | False | VALIDATED |
| tirith | configured path `tirith` | UNTESTED binary presence |
| agent-browser | not verified in this pass | UNTESTED |

## Filesystem and Service Account

| Item | Observed | Label |
|---|---|---|
| Hermes home | `/home/ubuntu/.hermes` | VALIDATED |
| Service user | systemd user service under `ubuntu` | VALIDATED |
| Disk `/` | 40G total, ~24G used, ~15G free (62%) | VALIDATED |
| Scripts path | `/home/ubuntu/.hermes/scripts/` used by quick_commands | VALIDATED |
| Worktree Git ownership | F: worktree needs command-local `safe.directory` | VALIDATED |

## Resource Baseline

| Metric | Value | Label | Implication |
|---|---|---|---|
| RAM total | 1967 MiB | VALIDATED | Tight for concurrent Chromium. |
| RAM available (sample) | ~1082 MiB | VALIDATED | Start concurrency benchmark at 1. |
| Swap total | 6083 MiB | VALIDATED | Safety net only. |
| Swap used (sample) | ~302 MiB | VALIDATED | Already some pressure. |
| Gateway + platforms | active while inventory ran | VALIDATED | Browser jobs must not starve gateway. |

## Supported / Missing / Rejected Matrix

| Capability | Status | Notes |
|---|---|---|
| L1 HTTP compose | SUPPORTED foundation | Need project adapter. |
| L2 search/extract | SUPPORTED live | search-cascade + hybrid-web. |
| L3 native browser tools | SUPPORTED live API | browser_* functions present. |
| L3 browser-use library | MISSING | Not installed; not required for native-first. |
| Native browser download/upload | MISSING | Project adapter required. |
| Phone-first private takeover | MISSING | Not native; design required. |
| Secure VPS↔PC CUA bridge | MISSING | CUA local only today; no enrolled outbound worker. |
| computer_use.enabled honesty | INCONSISTENT | Flag true without live MCP cua path. |
| Account farming/captcha ops | REJECTED as product | Stay PC ops / L5 human. |
| Paid browser cloud | REJECTED without explicit paid yes | Do not enable. |
| Hermes upgrade to latest docs | REJECTED for now | Keep live 0.17.0. |
| Telegram Research E2E this session | PARTIAL | Chat tools + trigger VALIDATED; formal Research Expert package/trace residual UNTESTED. |

## Adapter Decisions

1. **L3 primary:** native Hermes `browser_*` tools in live v0.17.0 tree.  
2. **L2:** call `web_search_tool` / `web_extract_tool` and/or existing backends; never reimplement cascade/hybrid.  
3. **Files:** project-owned two-stage quarantine; native browser has no download tool.  
4. **CUA:** Windows worker wraps `cua-driver 0.7.1` MCP/tool surface; do not depend on F:\ historical path.  
5. **Triggers:** extend `skill-trigger` only after Phase 1 skill exists; preserve med patterns untouched.  
6. **Config honesty:** before acceptance, either wire real CUA MCP or set `computer_use.enabled` false when bridge offline.  
7. **Telegram E2E gate:** remains open until owner sends the approved research DM and sanitized evidence is recorded.

## Official Docs Refresh (2026-07-17)

Checked:

- Browser automation docs
- Computer Use docs
- MCP docs
- Security docs
- Messaging gateway docs
- GitHub releases (latest tag still `v0.18.2` / `v2026.7.7.2`, newer than live install)

Key doc vs live deltas:

- Docs describe post-0.17 browser/CDP/dialog behavior; live has corresponding modules present in dirty tree.
- Latest release is 0.18.2; live remains 0.17.0 by policy.
- `/browser connect` remains CLI-only.
- No browser downloads in docs limitations.

## Phase 0 Gate Status

| Gate | Status |
|---|---|
| Official docs refresh | DONE |
| Read-only VPS inventory | DONE |
| Read-only PC/CUA inventory | DONE |
| Generated worktree cache cleanup | DONE |
| Telegram Research Expert E2E | **PARTIAL PASS** (see evidence table) |
| Live contracts ledger | THIS FILE |
| Phase 0 closed | YES — residual formal pipeline accepted for PX-1b compose path |

## Telegram E2E Evidence (sanitized, 2026-07-17)

| Check | Evidence | Label |
|---|---|---|
| Telegram response | Owner received multi-tool research reply from MJ | VALIDATED |
| Research Expert trigger | `~/.hermes/triggered_skills.txt` contains `research-expert` (mtime ~14:25 CST) | VALIDATED |
| Search backend | `tavily_key_usage.jsonl` last success `2026-07-17T06:28:23Z` key_index=0 fingerprint `d8158fdc356b`; chat used multiple `web_search` | VALIDATED |
| Extract backend | gateway logs hybrid-web Trafilatura + Crawl4AI/Playwright on official docs/GitHub URLs during run | VALIDATED |
| Formal research_trace.jsonl | No new entry after 2026-07-14; still 5231 bytes / 6 lines | UNTESTED for chat path |
| Standard artifact package | No new dir under `~/.hermes/research/artifacts/` for this run | UNTESTED for chat path |
| Alternate artifact | `~/.hermes/research-hermes-browser-automation.md` 10691 bytes written 14:29 | VALIDATED alternate path |

### Residual for later (not Phase 0 hard block for PX-1b tool composition)

Chat research currently uses tools + skill-trigger, but does not reliably execute the full Research Expert staged pipeline that writes `research_trace.jsonl` and `research/artifacts/YYYY-MM-DD-<slug>/`. PX-1b must not assume that formal package path is already live for every research phrasing. Optional PX-1 repair can be a separate narrow task if desired.
