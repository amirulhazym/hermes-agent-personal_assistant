# Chat-Edge Secret Handoff

Use this reference when a user wants to deliver an API key or other credential through a chat platform while keeping the plaintext out of the LLM context.

## Security verdicts

Keep these claims separate:

- **Model-blind:** the plaintext is intercepted before message extraction/queueing and is not included in the Python event, prompt, transcript, tool output, or agent reply.
- **Filesystem-blind:** the plaintext is not persisted in `.env`, config, logs, cache, or ordinary message storage.
- **Runtime-blind:** the credential is not held by the gateway/model process. This normally requires a separate broker process.
- **OS-blind:** the credential is inaccessible to same-user tools, debuggers, crash dumps, and privileged processes. Do not claim this unless OS identities, permissions, and tool sandboxing prove it.

A direct `.env` writer can provide the first two properties, but it is not a complete isolation boundary when the model's terminal/file tools run under the same OS user. Label it **PARTIAL**.

## Strongest practical pattern for a Node bridge + Python gateway

```text
Chat message
  -> edge bridge control lane
  -> exact sender + exact chat authorization
  -> one-time challenge/reference + bounded TTL
  -> consume control/malformed/unauthorized messages
  -> bridge-only stdin/pipe handoff
  -> memory-only credential broker
  -> loopback OpenAI-compatible proxy
  -> upstream provider

Normal messages only:
  edge bridge -> extract -> queue -> Python gateway -> LLM
```

Required properties:

1. Run the control lane before media/OCR, message-store writes, generic extraction, and queueing.
2. Bind the challenge to the exact authorized sender and chat; do not use a broad "any allowed user" rule for a group secret.
3. Use a two-step flow: explicit `begin`, then a one-use secret command containing the displayed reference. A marker ensures an expired/replayed key-looking message is still consumed and rejected rather than falling into the model path.
4. Enforce TTL, one-use state, message-ID replay suppression, length/character validation, and cancellation.
5. Consume malformed and unauthorized reserved-prefix messages fail-closed. Never forward them for the model to interpret.
6. Send the key only over a local pipe/stdin or protected IPC channel. Do not put it in argv, environment, config, `.env`, URL, stdout, stderr, or acknowledgement text.
7. Keep the broker's environment minimal and exclude all upstream credential variables.
8. Let Hermes use a non-secret local broker token. The broker injects the upstream bearer key and never returns it.
9. Filter response headers and stream bodies so an upstream error/echo cannot disclose the key back to the model. Test a sentinel split across stream chunks.
10. Treat broker restart as credential loss. Require re-entry; do not silently persist a key to make restart convenient.

If absolute same-user isolation is required, stop and state the architecture gap: add a separate OS service identity plus a tool sandbox/permission boundary. A same-user memory broker is stronger than `.env` storage but is not proof against a malicious same-user process or privileged inspection.

## Verification ladder

Run these in order and keep the evidence layers separate:

1. Prototype the capture and broker in `/tmp`; never start with a real credential.
2. Unit-test ordinary text, unauthorized/malformed commands, wrong reference, expiry, cancellation, duplicate message ID, invalid key characters, and persistence failure.
3. Use a fake upstream that records the received Authorization header. Send a synthetic sentinel and assert:
   - upstream receives the sentinel;
   - capture replies, broker stdout/stderr, client response, headers, and files do not contain it;
   - no-key requests fail closed;
   - wrong local token is rejected;
   - response redaction handles a sentinel split across chunks.
4. Run syntax/compile checks and a static ordering assertion proving capture occurs before extraction and queueing.
5. Resolve the actual Hermes provider config and prove the provider points to the local broker with no upstream `api_key_env` mapping.
6. Compare candidate hash to the live bridge health hash. A candidate on disk is not loaded runtime.
7. Obtain explicit approval before restarting the live bridge. Do not request the real key before the candidate hash is live and the broker health endpoint is observed.
8. After live loading, send only the non-secret challenge first. Confirm the sanitized acknowledgement. Only then request the real key through the control protocol.
9. Verify provider `/models` and a minimal inference separately. Report component, provider, runtime, and user-visible delivery evidence independently.

## Status vocabulary

- **DESIGN FEASIBLE — UNTESTED:** architecture only.
- **CANDIDATE TESTED:** isolated synthetic tests pass; not live-loaded.
- **LIVE LOADED:** runtime hash/health proves the candidate process loaded; no real key or provider call yet.
- **PROVIDER VERIFIED:** real key loaded into the broker and live provider request returned the expected response shape.
- **END-TO-END PROVEN:** the real WhatsApp challenge, key capture, provider request, gateway selection, and user-visible response were exercised.

Never collapse these into "secure setup done".

## Failure pattern to preserve

A stream-redaction implementation that passes unit reasoning can still break HTTP delivery. In one test, passing the Transform encoding label (`"buffer"`) to `Buffer.toString()` caused `ECONNRESET`/socket hang-up. The fix was explicit `chunk.toString('utf8')`, followed by rerunning the full focused suite. Preserve the failed first attempt and the corrected pass separately.

## Sources / further reading

- Hermes provider configuration: https://hermes-agent.nousresearch.com/docs
- APIMaster API documentation: https://apimaster.ai/docs/en/api
- APIMaster OpenAI-compatible guide: https://apimaster.ai/docs/en/guides/openai-compatible-api
