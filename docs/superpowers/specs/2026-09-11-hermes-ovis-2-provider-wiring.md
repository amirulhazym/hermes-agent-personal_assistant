# `hermes_ovis_2_bot` Provider Wiring and Profile Safety

> **Date:** 2026-09-11
> **Status:** Phase 2 artifact — architecture decision lock received; implementation and runtime mutation still require the Phase 3 owner gate.
> **Evidence labels:** `LIVE-VERIFIED` means direct VPS/runtime output from this investigation; `LOCAL-VERIFIED` means source/repository inspection; `UNVERIFIED` means not proven by the current evidence.

## Problem Statement

The live Telegram bot `@hermes_ovis_2_bot` is configured in the named profile `bot_2`, but the running default multiplex gateway still serves the old profile identity `ovis2`.

Fresh runtime evidence shows:

- `bot_2` Telegram `getMe` → `@hermes_ovis_2_bot` (`LIVE-VERIFIED`).
- `default` Telegram `getMe` → `@MJ_aiassistantbot` (`LIVE-VERIFIED`).
- `bot_2` has `config.yaml`, `.env`, provider plugins, and the configured provider blocks (`LIVE-VERIFIED`).
- `ovis2` has no `config.yaml`, no `.env`, and no provider plugin directory (`LIVE-VERIFIED — absent in checked paths`).
- Root `gateway_state.json` says `served_profiles: ["default", "ovis2"]` and has an `ovis2:telegram` adapter owned by PID `1834884` (`LIVE-VERIFIED`).
- The root runtime log says: `Profile 'ovis2' does not exist ... falling back to global HERMES_HOME`, followed by `Primary provider auth failed: No inference provider configured` (`LIVE-VERIFIED`).
- The durable routing table contains an orphan key `agent:ovis2:telegram:dm:679729206` whose origin profile is `ovis2`; the current root `sessions` table has zero matching `agent:ovis2:*` session rows (`LIVE-VERIFIED`).
- A standalone `bot_2` gateway is still alive and retrying because the default PID owns the Telegram token lock (`LIVE-VERIFIED`).

The observed symptom looks like “all providers are broken,” but provider boundary tests do not support that blanket claim. Zero-token model-list probes returned HTTP 200 for multiple providers under both `default` and `bot_2`, while Antigravity was connection-refused and Fiq returned HTTP 503 maintenance in both profiles. Those are shared/external failures, not evidence of a `bot_2` provider-wiring defect.

## Solution

1. Make `bot_2` the canonical profile for `@hermes_ovis_2_bot`.
2. Serve `bot_2` from the existing single default multiplex gateway; do not run a second gateway for the same Telegram token.
3. Change the live multiplex allowlist from `ovis2` to `bot_2` through the supported config command, only after the Phase 3 approval gate.
4. Add a source-level fail-closed guard: an explicit profile identity that no longer exists or is not served must be rejected/dropped, never silently resolved to global/default `HERMES_HOME` and its provider configuration.
5. Verify provider resolution, picker inventory, and zero-token model discovery under `bot_2`. Do not perform generation requests without a new explicit approval.
6. Capture the source-level guard as an exact upstream patch overlay in the personal SSOT. Do not edit `/home/ubuntu/.hermes/hermes-agent` directly during development.

## User Stories

1. As the owner of `@hermes_ovis_2_bot`, I want the bot to execute under `bot_2`, so its model/provider configuration is the one actually used.
2. As the operator of a multiplex gateway, I want exactly one runtime owner for each Telegram token, so a duplicate gateway cannot create token-lock retries.
3. As a Hermes user, I want an absent or stale profile to fail closed, so Hermes never silently executes a message with another profile's model, credentials, memory, or persona.
4. As an operator, I want `served_profiles` and adapter-owner state to agree with the configured allowlist after reload, so runtime status is meaningful.
5. As a provider maintainer, I want `/model` resolver and picker checks to run under `bot_2`, so provider wiring is tested at the same profile scope as the bot.
6. As a cost-conscious owner, I want model-list verification before any generation request, so diagnostic work does not burn provider tokens.
7. As an operator, I want external provider outages separated from Hermes profile-routing failures, so an Antigravity sidecar outage or Fiq maintenance response is not “fixed” by changing unrelated provider code.
8. As a maintainer, I want a regression test for missing-profile fallback, so deleting or renaming a served profile cannot silently reintroduce the same provider leak.
9. As an SSOT maintainer, I want the framework change represented as a reproducible patch overlay, so live behavior is reconstructible without committing secrets or mutable runtime state.
10. As a reviewer, I want the final report to distinguish `RESOLUTION`, `PICKER INVENTORY`, `MODEL DISCOVERY`, `INFERENCE`, `GATEWAY RELOAD`, and `CHANNEL E2E`, so one passing boundary is not reported as total completion.

