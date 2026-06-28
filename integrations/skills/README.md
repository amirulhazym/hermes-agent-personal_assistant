# Skills — Design Workflow Toolkit

> Design skills installed into Hermes Agent for AI-powered UI/frontend development.
> Each skill is created via `skill_manage` and lives in `~/.hermes/skills/<name>/`.
>
> **This document is for AI coding agents** updating this repo.
> **Maintenance:** Re-run the provisioning steps in `provision.sh` after a fresh Hermes install.

---

## Overview

These skills form a **progressive design toolkit** — from anti-slop rules (taste-skill) → UX knowledge (ux-designer) → technical build (canvas, web-artifacts) → process orchestration (ai-design-workflow).

The crown jewel is **ai-design-workflow**, which implements a vision-based critique loop (Evaluator-Optimizer pattern) that enables AI-generated designs to exceed average human quality.

## Skills Inventory

### Core Design Skills

| Skill | Source | Type | Status |
|-------|--------|------|--------|
| **taste-skill** | leonxlnx (★52k) | Anti-slop design rules | `installed ✅` |
| **ux-designer-skill** | szilu (★26) | UX best practices + 26 ref files | `installed ✅` |
| **frontend-design** | anthropics/skills | Frontend design principles | `installed ✅` |
| **brand-guidelines** | anthropics/skills | Brand color/typography system | `installed ✅` |
| **canvas-design** | anthropics/skills | Visual art generation | `installed ✅` |
| **web-artifacts-builder** | anthropics/skills | HTML artifact builder (Vite/React) | `installed ✅` |

### Sub-skills (from taste-skill ecosystem)

| Skill | Focus | Status |
|-------|-------|--------|
| **redesign-skill** | Site/app redesign workflow | `installed ✅` |
| **high-end-visual-design** | Premium agency-level visual polish | `installed ✅` |
| **minimalist-ui** | Clean editorial-style interfaces | `installed ✅` |
| **industrial-brutalist-ui** | Raw mechanical/industrial style | `installed ✅` |

### Process & Workflow Skills

| Skill | Source | Purpose | Status |
|-------|--------|---------|--------|
| **ai-design-workflow** | Custom-built | **End-to-end design pipeline** with visual critique loop | `installed ✅` |
| **brainstorming** | obra/superpowers | Ideation before creative work | `installed ✅` |
| **writing-plans** | obra/superpowers | Structured implementation plans | `installed ✅` |
| **verification-before-completion** | obra/superpowers | Quality gate before claiming done | `installed ✅` |
| **finishing-a-development-branch** | obra/superpowers | Clean branch wrap-up | `installed ✅` |
| **receiving-code-review** | obra/superpowers | Handle feedback professionally | `installed ✅` |

### Motion Reference

| Resource | Source | Format | Status |
|----------|--------|--------|--------|
| **transitions.dev motion tokens** | transitions.dev | 18 CSS transitions + root variables | `installed ✅` in `taste-skill/references/` |

### How to Use

```bash
# In chat with MJ:
"guna ai-design-workflow untuk design portfolio macam Linear + Vercel"

# Or load skill directly:
# MJ will load the skill SKILL.md and follow the phases
```

## The ai-design-workflow Pipeline

This is the main orchestrator. It wraps all other skills into a coherent process:

```
Phase 1: REFERENCE RESEARCH (vision model)
  Capture reference sites → Extract design tokens (color, type, spacing, mood)

Phase 2: GENERATION (code agent)
  Design tokens + taste-skill rules + content → HTML/CSS output

Phase 3: CRITIQUE LOOP — 3-5 iterations (vision model)
  Capture screenshot → Vision critique → Revise → Repeat until threshold met

Phase 4: FINAL QA
  Responsive check, accessibility, performance

Phase 5: DELIVERY
  Single HTML or React project
```

**Key insight:** The critique loop (Phase 3) is what separates human-quality from vibe-coded output. A multimodal model reviews actual rendered screenshots using structured criteria (aesthetics, layout, typography, motion, accessibility).

## Reference Files

Each skill has a `references/` directory with supporting documents.

### ai-design-workflow References (5 files)

| File | Lines | Purpose |
|------|-------|---------|
| `design-token-extraction-prompt.md` | 94 | Vision prompt to extract design system from reference screenshots |
| `design-critique-prompt.md` | 133 | Two-part prompt for vision-based UI critique (6 criteria) |
| `design-system-document-example.md` | 69 | Example output of Phase 1 (structured design tokens) |
| `workflow-execution.md` | 151 | Concrete step-by-step Hermes Agent commands |
| `anti-slop-checklist.md` | 56 | Fast-reference for critique agent (layout, color, type, motion bans) |

### ux-designer-skill References (26 files)

Covers: core principles, laws of UX, accessibility (WCAG 2.2 AA), visual design, information architecture, interaction design, forms, navigation, AI interfaces, design systems, responsive, prototyping, usability testing, and more.

### transitions.dev (in taste-skill)

18 CSS transitions with root variables: `ease-in-out`, `ease-out-expo`, `ease-bounce`, `spring-stiff`, `spring-bounce`, timing tokens for fast/medium/slow, and standard motion guidelines.

## Prerequisites to Run the Full Pipeline

| Requirement | Status | Notes |
|-------------|--------|-------|
| Multimodal model | `not yet configured` | OpenCode Go needed for vision critique loop |
| cua-driver | `standby` | For browser screenshots |
| Playwright | `installed` | For Crawl4AI/Browser-Use |

## Skipped / Excluded

| Skill | Reason |
|-------|--------|
| `systematic-debugging` | Already exists in system Hermes skills |
| `requesting-code-review` | Already exists in system Hermes skills |
| `test-driven-development` | Already exists in system Hermes skills |
| (other superpowers sub-skills) | Dev workflow focused, not design relevant |
