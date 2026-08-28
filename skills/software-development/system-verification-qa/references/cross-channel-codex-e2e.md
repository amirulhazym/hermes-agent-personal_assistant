# Cross-channel Codex E2E evidence pattern

## Scope

Reusable evidence pattern from the 31 Jul 2026 WhatsApp recovery test. This is a reference transcript, not a claim that future runs have the same timestamps or session IDs.

## Proven sequence

- WhatsApp inbound: `2026-07-31 10:55:16.899` — `inbound message: platform=whatsapp`.
- Runtime selection: `turn_context` recorded `model=gpt-5.6-luna provider=openai-codex platform=whatsapp`.
- Upstream calls: calls #1–#4 completed before compression; calls #5–#6 completed after compression. Each had `OpenAI client closed (request_complete)` followed by the matching `API call #N` line and no auth failure.
- Compression boundary: `context compression started ... messages=149 tokens=~151,830`.
- Final turn: `Turn ended: reason=text_response(finish_reason=stop) model=gpt-5.6-luna api_calls=6/100`.
- Gateway response: `response ready: platform=whatsapp ... response=440 chars`.
- Adapter acceptance: structured event `outbound_adapter_result` had `status=success`, `adapter_accepted=true`, `message_id=3EB0835A845F287A2D100E`, `destination_observed=null`.

## Interpretation

This proves the path through WhatsApp inbound, Hermes routing, OpenAI Codex inference, response assembly, and WhatsApp adapter acceptance. It does **not** prove recipient-side delivered/read state because the observability event explicitly records `destination_observed=null`.

## Diagnostic lesson

A multi-minute delay during a large-context turn is not evidence of token invalidation. Check for context compression and follow the post-compression session. Do not classify a run from the intermediate `Working`/compaction message; wait for `Turn ended`, `response ready`, and the structured adapter result.

## Required reporting fields

| Boundary | Required evidence |
|---|---|
| Inbound | platform + timestamp + message/session correlation |
| Routing | exact provider + model from turn context or agent init |
| Provider | request completion + API-call line |
| Agent | turn-ended line with finish reason |
| Gateway | response-ready line |
| Adapter | structured success + acceptance + message ID |
| Destination | explicit receipt event or user confirmation; otherwise unverified |
