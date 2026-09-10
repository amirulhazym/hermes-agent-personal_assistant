# Live Discovery Findings — Gemini 3.8 Flash + Antigravity V2 Architecture

## 1. Scope and Authority
- **Date**: 2026-09-10 (Asia/Kuala_Lumpur MYT)
- **Target Model**: `gemini-3.8-flash`
- **Target Provider**: `antigravity`
- **Execution Mode**: Standalone user plugin (`plugins/gemini-agentic-v2/`) operating exclusively via `llm_request` middleware.

---

## 2. Live Runtime & Middleware Contract
- **Middleware Hook**: `PluginContext.register_middleware("llm_request", on_llm_request)`
  - Confirmed valid kind in `hermes_cli/middleware.py:29` (`VALID_MIDDLEWARE`).
  - Invoked per API attempt in `agent/conversation_loop.py:3117`:
    ```python
    _llm_request_mw = apply_llm_request_middleware(
        api_kwargs,
        task_id=effective_task_id,
        turn_id=turn_id,
        api_request_id=api_request_id,
        session_id=agent.session_id or "",
        platform=agent.platform or "",
        model=agent.model,
        provider=agent.provider,
        base_url=agent.base_url,
        api_mode=agent.api_mode,
        api_call_count=api_call_count,
    )
    ```
- **Copy-on-Write Semantics**:
  - `apply_llm_request_middleware` deep-copies the request dict before passing to registered middleware (`hermes_cli/middleware.py:94-95`).
  - Stored conversation history, `SessionDB`, and `agent._cached_system_prompt` are unmutated by `llm_request` middleware.
  - Return structure: `{"request": modified_request, "source": "gemini-agentic-v2", ...}` replaces the outgoing ephemeral `api_kwargs`.
- **Pre-Verify Hook Analysis**:
  - `pre_verify` is present in `agent/conversation_loop.py:8411` but injects synthetic user messages (`_pre_verify_synthetic`) which modifies prompt cache structure across turns.
  - Per Section 17 of V2 Work Order: Since `pre_verify` adds multi-turn synthetic injection risk and is non-essential, **V2 core will rely exclusively on `llm_request` middleware** to guarantee zero cache invalidation and zero race conditions.

---

## 3. Provider Transformation Contract (`antigravity-provider`)
- **Live Provider Identity**: `agent.provider == "antigravity"`
- **Message Transformation** (`src/antigravity_provider/transform.py:200-205`):
  - Messages with role `system` or `developer` have their text extracted via `_content_text` and appended to `system_parts` (`{"text": text}`).
  - User and assistant messages are mapped into `contents` with roles `user` and `model`.
  - Adding V2 protocol and dynamic state into the `system` / `developer` message guarantees it is delivered cleanly to Cloud Code / Gemini wire API inside system instructions, without altering conversation message role alternation.

---

## 4. R6-B3 Coexistence and Idempotency
- **Live R6-B3 Baseline**:
  - Injects R6-B3 guardrail into the first system message.
  - Hardened in Round 7B.1 to check privileged context only (`_privileged_context_contains_guardrail`).
- **V2 Interaction**:
  - V2 static protocol text (`agentic-depth-v2.txt`) will be injected into privileged system context once.
  - Dynamic runtime state block will be injected/updated in privileged system context per request.
  - V2 must detect existing V2 static protocol and dynamic blocks independently so neither duplicates across multiple middleware passes.
  - R6-B3 and V2 operate on distinct sentinel markers and distinct content hashes, ensuring 100% coexistence without interference.

---

## 5. Dynamic State Derivation
- Request `messages` inspectable in `on_llm_request`:
  - `tool_calls` in assistant messages indicate tool invocation (terminal, read_file, search_files, write_file, patch, etc.).
  - `tool` role messages carry tool responses.
  - From these messages, the middleware deterministically tallies:
    - `searches_seen`: tool calls matching `search_files`, `web_search`
    - `reads_seen`: tool calls matching `read_file`, `web_extract`
    - `writes_seen`: tool calls matching `write_file`, `patch`
    - `unique_paths`: set of paths referenced in tool calls (bounded to top 5)
  - `mode_hint`:
    - Evaluated from the latest user message text:
      - Keywords indicating investigation/audit/fix -> `DEEP`
      - Active tool turn in progress -> `DEEP`
      - Short factual query with no tool calls -> `DIRECT`
      - Ambiguous -> `MODEL_DECIDE`
  - Dynamic state is rendered as a clean, bounded text block inside system context.
