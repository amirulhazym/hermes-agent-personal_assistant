#!/usr/bin/env python3
"""Switch session to Caveman Global Default Confirmed. Run as standalone process."""
import json, sqlite3, time, subprocess, sys, os

# 1. Stop gateway first
subprocess.run(["systemctl", "--user", "stop", "hermes-gateway"], check=True)
time.sleep(1)

# 2. Modify sessions.json
with open(os.path.expanduser("~/.hermes/sessions/sessions.json")) as f:
    d = json.load(f)
for k in d:
    if "whatsapp:dm" in k and "601166557800" in k:
        d[k]["session_id"] = "20260727_180853_f758b16a"
        print(f"Updated: {k} -> {d[k]['session_id']}")
with open(os.path.expanduser("~/.hermes/sessions/sessions.json"), "w") as f:
    json.dump(d, f, indent=2)

# 3. Modify state.db
db = sqlite3.connect(os.path.expanduser("~/.hermes/state.db"))
db.execute("UPDATE sessions SET ended_at=?, end_reason=? WHERE id=? AND ended_at IS NULL",
    (time.time(), "session_switch", "20260728_084152_61cef7b6"))
db.execute("UPDATE sessions SET ended_at=NULL, end_reason=NULL WHERE id=?",
    ("20260727_180853_f758b16a",))
db.commit()
db.close()
print("State.db updated")

# 4. Start gateway
subprocess.run(["systemctl", "--user", "start", "hermes-gateway"], check=True)
print("Gateway started with caveman session routing.")
