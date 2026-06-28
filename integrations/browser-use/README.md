# Browser-Use Integration

> Priority #3 — AI-driven browser automation for the web.  
> Uses Playwright to control a real browser. Different use case from cua-driver (desktop automation).

## What It Is

**Browser-Use** ([browser-use/browser-use](https://github.com/browser-use/browser-use)) is an open-source Python framework that lets an LLM drive a real web browser. The LLM decides what to click, type, or scroll to accomplish a task.

- **License**: MIT ✅ Free
- **Stars**: ~101K
- **Stack**: Python + Playwright
- **Why:** Provides AI-powered web automation — login flows, multi-step navigation, dynamic content extraction — things that pure scraping libraries cannot do programmatically.

> **Key distinction from cua-driver:** `cua-driver` automates the **desktop** (CUA driver for window capture, click, type on any app). Browser-Use is **web-browser-specific** (Playwright only, not desktop). Both serve different purposes and may coexist.

## System Impact

| Area | Effect |
|------|--------|
| **Web automation** | Can login to sites, navigate complex JS apps, extract data behind authentication. |
| **RAG / Knowledge base** | Can be a first step before extraction (e.g., login → navigate to page → Crawl4AI extracts). |
| **Computer Use** | cua-driver still used for desktop tasks (WhatsApp, Obsidian, etc.). Browser-Use supplements web-specific automation. |
| **Cost** | $0 (self-hosted). Optional cloud version at browser-use.com. |

## Install Steps

```bash
# Ensure in the active Hermes venv
source ~/.hermes/hermes-agent/venv/bin/activate

# Install browser-use
pip install browser-use

# Install Playwright browser binaries
playwright install-deps chromium
playwright install chromium

# Verify
python -c "from browser_use import Agent; print('OK')"
```

### System Dependencies

```bash
# Ubuntu/WSL — ensure browser deps installed
# Playwright auto-installs Chromium, but needs system libs
sudo apt-get install -y libatomic1 libasound2 libatk-bridge2.0-0 2>/dev/null || true
```

## Usage

### Python — Basic Task

```python
import asyncio
from browser_use import Agent

async def main():
    agent = Agent(task="Go to https://example.com and extract the main content")
    result = await agent.run()
    print(result)

asyncio.run(main())
```

### Multi-Step Automation Example

```python
import asyncio
from browser_use import Agent

async def login_and_scrape(login_url, username, password, target_page):
    agent = Agent(task=f"""
        1. Navigate to {login_url}
        2. Enter username: {username}
        3. Enter password: {password}
        4. Click login
        5. Navigate to {target_page}
        6. Extract all article titles and links
        7. Return as JSON
    """)
    result = await agent.run()
    return result

# Run
asyncio.run(login_and_scrape("https://login.com", "user", "pass", "https://data.com"))
```

### Hermes Skill Example

```python
# ~/.hermes/scripts/browser-automation.py
# Called by Hermes via execute_code or terminal tool

import asyncio
import sys
from browser_use import Agent

async def run_task(task_description: str):
    agent = Agent(task=task_description)
    return await agent.run()

if __name__ == "__main__":
    # Example usage:
    # python browser-automation.py "Go to https://quotes.toscrape.com and extract all quotes"
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Extract data from https://example.com"
    result = asyncio.run(run_task(task))
    print(result)
```

## When to Use Which

| Task | Tool |
|------|------|
| Web scraping (static, no login) | Trafilatura / Crawl4AI |
| Web scraping (JS-rendered SPA) | Crawl4AI |
| Login + multi-step web task | **Browser-Use** |
| Desktop app automation (WhatsApp, Obsidian, etc.) | **cua-driver** |
| Bypass anti-bot | Scrapling / curl-impersonate |

## Configuration

No global config needed. Browser-Use is used on-demand from scripts. Consider environment variable for LLM API key:

```bash
export BROWSER_USE_API_KEY="your-api-key"  # if using cloud
# or it uses your existing DEEPSEEK_API_KEY / OPENAI_API_KEY
```

## Infrastructure Role

```
User sends request requiring web login
        │
        ▼
Hermes decides: "task requires browser navigation"
        │
        ▼
Browser-Use launches Playwright (headed/headless)
        │
        ▼
LLM decides actions (click, type, navigate)
        │
        ▼
Page content extracted → Crawl4AI/MarkItDown (if needed) → Response to user
```

## Maintenance Checklist

- [ ] `pip list | grep browser-use` → correct version
- [ ] `playwright --version` → browsers installed
- [ ] Periodically: `pip install --upgrade browser-use`

## Links

- GitHub: https://github.com/browser-use/browser-use
- Docs: https://docs.browser-use.com/
- PyPI: https://pypi.org/project/browser-use/
