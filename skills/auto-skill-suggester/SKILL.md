---
name: auto-skill-suggester
description: "Suggest relevant skills by scanning conversation topics against a keyword map. Triggers when user starts a task in: debugging, planning, ML/AI, UI design, testing, research, code review, GitHub, content writing, creative media, Hermes config, computer-use, smart-home, or productivity."
disable-model-invocation: false
---

# Auto-Skill Suggester

## How It Works

When loaded, this skill instructs Jane to:

1. **Scan** your message for trigger keywords from the topic→skill mapping
2. **Match** against known categories (debugging, planning, ML/AI, etc.)
3. **Suggest** relevant skills to load — **only if** they aren't already loaded
4. **Ask** before loading ("Nampak topic X, nak I load Y?")

## Trigger Rules

Jane follows these rules when suggesting:

- **Only suggest once per topic per session** — no repeated nagging
- **Don't suggest for trivial chat** — "ok", "thanks", "good morning", simple Q&A
- **Suggest only when 2+ keywords match** in a single category (avoids false positives)
- **Max 2 category suggestions per turn** — don't overwhelm
- **If multiple categories match**, suggest the one with the strongest signal (most keyword hits)
- **If skills are already loaded** for that category → skip (no need to re-suggest)
- **Keep it short** — "Nampak bos nak debug. Nak I load diagnosing-bugs + systematic-debugging?" is enough

### Completion Criterion

The suggestion action is complete when:
- User says yes → load the skills immediately via `skill_view()` for each
- User says no / "tak" / "later" → drop it, don't suggest again for this topic this session
- User says "jangan suggest" → silence all suggestions for rest of session
- User changes topic → suggestion is voided, new topic may trigger new suggestion

## Mapping Reference

Full mapping is in `references/mapping.json`. Each entry has:
- `triggers`: keyword array matched against user message (case-insensitive)
- `skills`: ordered list of skills to suggest
- `reason`: one-line explanation of why these skills help

### Quick Category Reference

| Category | When user talks about... | Suggested skills |
|----------|------------------------|------------------|
| debugging | bug, error, crash, traceback, rosak | diagnosing-bugs, systematic-debugging, python-debugpy, node-inspect-debugger |
| code-review | PR, review, check code | requesting-code-review, github-code-review |
| planning | plan, feature, nak buat, cadangan | plan, planning-and-task-breakdown, writing-plans, to-issues, to-prd |
| testing | test, pytest, TDD, coverage | test-driven-development |
| ui-design | design, UI, frontend, mockup | sketch, ui-ux-pro-max, claude-design, excalidraw, architecture-diagram |
| ml-ai | model, LLM, fine-tune, inference, vllm | llama-cpp, serving-llms-vllm, huggingface-hub, evaluating-llms-harness |
| research | paper, arxiv, research, cari | arxiv, blogwatcher, youtube-content, llm-wiki |
| github | git, commit, repo, PR, CI/CD | github-auth, github-pr-workflow, github-issues, github-repo-management |
| productivity | note, obsidian, calendar, email, pdf | obsidian, notion, google-workspace, nano-pdf, powerpoint |
| creative-media | video, gif, music, art, animation | ascii-art, ascii-video, gif-search, heartmula, manim-video, p5js |
| hermes-config | hermes, config, profile, gateway, billing | hermes-agent, system-verification-qa |
| computer-use | click, screenshot, desktop, automation | computer-use, screenshot-verification |
| smart-home | lampu, hue, philips, smart home | openhue |

## Example Flow

```
User: "Kenapa test ni fail? Traceback dia tunjuk null pointer"

Jane: "Nampak topic debugging tu. Nak I load diagnosing-bugs +
systematic-debugging untuk kita track root cause properly?"

User: "Ok load"

Jane: <loads both skills via skill_view()>
```

## Edge Cases

- **No match found** → stay silent, don't force suggestions
- **Skills already loaded** → don't suggest again for that category
- **User says "jangan suggest" / "stop"** → pause suggestions for the rest of this session
- **User explicitly names a skill they want** (e.g. "guna X + Y") → treat as direct instruction, load it, don't suggest alternatives
- **User mentions a skill by name in passing** → don't suggest that skill or its category; they already know it exists
- **User corrects or declines a suggestion** → learn: don't suggest THAT category again this session (avoids annoying the user twice with the same thing)
