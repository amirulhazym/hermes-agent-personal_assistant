# Gemini 3.8 Flash R6-B3 Guardrail Plugin (V1)

## Status
`ACCEPTED PRODUCTION BASELINE`

## Exact Target

```yaml
model: gemini-3.8-flash
provider: antigravity
```

Strictly restricted to this exact tuple (`model == "gemini-3.8-flash"` and `provider == "antigravity"`).  
All other models (e.g. `gemini-3.1-pro`, `gpt-5.6-luna-900k`, `claude-3-7-sonnet`) and all other provider labels (including `google-antigravity`) remain completely untouched and unaugmented.

## Purpose

V1 delivers deterministic, non-intrusive prompt steering via the `llm_request` plugin middleware to improve agentic execution reliability on Gemini 3.8 Flash without touching SOUL.md or persistent memory:

- **Evidence boundary discipline**: State only what available evidence actually establishes; label unknown state explicitly.
- **Stop condition handling**: Treat explicit source termination markers as authoritative without unneeded calls.
- **Scope discipline**: Prioritize task-local evidence first; do not replace missing data with unrelated ambient host discovery.
- **Proportional verification**: Require every extra tool call to resolve a specific remaining uncertainty or acceptance condition.
- **Factual completion check**: Verify factual claims before finalizing; qualify or remove unsupported assertions.
- **Dependency-aware tool sequencing**: Do not pre-batch dependent tool calls before prerequisite observation.
- **Minimal temporal compliance**: Enforce minimal live time lookup only when explicitly demanded by higher-priority instructions.

*Boundary Note:* V1 improves execution discipline and tool proportionality. It does NOT claim to upgrade raw model reasoning capabilities or prove Luna-level agentic parity.

## Accepted Hashes

Tracked files in `plugins/gemini-r6b3-guardrail/` match the accepted production baseline:

- `__init__.py`: `1f4cbd2614bf92184f0cab9c81e69436ad11d2b809022f6652f4ee221817514c`
- `plugin.yaml`: `f455d9b84c6a080302310db5368dd9951bbe0b0ae680097fe2e2b534dd41d190`
- `r6-b3-guardrail.txt`: `950601ceebecdee13b94c9791cd0f212d03ab260cda7bdc9ba1970ecd47edbed`

## Runtime Location

Live installed location:

```text
/home/ubuntu/.hermes/plugins/gemini-r6b3-guardrail/
```

## Activation State

In production, the plugin is activated via standard Hermes plugin configuration:

- Present under `~/.hermes/plugins/gemini-r6b3-guardrail/`
- Listed in `~/.hermes/config.yaml` under `plugins.enabled: ["gemini-r6b3-guardrail", ...]`
- Loaded into the running gateway process

## Normal Recovery Procedure

To restore the accepted V1 baseline on a fresh or broken environment:

1. Copy the tracked repository plugin directory to the user plugin directory:
   ```bash
   cp -r plugins/gemini-r6b3-guardrail /home/ubuntu/.hermes/plugins/
   ```
2. Verify that the files match the accepted SHA-256 hashes:
   ```bash
   sha256sum /home/ubuntu/.hermes/plugins/gemini-r6b3-guardrail/*
   ```
3. Enable the plugin via supported Hermes CLI:
   ```bash
   hermes plugins enable gemini-r6b3-guardrail
   ```
4. Restart or reload the gateway using the supported service/process lifecycle commands.
5. Verify that `gemini-3.8-flash` on `antigravity` receives the R6-B3 prompt block while other models remain unaffected.

## Rollback Procedure

To roll back or disable the V1 guardrail:

1. Disable the plugin via Hermes CLI:
   ```bash
   hermes plugins disable gemini-r6b3-guardrail
   ```
2. (Optional) Remove the runtime directory:
   ```bash
   rm -rf /home/ubuntu/.hermes/plugins/gemini-r6b3-guardrail
   ```
3. Restart or reload the gateway.
4. Verify that requests to `gemini-3.8-flash` on `antigravity` no longer receive the R6-B3 block.

## Evidence Provenance

The empirical validation and production activation of V1 are documented in:

- **Round 7B.1 Hardening & Deterministic Testing:**  
  `/home/ubuntu/.hermes/evaluations/R1-G38-HERMES-v1.3-FROZEN/integration/round7b1-20260910-182201/report/round7b1-r6b3-middleware-hardening-report.md`
- **Round 7C Controlled Live Activation:**  
  `/home/ubuntu/.hermes/evaluations/R1-G38-HERMES-v1.3-FROZEN/integration/round7c-20260910-185529/report/round7c-controlled-live-activation-report.md`

*(Note: Evaluation and run artifacts reside in the host evaluation directory and are not tracked in Git.)*
