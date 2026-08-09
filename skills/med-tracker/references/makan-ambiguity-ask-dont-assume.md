# "Makan" Ambiguity — Ask, Don't Assume (2026-07-22)

Malay **"makan"** = food OR medicine. When message is unclear, **ASK once** — never silently assume food, never silently auto-log med.

## Failure chain (2026-07-22)
```
User (after Slot A reminder): "Dah makan 6am, thanks remind."
Agent assumed FOOD only → replied "bukan ubat" → delayed log
User furious: meant Slot A med at 06:00.
User correction: "Patutnya kau tanya, bukan assume. Tu behavior kau kalau tak tahu."
```

## Root cause
Agent filled ambiguity with a confident assumption (food) instead of one clarifying question. Wrong attitude for unclear input.

## Attitude (user-explicit, 2026-07-22)
- If tak tahu / tak clear / tak jelas → **ask**, not assume from vibes/context alone
- Reasoning chain: "makan?" → "makan makanan ke makan ubat?" → "ni timing slot ubat ke?"
- Correct response shape when still ambiguous:

> "Boss 'makan' yg boss maksudkan tu makan ubat kan? Ke boss baru lepas makan makanan? Sorry boss, saya nak confirmkan sebab saya nak log accurately."

- After user clarifies → execute `med_confirm.py` immediately

## When "dah makan [time]" is still loggable without ask
- User names drug/slot/alias (`A`, `Akurit`, `CC`, `dexa`, etc.), OR
- Explicit med phrasing (`makan ubat`, `dah ambil`, `slot A done`), OR
- Prior same-thread message already established the slot and this is pure time fill-in

## When MUST ask (do not write state)
- Bare `dah makan` / `dah makan 6am` / `thanks remind` with no drug/slot word AND verb could mean food
- Even if a reminder just fired — reminder context is a **hint**, not proof
- Even if schedule has exactly one candidate — schedule disambiguation still loses to food/med verb ambiguity until clarified once

## Do NOT
- Assume food and tell user "bukan ubat"
- Assume med and silent-log without drug/slot evidence
- Defend the assumption after user corrects — acknowledge, log, fix skill

## Related
- `references/time-only-confirmations.md` (schedule mapping + makan override)
- SKILL.md pitfall: Time-Based Slot Auto-Mapping (don't invent slot either)
