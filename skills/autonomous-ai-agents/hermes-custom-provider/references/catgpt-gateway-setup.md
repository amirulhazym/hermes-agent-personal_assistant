# CatGPT-Gateway: Custom Provider Setup

**Source:** [github.com/GautamVhavle/CatGPT-Gateway](https://github.com/GautamVhavle/CatGPT-Gateway)  
**License:** MIT | **Stars:** 211 | **Last commit:** Jun 21, 2026  
**Verified:** 2026-07-28 — repo active, documentation complete, Docker deployment confirmed

## When to Use

When the built-in `openai-codex` OAuth provider has unresolved bugs (see `evidence-first-feasibility-assessment` → `references/openai-codex-known-bugs.md`) and you need a reliable way to use ChatGPT Plus/Claude subscription as an OpenAI-compatible API endpoint.

## How It Works

CatGPT-Gateway runs a **real Chromium browser** (via Patchright/Playwright stealth fork) that automates the ChatGPT/Claude web UI. It:
1. Types messages into the chat input
2. Waits for response completion
3. Extracts text via clipboard/DOM
4. Returns OpenAI-format JSON

The result is a standard `/v1/chat/completions` endpoint that any OpenAI SDK-compatible tool can consume.

## Architecture

```
Your app (OpenAI SDK / LangChain / Hermes)
        │
        ▼
CatGPT Gateway (FastAPI, port 8000)   ← OpenAI-compatible
        │
        ▼
Real Chromium browser (Patchright)    ← stealth + anti-detection
        │
        ▼
chatgpt.com or claude.ai              ← your logged-in session
```

## Trade-offs vs Built-in Providers

| Aspect | openai-codex (built-in) | CatGPT-Gateway (custom) |
|--------|------------------------|------------------------|
| API type | Codex Responses API | Chat Completions API |
| Speed | ~1-2s | ~3-10s (browser automation) |
| Reliability | ❌ Known stream backfill bugs (#5736, #5883) | ✅ Proven working (211 stars, active) |
| Tool/function calling | Native | System-prompt injection + regex parsing |
| Resource usage | Minimal | Docker + Chromium (~500MB RAM) |
| Cloudflare risk | None (direct API) | Medium (browser fingerprint may trigger) |
| Setup complexity | `hermes auth add openai-codex` | `docker compose up` + one-time login |

## Setup for Hermes

### 1. Deploy CatGPT-Gateway

```bash
cd /opt
git clone https://github.com/GautamVhavle/CatGPT-Gateway.git
cd CatGPT-Gateway
cp .env.example .env
# Edit .env: set PROVIDER=chatgpt (or PROVIDER=claude)
docker compose up --build -d
```

### 2. One-Time Login

Open `http://<vps-ip>:6080/vnc.html` in browser → log into chatgpt.com.
Session saved to Docker volume. Close VNC tab after login.

⚠️ Use email+password, Microsoft, Apple, or magic link — NOT Google OAuth.

### 3. Verify

```bash
curl http://localhost:8000/v1/models -H "Authorization: Bearer dummy123"
# Expected: 200 OK with model list including "catgpt-browser"
```

### 4. Register as Custom Provider in Hermes

Since this is a simple OpenAI-compatible endpoint (not needing plugin registration), just add to config:

```bash
hermes config set providers.catgpt.name "CatGPT Gateway"
hermes config set providers.catgpt.base_url "http://localhost:8000/v1"
hermes config set providers.catgpt.api_key_env "CATGPT_API_KEY"
hermes config set providers.catgpt.default_model "catgpt-browser"
```

Then in `~/.hermes/.env`:
```
CATGPT_API_KEY=dummy123
```

### 5. Use in Hermes

```bash
hermes chat --provider catgpt --model catgpt-browser -q "Hello"
# Or in-session: /model catgpt-browser --provider catgpt
```

## Anti-Detection Details

CatGPT-Gateway uses multiple stealth layers:
- **Patchright** (Playwright fork with anti-detection patches)
- **playwright-stealth** — masks `navigator.webdriver`, canvas/WebGL fingerprints, plugin enumeration
- **Human simulation** — clipboard-pasted messages with randomized delays, mouse drift during thinking
- **Viewport jitter** — randomizes viewport ±20px from base 1280×720 per launch
- **noVNC** — VNC-based login viewer at port 6080 for manual CAPTCHA handling

## Pitfalls

- **Docker DNS bug**: `add_init_script()` in Playwright breaks Chrome DNS in Docker. CatGPT works around this by injecting stealth JS via `page.evaluate()` on every `framenavigated` event instead.
- **Cloudflare can change**: OpenAI may update detection. Monitor GitHub repo for updates.
- **One session at a time**: Browser automation is inherently single-threaded — concurrent requests queue up.
- **Login session expiry**: ChatGPT may log out after days/weeks. Re-login via noVNC required.
- **Memory usage**: Docker + Chromium ~500MB. Ensure VPS has sufficient RAM.
