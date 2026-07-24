import json
import os
import time as _time

TRACE_PATH = os.path.expanduser("~/.hermes/logs/med_chain_trace.jsonl")


def log_trace(run_id, input_slots, result, validator_result=None):
    os.makedirs(os.path.dirname(TRACE_PATH), exist_ok=True)
    row = {
        "ts": _time.time(),
        "run_id": run_id,
        "input": {k: str(v) for k, v in input_slots.items()},
        "slots": {k: str(v) for k, v in result.get("slots", {}).items()},
        "untouched": result.get("untouched"),
        "rules_fired": result.get("rules_fired"),
        "conflicts": result.get("conflicts"),
        "validator_result": validator_result,
    }
    with open(TRACE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row
