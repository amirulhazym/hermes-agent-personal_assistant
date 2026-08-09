# Auto-Confirm Hook: Input Pattern Reference

**File**: `~/.hermes/hooks/med-auto-confirm/handler.py`
**Resolve script**: `~/.hermes/scripts/med_confirm.py`
**Reminder generator**: `~/.hermes/scripts/chain_calc.py`

## Ambiguous verb: "makan" (2026-07-22)
- Bare `dah makan 6am` / `thanks remind` alone = **ASK** (food vs ubat). Do not auto-confirm. Do not declare "bukan ubat".
- `dah makan A` / `Akurit` / `ubat` / named drug = confirm.
- `dah ambil 6am` leans med (`ambil` usually = take med) but if still unsure, ask once.
- User attitude: unclear → clarify for accurate log, never silent assume. Full rule: `references/makan-ambiguity-ask-dont-assume.md`.

## Known Input Formats (all should work)

| User says | What happens | Notes |
|-----------|-------------|-------|
| `dah makan A akurit` | Logs akurit_2 for slot A via drug match | Bare "akurit" now matches via `\bakurit\b` fallback |
| `dah makan A pyridoxine` | Logs pyridoxine for slot A | Direct match |
| `Done akurit+pyridoxine jam 6.45am` | Logs BOTH akurit_2 + pyridoxine | The `+` connector is handled by bare `\bakurit\b` pattern |
| `dah makan A` | Confirms ALL drugs in slot A | Bare letter fallback (near "dah makan") |
| `C dah selesai` | Confirms ALL drugs in slot C | Bare letter fallback with completion word after |
| `confirm B` | Confirms ALL drugs in slot B | Bare letter near "confirm" |
| `dah makan slot A` | Confirms ALL drugs in slot A | Explicit "slot X" token |

## Input Pattern Matching Priority

The `_resolve_slot_drug()` function checks in this order:

1. **DRUG_MAP** — regex patterns for specific drug names (akurit, pyridoxine, etc.)
   - Specific pattern first: `\bakurit[- ]?(2|4)\b` (catches "akurit-2", "akurit 2")
   - Bare fallback: `\bakurit\b` (catches "akurit+pyridoxine", bare "akurit")
2. **"slot X" token** — explicit `slot A`, `slot C` etc.
3. **Bare letter + completion word** — standalone A-E letter within ~30 chars of a completion signal
   - Completion signals: `dah makan`, `sudah makan`, `done`, `confirm`, `selesai`, `siap`, etc.
   - This allows "dah makan A" while rejecting "Apa khabar"

## False Positive Prevention

The bare letter fallback (step 3) only activates when `is_med_confirmation()` first passes — i.e., the message must contain a completion phrase. Messages like "Apa khabar" or "Bagi la" never reach step 3 because they lack a completion word.

## Bug History: Partial Entry Blocking

**2026-07-15 (Fixed)**: `_already_logged()` returned True for both "completed" AND "partial" entries. This meant after a partial confirmation (e.g., only pyridoxine logged from "akurit+pyridoxine"), any follow-up "dah makan A akurit" was silently skipped because the entry already had `drugs: {...}`. Fix: `_already_logged` now only blocks on "completed". Partial entries allow additional drug-level confirmations.

## Bug History: Reminder Text Mismatch

**2026-07-15 (Fixed)**: The partial-reminder text in `chain_calc.py` said `Reply je 'dah makan A <nama_ubat>'` but this format couldn't be processed by the auto-confirm hook (bare "akurit" didn't match regex, bare "A" was blocked by G-1). Fix: reminder text now dynamically uses the first pending drug name, and the hook now handles both bare akurit and bare letter patterns.

## Links

- DRUG_MAP: handler.py lines 62-76
- `_resolve_slot_drug()`: handler.py lines 120-170
- `_already_logged()`: handler.py lines 173-201
- Reminder generator: `chain_calc.py` lines 752-761
