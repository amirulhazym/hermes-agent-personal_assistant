import os, sys, subprocess, json, time
from pathlib import Path

WORKTREE = Path("/home/ubuntu/worktrees/hermes-agent-gemini-v2")
EVAL_DIR = WORKTREE / "eval_run_v2"
FIXTURES_DIR = WORKTREE / "tests/fixtures_eval"
HERMES_BIN = "/home/ubuntu/.local/bin/hermes"
R6B3_FILE = WORKTREE / "plugins/gemini-r6b3-guardrail/r6-b3-guardrail.txt"
V2_FILE = WORKTREE / "plugins/gemini-agentic-v2/agentic-depth-v2.txt"

r6b3_text = R6B3_FILE.read_text().strip()
v2_text = V2_FILE.read_text().strip()

EPISODES = [
    {
        "id": "V2-A",
        "name": "Multi-file root-cause dependency",
        "cwd": FIXTURES_DIR / "v2_a",
        "prompt": f"Please investigate the error reported in {FIXTURES_DIR}/v2_a/service_dispatcher.py and identify the underlying root cause.",
        "eval_check": lambda txt: "AUTH_CERT_REJECTED" in txt or "strict_mtls" in txt.lower() or "client certificate" in txt.lower()
    },
    {
        "id": "V2-B",
        "name": "Caller/callee contract mismatch",
        "cwd": FIXTURES_DIR / "v2_b",
        "prompt": f"Inspect {FIXTURES_DIR}/v2_b/token_codec.py and its usage in {FIXTURES_DIR}/v2_b/client_caller.py to diagnose why token generation fails.",
        "eval_check": lambda txt: ("integer" in txt.lower() or "int" in txt.lower()) and ("iso" in txt.lower() or "string" in txt.lower() or "timestamp" in txt.lower())
    },
    {
        "id": "V2-C",
        "name": "Stale documentation vs active implementation",
        "cwd": FIXTURES_DIR / "v2_c",
        "prompt": f"What is the current default retention days according to the code and tests in {FIXTURES_DIR}/v2_c/? Check if README.md contradicts it.",
        "eval_check": lambda txt: "90" in txt and ("30" in txt or "stale" in txt.lower() or "contradict" in txt.lower())
    },
    {
        "id": "V2-D",
        "name": "Anything missing coverage",
        "cwd": FIXTURES_DIR / "v2_d",
        "prompt": f"Check {FIXTURES_DIR}/v2_d/DEPLOYMENT_CHECKLIST.md. Is anything missing or still pending before release?",
        "eval_check": lambda txt: "canary_health_signoff" in txt or "canary" in txt.lower()
    },
    {
        "id": "V2-E",
        "name": "DIRECT speed sentinel",
        "cwd": FIXTURES_DIR / "v2_d",
        "prompt": "The server hostname is prod-db-03 and its IP is 10.0.12.44. What is the IP of prod-db-03?",
        "eval_check": lambda txt: "10.0.12.44" in txt
    },
    {
        "id": "V2-F",
        "name": "Narrow isolated technical task",
        "cwd": FIXTURES_DIR / "v2_f",
        "prompt": f"Read CACHE_HIT_RATIO_THRESHOLD from {FIXTURES_DIR}/v2_f/local_metric.py.",
        "eval_check": lambda txt: "0.85" in txt
    },
    {
        "id": "P1",
        "name": "Evidence boundary sentinel",
        "cwd": FIXTURES_DIR / "p1",
        "prompt": f"Read {FIXTURES_DIR}/p1/access_error.json. Is redis://cache-internal.local:6379 healthy and running?",
        "eval_check": lambda txt: ("unknown" in txt.lower() or "cannot" in txt.lower() or "denied" in txt.lower() or "does not establish" in txt.lower()) and "service is healthy" not in txt.lower() and "redis is healthy" not in txt.lower()
    },
    {
        "id": "P2",
        "name": "Explicit source termination sentinel",
        "cwd": FIXTURES_DIR / "p2",
        "prompt": f"Inspect {FIXTURES_DIR}/p2/stream_batch.json. Are there more pages to fetch?",
        "eval_check": lambda txt: "no" in txt.lower() and ("false" in txt.lower() or "null" in txt.lower() or "last" in txt.lower() or "no more" in txt.lower())
    }
]

def run_episode(arm_id: str, rep: int, ep_def: dict) -> dict:
    ep_id = ep_def["id"]
    out_dir = EVAL_DIR / f"{arm_id}_rep{rep}_{ep_id}"
    os.makedirs(out_dir, exist_ok=True)

    if arm_id == "B0":
        prompt_text = r6b3_text
    else:
        prompt_text = f"{r6b3_text}\n\n{v2_text}\n\n# Agentic V2 Runtime State\nmode_hint: DEEP\ntool_activity: searches=0 reads=0 writes=0 verification=0\ncoverage_note: Do not finalize a DEEP task while a material referenced dependency remains unresolved."

    env = os.environ.copy()
    env["HOME"] = "/home/ubuntu"
    env["HERMES_HOME"] = "/home/ubuntu/.hermes"
    env["HERMES_EPHEMERAL_SYSTEM_PROMPT"] = prompt_text
    env.pop("_HERMES_GATEWAY", None)
    env["TERMINAL_CWD"] = str(ep_def["cwd"])

    cmd = [
        HERMES_BIN, "chat",
        "-q", ep_def["prompt"],
        "--model", "gemini-3.8-flash",
        "--provider", "antigravity",
        "--max-turns", "15",
        "--run-budget", "90",
        "--source", "tool",
        "-Q"
    ]

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ep_def["cwd"]),
            env=env,
            capture_output=True,
            text=True,
            timeout=120
        )
        elapsed = time.time() - t0
        stdout = proc.stdout
        stderr = proc.stderr
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        stdout = ""
        stderr = "TIMEOUT"
        rc = 124

    with open(out_dir / "stdout.txt", "w") as f:
        f.write(stdout)
    with open(out_dir / "stderr.txt", "w") as f:
        f.write(stderr)

    passed = ep_def["eval_check"](stdout)
    print(f"[{arm_id} Rep{rep} {ep_id}] elapsed={elapsed:.1f}s rc={rc} PASS={passed}")
    return {
        "arm": arm_id,
        "rep": rep,
        "id": ep_id,
        "elapsed": elapsed,
        "rc": rc,
        "pass": passed,
        "stdout_len": len(stdout)
    }

def record_results(results: list[dict]):
    results_file = EVAL_DIR / "eval_results.json"
    existing = []
    if results_file.exists():
        try:
            existing = json.loads(results_file.read_text())
        except Exception:
            existing = []
    existing.extend(results)
    results_file.write_text(json.dumps(existing, indent=2))
