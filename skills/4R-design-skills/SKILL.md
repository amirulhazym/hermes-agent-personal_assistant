---
name: 4R-design-skills
description: Use when designing any UI/UX from scratch — landing pages, prototypes, apps, decks. Load when the user wants a structured design process: reference research, render a first pass, structurally rebuild, then refine. Use when ai-design-workflow's in-place iteration isn't enough and you need a dedicated rebuild step.
---

# 4R Design Skills — Reference → Render → Rebuild → Refine

Meta-methodology for taste-driven design. 4R doesn't replace existing design skills — it orchestrates them. Each phase tells you WHAT to achieve, not WHICH tool to use. Tool choices live in `references/tool-options.md`.

## Mindset

- AI can't read your mind. Steering > begging.
- "Make it look good" is not a brief. Specific directions get specific results.
- Render is for exploration. Rebuild is for quality. Never skip the rebuild.
- The first version is supposed to be wrong. That's the point.

## When to use 4R vs ai-design-workflow

4R and `ai-design-workflow` are both design methodologies — pick one per task, don't stack.

| Situation | Use |
|---|---|
| Design direction uncertain, expect structural changes | **4R** (Rebuild is non-negotiable) |
| Brief is clear, iteration is refinement not rethink | **ai-design-workflow** (faster, in-place critique loop) |
| Need to explore multiple directions before committing | **4R** (Render → critique → Rebuild forces fresh thinking) |
| Reference research already done, just need execution | **ai-design-workflow** (straight to generation) |
| Output must be pixel-perfect with formal specs | **4R** (outputs DESIGN.md, Claude spec alongside artifact) |

Rule of thumb: 4R for when you'd say "let me try something and see if it works." ai-design-workflow for "I know what I want, make it."

## Phase 0: Discovery

Before any design work, establish the foundations.

**Output:** Design brief (1 paragraph max)

**What to establish:**
- **Archetype** — What kind of project? (landing page, app, dashboard, deck, prototype)
- **Audience** — Who uses this? What do they need to feel/do?
- **Constraints** — Brand guidelines? Platform? Deadline? Accessibility level?
- **References** — 1-3 existing designs that capture the right feel

If the user gave you a vague brief ("make a landing page"), ask targeted questions — one at a time, not a questionnaire dump.

## Phase 1: Reference

Extract PRINCIPLES from references, not elements.

**Goal:** Understand WHY the reference works, not WHAT it looks like.

**What to extract:**
- **Structural principles** — What makes the layout work? Density? White space? Grid choice?
- **Visual principles** — What makes the palette/mood work? Restraint? Contrast? Tone?
- **Interaction principles** — What makes the UX feel right? Speed? Feedback? Predictability?
- **Constraints discovered** — What did the reference NOT do that was a good call?

**Anti-pattern:** Copying a Stripe gradient and calling it done. The gradient is an element. The principle is "single bold accent on neutral canvas."

**Tools that help here:** popular-web-designs (supply visual vocabulary), excalidraw (map layout structure), design-md (tokenize principles into spec format).

**IMPORTANT:** Load the tool skill ALONGSIDE this one. If Phase 2 needs claude-design, load both `4R-design-skills` AND `claude-design` at the start — don't reach Phase 2 without the artifact skill loaded.

See `references/phase-1-reference-checklist.md` for detailed extraction guide.

## Phase 2: Render

Get something tangible fast. Functional > beautiful.

**Minimum viable bar (non-negotiable):**
- All primary content visible — no placeholder text for main sections
- Layout structure resolved — grid, hierarchy, spacing fundamentally correct
- Core interaction flow works — navigation, clicks, primary actions traceable
- Visual polish NOT required — color refinement, typography tuning, micro-interactions are Phase 4

**Goal:** Something the user and you can open in a browser and honestly critique. If the user can't tell what they're looking at, the render isn't done yet. If they can tell but it's ugly, perfect — that's the point of Phase 3.

**Choose tool from `references/tool-options.md`** based on project type:
- Full design system → ui-ux-pro-max
- One-off HTML artifact → claude-design
- Throwaway exploration → sketch
- Known brand direction → popular-web-designs + claude-design

**Anti-pattern:** Spending 4 hours tuning a button shadow in Phase 2. That's Phase 4 work. Stop yourself.

See `references/phase-2-render-requirements.md` for detailed bar.

## Phase 3: Rebuild ← KEY DIFFERENTIATOR

**Close the render file. Do not iterate on it.** Start fresh with learnings only.

This is what separates 4R from every other design workflow. The render is disposable. The principles you discovered from critiquing it are what you keep.

