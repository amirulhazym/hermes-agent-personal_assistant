# Medication Compliance Report — WhatsApp Format

## Data Integrity Rule

**Only count COMPLETE days in historical compliance metrics.** A complete day = yesterday or earlier. Today is never complete when the report runs (not all slots have had their turn). Exclude today from the compliance calculation period.

Today is shown separately as a live snapshot — never merged into the compliance denominator.

## Exact WhatsApp Output Format

```
📊 MED COMPLIANCE REPORT

🔅 N complete days: DD/MM/YYYY - DD/MM/YYYY

Date-to-Date (%): XX.X%

A — X/X ✅
B — X/X ✅
C — X/X ✅
D — X/X ✅
E — X/X ✅

🔅Today, DD/MM/YYYY:
A✅ B✅ C✅ D🟡 E🟡

`Note: Dexa Xmg TDS, Phase ends DD/MM/YYYY (X days)`
```

## Emoji Conventions

| Emoji | Meaning | Context |
|-------|---------|---------|
| ✅ | Completed / ≥90% | Slot taken, high compliance |
| 🟡 | Pending / partial | Not yet taken today, or partial dose |
| ⚠️ | Warning | 70-89% compliance |
| ❌ | Critical | <70% compliance |
| 🔅 | Section header | Period header, Today header |
| `backticks` | Notes | Taper info, supply warnings |

## Date Format

Always **DD/MM/YYYY** for WhatsApp delivery. Never ISO or other formats.

## Slot Status Priority

When checking `med-status.json` for a given date+slot:
- `completed` / `confirmed` → counted as taken
- `partial` → counted separately
- `pending` / `no_data` → missed (if date is past) or pending (if today)
- Skip dates before tracking start (2026-07-02)
