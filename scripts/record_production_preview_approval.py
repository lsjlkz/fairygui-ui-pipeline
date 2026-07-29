#!/usr/bin/env python3
"""Create a hash-bound human approval record for the exact production preview and runtime assets."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

ALLOWED_CONFIRMATION_TYPES = {"user_confirmation", "manual_review"}
ALLOWED_RECORDED_BY = {"user", "human_reviewer"}


def normalize_relative(value: str) -> Path:
    normalized = str(PurePosixPath(value.replace("\\", "/"))).lstrip("./")
    return Path(*PurePosixPath(normalized).parts)


def resolve_inside(root: Path, value: str) -> Path:
    path = (root / normalize_relative(value)).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"Path must stay inside UIProduction: {value}") from exc
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Top-level JSON must be an object: {path}")
    return value


def evidence_hashes(root: Path) -> dict[str, str]:
    candidates = {
        "productionPreviewLineage": root / "specs" / "production_preview_lineage.json",
        "typographySpec": root / "specs" / "typography_spec.json",
        "typographyRenderTrace": root / "reports" / "typography_render_trace.json",
    }
    return {name: sha256_file(path) for name, path in candidates.items() if path.is_file()}


def read_lineage(root: Path) -> tuple[dict[str, Any], Path, str, dict[str, str]]:
    lineage_path = root / "specs" / "production_preview_lineage.json"
    if not lineage_path.is_file():
        raise FileNotFoundError(lineage_path)
    lineage = read_json(lineage_path)
    preview = lineage.get("productionPreview") if isinstance(lineage.get("productionPreview"), dict) else {}
    preview_value = str(preview.get("file") or "")
    if not preview_value:
        raise ValueError("productionPreview.file is required in production_preview_lineage.json")
    preview_path = resolve_inside(root, preview_value)
    if not preview_path.is_file():
        raise FileNotFoundError(preview_path)

    hashes: dict[str, str] = {}
    assets = lineage.get("assets")
    if not isinstance(assets, list):
        raise ValueError("production_preview_lineage.assets must be an array")
    for index, item in enumerate(assets):
        if not isinstance(item, dict):
            raise ValueError(f"assets[{index}] must be an object")
        name = str(item.get("assetName") or "")
        runtime_file = str(item.get("runtimeFile") or "")
        if not name or not runtime_file:
            raise ValueError(f"assets[{index}] requires assetName and runtimeFile")
        runtime_path = resolve_inside(root, runtime_file)
        if not runtime_path.is_file():
            raise FileNotFoundError(runtime_path)
        hashes[name] = sha256_file(runtime_path)
    return lineage, preview_path, preview_value, hashes


def pending_record(root: Path, note: str) -> dict[str, Any]:
    _, preview_path, preview_value, hashes = read_lineage(root)
    frozen_evidence = evidence_hashes(root)
    now = datetime.now(timezone.utc).isoformat()
    return {
        "version": "0.1.0",
        "status": "pending",
        "candidateFile": preview_value,
        "candidateFileSha256": sha256_file(preview_path),
        "candidateAssetHashes": hashes,
        "candidateEvidenceHashes": frozen_evidence,
        "approvedFile": None,
        "approvedFileSha256": None,
        "approvedAssetHashes": {},
        "approvedEvidenceHashes": {},
        "confirmation": None,
        "reviewNotes": [note] if note.strip() else [],
        "updatedAt": now,
    }


def approved_record(
    root: Path,
    confirmation_type: str,
    recorded_by: str,
    note: str,
) -> dict[str, Any]:
    if confirmation_type not in ALLOWED_CONFIRMATION_TYPES:
        raise ValueError("Approval requires user_confirmation or manual_review")
    if recorded_by not in ALLOWED_RECORDED_BY:
        raise ValueError("Approval must be recorded by user or human_reviewer")
    if not note.strip():
        raise ValueError("Approval requires a confirmation note")
    _, preview_path, preview_value, hashes = read_lineage(root)
    frozen_evidence = evidence_hashes(root)
    now = datetime.now(timezone.utc).isoformat()
    return {
        "version": "0.1.0",
        "status": "approved",
        "candidateFile": preview_value,
        "candidateFileSha256": sha256_file(preview_path),
        "candidateAssetHashes": hashes,
        "candidateEvidenceHashes": frozen_evidence,
        "approvedFile": preview_value,
        "approvedFileSha256": sha256_file(preview_path),
        "approvedAssetHashes": hashes,
        "approvedEvidenceHashes": frozen_evidence,
        "confirmation": {
            "type": confirmation_type,
            "recordedBy": recorded_by,
            "note": note.strip(),
            "confirmedAt": now,
        },
        "reviewNotes": [],
        "updatedAt": now,
    }


def closed_record(status: str, note: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "version": "0.1.0",
        "status": status,
        "candidateFile": None,
        "candidateFileSha256": None,
        "candidateAssetHashes": {},
        "candidateEvidenceHashes": {},
        "approvedFile": None,
        "approvedFileSha256": None,
        "approvedAssetHashes": {},
        "approvedEvidenceHashes": {},
        "confirmation": None,
        "reviewNotes": [note] if note.strip() else [],
        "updatedAt": now,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--action", required=True, choices=("pending", "approve", "reject", "supersede"))
    parser.add_argument("--confirmation-type", choices=sorted(ALLOWED_CONFIRMATION_TYPES))
    parser.add_argument("--recorded-by", choices=sorted(ALLOWED_RECORDED_BY))
    parser.add_argument("--note", default="")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    out = args.out or root / "reports" / "production_preview_approval.json"
    if not out.is_absolute():
        out = root / out
    out = out.resolve()
    try:
        out.relative_to(root)
    except ValueError:
        parser.error("--out must stay inside UIProduction")

    try:
        if args.action == "pending":
            record = pending_record(root, args.note)
        elif args.action == "approve":
            record = approved_record(root, args.confirmation_type or "", args.recorded_by or "", args.note)
        elif args.action == "reject":
            record = closed_record("rejected", args.note)
        else:
            record = closed_record("superseded", args.note)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
