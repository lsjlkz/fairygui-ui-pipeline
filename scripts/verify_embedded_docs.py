#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify that the complete portable FairyGUI source documents are intact.

This check intentionally validates exact byte lengths plus required headings and
final version rows. If either source document is intentionally updated, update
references/embedded-docs-manifest.json in the same change.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    """Read a JSON object while accepting UTF-8 files with or without BOM."""
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def normalize_relative(value: str) -> Path:
    """Normalize a portable slash-separated path into a local Path."""
    normalized = str(PurePosixPath(value.replace("\\", "/"))).lstrip("./")
    return Path(*PurePosixPath(normalized).parts)


def verify(skill_root: Path) -> dict[str, Any]:
    """Return a complete integrity report for the embedded source documents."""
    skill_root = skill_root.resolve()
    manifest_path = skill_root / "references" / "embedded-docs-manifest.json"
    report: dict[str, Any] = {
        "ok": False,
        "skillRoot": str(skill_root),
        "manifest": str(manifest_path),
        "documents": [],
        "errors": [],
    }

    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        report["errors"].append({"code": "manifest_invalid", "message": str(exc), "path": str(manifest_path)})
        return report

    documents = manifest.get("documents")
    if not isinstance(documents, list) or not documents:
        report["errors"].append({"code": "documents_missing", "message": "manifest.documents must be a non-empty list"})
        return report

    for index, entry in enumerate(documents):
        item: dict[str, Any] = {"index": index, "ok": False, "errors": []}
        report["documents"].append(item)
        if not isinstance(entry, dict):
            item["errors"].append("manifest entry must be an object")
            continue

        relative = entry.get("path")
        if not isinstance(relative, str) or not relative:
            item["errors"].append("path is required")
            continue

        path = (skill_root / normalize_relative(relative)).resolve()
        item["path"] = str(path)
        try:
            path.relative_to(skill_root)
        except ValueError:
            item["errors"].append("document path escapes skill root")
            continue

        if not path.is_file():
            item["errors"].append("document file is missing")
            continue

        expected_bytes = entry.get("expectedBytes")
        actual_bytes = path.stat().st_size
        item["expectedBytes"] = expected_bytes
        item["actualBytes"] = actual_bytes
        if not isinstance(expected_bytes, int) or expected_bytes <= 0:
            item["errors"].append("expectedBytes is invalid")
        elif actual_bytes != expected_bytes:
            item["errors"].append("byte length does not match the embedded source snapshot")

        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            item["errors"].append(f"document cannot be read as UTF-8: {exc}")
            continue

        # These markers ensure the beginning, final required chapter, and final
        # version record are present, in addition to the exact byte-length gate.
        for field in ("firstHeading", "lastRequiredHeading", "requiredTailText"):
            expected = entry.get(field)
            if not isinstance(expected, str) or not expected:
                item["errors"].append(f"{field} is invalid in manifest")
            elif expected not in text:
                item["errors"].append(f"required content missing: {field}")

        item["ok"] = not item["errors"]

    # The provenance path is allowed only inside the manifest metadata. Runtime
    # instructions and scripts must not depend on the original computer path.
    forbidden_markers = (
        "D:\\ChatGPTShare\\AI文档\\",
        "D:/ChatGPTShare/AI文档/",
    )
    scan_paths = [
        skill_root / "SKILL.md",
        skill_root / "USAGE.md",
        *(skill_root / "references").glob("*.md"),
        *(skill_root / "scripts").glob("*.py"),
        *(skill_root / "agents").glob("*.yaml"),
    ]
    for path in scan_paths:
        # This verifier necessarily contains the forbidden markers it searches
        # for, so scanning its own source would always produce a false positive.
        if path.resolve() == Path(__file__).resolve():
            continue
        if not path.is_file() or path.name in {"embedded-docs-manifest.json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            report["errors"].append({
                "code": "portability_scan_failed",
                "message": str(exc),
                "path": str(path),
            })
            continue
        if any(marker in text for marker in forbidden_markers):
            report["errors"].append({
                "code": "external_ai_docs_dependency",
                "message": "runtime file still references the original AI文档 absolute path",
                "path": str(path),
            })

    report["ok"] = not report["errors"] and all(item.get("ok") for item in report["documents"])
    return report


def emit(report: dict[str, Any], output_path: Path | None) -> int:
    """Print or write a report and return a process exit code."""
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0 if report.get("ok") else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify embedded full FairyGUI documents.")
    parser.add_argument(
        "--skill-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="fairygui-ui-pipeline skill root",
    )
    parser.add_argument("--out", type=Path, help="Optional JSON report output path")
    args = parser.parse_args()
    return emit(verify(args.skill_root), args.out)


if __name__ == "__main__":
    raise SystemExit(main())
