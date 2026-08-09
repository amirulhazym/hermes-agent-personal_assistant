---
name: wiki-vs-gdocs-hybrid
description: Reference — comparative analysis of local filesystem wiki (Obsidian/llm-wiki) vs Google Workspace as Hermes knowledge base, with hybrid architecture recommendation.
version: 1.0.0
author: Hermes Agent
---

# Wiki vs Google Docs — Hybrid Knowledge Base Architecture for Hermes

## Problem

Where should Hermes store knowledge for efficient agent access while keeping it accessible to the human (Amirulhazym)?

## Live Benchmarks (tested 26 Jul 2026, VPS Singapore)

| Operation | Local file (wiki) | Google Docs API | Ratio |
|-----------|------------------|----------------|-------|
| Read 250 lines | ~3ms | ~500-900ms | 170x faster |
| Search (ripgrep) | ~3ms | ~300-800ms | 100x faster |
| Write/create | ~1ms | ~500ms | 500x faster |
| Bulk 100 notes | <1s | Rate-limited ~60/min | Unlimited |

## Agent Performance Comparison

| Metric | Wiki (local .md) | Google Docs | Verdict |
|--------|-----------------|-------------|---------|
| Token overhead per read | 0 | ~200 (OAuth) | Wiki |
| Search speed | 3ms ripgrep | 300ms+ API | Wiki |
| Write speed | Unlimited | 60/min cap | Wiki |
| Availability | Always (local SSD) | Google uptime dependent | Wiki |
| Cross-reference | [[wikilinks]] | None | Wiki |
| Structured ingestion | llm-wiki skill | None | Wiki |
| Rich formatting | Markdown | Native Docs | GDrive |
| Phone editing | Obsidian app | Google Docs app | GDrive |
| Sharing | git/export | Direct link | GDrive |
| Cost | Free (or $4-10 sync) | Free | Tie |

## Hybrid Architecture

**Principle: Wiki = Source of Truth. Google Docs = Rendered Snapshot.**

```
KNOWLEDGE ENTERS
    ↓
WIKI (source of truth, local .md on VPS)
    ├── Hermes reads → 0 API, 3ms, always fresh
    ├── Hermes writes → 0 API, instant
    ├── search_files → one search, complete results
    │
    └── [OPTIONAL] Export to Google Docs
         Only when human needs formatted/shared version.
         Google Doc = SNAPSHOT with date. NEVER independent source.
         Label: "Generated from wiki, DD MMM YYYY"
```

## Token Accounting

Without wiki: Every knowledge read = 1 Google API call (~500-900ms + OAuth tokens)
With wiki (hybrid): Knowledge read = 0 API. Only shareable renders use API.

Break-even after ~3 reads. Over months of daily use = hundreds of API calls saved.

## Key Architectural Rules

1. **Wiki is the single source of truth.** Google Docs are snapshots.
2. **Default = wiki.** Only promote to Google Docs when sharing/formatted copy needed.
3. **Search wiki first.** Google Drive only for non-wiki files (PDFs, images).
4. **No double-write.** Never write same content to both places independently.
5. **Label all Google Doc snapshots** with source wiki page + date generated.

## Layer Stack

| Layer | Tool | Purpose | Token Cost |
|-------|------|---------|-----------|
| System memory | Hermes memory + USER.md | Preferences, corrections, stable facts | Always in context |
| Knowledge base | ~/wiki/ (local .md) | Medication rules, design decisions, research | 0 API |
| Session history | SQLite FTS5 (session DB) | Past conversations | Built-in |
| Formatted docs | Google Docs | Shareable documents | API on write only |
| Code/config | Git repos | Source code | Already local |

## Drift Prevention

If content exists in both wiki AND Google Docs independently, they WILL diverge.
Fix: Google Doc is a snapshot with a date label. Always trust wiki.

## Related Skills

- `obsidian` — Read, search, create, edit notes in Obsidian vault
- `llm-wiki` — Karpathy's LLM Wiki: build/query interlinked markdown KB
- `google-workspace` — Gmail, Calendar, Drive, Docs, Sheets via API
- `gdocs` — Create properly formatted Google Docs

## When to load this skill

- User asks about wiki vs Google Docs trade-offs
- User asks about knowledge base architecture
- User asks about hybrid storage approach
- When designing knowledge ingestion pipeline
- **Operating the local wiki vault** (~/wiki exists, 13 files, 31 Jul):
  rules, lint tool, migration workflow, gate measurement — see
  `references/vault-operations.md`
