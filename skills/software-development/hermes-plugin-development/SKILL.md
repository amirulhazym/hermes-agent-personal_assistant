---
name: hermes-plugin-development
description: "Create Hermes Agent plugins — slash commands, hooks, model-providers, tools. Use when building a Hermes plugin, adding custom slash commands, creating a model-provider plugin, or extending Hermes via the plugin API."
version: 1.1.0
author: agent
---

# Hermes Plugin Development

Recipes and pitfalls for building Hermes Agent plugins — the supported way to extend Hermes without touching core source code. Plugins survive `hermes update`, work across all gateways (Telegram, WhatsApp, Discord, CLI), and auto-register via the plugin manifest.

## Plugin Categories

Hermes has several distinct plugin types. Use the right directory:

| Type | Location | Entry Point | Purpose |
|------|----------|-------------|---------|
| **Model Provider** | `plugins/model-providers/<name>/` | `__init__.py` + `plugin.yaml` | Add an LLM inference provider (OpenAI-compatible API, custom router, etc.) |
| **Slash Commands** | `plugins/<name>/` | `__init__.py` + `plugin.yaml` | Custom `/command` handlers across all surfaces |
| **Lifecycle Hooks** | `plugins/<name>/` | `__init__.py` | `post_tool_call`, `on_session_end`, etc. |
| **Custom Providers** | `plugins/<name>/` | `__init__.py` | Web search, browser, TTS, image-gen, transcription backends |

---

## Model-Provider Plugins

Add a new LLM inference provider without touching any core source file. Uses the `ProviderProfile` pattern — same as the 20+ bundled providers (arcee, gmi, fireworks, novita, etc.).

### Directory Structure

```
~/.hermes/plugins/model-providers/<provider-name>/
├── plugin.yaml          # Manifest (name, kind, version, description)
└── __init__.py          # ProviderProfile definition + register_provider()
```

### plugin.yaml

```yaml
name: <provider-id>-provider
kind: model-provider
version: "1.0"
description: Human-readable description
author: <your-name>
```

### __init__.py — Simple OpenAI-compatible provider

```python
"""Provider display name — brief description."""

from providers import register_provider
from providers.base import ProviderProfile

provider = ProviderProfile(
    name="<provider-id>",              # Canonical slug — used in /model and config
    aliases=("alias1", "alias2"),       # Alternative names for provider:model syntax
    display_name="Display Name",        # Human-readable in pickers
    description="What this provider is",
    signup_url="https://example.com/signup",  # Optional
    env_vars=("API_KEY_ENV_VAR",),      # Env var names checked for API key
    base_url="https://api.example.com/v1",    # Base API URL
    auth_type="api_key",                # "api_key" (default), "oauth_device_code", etc.
    default_aux_model="model-name",     # Default auxiliary/fallback model
    fallback_models=(                   # Model list when live fetch unavailable
        "model-1",
        "model-2",
    ),
)

register_provider(provider)
```

### __init__.py — Custom logic provider (override methods)

For providers needing custom model fetching, API kwargs, or reasoning handling, subclass `ProviderProfile`:

```python
"""Custom provider with override methods."""

from providers import register_provider
from providers.base import ProviderProfile

class MyCustomProfile(ProviderProfile):
    def fetch_models(self, *, api_key=None, base_url=None, timeout=8.0):
        """Override to call a custom models endpoint."""
        if not (base_url or self.base_url):
            return None
        return super().fetch_models(api_key=api_key, base_url=base_url, timeout=timeout)

    def build_api_kwargs_extras(self, *, reasoning_config=None, **ctx):
        """Override to add extra_body or top-level params."""
        return {}, {}

provider = MyCustomProfile(
    name="my-custom",
    ...
)

register_provider(provider)
```

### What Auto-Wires

