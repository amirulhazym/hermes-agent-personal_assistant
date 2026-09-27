# Spec: OpenCode Free 403 & Compression Auxiliary Runtime Drift Recovery

## Problem Statement

On 2026-09-27 at 15:05 MYT, the active WhatsApp Maxis session crossed the compression threshold while its persisted main runtime was `opencode-free / mimo-v2.6-flash-free`. The provider returned HTTP 403 `FreeTierError` stating that OpenCode's free tier can only be used from within OpenCode.

The compression path was configured correctly on disk as `auxiliary.compression = antigravity / gemini-3.8-flash`, but the live `agent/auxiliary_client.py` did not contain the SSOT-managed `llm_execution` middleware relay. Antigravity is an in-process plugin whose `127.0.0.1:8765` URL is a dummy compatibility endpoint; without middleware interception, the auxiliary request attempted the dummy URL directly and failed with connection refused.

Compression then fell back to the main agent model, which was the same unusable OpenCode Free route, causing the final 403 and leaving the transcript over threshold. The transcript itself was preserved; no historical messages were dropped.

The authoritative runtime tree manifest expects `agent/auxiliary_client.py` SHA-256 `ccd50504928c5c5c347517e087e487373a9fd46082523559149eb593942d598b`, while the live VPS file was `de28c68a86491988e8098f9fd021e99c95e866f3782ba48893f561d33f4f24a3`. Existing repository reconstruction tests remained green because they intentionally do not compare live runtime bytes.

The current live Codex model cache exposes `gpt-6-luna` but does not expose `gpt-6-luna-900k`. The owner selected `openai-codex / gpt-6-luna` as the replacement global default unless a genuine 900k variant is later discovered.

## Solution
1. **Fail closed OpenCode Free for Hermes chat use while provider restriction remains**
   - Treat `opencode-free` as unavailable for selectable/default chat routing.
   - Hide it from shared Telegram/WhatsApp model picker output and reject typed attempts to select it.
   - Do not spoof OpenCode client identity, proprietary headers, or other client-gating behavior.
   - Preserve a future re-enable path only after legitimate external callability is re-verified.

2. **Move the global default to verified Codex**
   - Set SSOT config template and, after owner execution approval, live config to `provider: openai-codex` and `default: gpt-6-luna`.
   - Do not synthesize `gpt-6-luna-900k`; use it only if live Codex discovery later exposes that exact ID.
   - Existing session-level overrides are not automatically migrated.

3. **Restore auxiliary middleware routing from authoritative source**
   - Reconstruct the approved Hermes runtime from the current source lock and patch series.
   - Verify that the reconstructed `agent/auxiliary_client.py` routes synchronous auxiliary completions through `run_llm_execution_middleware`.
   - Preserve the fail-closed middleware hardening already represented in SSOT.
   - Keep auxiliary compression on `antigravity / gemini-3.8-flash`.

4. **Add targeted live-drift protection**
   - Add a release-specific preflight/read-back gate for the exact runtime files this repair manages.
   - The gate must compare expected reconstructed bytes against the live destination and report the mismatching paths before deployment and after deployment.
   - Repository-only reconstruction tests remain source-contract tests; live parity must be a distinct gate.

## User Stories
1. As the owner, I want Hermes to stop offering OpenCode Free chat routes that the provider currently rejects, so normal messages do not fail with a known 403.
2. As the owner, I want the daily default to use my verified `openai-codex / gpt-6-luna` entitlement, so new sessions start on a working model.
3. As the owner, I want existing Telegram/WhatsApp sessions left untouched, so I can manually select another model and retry without automatic session mutation.
4. As the owner, I want compression to continue using Antigravity Gemini 3.8 Flash through the in-process middleware path, so large conversations can compact without falling through to the dummy URL.
5. As the operator, I want deployment preflight to expose managed live-byte drift for this release, so source/runtime divergence cannot remain invisible until an incident.

## Implementation Decisions

- Owner lock: `opencode-free` is fail-closed for Hermes chat selection while the provider restriction persists.
- Owner lock: global default becomes `openai-codex / gpt-6-luna`.
- Evidence lock: `gpt-6-luna-900k` is absent from the current live Codex cache and must not be invented.
- Owner lock: do not migrate or rewrite existing session model overrides; the owner will use Hermes slash commands and retry manually.
- Preserve `auxiliary.compression.provider: antigravity` and `model: gemini-3.8-flash`.
- Source changes must be represented in the personal SSOT and deployed only from an exact reconstructed candidate.
- No direct edits are allowed inside the live Hermes framework checkout or the installed Antigravity dependency.

## Testing Decisions
- RED test: shared model discovery/picker does not expose `opencode-free` while the fail-closed policy is active.
- RED test: typed model selection using `opencode-free`, `free`, or an OpenCode Free model ID is rejected with an actionable unavailable message.
- RED test: Codex default contract uses `gpt-6-luna` and never synthesizes `gpt-6-luna-900k` when live discovery does not return it.
- RED test: synchronous auxiliary completion invokes `run_llm_execution_middleware` for `provider=antigravity`; direct downstream creation is not used as a silent bypass when middleware raises.
- RED test: targeted runtime parity preflight reports a live hash mismatch for `agent/auxiliary_client.py` and passes after bytes match the approved candidate.
- Regression: existing OpenCode Go, OpenCode Zen fail-closed policy, Codex discovery, Antigravity main-chat path, Telegram/WhatsApp shared model picker, compression, and runtime reconstruction suites remain green.
- Runtime verification after approval must prove compression produces a summary through Antigravity without a connection attempt to the dummy URL and without OpenCode Free fallback.

## Out of Scope

- Migrating, deleting, resetting, or directly editing the two currently active sessions pinned to OpenCode Free.
- Creating or spoofing a `gpt-6-luna-900k` alias.
- Bypassing OpenCode's client restriction.
- Changing OpenCode Go subscription behavior.
- Changing medication tracking logic or any unrelated Hermes subsystem.
- Full-tree overwrite of unrelated live drift; deployment remains selective to the approved repair surface.

## Release Boundary

Phase 2 produces only this spec, tracer-bullet tickets, and an implementation plan. Phase 4 code/config/runtime execution is blocked until the mandatory Phase 3 owner approval gate.
