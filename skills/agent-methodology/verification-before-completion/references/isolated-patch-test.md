# Isolated patch-test harness (scripts that hardcode `Path.home()`)

Use this when you need to PROVE a patch to a stateful script works, without
touching the live `~/.hermes` state files. Verified 2026-07-10.

## Why
Scripts like `med_confirm.py` / `chain_calc.py` build their paths as
`Path.home() / ".hermes" / ...`. A `--dry-run` flag may not exercise the code
path you changed, and copying state back and forth risks contaminating prod.
Setting `HOME` to a temp dir makes the script write ONLY to the temp tree.

## Recipe
```bash
export HOME=/tmp/medtest/home
mkdir -p "$HOME/.hermes/scripts"
# Copy the script under test + any lazy-imported deps it needs
cp /home/ubuntu/.hermes/scripts/med_confirm.py "$HOME/.hermes/scripts/"
cp /home/ubuntu/.hermes/scripts/med_resolve.py "$HOME/.hermes/scripts/"
cp /home/ubuntu/.hermes/scripts/med_supply.py  "$HOME/.hermes/scripts/"
cp /home/ubuntu/.hermes/med-schedule.json "$HOME/.hermes/"
# Start from a clean/minimal state (or copy the real one if you need real data)
printf '{"meds":{}}' > "$HOME/.hermes/med-status.json"

# Apply your patch to the COPY (never the original). Example: a python
# script that does str.replace(old, new) for each hunk, asserting count==1.
python3 /tmp/apply_patch.py

# Syntax check
python3 -m py_compile "$HOME/.hermes/scripts/med_confirm.py" && echo COMPILE_OK

# Run real tests — prod is untouched because HOME points at /tmp
export HOME=/tmp/medtest/home
export MED_AUDIT_LOG=/tmp/medtest/audit.log   # optional: keep logs out of prod too
python3 "$HOME/.hermes/scripts/med_confirm.py" A --at 20:00 --source-text test
python3 "$HOME/.hermes/scripts/med_confirm.py" A --at 06:30 --source-text "dah makan A 6.30am" --caller agent
# ... assert outcomes ...
```

## Gotchas
- Copy EVERY lazy-imported module the script pulls in (e.g. `med_resolve`,
  `med_supply`) or the test crashes on import inside the function.
- If the patch touches `main()` arg parsing, test BOTH the `--at` branch and the
  default-confirm branch — and any new flag (e.g. `--caller`) must be skipped in
  the arg loop or its value gets misread as a drug fragment.
- `Path.home()` respects `$HOME` on Linux/macOS. On Windows it's `%USERPROFILE%`.
- After passing, `rm -rf /tmp/medtest` — the temp tree is disposable.

## Concrete result (2026-07-10)
Patched `med_confirm.py` with 11 hunks (time validation + `--source-text`
requirement + per-write audit log). 7 tests, all pass. Live
`~/.hermes/med-status.json` confirmed unchanged (A still showed its corrected
06:50, not the 20:00 the patch would otherwise have rejected). The patch draft
lives in `med-tracker/references/med-confirm-at-validation-fix.md`.
