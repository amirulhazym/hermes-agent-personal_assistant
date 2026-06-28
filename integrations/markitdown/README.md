# MarkItDown Integration

> Priority #2 — Convert documents to Markdown for LLM/RAG consumption.  
> Bridges PDFs, Word, Excel, PowerPoint, images (OCR), audio (transcription) → clean Markdown.

## What It Is

**MarkItDown** ([microsoft/markitdown](https://github.com/microsoft/markitdown)) is an open-source Python utility by Microsoft for converting various document formats to Markdown. Designed for LLM and text-analysis pipelines.

- **License**: MIT ✅ Free
- **Stars**: ~160K
- **Stack**: Python
- **Why:** Hermes needs to ingest documents for RAG (Obsidian vault, knowledge base). MarkItDown turns any file type into clean Markdown while preserving structure.

## System Impact

| Area | Effect |
|------|--------|
| **RAG Pipeline** | Documents (PDF, Word, Excel, PPT) can now be converted → markdown → stored in Obsidian vault → indexed by LLM. |
| **Chat ingestion** | Users can send any document to Hermes; MarkItDown converts it before processing. |
| **Cost** | $0 — runs locally. No API key. |

## Install Steps

```bash
# Ensure in the active Hermes venv
source ~/.hermes/hermes-agent/venv/bin/activate  # Hermes agent venv

# Install main package
pip install markitdown

# Optional: install all extras for full format support
pip install markitdown[all]

# Verify
python -c "from markitdown import MarkItDown; print('OK')"
```

### System Dependencies for Full Format Support

| Format | Needs |
|--------|-------|
| PDF | `pdftotext` or `pdfplumber` (auto-installed via extras) |
| PowerPoint | No extra deps |
| Word | No extra deps |
| Excel | `openpyxl` (auto) |
| Images (OCR) | `pytesseract` + `pillow` |
| Audio (transcription) | `faster-whisper` or `whisper` + FFmpeg |

```bash
# For audio transcription (optional)
# Ubuntu/WSL
sudo apt-get install tesseract-ocr ffmpeg  # if not already installed

# For Windows (if using from Windows Python)
# Download tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
```

## Usage

### Python — Quick Example

```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("document.pdf")
print(result.text_content)  # Converted markdown
```

### Supported Formats

| Format | Extension | Example |
|--------|-----------|---------|
| PDF | `.pdf` | `md.convert("report.pdf")` |
| PowerPoint | `.ppt`, `.pptx` | `md.convert("deck.pptx")` |
| Word | `.doc`, `.docx` | `md.convert("memo.docx")` |
| Excel | `.xls`, `.xlsx` | `md.convert("data.xlsx")` |
| Images | `.jpg`, `.png`, `.webp` | `md.convert("receipt.jpg")` ✺ OCR |
| Audio | `.mp3`, `.wav`, `.m4a` | `md.convert("meeting.mp3")` ✺ transcription |
| HTML | `.html`, `.htm` | `md.convert("page.html")` |
| YouTube | URL | `md.convert("https://youtube.com/watch?v=...")` |
| EPUB | `.epub` | `md.convert("book.epub")` |
| ZIP | `.zip` | `md.convert("archive.zip")` (iterates contents) |

### Hermes Skill / Cron — Document Ingestion Pipeline

```python
# ~/.hermes/scripts/ingest-document.py
# Usage: python ./ingest-document.py /path/to/file.pdf

import sys, os, hashlib
from markitdown import MarkItDown
from datetime import datetime

INPUT_PATH = sys.argv[1]
VAULT_DIR = "/mnt/f/obsidian-vault/2-areas/Personal/reading/"

def derive_slug(filepath):
    # e.g., "report" from "report.pdf"
    return os.path.splitext(os.path.basename(filepath))[0].replace(" ", "_")

def derive_filename(slug):
    return os.path.join(VAULT_DIR, f"{slug}.md")

md = MarkItDown()
result = md.convert(INPUT_PATH)
slug = derive_slug(INPUT_PATH)
filename = derive_filename(slug)

# Derive Obsidian-compatible title from original filename or metadata
title = result.title or slug.replace("_", " ").title()

# Write as Obsidian note
output = f"""---
title: {title}
source: {INPUT_PATH}
ingested: {datetime.now().strftime('%Y-%m-%d')}
tags: [ingested, auto]
---

{result.text_content}
"""

with open(filename, "w", encoding="utf-8") as f:
    f.write(output)

print(f"Saved → {filename}")
```

### Integration with Hermes Chat

```python
# Concept: when user sends a document via WhatsApp/Telegram,
# Hermes receives the file, saves to /tmp/, runs MarkItDown,
# stores markdown in vault, returns summary.

def handle_document(filepath, filename):
    from markitdown import MarkItDown
    md = MarkItDown()
    result = md.convert(filepath)
    # ... save to vault, return summary ...
    return result.text_content[:2000]  # Preview first 2K chars
```

## Configuration

No config changes required. MarkItDown is used on-demand from scripts/skills.

## Maintenance Checklist

- [ ] `pip list | grep markitdown` returns version
- [ ] Run test: `python -c "from markitdown import MarkItDown; print('OK')"`
- [ ] Periodically: `pip install --upgrade markitdown`

## Links

- GitHub: https://github.com/microsoft/markitdown
- PyPI: https://pypi.org/project/markitdown/
- Docs: https://github.com/microsoft/markitdown#readme
