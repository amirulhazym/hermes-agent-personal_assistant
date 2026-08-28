# Google Workspace Slash Commands Plugin

Real working example built 2026-07-15. Registered /gdocs, /gdrive, /gsheet, /gmail, /gworkspace as Hermes slash commands via `ctx.register_command()`.

## Plugin Structure

```
~/.hermes/plugins/google-workspace-commands/
├── plugin.yaml
└── __init__.py
```

### plugin.yaml

```yaml
name: google-workspace-commands
version: 1.0.0
description: "Google Workspace slash commands — /gdocs, /gdrive, /gsheet, /gmail, /gworkspace."
author: "@amirulhazym"
```

### Handler Architecture (corrected for gateway-mode limitation)

Each command handler uses the Two-Pattern Design — direct subprocess for API operations, redirect to natural message for NL-heavy instructions.

The handler does NOT use `delegate_task` because it DOES NOT WORK in gateway mode (WhatsApp, Telegram, Discord — see the parent_agent architecture constraint in the main SKILL.md). Instead:

```python
def _delegate(name: str, service: str, raw_args: str) -> str:
    prompt = raw_args.strip()
    if not prompt:
        return usage_help(name, service)

    # Pattern 1: Direct subprocess call to google_api.py (works in ALL modes)
    # Runs as a regular Python subprocess — zero LLM cost, no model burn
    import subprocess
    try:
        result = subprocess.run(
            ["python3", GOOGLE_API_PATH, service] + prompt.split(),
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return f"API error (code {result.returncode}): {result.stderr[:500]}"
    except Exception as exc:
        return f"Execution failed: {exc}"
```

### Key Design Decisions

1. **No delegage_task** — understood limitation: parent_agent is only available in CLI mode. Gateway-mode handlers must use direct execution.

2. **Zero LLM cost** — the handler calls google_api.py via subprocess. Every API call costs 0 tokens. The google_api.py script uses the OAuth token cached on disk.

3. **NL instructions go through natural conversation** — user types the complex request as a regular message (no / prefix), and the agent processes it with full LLM access, session context, and tool calling.

4. **Plugin visibility is the PRIMARY value** — commands appear in Telegram picker, Discord native menus, WhatsApp /commands list. They surface the capability exists.

5. **Synchronous** — commands return inline. Direct subprocess is near-instant for API lookups.

6. **Usage help on empty args** — handler returns formatted usage text when no arguments provided.

### Verification Commands

```bash
# Check plugin is listed
hermes plugins list | grep google-workspace

# Enable if needed
hermes plugins enable google-workspace-commands

# Verify command discovery
python3 -c "
from hermes_cli.plugins import discover_plugins
discover_plugins(force=True)
from hermes_cli.commands import _iter_plugin_command_entries
for name, desc, hint in _iter_plugin_command_entries():
    print(f'  /{name} — {desc}')
"

# Verify handlers run
python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location(
    'gws_plugin',
    '$HOME/.hermes/plugins/google-workspace-commands/__init__.py'
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
for name in ['gdocs', 'gdrive', 'gsheet', 'gmail', 'gworkspace']:
    handler = mod._make_handler(name, mod._COMMANDS[name]['service'])
    assert handler('') is not None, f'{name} empty failed'
    print(f'  /{name}: OK')
"
```

### Setup Prerequisites

The Google Workspace OAuth must be completed first (setup.py --auth-url to --auth-code to --check). The plugin uses the same google_token.json for auth.

**PKCE fix**: Desktop app OAuth client secrets should NOT use PKCE. setup.py was patched to remove `autogenerate_code_verifier=True` from the flow. See google-oauth-vps-setup skill for full setup flow.
