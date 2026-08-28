# Output: Google DESIGN.md

When to produce a DESIGN.md file from the 4R process, and how.

## When to use this format

- The project needs a formal, persistent design token spec
- Multiple agents or projects will consume the same design system
- The user explicitly asks for a DESIGN.md
- You need WCAG contrast validation on the color palette
- The output will live in a repo and be version-controlled

## How to extract tokens from 4R phases

### Phase 1 → Token seeds

Reference principles translate directly to DESIGN.md tokens:

| Reference principle | DESIGN.md token |
|---|---|
| "One bold accent on neutral canvas" | `colors.primary` (neutral), `colors.tertiary` (accent) |
| "8px grid with deliberate exceptions" | `spacing` scale based on 8px |
| "Editorial typography, serif headings" | `typography.h1` with serif fontFamily |
| "Generous white space, card-based" | `rounded`, `spacing.lg` |

### Phase 2 & 3 → Token validation

During render and rebuild, the token draft gets tested. Revisions to tokens (e.g. "the accent is too strong at full saturation") update the DESIGN.md. The Rebuild step is the right time to lock token values — by then you've seen them in context.

### Phase 4 → Token lock

After Phase 4 refinement, tokens are frozen. This is when you run `npx @google/design.md lint DESIGN.md` for WCAG validation and structure checks.

## File structure

See `design-md` skill for full spec. Minimum viable DESIGN.md:

```yaml
---
version: alpha
name: <project-name>
description: <one-line description>
colors:
  primary: "#1A1C1E"
  secondary: "#6C7278"
  tertiary: "#B8422E"
  neutral: "#F7F5F2"
typography:
  h1:
    fontFamily: Public Sans
    fontSize: 3rem
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  body-md:
    fontFamily: Public Sans
    fontSize: 1rem
spacing:
  sm: 8px
  md: 16px
  lg: 24px
---
```

## DESIGN.md vs other output formats

| Output | Primary use | Token precision |
|---|---|---|
| HTML artifact | Visual review, client demo | Loose (approximate) |
| DESIGN.md | Repo spec, agent consumption | Exact (normative) |
| Claude spec | Handoff to external design agents | Medium (rationale + tokens) |
| Excalidraw | Wireframes, flow, structure | None (structural only) |

You can produce DESIGN.md alongside an HTML artifact — tokens from DESIGN.md feed the artifact's CSS custom properties.
