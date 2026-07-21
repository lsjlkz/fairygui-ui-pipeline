#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strict validator for AI-generated or FairyGUI-editor-compatible XML.

The validator focuses on failures that are common in generated XML:
- unresolved placeholders
- invalid or unstable package/resource/instance IDs
- src values that use asset names or filenames instead of resource IDs
- invalid or unregistered ui:// URLs
- manifest, registry, package.xml, and component XML mismatches
- Button/Label component-instance extension override mismatches and unresolved override URLs
- missing required object attributes
- pseudo tags that FairyGUI cannot parse

Two modes are supported:
- fresh: strict rules for newly generated XML
- editor-compatible: preserve valid FairyGUI editor exports and downgrade
  generator-only conventions, such as instance-ID shape, to warnings
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any

from image_metadata import ImageMetadataError, read_image_metadata
from validate_semantic_controller_mapping import validate as validate_semantic_controller_mapping
from validate_visual_part_coverage import validate as validate_visual_part_coverage

PACKAGE_ID_RE = re.compile(r"^[a-z0-9]{8}$")
RESOURCE_ID_RE = re.compile(r"^[a-z0-9]{2,16}$")
INSTANCE_ID_RE = re.compile(r"^n\d+_[a-z0-9]{4}$")
URL_RE = re.compile(r"^ui://([a-z0-9]{8})([a-z0-9]{2,16})$")
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

EXTENSION_OVERRIDE_ALLOWED_ATTRIBUTES = {
    "Button": {
        "title", "titleColor", "titleFontSize", "icon", "selectedTitle", "selectedIcon",
        "sound", "soundVolumeScale", "mode", "downEffect", "downEffectValue",
        "relatedController", "relatedPageId", "selected",
    },
    "Label": {"title", "titleColor", "titleFontSize", "icon"},
}
EXTENSION_OVERRIDE_URL_ATTRIBUTES = {"icon", "selectedIcon", "sound"}
EXTENSION_OVERRIDE_LOCALIZED_TEXT_ATTRIBUTES = {"title", "selectedTitle"}
EXTENSION_OVERRIDE_REQUIRED_CHILD_NAMES = {
    "title": "title",
    "selectedTitle": "title",
    "icon": "icon",
    "selectedIcon": "icon",
}

PLACEHOLDERS = [
    "包ID",
    "资源ID",
    "背景资源ID",
    "按钮资源ID",
    "图标资源ID",
    "列表项资源ID",
    "PACKAGE_ID",
    "RESOURCE_ID",
    "xxxx",
    "{",
    "}",
]

FORBIDDEN_TAGS = {"panel", "button", "sprite", "container", "layer"}

ALLOWED_TAGS = {
    "packageDescription", "resources", "publish",
    "component", "image", "sound", "movieclip", "font", "atlas", "misc",
    "displayList", "controller", "action",
    "text", "richtext", "loader", "graph", "list", "group", "item",
    "Button", "Label", "ComboBox", "ProgressBar", "Slider", "ScrollBar", "Tree",
    "relation",
    "gearDisplay", "gearXY", "gearSize", "gearLook", "gearColor",
    "gearAnimation", "gearText", "gearIcon", "gearDisplay2", "gearFontSize",
    "transition", "tween",
}

DISPLAY_OBJECT_TAGS = {
    "image", "text", "richtext", "loader", "graph", "list", "group", "component"
}


def read_json(path: str | None) -> tuple[dict[str, Any], str | None]:
    if not path:
        return {}, None
    p = Path(path)
    if not p.exists():
        return {}, "file does not exist"
    try:
        value = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, str(exc)
    if not isinstance(value, dict):
        return {}, "top-level JSON value must be an object"
    return value, None


def normalize_path(value: str) -> str:
    return str(PurePosixPath(value.replace("\\", "/"))).lstrip("./")



def collect_registry(registry: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "package_ids": set(),
        "package_id_by_name": {},
        "resource_ids": set(),
        "resource_ids_by_package_id": {},
        "resource_name_by_package_and_id": {},
        "instance_ids": set(),
    }

    packages = registry.get("packages", {})
    if not isinstance(packages, dict):
        return result

    for package_name, package in packages.items():
        if not isinstance(package, dict):
            continue

        package_id = package.get("packageId") or package.get("id")
        if not isinstance(package_id, str):
            continue

        result["package_ids"].add(package_id)
        result["package_id_by_name"][package_name] = package_id
        result["resource_ids_by_package_id"].setdefault(package_id, set())

        resources = package.get("resources", {})
        if isinstance(resources, dict):
            for resource_name, resource_id in resources.items():
                if not isinstance(resource_id, str):
                    continue
                result["resource_ids"].add(resource_id)
                result["resource_ids_by_package_id"][package_id].add(resource_id)
                result["resource_name_by_package_and_id"][(package_id, resource_id)] = str(resource_name)

        instances = package.get("instances", {})
        if isinstance(instances, dict):
            for instance_id in instances.values():
                if isinstance(instance_id, str):
                    result["instance_ids"].add(instance_id)

    return result


