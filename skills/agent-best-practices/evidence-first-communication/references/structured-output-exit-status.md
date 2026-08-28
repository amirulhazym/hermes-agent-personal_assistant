# Structured Output vs Process Exit Status

## Pattern-Key

`structured-payload-over-exit-code`

## Use when

A command emits JSON or another structured verdict but returns a non-zero process status, especially for query/read-back commands and wrapper scripts.

## Evidence rule

Keep both signals. The process status describes the wrapper/process outcome; the payload describes the operation's domain result. Do not discard either, and do not let a generic `exit != 0` rule overwrite an explicit payload verdict.

## Reproduced medication case — 2026-08-16

Command:

```text
python3 ~/.hermes/scripts/med_confirm.py --check A
```

Raw payload:

```json
{
  "med": "A",
  "date": "2026-08-16",
  "overall": "completed",
  "confirmed": true,
  "drugs": {
    "akurit_2": {"status": "taken", "time": "06:00"},
    "pyridoxine": {"status": "taken", "time": "06:00"}
  }
}
```

Observed process result: `exit_code=1`.

The live `med_confirm.py` `main()` returns `0` only when `result.get("ok")` is truthy. The `--check` payload does not include `ok`, so a correct read-back can still produce exit `1`. This is a wrapper-contract mismatch, not evidence that Slot A was unconfirmed.

## Reproduced drug-level case — 2026-08-18

Command:

```text
python3 ~/.hermes/scripts/med_confirm.py --check E levetiracetam_e
```

Raw payload:

```json
{
  "med": "E",
  "drug": "levetiracetam_e",
  "date": "2026-08-18",
  "status": "taken",
  "time": "21:25"
}
```

Observed process result: `exit_code=1`. The payload had no `ok` key, but its drug-level fields directly established the read-back state.

A separate capability probe also returned `Unknown option: --help` with `exit_code=1`; this is an unsupported CLI help path, not a confirmation failure. Usage is documented in the script docstring/no-argument output.

## Safe handling

1. Capture stdout/stderr and the exit status even when the process is non-zero.
2. Parse the payload and use operation-specific fields such as `overall`, `confirmed`, `status`, `time`, and `error`.
3. For a successful read-back, report both facts: `payload: confirmed=true; process exit: 1 (query wrapper)`.
4. Do not use `query && next_command`; a valid query result may stop the chain. Use `;`, explicit status handling, or a parser that knows the command contract.
5. Do not retry or repeat a state-changing write solely because a subsequent query returned a misleading non-zero status.
6. If the payload is missing, malformed, contradictory, or lacks a field that can establish the operation's result, classify it as `UNVERIFIED` and investigate. This pattern is not permission to ignore non-zero exits generally.
