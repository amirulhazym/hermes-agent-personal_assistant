# Phase 4: Refine — Quality Gates

Only start Phase 4 when Phase 3 produced a design that structurally works. If the user's feedback is about layout hierarchy or missing content, you're not in Phase 4 yet — go back to Phase 3.

## Quality Gates

Gate all of these before declaring the design deliverable:

### Color
- [ ] Primary palette has 3-5 colors max (unless the brand requires more)
- [ ] Accent color is used sparingly — if it's everywhere, it's not an accent
- [ ] Text has sufficient contrast: body text ≥ 4.5:1, large text ≥ 3:1 (WCAG AA)
- [ ] No pure black text on pure white (or vice versa) — soften slightly

### Typography
- [ ] Max 2 font families (unless brand requires more)
- [ ] Heading hierarchy is clearly distinguishable — size, weight, or both
- [ ] Line height is comfortable for reading (1.4-1.6 for body, tighter for headings)
- [ ] No orphans or widows in primary headings (use `text-wrap: pretty`)

### Spacing & Layout
- [ ] Consistent spacing scale applied (not random pixel values)
- [ ] No visual elements touching or overlapping unintentionally
- [ ] Content has breathing room — not crammed, not floating
- [ ] Alignment is consistent — elements on the same visual axis

### Interaction & Motion
- [ ] Hover states visible on all clickable elements
- [ ] Focus states visible for keyboard navigation
- [ ] Transitions are consistent — same duration/easing for same element types
- [ ] `prefers-reduced-motion` handled if motion is significant

### Responsive (if applicable)
- [ ] Primary viewport (desktop/mobile whichever was specified) — verified
- [ ] No horizontal scroll on the primary viewport
- [ ] Content doesn't break at intermediate sizes (no fixed-width traps)

### Accessibility
- [ ] Semantic HTML used (nav, main, section, heading tags in correct order)
- [ ] All interactive elements keyboard-accessible
- [ ] Alt text on meaningful images

### Content
- [ ] No placeholder text in final output (if real copy wasn't provided, label as [draft])
- [ ] No fake metrics, stats, or testimonials
- [ ] CTAs use action-oriented language, not "Submit" / "Click Here"

## Final Verification

Before delivery:

1. Open the artifact in browser
2. Check console for errors (JS, CSS, loading)
3. Verify at primary breakpoint
4. If responsive matters, check at least one other breakpoint

## Delivery Checklist

- [ ] Artifact file path confirmed
- [ ] Tool/format choice documented (which tool, which 4R phases)
- [ ] Known issues or trade-offs stated
- [ ] DESIGN.md or spec generated if required
