# Hybrid-Web Plugin

> Custom Hermes plugin that intelligently routes web extraction requests to the optimal backend based on page type.
>
> **This document is for AI coding agents** updating this repo.
> **Maintenance:** Plugin lives at `~/.hermes/plugins/hybrid-web/`.

---

## Overview

The hybrid-web plugin solves a fundamental problem: **no single extraction backend works well for all websites**.

- **Static HTML pages** (blogs, docs, Wikipedia) → Fast, lightweight extraction via Trafilatura
- **JavaScript-heavy SPAs** (React, Next.js, Angular apps) → Headless browser rendering via Crawl4AI

Previously, choosing between these backends required manual configuration or accepting suboptimal results. Hybrid-web **automatically detects** page characteristics and routes to the best backend.

## Architecture

```
User Request (URL)
       │
       ▼
┌─────────────────┐
│  hybrid-web      │
│  Plugin          │
│                  │
│  1. Fetch headers│
│  2. Detect JS    │
│  3. Route:       │
│     ├─ Static → Trafilatura (fast, lightweight)
│     └─ Dynamic → Crawl4AI (headless browser)
└─────────────────┘
```

### Detection Logic

The plugin uses multiple signals to determine page type:

1. **Content-Type header** — `text/html` vs `application/json`
2. **HTML analysis** — presence of React/Next.js/Angular markers
3. **Script tags** — heavy JS bundles indicate SPA
4. **Meta tags** — `__NEXT_DATA__`, `__NUXT__`, framework-specific markers

## Configuration

### Plugin Installation

Plugin directory: `~/.hermes/plugins/hybrid-web/`

```
~/.hermes/plugins/hybrid-web/
├── __init__.py      # Plugin registration
├── provider.py      # HybridWebSearchProvider implementation
└── plugin.yaml      # Plugin metadata
```

### Config Settings

In `~/.hermes/config.yaml`:

```yaml
web:
  extract_backend: hybrid-web    # Use hybrid-web for extraction
  backend: ddgs                  # Default search backend (unchanged)

plugins:
  enabled:
    - hybrid-web                 # Enable the plugin
```

### Backend Timeouts

- **Trafilatura**: 10 seconds (static pages are fast)
- **Crawl4AI**: 45 seconds (JS rendering takes longer)

## Usage

### Via Hermes Tools

The plugin integrates seamlessly with the existing `web_extract` tool:

```python
# Static page — Trafilatura handles it
web_extract(urls=["https://example.com"])

# JS-heavy page — Crawl4AI handles it
web_extract(urls=["https://github.com/about"])
web_extract(urls=["https://react.dev"])
```

### Automatic Routing

No manual intervention needed. The plugin:

1. Receives extraction request
2. Analyzes target URL
3. Selects optimal backend
4. Returns extracted content

## Testing

### Verification Commands

```bash
# Test plugin import
python3 -c "
import sys
sys.path.insert(0, '/home/amirul/.hermes/plugins/hybrid-web')
from provider import HybridWebSearchProvider
p = HybridWebSearchProvider()
print('available:', p.is_available())
print('name:', p.name)
print('supports_extract:', p.supports_extract())
"

# Test backend resolution
python3 -c "
from hermes_cli.plugins import _ensure_plugins_discovered, get_plugin
_ensure_plugins_discovered(force=True)
plugin = get_plugin('hybrid-web')
print('Plugin loaded:', plugin is not None)
print('Available:', plugin.is_available())
"

# Test actual extraction
web_extract(urls=["https://example.com"])        # Should use Trafilatura
web_extract(urls=["https://github.com/about"])   # Should use Crawl4AI
```

### Expected Results

- Static pages: Fast extraction (< 2 seconds)
- JS-heavy pages: Slower but complete extraction (5-30 seconds)
- No fallback to DuckDuckGo (ddgs) for extraction

## Troubleshooting

### Plugin Not Loading

**Symptom:** `web_extract` falls back to DuckDuckGo with "search-only backend" error

**Fix:**
1. Verify plugin is enabled in config:
   ```bash
   grep -A 5 "plugins:" ~/.hermes/config.yaml
   # Should show: enabled: [hybrid-web]
   ```

2. Restart Hermes gateway:
   ```bash
   hermes gateway restart
   ```

### Extraction Timeout

**Symptom:** Crawl4AI times out on complex pages

**Fix:** Increase timeout in `~/.hermes/plugins/hybrid-web/provider.py`:

```python
# Find and modify the timeout value
CRAWL4AI_TIMEOUT = 60  # Increase from 45 to 60 seconds
```

### Backend Always Uses Trafilatura

**Symptom:** JS-heavy pages return incomplete content

**Fix:** Check detection logic in `provider.py`. Some SPAs may need marker updates.

## Implementation Details

### Provider Class

`HybridWebSearchProvider` extends the base web search provider:

- `is_available()` — Returns True if plugin is loaded
- `supports_extract()` — Returns True (enables web_extract routing)
- `extract(urls, ...)` — Main extraction logic with backend selection

### Integration with Hermes

The plugin hooks into Hermes' web tools via:

1. **Plugin discovery** — `_ensure_plugins_discovered()` loads the plugin
2. **Backend selection** — `_is_backend_available("hybrid-web")` validates availability
3. **Tool dispatch** — `web_extract_tool()` routes to the plugin

## Related Files

- `~/.hermes/plugins/hybrid-web/` — Plugin source code
- `~/.hermes/config.yaml` — Configuration (extract_backend, plugins.enabled)
- `~/.hermes/hermes-agent/tools/web_tools.py` — Backend selection logic
- `~/.hermes/hermes-agent/hermes_cli/plugins.py` — Plugin discovery/loading

## Changelog

### 2026-06-29

- Initial implementation
- Automatic static/dynamic page detection
- Trafilatura + Crawl4AI backend routing
- 45-second timeout for JS-heavy pages
- Config: `web.extract_backend: hybrid-web`
