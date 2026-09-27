# 02 — Sanitize Runtime Supply Data in med-supply.json

**What to build:** Create an atomic backup of `~/.hermes/med-supply.json` and sanitize all drug entries to `current: null`, removing all fabricated pill count values and notes.

**Blocked by:** 01 — Decouple Supply Decrement & Alerts from med_confirm.py

**Status:** ready-for-agent

- [ ] Take pre-change timestamped backup of `~/.hermes/med-supply.json`
- [ ] Set `current: null` for `levetiracetam_b` and ensure all other drugs remain `current: null`
- [ ] Scrub fabricated text `"Still sufficient (95 pills)."` from notes, replacing with accurate restock note
- [ ] Verify `python3 med_supply.py --check` reports zero out-of-stock or low warnings
