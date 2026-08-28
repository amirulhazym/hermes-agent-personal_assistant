# AI Design Workflow

> End-to-end design pipeline with vision-based critique loop (Evaluator-Optimizer pattern)

## Overview

This skill orchestrates the full design process: reference research → design token extraction → HTML/CSS generation → screenshot capture → vision critique → iterative revision → final QA.

## Pipeline Phases

### Phase 1: REFERENCE RESEARCH
- Capture reference site screenshots
- Extract design tokens (color, typography, spacing, mood)
- Document the design system

### Phase 2: GENERATION
- Apply design tokens + taste-skill rules + content
- Generate HTML/CSS output
- Ensure responsive layout

### Phase 3: CRITIQUE LOOP (3-5 iterations)
- Capture screenshot of current design
- Run vision critique with structured criteria
- Identify: layout issues, color problems, typography, motion, accessibility
- Revise based on critique
- Repeat until quality threshold met

### Phase 4: FINAL QA
- Responsive check (mobile, tablet, desktop)
- Accessibility validation (WCAG 2.2 AA)
- Performance check (no excessive animations)

### Phase 5: DELIVERY
- Single HTML file or React project
- Include all assets inline

## Quality Criteria (for critique)

1. **Layout** — visual hierarchy, balance, whitespace
2. **Color** — palette cohesion, contrast ratios, brand alignment
3. **Typography** — font choices, size hierarchy, readability
4. **Motion** — purposeful animations, not gratuitous
5. **Accessibility** — WCAG compliance, keyboard navigation
6. **Polish** — hover states, transitions, micro-interactions

## Anti-Slop Rules

- Never use generic templates
- Never mix more than 2 font families
- Never use rainbow gradients
- Never skip the critique loop
- Always test on mobile viewport
