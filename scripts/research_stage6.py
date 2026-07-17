#!/usr/bin/env python3
"""Deterministically package a completed Research Expert pipeline run."""

import argparse
import json
import os
import re
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path


def hermes_home() -> Path:
    configured = os.environ.get("HERMES_HOME")
    if configured:
        return Path(configured)
    return Path(os.environ.get("HOME", str(Path.home()))) / ".hermes"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or "research")[:60].rstrip("-")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def yaml_scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=True)


def yaml_list(values):
    return "[" + ", ".join(yaml_scalar(value) for value in values) + "]"


def write_meta(path: Path, payload: dict, created_utc: str, slug: str) -> None:
    meta = payload.get("meta") or {}
    labels = meta.get("labels") or {}
    search_backends = payload.get("search_backends_used", meta.get("search_backends_used", []))
    extract_backends = payload.get("extract_backends_used", meta.get("extract_backends_used", []))
    lines = [
        "schema: research-artifact/v1",
        f"created_utc: {yaml_scalar(created_utc)}",
        f"question: {yaml_scalar(payload['question'][:500])}",
        f"slug: {yaml_scalar(slug)}",
        "pipeline: [plan, search, extract, verify, synthesize]",
        f"search_backends_used: {yaml_list(search_backends)}",
        f"extract_backends_used: {yaml_list(extract_backends)}",
        f"source_count: {yaml_scalar(len(payload['sources']))}",
        f"confidence: {yaml_scalar(meta.get('confidence', payload.get('confidence', 'medium')))}",
        "labels:",
    ]
    for label in ("validated", "untested", "rejected", "pending"):
        lines.append(f"  {label}: {yaml_scalar(labels.get(label, 0))}")
    lines.extend([
        "constraints:",
        "  max_spawn_depth: 1",
        "  max_concurrent_children: 3",
        "  med_touch: false",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def package(payload: dict) -> dict:
    question = payload.get("question")
    report = payload.get("report")
    sources = payload.get("sources")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")
    if not isinstance(report, str) or not report.strip():
        raise ValueError("report must be a non-empty string")
    if not isinstance(sources, list):
        raise ValueError("sources must be a list")

    slug = slugify(payload.get("slug") or question)
    artifact_dir = hermes_home() / "research" / "artifacts" / f"{date.today().isoformat()}-{slug}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    created_utc = utc_now()

    write_meta(artifact_dir / "meta.yaml", payload, created_utc, slug)
    (artifact_dir / "report.md").write_text(report.rstrip() + "\n", encoding="utf-8")
    (artifact_dir / "sources.json").write_text(
        json.dumps({"schema": "research-sources/v1", "sources": sources}, indent=2) + "\n",
        encoding="utf-8",
    )

    trace_path = hermes_home() / "logs" / "research_trace.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace = {
        "schema": "research-trace/v1",
        "run_id": payload.get("run_id") or str(uuid.uuid4()),
        "started_utc": payload.get("started_utc", created_utc),
        "completed_utc": created_utc,
        "question": question[:200],
        "slug": f"{date.today().isoformat()}-{slug}",
        "pipeline_stages": payload.get(
            "pipeline_stages", ["plan", "search", "extract", "verify", "synthesize"]
        ),
        "stage_log": payload.get("stage_log", []),
        "outcome": payload.get("outcome", {}),
        "artifact_dir": str(artifact_dir),
        "med_touch": False,
        "soul_grounding_violations": payload.get("soul_grounding_violations", 0),
    }
    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(trace, ensure_ascii=True, separators=(",", ":")) + "\n")

    return {"artifact_dir": str(artifact_dir), "trace_path": str(trace_path), "run_id": trace["run_id"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Read the JSON payload from a file instead of stdin")
    args = parser.parse_args()
    raw = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
    try:
        result = package(json.loads(raw))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