## Implementation Decisions

### Locked architecture decisions

- **Canonical profile:** `bot_2`.
- **Runtime topology:** one default multiplex gateway owns `default` and `bot_2` adapters.
- **Rejected topology:** a second standalone `bot_2` gateway competing for a token already owned by the multiplex gateway.
- **Provider verification budget:** zero-token resolver/picker/model-list checks first; no paid generation in this work item.
- **Provider adapter scope:** no new provider adapter or credential rotation. Existing external failures remain separately classified.
- **Deployment boundary:** source candidate and patch overlay first; live config/process changes only after Phase 3 owner approval.

### Terminology lock

- **Canonical profile:** the durable profile ID selected as the owner of a bot's configuration and platform credential. Here: `bot_2`.
- **Served profile:** a `(name, HERMES_HOME)` pair returned by `profiles_to_serve(multiplex=True, profile_allowlist=...)` for the current gateway process.
- **Adapter owner profile:** the profile whose platform credential and adapter instance admit an inbound message. In a multiplexed gateway this is stamped before agent execution.
- **Routed profile:** the profile selected for the source/session by an explicit profile route or adapter ownership.
- **Effective profile home:** the profile directory actually used for config, skills, memory, sessions, and secret scope for that inbound turn.
- **Provider resolution:** a concrete Hermes provider definition with transport/API mode, base URL, and credential mapping.
- **Picker inventory:** the provider/model rows returned by the same listing path used by `/model`.
- **Model discovery:** a provider's zero-token model-list response. It proves connectivity/key/model-list access only.
- **Inference:** a real completion/response request. It is not authorized by this spec.
- **Channel E2E:** a user-visible response through the live Telegram bot after gateway reload. It remains unverified until directly exercised.
- **Orphan routing entry:** durable `gateway_routing` metadata that names a profile/session namespace no longer present in the current served profile set.

### Ownership and lifecycle

| State | Owner | Writable by | Read by | Lifecycle |
|---|---|---|---|---|
| `gateway.multiplex_profile_allowlist` | root/default config | supported config command under owner approval | gateway startup and profile enumerator | until config change |
| `bot_2/config.yaml` | `bot_2` profile | profile config command / approved migration | provider resolver, gateway, picker | profile lifetime |
| `bot_2/.env` | `bot_2` secret scope | approved credential operation only | scoped adapter/provider calls | profile lifetime; secrets excluded from Git |
| served-profile set | current default gateway | gateway startup/reload | adapter construction, route validation, status | process lifetime |
| adapter-owner profile | gateway runner/adapter construction | gateway runtime only | source/session-key and secret-scope logic | adapter lifetime |
| effective profile home | gateway runner per source | scoped runtime context | config, memory, sessions, provider selection | per inbound turn |
| provider model-list result | provider/cache subsystem | zero-token discovery path | picker/provider verification | cache TTL/runtime-dependent |
| `gateway_routing` entry | session-routing store | supported session/routing path | inbound gateway dispatch | until reset/expiry/replacement |
| token lock | gateway lock manager | adapter startup/release | gateway status and adapter lifecycle | adapter lifetime |

### State transition contract

```text
Configured allowlist
  -> served-profile set at gateway startup
  -> adapter owner + token lock
  -> inbound source profile
  -> effective profile home + secret scope
  -> provider resolution
  -> picker inventory/model discovery
  -> optional inference (out of scope here)
  -> channel E2E (separate gate)
```

Every transition must preserve the profile identity. If a named profile is absent from disk or not in the served set, the transition terminates with a secret-free rejection/drop; it must not continue through global/default `HERMES_HOME`.

### Fail-closed profile-resolution contract

`GatewayRunner._resolve_profile_home_for_source()` and the secondary-profile message handler must treat an explicit missing/unserved profile as a rejected source. The existing `ProfileRouteRejected`/`profile_route_rejected` ingress path is the preferred seam unless implementation review proves a narrower typed exception is required.

Required behavior:

- Existing profile → return its profile home and enter its scoped runtime.
- Explicit missing profile → log profile/platform/chat context without secrets, mark/drop the source before agent/provider resolution, and do not call the global/default provider path.
- Invalid profile resolution → fail closed with the same source-level rejection semantics; do not silently fall back.
- Unrouted source with no explicit profile → preserve existing default-profile behavior.

### Provider boundary contract

For `bot_2`, verification is layered:

1. **Registration:** provider plugin/profile is present for the profile process.
2. **Resolution:** actual resolver returns a concrete provider definition from `bot_2` config/pool.
3. **Picker inventory:** `/model` listing path exposes non-empty model IDs.
4. **Model discovery:** zero-token `GET /models` result is captured.
5. **Inference:** not run in this work item.
6. **Gateway reload:** not claimed until the approved config change and process reload are read back.
7. **Channel E2E:** not claimed until the bot visibly responds after reload.

