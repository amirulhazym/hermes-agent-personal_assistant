# Codex Account-Usage Audit Reference

**Pattern-Key:** `codex-account-usage-evidence-chain`
**Captured:** 2026-07-28
**Scope:** Hermes `/usage`, `/insights`, ChatGPT-plan Codex rate limits, and the ChatGPT backend usage endpoint.

## Durable findings

1. Hermes `/usage` can combine two different domains in one reply:
   - live authenticated account rate-limit data from `https://chatgpt.com/backend-api/wham/usage`;
   - Hermes-local session counters, context usage, and cost-route output.
   Keep these sections visibly separate. Local token totals are not account quota.

2. Preserve the raw schema before rendering. At minimum retain:
   `plan_type`, `allowed`, `limit_reached`, `primary_window`, `secondary_window`,
   `used_percent`, `limit_window_seconds`, `reset_after_seconds`, `reset_at`,
   `additional_rate_limits`, `credits`, `rate_limit_reset_credits`, and
   `spend_control`.

3. Never infer window meaning from a field name or a null value. A null
   `secondary_window` proves only that the field was null in that response; it
   does not prove that no other limit exists.

4. Never call a primary window `Session` unless the server schema explicitly
   defines that semantic. Calculate and display the duration dynamically. Example:
   `604800 seconds = 10080 minutes = 168 hours = 7 days`.

5. Convert epoch timestamps three ways when region matters: UTC, system local,
   and the user's requested IANA timezone. Do not trust a system abbreviation
   such as `CST` to mean Malaysia time.

6. The official Codex Rust client has evidence of the same ChatGPT route:
   `PathStyle::ChatGptApi => format!("{}/wham/usage", self.base_url)` and converts
   `limit_window_seconds` to rounded-up minutes. This supports “used by official
   Codex software” but does not make the endpoint a documented public API.

7. Official pricing documentation and live account responses can disagree in
   apparent window semantics. Report both raw sources. Do not force an account's
   seven-day primary window into the published five-hour description, and do not
   declare either source wrong without schema/rollout evidence.

## Required fresh-capture protocol

1. Resolve the real Hermes credential path; never type a fake `***` token or
   placeholder into a request.
2. Capture request start/end timestamps with timezone, method, URL/path, query,
   body presence, non-secret headers, status, HTTP version, redirects, response
   content type, date/cache headers, and duration.
3. Redact account ID, email, user ID, access/refresh tokens, authorization values,
   cookies, device IDs, and request IDs before printing JSON.
4. Capture at least two successful responses separated by ordinary investigation
   work. Timestamp every response. A percentage change is not chronological
   evidence if one side has no timestamp.
5. Show raw sanitized JSON before interpretation. Then calculate duration and
   timestamp conversions with a tool.
6. If the request is made directly rather than through the user-facing adapter,
   label it a source/handler test, not an end-to-end delivery test.

## Handler versus delivery boundary

Running Hermes' `_handle_usage_command()` with a synthetic event proves the
handler/render path and its live upstream fetch. It does **not** prove that a
Telegram user received the message. Report these separately:

- **Handler output:** direct return value from the actual Hermes handler.
- **Adapter delivery:** outbound Telegram API acceptance/status.
- **User-visible receipt:** destination-side evidence or screenshot.

Do not upgrade the first into the third.

## `/insights` boundary

Trace `gateway/slash_commands.py` → `SessionDB` → `InsightsEngine` → SQL aggregation.
A local insights report is not official OpenAI account usage. Evidence that it is
local includes:

- SQLite path under Hermes state;
- `sessions` fields such as `input_tokens`, `output_tokens`, cache counters,
  reasoning counters, billing route, and cost fields;
- output containing non-OpenAI models or multiple platforms;
- no OpenAI request in the handler's data path.

If possible, run the analysis with a read-only SQLite URI (`mode=ro`) or an
isolated copy. A normal `SessionDB()` may initialize or migrate state and should
not be described as read-only merely because the query is SELECT-only.

## Official-source retrieval pitfalls

- Prefer the current official page in a browser when `.md` or `llms.txt` URLs
  return 403/404. Record the redirect (for example, developers.openai.com →
  learn.chatgpt.com) and the exact page title/URL actually read.
- Search-result snippets are useful discovery evidence but are weaker than the
  page body. If the Help Center is Cloudflare-blocked, say so and downgrade the
  Help Center claim rather than presenting the snippet as a full-page capture.
- Official source-code evidence can establish client behavior and endpoint use;
  it cannot establish a stable public API contract or guarantee future schema
  compatibility.

## Security checks

- Check auth store and Hermes state permissions without printing contents.
- Scan logs for actual secret-shaped values, not merely identifier strings such
  as `api_key` or `Authorization` in source/log messages.
- Treat a world-readable session database as a privacy finding even if OAuth
  tokens are protected separately.
- Do not change permissions or rotate credentials during an audit unless the user
  explicitly authorizes the change.

## Evidence labels

Use:

- **Verified:** direct source/runtime evidence supports the exact claim.
- **Mostly verified:** core claim is supported but a presentation or boundary gap remains.
- **Plausible but unverified:** consistent with available evidence, not established.
- **Unsupported:** no evidence supports the claim.
- **Contradicted:** direct evidence conflicts with it.
- **Unable to verify:** access or installation boundary prevented the test.

Do not use “complete” when dashboard comparison, native CLI execution, adapter
receipt, or other required boundary evidence is missing.

## Primary sources

- OpenAI Codex pricing: https://developers.openai.com/codex/pricing
- OpenAI Codex developer commands: https://developers.openai.com/codex/developer-commands
- Official Codex client source (pinned evidence): https://github.com/openai/codex/blob/4d4767f7979ae7da6f64595c80d2bb8d6fdd0c49/codex-rs/backend-client/src/client.rs
- ChatGPT usage dashboard: https://chatgpt.com/settings/usage
- ChatGPT-plan Codex help article: https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
