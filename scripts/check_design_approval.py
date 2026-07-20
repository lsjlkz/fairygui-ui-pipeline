#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hard gate for full-screen UI design approval.

The AI may generate mockups and pending approval records, but downstream stages
must not continue until a human has approved the exact image bytes.
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
REQUIRED_BRIEF_HEADINGS = (
    "Confirmed Requirement Sources",
    "Screen Goal",
    "Design Resolution",
    "Primary Reference And Allowed Uses",
    "Functional Region Map",
    "Required Components And States",
    "Visual Hierarchy",
    "Art Direction",
    "Text And Localization Policy",
    "Asset Separation Constraints",
    "Negative Constraints",
    "Mockup Acceptance Criteria",
    "Known Risks",
)


def add(report: dict[str, Any], level: str, code: str, message: str, path: Path | None = None) -> None:
    item: dict[str, str] = {"code": code, "message": message}
    if path is not None:
        item["path"] = str(path)
    report[level].append(item)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def normalize_relative(value: str) -> Path:
    normalized = str(PurePosixPath(value.replace("\\", "/"))).lstrip("./")
    return Path(*PurePosixPath(normalized).parts)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_positive_pair(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(isinstance(item, int) and item > 0 for item in value)


def validate(root: Path, stage: str) -> dict[str, Any]:
    specs_dir = root / "specs"
    reports_dir = root / "reports"
    ui_spec_path = specs_dir / "ui_spec.md"
    brief_path = specs_dir / "visual_design_brief.md"
    approval_path = reports_dir / "design_approval.json"

    report: dict[str, Any] = {
        "approved": False,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "stage": stage,
        "approvedFile": None,
        "approvedFileSha256": None,
        "blockers": [],
        "warnings": [],
    }

    if not ui_spec_path.is_file():
        add(report, "blockers", "ui_spec_missing", "缺少 specs/ui_spec.md", ui_spec_path)
    if not brief_path.is_file():
        add(report, "blockers", "visual_design_brief_missing", "缺少 specs/visual_design_brief.md", brief_path)
    else:
        brief_text = brief_path.read_text(encoding="utf-8-sig")
        normalized_brief = brief_text.lower()
        for heading in REQUIRED_BRIEF_HEADINGS:
            if f"## {heading.lower()}" not in normalized_brief:
                add(report, "blockers", "visual_design_brief_section_missing", f"visual_design_brief.md 缺少章节: {heading}", brief_path)

    if not approval_path.is_file():
        add(report, "blockers", "design_approval_missing", "缺少 reports/design_approval.json", approval_path)
        return report

    try:
        approval = load_json(approval_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        add(report, "blockers", "design_approval_invalid", f"design_approval.json 无法解析: {exc}", approval_path)
        return report

    status = approval.get("status")
    if status != "approved":
        add(report, "blockers", "design_not_approved", f"设计稿状态不是 approved: {status}", approval_path)

    approved_for = approval.get("approvedFor")
    if not isinstance(approved_for, list):
        add(report, "blockers", "approved_for_invalid", "approvedFor 必须是数组", approval_path)
    elif stage not in approved_for:
        add(report, "blockers", "stage_not_approved", f"设计稿未批准用于阶段: {stage}", approval_path)
    else:
        unknown = [item for item in approved_for if item not in ALLOWED_STAGES]
        if unknown:
            add(report, "warnings", "unknown_approval_scopes", f"approvedFor 包含未知阶段: {unknown}", approval_path)

    confirmation = approval.get("confirmation")
    if not isinstance(confirmation, dict):
        add(report, "blockers", "human_confirmation_missing", "缺少人工确认记录 confirmation", approval_path)
    else:
        confirmation_type = confirmation.get("type")
        recorded_by = confirmation.get("recordedBy")
        if confirmation_type not in ALLOWED_CONFIRMATION_TYPES:
            add(report, "blockers", "confirmation_type_invalid", f"确认类型不是人工确认: {confirmation_type}", approval_path)
        if recorded_by not in ALLOWED_RECORDED_BY:
            add(report, "blockers", "confirmation_origin_invalid", f"确认来源不是用户/人工审核人: {recorded_by}", approval_path)
        if not isinstance(confirmation.get("confirmedAt"), str) or not confirmation.get("confirmedAt"):
            add(report, "blockers", "confirmation_time_missing", "confirmation.confirmedAt 缺失", approval_path)
        if not isinstance(confirmation.get("note"), str) or not confirmation.get("note"):
            add(report, "warnings", "confirmation_note_missing", "建议记录用户确认的具体说明", approval_path)

    approved_file = approval.get("approvedFile")
    candidate_file = approval.get("candidateFile")
    if candidate_file is not None and candidate_file != approved_file:
        add(report, "blockers", "candidate_approved_file_mismatch", "candidateFile 与 approvedFile 不一致，必须重新确认最终文件", approval_path)
    if not isinstance(approved_file, str) or not approved_file:
        add(report, "blockers", "approved_file_missing", "approvedFile 缺失", approval_path)
        return report

    relative_path = normalize_relative(approved_file)
    design_path = (root / relative_path).resolve()
    root_resolved = root.resolve()
    try:
        design_path.relative_to(root_resolved)
    except ValueError:
        add(report, "blockers", "approved_file_outside_root", "approvedFile 必须位于当前 UIProduction 目录内", design_path)
        return report

    report["approvedFile"] = str(design_path)
    if not design_path.is_file():
        add(report, "blockers", "approved_file_not_found", "已批准设计图文件不存在", design_path)
        return report

    try:
        metadata = read_image_metadata(design_path)
    except (OSError, ImageMetadataError) as exc:
        add(report, "blockers", "approved_image_invalid", f"已批准设计图无法读取: {exc}", design_path)
        return report

    declared_resolution = approval.get("resolution")
    actual_resolution = [metadata["width"], metadata["height"]]
    if not is_positive_pair(declared_resolution):
        add(report, "blockers", "approval_resolution_invalid", "resolution 必须是 [width,height]", approval_path)
    elif declared_resolution != actual_resolution:
        add(
            report,
            "blockers",
            "approval_resolution_mismatch",
            f"审批记录分辨率 {declared_resolution} 与实际设计图像素 {actual_resolution} 不一致",
            design_path,
        )

    actual_sha256 = sha256_file(design_path)
    report["approvedFileSha256"] = actual_sha256
    declared_sha256 = approval.get("approvedFileSha256")
    if not isinstance(declared_sha256, str) or len(declared_sha256) != 64:
        add(report, "blockers", "approved_file_hash_missing", "approvedFileSha256 缺失或格式错误", approval_path)
    elif declared_sha256.lower() != actual_sha256:
        add(report, "blockers", "approved_file_changed", "设计图在确认后已发生变化，必须重新确认", design_path)

    if "generated/design" not in str(PurePosixPath(approved_file.replace("\\", "/"))):
        add(report, "warnings", "nonstandard_design_path", "建议将已确认设计图存放在 generated/design/", design_path)

    report["approved"] = not report["blockers"]
    return report


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = ["# 设计稿确认阻塞报告", ""]
    if report["approved"]:
        lines.extend([
            "## 结果",
            "",
            f"设计稿已确认，可以进入 `{report['stage']}` 阶段。",
            "",
            f"- approvedFile: `{report['approvedFile']}`",
            f"- sha256: `{report['approvedFileSha256']}`",
            "",
        ])
    else:
        lines.extend(["## 阻塞原因", ""])
        for item in report["blockers"]:
            location = f"（{item['path']}）" if item.get("path") else ""
            lines.append(f"- [{item['code']}] {item['message']}{location}")
        lines.extend([
            "",
            "## 当前允许的操作",
            "",
            "- 修订 visual_design_brief.md",
            "- 生成或修改整屏设计稿",
            "- 输出设计稿评审记录",
            "- 保持 design_approval.json 为 pending/rejected",
            "- 请求用户确认具体设计文件",
            "",
        ])

    lines.extend(["## 警告", ""])
    if report["warnings"]:
        for item in report["warnings"]:
            location = f"（{item['path']}）" if item.get("path") else ""
            lines.append(f"- [{item['code']}] {item['message']}{location}")
    else:
        lines.append("- 无")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check explicit human approval for a full-screen UI design mockup.")
    parser.add_argument("--root", type=Path, required=True, help="UIProduction root directory")
    parser.add_argument("--stage", choices=sorted(ALLOWED_STAGES), required=True, help="Requested downstream stage")
    parser.add_argument("--out", type=Path, help="JSON report output path")
    parser.add_argument("--report-md", type=Path, help="Human-readable blocking report output path")
    args = parser.parse_args()

    report = validate(args.root.resolve(), args.stage)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    if args.report_md:
        write_markdown(args.report_md, report)

    return 0 if report["approved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