### Engineering invariants

The implementation MUST ALWAYS:

- route `@hermes_ovis_2_bot` to canonical profile `bot_2`;
- keep the default gateway as the sole owner in the selected multiplex topology;
- preserve profile-local provider config and secret scope;
- reject/drop explicit missing or unserved profiles before provider/model resolution;
- preserve the existing default behavior for genuinely unrouted sources;
- keep token values, OAuth material, `.env`, `auth.json`, sessions, and raw logs out of SSOT artifacts;
- report provider status per boundary and external error, not as a single “all providers” boolean.

The implementation MUST NEVER:

- silently map `ovis2` to `bot_2` through an undocumented alias;
- silently fall back from a missing explicit profile to global/default `HERMES_HOME`;
- run a standalone `bot_2` gateway concurrently with the default multiplex owner;
- infer live inference success from a resolver or `/models` response;
- patch Antigravity/Fıq/Codex/Copilot adapters solely because this routing incident exposed their independent status;
- edit the live framework checkout directly during candidate construction;
- run paid generation without a separate owner authorization.

### System-side versus external-side boundary

**System-side:** profile identity, allowlist, served-profile enumeration, adapter ownership, token-lock ownership, session-routing namespace, effective profile home, secret scope, provider resolver/picker wiring.

**External-side:** Antigravity loopback availability, Fiq maintenance state, provider-specific `/models` contracts, Codex/Copilot authentication/API requirements, and model entitlement. External failures are recorded, not “repaired” by changing profile routing.

## Testing Decisions

- Use strict RED → GREEN → REFACTOR for the source guard. The current missing-profile test is intentionally a RED candidate once its assertion is changed from “fallback to global” to “reject/drop.”
- Test the highest useful seam: `GatewayRunner` profile-home resolution plus the secondary message handler, not only a helper's return value.
- Add an isolated multiplex integration fixture with `default` and `bot_2` profile homes, an allowlist containing `bot_2`, and no `ovis2` directory. Assert the source uses `bot_2`, and an explicit `ovis2` source is dropped without entering default scope.
- Run provider resolver/picker/model-list checks in fresh processes with `HERMES_HOME=bot_2`; no generation requests.
- Preserve raw zero-token outputs and classify shared external failures independently.
- Do not modify or query production session state in candidate tests. The live `gateway_routing` orphan row is read-only evidence for the operational migration gate.
- Candidate framework tests run from an isolated materialized upstream tree. The SSOT stores the intentional patch overlay and evidence, not the private runtime checkout.

## Out of Scope

- Renaming or copying the profile to `ovis2`.
- Dedicated `bot_2` gateway topology.
- Direct SQL deletion or hand-editing of `gateway_routing`/`state.db`.
- Paid provider inference or load/stress testing.
- Fixing the Antigravity sidecar connection refusal.
- Fixing Fiq's provider-side HTTP 503 maintenance response.
- Declaring OpenAI Codex or Copilot broken from the current probe's HTTP 400 responses; their endpoint/auth contracts require a separate investigation.
- Credential rotation, token replacement, OAuth refresh, or `.env` content changes.
- Changes to `/goal`, delegation budgets, WhatsApp group policy, or unrelated provider adapters.
- Release, push, deploy, gateway reload, or channel E2E before the Phase 3/owner gate.

## Further Notes and Evidence Ledger

- `LIVE-VERIFIED`: `/home/ubuntu/.hermes/gateway_state.json` served `default, ovis2`; `ovis2:telegram` was owned by default PID `1834884`.
- `LIVE-VERIFIED`: `/home/ubuntu/.hermes/profiles/bot_2/gateway_state.json` showed the standalone child retrying on `telegram-bot-token_lock`.
- `LIVE-VERIFIED`: root `gateway.log` recorded missing `ovis2` fallback and `No inference provider configured`.
- `LIVE-VERIFIED`: root `state.db` `gateway_routing` contained `agent:ovis2:telegram:dm:679729206`; the `sessions` query returned zero `agent:ovis2:*` rows.
- `LIVE-VERIFIED`: zero-token provider probes were captured at `/tmp/provider-probe-default-20260911.txt`, `/tmp/provider-probe-bot_2-20260911.txt`, and `/tmp/provider-probe-ovis2-20260911.txt`.
- `LOCAL-VERIFIED`: `profiles_to_serve()` only serves valid on-disk profiles allowed by `gateway.multiplex_profile_allowlist` and warns on missing allowlist entries.
- `LOCAL-VERIFIED`: `tests/gateway/test_profile_resolution.py` currently asserts the unsafe global fallback for a missing explicit profile; this is the regression target.