**Process:**
1. **Audit the render** against structured criteria (see `references/phase-3-rebuild-criteria.md`)
2. **Document what worked and what didn't** — be specific: "nav dropdown too slow, hero hierarchy unclear, color accent not pulling weight"
3. **Close the render file** — do NOT reopen it. No peeking, no "just one tweak"
4. **Write the rebuild from scratch** — same Phase 2 tool or different, doesn't matter. What matters is you carry forward only the learnings, not the assumptions baked into the first file

**Why this works:** The render inevitably encodes bad assumptions in its structure. Iterating in-place gradually improves the surface while the foundation stays compromised. Rebuilding forces you to re-examine every decision.

**Signs you're doing it wrong:**
- "I'll just copy the parts that worked into the new file" → Wrong. That carries the bad assumptions too.
- "This render is actually pretty good, let me just polish it" → Maybe. But if you're sure, you should be using ai-design-workflow instead.
- "Rebuilding is wasteful" → It's not. A 2-hour rebuild is cheaper than 6 rounds of in-place polish that never fixes the core layout.

See `references/phase-3-rebuild-criteria.md` for structured audit checklist.

## Phase 4: Refine

Micro-polish on a solid foundation. Only start this when Phase 3 produced a design that structurally works.

**What belongs here:**
- Color refinement — pick the exact accent, check contrast
- Typography tuning — adjust size scale, line height, letter-spacing
- Micro-interactions — hover states, transitions, loading states
- Responsive polish — verify all breakpoints
- Accessibility pass — WCAG checks, keyboard nav
- Final content — replace placeholders with real copy

**What does NOT belong here:**
- Layout restructure (that's Phase 3 fail)
- Adding new sections not in the brief (that's scope creep)
- "While I'm here..." refactors

**Quality gates** for declaring Phase 4 complete: see `references/phase-4-refine-gates.md`.

**Final step before delivery:** Confirm the user has picked a direction. Don't declare Phase 4 done with multiple variants open — the user must choose one before you deliver.

**Output order when producing multiple formats:** Generate DESIGN.md tokens FIRST, then build the HTML artifact from those tokens. Not the reverse. This ensures the artifact uses canonical values.

## Tool Attachment Points

4R doesn't hardcode tools. Each phase tells you what to achieve; `references/tool-options.md` tells you which tool fits.

Quick reference:

| Tool | Phase fit |
|---|---|
| ui-ux-pro-max | Phase 1 (generate design system) + Phase 2 (apply) |
| claude-design | Phase 2 (render) + Phase 4 (polish) |
| sketch | Phase 2 only (throwaway exploration) |
| popular-web-designs | Phase 1 (supply visual vocabulary) — pair with claude-design for execution |
| ai-design-workflow | Independent methodology — see "When to use 4R vs ai-design-workflow" |
| excalidraw | Phase 1 (map current state / wireframes) + Delivery |
| architecture-diagram | Phase 1 (system mapping) + Delivery (final architecture) |
| design-md | Output format — formal token spec after Phase 4 |

## Output Formats

4R can produce four output formats depending on what the project needs:

| Format | When to use | How |
|---|---|---|
| HTML artifact | Client-facing prototype, landing page, interactive mockup | Generate via claude-design or sketch |
| DESIGN.md | Design system spec, token reference, agent-consumable format | Use design-md skill. See `references/output-google-design-md.md` |
| Claude design spec | Structured brief for Claude Design / external agents | See `references/output-claude-spec.md` |
| Excalidraw / SVG diagram | Architecture docs, wireframes, flow diagrams | Use excalidraw or architecture-diagram skills |

You can produce multiple: an HTML artifact for visual review + a DESIGN.md for token documentation.

## Anti-Patterns

- **Skipping Rebuild.** The most common failure. "This render is good enough" means you skipped the step that produces great work. If the brief is easy, use ai-design-workflow instead — don't half-ass 4R.
- **Polishing too early.** Tweaking colors in Phase 2 is wasted effort. The rebuild will change the layout anyway.
- **Tool first, methodology second.** Picking claude-design and following its workflow instead of 4R's. The tool serves the phase, not the other way around.
- **Copying elements instead of principles.** A Stripe gradient on your page doesn't make it Stripe-quality. The layout hierarchy, spacing discipline, and restraint do.
- **Rebuilding by copy-paste.** Opening the render file and dragging parts into the new file defeats the purpose. Close it. Type fresh.
- **Design brief by questionnaire.** Asking 10 questions at once overwhelms the user. One question at a time, reflect their answer, confirm understanding, move to next.
