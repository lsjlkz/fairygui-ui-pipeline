#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create or update a full-screen design approval record deterministically.

Important: this script records an approval; it does not decide whether approval
was actually granted. Invoke the `approve` action only after explicit user or
human-reviewer confirmation of the exact file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from image_metadata import ImageMetadataError, read_image_metadata

ALLOWED_STAGES = {
    "semantic_analysis",
    "layout_analysis",
    "asset_planning",
    "resource_generation",
    "fairygui_assembly",
    "xml_generation",
}
ALLOWED_CONFIRMATION_TYPES = {"user_confirmation", "manual_review"}
ALLOWED_RECORDED_BY = {"user", "human_reviewer"}


def normalize_relative(value: str) -> Path:
    normalized = str(PurePosixPath(value.replace("\\", "/"))).lstrip("./")
    return Path(*PurePosixPath(normalized).parts)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_inside(root: Path, relative_value: str) -> Path:
    path = (root / normalize_relative(relative_value)).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("design file must stay inside UIProduction") from exc
    return path


def build_pending(root: Path, candidate_file: str | None, note: str) -> dict[str, Any]:
    resolution = None
    if candidate_file:
        path = resolve_inside(root, candidate_file)
        if not path.is_file():
            raise FileNotFoundError(path)
        metadata = read_image_metadata(path)
        resolution = [metadata["width"], metadata["height"]]

    now = datetime.now(timezone.utc).isoformat()
    return {
        "version": "0.1.0",
        "status": "pending",
        "candidateFile": candidate_file,
        "approvedFile": None,
        "approvedFileSha256": None,
        "resolution": resolution,
        "approvedFor": [],
        "confirmation": None,
        "knownDeviations": [],
        "reviewNotes": [note] if note else [],
        "updatedAt": now,
    }


def build_approved(
    root: Path,
    file_value: str,
    approved_for: list[str],
    confirmation_type: str,
    recorded_by: str,
    note: str,
) -> dict[str, Any]:
    unknown = [stage for stage in approved_for if stage not in ALLOWED_STAGES]
    if unknown:
        raise ValueError(f"unknown approval stages: {unknown}")
    if not approved_for:
        raise ValueError("approve requires at least one --approved-for stage")
    if confirmation_type not in ALLOWED_CONFIRMATION_TYPES:
        raise ValueError("approve requires user_confirmation or manual_review")
    if recorded_by not in ALLOWED_RECORDED_BY:
        raise ValueError("approve must be recorded by user or human_reviewer")
    if not note.strip():
        raise ValueError("approve requires a confirmation note")

    design_path = resolve_inside(root, file_value)
    if not design_path.is_file():
        raise FileNotFoundError(design_path)
    metadata = read_image_metadata(design_path)
    now = datetime.now(timezone.utc).isoformat()

    return {
        "version": "0.1.0",
        "status": "approved",
        "candidateFile": file_value,
        "approvedFile": file_value,
        "approvedFileSha256": sha256_file(design_path),
        "resolution": [metadata["width"], metadata["height"]],
        "approvedFor": approved_for,
        "confirmation": {
            "type": confirmation_type,
            "recordedBy": recorded_by,
            "note": note.strip(),
            "confirmedAt": now,
        },
        "knownDeviations": [],
        "reviewNotes": [],
        "updatedAt": now,
    }


def build_closed(status: str, note: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "version": "0.1.0",
        "status": status,
        "candidateFile": None,
        "approvedFile": None,
        "approvedFileSha256": None,
        "resolution": None,
        "approvedFor": [],
        "confirmation": None,
        "knownDeviations": [],
        "reviewNotes": [note] if note else [],
        "updatedAt": now,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Record pending, approved, rejected, or superseded design state.")
    parser.add_argument("--root", type=Path, required=True, help="UIProduction root directory")
    parser.add_argument("--action", choices=("pending", "approve", "reject", "supersede"), required=True)
    parser.add_argument("--file", default="", help="Project-relative design image path")
    parser.add_argument("--approved-for", nargs="*", default=[])
    parser.add_argument("--confirmation-type", choices=sorted(ALLOWED_CONFIRMATION_TYPES))
    parser.add_argument("--recorded-by", choices=sorted(ALLOWED_RECORDED_BY))
    parser.add_argument("--note", default="")
    parser.add_argument("--out", type=Path, help="Defaults to UIProduction/reports/design_approval.json")
    args = parser.parse_args()

    root = args.root.resolve()
    if args.out:
        out = args.out if args.out.is_absolute() else root / args.out
        out = out.resolve()
        try:
            out.relative_to(root)
        except ValueError:
            parser.error("--out must stay inside UIProduction")
    else:
        out = root / "reports" / "design_approval.json"

    try:
        if args.action == "pending":
            record = build_pending(root, args.file or None, args.note)
        elif args.action == "approve":
            if not args.file:
                raise ValueError("approve requires --file")
            record = build_approved(
                root,
                args.file,
                args.approved_for,
                args.confirmation_type or "",
                args.recorded_by or "",
                args.note,
            )
        elif args.action == "reject":
            record = build_closed("rejected", args.note)
        else:
            record = build_closed("superseded", args.note)
    except (OSError, ValueError, ImageMetadataError) as exc:
        parser.error(str(exc))

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
