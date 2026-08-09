# v3 Config Schema Delta — 2026-08-08

This candidate reconciles key schema only. Live values, credentials and runtime state were not copied. Placeholder values in `config/config.yaml.template` are non-functional examples.

- Live key paths inspected: `698` (key names only)
- Baseline template key paths: `665`
- Live-only paths represented: `37`
- Template-only paths retained: `4`
- Candidate template key paths after merge: `702`

## Live-only key paths represented

- `agent.personalities.caveman`
- `agent.personality`
- `agent.system_prompt`
- `credential_pool_strategies.custom:ftf`
- `display.platforms.whatsapp.busy_ack_detail`
- `display.platforms.whatsapp.tool_progress`
- `mcp_servers.tavily`
- `mcp_servers.tavily.connect_timeout`
- `mcp_servers.tavily.timeout`
- `mcp_servers.tavily.url`
- `model.models`
- `model.models.big-pickle`
- `model.models.big-pickle.context_length`
- `model.models.deepseek-v4-flash-free`
- `model.models.deepseek-v4-flash-free.context_length`
- `model.models.laguna-s-2.1-free`
- `model.models.laguna-s-2.1-free.context_length`
- `model.models.ling-3.0-flash-free`
- `model.models.ling-3.0-flash-free.context_length`
- `model.models.mimo-v2.5-free`
- `model.models.mimo-v2.5-free.context_length`
- `onboarding.seen.profile_build_offered`
- `personality`
- `plugins.disabled`
- `providers.a6api`
- `providers.a6api.api_key_env`
- `providers.a6api.base_url`
- `providers.a6api.default_model`
- `providers.a6api.name`
- `providers.ftf`
- `providers.ftf.api_key_env`
- `providers.ftf.base_url`
- `providers.ftf.name`
- `quick_commands.browse`
- `quick_commands.browse.description`
- `quick_commands.browse.target`
- `quick_commands.browse.type`

## Template-only compatibility paths retained

- `auxiliary.background_review.extra_body`
- `mcp_servers.cua-driver`
- `mcp_servers.cua-driver.args`
- `mcp_servers.cua-driver.command`

## Safety

- No live scalar values are present in this document or the template update.
- `config.yaml` with real values remains private runtime state.
- This schema document is evidence of key coverage, not proof that a live configuration is valid for deployment.
