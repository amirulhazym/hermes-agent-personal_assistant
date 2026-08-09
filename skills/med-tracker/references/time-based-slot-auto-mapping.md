# Time-Based Slot Auto-Mapping Pitfall (2026-07-07)

When user says they took **something** at a specific time, the agent MUST verify WHAT was taken — not map "medication at TIME" to the nearest slot by schedule.

## Failure chain (2026-07-07)
```
User: "dah makan dah pun jam 7.15am tadi" (referring to pantoprazole, not tracked)
Agent: "medication taken at 7:15am → Slot B = 7-8am → matches → EXECUTE med_confirm.py B"
Agent logged Dexa #1 + Levetiracetam as taken. User NEVER said those drugs.
```

## Root cause
Time-based pattern matching ("dah makan jam X") triggers automatic slot assignment based on schedule time alone, WITHOUT checking whether user's actual words contain the slot's drug names.

## Guard
Before executing `med_confirm.py <slot>`, ask: "Did the user's message mention ANY drug name or alias that maps to this slot?" If the answer is NO (user only mentioned an untracked drug like pantoprazole, or no drug name at all), DO NOT confirm the slot. Ask: "Which drug/slot was that?"

Same ask-don't-assume attitude as `references/makan-ambiguity-ask-dont-assume.md` — both directions:
- don't invent a slot
- don't invent "food only"

## When untracked drugs are mentioned
- Pantoprazole, probiotics, supplements, OTC meds — not in med-schedule.json
- If user confirms taking an untracked drug, acknowledge verbally but do NOT map to any slot
- The system has no slot to log it to — do not fabricate one
