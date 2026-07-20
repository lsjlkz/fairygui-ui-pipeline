#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preflight gate for FairyGUI XML Strict Mode.

This script does not generate XML. It checks whether the project has enough
verified information to allow XML generation and writes a machine-readable
report plus an optional human-readable XML生成阻塞报告.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from check_design_approval import validate as validate_design_approval_gate
from image_metadata import ImageMetadataError, read_image_metadata
from verify_embedded_docs import verify as verify_embedded_docs

PACKAGE_ID_RE = re.compile(r"^[a-z0-9]{8}$")
RESOURCE_ID_RE = re.compile(r"^[a-z0-9]{2,16}$")
REFERENCE_ROLES = {
    "style_only", "layout_only", "asset_shape", "color_palette",
    "style_and_layout", "full_reconstruction",
}
REFERENCE_USES = {"style", "composition", "layout", "asset_generation", "color", "shape", "reconstruction"}
SCALE_POLICIES = {"pixel_exact", "explicit_scale", "nine_slice", "tile", "fit", "fill", "relation_driven"}
RENDER_MODES = {"normal", "nine_slice", "tile", "fit", "fill", "loader_fit", "loader_fill", "relation_driven"}
RENDER_MODES_BY_POLICY = {
    "pixel_exact": {"normal"},
    "explicit_scale": {"normal"},
    "nine_slice": {"nine_slice"},
    "tile": {"tile"},
    "fit": {"fit", "loader_fit"},
    "fill": {"fill", "loader_fill"},
    "relation_driven": {"relation_driven"},
}

