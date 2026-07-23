#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate reusable-component planning, parameterization, and XML structure.

The validator prevents data-only differences from becoming permanent duplicate
FairyGUI component XML files. It validates component_state_map reusePlan data,
the fgui_spec Component Reuse Plan table, and optional XML structural
signatures.
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

STAGES = {"semantic_analysis", "fairygui_assembly", "xml_generation"}
REUSE_STRATEGIES = {"single_component", "composite_component", "variant_allowed", "unique_component"}
EXTENSIONS = {"Button", "Label", "none"}
VARIANT_REASONS = {
    "structural_difference",
    "verified_editor_limitation",
    "package_compatibility",
    "temporary_preview_only",
}
CONFIGURATION_MODES = {
    "variant_component", "extension_override", "controller_pages", "runtime_binding", "static_default"
}
NONE_VALUES = {"", "none", "n/a", "na", "null", "无"}


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


def normalized_file(value: Any) -> str:
    return str(PurePosixPath(str(value).replace("\\", "/"))).lower().lstrip("./")


def split_values(value: Any) -> list[str]:
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(split_values(item))
        return result
    if value is None:
        return []
    text = str(value).strip().strip("`")
    if text.lower() in NONE_VALUES:
        return []
    return [part.strip().strip("`") for part in re.split(r"[,;|、，；\n]+", text) if part.strip()]


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


