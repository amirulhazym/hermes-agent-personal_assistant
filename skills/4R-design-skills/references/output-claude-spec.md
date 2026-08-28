# Output: Claude Design Spec

When to produce a Claude design spec from the 4R process, and how.

## When to use this format

- You need to hand off the design brief to an external design agent (Claude Design, another LLM)
- The project needs a structured but human-readable design document — not as strict as DESIGN.md, more detailed than a simple prompt
- You want to preserve rationale alongside token choices for future reference
- The design will be implemented by another agent across multiple sessions

## Structure

A Claude design spec follows this order:

### 1. Brief Summary

One paragraph: what is being designed, for whom, and why.

```
A landing page for an AI code review tool targeting senior engineers.
Primary message: "Your code, reviewed by AI that actually understands context."
Tone: technical, confident, not hype-y.
```

### 2. Design Tokens

Exact values extracted from 4R Phase 1 (reference) and validated in Phase 2-3.

- Colors (hex values, purpose)
- Typography (font, size, weight, line-height per level)
- Spacing (base unit, scale)
- Radii, shadows (if applicable)
- Component specs (button, card, nav — states included)

Keep it to what's actually used. Don't list unused tokens.

### 3. Layout Structure

The grid system and content hierarchy:

- Primary layout (single column, sidebar, split, etc.)
- Section order and purpose
- Breakpoint behavior (if multi-viewport)
- Key content priorities per section

### 4. Component Specifications

For each distinct component:

- States: default, hover, active, disabled, focus
- Behavior: click, hover, transition, animation
- Variants: primary/secondary, small/medium/large
- Rationale: why this component behaves this way

### 5. Variant Rationale

If the 4R process produced multiple variants (sketch, ui-ux-pro-max exploration), document:

- What was explored
- Why the chosen direction won
- What was rejected and why

### 6. Constraints

- Accessibility requirements (WCAG level)
- Platform/browser targets
- Performance budgets
- Content limitations (no real copy yet? placeholder labels?)

### 7. Rebuild Notes (from Phase 3)

What changed structurally between Render and Rebuild. This helps the next agent understand why certain decisions were made:

```
Header: moved from fixed top to inline after hero (render had scrolling issues).
Card grid: reduced from 4-col to 3-col (content looked sparse at 4-col).
Color: accent shifted from blue to amber (render felt too generic/tool-like).
```

## Claude spec vs other output formats

| Output | Primary use | Detail level |
|---|---|---|
| HTML artifact | Visual review, client demo | Visual only |
| DESIGN.md | Repo spec, agent consumption | Exact tokens, minimal rationale |
| Claude spec | Handoff to design agents | Tokens + rationale + decisions |
| Excalidraw | Wireframes, flow, structure | Structural only |

## Example spec (minimal)

```
# Claude Design Spec: Code Review Landing Page

## Brief
Landing page for senior engineers. Tone: technical, confident. CTA: "Start free trial."

## Tokens
- Primary: #1A1C1E (headings, body)
- Accent: #B8422E (buttons, links)
- Neutral: #F7F5F2 (background)
- Font: Inter (headings + body, one family for technical feel)

## Layout
Hero → Features (3-col) → Testimonial → Pricing → Footer
Single column, max-width 1200px, centered.

## Components
Button-primary: bg=accent, text=white, radius=8px, hover=darken 10%
Button-secondary: bg=transparent, border=primary, hover=fill

## Rebuild notes
Phase 2 render was too generic (standard SaaS). Rebuild focused on technical density — tighter type, more code samples, less marketing fluff.
```
