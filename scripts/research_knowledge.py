#!/usr/bin/env python3
"""PX-1 Knowledge Export Stub — Fasa 4 thin interface.

Usage:
  python3 research_knowledge.py <artifact_dir>
  python3 research_knowledge.py --list

Reads artifact meta.yaml + report.md + sources.json → produces vault-note.md.
Does NOT auto-write to any vault. User copies manually.
"""
import sys, json
from pathlib import Path
from datetime import datetime

ARTIFACTS_ROOT = Path.home() / ".hermes" / "research" / "artifacts"


def artifact_to_frontmatter(meta_path: Path) -> dict:
    if not meta_path.exists():
        return {}
    import yaml
    with open(meta_path, encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    return {
        "title": meta.get("question", "Untitled Research")[:80],
        "date": meta.get("created_utc", "")[:10],
        "created_utc": meta.get("created_utc", ""),
        "question": meta.get("question", ""),
        "confidence": meta.get("confidence", "medium"),
        "labels": meta.get("labels", {}),
        "sources": meta.get("source_count", 0),
        "backends": {
            "search": meta.get("search_backends_used", []),
            "extract": meta.get("extract_backends_used", []),
        },
        "tags": ["research", "PX-1"],
    }


def frontmatter_md(data: dict) -> str:
    lines = ["---"]
    for k, v in data.items():
        if isinstance(v, (list, dict)):
            lines.append(f"{k}:")
            if isinstance(v, dict):
                for sk, sv in v.items():
                    lines.append(f"  {sk}: {sv}")
            else:
                for item in v:
                    lines.append(f"  - {item}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def artifact_to_markdown(artifact_dir: Path) -> str:
    parts = []

    # Frontmatter
    meta_path = artifact_dir / "meta.yaml"
    if meta_path.exists():
        fm = artifact_to_frontmatter(meta_path)
        parts.append(frontmatter_md(fm))
        parts.append("")

    # Report body
    report = artifact_dir / "report.md"
    if report.exists():
        parts.append(report.read_text(encoding="utf-8"))
        parts.append("")

    # Sources
    sources_path = artifact_dir / "sources.json"
    if sources_path.exists():
        parts.append("## Sources\n")
        with open(sources_path, encoding="utf-8") as f:
            sources_data = json.load(f)
        for s in sources_data.get("sources", []):
            sid = s.get("id", "?")
            title = s.get("title", "Untitled")
            url = s.get("url", "")
            label = s.get("label", "")
            parts.append(f"- **{sid}** [{title}]({url}) — {label}")
        parts.append("")

    return "\n".join(parts)


def export_artifact(artifact_dir: Path, output_dir: Path = None) -> Path:
    if output_dir is None:
        output_dir = artifact_dir
    md = artifact_to_markdown(artifact_dir)
    out_path = output_dir / "vault-note.md"
    out_path.write_text(md, encoding="utf-8")
    return out_path


def list_artifacts():
    if not ARTIFACTS_ROOT.exists():
        print("No artifacts directory.", file=sys.stderr)
        return []
    dirs = sorted(
        [d for d in ARTIFACTS_ROOT.iterdir() if d.is_dir()], reverse=True
    )
    for d in dirs[:10]:
        report = d / "report.md"
        meta = d / "meta.yaml"
        has_report = "report" if report.exists() else "no-report"
        has_meta = "meta" if meta.exists() else "no-meta"
        print(f"  {d.name}  [{has_report},{has_meta}]")
    return dirs


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print("Usage: research_knowledge.py <artifact_dir> | --list", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "--list":
        list_artifacts()
        return

    artifact_dir = Path(sys.argv[1]).resolve()
    if not artifact_dir.is_dir():
        print(f"Not a directory: {artifact_dir}", file=sys.stderr)
        sys.exit(1)

    out = export_artifact(artifact_dir)
    print(f"Exported: {out}")
    print(f"Copy to your Obsidian vault: {out.parent.name}/vault-note.md")


if __name__ == "__main__":
    main()