def collect_manifest(manifest: dict[str, Any], manifest_path: str | None = None) -> dict[str, Any]:
    assets_by_name: dict[str, dict[str, Any]] = {}
    assets_by_file_name: dict[str, dict[str, Any]] = {}

    assets = manifest.get("assets", [])
    if isinstance(assets, list):
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = asset.get("name")
            file_name = asset.get("file")
            if isinstance(name, str):
                assets_by_name[name] = asset
            if isinstance(file_name, str):
                assets_by_file_name[PurePosixPath(normalize_path(file_name)).name] = asset

    package = manifest.get("package", {})
    package_name = package.get("name") if isinstance(package, dict) else None
    package_output_path = package.get("outputPath") if isinstance(package, dict) else None

    project_root = None
    if manifest_path:
        project_root = Path(manifest_path).resolve().parent.parent

    return {
        "assets_by_name": assets_by_name,
        "assets_by_file_name": assets_by_file_name,
        "package_name": package_name,
        "package_output_path": package_output_path,
        "project_root": project_root,
    }


def parse_size(value: str | None) -> list[int] | None:
    if not value:
        return None
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        return None
    try:
        result = [int(parts[0]), int(parts[1])]
    except ValueError:
        return None
    return result if all(item > 0 for item in result) else None


def normalize_relative_path(value: str) -> Path:
    normalized = str(PurePosixPath(value.replace("\\", "/"))).lstrip("./")
    return Path(*PurePosixPath(normalized).parts)


def issue(level: str, file: Path, message: str) -> dict[str, str]:
    return {"level": level, "file": str(file), "message": message}


def add_mode_issue(
    issues: list[dict[str, str]],
    mode: str,
    file: Path,
    message: str,
    *,
    strict_level: str = "error",
) -> None:
    level = strict_level if mode == "fresh" else "warning"
    issues.append(issue(level, file, message))


def contains_placeholder(value: str) -> bool:
    return any(token in value for token in PLACEHOLDERS)


def resolve_manifest_asset(
    package_id: str | None,
    resource_id: str,
    registry_info: dict[str, Any],
    manifest_info: dict[str, Any],
) -> dict[str, Any] | None:
    resource_name: str | None = None
    if package_id:
        resource_name = registry_info["resource_name_by_package_and_id"].get((package_id, resource_id))

    if resource_name:
        by_name = manifest_info["assets_by_name"].get(resource_name)
        if by_name:
            return by_name
        by_file = manifest_info["assets_by_file_name"].get(PurePosixPath(resource_name).name)
        if by_file:
            return by_file

    return None


def validate_registered_url(
    source_file: Path,
    attribute_name: str,
    value: str,
    registry_info: dict[str, Any],
    issues: list[dict[str, str]],
) -> None:
    if not value:
        return
    match = URL_RE.fullmatch(value)
    if match is None:
        issues.append(issue("error", source_file, f"{attribute_name} 必须是合法 ui://包ID资源ID: {value}"))
        return
    package_id, resource_id = match.groups()
    if registry_info["package_ids"] and package_id not in registry_info["package_ids"]:
        issues.append(issue("error", source_file, f"{attribute_name} 引用未注册包: {value}"))
        return
    package_resources = registry_info["resource_ids_by_package_id"].get(package_id, set())
    if resource_id not in package_resources:
        issues.append(issue("error", source_file, f"{attribute_name} 引用未注册资源: {value}"))


def resolve_package_component_file(package_root: Path, resource_id: str) -> str | None:
    package_xml = package_root / "package.xml"
    if not package_xml.is_file():
        return None
    try:
        root = ET.parse(package_xml).getroot()
    except (OSError, ET.ParseError):
        return None
    for element in root.findall(".//component"):
        if element.attrib.get("id") != resource_id:
            continue
        name = element.attrib.get("name", "")
        path_attr = element.attrib.get("path", "")
        relative = f"{path_attr.strip('/')}/{name}".strip("/")
        return normalize_path(relative) if relative else None
    return None


