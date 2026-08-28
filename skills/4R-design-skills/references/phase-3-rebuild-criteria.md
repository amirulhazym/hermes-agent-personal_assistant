# Phase 3: Rebuild Criteria

## Structured Audit Checklist

Run this against the Phase 2 render. Each finding feeds the rebuild.

### Structural
- [ ] Does the layout hierarchy match the brief's content priorities? (Is the most important thing visually most prominent?)
- [ ] Is the grid rational or accidental? (Would a different column count / breakpoint serve the content better?)
- [ ] Is the visual weight balanced? (Empty areas vs dense areas — is the tension intentional?)
- [ ] Does the navigation/scannable flow make sense? (Can a user find what they need without hunting?)

### Visual
- [ ] Does the color palette support the mood, not fight it? (Too many colors? Wrong temperature?)
- [ ] Does the typography hierarchy work at a glance? (Headlines vs body vs captions — are they distinct enough?)
- [ ] Are surfaces and shadows purposeful? (Every surface needs a reason to exist)
- [ ] Does the design feel cohesive or patched together? (Do all sections look like they belong to the same page?)

### Content
- [ ] Is the primary message clear within seconds?
- [ ] Are CTAs / primary actions obvious?
- [ ] Is there any content that doesn't serve the brief? (Scope creep in the render)

### Interaction
- [ ] Do interactive elements feel interactive? (Affordance — does it look clickable?)
- [ ] Is the feedback model consistent? (Same hover/tap behavior for same element types)
- [ ] Are there any dead states? (What happens on error, empty, loading?)

## What to Keep from the Render

Only these:
- **Principles discovered** — "the grid needs tighter alignment" becomes a rebuild constraint
- **What worked** — "the hero typography scale was right" becomes a rebuild starting point
- **User reactions** — "too cramped" becomes a spacing constraint

What NOT to keep:
- HTML structure
- CSS values
- Component layout decisions
- Any specific element positions

## The Close Rule

**Non-negotiable:** Save the render file. Close it. Do not open it again.

If you find yourself thinking "I'll just check one thing in the old file," you're about to violate the rebuild. Close the tab. `rm` the file if you have to. The rebuild must be written from scratch with only the principles above as input.

## Rebuild Execution

1. Select the tool for the rebuild (same or different from Phase 2 — tool-options.md guides this)
2. Write the new file with only the design brief + Phase 1 principles + Phase 3 audit findings as input
3. After first draft, verify against each audit item that was flagged
4. Only then move to Phase 4

## Signs You Need Another Rebuild Cycle

- The rebuild fixed one problem but introduced others in the same class (structural → structural)
- The user says "closer but still not right" on foundational aspects
- You find yourself reaching for Phase 4 micro-tweaks to fix what is fundamentally a layout issue
