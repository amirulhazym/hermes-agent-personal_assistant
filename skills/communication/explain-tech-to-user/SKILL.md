---
name: explain-tech-to-user
description: "Explain tech to amirulhazym: analogy, numbers, BM."
version: 1.0.0
author: Hermes (curator-managed)
license: MIT
---

# Explaining Technical Things to amirulhazym

## Approved style (2026-08-13)
User explicitly praised and asked to save: "Niceee, nice cara kau explain, macam tu baru betul. Save as preference untuk any conversation please."

Three pillars, in order:
1. **Simple everyday analogy** — e.g. `session_key` explained as "nombor rak dalam perpustakaan"; untagged rows = "buku ada tapi tak tau letak rak mana". Lead with this.
2. **REAL numbers from the actual system** — not vague. Show measured counts pulled live (e.g. "870 rows NULL", "454 telegram updated, 0 remaining"). Do NOT estimate; query the DB/tool and report the figure.
3. **Bahasa Malaysia** (Manglish ok) for his conversations.

## When to use
Any time you explain a technical concept, root cause, or plan to him — not just `/non-tech`. Structure: analogy → real numbers → implication/next-step.

## Telegram reply discipline (corrected 2026-08-21, HARD RULE)

His #1 complaint this session: replies "berserabut" — NOT markdown, NOT chunking.
Measured root causes (Phase-A audit, state.db): model regeneration after
`finish_reason=length` cut-offs re-pours the same closing lines; plus my own habit
of stacking multiple closing lines every turn. In 40 consecutive TG messages:
"standing by" ×62, "awaiting" ×22, identical deeplink ×6.

Rules for EVERY reply to him (Telegram especially):
1. **ONE closing line maximum** — or none. Never stack 2+ sign-offs ("— standing
   by." + "Standing by boss" + "awaiting your done" = forbidden).
2. **Never repeat an already-sent sentence** in the same reply or as a re-send of a
   prior turn's content. After a mid-stream cut-off, CONTINUE with new text only —
   do not re-emit the table/summary/closing from before the cut.
3. One topic per reply; verdict first, then minimal supporting evidence.
4. Tables OK for multi-item data, but no giant table + repeated footer combos.
5. When he says "messy/tak clear", first suspect REPEATED TEXT inside one reply,
   not formatting — ask for one screenshot only if genuinely ambiguous; do not
   guess-and-fix the wrong cause repeatedly (that pattern itself frustrated him).

Evidence base: see `references/telegram-response-quality-audit.md` (Phase-A
audit 2026-08-21: measured repeat counts, gateway display keys, verified
NOT-FOUND items like post-send dedup).

## Anti-pattern (corrected 2026-08-13)
Do NOT claim "no access" to systems he already set up. He corrected this firmly: "sejak bila kau takde akses dekat drive aku? Kita dah setup...". Verify first via the actual tool.
- Google Drive / Workspace: use `python ~/.hermes/skills/productivity/google-workspace/scripts/google_api.py drive get <fileId>` (reads `~/.hermes/google_token.json`, already authenticated). The `gws` CLI needs SEPARATE auth (`gws auth login`) and is not the path for Drive ops here.
- Never substitute a guessed "no access" for a real tool check.

## Hands-on / self-service mode (corrected 2026-08-25)

Signal phrases: "aku nak handson", "macam mana aku nak buat sendiri", "dekat mana aku boleh access semua files tu", "tanpa arahkan kau".

Correction received: a conceptual mental-model guide (layers/analogies) was rejected — "Bukan, maksud aku hands-on manually... dekat mana aku boleh access semua files tu, nak ubah itu ubah ini." For HIM, self-service means a LAB MANUAL, not a mental model:

1. SURVEY REAL PATHS FIRST — inspect the live system and report exact file paths WITH current line numbers of the sections he will edit (e.g. config.yaml — providers: baris N, model_aliases: baris M; which .env line holds the key). Never give generic example paths.
2. Numbered steps; each step = one copy-paste command block + one-line objective pass criterion (HTTP status, resolver output field, picker row visible).
3. End with a compact troubleshooting table (gejala → sebab → fix), built ONLY from errors actually hit this session — no invented rows.
4. Deliver as .md via MEDIA: directly.
5. Max ONE analogy line total — analogies are for concepts he asked to understand, not for procedures he asked to execute.
6. Close with the working agreement: he drives the next repetition; agent only spot-checks when given the REAL error message (bukan "tak jadi" tanpa output).