def validate_component_extension_overrides(
    source_file: Path,
    component_instance: ET.Element,
    mode: str,
    current_package_id: str | None,
    registry_info: dict[str, Any],
    package_root: Path,
    issues: list[dict[str, str]],
) -> None:
    override_nodes = [
        child for child in list(component_instance)
        if child.tag in EXTENSION_OVERRIDE_ALLOWED_ATTRIBUTES
    ]
    if not override_nodes:
        return

    if len(override_nodes) > 1:
        issues.append(
            issue(
                "error",
                source_file,
                f"component 实例 {component_instance.attrib.get('name', '')} 包含多个扩展参数节点: "
                + ",".join(child.tag for child in override_nodes),
            )
        )

    file_name = component_instance.attrib.get("fileName", "")
    src = component_instance.attrib.get("src", "")
    target_pkg = component_instance.attrib.get("pkg")
    if target_pkg and target_pkg != current_package_id:
        add_mode_issue(
            issues,
            mode,
            source_file,
            f"跨包组件实例的扩展参数无法从当前包验证目标 extention: pkg={target_pkg}, fileName={file_name}",
        )
        target_root = None
    elif not src:
        issues.append(issue("error", source_file, "带扩展参数的 component 实例缺少 src"))
        target_root = None
    elif not file_name:
        issues.append(issue("error", source_file, "带扩展参数的 component 实例缺少 fileName"))
        target_root = None
    else:
        target_raw = file_name.replace("\\", "/")
        target_posix = PurePosixPath(target_raw)
        registered_file = resolve_package_component_file(package_root, src)
        if registered_file is None:
            issues.append(issue("error", source_file, f"component@src 未在 package.xml 注册为组件资源: {src}"))
            target_root = None
        elif normalize_path(target_raw) != registered_file:
            issues.append(
                issue(
                    "error",
                    source_file,
                    f"component@fileName 与 package.xml 中 src={src} 的组件文件不一致: "
                    f"XML={normalize_path(target_raw)}, package={registered_file}",
                )
            )
            target_root = None
        elif target_raw.startswith("/") or target_posix.is_absolute() or ".." in target_posix.parts:
            issues.append(issue("error", source_file, f"component@fileName 必须是安全的包内相对路径: {file_name}"))
            target_root = None
        else:
            target_file = package_root / normalize_relative_path(registered_file)
            if not target_file.is_file():
                issues.append(issue("error", source_file, f"扩展参数目标组件 XML 不存在: {registered_file} -> {target_file}"))
                target_root = None
            else:
                try:
                    target_root = ET.parse(target_file).getroot()
                except (OSError, ET.ParseError) as exc:
                    issues.append(issue("error", source_file, f"无法读取扩展参数目标组件 XML: {target_file}: {exc}"))
                    target_root = None

    for override in override_nodes:
        allowed = EXTENSION_OVERRIDE_ALLOWED_ATTRIBUTES[override.tag]
        unsupported = sorted(set(override.attrib) - allowed)
        if unsupported:
            add_mode_issue(
                issues,
                mode,
                source_file,
                f"外部 {override.tag} 参数包含不支持的属性: {','.join(unsupported)}",
            )

        if target_root is not None:
            if target_root.tag != "component":
                issues.append(issue("error", source_file, f"扩展参数目标文件根节点不是 component: {file_name}"))
            target_extension = target_root.attrib.get("extention", "")
            if target_extension != override.tag:
                issues.append(
                    issue(
                        "error",
                        source_file,
                        f"外部参数节点 <{override.tag}> 与目标组件 extention 不匹配: "
                        f"target={target_extension or '<none>'}, fileName={file_name}",
                    )
                )

            target_child_names = {
                elem.attrib.get("name")
                for elem in target_root.iter()
                if isinstance(elem.attrib.get("name"), str)
            }
            for attribute_name, required_child_name in EXTENSION_OVERRIDE_REQUIRED_CHILD_NAMES.items():
                value = override.attrib.get(attribute_name)
                if value and required_child_name not in target_child_names:
                    add_mode_issue(
                        issues,
                        mode,
                        source_file,
                        f"外部 {override.tag}@{attribute_name} 无法映射到目标组件内部对象 "
                        f"name={required_child_name}: {file_name}",
                    )

        for attribute_name, value in override.attrib.items():
            if attribute_name in EXTENSION_OVERRIDE_URL_ATTRIBUTES:
                validate_registered_url(source_file, f"{override.tag}@{attribute_name}", value, registry_info, issues)
            elif attribute_name in EXTENSION_OVERRIDE_LOCALIZED_TEXT_ATTRIBUTES:
                if value and not value.startswith("@"):
                    issues.append(
                        issue(
                            "warning",
                            source_file,
                            f"外部 {override.tag}@{attribute_name} 使用硬编码正式文案，建议改为多语言 key: {value}",
                        )
                    )


