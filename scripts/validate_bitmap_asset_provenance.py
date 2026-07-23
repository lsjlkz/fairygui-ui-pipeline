#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate bitmap provenance for style-sensitive UI icons."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

STAGES = {"asset_planning", "fairygui_assembly", "xml_generation"}
ALLOWED_SOURCE_MODES = {
    "approved_design_slice",
    "approved_sheet_slice",
    "provided_bitmap",
    "existing_package_bitmap",
    "image_generation_with_reference",
}
FORBIDDEN_SOURCE_MODES = {
    "procedural_vector",
    "procedural_raster",
    "svg",
    "font_glyph",
    "graph",
    "shape_primitive",
}
BITMAP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
PROCEDURAL_DRAW_RE = re.compile(r"\.\s*(polygon|ellipse|line|arc|rectangle|rounded_rectangle)\s*\(", re.IGNORECASE)
PROCEDURAL_MARKERS = (
    "draw.polygon",
    "draw.ellipse",
    "draw.line",
    "draw.arc",
    "draw.rectangle",
    "draw.rounded_rectangle",
    "svgwrite",
    "<svg",
    "path2d",
    "canvasrenderingcontext2d",
)
SCRIPT_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".ps1", ".cs"}
ICON_ROLE_RE = re.compile(r"(?:^|[_\-])(icon|badge|crest|emblem)(?:$|[_\-])", re.IGNORECASE)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def normalized(value: Any) -> str:
    return "".join(character.lower() for character in str(value) if character.isalnum())


def normalize_relative(value: str) -> Path:
    normalized_value = str(PurePosixPath(value.replace("\\", "/"))).lstrip("./")
    return Path(*PurePosixPath(normalized_value).parts)


def add(report: dict[str, Any], level: str, code: str, message: str, path: Path | None = None) -> None:
    item: dict[str, str] = {"code": code, "message": message}
    if path is not None:
        item["path"] = str(path)
    report[level].append(item)


def is_icon_asset(asset: dict[str, Any]) -> bool:
    asset_type = str(asset.get("type", "")).strip().lower()
    name = str(asset.get("name", "")).strip().lower()
    fgui = asset.get("fgui") if isinstance(asset.get("fgui"), dict) else {}
    layer = str(fgui.get("layer", "")).strip().lower()
    return asset_type == "icon" or layer == "icon" or name.startswith("icon_") or bool(ICON_ROLE_RE.search(name))


def positive_crop(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(item, int) for item in value)
        and value[0] >= 0
        and value[1] >= 0
        and value[2] > 0
        and value[3] > 0
    )