When a plugin calls `register_provider()`, the following wire up automatically:
- `PROVIDER_REGISTRY` entry in `auth.py` (credential resolution, env-var lookup)
- `api_mode` set to `chat_completions` (or the profile's setting)
- `base_url` from profile or config/env override
- `env_vars` checked in priority order for API key
- `fallback_models` list registered
- `--provider` CLI flag accepts the provider id
- `hermes model` picker includes the provider
- `hermes setup` wizard delegates automatically
- `provider:model` alias syntax works
- Runtime resolver returns correct `base_url` and `api_key`
- Fallback model activation works

**User plugins override bundled plugins of the same name** (last-writer-wins in `register_provider()`).

### Reference Examples (Bundled)

Grab actual working templates from the Hermes source:

- **Simple API-key provider:** `plugins/model-providers/arcee/__init__.py` — minimal ProviderProfile
- **Aliases + aux model:** `plugins/model-providers/gmi/__init__.py` — display_name, signup_url, default_aux_model, default_headers
- **Custom logic:** `plugins/model-providers/custom/__init__.py` — subclass with fetch_models + build_api_kwargs_extras overrides

### Pitfalls

1. **Import path:** Use `from providers import register_provider` and `from providers.base import ProviderProfile`. These are runtime-resolved in Hermes's plugin loader — static analysis (pyright/pylance) will show import errors that work fine at runtime.

2. **Provider ID uniqueness:** The canonical `name` must not collide with existing providers. Check `hermes model` for existing list. Provider IDs are case-sensitive.

3. **Model names must match the endpoint** — if the provider expects exact model strings (e.g. `gpt-5.6-sol` not `gpt-5.6-sol-preview`), use the exact names from their docs or `/models` endpoint.

4. **Known bug #14849:** Custom providers in `config.yaml::providers:` emit a false "Unknown provider" warning from `hermes doctor` and `hermes model` pre-validation. Plugin path (above) does NOT trigger this bug — plugin-registered providers are recognised by all validation surfaces. The bug only affects the `config.yaml` `providers:` dict syntax.

5. **Gateway restart needed** for provider discovery. After creating the plugin files, run `hermes gateway restart` (or `/restart` in gateway chat) for the provider to appear in model pickers.

---

## Slash Command Plugins

(Content unchanged — see below for full documentation.)

Slash commands accessible across platforms. Commands are auto-discovered by gateway on startup and rebuilt on `hermes gateway restart`. They appear in:
- Telegram bot command menu (via `setMyCommands`)
- Discord native slash picker
- `/commands` browse
- `GATEWAY_KNOWN_COMMANDS` for WhatsApp routing

### Directory Structure

```
~/.hermes/plugins/<plugin-name>/
├── plugin.yaml          # Manifest (name, version, description, author)
└── __init__.py          # register(ctx) entry point + handler logic
```

### plugin.yaml (minimal)

```yaml
name: my-plugin
version: 1.0.0
description: "What it does"
author: "@username"
```

### __init__.py (skeleton)

```python
def register(ctx) -> None:
    """Plugin entry point. ctx is hermes_cli.plugins.PluginContext."""
    ctx.register_command(
        "my-command",
        handler=_handle,
        description="Does something",
        args_hint="<prompt>",
    )

def _handle(raw_args: str) -> str | None:
    if not raw_args.strip():
        return "Usage: /my-command <prompt>"
    # Process via subprocess, delegate_task, or direct Python
    return f"Result: {raw_args}"
```

### Slash Command Registration

`ctx.register_command(name, handler, description, args_hint)`:

- **name** — canonical name without slash. Appears in Telegram picker, `/help`, Discord native menu.
- **handler** — `fn(raw_args: str) -> str | None`. Can be async. Returns response text sent to user.
- **description** — one-line shown in command menus.
- **args_hint** — optional, shown as placeholder. E.g. `"<instruction>"`, `"<file>"`.

Commands are auto-discovered by gateway on startup and rebuilt on `hermes gateway restart`. They appear in:
- Telegram bot command menu (via `setMyCommands`)
- Discord native slash picker
- `/commands` browse
- `GATEWAY_KNOWN_COMMANDS` for WhatsApp routing

## Testing During Development

1. Verify plugin discovery: `hermes plugins list` → check Status column
2. Enable: `hermes plugins enable <name>`
3. Force reload: `python3 -c "from hermes_cli.plugins import discover_plugins; discover_plugins(force=True)"`
4. Check command registry: `python3 -c "from hermes_cli.commands import _iter_plugin_command_entries; print(list(_iter_plugin_command_entries()))"`
5. Gateway restart needed for live activation: `hermes gateway restart`

## Critical Architecture Constraint: Gateway vs CLI Mode

This is the single most important thing to understand about plugin slash commands:

**`delegate_task` does NOT work from gateway-mode handlers.** This is not a "sometimes works" edge case — it is a hard architectural boundary.

- **CLI mode:** self._manager._cli_ref.agent IS available during dispatch_tool, so parent_agent is injected and delegate_task works.
- **Gateway mode (WhatsApp, Telegram, Discord):** self._manager._cli_ref is None, so parent_agent is NOT injected and delegate_task fails with "requires a parent agent context."

Source: `hermes_cli/plugins.py:492-496` — dispatch_tool checks `getattr(cli, "agent", None)` only when `cli` is not None. In gateway mode, `cli` is None, so parent_agent is never set.

**What this means for your design:** The handler runs in the gateway's ASGI process, not inside the agent loop. The gateway does not host a live agent object — agents are created per conversation turn. parent_agent is only available in CLI mode.

**Working pattern for gateway-mode handlers:** The handler must run DIRECT Python (subprocess, file I/O, API calls). If LLM-powered processing is needed, the handler should return a redirect message telling the user to send as a regular message for complex requests.

## The Two-Pattern Design (recommended)

For plugins that need BOTH quick API operations AND NL-powered processing, design with two explicit paths:

```python
def _handle(raw_args: str) -> str:
    prompt = raw_args.strip()
    # Pattern 1: Quick API ops -> direct subprocess (works in ALL modes)
    for kw in ["search", "list", "get", "find", "create"]:
        if prompt.lower().startswith(kw):
            return _direct_api_call(prompt)
    # Pattern 2: NL-heavy -> redirect to natural message
    return (
        "For complex instructions like 'create doc from today's session', "
        "send as a regular message (no / prefix) so I can process it "
        "with full context and LLM access.\n\n"
        "Quick operations you CAN use here:\n"
        "/gmail search is:unread --max 5\n"
        "/gdrive search quarterly report\n"
        "/gdocs create --title Notes --body text"
    )
```

The plugin commands exist PRIMARILY for visibility in platform command pickers (Telegram, Discord) and for quick API lookups. NL-heavy tasks go through natural conversation where the agent has full context.

## Pitfalls

1. **Gateway restart required** — plugin enable is instant but command routing rebuilds on gateway restart. Until restart, commands won't route through handlers even though `hermes plugins list` shows "enabled."

2. **Handler runs OUTSIDE agent loop** — `_handle(raw_args)` is a plain Python function called from gateway command dispatch, not from the agent's LLM loop. It has no model access, no session context, no tool calling.

3. **delegate_task ALWAYS fails in gateway mode** — This is architecture, not a bug. `ctx.dispatch_tool("delegate_task", ...)` WILL fail in gateway mode (WhatsApp, Telegram, Discord) because parent_agent is None. Design your handler to work WITHOUT delegate_task. Subprocess-based direct execution is the only reliable approach for gateway plugin handlers.

4. **No model access = no API burn** — Since the handler cannot use delegate_task in gateway mode, it also cannot trigger LLM API calls. Plugin slash commands are inherently safe against accidental model switches or wrong-provider billing. Subprocess execution costs zero LLM tokens. This is a FEATURE, not a limitation.

5. **Command name conflicts** — names colliding with built-in commands are silently rejected. Check `hermes_cli.commands.COMMAND_REGISTRY` before naming.

6. **Hyphens in names** — Telegram replaces `-` with `_` in command names. Use hyphens freely; the gateway handles translation.

7. **not enabled after creation** — new plugins default to disabled. Run `hermes plugins enable <name>` once.

8. **Plugin is discovered lazily** — `_iter_plugin_command_entries()` calls `get_plugin_commands()` only when gateway needs the list. Plugin loading happens at gateway startup; `discover_plugins(force=True)` forces rescan.

## References

- `references/example-google-workspace-plugin.md` — real working example: slash commands for Google Workspace
