# med-status.json Stale-Data Investigation (2026-07-09)

Verified trace recipe for when `med-status.json` shows a drug marked "taken" at a
time the user did NOT report today. Root cause this session: a PRIOR session's mistaken
`confirm_slot C --at 20:00` left stale "20:00" data that persisted into the new
day because `med_confirm.py` has NO day-boundary reset (unlike `chain-state.json`).

## Symptom
- `--status` shows e.g. `calcium: taken 20:00` for today, but user says
  "mana datang aku makan cc jam 20:00? gila ke."
- Data pre-exists the current chat session (user hadn't confirmed it).

## Investigation path (exhaust BEFORE asking user)
```bash
# 1. File mtime timeline — which backup holds the bad data?
stat -c '%y %n' ~/.hermes/med-status.json*

# 2. Diff each backup's drugs for the slot in question
python3 -c "
import json
for f in ['med-status.json.bak1','med-status.json.bak2','med-status.json.bak3']:
    d=json.load(open(f))
    print(f, d['meds']['C'].get('2026-07-09',{}).get('drugs',{}))
"

# 3. Cron jobs that could write state
cronjob action=list   # look for no_agent scripts touching med-status

# 4. Script source — hardcode or confirm_slot call?
grep -rn "20:00\|confirm_slot\|med_confirm" ~/.hermes/scripts/*.py

# 5. Live session DB (NOTE: in-flight sessions may not be flushed — tool_calls
#    column can be empty for today even though commands ran)
python3 -c "
import sqlite3
con=sqlite3.connect('/home/ubuntu/.hermes/state.db')
cur=con.cursor()
cur.execute(\"SELECT timestamp,role,substr(content,1,200) FROM messages WHERE timestamp LIKE '2026-07-09%' AND content LIKE '%med_confirm%'\")
for r in cur.fetchall(): print(r)
"

# 6. Gateway / error logs for cron execution traces
grep -n "med_confirm\|chain_monitor" ~/.hermes/logs/gateway.log ~/.hermes/logs/errors.log
```

## Verified exclusions (this session)
- bash_history: empty (Hermes uses own shell, not persisted to .bash_history)
- agent.log: logs WARNINGs only, not tool commands
- state.db: today's session NOT yet persisted at time of trace (0 med_confirm hits)
- chain-state.json: no C confirm record
- cron list: no med_confirm caller; chain_monitor is READ-ONLY on med-status
- med_report.py / chain_calc.py: read-only on med-status drugs
- No crontab entry; no script hardcodes "20:00" drug writes

## Conclusion pattern
If steps 1-6 all return empty/not-found for the bad value, the data is
STALE from a prior session (carried via missing day-boundary reset). Report:
"I traced all logs/scripts/state and found no write source for X today — this is
likely stale data from a prior session, not a live action." Do NOT ask the user
to self-incriminate ("awak pernah ke...").

## Fix (agent-side, until code patched)
1. `med_confirm.py --reset <slot> <drug_id>` — clears the single bad drug.
2. Do NOT use slot-level confirm to "fix" (re-corrupts per Bug #5).
3. Re-log only what user actually confirms with `confirm_drug` + `--at`.
