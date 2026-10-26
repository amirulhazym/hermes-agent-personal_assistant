# Ticket 03: Dedicated Hermes Skill and Cron Job Integration

## Description
Create the domain skill `skills/diet-tracker/SKILL.md` documenting:
- ADHD output protocol.
- Dexa clinical rules (sodium retention, potassium balance, anti-catabolism protein targets).
- Trigger rules for when to run `scripts/diet_report.py`.
Update Cron job `91dd42eacfba` (21:30 Daily Diet Nudge) to utilize `diet_report.py`.

## Acceptance Criteria
- [ ] `skills/diet-tracker/SKILL.md` authored and valid frontmatter.
- [ ] Cron prompt in `jobs.json` updated with deterministic invocation command.
- [ ] Manifest updated in SSOT.

## Blocked by: 02-adhd-whatsapp-formatter