def source_file_exists(root: Path, value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = Path(value)
    resolved = path if path.is_absolute() else root / normalize_relative(value)
    return resolved.is_file()


def validate_icon_asset(
    report: dict[str, Any],
    root: Path,
    manifest_path: Path,
    asset: dict[str, Any],
    index: int,
) -> None:
    name = str(asset.get("name", f"assets[{index}]"))
    file_name = asset.get("file")
    extension = PurePosixPath(str(file_name).replace("\\", "/")).suffix.lower() if isinstance(file_name, str) else ""
    if extension not in BITMAP_EXTENSIONS:
        add(report, "errors", "icon_file_format_forbidden", f"图标 {name} 必须使用审核后的位图文件，当前扩展名={extension or '<none>'}", manifest_path)

    source = asset.get("assetSource")
    if not isinstance(source, dict):
        add(report, "errors", "icon_asset_source_missing", f"图标 {name} 缺少 assetSource 位图来源声明", manifest_path)
        return

    mode = source.get("mode")
    if mode in FORBIDDEN_SOURCE_MODES:
        add(report, "errors", "icon_asset_source_mode_forbidden", f"图标 {name} 禁止使用来源模式: {mode}", manifest_path)
        return
    if mode not in ALLOWED_SOURCE_MODES:
        add(report, "errors", "icon_asset_source_mode_invalid", f"图标 {name}.assetSource.mode 非法: {mode}", manifest_path)
        return

    review_status = source.get("reviewStatus")
    if review_status != "approved":
        add(report, "errors", "icon_asset_review_missing", f"图标 {name} 的位图来源尚未标记 reviewStatus=approved", manifest_path)

    if mode in {"approved_design_slice", "approved_sheet_slice"}:
        source_file = source.get("sourceFile")
        if not source_file_exists(root, source_file):
            add(report, "errors", "icon_slice_source_missing", f"图标 {name} 的切图来源不存在: {source_file}", manifest_path)
        if not positive_crop(source.get("crop")):
            add(report, "errors", "icon_slice_crop_invalid", f"图标 {name} 缺少合法 crop=[x,y,width,height]", manifest_path)
    elif mode in {"provided_bitmap", "existing_package_bitmap"}:
        source_file = source.get("sourceFile")
        if not source_file_exists(root, source_file):
            add(report, "errors", "icon_bitmap_source_missing", f"图标 {name} 的原始位图不存在: {source_file}", manifest_path)
    elif mode == "image_generation_with_reference":
        references = source.get("referenceFiles")
        if not isinstance(references, list) or not references:
            add(report, "errors", "icon_generation_reference_missing", f"图标 {name} 使用图片生成但缺少 referenceFiles", manifest_path)
        else:
            for reference in references:
                if not source_file_exists(root, reference):
                    add(report, "errors", "icon_generation_reference_missing", f"图标 {name} 的参考图不存在: {reference}", manifest_path)
        evidence = source.get("evidenceFile")
        if not source_file_exists(root, evidence):
            add(report, "errors", "icon_generation_evidence_missing", f"图标 {name} 缺少图片生成提示词/审核记录: {evidence}", manifest_path)


def scan_procedural_scripts(
    report: dict[str, Any],
    root: Path,
    icon_assets: list[dict[str, Any]],
) -> None:
    scripts_dir = root / "scripts"
    if not scripts_dir.is_dir() or not icon_assets:
        return

    icon_names = [str(asset.get("name", "")) for asset in icon_assets if isinstance(asset.get("name"), str)]
    for path in scripts_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SCRIPT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig").lower()
        except (OSError, UnicodeDecodeError):
            continue
        markers = [marker for marker in PROCEDURAL_MARKERS if marker in text]
        draw_operations = sorted(set(PROCEDURAL_DRAW_RE.findall(text))) if "imagedraw" in text else []
        markers.extend(f"ImageDraw.{operation}" for operation in draw_operations)
        if not markers:
            continue
        referenced = [name for name in icon_names if name.lower() in text]
        if referenced:
            add(
                report,
                "errors",
                "procedural_icon_generator_detected",
                f"脚本使用程序化几何绘制生产图标 {referenced}: markers={markers}",
                path,
            )


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Bitmap Asset Provenance Report",
        "",
        f"- result: {'PASS' if report['ok'] else 'BLOCKED'}",
        f"- stage: {report['stage']}",
        "",
        "## Errors",
        "",
    ]
    if report["errors"]:
        for item in report["errors"]:
            location = f" ({item['path']})" if item.get("path") else ""
            lines.append(f"- [{item['code']}] {item['message']}{location}")
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    if report["warnings"]:
        for item in report["warnings"]:
            location = f" ({item['path']})" if item.get("path") else ""
            lines.append(f"- [{item['code']}] {item['message']}{location}")
    else:
        lines.append("- none")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate(root: Path, stage: str) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = root / "manifests" / "asset_manifest.json"
    report: dict[str, Any] = {
        "ok": False,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "stage": stage,
        "errors": [],
        "warnings": [],
        "summary": {"assets": 0, "icons": 0, "scriptsScanned": 0},
    }

    if not manifest_path.is_file():
        add(report, "errors", "bitmap_provenance_manifest_missing", "缺少 asset_manifest.json", manifest_path)
        return report
    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        add(report, "errors", "bitmap_provenance_manifest_invalid", f"asset_manifest.json 无法解析: {exc}", manifest_path)
        return report

    assets = manifest.get("assets")
    if not isinstance(assets, list):
        add(report, "errors", "bitmap_provenance_assets_invalid", "manifest.assets 必须是数组", manifest_path)
        return report

    icon_assets = [asset for asset in assets if isinstance(asset, dict) and is_icon_asset(asset)]
    report["summary"]["assets"] = len(assets)
    report["summary"]["icons"] = len(icon_assets)
    for index, asset in enumerate(assets):
        if isinstance(asset, dict) and is_icon_asset(asset):
            validate_icon_asset(report, root, manifest_path, asset, index)

    scripts_dir = root / "scripts"
    if scripts_dir.is_dir():
        report["summary"]["scriptsScanned"] = sum(
            1 for path in scripts_dir.rglob("*") if path.is_file() and path.suffix.lower() in SCRIPT_EXTENSIONS
        )
    scan_procedural_scripts(report, root, icon_assets)

    report["ok"] = not report["errors"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate bitmap provenance for style-sensitive icons.")
    parser.add_argument("--root", type=Path, required=True, help="UIProduction root directory")
    parser.add_argument("--stage", choices=sorted(STAGES), default="xml_generation")
    parser.add_argument("--out", type=Path, help="JSON report output path")
    parser.add_argument("--report-md", type=Path, help="Markdown report output path")
    args = parser.parse_args()

    report = validate(args.root, args.stage)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    if args.report_md:
        write_markdown(args.report_md, report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