REQUIRED_FGUI_SPEC_HEADINGS = (
    "Package",
    "Components",
    "Display List",
    "Layout Region Table",
    "Slot Table",
    "Component Ownership Table",
    "Controllers",
    "Gear Mapping Table",
    "Transitions",
    "Relations",
    "Unity Bindings",
    "Automation Risks",
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def normalize_relative(value: str) -> Path:
    normalized = str(PurePosixPath(value.replace("\\", "/"))).lstrip("./")
    return Path(*PurePosixPath(normalized).parts)


def add(report: dict[str, Any], level: str, code: str, message: str, path: Path | None = None) -> None:
    item: dict[str, str] = {"code": code, "message": message}
    if path is not None:
        item["path"] = str(path)
    report[level].append(item)


def require_file(report: dict[str, Any], path: Path, code: str, label: str) -> bool:
    if not path.is_file():
        add(report, "blockers", code, f"缺少 {label}", path)
        return False
    return True


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def is_positive_pair(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(isinstance(v, int) and v > 0 for v in value)


def validate_manifest(report: dict[str, Any], path: Path, force_visual_reference: bool) -> tuple[dict[str, Any], str | None]:
    try:
        manifest = load_json(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        add(report, "blockers", "manifest_invalid", f"asset_manifest.json 无法解析: {exc}", path)
        return {}, None

    production = manifest.get("production", {})
    generate_visual_assets = force_visual_reference
    requires_visual_reference = force_visual_reference
    if not isinstance(production, dict):
        add(report, "blockers", "manifest_production_invalid", "manifest.production 必须是对象", path)
    else:
        if force_visual_reference and production.get("generateVisualAssets") is not True:
            add(report, "blockers", "resource_generation_not_declared", "使用 --resource-generation 时必须设置 production.generateVisualAssets=true", path)
        if force_visual_reference and production.get("requiresVisualReference") is not True:
            add(report, "blockers", "visual_reference_requirement_not_declared", "使用 --resource-generation 时必须设置 production.requiresVisualReference=true", path)
        generate_visual_assets = generate_visual_assets or production.get("generateVisualAssets") is True
        requires_visual_reference = requires_visual_reference or production.get("requiresVisualReference") is True
        if generate_visual_assets and not requires_visual_reference:
            add(report, "blockers", "visual_reference_not_required", "视觉资源生产必须设置 production.requiresVisualReference=true", path)

    references = manifest.get("referenceImages", [])
    primary_count = 0
    if not isinstance(references, list):
        add(report, "blockers", "reference_images_invalid", "manifest.referenceImages 必须是数组", path)
        references = []
    for index, reference in enumerate(references):
        base = f"referenceImages[{index}]"
        if not isinstance(reference, dict):
            add(report, "blockers", "reference_image_invalid", f"{base} 必须是对象", path)
            continue
        if not isinstance(reference.get("file"), str) or not reference.get("file"):
            add(report, "blockers", "reference_file_missing", f"{base}.file 缺失", path)
        if reference.get("role") not in REFERENCE_ROLES:
            add(report, "blockers", "reference_role_invalid", f"{base}.role 非法", path)
        if not is_positive_pair(reference.get("resolution")):
            add(report, "blockers", "reference_resolution_invalid", f"{base}.resolution 必须是 [width,height]", path)
        if not isinstance(reference.get("isPrimary"), bool):
            add(report, "blockers", "reference_primary_invalid", f"{base}.isPrimary 必须是布尔值", path)
        elif reference.get("isPrimary") is True:
            primary_count += 1
        allowed_uses = reference.get("allowedUses")
        if not isinstance(allowed_uses, list) or not allowed_uses:
            add(report, "blockers", "reference_allowed_uses_missing", f"{base}.allowedUses 必须是非空数组", path)
        elif any(use not in REFERENCE_USES for use in allowed_uses):
            add(report, "blockers", "reference_allowed_use_invalid", f"{base}.allowedUses 包含非法值", path)
    if generate_visual_assets or requires_visual_reference:
        if not references:
            add(report, "blockers", "visual_reference_missing", "视觉资源生产缺少参考图", path)
        if primary_count < 1:
            add(report, "blockers", "primary_reference_missing", "视觉资源生产缺少主参考图", path)
    if primary_count > 1:
        add(report, "warnings", "multiple_primary_references", "存在多个主参考图，必须在 ui_spec.md 记录融合规则", path)

    package = manifest.get("package")
    package_name: str | None = None
    if not isinstance(package, dict):
        add(report, "blockers", "manifest_package_missing", "manifest.package 必须是对象", path)
    else:
        raw_name = package.get("name")
        if not isinstance(raw_name, str) or not raw_name:
            add(report, "blockers", "manifest_package_name_missing", "manifest.package.name 缺失", path)
        else:
            package_name = raw_name

    assets = manifest.get("assets")
    if not isinstance(assets, list):
        add(report, "blockers", "manifest_assets_invalid", "manifest.assets 必须是数组", path)
    else:
        if not assets:
            add(report, "warnings", "manifest_assets_empty", "manifest.assets 为空；仅在纯文本/纯组件包中合理", path)
        names: set[str] = set()
        for index, asset in enumerate(assets):
            base = f"assets[{index}]"
            if not isinstance(asset, dict):
                add(report, "blockers", "manifest_asset_invalid", f"{base} 必须是对象", path)
                continue
            name = asset.get("name")
            file_name = asset.get("file")
            fgui = asset.get("fgui")
            if not isinstance(name, str) or not name:
                add(report, "blockers", "manifest_asset_name_missing", f"{base}.name 缺失", path)
            elif name in names:
                add(report, "blockers", "manifest_asset_name_duplicate", f"资源名重复: {name}", path)
            else:
                names.add(name)
            if not isinstance(file_name, str) or not file_name:
                add(report, "blockers", "manifest_asset_file_missing", f"{base}.file 缺失", path)
            extension = PurePosixPath(file_name.replace("\\", "/")).suffix.lower() if isinstance(file_name, str) else ""
            resource_type = fgui.get("resourceType") if isinstance(fgui, dict) else None
            is_bitmap = resource_type in {"image", "atlas", "movieclip"} or extension in {".png", ".jpg", ".jpeg", ".webp"}
            if is_bitmap:
                source_size = asset.get("sourcePixelSize")
                display_size = asset.get("displaySize")
                scale_policy = asset.get("scalePolicy")
                render_mode = asset.get("renderMode")
                if not is_positive_pair(source_size):
                    add(report, "blockers", "asset_source_size_missing", f"{base}.sourcePixelSize 缺失或非法", path)
                if not is_positive_pair(display_size):
                    add(report, "blockers", "asset_display_size_missing", f"{base}.displaySize 缺失或非法", path)
                if scale_policy not in SCALE_POLICIES:
                    add(report, "blockers", "asset_scale_policy_invalid", f"{base}.scalePolicy 缺失或非法", path)
                if render_mode not in RENDER_MODES:
                    add(report, "blockers", "asset_render_mode_invalid", f"{base}.renderMode 缺失或非法", path)
                elif scale_policy in RENDER_MODES_BY_POLICY and render_mode not in RENDER_MODES_BY_POLICY[scale_policy]:
                    add(report, "blockers", "asset_render_mode_mismatch", f"{base}.renderMode 与 scalePolicy 不匹配", path)
                if scale_policy == "pixel_exact" and is_positive_pair(source_size) and is_positive_pair(display_size) and source_size != display_size:
                    add(report, "blockers", "pixel_exact_size_mismatch", f"{base} 使用 pixel_exact 但 sourcePixelSize != displaySize", path)
                if scale_policy == "nine_slice":
                    grid = asset.get("nineSliceGrid")
                    valid_grid = isinstance(grid, list) and len(grid) == 4 and all(isinstance(v, int) and v >= 0 for v in grid) and grid[2] > 0 and grid[3] > 0
                    if render_mode != "nine_slice" or not valid_grid:
                        add(report, "blockers", "nine_slice_invalid", f"{base} 的 nine_slice 配置不完整", path)
                    elif is_positive_pair(source_size) and (grid[0] + grid[2] > source_size[0] or grid[1] + grid[3] > source_size[1]):
                        add(report, "blockers", "nine_slice_out_of_bounds", f"{base}.nineSliceGrid 超出 sourcePixelSize", path)
                if "size" in asset:
                    add(report, "warnings", "legacy_asset_size", f"{base}.size 是旧字段，不能替代 sourcePixelSize/displaySize", path)
            if not isinstance(fgui, dict) or not isinstance(fgui.get("resourceType"), str):
                add(report, "blockers", "manifest_fgui_mapping_missing", f"{base}.fgui.resourceType 缺失", path)

    return manifest, package_name


def validate_registry(
    report: dict[str, Any],
    path: Path,
    package_name: str | None,
) -> tuple[dict[str, Any], str | None]:
    try:
        registry = load_json(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        add(report, "blockers", "registry_invalid", f"fgui_id_registry.json 无法解析: {exc}", path)
        return {}, None

    packages = registry.get("packages")
    if not isinstance(packages, dict):
        add(report, "blockers", "registry_packages_missing", "registry.packages 必须是对象", path)
        return registry, None

    if not package_name:
        return registry, None

    package = packages.get(package_name)
    if not isinstance(package, dict):
        add(report, "blockers", "registry_package_missing", f"registry 中缺少包: {package_name}", path)
        return registry, None

    package_id = package.get("id") or package.get("packageId")
    if not isinstance(package_id, str) or not PACKAGE_ID_RE.fullmatch(package_id):
        add(
            report,
            "blockers",
            "registry_package_id_invalid",
            f"包 {package_name} 的 ID 必须是 8 位小写字母数字",
            path,
        )
        package_id = None

    resources = package.get("resources")
    if not isinstance(resources, dict) or not resources:
        add(report, "blockers", "registry_resources_empty", f"包 {package_name} 没有稳定资源 ID 表", path)
    else:
        seen: set[str] = set()
        for resource_name, resource_id in resources.items():
            if not isinstance(resource_id, str) or not RESOURCE_ID_RE.fullmatch(resource_id):
                add(
                    report,
                    "blockers",
                    "registry_resource_id_invalid",
                    f"资源 {resource_name} 的 ID 必须是 2-16 位小写字母数字",
                    path,
                )
                continue
            if resource_id in seen:
                add(report, "blockers", "registry_resource_id_duplicate", f"资源 ID 重复: {resource_id}", path)
            seen.add(resource_id)

    instances = package.get("instances")
    if not isinstance(instances, dict):
        add(report, "blockers", "registry_instances_missing", f"包 {package_name} 缺少 instances 稳定实例 ID 表", path)

    return registry, package_id


def validate_manifest_registry_alignment(
    report: dict[str, Any],
    manifest: dict[str, Any],
    registry: dict[str, Any],
    package_name: str | None,
    registry_path: Path,
) -> None:
    if not package_name:
        return

    packages = registry.get("packages", {})
    package = packages.get(package_name) if isinstance(packages, dict) else None
    resources = package.get("resources", {}) if isinstance(package, dict) else {}
    if not isinstance(resources, dict):
        return

    registry_names: set[str] = set()
    for resource_name in resources:
        normalized = str(PurePosixPath(str(resource_name).replace("\\", "/")))
        resource_path = PurePosixPath(normalized)
        registry_names.update({normalized, resource_path.name, resource_path.stem})

    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        return

    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            continue
        name = asset.get("name")
        file_name = asset.get("file")
        candidates: set[str] = set()
        if isinstance(name, str) and name:
            candidates.add(name)
        if isinstance(file_name, str) and file_name:
            asset_path = PurePosixPath(str(PurePosixPath(file_name.replace("\\", "/"))))
            candidates.update({asset_path.name, asset_path.stem})
        if candidates and not candidates.intersection(registry_names):
            add(
                report,
                "blockers",
                "manifest_asset_unregistered",
                f"manifest 资源未在包 {package_name} 的 registry.resources 中登记: assets[{index}] {sorted(candidates)}",
                registry_path,
            )


def parse_markdown_table(text: str, heading: str) -> tuple[list[str], list[dict[str, str]]]:
    lines = text.splitlines()
    start = None
    heading_pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.IGNORECASE)
    for index, line in enumerate(lines):
        if heading_pattern.match(line.strip()):
            start = index + 1
            break
    if start is None:
        return [], []

    table_lines: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines.append(stripped)
    if len(table_lines) < 2:
        return [], []

    def cells(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip("|").split("|")]

    headers = [cell.lower() for cell in cells(table_lines[0])]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        values = cells(line)
        if len(values) != len(headers):
            continue
        rows.append(dict(zip(headers, values)))
    return headers, rows


def parse_document_size(value: str) -> list[int] | None:
    numbers = re.findall(r"\d+", value)
    if len(numbers) != 2:
        return None
    result = [int(numbers[0]), int(numbers[1])]
    return result if all(item > 0 for item in result) else None


def validate_fgui_spec(report: dict[str, Any], path: Path, manifest: dict[str, Any]) -> None:
    text = read_text(path)
    normalized = text.lower()
    for heading in REQUIRED_FGUI_SPEC_HEADINGS:
        if heading.lower() not in normalized:
            add(report, "blockers", "fgui_spec_section_missing", f"fgui_spec.md 缺少章节: {heading}", path)

    if "|" not in text:
        add(report, "blockers", "fgui_spec_tables_missing", "fgui_spec.md 未检测到表格，无法校验图片尺寸", path)
        return

    headers, rows = parse_markdown_table(text, "Display List")
    required_columns = {"name", "node type", "asset name", "size", "size source"}
    missing_columns = sorted(required_columns.difference(headers))
    if missing_columns:
        add(report, "blockers", "fgui_display_list_columns_missing", f"Display List 缺少列: {missing_columns}", path)
        return

    assets = manifest.get("assets", [])
    assets_by_name = {
        asset.get("name"): asset
        for asset in assets
        if isinstance(asset, dict) and isinstance(asset.get("name"), str)
    } if isinstance(assets, list) else {}

    for index, row in enumerate(rows):
        if row.get("node type", "").strip().lower() != "image":
            continue
        asset_name = row.get("asset name", "").strip().strip("`")
        asset = assets_by_name.get(asset_name)
        if not isinstance(asset, dict):
            add(report, "blockers", "fgui_asset_unresolved", f"Display List 图片行 {index} 的 Asset Name 未在 manifest 注册: {asset_name}", path)
            continue
        document_size = parse_document_size(row.get("size", ""))
        display_size = asset.get("displaySize")
        if document_size is None:
            add(report, "blockers", "fgui_size_invalid", f"Display List 图片行 {index} 的 Size 非法", path)
        elif document_size != display_size:
            add(report, "blockers", "fgui_display_size_mismatch", f"Display List 图片 {asset_name} 的 Size={document_size} 与 displaySize={display_size} 不一致", path)
        if row.get("size source", "").strip().strip("`").lower() != "asset_manifest.displaysize":
            add(report, "blockers", "fgui_size_source_invalid", f"Display List 图片 {asset_name} 的 Size Source 必须是 asset_manifest.displaySize", path)


def normalize_source_image_entries(value: Any) -> set[str]:
    result: set[str] = set()
    if not isinstance(value, list):
        return result
    for item in value:
        if isinstance(item, str):
            result.add(str(PurePosixPath(item.replace("\\", "/"))))
        elif isinstance(item, dict) and isinstance(item.get("file"), str):
            result.add(str(PurePosixPath(item["file"].replace("\\", "/"))))
    return result


def validate_design_driven_inputs(
    report: dict[str, Any],
    root: Path,
    specs_dir: Path,
    manifest: dict[str, Any],
    approved_design_file: str | None,
) -> None:
    semantic_path = specs_dir / "uxui_semantic_spec.md"
    state_map_path = specs_dir / "component_state_map.json"
    layout_path = specs_dir / "layout_spec.json"
    slice_path = specs_dir / "slice_plan.json"

    require_file(report, semantic_path, "semantic_spec_missing", "uxui_semantic_spec.md")
    loaded: dict[str, dict[str, Any]] = {}
    for path, code, label in (
        (state_map_path, "component_state_map_missing", "component_state_map.json"),
        (layout_path, "layout_spec_missing", "layout_spec.json"),
        (slice_path, "slice_plan_missing", "slice_plan.json"),
    ):
        if not require_file(report, path, code, label):
            continue
        try:
            value = load_json(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            add(report, "blockers", code + "_invalid", f"{label} 无法解析: {exc}", path)
            continue
        loaded[label] = value
        if value.get("blockingForXml") is True:
            add(report, "blockers", code + "_blocks_xml", f"{label} 明确标记 blockingForXml=true", path)

    layout = loaded.get("layout_spec.json", {})
    if layout:
        layout_sources = normalize_source_image_entries(layout.get("sourceImages"))

        if approved_design_file:
            approved_path = Path(approved_design_file).resolve()
            resolved_layout_sources = {
                (root / normalize_relative(source)).resolve()
                for source in layout_sources
            }
            if approved_path not in resolved_layout_sources:
                add(
                    report,
                    "blockers",
                    "approved_design_not_used_for_layout",
                    "layout_spec.sourceImages 必须包含已确认的整屏设计稿",
                    layout_path,
                )
            if semantic_path.is_file():
                semantic_text = read_text(semantic_path)
                approved_name = approved_path.name
                approved_relative = str(approved_path.relative_to(root.resolve())).replace("\\", "/")
                if approved_name not in semantic_text and approved_relative not in semantic_text:
                    add(
                        report,
                        "blockers",
                        "approved_design_not_used_for_semantics",
                        "uxui_semantic_spec.md 必须记录已确认设计稿作为视觉来源",
                        semantic_path,
                    )
        else:
            references = manifest.get("referenceImages", [])
            if isinstance(references, list):
                for index, reference in enumerate(references):
                    if not isinstance(reference, dict):
                        continue
                    role = reference.get("role")
                    allowed_uses = reference.get("allowedUses", [])
                    file_name = reference.get("file")
                    used_for_layout = role in {"layout_only", "style_and_layout", "full_reconstruction"} or (
                        isinstance(allowed_uses, list) and any(use in {"layout", "composition"} for use in allowed_uses)
                    )
                    if used_for_layout and isinstance(file_name, str):
                        normalized = str(PurePosixPath(file_name.replace("\\", "/")))
                        if normalized not in layout_sources:
                            add(report, "blockers", "layout_reference_unlinked", f"layout_spec.sourceImages 未引用布局参考图: referenceImages[{index}].file={file_name}", layout_path)

        assets = manifest.get("assets", [])
        assets_by_name = {
            asset.get("name"): asset
            for asset in assets
            if isinstance(asset, dict) and isinstance(asset.get("name"), str)
        } if isinstance(assets, list) else {}
        objects = layout.get("objects", [])
        if not isinstance(objects, list):
            add(report, "blockers", "layout_objects_invalid", "layout_spec.objects 必须是数组", layout_path)
        else:
            for index, obj in enumerate(objects):
                if not isinstance(obj, dict):
                    continue
                if obj.get("nodeType") != "image":
                    continue
                asset_name = obj.get("assetName")
                if not isinstance(asset_name, str) or asset_name not in assets_by_name:
                    add(report, "blockers", "layout_asset_unresolved", f"objects[{index}].assetName 缺失或未在 manifest 注册", layout_path)
                    continue
                bbox = obj.get("bbox")
                if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(v, int) for v in bbox) and bbox[2] > 0 and bbox[3] > 0):
                    add(report, "blockers", "layout_bbox_invalid", f"objects[{index}].bbox 非法", layout_path)
                    continue
                display_size = assets_by_name[asset_name].get("displaySize")
                layout_size = [bbox[2], bbox[3]]
                if display_size != layout_size:
                    add(report, "blockers", "layout_display_size_mismatch", f"objects[{index}] 尺寸 {layout_size} 与资源 {asset_name}.displaySize={display_size} 不一致", layout_path)
                if obj.get("sizeSource") != "asset_manifest.displaySize":
                    add(report, "blockers", "layout_size_source_missing", f"objects[{index}].sizeSource 必须是 asset_manifest.displaySize", layout_path)

    overlay_candidates = (
        specs_dir.parent / "generated" / "preview" / "layout_overlay_preview.png",
        specs_dir.parent / "reports" / "layout_overlay_review.md",
    )
    if not any(path.exists() for path in overlay_candidates):
        add(
            report,
            "blockers",
            "overlay_review_missing",
            "设计图驱动模式缺少 layout overlay 预览或书面风险接受记录",
            specs_dir.parent,
        )


def validate_asset_files(
    report: dict[str, Any],
    root: Path,
    manifest: dict[str, Any],
    skip_asset_existence: bool,
    profile: str,
) -> None:
    if skip_asset_existence:
        level = "blockers" if profile == "fresh" else "warnings"
        add(report, level, "asset_existence_skipped", "已跳过参考图/资源文件存在性和像素尺寸检查")
        return

    references = manifest.get("referenceImages", [])
    if isinstance(references, list):
        for index, reference in enumerate(references):
            if not isinstance(reference, dict):
                continue
            file_name = reference.get("file")
            declared = reference.get("resolution")
            if not isinstance(file_name, str) or not file_name:
                continue
            reference_path = root / normalize_relative(file_name)
            if not reference_path.is_file():
                add(report, "blockers", "reference_file_missing", f"参考图不存在: referenceImages[{index}].file={file_name}", reference_path)
                continue
            try:
                metadata = read_image_metadata(reference_path)
            except (OSError, ImageMetadataError) as exc:
                add(report, "blockers", "reference_metadata_invalid", f"参考图无法读取尺寸: {exc}", reference_path)
                continue
            actual = [metadata["width"], metadata["height"]]
            if declared != actual:
                add(report, "blockers", "reference_resolution_mismatch", f"参考图声明尺寸 {declared} 与实际像素 {actual} 不一致", reference_path)

    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        return

    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            continue
        file_name = asset.get("file")
        fgui = asset.get("fgui", {})
        extension = PurePosixPath(file_name.replace("\\", "/")).suffix.lower() if isinstance(file_name, str) else ""
        resource_type = fgui.get("resourceType") if isinstance(fgui, dict) else None
        is_bitmap = resource_type in {"image", "atlas", "movieclip"} or extension in {".png", ".jpg", ".jpeg", ".webp"}
        if not is_bitmap or not isinstance(file_name, str) or not file_name:
            continue
        asset_path = root / normalize_relative(file_name)
        if not asset_path.is_file():
            add(
                report,
                "blockers",
                "asset_file_missing",
                f"manifest 资源文件不存在: assets[{index}].file={file_name}",
                asset_path,
            )
            continue
        try:
            metadata = read_image_metadata(asset_path)
        except (OSError, ImageMetadataError) as exc:
            add(report, "blockers", "asset_metadata_invalid", f"资源图片无法读取尺寸: {exc}", asset_path)
            continue
        actual = [metadata["width"], metadata["height"]]
        declared = asset.get("sourcePixelSize")
        if declared != actual:
            add(report, "blockers", "asset_pixel_size_mismatch", f"sourcePixelSize={declared} 与实际像素 {actual} 不一致", asset_path)
        if asset.get("transparent") is True and metadata.get("format") == "png" and metadata.get("hasAlphaCapability") is not True:
            add(report, "blockers", "asset_alpha_missing", "资源声明透明，但 PNG 不支持 Alpha 通道", asset_path)


def file_fingerprint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {
        "path": str(path),
        "size": stat.st_size,
        "modifiedAt": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "sha256": digest.hexdigest(),
    }


def write_input_snapshot(
    path: Path,
    profile: str,
    report: dict[str, Any],
    source_paths: dict[str, Path],
) -> None:
    sources = {
        name: file_fingerprint(source_path)
        for name, source_path in source_paths.items()
        if source_path.is_file()
    }
    snapshot = {
        "version": "0.1.0",
        "profile": profile,
        "packageName": report.get("packageName"),
        "packageId": report.get("packageId"),
        "sources": sources,
        "unresolvedRisks": [item["message"] for item in report.get("warnings", [])],
        "status": "frozen_for_generation",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    lines = ["# XML生成阻塞报告", ""]
    if report["ready"]:
        lines.extend([
            "## 结果",
            "",
            "XML 严格模式前置检查通过，可以进入 XML 草稿生成阶段。",
            "",
        ])
    else:
        lines.extend([
            "## 不能生成 XML 的原因",
            "",
        ])
        for item in report["blockers"]:
            location = f"（{item['path']}）" if item.get("path") else ""
            lines.append(f"- [{item['code']}] {item['message']}{location}")
        lines.append("")

    lines.extend(["## 警告", ""])
    if report["warnings"]:
        for item in report["warnings"]:
            location = f"（{item['path']}）" if item.get("path") else ""
            lines.append(f"- [{item['code']}] {item['message']}{location}")
    else:
        lines.append("- 无")

    lines.extend([
        "",
        "## 当前可以安全输出",
        "",
        "- fgui_spec.md 修正建议",
        "- asset_manifest.json 修正建议",
        "- fgui_id_registry.json 修正或增量 ID 草案",
        "- FairyGUI 编辑器拼装计划",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether FairyGUI XML Strict Mode may start.")
    parser.add_argument("--root", type=Path, required=True, help="UIProduction root directory")
    embedded_full_xml_spec = Path(__file__).resolve().parent.parent / "references" / "fairygui-xml-parsing-specification.md"
    parser.add_argument(
        "--full-xml-spec",
        type=Path,
        default=embedded_full_xml_spec,
        help="Complete FairyGUI XML parsing specification; defaults to the copy embedded in this skill",
    )
    parser.add_argument(
        "--profile",
        choices=("fresh", "editor-compatible"),
        default="fresh",
        help="XML validation profile to freeze into the generation snapshot",
    )
    parser.add_argument("--design-driven", action="store_true", help="Require semantic/layout/slice/overlay inputs")
    parser.add_argument("--require-design-approval", action="store_true", help="Require explicit human approval of the exact full-screen design")
    parser.add_argument("--resource-generation", action="store_true", help="Require a valid primary visual reference for generated/redrawn assets")
    parser.add_argument("--skip-asset-existence", action="store_true", help="Do not verify files listed in manifest")
    parser.add_argument("--out", type=Path, help="JSON readiness report path")
    parser.add_argument("--report-md", type=Path, help="Human-readable blocking report path")
    parser.add_argument("--snapshot-out", type=Path, help="Write frozen generation input snapshot when ready")
    args = parser.parse_args()

    root = args.root.resolve()
    specs_dir = root / "specs"
    manifests_dir = root / "manifests"

    report: dict[str, Any] = {
        "ready": False,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "profile": args.profile,
        "designDriven": args.design_driven,
        "requireDesignApproval": args.require_design_approval,
        "resourceGeneration": args.resource_generation,
        "embeddedDocsIntegrity": None,
        "designApproved": None,
        "packageName": None,
        "packageId": None,
        "blockers": [],
        "warnings": [],
    }

    skill_root = Path(__file__).resolve().parent.parent
    local_contracts = {
        "fullAutomationFlow": skill_root / "references" / "fairygui-ai-generation-workflow.md",
        "embeddedFullXmlSpec": skill_root / "references" / "fairygui-xml-parsing-specification.md",
        "embeddedDocsManifest": skill_root / "references" / "embedded-docs-manifest.json",
        "embeddedDocsVerifier": skill_root / "scripts" / "verify_embedded_docs.py",
        "xmlContract": skill_root / "references" / "fairygui-xml-contract.md",
        "strictProcedure": skill_root / "references" / "xml-strict-generation.md",
        "manifestContract": skill_root / "references" / "manifest-contract.md",
        "visualReferenceContract": skill_root / "references" / "visual-reference-contract.md",
        "designMockupApprovalContract": skill_root / "references" / "design-mockup-approval-contract.md",
        "assetSizeContract": skill_root / "references" / "asset-size-contract.md",
    }
    for contract_name, contract_path in local_contracts.items():
        require_file(report, contract_path, f"{contract_name}_missing", contract_name)

    embedded_report = verify_embedded_docs(skill_root)
    report["embeddedDocsIntegrity"] = embedded_report.get("ok")
    for item in embedded_report.get("errors", []):
        add(
            report,
            "blockers",
            "embedded_docs_" + item.get("code", "invalid"),
            item.get("message", "内置完整文档校验失败"),
            Path(item["path"]) if item.get("path") else skill_root,
        )
    for document in embedded_report.get("documents", []):
        if document.get("ok"):
            continue
        document_path = Path(document["path"]) if document.get("path") else skill_root
        for index, message in enumerate(document.get("errors", [])):
            add(
                report,
                "blockers",
                f"embedded_document_invalid_{document.get('index', 0)}_{index}",
                str(message),
                document_path,
            )

    full_spec_ok = require_file(report, args.full_xml_spec, "full_xml_spec_missing", "完整 FairyGUI XML 解析规范")
    if full_spec_ok and args.full_xml_spec.stat().st_size < 10_000:
        add(
            report,
            "blockers",
            "full_xml_spec_too_small",
            "完整 XML 规范文件体积异常，可能只是摘要或桥接文件",
            args.full_xml_spec,
        )

    manifest_path = manifests_dir / "asset_manifest.json"
    registry_path = manifests_dir / "fgui_id_registry.json"
    fgui_spec_path = specs_dir / "fgui_spec.md"

    manifest: dict[str, Any] = {}
    registry: dict[str, Any] = {}
    design_gate_report: dict[str, Any] = {}
    package_name: str | None = None
    if require_file(report, manifest_path, "manifest_missing", "asset_manifest.json"):
        manifest, package_name = validate_manifest(report, manifest_path, args.resource_generation)
        report["packageName"] = package_name

    if require_file(report, registry_path, "registry_missing", "fgui_id_registry.json"):
        registry, package_id = validate_registry(report, registry_path, package_name)
        report["packageId"] = package_id

    production = manifest.get("production", {}) if isinstance(manifest, dict) else {}
    generates_full_screen = isinstance(production, dict) and production.get("generateFullScreenDesign") is True
    declares_design_approval = isinstance(production, dict) and production.get("requiresDesignApproval") is True
    require_design_approval = args.require_design_approval or generates_full_screen or declares_design_approval
    report["requireDesignApproval"] = require_design_approval

    if args.require_design_approval and not generates_full_screen:
        add(report, "blockers", "full_screen_design_not_declared", "使用 --require-design-approval 时必须设置 production.generateFullScreenDesign=true", manifest_path)
    if require_design_approval and not declares_design_approval:
        add(report, "blockers", "design_approval_not_declared", "完整界面设计流程必须设置 production.requiresDesignApproval=true", manifest_path)

    if require_design_approval:
        design_gate_report = validate_design_approval_gate(root, "xml_generation")
        report["designApproved"] = design_gate_report.get("approved")
        for item in design_gate_report.get("blockers", []):
            add(
                report,
                "blockers",
                "design_approval_" + item.get("code", "blocked"),
                item.get("message", "设计稿确认门禁失败"),
                Path(item["path"]) if item.get("path") else root,
            )
        for item in design_gate_report.get("warnings", []):
            add(
                report,
                "warnings",
                "design_approval_" + item.get("code", "warning"),
                item.get("message", "设计稿确认门禁警告"),
                Path(item["path"]) if item.get("path") else root,
            )

    if manifest and registry:
        validate_manifest_registry_alignment(report, manifest, registry, package_name, registry_path)

    if require_file(report, fgui_spec_path, "fgui_spec_missing", "fgui_spec.md"):
        validate_fgui_spec(report, fgui_spec_path, manifest)

    if args.design_driven:
        validate_design_driven_inputs(
            report,
            root,
            specs_dir,
            manifest,
            design_gate_report.get("approvedFile") if design_gate_report.get("approved") else None,
        )

    if manifest:
        validate_asset_files(report, root, manifest, args.skip_asset_existence, args.profile)

    report["ready"] = not report["blockers"]
    output = json.dumps(report, ensure_ascii=False, indent=2)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    if args.report_md:
        write_markdown_report(args.report_md, report)

    if report["ready"] and args.snapshot_out:
        source_paths: dict[str, Path] = {
            "fullXmlSpec": args.full_xml_spec,
            "manifest": manifest_path,
            "registry": registry_path,
            "fguiSpec": fgui_spec_path,
            **local_contracts,
        }
        if args.design_driven:
            source_paths.update(
                {
                    "uxuiSemanticSpec": specs_dir / "uxui_semantic_spec.md",
                    "componentStateMap": specs_dir / "component_state_map.json",
                    "layoutSpec": specs_dir / "layout_spec.json",
                    "slicePlan": specs_dir / "slice_plan.json",
                }
            )
        if design_gate_report.get("approved"):
            source_paths.update(
                {
                    "visualDesignBrief": specs_dir / "visual_design_brief.md",
                    "designApproval": root / "reports" / "design_approval.json",
                }
            )
            approved_file = design_gate_report.get("approvedFile")
            if isinstance(approved_file, str):
                source_paths["approvedDesign"] = Path(approved_file)
        references = manifest.get("referenceImages", [])
        if isinstance(references, list):
            for index, reference in enumerate(references):
                if isinstance(reference, dict) and isinstance(reference.get("file"), str):
                    source_paths[f"referenceImage{index}"] = root / normalize_relative(reference["file"])
        assets = manifest.get("assets", [])
        if isinstance(assets, list):
            for index, asset in enumerate(assets):
                if isinstance(asset, dict) and isinstance(asset.get("file"), str):
                    source_paths[f"assetImage{index}"] = root / normalize_relative(asset["file"])
        write_input_snapshot(args.snapshot_out, args.profile, report, source_paths)

    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
