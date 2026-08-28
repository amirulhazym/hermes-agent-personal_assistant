# Cron-Trace Debugging Pattern

Use when a cron job with `no_agent=true` fires too frequently or at unexpected
times. The cron output directory is your first and best data source.

## Step 1: Fingerprint firing pattern from output file sizes

Every cron tick writes an output file to `~/.hermes/cron/output/<job_id>/`.
File sizes tell you immediately which ticks produced output:

```bash
ls -la cron/output/c97c00f2fb46/  # med monitor example
```

- **166 bytes** = silent (empty output) — script had nothing to report
- **>166 bytes** = delivered content — a reminder fired

Scan the listing visually: a pattern like `312, 166, 166, 312, 166, 312` tells you
reminders fired at `:15` not `:00/:30` — a cooldown boundary symptom.

## Step 2: Read actual fired content

Read just the non-silent files (the ones >166 bytes):

```bash
cat cron/output/c97c00f2fb46/2026-07-17_*.md | grep -A5 '^⚠️'  # quick scan
```

This tells you:
- What message was delivered
- Whether it came from `chain_llm.py` (LLM-generated, varied text) or
  `chain_calc.py --template` (hardcoded, same template every time)
- Whether content changed over time (escalation pattern)

## Step 3: Identify the delivery source

Compare written output against the known templates in `chain_calc.py`
`generate_reminder()`. If text varies beyond the template parameters, it came from
`chain_llm.py` (API call). If text matches the template exactly, the LLM failed
and `chain_monitor.sh` fell back to template.

## Step 4: Trace the decision path

Follow the code: `chain_monitor.sh` → calls `chain_calc.py --next` (step 1),
then `chain_llm.py` or `chain_calc.py --template` (step 5).

In `--next`, the `is_within_cooldown()` function is the gatekeeper — it's where
boundary bugs live.

## Step 5: Reproduce the boundary math

Python prototype:
```python
# Simulate the tick pattern
last_time = "13:15"  # when last reminder fired
cooldown = 30        # minutes
for tick in ["14:00", "14:15", "14:30", "14:45", "15:00"]:
    h, m = map(int, last_time.split(':'))
    last_min = h*60 + m
    h2, m2 = map(int, tick.split(':'))
    now_min = h2*60 + m2
    elapsed = now_min - last_min
    print(f"{tick}: elapsed={elapsed}, cooldown={cooldown}, "
          f"within={elapsed < cooldown}")  # < is the BUG — should be <=
```

## Concrete case: 2026-07-17 CC spam

**Symptom:** 5 reminders for CC in ~3h (13:15, 14:15, 14:45, 15:15)
**Fingerprint:** Output file sizes showed 312 bytes at `:15` ticks, 166 at `:00/:30`

**Root cause chain:**
1. Cron every 15 min (`*/15 5-22 * * *`)
2. At count=3+, cooldown drops to 30 min (too aggressive for supplements)
3. Boundary bug: `mins_since < interval` — at `30 < 30 = False` → fires
4. Combined effect: 2 extra ticks per hour at boundary

**Fixes applied** (see `med-tracker/references/cooldown-bugs-20260717.md`):
- `<=` instead of `<` in cooldown check
- Partial-slot cooldown flat 120 min (no escalation for supplements)
- Tone fix for partial reminders

## Pitfalls
- Use file size, not modification time, as the first signal — mtime drifts with
  delivery delays, file size is instant.
- Don't confuse silent (166 bytes) with "no run" — every cron tick writes a wrapper.
  A silent file means the script produced empty stdout.
- For `no_agent=true` jobs, the output IS the script's stdout verbatim — no LLM
  intervention. This makes content analysis deterministic.