def validate_file(
    path: Path,
    mode: str,
    current_package_id: str | None,
    registry_info: dict[str, Any],
    manifest_info: dict[str, Any],
    package_root: Path,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    text = path.read_text(encoding="utf-8-sig")

    if not text.lstrip().startswith('<?xml version="1.0" encoding="utf-8"?>'):
        issues.append(issue("error", path, "缺少标准 XML 声明"))

    for token in PLACEHOLDERS:
        if token in text:
            issues.append(issue("error", path, f"存在占位符或未替换内容: {token}"))

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        issues.append(issue("error", path, f"XML 解析失败: {exc}"))
        return issues

    if root.tag not in {"packageDescription", "component"}:
        issues.append(issue("error", path, f"非法根节点: <{root.tag}>"))

    seen_ids: set[str] = set()

    for elem in root.iter():
        if elem.tag in FORBIDDEN_TAGS:
            issues.append(issue("error", path, f"禁止的伪标签: <{elem.tag}>"))
        elif elem.tag not in ALLOWED_TAGS:
            issues.append(issue("warning", path, f"未知标签，需要人工确认: <{elem.tag}>"))

        for key, value in elem.attrib.items():
            if contains_placeholder(value):
                issues.append(issue("error", path, f"<{elem.tag}> 属性 {key} 含占位符: {value}"))

        elem_id = elem.attrib.get("id")
        if elem_id:
            if elem_id in seen_ids:
                issues.append(issue("error", path, f"重复 id: {elem_id}"))
            seen_ids.add(elem_id)

        if root.tag == "packageDescription":
            validate_package_element(
                path,
                elem,
                mode,
                current_package_id,
                registry_info,
                manifest_info,
                package_root,
                issues,
            )
        elif root.tag == "component":
            validate_component_element(
                path,
                root,
                elem,
                mode,
                current_package_id,
                registry_info,
                manifest_info,
                package_root,
                issues,
            )

    return issues


def validate_package_element(
    path: Path,
    elem: ET.Element,
    mode: str,
    current_package_id: str | None,
    registry_info: dict[str, Any],
    manifest_info: dict[str, Any],
    package_root: Path,
    issues: list[dict[str, str]],
) -> None:
    if elem.tag == "packageDescription":
        package_id = elem.attrib.get("id", "")
        if not PACKAGE_ID_RE.fullmatch(package_id):
            issues.append(issue("error", path, f"package id 格式错误，必须为 8 位小写字母数字: {package_id}"))
        elif registry_info["package_ids"] and package_id not in registry_info["package_ids"]:
            issues.append(issue("error", path, f"package id 未在 fgui_id_registry 中注册: {package_id}"))
        return

    if elem.tag in {"component", "image", "sound", "movieclip", "font", "atlas", "misc"}:
        resource_id = elem.attrib.get("id", "")
        if not RESOURCE_ID_RE.fullmatch(resource_id):
            issues.append(issue("error", path, f"资源 id 格式错误，应为 2-16 位小写字母数字: {resource_id}"))
        elif current_package_id:
            package_resources = registry_info["resource_ids_by_package_id"].get(current_package_id, set())
            if resource_id not in package_resources:
                issues.append(
                    issue(
                        "error",
                        path,
                        f"package.xml 资源 id 未注册到当前包 {current_package_id}: {resource_id}",
                    )
                )
        elif registry_info["resource_ids"] and resource_id not in registry_info["resource_ids"]:
            issues.append(issue("error", path, f"package.xml 资源 id 未在 registry 中注册: {resource_id}"))

        name = elem.attrib.get("name", "")
        if not name:
            issues.append(issue("error", path, f"<{elem.tag}> 缺少 name"))

        if elem.tag == "component" and not name.endswith(".xml"):
            issues.append(issue("error", path, f"component@name 必须是 XML 文件名: {name}"))

        path_attr = elem.attrib.get("path", "")
        if not path_attr.startswith("/") or not path_attr.endswith("/"):
            add_mode_issue(issues, mode, path, f"资源 path 应以 / 开头并以 / 结尾: {path_attr}")

        relative_raw = f"{path_attr.strip('/')}/{name}".strip("/")
        relative_path = PurePosixPath(relative_raw.replace("\\", "/"))
        relative_value = str(relative_path)
        relative_parts = relative_path.parts
        if not relative_value or relative_path.is_absolute() or ".." in relative_parts:
            issues.append(issue("error", path, f"package.xml 资源路径非法: path={path_attr}, name={name}"))
        else:
            resource_file = package_root / normalize_relative_path(relative_value)
            if not resource_file.is_file():
                issues.append(
                    issue(
                        "error",
                        path,
                        f"package.xml 资源文件不存在（按包根目录解析）: {relative_value} -> {resource_file}",
                    )
                )

        if elem.tag == "image" and resource_id:
            asset = resolve_manifest_asset(current_package_id, resource_id, registry_info, manifest_info)
            if asset is not None:
                expected_relative = asset.get("packageRelativeFile")
                if not isinstance(expected_relative, str) or not expected_relative:
                    issues.append(issue("error", path, f"manifest 资源 {asset.get('name')} 缺少 packageRelativeFile"))
                elif normalize_path(expected_relative) != relative_value:
                    issues.append(
                        issue(
                            "error",
                            path,
                            f"package.xml path+name 与 manifest.packageRelativeFile 不一致: XML={relative_value}, manifest={expected_relative}",
                        )
                    )


def validate_component_element(
    path: Path,
    root: ET.Element,
    elem: ET.Element,
    mode: str,
    current_package_id: str | None,
    registry_info: dict[str, Any],
    manifest_info: dict[str, Any],
    package_root: Path,
    issues: list[dict[str, str]],
) -> None:
    if elem is root:
        if "size" not in elem.attrib:
            issues.append(issue("error", path, "component 根节点缺少 size"))
        remark = elem.attrib.get("remark")
        if remark is not None and not remark.isdigit():
            issues.append(issue("warning", path, f"remark 通常应为数字，当前值: {remark}"))
        return

    if elem.tag in DISPLAY_OBJECT_TAGS:
        elem_id = elem.attrib.get("id")
        if not elem_id:
            issues.append(issue("error", path, f"<{elem.tag}> 缺少 id"))
        elif mode == "fresh" and not INSTANCE_ID_RE.fullmatch(elem_id):
            issues.append(issue("error", path, f"新生成实例 id 格式错误，应为 n数字_包ID后4位: {elem_id}"))
        elif mode == "editor-compatible" and not INSTANCE_ID_RE.fullmatch(elem_id):
            issues.append(issue("warning", path, f"保留编辑器实例 id，但不符合新生成命名约定: {elem_id}"))

        if "name" not in elem.attrib:
            issues.append(issue("error", path, f"<{elem.tag}> 缺少 name"))

    if elem.tag == "component":
        validate_component_extension_overrides(
            path,
            elem,
            mode,
            current_package_id,
            registry_info,
            package_root,
            issues,
        )

    if elem.tag == "image":
        src = elem.attrib.get("src", "")
        file_name = elem.attrib.get("fileName", "")
        xml_size = parse_size(elem.attrib.get("size"))

        if not src:
            issues.append(issue("error", path, "image 缺少 src"))
        elif not RESOURCE_ID_RE.fullmatch(src):
            issues.append(issue("error", path, f"image@src 必须是资源 ID，不是资源名或文件名: {src}"))
        elif not resource_reference_resolves(elem, src, current_package_id, registry_info):
            issues.append(issue("error", path, f"image@src 未在正确的本包或跨包 registry 中注册: {src}"))

        if not file_name:
            issues.append(issue("error", path, "image 缺少 fileName"))

        if src and manifest_info["assets_by_name"]:
            asset = resolve_manifest_asset(current_package_id, src, registry_info, manifest_info)
            if asset is None:
                add_mode_issue(
                    issues,
                    mode,
                    path,
                    f"无法通过 registry 中的资源名把 image@src={src} 映射到 asset_manifest.json",
                )
            else:
                expected_file = asset.get("file")
                expected_package_file = asset.get("packageRelativeFile")
                source_size = asset.get("sourcePixelSize")
                display_size = asset.get("displaySize")
                scale_policy = asset.get("scalePolicy")
                render_mode = asset.get("renderMode")

                if not isinstance(expected_package_file, str) or not expected_package_file:
                    issues.append(issue("error", path, f"manifest 资源 {asset.get('name')} 缺少 packageRelativeFile"))
                elif file_name:
                    actual_package_raw = file_name.replace("\\", "/")
                    actual_package_path = PurePosixPath(actual_package_raw)
                    actual_package_file = str(actual_package_path).lstrip("./")
                    expected_package_file_normalized = normalize_path(expected_package_file)
                    if actual_package_raw.startswith("/") or actual_package_path.is_absolute() or ".." in actual_package_path.parts:
                        issues.append(issue("error", path, f"image@fileName 必须是安全的包内相对路径: {file_name}"))
                    if actual_package_file != expected_package_file_normalized:
                        level = "error" if mode == "fresh" else "warning"
                        issues.append(
                            issue(
                                level,
                                path,
                                f"image@fileName 必须使用精确包内路径: XML={actual_package_file}, manifest={expected_package_file_normalized}",
                            )
                        )
                    resolved_package_file = package_root / normalize_relative_path(actual_package_file)
                    if not resolved_package_file.is_file():
                        issues.append(issue("error", path, f"image@fileName 在包目录中不存在: {actual_package_file} -> {resolved_package_file}"))

                if not (isinstance(source_size, list) and len(source_size) == 2 and all(isinstance(v, int) and v > 0 for v in source_size)):
                    add_mode_issue(issues, mode, path, f"manifest 资源 {asset.get('name')} 缺少有效 sourcePixelSize")
                if not (isinstance(display_size, list) and len(display_size) == 2 and all(isinstance(v, int) and v > 0 for v in display_size)):
                    add_mode_issue(issues, mode, path, f"manifest 资源 {asset.get('name')} 缺少有效 displaySize")
                if scale_policy not in SCALE_POLICIES:
                    add_mode_issue(issues, mode, path, f"manifest 资源 {asset.get('name')} 的 scalePolicy 缺失或非法: {scale_policy}")
                if render_mode not in RENDER_MODES:
                    add_mode_issue(issues, mode, path, f"manifest 资源 {asset.get('name')} 的 renderMode 缺失或非法: {render_mode}")
                elif scale_policy in RENDER_MODES_BY_POLICY and render_mode not in RENDER_MODES_BY_POLICY[scale_policy]:
                    issues.append(issue("error", path, f"renderMode 与 scalePolicy 不匹配: scalePolicy={scale_policy}, renderMode={render_mode}"))

                valid_source = isinstance(source_size, list) and len(source_size) == 2 and all(isinstance(v, int) and v > 0 for v in source_size)
                valid_display = isinstance(display_size, list) and len(display_size) == 2 and all(isinstance(v, int) and v > 0 for v in display_size)

                if xml_size is None:
                    if mode == "fresh":
                        issues.append(issue("error", path, f"新生成 image 必须显式声明 size，目标 displaySize={display_size}"))
                    elif valid_source and valid_display and source_size == display_size:
                        issues.append(issue("warning", path, f"编辑器 XML 未显式声明 image@size，按 source=display={display_size} 人工确认"))
                    else:
                        issues.append(issue("error", path, f"image 未声明 size，且 sourcePixelSize={source_size} 与 displaySize={display_size} 不同"))
                elif valid_display and xml_size != display_size:
                    issues.append(issue("error", path, f"image@size 与 manifest.displaySize 不一致: XML={xml_size}, manifest={display_size}"))

                if valid_source and valid_display and scale_policy == "pixel_exact" and source_size != display_size:
                    issues.append(issue("error", path, f"pixel_exact 资源尺寸不一致: sourcePixelSize={source_size}, displaySize={display_size}"))

                if scale_policy == "nine_slice":
                    grid = asset.get("nineSliceGrid")
                    valid_grid = isinstance(grid, list) and len(grid) == 4 and all(isinstance(v, int) and v >= 0 for v in grid) and grid[2] > 0 and grid[3] > 0
                    if render_mode != "nine_slice" or not valid_grid:
                        issues.append(issue("error", path, "nine_slice 资源缺少合法 renderMode/nineSliceGrid"))
                    elif valid_source and (grid[0] + grid[2] > source_size[0] or grid[1] + grid[3] > source_size[1]):
                        issues.append(issue("error", path, f"nineSliceGrid 超出 sourcePixelSize: grid={grid}, source={source_size}"))

                project_root = manifest_info.get("project_root")
                if isinstance(project_root, Path) and isinstance(expected_file, str):
                    asset_path = project_root / normalize_relative_path(expected_file)
                    if not asset_path.is_file():
                        add_mode_issue(issues, mode, path, f"manifest 资源文件不存在: {asset_path}")
                    else:
                        try:
                            metadata = read_image_metadata(asset_path)
                        except (OSError, ImageMetadataError) as exc:
                            add_mode_issue(issues, mode, path, f"无法读取资源图片像素尺寸: {asset_path}: {exc}")
                        else:
                            actual_size = [metadata["width"], metadata["height"]]
                            if valid_source and actual_size != source_size:
                                issues.append(issue("error", path, f"实际图片像素与 sourcePixelSize 不一致: actual={actual_size}, manifest={source_size}"))
                            if asset.get("transparent") is True and metadata.get("format") == "png" and metadata.get("hasAlphaCapability") is not True:
                                issues.append(issue("error", path, "资源声明 transparent=true，但 PNG 不支持 Alpha 通道"))

    if elem.tag in {"text", "richtext"}:
        if "xy" not in elem.attrib:
            issues.append(issue("error", path, f"<{elem.tag}> 缺少 xy"))
        if "size" not in elem.attrib:
            issues.append(issue("error", path, f"<{elem.tag}> 缺少 size"))

    if elem.tag == "component":
        src = elem.attrib.get("src")
        if src:
            if not RESOURCE_ID_RE.fullmatch(src):
                issues.append(issue("error", path, f"child component@src 必须是资源 ID: {src}"))
            elif not resource_reference_resolves(elem, src, current_package_id, registry_info):
                issues.append(issue("error", path, f"child component@src 未在正确的本包或跨包 registry 中注册: {src}"))

    if elem.tag == "loader":
        url = elem.attrib.get("url")
        if url:
            check_url(path, url, registry_info, issues, "loader@url")

    if elem.tag == "list":
        for required in ("xy", "size"):
            if required not in elem.attrib:
                issues.append(issue("error", path, f"list 缺少 {required}"))
        default_item = elem.attrib.get("defaultItem")
        if default_item:
            check_url(path, default_item, registry_info, issues, "list@defaultItem")


def resource_reference_resolves(
    elem: ET.Element,
    resource_id: str,
    current_package_id: str | None,
    registry_info: dict[str, Any],
) -> bool:
    if not registry_info["resource_ids"]:
        return True

    cross_package_id = elem.attrib.get("pkg")
    target_package_id = cross_package_id or current_package_id
    if target_package_id:
        package_resources = registry_info["resource_ids_by_package_id"].get(target_package_id)
        return bool(package_resources and resource_id in package_resources)

    return resource_id in registry_info["resource_ids"]


def check_url(
    path: Path,
    url: str,
    registry_info: dict[str, Any],
    issues: list[dict[str, str]],
    label: str,
) -> None:
    match = URL_RE.fullmatch(url)
    if not match:
        issues.append(issue("error", path, f"{label} 格式错误，应为 ui://8位包ID + 已注册资源ID: {url}"))
        return

    package_id, resource_id = match.groups()
    if registry_info["package_ids"] and package_id not in registry_info["package_ids"]:
        issues.append(issue("error", path, f"{label} 包 ID 未注册: {package_id}"))
        return

    package_resources = registry_info["resource_ids_by_package_id"].get(package_id, set())
    if registry_info["resource_ids_by_package_id"] and resource_id not in package_resources:
        issues.append(issue("error", path, f"{label} 资源 ID 未注册到包 {package_id}: {resource_id}"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate FairyGUI XML drafts generated by AI or exported by the editor.")
    parser.add_argument("--xml-dir", required=True, help="Directory containing package.xml and component XML files")
    parser.add_argument("--manifest", default="", help="Path to asset_manifest.json")
    parser.add_argument("--registry", default="", help="Path to fgui_id_registry.json")
    parser.add_argument("--out", default="", help="Output JSON report path")
    parser.add_argument(
        "--mode",
        choices=("fresh", "editor-compatible"),
        default="fresh",
        help="fresh enforces generated-ID conventions; editor-compatible preserves editor exports",
    )
    args = parser.parse_args()

    xml_dir = Path(args.xml_dir)
    if not xml_dir.exists():
        print(f"xml dir does not exist: {xml_dir}", file=sys.stderr)
        return 2

    registry, registry_error = read_json(args.registry)
    manifest, manifest_error = read_json(args.manifest)
    registry_info = collect_registry(registry)
    manifest_info = collect_manifest(manifest, args.manifest)

    package_name = manifest_info["package_name"] or xml_dir.name
    current_package_id = registry_info["package_id_by_name"].get(package_name)

    all_issues: list[dict[str, str]] = []
    missing_input_level = "error" if args.mode == "fresh" else "warning"

    if not args.registry:
        all_issues.append(issue(missing_input_level, xml_dir, "未提供 --registry，无法验证资源和 URL 是否真实注册"))
    elif registry_error:
        all_issues.append(issue("error", xml_dir, f"registry 不存在或无法读取: {args.registry}: {registry_error}"))

    if not args.manifest:
        all_issues.append(issue(missing_input_level, xml_dir, "未提供 --manifest，无法验证 image@fileName 与资源清单一致性"))
    elif manifest_error:
        all_issues.append(issue("error", xml_dir, f"manifest 不存在或无法读取: {args.manifest}: {manifest_error}"))

    if registry and manifest and current_package_id is None:
        all_issues.append(
            issue(
                "error",
                xml_dir,
                f"manifest package.name={package_name} 无法映射到 fgui_id_registry.json 中的包",
            )
        )

    xml_files = sorted(xml_dir.rglob("*.xml"))
    if not xml_files:
        all_issues.append(issue("error", xml_dir, "XML 目录中没有找到任何 .xml 文件"))

    for xml_file in xml_files:
        all_issues.extend(
            validate_file(
                xml_file,
                args.mode,
                current_package_id,
                registry_info,
                manifest_info,
                xml_dir.resolve(),
            )
        )

    semantic_controller_mapping_checked = False
    visual_part_coverage_checked = False
    project_root = manifest_info.get("project_root")
    production = manifest.get("production", {}) if isinstance(manifest, dict) else {}
    requires_semantic_mapping = (
        isinstance(project_root, Path)
        and (
            (project_root / "specs" / "component_state_map.json").is_file()
            or (
                isinstance(production, dict)
                and (
                    production.get("generateFullScreenDesign") is True
                    or production.get("requiresDesignApproval") is True
                )
            )
        )
    )
    if requires_semantic_mapping and isinstance(project_root, Path):
        semantic_controller_mapping_checked = True
        semantic_report = validate_semantic_controller_mapping(project_root, "xml_generation", xml_dir)
        for item in semantic_report.get("errors", []):
            item_path = Path(item["path"]) if item.get("path") else xml_dir
            all_issues.append(issue("error", item_path, f"semantic controller mapping [{item.get('code', 'invalid')}]: {item.get('message', 'invalid')}"))
        for item in semantic_report.get("warnings", []):
            item_path = Path(item["path"]) if item.get("path") else xml_dir
            all_issues.append(issue("warning", item_path, f"semantic controller mapping [{item.get('code', 'warning')}]: {item.get('message', 'warning')}"))

    requires_visual_part_coverage = (
        isinstance(project_root, Path)
        and (
            (project_root / "specs" / "component_visual_parts.json").is_file()
            or (
                isinstance(production, dict)
                and (
                    production.get("generateFullScreenDesign") is True
                    or production.get("requiresVisualPartCoverage") is True
                )
            )
        )
    )
    if requires_visual_part_coverage and isinstance(project_root, Path):
        visual_part_coverage_checked = True
        visual_part_report = validate_visual_part_coverage(project_root, "xml_generation", xml_dir)
        for item in visual_part_report.get("errors", []):
            item_path = Path(item["path"]) if item.get("path") else xml_dir
            all_issues.append(issue("error", item_path, f"visual part coverage [{item.get('code', 'invalid')}]: {item.get('message', 'invalid')}"))
        for item in visual_part_report.get("warnings", []):
            item_path = Path(item["path"]) if item.get("path") else xml_dir
            all_issues.append(issue("warning", item_path, f"visual part coverage [{item.get('code', 'warning')}]: {item.get('message', 'warning')}"))

    report = {
        "ok": not any(item["level"] == "error" for item in all_issues),
        "mode": args.mode,
        "package_name": package_name,
        "package_id": current_package_id,
        "files_checked": len(xml_files),
        "manifest_loaded": bool(manifest),
        "registry_loaded": bool(registry),
        "package_resource_paths_checked": True,
        "component_extension_overrides_checked": True,
        "semantic_controller_mapping_checked": semantic_controller_mapping_checked,
        "component_instance_configurations_checked": semantic_controller_mapping_checked,
        "visual_part_coverage_checked": visual_part_coverage_checked,
        "error_count": sum(1 for item in all_issues if item["level"] == "error"),
        "warning_count": sum(1 for item in all_issues if item["level"] == "warning"),
        "issues": all_issues,
    }

    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
