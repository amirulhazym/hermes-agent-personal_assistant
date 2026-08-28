# Env Var Loading Diagnostics — Worked Examples

## vision_analyze 401 AuthError (2026-07-08)

### Symptoms
- User sent image at 12:28pm via WhatsApp
- vision_analyze returned 401 AuthError — invalid API key
- Config had `api_key: ''` removed on July 3 (fix applied)
- `.env` contained `OPENCODE_ZEN_API_KEY=***`

### Investigation

**Step 1 — Verify config fix was actually applied:**
```yaml
# ~/.hermes/config.yaml → auxiliary.vision:
provider: opencode-zen
model: mimo-v2.5-free
base_url: https://opencode.ai/zen/v1
# No api_key line — good, fallback to env var
```

**Step 2 — Check .env content:**
```
~/.hermes/.env → OPENCODE_ZEN_API_KEY=***  (present, 67 chars)
```

**Step 3 — Check process lifetime vs .env mtime:**
```bash
# Gateway lifetime
$ ps -o lstart= -p 2547611
Wed Jul  8 00:12:43 2026

# .env mtime
$ stat --format='%y' ~/.hermes/.env
2026-07-08 12:37:18.231288912 +0800
```
**.env was modified 9 minutes AFTER the error** — the gateway started at 00:12 with old .env (no OPENCODE_ZEN_API_KEY), error at 12:28, .env updated at 12:37.

**Step 4 — Trace API key resolution chain:**
```python
# hermes_cli/auth.py:371-378
"opencode-zen": ProviderConfig(
    id="opencode-zen",
    api_key_env_vars=("OPENCODE_ZEN_API_KEY",),
    ...
)
```

```python
# hermes_cli/env_loader.py:212-248
def load_hermes_dotenv():
    user_env = home_path / ".env"
    if user_env.exists():
        _load_dotenv_with_fallback(user_env, override=True)  # ← ONCE at import
```

```python
# hermes_cli/main.py:513-515  (called at MODULE IMPORT TIME)
from hermes_cli.env_loader import load_hermes_dotenv
load_hermes_dotenv(project_env=PROJECT_ROOT / ".env")
```

### Root Cause

At gateway startup (00:12), `.env` didn't contain `OPENCODE_ZEN_API_KEY`. `load_hermes_dotenv()` ran once at import time, injected the (missing) env var into `os.environ`. When someone updated `.env` at 12:37 (adding the key), the running gateway had no mechanism to re-read it. Vision_analyze resolved `api_key = os.environ.get("OPENCODE_ZEN_API_KEY", "")` → `""` → 401.

### Fix

Restart the gateway: `systemctl --user restart hermes-gateway`

### Verification

After restart:
1. Check new PID: `ps -o lstart= -p $(pgrep -f 'hermes_cli.main gateway' | head -1)`
2. Verify .env loading in fresh Python: `python3 -c "from dotenv import load_dotenv; import os; load_dotenv('/home/ubuntu/.hermes/.env'); print('OK' if os.environ.get('OPENCODE_ZEN_API_KEY') else 'MISSING')"`
3. Test vision_analyze with a test image

### Key Lesson

When a user says "I applied the fix but it still doesn't work" for any env-var-dependent issue:

1. ✅ Check the file (config.yaml / .env) — was the fix actually written?
2. ✅ Check process lifetime vs file mtime — did the process start before the fix?
3. ✅ Check os.environ inside the running process — /proc/PID/environ is MISLEADING (shows initial env only)
4. ✅ If gap found → restart gateway, don't chase phantom bugs

## Helper: Python probe for env var at runtime

```python
from pathlib import Path
from dotenv import load_dotenv
import os

home = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
env_file = home / ".env"
print(f"Env file: {env_file} (exists={env_file.exists()})")
print(f"mtime={env_file.stat().st_mtime}")
load_dotenv(dotenv_path=env_file, override=True, encoding="utf-8")

var = os.environ.get("OPENCODE_ZEN_API_KEY", "")
print(f"OPENCODE_ZEN_API_KEY after load: {'SET (len=' + str(len(var)) + ')' if var else 'EMPTY'}")
```
