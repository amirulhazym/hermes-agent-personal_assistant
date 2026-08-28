# Phase 2: Render Requirements

## Minimum Viable Bar

The render is ready for critique when ALL of these are true:

### Content
- [ ] Every section from the brief has visible content — no "TODO" or "lorem ipsum" for primary sections
- [ ] Content hierarchy matches the brief — hero has prominent copy, secondary content is visually subordinate
- [ ] Navigation items visible and labelled (even if not all linked)
- [ ] Call-to-action / primary action clearly identifiable

### Layout
- [ ] Grid structure is resolved — columns, alignment, spacing are consistent
- [ ] Content fits within intended viewport without overflow or horizontal scroll
- [ ] Whitespace is intentional, not accidental — gaps are recognisable as design choices
- [ ] Header/footer/sidebar if applicable are distinguishable from main content

### Interaction (if applicable)
- [ ] Primary nav links/buttons are clickable
- [ ] At least one state transition visible (hover, click, toggle)
- [ ] No dead click targets that look interactive but do nothing

### Not Required (save for Phase 4)
- ❌ Exact color palette — approximate is fine
- ❌ Typography tuning — font size hierarchy matters, exact font face doesn't
- ❌ Micro-interactions — hover shadows, loading states, transitions
- ❌ Responsive beyond primary viewport — one breakpoint is enough
- ❌ Real copy — placeholder sentences are OK for non-primary content
- ❌ Accessibility audit — structural a11y (semantic HTML) yes, contrast check no

## How to choose tool

See `tool-options.md` for full catalog. Quick guide:

| Project type | Recommended tool |
|---|---|
| Landing page / deck / prototype | claude-design |
| Full design system exploration | ui-ux-pro-max → export tokens → claude-design |
| Direction exploration (no idea yet) | sketch (2-3 variants) |
| "Make it look like [brand]" | popular-web-designs + claude-design |
| Wireframe/structure first | excalidraw → then claude-design |

## How to verify render is good enough

Open the render file in a browser (or use browser_vision). Ask:

1. Can I tell what this page/screen is for within 3 seconds? If no → content hierarchy failed.
2. Are there obvious layout bugs? (overlapping, misaligned, broken) If yes → fix before moving on.
3. Can I click the main action? If no → interaction minimum not met.

If all 3 pass, the render is ready for Phase 3 critique. Move on. Do not polish.
