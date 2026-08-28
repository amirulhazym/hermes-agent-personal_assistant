# Tool Options Catalog

Each tool listed with when to use, when not to use, and which 4R phases it fits.

---

### ui-ux-pro-max

Design system generator — 67 styles, 161 palettes, 57 fonts.

- **Best for:** Full design system from scratch, need direction fast
- **When to use:** Early discovery, brand exploration, 0→1 projects where no visual identity exists
- **When NOT:** You already have a brand system; you need a single focused page; speed matters more than variety
- **Affects end result:** Generative — produces a palette/style you react to, not one you dictated
- **4R phases it fits:** Phase 1 (generate design system as reference), Phase 2 (apply system to render)
- **Compatibility:** Standalone, or paired with claude-design for execution

---

### claude-design

Full design process + HTML artifact generation. 7-step workflow: brief → context → tokens → format → build → verify → report.

- **Best for:** One-off designed HTML artifacts (landing pages, prototypes, decks, component labs)
- **When to use:** The deliverable is a single polished HTML file; you want taste-driven process with verification
- **When NOT:** You're still exploring directions (use sketch); you need a full design system (use ui-ux-pro-max)
- **Affects end result:** Process-driven — the quality comes from the workflow, not the starting prompt
- **4R phases it fits:** Phase 2 (render), Phase 4 (polish)
- **Compatibility:** Pairs with popular-web-designs for visual vocabulary; with ui-ux-pro-max for token application

---

### sketch

Throwaway HTML mockups — 2-3 variants for head-to-head comparison.

- **Best for:** Exploring design directions before committing
- **When to use:** You don't know what it should look like; you want to compare layouts/approaches side by side
- **When NOT:** You already know the direction; the output needs to be production-ready
- **Affects end result:** Exploratory — the point is to discard every variant except the winning direction
- **4R phases it fits:** Phase 2 only (throwaway render exploration)
- **Compatibility:** Winner from sketch can be rebuilt in Phase 3 using claude-design

---

### popular-web-designs

54 real design system templates — exact tokens, colors, typography, components for Stripe, Linear, Vercel, Notion, etc.

- **Best for:** "Make it look like Stripe/Linear/Vercel" — known brand directions
- **When to use:** User references a specific brand; you need a proven visual vocabulary fast
- **When NOT:** User wants something original; the brand reference is unknown (not in the 54 templates)
- **Affects end result:** Derived — the output takes its visual DNA from the chosen template
- **4R phases it fits:** Phase 1 (supply visual vocabulary as reference principles)
- **Compatibility:** Always pair with an execution tool (claude-design, sketch). Never standalone.

---

### ai-design-workflow

Full 5-phase pipeline: Reference Research → Generation → Critique Loop (3-5 iter) → QA → Delivery.

- **Best for:** Design tasks where the brief is clear and iteration means refinement
- **When to use:** Speed matters, direction is locked, you expect in-place improvement not structural rebuild
- **When NOT:** Design direction is uncertain; you need the Rebuild step to break bad assumptions
- **Affects end result:** Iterative — each critique round tightens the same file
- **4R phases it fits:** Independent methodology — not a 4R tool. See SKILL.md "When to use 4R vs ai-design-workflow"
- **Compatibility:** Use instead of 4R when applicable, not alongside it

---

### excalidraw

Hand-drawn JSON diagrams via excalidraw.com.

- **Best for:** Wireframes, flow diagrams, architecture sketches, concept maps
- **When to use:** You need to communicate layout structure or user flow before visual design; collaborative review
- **When NOT:** You need pixel-precise UI mockups; you need dark theme diagrams (use architecture-diagram)
- **Affects end result:** Structural — communicates layout and flow, not visual polish
- **4R phases it fits:** Phase 1 (map current state / existing system), Delivery (architecture docs)
- **Compatibility:** Can feed into Phase 2 as structural reference

---

### architecture-diagram

Dark-themed SVG architecture/cloud/infra diagrams as styled HTML.

- **Best for:** System design docs, technical presentations, README architecture sections
- **When to use:** You need dark-themed, production-quality architecture diagrams; README documentation
- **When NOT:** You want hand-drawn/wireframe feel; collaborative editing needed
- **Affects end result:** Formal — produces styled, ready-to-publish SVG diagrams
- **4R phases it fits:** Phase 1 (document existing system architecture), Delivery (final architecture output)
- **Compatibility:** Pairs well with design-md for tokenized diagram specs

---

### design-md

Google's DESIGN.md spec format — author, validate, diff, export design tokens.

- **Best for:** Formal machine-readable design token specs that agents and tools consume
- **When to use:** Output must be a DESIGN.md file; you need WCAG contrast validation; multi-project design consistency
- **When NOT:** The deliverable is a visual artifact (use claude-design); quick exploration (use sketch)
- **Affects end result:** Spec-driven — produces consumable tokens rather than visual output
- **4R phases it fits:** Output format — used at Delivery after Phase 4. Can also formalize Phase 1 reference principles
- **Compatibility:** Tokens from ui-ux-pro-max or popular-web-designs can be ported to DESIGN.md format