def list_of_objects(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


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


def component_index(components: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for component in components:
        for field in ("componentType", "fguiComponent", "name"):
            value = component.get(field)
            if isinstance(value, str) and value:
                result[normalized(value)] = component
    return result


def find_component(index: dict[str, dict[str, Any]], value: Any) -> dict[str, Any] | None:
    key = normalized(value)
    if key in index:
        return index[key]
    candidates = {id(component): component for alias, component in index.items() if key and (key in alias or alias in key)}
    return next(iter(candidates.values())) if len(candidates) == 1 else None


def flatten_extension_fields(parameters: Any) -> set[str]:
    result: set[str] = set()
    if not isinstance(parameters, dict):
        return result
    for extension, values in parameters.items():
        if not isinstance(values, dict):
            continue
        for attribute in values:
            result.add(normalized(f"{extension}.{attribute}"))
    return result


def validate_semantic_reuse(
    report: dict[str, Any],
    state_map_path: Path,
    state_map: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    components = list_of_objects(state_map.get("components"))
    instances = list_of_objects(state_map.get("visualInstances"))
    index = component_index(components)
    grouped_instances: dict[str, list[dict[str, Any]]] = {}

    for component_position, component in enumerate(components):
        component_type = component.get("componentType")
        reusable = component.get("reusable")
        plan = component.get("reusePlan")
        if reusable is not True:
            if isinstance(plan, dict) and plan.get("strategy") in {"single_component", "composite_component", "variant_allowed"}:
                add(report, "warnings", "non_reusable_component_has_reuse_plan", f"组件 {component_type} 标记 reusable=false，但声明了复用策略", state_map_path)
            continue
        if not isinstance(plan, dict):
            add(report, "errors", "component_reuse_plan_missing", f"复用组件 {component_type} 缺少 reusePlan", state_map_path)
            continue

        strategy = plan.get("strategy")
        base_file = plan.get("baseComponentFile")
        extension = plan.get("extension")
        parameterizable = plan.get("parameterizableFields")
        child_files = plan.get("childComponentFiles")
        variant_reasons = plan.get("variantReasons")

        if strategy not in REUSE_STRATEGIES:
            add(report, "errors", "component_reuse_strategy_invalid", f"组件 {component_type}.reusePlan.strategy 非法: {strategy}", state_map_path)
        if strategy == "unique_component":
            add(report, "errors", "reusable_component_marked_unique", f"组件 {component_type} 标记 reusable=true，却使用 unique_component", state_map_path)
        if not isinstance(base_file, str) or not base_file.endswith(".xml"):
            add(report, "errors", "component_reuse_base_file_missing", f"组件 {component_type} 缺少合法 baseComponentFile", state_map_path)
        if extension not in EXTENSIONS:
            add(report, "errors", "component_reuse_extension_invalid", f"组件 {component_type}.reusePlan.extension 非法: {extension}", state_map_path)
        if not isinstance(parameterizable, list):
            add(report, "errors", "component_parameterizable_fields_invalid", f"组件 {component_type}.parameterizableFields 必须是数组", state_map_path)
        else:
            extension_fields = [str(item) for item in parameterizable if isinstance(item, str) and "." in item and item.split(".", 1)[0] in {"Button", "Label"}]
            if extension == "none" and extension_fields:
                add(report, "errors", "component_parameter_extension_missing", f"组件 {component_type} 声明了外部参数 {extension_fields}，但 reusePlan.extension=none", state_map_path)
            if extension in {"Button", "Label"}:
                wrong_extension_fields = [item for item in extension_fields if not item.startswith(extension + ".")]
                if wrong_extension_fields:
                    add(report, "errors", "component_parameter_extension_mismatch", f"组件 {component_type} 的参数字段与 extension={extension} 不一致: {wrong_extension_fields}", state_map_path)
        if not isinstance(child_files, list):
            add(report, "errors", "component_child_files_invalid", f"组件 {component_type}.childComponentFiles 必须是数组", state_map_path)
        elif any(not isinstance(item, str) or not item.endswith(".xml") for item in child_files):
            add(report, "errors", "component_child_file_invalid", f"组件 {component_type}.childComponentFiles 包含非法 XML 文件", state_map_path)
        if not isinstance(variant_reasons, list):
            add(report, "errors", "component_variant_reasons_invalid", f"组件 {component_type}.variantReasons 必须是数组", state_map_path)
        else:
            invalid_reasons = [reason for reason in variant_reasons if reason not in VARIANT_REASONS]
            if invalid_reasons:
                add(report, "errors", "component_variant_reason_invalid", f"组件 {component_type}.variantReasons 包含非法值: {invalid_reasons}", state_map_path)
        if strategy == "composite_component" and not child_files:
            add(report, "errors", "composite_component_children_missing", f"复合组件 {component_type} 必须声明 childComponentFiles", state_map_path)
        if strategy == "variant_allowed" and not variant_reasons:
            add(report, "errors", "variant_allowed_reasons_missing", f"组件 {component_type} 使用 variant_allowed，但 variantReasons 为空", state_map_path)
        if strategy in {"single_component", "composite_component"} and variant_reasons:
            add(report, "warnings", "unused_variant_reasons", f"组件 {component_type} 不允许变体，但 variantReasons 非空", state_map_path)

    base_file_owners: dict[str, list[str]] = {}
    for component in components:
        if component.get("reusable") is not True:
            continue
        plan = component.get("reusePlan") if isinstance(component.get("reusePlan"), dict) else {}
        base_file = plan.get("baseComponentFile")
        if isinstance(base_file, str):
            base_file_owners.setdefault(normalized_file(base_file), []).append(str(component.get("componentType", "")))
    for base_file, owners in base_file_owners.items():
        if len(owners) > 1:
            add(report, "errors", "base_component_shared_by_multiple_types", f"同一个基组件文件 {base_file} 被多个 componentType 使用: {owners}；应合并语义组件类型或明确包装层", state_map_path)
    for component in components:
        if component.get("reusable") is not True:
            continue
        plan = component.get("reusePlan") if isinstance(component.get("reusePlan"), dict) else {}
        if plan.get("strategy") != "composite_component":
            continue
        for child_file in split_values(plan.get("childComponentFiles")):
            if normalized_file(child_file) not in base_file_owners:
                add(report, "errors", "composite_child_reuse_plan_missing", f"复合组件 {component.get('componentType')} 的子组件 {child_file} 没有独立 reusable 组件条目和 reusePlan", state_map_path)

    for position, instance in enumerate(instances):
        component = find_component(index, instance.get("componentType"))
        if component is None:
            continue
        component_key = normalized(component.get("componentType"))
        grouped_instances.setdefault(component_key, []).append(instance)
        if component.get("reusable") is not True:
            continue
        plan = component.get("reusePlan") if isinstance(component.get("reusePlan"), dict) else {}
        strategy = plan.get("strategy")
        base_file = plan.get("baseComponentFile")
        allowed_parameters = {normalized(item) for item in split_values(plan.get("parameterizableFields"))}
        allowed_variant_reasons = set(split_values(plan.get("variantReasons")))
        implementation = instance.get("implementation") if isinstance(instance.get("implementation"), dict) else {}
        mode = implementation.get("configurationMode")
        component_file = implementation.get("componentFile")
        instance_id = instance.get("instanceId") or f"visualInstances[{position}]"

        if mode not in CONFIGURATION_MODES:
            continue
        if strategy in {"single_component", "composite_component"}:
            if mode == "variant_component":
                add(report, "errors", "variant_component_forbidden_by_reuse_plan", f"实例 {instance_id} 属于 {strategy}，禁止使用 variant_component", state_map_path)
            if isinstance(base_file, str) and normalized_file(component_file) != normalized_file(base_file):
                add(report, "errors", "instance_must_use_base_component", f"实例 {instance_id} 必须使用基组件 {base_file}，实际 {component_file}", state_map_path)

        if mode == "extension_override":
            if plan.get("extension") not in {"Button", "Label"}:
                add(report, "errors", "extension_override_without_extension", f"实例 {instance_id} 使用 extension_override，但组件 reusePlan.extension={plan.get('extension')}", state_map_path)
            fields = flatten_extension_fields(implementation.get("extensionParameters"))
            if not fields:
                add(report, "errors", "extension_override_parameters_missing", f"实例 {instance_id} 使用 extension_override，但没有 extensionParameters", state_map_path)
            undeclared = sorted(field for field in fields if field not in allowed_parameters)
            if undeclared:
                add(report, "errors", "extension_parameter_not_declared", f"实例 {instance_id} 使用了未在 reusePlan.parameterizableFields 声明的外部参数: {undeclared}", state_map_path)

        if mode == "controller_pages":
            controller_parameters = implementation.get("controllerParameters")
            if not isinstance(controller_parameters, dict) or not controller_parameters:
                add(report, "errors", "controller_parameters_missing", f"实例 {instance_id} 使用 controller_pages，但没有 controllerParameters", state_map_path)
            else:
                undeclared_controllers = sorted(
                    controller_name
                    for controller_name in controller_parameters
                    if normalized(f"controller.{controller_name}") not in allowed_parameters
                )
                if undeclared_controllers:
                    add(report, "errors", "controller_parameter_not_declared", f"实例 {instance_id} 外传的 Controller 未在 reusePlan.parameterizableFields 声明: {undeclared_controllers}", state_map_path)
                if len(controller_parameters) > 1:
                    add(report, "errors", "multiple_controller_parameters_unverified", f"实例 {instance_id} 同时外传多个 Controller；当前仅允许一个经过 FairyGUI Editor 验证的 controller 属性", state_map_path)
            if isinstance(base_file, str) and normalized_file(component_file) != normalized_file(base_file):
                add(report, "errors", "controller_pages_must_use_base_component", f"实例 {instance_id} 使用外部 Controller 参数时必须引用基组件 {base_file}", state_map_path)

        uses_variant = mode == "variant_component" or (
            isinstance(base_file, str) and isinstance(component_file, str)
            and normalized(component_file) != normalized(base_file)
        )
        if uses_variant:
            if strategy != "variant_allowed":
                add(report, "errors", "variant_not_allowed", f"实例 {instance_id} 使用变体文件，但组件复用策略不是 variant_allowed", state_map_path)
                continue
            justification = implementation.get("variantJustification")
            if not isinstance(justification, dict):
                add(report, "errors", "variant_justification_missing", f"实例 {instance_id} 使用变体文件但缺少 variantJustification", state_map_path)
                continue
            reason = justification.get("reason")
            if reason not in VARIANT_REASONS or reason not in allowed_variant_reasons:
                add(report, "errors", "variant_justification_reason_invalid", f"实例 {instance_id} 的变体理由未被 reusePlan 允许: {reason}", state_map_path)
            if reason == "structural_difference":
                differences = justification.get("structuralDifferences")
                if not isinstance(differences, list) or not any(isinstance(item, str) and item.strip() for item in differences):
                    add(report, "errors", "variant_structural_differences_missing", f"实例 {instance_id} 声明 structural_difference，但未列出结构差异", state_map_path)
            if reason == "temporary_preview_only" and justification.get("retireAfterEditorValidation") is not True:
                add(report, "errors", "temporary_variant_retirement_missing", f"实例 {instance_id} 的临时预览变体必须设置 retireAfterEditorValidation=true", state_map_path)

    for component_key, component_instances in grouped_instances.items():
        component = find_component(index, component_key)
        if component is None or component.get("reusable") is not True:
            continue
        plan = component.get("reusePlan") if isinstance(component.get("reusePlan"), dict) else {}
        strategy = plan.get("strategy")
        files = {
            normalized_file((item.get("implementation") or {}).get("componentFile"))
            for item in component_instances
            if isinstance(item.get("implementation"), dict)
            and isinstance((item.get("implementation") or {}).get("componentFile"), str)
        }
        files.discard("")
        if len(files) > 1 and strategy in {"single_component", "composite_component"}:
            add(report, "errors", "reusable_component_split_into_multiple_files", f"组件 {component.get('componentType')} 使用 {strategy}，却被拆成多个组件文件", state_map_path)

    return components, instances, index


def validate_fgui_spec(
    report: dict[str, Any],
    path: Path,
    components: list[dict[str, Any]],
) -> None:
    reusable_components = [component for component in components if component.get("reusable") is True]
    if not reusable_components:
        return
    if not require_file(report, path, "component_reuse_fgui_spec_missing", "fgui_spec.md"):
        return
    text = read_text(path)
    headers, rows = parse_markdown_table(text, "Component Reuse Plan")
    required = {
        "component type", "strategy", "base component file", "extension",
        "parameterizable fields", "child components", "variant reasons", "requirement ids",
    }
    missing = sorted(required.difference(headers))
    if missing:
        add(report, "errors", "component_reuse_table_columns_missing", f"fgui_spec Component Reuse Plan 缺少列: {missing}", path)
        return

    row_index: dict[str, dict[str, str]] = {}
    row_counts: dict[str, int] = {}
    for row in rows:
        component_key = normalized(row.get("component type"))
        if not component_key:
            continue
        row_counts[component_key] = row_counts.get(component_key, 0) + 1
        row_index[component_key] = row
    for component_key, count in row_counts.items():
        if count > 1:
            add(report, "errors", "component_reuse_table_row_duplicate", f"Component Reuse Plan 中组件 {component_key} 出现 {count} 次", path)
    for component in reusable_components:
        component_type = str(component.get("componentType", ""))
        plan = component.get("reusePlan") if isinstance(component.get("reusePlan"), dict) else {}
        row = row_index.get(normalized(component_type))
        if row is None:
            add(report, "errors", "component_reuse_table_row_missing", f"复用组件 {component_type} 未写入 fgui_spec Component Reuse Plan", path)
            continue
        expected = {
            "strategy": plan.get("strategy"),
            "base component file": plan.get("baseComponentFile"),
            "extension": plan.get("extension"),
        }
        for column, value in expected.items():
            if value and (normalized_file(row.get(column)) != normalized_file(value) if column == "base component file" else normalized(row.get(column)) != normalized(value)):
                add(report, "errors", "component_reuse_table_mismatch", f"组件 {component_type} 的 {column} 与 component_state_map.reusePlan 不一致", path)
        expected_parameters = {normalized(item) for item in split_values(plan.get("parameterizableFields"))}
        actual_parameters = {normalized(item) for item in split_values(row.get("parameterizable fields"))}
        if expected_parameters != actual_parameters:
            add(report, "errors", "component_reuse_parameters_mismatch", f"组件 {component_type} 的 Parameterizable Fields 不一致", path)
        expected_children = {normalized_file(item) for item in split_values(plan.get("childComponentFiles"))}
        actual_children = {normalized_file(item) for item in split_values(row.get("child components"))}
        if expected_children != actual_children:
            add(report, "errors", "component_reuse_children_mismatch", f"组件 {component_type} 的 Child Components 不一致", path)
        expected_reasons = {normalized(item) for item in split_values(plan.get("variantReasons"))}
        actual_reasons = {normalized(item) for item in split_values(row.get("variant reasons"))}
        if expected_reasons != actual_reasons:
            add(report, "errors", "component_reuse_variant_reasons_mismatch", f"组件 {component_type} 的 Variant Reasons 不一致", path)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def controller_page_names(value: str | None) -> tuple[str, ...]:
    tokens = split_values(value)
    if len(tokens) % 2 == 0 and tokens and all(tokens[index].isdigit() for index in range(0, len(tokens), 2)):
        tokens = tokens[1::2]
    return tuple(normalized(token) for token in tokens)


def structural_signature(element: ET.Element) -> tuple[Any, ...]:
    tag = local_name(element.tag)
    details: list[Any] = [tag, normalized(element.attrib.get("name", ""))]
    if tag == "component" and "extention" in element.attrib:
        details.append(("extention", element.attrib.get("extention")))
    if tag == "component" and element.attrib.get("fileName"):
        details.append(("childFile", normalized_file(element.attrib.get("fileName"))))
    if tag == "controller":
        details.append(("controller", normalized(element.attrib.get("name"))))
        details.append(("pages", controller_page_names(element.attrib.get("pages"))))
    return tuple(details + [tuple(structural_signature(child) for child in list(element))])


def hierarchy_signature(element: ET.Element) -> tuple[Any, ...]:
    tag = local_name(element.tag)
    details: list[Any] = [tag]
    if tag == "component" and "extention" in element.attrib:
        details.append(("extention", element.attrib.get("extention")))
    if tag == "component" and element.attrib.get("fileName"):
        details.append(("childComponent", True))
    if tag == "controller":
        details.append(("pages", controller_page_names(element.attrib.get("pages"))))
    return tuple(details + [tuple(hierarchy_signature(child) for child in list(element))])


def structural_features(root: ET.Element) -> set[str]:
    result: set[str] = set()

    def visit(element: ET.Element, path: tuple[str, ...]) -> None:
        tag = local_name(element.tag)
        name = normalized(element.attrib.get("name", ""))
        token = f"{tag}:{name}" if name else tag
        current = path + (token,)
        result.add("/".join(current))
        for child in list(element):
            visit(child, current)

    visit(root, tuple())
    return result


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def parse_xml(path: Path) -> ET.Element | None:
    try:
        return ET.fromstring(read_text(path))
    except (OSError, ET.ParseError):
        return None


def resolve_xml_file(xml_dir: Path, file_name: str) -> Path | None:
    direct = xml_dir / Path(file_name.replace("\\", "/"))
    if direct.is_file():
        return direct
    matches = [path for path in xml_dir.rglob(Path(file_name.replace("\\", "/")).name) if path.is_file()]
    return matches[0] if len(matches) == 1 else None


def validate_visual_part_file_scope(
    report: dict[str, Any],
    root: Path,
    components: list[dict[str, Any]],
    index: dict[str, dict[str, Any]],
) -> None:
    coverage_path = root / "specs" / "component_visual_parts.json"
    if not coverage_path.is_file():
        return
    try:
        coverage = load_json(coverage_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        add(report, "errors", "component_reuse_visual_parts_invalid", f"component_visual_parts.json 无法解析: {exc}", coverage_path)
        return
    for group in list_of_objects(coverage.get("components")):
        component = find_component(index, group.get("componentType"))
        if component is None or component.get("reusable") is not True:
            continue
        plan = component.get("reusePlan") if isinstance(component.get("reusePlan"), dict) else {}
        strategy = plan.get("strategy")
        base_file = plan.get("baseComponentFile")
        files = {normalized_file(item) for item in split_values(group.get("componentFiles"))}
        if strategy in {"single_component", "composite_component"} and isinstance(base_file, str):
            extras = sorted(file_name for file_name in files if file_name != normalized_file(base_file))
            if extras:
                add(
                    report,
                    "errors",
                    "visual_part_component_files_violate_reuse_plan",
                    f"组件 {component.get('componentType')} 的视觉部件清单包含基组件之外的文件: {extras}",
                    coverage_path,
                )


def validate_xml_parameter_overrides(
    report: dict[str, Any],
    xml_dir: Path,
    components: list[dict[str, Any]],
) -> None:
    plans_by_file: dict[str, tuple[str, dict[str, Any]]] = {}
    for component in components:
        if component.get("reusable") is not True:
            continue
        plan = component.get("reusePlan") if isinstance(component.get("reusePlan"), dict) else {}
        base_file = plan.get("baseComponentFile")
        if isinstance(base_file, str):
            plans_by_file[normalized_file(base_file)] = (str(component.get("componentType", "")), plan)

    for source_path in xml_dir.rglob("*.xml"):
        root = parse_xml(source_path)
        if root is None:
            continue
        for element in root.iter():
            if local_name(element.tag) != "component" or not element.attrib.get("fileName"):
                continue
            matched = plans_by_file.get(normalized_file(element.attrib.get("fileName")))
            if matched is None:
                continue
            component_type, plan = matched
            declared_extension = plan.get("extension")
            allowed = {normalized(item) for item in split_values(plan.get("parameterizableFields"))}
            for child in list(element):
                child_tag = local_name(child.tag)
                if child_tag not in {"Button", "Label"}:
                    continue
                if declared_extension != child_tag:
                    add(
                        report,
                        "errors",
                        "xml_extension_override_reuse_plan_mismatch",
                        f"{source_path.name} 中组件 {component_type} 使用 <{child_tag}> 外部参数，但 reusePlan.extension={declared_extension}",
                        source_path,
                    )
                fields = {normalized(f"{child_tag}.{attribute}") for attribute in child.attrib}
                undeclared = sorted(field for field in fields if field not in allowed)
                if undeclared:
                    add(
                        report,
                        "errors",
                        "xml_extension_parameter_not_declared",
                        f"{source_path.name} 中组件 {component_type} 使用未声明的外部参数: {undeclared}",
                        source_path,
                    )


def validate_xml_reuse(
    report: dict[str, Any],
    xml_dir: Path,
    components: list[dict[str, Any]],
    instances: list[dict[str, Any]],
    index: dict[str, dict[str, Any]],
) -> None:
    if not xml_dir.is_dir():
        add(report, "errors", "component_reuse_xml_dir_missing", "XML 目录不存在", xml_dir)
        return

    validate_xml_parameter_overrides(report, xml_dir, components)

    instances_by_component: dict[str, list[dict[str, Any]]] = {}
    for instance in instances:
        component = find_component(index, instance.get("componentType"))
        if component is not None:
            instances_by_component.setdefault(normalized(component.get("componentType")), []).append(instance)

    for component in components:
        if component.get("reusable") is not True:
            continue
        component_type = str(component.get("componentType", ""))
        component_key = normalized(component_type)
        plan = component.get("reusePlan") if isinstance(component.get("reusePlan"), dict) else {}
        base_file = plan.get("baseComponentFile")
        extension = plan.get("extension")
        child_files = split_values(plan.get("childComponentFiles"))
        file_names: set[str] = set()
        if isinstance(base_file, str):
            file_names.add(base_file)
        for instance in instances_by_component.get(component_key, []):
            implementation = instance.get("implementation") if isinstance(instance.get("implementation"), dict) else {}
            component_file = implementation.get("componentFile")
            if isinstance(component_file, str):
                file_names.add(component_file)

        parsed: dict[str, tuple[Path, ET.Element]] = {}
        for file_name in sorted(file_names):
            path = resolve_xml_file(xml_dir, file_name)
            if path is None:
                add(report, "errors", "component_reuse_xml_file_missing", f"组件 {component_type} 的 XML 文件不存在或同名文件不唯一: {file_name}", xml_dir)
                continue
            root = parse_xml(path)
            if root is None:
                add(report, "errors", "component_reuse_xml_invalid", f"组件 XML 无法解析: {file_name}", path)
                continue
            parsed[file_name] = (path, root)

        if isinstance(base_file, str) and base_file in parsed:
            base_path, base_root = parsed[base_file]
            actual_extension = base_root.attrib.get("extention", "none") or "none"
            if extension in EXTENSIONS and actual_extension != extension:
                add(report, "errors", "component_reuse_extension_mismatch", f"组件 {component_type} 声明 extension={extension}，但基组件 XML 为 {actual_extension}", base_path)
            if plan.get("strategy") == "composite_component":
                referenced_children = {
                    normalized_file(element.attrib.get("fileName"))
                    for element in base_root.iter()
                    if local_name(element.tag) == "component" and element.attrib.get("fileName")
                }
                for child_file in child_files:
                    child_path = resolve_xml_file(xml_dir, child_file)
                    if child_path is None:
                        add(report, "errors", "composite_child_file_missing", f"复合组件 {component_type} 声明的子组件不存在或同名文件不唯一: {child_file}", xml_dir)
                    if normalized_file(child_file) not in referenced_children:
                        add(report, "errors", "composite_child_not_referenced", f"复合组件 {component_type} 的基组件未引用 childComponentFile={child_file}", base_path)

        parsed_items = list(parsed.items())
        for left_index in range(len(parsed_items)):
            left_name, (left_path, left_root) = parsed_items[left_index]
            for right_index in range(left_index + 1, len(parsed_items)):
                right_name, (right_path, right_root) = parsed_items[right_index]
                same_named_structure = structural_signature(left_root) == structural_signature(right_root)
                same_hierarchy = hierarchy_signature(left_root) == hierarchy_signature(right_root)
                if same_named_structure or same_hierarchy:
                    detail = "结构和节点名完全相同" if same_named_structure else "标签层级相同，仅节点名或数据不同"
                    add(
                        report,
                        "errors",
                        "duplicate_variant_structure_should_reuse_base",
                        f"组件 {component_type} 的 {left_name} 与 {right_name} {detail}，应合并为基组件并通过参数、Controller、运行时绑定或可复用子组件配置",
                        left_path,
                    )
                    continue
                similarity = jaccard(structural_features(left_root), structural_features(right_root))
                if similarity >= 0.85:
                    add(
                        report,
                        "warnings",
                        "near_duplicate_variant_should_review_reuse",
                        f"组件 {component_type} 的 {left_name} 与 {right_name} 结构相似度 {similarity:.2f}，应复核是否可以合并",
                        right_path,
                    )


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Component Reuse Report",
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
    state_map_path = root / "specs" / "component_state_map.json"
    fgui_spec_path = root / "specs" / "fgui_spec.md"
    report: dict[str, Any] = {
        "ok": False,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "stage": stage,
        "xmlDir": str(xml_dir.resolve()) if xml_dir else None,
        "errors": [],
        "warnings": [],
        "summary": {
            "reusableComponents": 0,
            "visualInstances": 0,
            "variantFiles": 0,
        },
    }

    if not require_file(report, state_map_path, "component_reuse_state_map_missing", "component_state_map.json"):
        return report
    try:
        state_map = load_json(state_map_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        add(report, "errors", "component_reuse_state_map_invalid", f"component_state_map.json 无法解析: {exc}", state_map_path)
        return report

    components, instances, index = validate_semantic_reuse(report, state_map_path, state_map)
    validate_visual_part_file_scope(report, root, components, index)
    report["summary"]["reusableComponents"] = sum(1 for item in components if item.get("reusable") is True)
    report["summary"]["visualInstances"] = len(instances)
    report["summary"]["variantFiles"] = len({
        (item.get("implementation") or {}).get("componentFile")
        for item in instances
        if isinstance(item.get("implementation"), dict)
        and (item.get("implementation") or {}).get("configurationMode") == "variant_component"
        and isinstance((item.get("implementation") or {}).get("componentFile"), str)
    })

    if stage in {"fairygui_assembly", "xml_generation"}:
        validate_fgui_spec(report, fgui_spec_path, components)
    if xml_dir is not None:
        validate_xml_reuse(report, xml_dir.resolve(), components, instances, index)

    report["ok"] = not report["errors"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate component reuse and parameterization planning.")
    parser.add_argument("--root", type=Path, required=True, help="UIProduction root directory")
    parser.add_argument("--stage", choices=sorted(STAGES), default="xml_generation")
    parser.add_argument("--xml-dir", type=Path, help="Optional package XML directory for structure validation")
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
