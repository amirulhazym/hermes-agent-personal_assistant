# GMI Cloud Provider (live-tested 2026-08-25)

Verified working setup notes. Config-only path (no plugin needed).

## Facts (probed live with real key)

- Base URL: `https://api.gmi-serving.com/v1` (OpenAI-compatible: `/models`, `/chat/completions`)
- Keys are JWT-style (`eyJ...`, ~252 chars, scope `ie_model`, product `IE`), created in console.gmicloud.ai
- Model IDs are HuggingFace-shaped: e.g. `MiniMaxAI/MiniMax-M3`, `deepseek-ai/DeepSeek-V3.2`, `anthropic/claude-opus-4.5`
- `/v1/models` returned 76 models on 2026-08-25; MiniMax present: `MiniMaxAI/MiniMax-M3`, `MiniMaxAI/MiniMax-M2.7`, `MiniMaxAI/MiniMax-M2.5`
- Promo (single source, GMI X post 2026-08-22): MiniMax M3 + M2.7 free 8/24–9/6 "unlimited" — single-source, unverified billing-side

## Setup recipe (config-only)

```bash
hermes config set providers.gmi.name "GMI Cloud"
hermes config set providers.gmi.base_url "https://api.gmi-serving.com/v1"
hermes config set providers.gmi.key_env "GMI_API_KEY"   # canonical key_env, NOT api_key_env alias
hermes config set providers.gmi.default_model "MiniMaxAI/MiniMax-M3"
hermes config set providers.gmi.discover_models true
# key value goes in ~/.hermes/.env as GMI_API_KEY=...
```

Verification chain used (all passed):
1. `GET /v1/models` with Bearer key → HTTP 200, 76 models
2. Minimal `POST /chat/completions` max_tokens=10 on M3 → HTTP 200, reply ok
3. `resolve_provider_full("gmi", user_providers, None)` → `api_key_env_vars=('GMI_API_KEY',)`
4. `list_picker_providers(user_providers=...)` → gmi row, 76 models incl. all 3 MiniMax

## Short aliases (live-tested 2026-08-25)

`hermes config set` warns "not a recognized config key, did you mean model_catalog" for `model_aliases.*` — VERIFIED NOISE. Runtime truth: `model_aliases` is explicitly read by `_load_direct_aliases()` (model_switch.py ~line 402); `model_catalog` has ZERO runtime readers (schema-only open-dict key). End-to-end proven in fresh process:

```yaml
model_aliases:
  m3:      {model: MiniMaxAI/MiniMax-M3,   provider: gmi, base_url: https://api.gmi-serving.com/v1}
  m27:     {model: MiniMaxAI/MiniMax-M2.7, provider: gmi, base_url: https://api.gmi-serving.com/v1}
```

Then plain `/model m3` works (direct aliases are checked BEFORE catalog resolution). `switch_model('m3')` returned success with api_key auto-populated from env.

## Gotchas

- Picker row may show `source: hermes, is_user_defined: false` (built-in models.dev catalog knows GMI) even when added via user config — resolution still goes through user-config first; both paths checked OK.
- M2.7 is a reasoning model: tiny max_tokens budgets get consumed by thinking, content may be null with completion_tokens>0.
- urllib probes need a browser User-Agent (same class of issue as other Cloudflare-fronted providers).
- `md2ops.py` writes ops JSON to STDOUT — capture with `> ops.json` (shell) or subprocess stdout; it does NOT write the file itself. `ops.json` is single-line; check size with byte count, not line count.
- When authoring doc.md via multiple small write_file calls (stream-timeout guard), keep part filenames lexicographically ordered (`doc_part2.md`, `doc_part3.md`...) and merge with sorted(glob) before md2ops.
- gdocs pipeline artifacts for this session live under ~/.hermes/tmp/gdocs/<timestamp>/ (doc.md + ops.json + manifest.json).
