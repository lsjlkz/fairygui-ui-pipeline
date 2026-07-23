#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate approved-design visual-part coverage across specs, manifest, and XML."""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

STAGES = {"asset_planning", "fairygui_assembly", "xml_generation"}
IMPLEMENTATION_MODES = {
    "asset_image", "runtime_loader", "graph", "text", "child_component", "group", "none"
}
VISUAL_IMPORTANCE = {"structural", "semantic", "decorative"}
COMPLEXITY = {"simple", "detailed"}
FALLBACK_POLICIES = {"forbidden", "allowed", "approved"}
NODE_MATCH = {"all", "any"}
MODE_TAGS = {
    "asset_image": {"image", "loader"},
    "runtime_loader": {"loader"},
    "graph": {"graph"},
    "text": {"text", "richtext"},
    "child_component": {"component"},
    "group": {"group"},
    "none": set(),
}
RAW_LOCALIZATION_RE = re.compile(r"^@(?:ui_|loc:|i18n:)", re.IGNORECASE)
ICON_ROLE_RE = re.compile(r"(?:^|[_\-])(icon|badge|crest|emblem)(?:$|[_\-])", re.IGNORECASE)
ICON_IMPLEMENTATION_MODES = {"asset_image", "runtime_loader", "child_component"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def normalized(value: Any) -> str:
    return "".join(character.lower() for character in str(value) if character.isalnum())


def normalize_path(value: str) -> str:
    return str(PurePosixPath(value.replace("\\", "/"))).lstrip("./")


def split_values(value: Any) -> list[str]:
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(split_values(item))
        return result
    if value is None:
        return []
    text = str(value).strip().strip("`")
    if not text or text.lower() in {"none", "n/a", "na", "null", "无"}:
        return []
    return [part.strip().strip("`") for part in re.split(r"[,;/|、，；\n]+", text) if part.strip()]


def add(report: dict[str, Any], level: str, code: str, message: str, path: Path | None = None) -> None:
    item: dict[str, str] = {"code": code, "message": message}
    if path is not None:
        item["path"] = str(path)
    report[level].append(item)


def require_file(report: dict[str, Any], path: Path, code: str, label: str) -> bool:
    if not path.is_file():
        add(report, "errors", code, f"缺少 {label}", path)
        return False
    return True


def parse_markdown_table(text: str, heading: str) -> tuple[list[str], list[dict[str, str]]]:
    lines = text.splitlines()
    start: int | None = None
    pattern = re.compile(rf"^##+\s+{re.escape(heading)}\s*$", re.IGNORECASE)
    for index, line in enumerate(lines):
        if pattern.match(line.strip()):
            start = index + 1
            break
    if start is None:
        return [], []

    table_lines: list[str] = []
    started = False
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("##") and started:
            break
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines.append(stripped)
            started = True
        elif started and stripped:
            break
    if len(table_lines) < 2:
        return [], []

    def cells(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip("|").split("|")]

    headers = [cell.lower() for cell in cells(table_lines[0])]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        values = cells(line)
        if len(values) == len(headers):
            rows.append(dict(zip(headers, values)))
    return headers, rows


def source_labels(value: Any) -> list[str]:
    result: list[str] = []
    if not isinstance(value, list):
        return result
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
        elif isinstance(item, dict):
            for field in ("file", "path", "name", "id"):
                candidate = item.get(field)
                if isinstance(candidate, str) and candidate.strip():
                    result.append(candidate.strip())
                    break
    return result


def find_project_file(root: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else root / Path(*PurePosixPath(value.replace("\\", "/")).parts)


def build_manifest_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        return result
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = asset.get("name")
        if isinstance(name, str) and name:
            result[normalized(name)] = asset
    return result


def registry_package(registry: dict[str, Any], package_name: str | None) -> tuple[str | None, dict[str, Any]]:
    packages = registry.get("packages", {})
    if not isinstance(packages, dict) or not package_name:
        return None, {}
    package = packages.get(package_name)
    if not isinstance(package, dict):
        return None, {}
    package_id = package.get("id") or package.get("packageId")
    return package_id if isinstance(package_id, str) else None, package


def resolve_asset_resource_id(asset: dict[str, Any], package: dict[str, Any]) -> str | None:
    resources = package.get("resources", {})
    if not isinstance(resources, dict):
        return None
    candidates: set[str] = set()
    name = asset.get("name")
    file_name = asset.get("packageRelativeFile") or asset.get("file")
    if isinstance(name, str):
        candidates.add(normalized(name))
    if isinstance(file_name, str):
        path = PurePosixPath(normalize_path(file_name))
        candidates.update({normalized(str(path)), normalized(path.name), normalized(path.stem)})
    for resource_name, resource_id in resources.items():
        resource_path = PurePosixPath(str(resource_name).replace("\\", "/"))
        resource_candidates = {
            normalized(resource_name), normalized(resource_path.name), normalized(resource_path.stem)
        }
        if candidates.intersection(resource_candidates) and isinstance(resource_id, str):
            return resource_id
    return None


def validate_structure(
    report: dict[str, Any],
    root: Path,
    coverage_path: Path,
    coverage: dict[str, Any],
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    sources = source_labels(coverage.get("designSources"))
    if not sources:
        add(report, "errors", "visual_part_design_sources_missing", "component_visual_parts.json 必须记录已确认设计稿来源", coverage_path)
    for source in sources:
        if "://" not in source:
            source_path = find_project_file(root, source)
            if not source_path.is_file():
                add(report, "errors", "visual_part_design_source_missing", f"设计稿来源不存在: {source}", source_path)

    if coverage.get("blockingForXml") is True:
        add(report, "errors", "visual_part_coverage_blocks_xml", "component_visual_parts.json 标记 blockingForXml=true", coverage_path)

    components = coverage.get("components")
    if not isinstance(components, list) or not components:
        add(report, "errors", "visual_part_components_missing", "component_visual_parts.components 必须是非空数组", coverage_path)
        return [], build_manifest_index(manifest)

    manifest_index = build_manifest_index(manifest)
    seen_components: set[str] = set()
    normalized_components: list[dict[str, Any]] = []

    for component_index, component in enumerate(components):
        if not isinstance(component, dict):
            add(report, "errors", "visual_part_component_invalid", f"components[{component_index}] 必须是对象", coverage_path)
            continue
        component_type = component.get("componentType")
        component_files = split_values(component.get("componentFiles"))
        requirement_ids = split_values(component.get("requirementIds"))
        parts = component.get("parts")
        if not isinstance(component_type, str) or not component_type:
            add(report, "errors", "visual_part_component_type_missing", f"components[{component_index}].componentType 缺失", coverage_path)
            continue
        component_key = normalized(component_type)
        if component_key in seen_components:
            add(report, "errors", "visual_part_component_duplicate", f"componentType 重复: {component_type}", coverage_path)
        seen_components.add(component_key)
        if not component_files:
            add(report, "errors", "visual_part_component_files_missing", f"组件 {component_type} 缺少 componentFiles", coverage_path)
        if not requirement_ids:
            add(report, "errors", "visual_part_component_requirement_ids_missing", f"组件 {component_type} 缺少 requirementIds", coverage_path)
        if not isinstance(parts, list) or not parts:
            add(report, "errors", "visual_part_parts_missing", f"组件 {component_type} 缺少 parts", coverage_path)
            continue

        seen_parts: set[str] = set()
        valid_parts: list[dict[str, Any]] = []
        for part_index, part in enumerate(parts):
            base = f"{component_type}.parts[{part_index}]"
            if not isinstance(part, dict):
                add(report, "errors", "visual_part_invalid", f"{base} 必须是对象", coverage_path)
                continue
            part_id = part.get("partId")
            role = part.get("role")
            required = part.get("required")
            visible = part.get("visibleInApprovedDesign")
            importance = part.get("visualImportance")
            complexity = part.get("complexity")
            part_requirement_ids = split_values(part.get("requirementIds"))
            implementation = part.get("implementation")
            if not isinstance(part_id, str) or not part_id:
                add(report, "errors", "visual_part_id_missing", f"{base}.partId 缺失", coverage_path)
                continue
            part_key = normalized(part_id)
            if part_key in seen_parts:
                add(report, "errors", "visual_part_id_duplicate", f"组件 {component_type} 的 partId 重复: {part_id}", coverage_path)
            seen_parts.add(part_key)
            if not isinstance(role, str) or not role:
                add(report, "errors", "visual_part_role_missing", f"{component_type}.{part_id} 缺少 role", coverage_path)
            if not isinstance(required, bool):
                add(report, "errors", "visual_part_required_invalid", f"{component_type}.{part_id}.required 必须是布尔值", coverage_path)
            if not isinstance(visible, bool):
                add(report, "errors", "visual_part_visibility_invalid", f"{component_type}.{part_id}.visibleInApprovedDesign 必须是布尔值", coverage_path)
            if importance not in VISUAL_IMPORTANCE:
                add(report, "errors", "visual_part_importance_invalid", f"{component_type}.{part_id}.visualImportance 非法: {importance}", coverage_path)
            if complexity not in COMPLEXITY:
                add(report, "errors", "visual_part_complexity_invalid", f"{component_type}.{part_id}.complexity 非法: {complexity}", coverage_path)
            if not part_requirement_ids:
                add(report, "errors", "visual_part_requirement_ids_missing", f"{component_type}.{part_id} 缺少 requirementIds", coverage_path)
            if not isinstance(implementation, dict):
                add(report, "errors", "visual_part_implementation_missing", f"{component_type}.{part_id} 缺少 implementation", coverage_path)
                continue

            mode = implementation.get("mode")
            node_names = split_values(implementation.get("xmlNodeNames"))
            fallback_policy = implementation.get("fallbackPolicy")
            node_match = implementation.get("nodeMatch", "all")
            applies_to_files = split_values(implementation.get("appliesToFiles")) or component_files
            asset_name = implementation.get("assetName")

            if mode not in IMPLEMENTATION_MODES:
                add(report, "errors", "visual_part_mode_invalid", f"{component_type}.{part_id}.implementation.mode 非法: {mode}", coverage_path)
            asset = manifest_index.get(normalized(asset_name)) if isinstance(asset_name, str) else None
            asset_type = str(asset.get("type", "")).lower() if isinstance(asset, dict) else ""
            asset_layer = str((asset.get("fgui") or {}).get("layer", "")).lower() if isinstance(asset, dict) and isinstance(asset.get("fgui"), dict) else ""
            icon_like = (
                bool(ICON_ROLE_RE.search(str(part_id)))
                or bool(ICON_ROLE_RE.search(str(role)))
                or asset_type == "icon"
                or asset_layer == "icon"
            )
            if icon_like and mode not in ICON_IMPLEMENTATION_MODES:
                add(report, "errors", "icon_visual_part_graph_forbidden", f"{component_type}.{part_id} 是图标类视觉部件，禁止使用 {mode}；必须使用审核后的位图或位图子组件", coverage_path)
            if fallback_policy not in FALLBACK_POLICIES:
                add(report, "errors", "visual_part_fallback_policy_invalid", f"{component_type}.{part_id}.fallbackPolicy 非法: {fallback_policy}", coverage_path)
            if node_match not in NODE_MATCH:
                add(report, "errors", "visual_part_node_match_invalid", f"{component_type}.{part_id}.nodeMatch 非法: {node_match}", coverage_path)
            if required is True and visible is True and mode == "none":
                add(report, "errors", "required_visual_part_unimplemented", f"{component_type}.{part_id} 为必需可见部件，但 implementation.mode=none", coverage_path)
            if required is True and visible is True and not node_names:
                add(report, "errors", "visual_part_xml_nodes_missing", f"{component_type}.{part_id} 缺少 xmlNodeNames", coverage_path)
            if mode in {"asset_image", "runtime_loader"}:
                if not isinstance(asset_name, str) or not asset_name:
                    add(report, "errors", "visual_part_asset_name_missing", f"{component_type}.{part_id} 为资源部件但缺少 assetName", coverage_path)
                elif normalized(asset_name) not in manifest_index:
                    add(report, "errors", "missing_visual_part_asset", f"{component_type}.{part_id} 需要的资源未进入 asset_manifest: {asset_name}", coverage_path)
            if complexity == "detailed" and mode == "graph":
                approval = implementation.get("fallbackApproval")
                approval_valid = (
                    fallback_policy == "approved"
                    and isinstance(approval, dict)
                    and approval.get("status") == "approved"
                    and approval.get("recordedBy") in {"user", "human_reviewer"}
                )
                if not approval_valid:
                    add(report, "errors", "visual_part_degraded_to_graph_without_approval", f"详细视觉部件 {component_type}.{part_id} 被降级为 Graph，但没有人工批准", coverage_path)
            for file_name in applies_to_files:
                if normalized(file_name) not in {normalized(item) for item in component_files}:
                    add(report, "errors", "visual_part_file_scope_invalid", f"{component_type}.{part_id}.appliesToFiles 包含未声明组件文件: {file_name}", coverage_path)
            valid_parts.append(part)

        normalized_component = dict(component)
        normalized_component["parts"] = valid_parts
        normalized_components.append(normalized_component)

    return normalized_components, manifest_index


def validate_fgui_spec(
    report: dict[str, Any],
    fgui_spec_path: Path,
    components: list[dict[str, Any]],
) -> None:
    if not require_file(report, fgui_spec_path, "visual_part_fgui_spec_missing", "fgui_spec.md"):
        return
    text = read_text(fgui_spec_path)
    headers, rows = parse_markdown_table(text, "Visual Part Coverage")
    required_headers = {
        "component type", "part id", "role", "required", "importance", "complexity",
        "implementation mode", "asset name", "xml nodes", "applies to files", "fallback policy", "requirement ids",
    }
    missing_headers = sorted(required_headers.difference(headers))
    if missing_headers:
        add(report, "errors", "visual_part_fgui_table_columns_missing", f"fgui_spec Visual Part Coverage 缺少列: {missing_headers}", fgui_spec_path)
        return

    row_index = {
        (normalized(row.get("component type")), normalized(row.get("part id"))): row
        for row in rows
        if row.get("component type") and row.get("part id")
    }
    for component in components:
        component_type = str(component.get("componentType", ""))
        for part in component.get("parts", []):
            part_id = str(part.get("partId", ""))
            row = row_index.get((normalized(component_type), normalized(part_id)))
            if row is None:
                add(report, "errors", "visual_part_fgui_row_missing", f"{component_type}.{part_id} 未写入 fgui_spec Visual Part Coverage", fgui_spec_path)
                continue
            implementation = part.get("implementation") if isinstance(part.get("implementation"), dict) else {}
            expected = {
                "role": part.get("role"),
                "importance": part.get("visualImportance"),
                "complexity": part.get("complexity"),
                "implementation mode": implementation.get("mode"),
                "fallback policy": implementation.get("fallbackPolicy"),
            }
            for column, value in expected.items():
                if value and normalized(row.get(column)) != normalized(value):
                    add(report, "errors", "visual_part_fgui_row_mismatch", f"{component_type}.{part_id} 的 {column} 与 component_visual_parts.json 不一致", fgui_spec_path)
            asset_name = implementation.get("assetName")
            if asset_name and normalized(row.get("asset name")) != normalized(asset_name):
                add(report, "errors", "visual_part_fgui_asset_mismatch", f"{component_type}.{part_id} 的 Asset Name 不一致", fgui_spec_path)


def xml_node_index(root: ET.Element) -> dict[str, list[ET.Element]]:
    result: dict[str, list[ET.Element]] = {}
    for element in root.iter():
        name = element.attrib.get("name")
        if isinstance(name, str) and name:
            result.setdefault(normalized(name), []).append(element)
    return result


def validate_xml(
    report: dict[str, Any],
    xml_dir: Path,
    components: list[dict[str, Any]],
    manifest_index: dict[str, dict[str, Any]],
    registry: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    if not xml_dir.is_dir():
        add(report, "errors", "visual_part_xml_dir_missing", "XML 目录不存在", xml_dir)
        return
    package_info = manifest.get("package", {}) if isinstance(manifest.get("package"), dict) else {}
    package_name = package_info.get("name") if isinstance(package_info.get("name"), str) else xml_dir.name
    package_id, package_registry = registry_package(registry, package_name)

    parsed_files: dict[str, tuple[Path, ET.Element, dict[str, list[ET.Element]]]] = {}
    for xml_path in xml_dir.rglob("*.xml"):
        if xml_path.name == "package.xml":
            continue
        try:
            root = ET.fromstring(read_text(xml_path))
        except (OSError, ET.ParseError) as exc:
            add(report, "errors", "visual_part_component_xml_invalid", f"组件 XML 无法解析: {exc}", xml_path)
            continue
        relative = normalize_path(str(xml_path.relative_to(xml_dir)))
        parsed_files[normalized(relative)] = (xml_path, root, xml_node_index(root))
        parsed_files.setdefault(normalized(xml_path.name), (xml_path, root, xml_node_index(root)))

    for component in components:
        component_type = str(component.get("componentType", ""))
        component_files = split_values(component.get("componentFiles"))
        for part in component.get("parts", []):
            part_id = str(part.get("partId", ""))
            required = part.get("required") is True
            visible = part.get("visibleInApprovedDesign") is True
            implementation = part.get("implementation") if isinstance(part.get("implementation"), dict) else {}
            mode = implementation.get("mode")
            node_names = split_values(implementation.get("xmlNodeNames"))
            node_match = implementation.get("nodeMatch", "all")
            target_files = split_values(implementation.get("appliesToFiles")) or component_files
            asset_name = implementation.get("assetName")
            expected_tags = MODE_TAGS.get(str(mode), set())

            if not required or not visible or mode == "none":
                continue
            for file_name in target_files:
                parsed = parsed_files.get(normalized(file_name))
                if parsed is None:
                    add(report, "errors", "visual_part_component_file_missing", f"{component_type}.{part_id} 的目标组件文件不存在: {file_name}", xml_dir / file_name)
                    continue
                xml_path, _, nodes = parsed
                found: list[ET.Element] = []
                missing_names: list[str] = []
                for node_name in node_names:
                    matches = nodes.get(normalized(node_name), [])
                    if matches:
                        found.extend(matches)
                    else:
                        missing_names.append(node_name)
                condition_failed = bool(missing_names) if node_match == "all" else not found
                if condition_failed:
                    add(report, "errors", "xml_visual_part_missing", f"{component_type}.{part_id} 在 {file_name} 缺少 XML 节点: {missing_names or node_names}", xml_path)
                    continue

                for element in found:
                    tag = element.tag.rsplit("}", 1)[-1]
                    if expected_tags and tag not in expected_tags:
                        add(report, "errors", "visual_part_xml_tag_mismatch", f"{component_type}.{part_id} 节点 {element.attrib.get('name')} 使用 <{tag}>，期望 {sorted(expected_tags)}", xml_path)

                if mode in {"asset_image", "runtime_loader"} and isinstance(asset_name, str):
                    asset = manifest_index.get(normalized(asset_name))
                    resource_id = resolve_asset_resource_id(asset, package_registry) if asset else None
                    if not resource_id:
                        add(report, "errors", "visual_part_resource_unregistered", f"{component_type}.{part_id} 的资源无法映射到 registry: {asset_name}", xml_path)
                    else:
                        expected_url = f"ui://{package_id}{resource_id}" if package_id else None
                        if not any(
                            element.attrib.get("src") == resource_id
                            or (expected_url is not None and element.attrib.get("url") == expected_url)
                            for element in found
                        ):
                            add(report, "errors", "visual_part_asset_reference_mismatch", f"{component_type}.{part_id} 的 XML 节点没有引用声明资源 {asset_name}", xml_path)

                if mode == "text":
                    preview_text = implementation.get("previewText")
                    localization_key = implementation.get("localizationKey")
                    for element in found:
                        text_value = element.attrib.get("text", "")
                        if not text_value:
                            add(report, "errors", "visual_part_text_empty", f"{component_type}.{part_id} 的必需预览文本为空", xml_path)
                        elif RAW_LOCALIZATION_RE.match(text_value):
                            add(report, "errors", "visual_part_text_raw_localization_key", f"{component_type}.{part_id} 显示未解析本地化 Key: {text_value}", xml_path)
                        if isinstance(preview_text, str) and preview_text and text_value != preview_text:
                            add(report, "errors", "visual_part_preview_text_mismatch", f"{component_type}.{part_id} 预览文本不匹配: XML={text_value}, expected={preview_text}", xml_path)
                        if isinstance(localization_key, str) and localization_key:
                            custom_data = element.attrib.get("customData", "")
                            if localization_key not in custom_data:
                                add(report, "errors", "visual_part_localization_identity_missing", f"{component_type}.{part_id} 未保留 localizationKey={localization_key}", xml_path)


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Visual Part Coverage Report",
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


def validate(root: Path, stage: str, xml_dir: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    coverage_path = root / "specs" / "component_visual_parts.json"
    manifest_path = root / "manifests" / "asset_manifest.json"
    registry_path = root / "manifests" / "fgui_id_registry.json"
    fgui_spec_path = root / "specs" / "fgui_spec.md"

    report: dict[str, Any] = {
        "ok": False,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "stage": stage,
        "xmlDir": str(xml_dir.resolve()) if xml_dir else None,
        "errors": [],
        "warnings": [],
        "summary": {"components": 0, "parts": 0, "requiredParts": 0},
    }

    if not require_file(report, coverage_path, "component_visual_parts_missing", "component_visual_parts.json"):
        return report
    if not require_file(report, manifest_path, "visual_part_manifest_missing", "asset_manifest.json"):
        return report

    try:
        coverage = load_json(coverage_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        add(report, "errors", "component_visual_parts_invalid", f"component_visual_parts.json 无法解析: {exc}", coverage_path)
        return report
    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        add(report, "errors", "visual_part_manifest_invalid", f"asset_manifest.json 无法解析: {exc}", manifest_path)
        return report

    registry: dict[str, Any] = {}
    if registry_path.is_file():
        try:
            registry = load_json(registry_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            add(report, "errors", "visual_part_registry_invalid", f"fgui_id_registry.json 无法解析: {exc}", registry_path)

    components, manifest_index = validate_structure(report, root, coverage_path, coverage, manifest)
    report["summary"]["components"] = len(components)
    report["summary"]["parts"] = sum(len(component.get("parts", [])) for component in components)
    report["summary"]["requiredParts"] = sum(
        1
        for component in components
        for part in component.get("parts", [])
        if part.get("required") is True and part.get("visibleInApprovedDesign") is True
    )

    if stage in {"fairygui_assembly", "xml_generation"}:
        validate_fgui_spec(report, fgui_spec_path, components)

    if xml_dir is not None:
        validate_xml(report, xml_dir.resolve(), components, manifest_index, registry, manifest)

    report["ok"] = not report["errors"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate visual-part coverage for an approved FairyGUI screen design.")
    parser.add_argument("--root", type=Path, required=True, help="UIProduction root directory")
    parser.add_argument("--stage", choices=sorted(STAGES), default="xml_generation")
    parser.add_argument("--xml-dir", type=Path, help="Optional package XML directory for node/resource validation")
    parser.add_argument("--out", type=Path, help="JSON report output path")
    parser.add_argument("--report-md", type=Path, help="Markdown report output path")
    args = parser.parse_args()

    report = validate(args.root, args.stage, args.xml_dir)
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
