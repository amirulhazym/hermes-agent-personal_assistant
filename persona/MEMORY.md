Obsidian vault: F:\obsidian-vault\ (WSL: /mnt/f/obsidian-vault/). PARA system — 2-areas/Personal/ has profile, health, goals.
§
Medical reminders: Boss wants me to be SERIOUS about medication timing. Set up daily cron reminders for wajib meds. Research, record daily logs, track compliance. Default: serious/proactive mode for medical matters.
§
User calls me MJ or Jane. When I refer to myself, use "Jane", not "MJ" or "MJ".
§
User wants me to track his food intake/diet patterns too (not just medication). He's trying to lose weight (60kg target 53kg). I should alert him about unbalanced eating patterns gently.
§
User's morning routine: solat sunat subuh, solat fardhu subuh, baca Yassin & Al-Waqiah after taking Akurit-4 (around 6:15am)
§
Full-screen screenshot on Windows: use PowerShell System.Drawing CopyFromScreen, not cua-driver window capture.
§
Cron wrap_response & config changes need gateway restart from external terminal (can't restart from inside gateway process).
§
DeepSeek billing: when user asks, always show ¥ original amount + live converted RM & USD rates side by side
§
Custom model list overrides in hermes_cli/models.py (applied 2026-06-27):
  - NVIDIA: only 5 models (minimaxai/minimax-m3, moonshotai/kimi-k2.6, deepseek-ai/deepseek-v4-flash, deepseek-ai/deepseek-v4-pro, z-ai/glm-5.1). Live API fetch is SKIPPED for NVIDIA.
  - OpenCode Zen: only free models (deepseek-v4-flash-free, minimax-m3-free, mimo-v2.5-free, qwen3.6-plus-free, nemotron-3-ultra-free, north-mini-code-free).
  - Gemini provider: REMOVED from CANONICAL_PROVIDERS and PROVIDER_GROUPS.
  - After `hermes update`, these changes will be overwritten. Re-apply from this note or run ~/.hermes/scripts/fix-models.sh.
§
Skills: sakana (automation/sakana) = /sakana via Brave → chat.sakana.ai. qwen (automation/qwen) = /qwen via Brave → chat.qwen.ai. Both use cua-driver for browser automation — navigate, inject prompt, extract response. Qwen has + menu for Deep Research, Create Image, Web Dev, Slides etc.
§
2026-06-27 maintenance:
  - Watchdog.sh: fixed CRLF line endings (was silently broken). Now runs clean.
  - Web extract: changed config.yaml web.extract_backend to 'trafilatura' with custom Hermes plugin at ~/.hermes/plugins/trafilatura/. Free, no API key needed. FIRECRAWL_API_KEY kept in .env as fallback placeholder.
§
Reminder rules: NEVER first-person. Always ask USER directly. No ✅. Let user confirm, not me. Follow-up ONLY when user hasn't replied at all. If user replied, no more nudges.