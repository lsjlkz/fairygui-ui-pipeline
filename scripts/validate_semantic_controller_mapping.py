#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate requirement-to-semantic-to-layout-to-FairyGUI controller mapping.

The validator checks that stateful objects discovered from requirements and an
approved design are represented consistently across:

- specs/ui_spec.md State Matrix
- specs/component_state_map.json
- specs/layout_spec.json
- specs/fgui_spec.md Controllers and Gear Mapping Table
- optional FairyGUI component XML
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_OWNERS = {"FGUI", "GameUI", "GamePlay", "Config", "Mixed", "None"}
FGUI_VISUAL_OWNERS = {"FGUI", "Mixed"}
OWNER_ALIASES = {
    "fgui": "FGUI",
    "fairygui": "FGUI",
    "fui": "FGUI",
    "gameui": "GameUI",
    "uilogic": "GameUI",
    "界面逻辑": "GameUI",
    "gameplay": "GamePlay",
    "gamelogic": "GamePlay",
    "游戏逻辑": "GamePlay",
    "config": "Config",
    "configuration": "Config",
    "配置": "Config",
    "mixed": "Mixed",
    "混合": "Mixed",
    "none": "None",
    "无": "None",
    "不适用": "None",
}
SUPPORTED_GEARS = {
    "gearDisplay", "gearXY", "gearSize", "gearLook", "gearColor",
    "gearAnimation", "gearText", "gearIcon", "gearDisplay2", "gearFontSize",
}
STAGES = {"semantic_analysis", "layout_analysis", "fairygui_assembly", "xml_generation"}
NONE_VALUES = {"", "none", "n/a", "na", "null", "无", "不需要", "runtime", "runtime_only"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def normalized(value: Any) -> str:
    """Normalize identifiers while preserving Unicode letters and digits."""
    return "".join(character.lower() for character in str(value) if character.isalnum())


def split_values(value: Any) -> list[str]:
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(split_values(item))
        return result
    if value is None:
        return []
    text = str(value).strip().strip("`")
    if normalized(text) in {normalized(item) for item in NONE_VALUES}:
        return []
    parts = re.split(r"[,;/|、，；\n]+", text)
    return [part.strip().strip("`") for part in parts if part.strip()]


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
    heading_pattern = re.compile(rf"^##+\s+{re.escape(heading)}\s*$", re.IGNORECASE)
    for index, line in enumerate(lines):
        if heading_pattern.match(line.strip()):
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
        if len(values) != len(headers):
            continue
        rows.append(dict(zip(headers, values)))
    return headers, rows


def list_of_objects(value: Any, *, key_field: str | None = None) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        result: list[dict[str, Any]] = []
        for key, item in value.items():
            if not isinstance(item, dict):
                continue
            copied = dict(item)
            if key_field and key_field not in copied:
                copied[key_field] = key
            result.append(copied)
        return result
    return []


def component_aliases(component: dict[str, Any]) -> set[str]:
    result = set()
    for field in ("componentType", "fguiComponent", "name"):
        value = component.get(field)
        if isinstance(value, str) and value:
            result.add(normalized(value))
    return result


def build_component_index(components: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, set[str]]]:
    index: dict[str, dict[str, Any]] = {}
    aliases_by_type: dict[str, set[str]] = {}
    for component in components:
        component_type = component.get("componentType")
        if not isinstance(component_type, str) or not component_type:
            continue
        key = normalized(component_type)
        aliases = component_aliases(component)
        aliases.add(key)
        aliases_by_type[key] = aliases
        for alias in aliases:
            index[alias] = component
    return index, aliases_by_type


def find_component(index: dict[str, dict[str, Any]], name: Any) -> dict[str, Any] | None:
    key = normalized(name)
    if not key:
        return None
    if key in index:
        return index[key]
    candidates = {id(component): component for alias, component in index.items() if alias in key or key in alias}
    return next(iter(candidates.values())) if len(candidates) == 1 else None


def normalize_owner(value: Any) -> str | None:
    key = normalized(value)
    if key in OWNER_ALIASES:
        return OWNER_ALIASES[key]
    for owner in ALLOWED_OWNERS:
        if key == normalized(owner):
            return owner
    return None


def owner_compatible(layout_owner: str | None, semantic_owner: str | None) -> bool:
    if layout_owner is None or semantic_owner is None:
        return False
    if semantic_owner == "Mixed" or layout_owner == "Mixed":
        return True
    return layout_owner == semantic_owner


def source_labels(value: Any) -> list[str]:
    labels: list[str] = []
    if not isinstance(value, list):
        return labels
    for item in value:
        if isinstance(item, str) and item.strip():
            labels.append(item.strip())
        elif isinstance(item, dict):
            for field in ("file", "path", "id", "title", "name"):
                field_value = item.get(field)
                if isinstance(field_value, str) and field_value.strip():
                    labels.append(field_value.strip())
                    break
    return labels


def source_is_mentioned(text: str, source: str) -> bool:
    normalized_text = text.replace("\\", "/").lower()
    normalized_source = source.replace("\\", "/").lower()
    candidates = {
        normalized_source,
        Path(normalized_source).name,
        Path(normalized_source).stem,
    }
    return any(candidate and candidate in normalized_text for candidate in candidates)


def validate_semantic_sources(
    report: dict[str, Any],
    project_root: Path,
    state_map_path: Path,
    semantic_spec_path: Path,
    state_map: dict[str, Any],
    semantic_text: str,
) -> None:
    fields = (
        ("requirementSources", "需求文档来源"),
        ("designDocumentSources", "UI/UX 设计文档来源"),
        ("designSources", "已确认设计图来源"),
    )
    for field, label in fields:
        sources = source_labels(state_map.get(field))
        if not sources:
            add(report, "errors", "semantic_source_missing", f"component_state_map.{field} 必须记录{label}", state_map_path)
            continue
        for source in sources:
            if not source_is_mentioned(semantic_text, source):
                add(report, "errors", "semantic_source_not_documented", f"uxui_semantic_spec.md 未明确引用 {field}: {source}", semantic_spec_path)
            path_like = "/" in source or "\\" in source or bool(Path(source).suffix)
            if path_like and "://" not in source:
                source_path = Path(source)
                resolved = source_path if source_path.is_absolute() else project_root / source_path
                if not resolved.is_file():
                    add(report, "errors", "semantic_source_file_missing", f"声明的 {field} 文件不存在: {source}", resolved)


def validate_ui_state_matrix(
    report: dict[str, Any],
    path: Path,
    component_index: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    text = read_text(path)
    headers, rows = parse_markdown_table(text, "State Matrix")
    required = {
        "component", "states", "trigger", "visual change", "controller",
        "business owner", "visual owner", "dynamic data owner", "requirement ids",
    }
    missing = sorted(required.difference(headers))
    if missing:
        add(report, "errors", "ui_state_matrix_columns_missing", f"ui_spec.md State Matrix 缺少列: {missing}", path)
        return []

    for row_index, row in enumerate(rows):
        component_name = row.get("component", "")
        component = find_component(component_index, component_name)
        if component is None:
            add(report, "errors", "requirement_component_unmapped", f"State Matrix 行 {row_index} 的组件未映射到 component_state_map: {component_name}", path)
            continue

        requirement_states = split_values(row.get("states"))
        semantic_states = split_values(component.get("states"))
        missing_states = [state for state in requirement_states if normalized(state) not in {normalized(item) for item in semantic_states}]
        if missing_states:
            add(report, "errors", "requirement_states_unmapped", f"组件 {component_name} 的需求状态未进入 component_state_map: {missing_states}", path)

        requirement_ids = split_values(row.get("requirement ids"))
        semantic_requirement_ids = split_values(component.get("requirementIds"))
        if not requirement_ids:
            add(report, "errors", "ui_requirement_ids_missing", f"组件 {component_name} 的 State Matrix 行缺少 Requirement IDs", path)
        elif not {normalized(item) for item in requirement_ids}.intersection({normalized(item) for item in semantic_requirement_ids}):
            add(report, "errors", "ui_requirement_ids_unmapped", f"组件 {component_name} 的 Requirement IDs 未进入 component_state_map: {requirement_ids}", path)

        requirement_controller = row.get("controller", "")
        semantic_controllers = split_values(component.get("controllers"))
        if normalized(requirement_controller) not in {normalized(item) for item in NONE_VALUES}:
            if normalized(requirement_controller) not in {normalized(item) for item in semantic_controllers}:
                add(report, "errors", "requirement_controller_unmapped", f"组件 {component_name} 的需求 Controller={requirement_controller} 未进入 component_state_map.controllers", path)

        business_owner = normalize_owner(row.get("business owner"))
        visual_owner = normalize_owner(row.get("visual owner"))
        dynamic_owner = normalize_owner(row.get("dynamic data owner"))
        if business_owner is None:
            add(report, "errors", "ui_business_owner_invalid", f"组件 {component_name} 缺少合法 Business Owner", path)
        if visual_owner is None:
            add(report, "errors", "ui_visual_owner_invalid", f"组件 {component_name} 缺少合法 Visual Owner", path)
        if dynamic_owner is None:
            add(report, "errors", "ui_dynamic_owner_invalid", f"组件 {component_name} 缺少合法 Dynamic Data Owner", path)
        semantic_business_owner = normalize_owner(component.get("businessStateOwner"))
        semantic_visual_owner = normalize_owner(component.get("visualStateOwner"))
        semantic_dynamic_owner = normalize_owner(component.get("dynamicDataOwner"))
        if business_owner is not None and not owner_compatible(business_owner, semantic_business_owner):
            add(report, "errors", "ui_business_owner_mismatch", f"组件 {component_name} 的 Business Owner={business_owner} 与语义归属 {semantic_business_owner} 不一致", path)
        if visual_owner is not None and not owner_compatible(visual_owner, semantic_visual_owner):
            add(report, "errors", "ui_visual_owner_mismatch", f"组件 {component_name} 的 Visual Owner={visual_owner} 与语义归属 {semantic_visual_owner} 不一致", path)
        if dynamic_owner is not None and not owner_compatible(dynamic_owner, semantic_dynamic_owner):
            add(report, "errors", "ui_dynamic_owner_mismatch", f"组件 {component_name} 的 Dynamic Data Owner={dynamic_owner} 与语义归属 {semantic_dynamic_owner} 不一致", path)
        if len(requirement_states) > 1 and visual_owner in FGUI_VISUAL_OWNERS and not semantic_controllers:
            add(report, "errors", "stateful_component_controller_missing", f"组件 {component_name} 有多个离散状态且视觉归属 {visual_owner}，但未声明 Controller", path)

    return rows


def validate_semantic_map(
    report: dict[str, Any],
    path: Path,
    state_map: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, set[str]]]:
    components = list_of_objects(state_map.get("components"), key_field="componentType")
    state_groups = list_of_objects(state_map.get("stateGroups"))
    if not components:
        add(report, "errors", "semantic_components_missing", "component_state_map.components 必须包含组件", path)

    component_index, aliases_by_type = build_component_index(components)
    group_keys: set[tuple[str, str, str]] = set()

    for index, component in enumerate(components):
        component_type = component.get("componentType")
        if not isinstance(component_type, str) or not component_type:
            add(report, "errors", "semantic_component_type_missing", f"components[{index}].componentType 缺失", path)
            continue
        fgui_component = component.get("fguiComponent")
        purpose = component.get("purpose")
        reusable = component.get("reusable")
        runtime_owner = normalize_owner(component.get("runtimeOwner"))
        business_owner = normalize_owner(component.get("businessStateOwner"))
        visual_owner = normalize_owner(component.get("visualStateOwner"))
        dynamic_owner = normalize_owner(component.get("dynamicDataOwner"))
        requirement_ids = split_values(component.get("requirementIds"))
        states = split_values(component.get("states"))
        controllers = split_values(component.get("controllers"))
        if not isinstance(fgui_component, str) or not fgui_component:
            add(report, "errors", "semantic_fgui_component_missing", f"组件 {component_type} 缺少 fguiComponent", path)
        if not isinstance(purpose, str) or not purpose:
            add(report, "errors", "semantic_purpose_missing", f"组件 {component_type} 缺少 purpose", path)
        if not states:
            add(report, "errors", "semantic_states_missing", f"组件 {component_type} 缺少 states", path)
        if not isinstance(reusable, bool):
            add(report, "errors", "semantic_reusable_invalid", f"组件 {component_type}.reusable 必须是布尔值", path)
        if runtime_owner is None:
            add(report, "errors", "semantic_runtime_owner_invalid", f"组件 {component_type} 缺少合法 runtimeOwner", path)
        if business_owner is None:
            add(report, "errors", "semantic_business_owner_invalid", f"组件 {component_type} 缺少合法 businessStateOwner", path)
        if visual_owner is None:
            add(report, "errors", "semantic_visual_owner_invalid", f"组件 {component_type} 缺少合法 visualStateOwner", path)
        if dynamic_owner is None:
            add(report, "errors", "semantic_dynamic_owner_invalid", f"组件 {component_type} 缺少合法 dynamicDataOwner", path)
        if not requirement_ids:
            add(report, "errors", "semantic_requirement_ids_missing", f"组件 {component_type} 缺少 requirementIds，无法追溯需求/设计文档", path)
        if len(states) > 1 and visual_owner in FGUI_VISUAL_OWNERS and not controllers:
            add(report, "errors", "semantic_controller_missing", f"组件 {component_type} 为多状态且视觉归属 {visual_owner}，必须声明 controllers", path)
        if len(controllers) > 1 and not state_groups:
            add(report, "warnings", "multiple_controllers_need_state_groups", f"组件 {component_type} 声明多个 Controller，应通过 stateGroups 明确状态归属", path)

    for index, group in enumerate(state_groups):
        component_type = group.get("componentType")
        component = find_component(component_index, component_type)
        if component is None:
            add(report, "errors", "state_group_component_unresolved", f"stateGroups[{index}].componentType 未解析: {component_type}", path)
            continue
        state_name = group.get("stateName")
        controller = group.get("fguiController")
        if not isinstance(group.get("trigger"), str) or not group.get("trigger"):
            add(report, "errors", "state_group_trigger_missing", f"stateGroups[{index}] 缺少 trigger", path)
        if not isinstance(group.get("visualDifference"), str) or not group.get("visualDifference"):
            add(report, "errors", "state_group_visual_difference_missing", f"stateGroups[{index}] 缺少 visualDifference", path)
        if not isinstance(group.get("runtimeData"), list):
            add(report, "errors", "state_group_runtime_data_invalid", f"stateGroups[{index}].runtimeData 必须是数组", path)
        if controller is None:
            add(report, "errors", "state_group_controller_field_missing", f"stateGroups[{index}] 缺少 fguiController；无 Controller 时必须显式写 none", path)
        if "gearType" not in group:
            add(report, "errors", "state_group_gear_field_missing", f"stateGroups[{index}] 缺少 gearType；无 Gear 时必须显式写空数组", path)
        semantic_states = split_values(component.get("states"))
        semantic_controllers = split_values(component.get("controllers"))
        if not isinstance(state_name, str) or normalized(state_name) not in {normalized(item) for item in semantic_states}:
            add(report, "errors", "state_group_state_invalid", f"stateGroups[{index}].stateName 不在组件 states 中: {state_name}", path)
        if controller and normalized(controller) not in {normalized(item) for item in semantic_controllers}:
            add(report, "errors", "state_group_controller_invalid", f"stateGroups[{index}].fguiController 未在组件 controllers 中声明: {controller}", path)
        requirement_ids = split_values(group.get("requirementIds"))
        if not requirement_ids:
            add(report, "errors", "state_group_requirement_ids_missing", f"stateGroups[{index}] 缺少 requirementIds", path)
        gears = split_values(group.get("gearType"))
        for gear in gears:
            if gear not in SUPPORTED_GEARS:
                add(report, "errors", "state_group_gear_invalid", f"stateGroups[{index}] 包含不支持的 Gear: {gear}", path)
        group_keys.add((normalized(component.get("componentType")), normalized(controller), normalized(state_name)))

    for component in components:
        states = split_values(component.get("states"))
        controllers = split_values(component.get("controllers"))
        visual_owner = normalize_owner(component.get("visualStateOwner")) or normalize_owner(component.get("runtimeOwner"))
        component_key = normalized(component.get("componentType"))
        if len(states) > 1 and visual_owner in FGUI_VISUAL_OWNERS:
            if len(controllers) == 1:
                controller_key = normalized(controllers[0])
                for state in states:
                    if (component_key, controller_key, normalized(state)) not in group_keys:
                        add(report, "errors", "semantic_state_group_missing", f"组件 {component.get('componentType')} 的状态 {state} 未在 stateGroups 中映射到 Controller {controllers[0]}", path)
            elif len(controllers) > 1:
                for state in states:
                    if not any(key[0] == component_key and key[2] == normalized(state) for key in group_keys):
                        add(report, "errors", "semantic_state_group_ambiguous", f"组件 {component.get('componentType')} 的状态 {state} 未明确归属哪个 Controller", path)

    return components, state_groups, component_index, aliases_by_type


def validate_layout(
    report: dict[str, Any],
    path: Path,
    layout: dict[str, Any],
    component_index: dict[str, dict[str, Any]],
) -> None:
    objects = list_of_objects(layout.get("objects"))
    slots = list_of_objects(layout.get("slots"))
    for collection_name, entries in (("objects", objects), ("slots", slots)):
        for index, entry in enumerate(entries):
            component_type = entry.get("componentType")
            if not component_type:
                if collection_name == "objects" and entry.get("nodeType") in {"image", "group", "graph"} and entry.get("slicePolicy") in {"slice_static", "use_manifest_asset"}:
                    continue
                add(report, "warnings", "layout_semantic_link_missing", f"{collection_name}[{index}] 缺少 componentType；若非纯装饰则必须关联语义组件", path)
                continue
            component = find_component(component_index, component_type)
            if component is None:
                add(report, "errors", "layout_component_unresolved", f"{collection_name}[{index}].componentType 未在 component_state_map 中定义: {component_type}", path)
                continue
            for required_field in ("semanticId", "instanceId", "runtimeRole", "requirementIds"):
                value = entry.get(required_field)
                if value is None or value == "" or (required_field == "requirementIds" and not split_values(value)):
                    add(report, "errors", "layout_semantic_field_missing", f"{collection_name}[{index}] 缺少 {required_field}", path)
            layout_requirement_ids = split_values(entry.get("requirementIds"))
            semantic_requirement_ids = split_values(component.get("requirementIds"))
            if layout_requirement_ids and not {normalized(item) for item in layout_requirement_ids}.intersection({normalized(item) for item in semantic_requirement_ids}):
                add(report, "errors", "layout_requirement_ids_mismatch", f"{collection_name}[{index}].requirementIds 无法追溯到语义组件 {component_type}", path)
            state_variant = entry.get("stateVariant")
            states = split_values(component.get("states"))
            if state_variant and normalized(state_variant) not in {normalized(item) for item in states}:
                add(report, "errors", "layout_state_variant_invalid", f"{collection_name}[{index}].stateVariant={state_variant} 不在 {component_type}.states 中", path)
            semantic_owner = normalize_owner(component.get("visualStateOwner")) or normalize_owner(component.get("runtimeOwner"))
            layout_owner = normalize_owner(entry.get("stateOwner"))
            if layout_owner is None:
                add(report, "errors", "layout_state_owner_missing", f"{collection_name}[{index}] 缺少合法 stateOwner", path)
            elif not owner_compatible(layout_owner, semantic_owner):
                add(report, "errors", "layout_state_owner_mismatch", f"{collection_name}[{index}].stateOwner={layout_owner} 与语义归属 {semantic_owner} 不一致", path)
            if len(states) > 1 and semantic_owner in FGUI_VISUAL_OWNERS:
                if collection_name == "objects" and entry.get("nodeType") == "image" and entry.get("slicePolicy") == "slice_static":
                    add(report, "errors", "stateful_component_flattened", f"{collection_name}[{index}] 把多状态组件 {component_type} 扁平化为静态图片", path)


def aliases_match(name: Any, component: dict[str, Any]) -> bool:
    key = normalized(name)
    return bool(key and any(key == alias or key in alias or alias in key for alias in component_aliases(component)))


def validate_fgui_spec(
    report: dict[str, Any],
    path: Path,
    text: str,
    components: list[dict[str, Any]],
    state_groups: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, str]]:
    controller_headers, controller_rows = parse_markdown_table(text, "Controllers")
    gear_headers, gear_rows = parse_markdown_table(text, "Gear Mapping Table")
    component_headers, component_rows = parse_markdown_table(text, "Components")

    required_controller_columns = {"component", "controller", "pages", "default", "used by", "requirement ids", "state owner"}
    missing_controller_columns = sorted(required_controller_columns.difference(controller_headers))
    if missing_controller_columns:
        add(report, "errors", "fgui_controller_columns_missing", f"fgui_spec Controllers 缺少列: {missing_controller_columns}", path)

    required_gear_columns = {"component", "controller", "page", "gear target", "gear type", "result", "requirement ids"}
    missing_gear_columns = sorted(required_gear_columns.difference(gear_headers))
    if missing_gear_columns:
        add(report, "errors", "fgui_gear_columns_missing", f"fgui_spec Gear Mapping Table 缺少列: {missing_gear_columns}", path)

    files_by_component: dict[str, str] = {}
    for row in component_rows:
        component_name = row.get("component", "")
        file_name = row.get("file", "")
        if component_name and file_name:
            files_by_component[normalized(component_name)] = file_name.strip().strip("`")

    controller_index: dict[tuple[str, str], dict[str, str]] = {}
    for index, row in enumerate(controller_rows):
        component_name = row.get("component", "")
        controller_name = row.get("controller", "")
        key = (normalized(component_name), normalized(controller_name))
        if not all(key):
            continue
        if key in controller_index:
            add(report, "errors", "fgui_controller_duplicate", f"Controllers 表重复定义 {component_name}.{controller_name}", path)
        controller_index[key] = row
        pages = split_values(row.get("pages"))
        default = row.get("default", "").strip().strip("`")
        if not split_values(row.get("requirement ids")):
            add(report, "errors", "fgui_controller_requirement_ids_missing", f"Controllers 行 {index} 缺少 Requirement IDs", path)
        if normalize_owner(row.get("state owner")) is None:
            add(report, "errors", "fgui_controller_state_owner_invalid", f"Controllers 行 {index} 缺少合法 State Owner", path)
        if default and normalized(default) not in {normalized(page) for page in pages}:
            add(report, "errors", "fgui_controller_default_invalid", f"Controllers 行 {index} 的 Default={default} 不在 Pages 中", path)

    def find_controller_row(component: dict[str, Any], controller: str) -> dict[str, str] | None:
        for row in controller_rows:
            if aliases_match(row.get("component"), component) and normalized(row.get("controller")) == normalized(controller):
                return row
        return None

    for component in components:
        states = split_values(component.get("states"))
        controllers = split_values(component.get("controllers"))
        visual_owner = normalize_owner(component.get("visualStateOwner")) or normalize_owner(component.get("runtimeOwner"))
        if len(states) <= 1 or visual_owner not in FGUI_VISUAL_OWNERS:
            continue
        for controller in controllers:
            row = find_controller_row(component, controller)
            if row is None:
                add(report, "errors", "fgui_controller_missing", f"语义组件 {component.get('componentType')} 的 Controller {controller} 未写入 fgui_spec Controllers", path)
                continue
            semantic_requirement_ids = {normalized(item) for item in split_values(component.get("requirementIds"))}
            row_requirement_ids = {normalized(item) for item in split_values(row.get("requirement ids"))}
            if semantic_requirement_ids and not semantic_requirement_ids.intersection(row_requirement_ids):
                add(report, "errors", "fgui_controller_requirement_ids_mismatch", f"组件 {component.get('componentType')} Controller {controller} 的 Requirement IDs 与语义组件不一致", path)
            semantic_owner = normalize_owner(component.get("visualStateOwner"))
            row_owner = normalize_owner(row.get("state owner"))
            if not owner_compatible(row_owner, semantic_owner):
                add(report, "errors", "fgui_controller_state_owner_mismatch", f"组件 {component.get('componentType')} Controller {controller} 的 State Owner={row_owner} 与语义归属 {semantic_owner} 不一致", path)
            expected_pages = {
                normalized(group.get("stateName"))
                for group in state_groups
                if aliases_match(group.get("componentType"), component)
                and normalized(group.get("fguiController")) == normalized(controller)
            }
            if not expected_pages and len(controllers) == 1:
                expected_pages = {normalized(state) for state in states}
            actual_pages = {normalized(page) for page in split_values(row.get("pages"))}
            missing_pages = sorted(page for page in expected_pages if page and page not in actual_pages)
            if missing_pages:
                add(report, "errors", "fgui_controller_pages_missing", f"组件 {component.get('componentType')} Controller {controller} 缺少语义状态页: {missing_pages}", path)

    for index, row in enumerate(gear_rows):
        gear_type = row.get("gear type", "").strip().strip("`")
        if not split_values(row.get("requirement ids")):
            add(report, "errors", "fgui_gear_requirement_ids_missing", f"Gear Mapping 行 {index} 缺少 Requirement IDs", path)
        if gear_type and gear_type not in SUPPORTED_GEARS:
            add(report, "errors", "fgui_gear_type_invalid", f"Gear Mapping 行 {index} 使用不支持的 Gear: {gear_type}", path)
        component_name = row.get("component", "")
        controller_name = row.get("controller", "")
        page = row.get("page", "")
        matching_controller = next(
            (
                controller_row for controller_row in controller_rows
                if normalized(controller_row.get("component")) == normalized(component_name)
                and normalized(controller_row.get("controller")) == normalized(controller_name)
            ),
            None,
        )
        if matching_controller is None:
            add(report, "errors", "fgui_gear_controller_unresolved", f"Gear Mapping 行 {index} 引用了不存在的 Controller: {component_name}.{controller_name}", path)
        elif normalized(page) not in {normalized(item) for item in split_values(matching_controller.get("pages"))}:
            add(report, "errors", "fgui_gear_page_unresolved", f"Gear Mapping 行 {index} 的 Page={page} 不属于 Controller {controller_name}", path)

    for group_index, group in enumerate(state_groups):
        gears = split_values(group.get("gearType"))
        if not gears:
            continue
        component = next((item for item in components if aliases_match(group.get("componentType"), item)), None)
        if component is None:
            continue
        controller = group.get("fguiController")
        page = group.get("stateName")
        for gear in gears:
            group_requirement_ids = {normalized(item) for item in split_values(group.get("requirementIds"))}
            matching_rows = [
                row for row in gear_rows
                if aliases_match(row.get("component"), component)
                and normalized(row.get("controller")) == normalized(controller)
                and normalized(row.get("page")) == normalized(page)
                and row.get("gear type", "").strip().strip("`") == gear
            ]
            matched = bool(matching_rows)
            if matched and group_requirement_ids and not any(
                group_requirement_ids.intersection({normalized(item) for item in split_values(row.get("requirement ids"))})
                for row in matching_rows
            ):
                add(report, "errors", "fgui_gear_requirement_ids_mismatch", f"stateGroups[{group_index}] 的 {gear} Requirement IDs 与 Gear Mapping 不一致", path)
            if not matched:
                add(report, "errors", "fgui_gear_mapping_missing", f"stateGroups[{group_index}] 的 {component.get('componentType')}.{controller}.{page}.{gear} 未写入 Gear Mapping Table", path)

    return controller_rows, gear_rows, files_by_component


def find_component_file(files_by_component: dict[str, str], component: dict[str, Any]) -> str | None:
    aliases = component_aliases(component)
    for key, file_name in files_by_component.items():
        if any(key == alias or key in alias or alias in key for alias in aliases):
            return file_name
    return None


def xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def validate_xml(
    report: dict[str, Any],
    xml_dir: Path,
    components: list[dict[str, Any]],
    state_groups: list[dict[str, Any]],
    controller_rows: list[dict[str, str]],
    gear_rows: list[dict[str, str]],
    files_by_component: dict[str, str],
) -> None:
    if not xml_dir.is_dir():
        add(report, "errors", "xml_dir_missing", "指定的 XML 目录不存在", xml_dir)
        return

    for component in components:
        controllers = split_values(component.get("controllers"))
        if not controllers:
            continue
        file_name = find_component_file(files_by_component, component)
        if not file_name:
            add(report, "errors", "xml_component_file_unmapped", f"无法从 fgui_spec Components 表确定 {component.get('componentType')} 的 XML 文件", xml_dir)
            continue
        xml_path = xml_dir / file_name
        if not xml_path.is_file():
            matches = list(xml_dir.rglob(Path(file_name).name))
            xml_path = matches[0] if len(matches) == 1 else xml_path
        if not xml_path.is_file():
            add(report, "errors", "xml_component_file_missing", f"组件 XML 不存在: {file_name}", xml_path)
            continue
        try:
            root = ET.fromstring(read_text(xml_path))
        except (OSError, ET.ParseError) as exc:
            add(report, "errors", "xml_component_invalid", f"组件 XML 无法解析: {exc}", xml_path)
            continue

        xml_controllers = {
            normalized(elem.attrib.get("name")): elem
            for elem in root.iter()
            if xml_local_name(elem.tag) == "controller" and elem.attrib.get("name")
        }
        for controller in controllers:
            elem = xml_controllers.get(normalized(controller))
            if elem is None:
                add(report, "errors", "xml_controller_missing", f"组件 {component.get('componentType')} XML 缺少 Controller {controller}", xml_path)
                continue
            expected_pages = {
                normalized(group.get("stateName"))
                for group in state_groups
                if aliases_match(group.get("componentType"), component)
                and normalized(group.get("fguiController")) == normalized(controller)
            }
            page_tokens = {normalized(item) for item in split_values(elem.attrib.get("pages"))}
            if expected_pages and page_tokens:
                missing = sorted(page for page in expected_pages if page not in page_tokens)
                if missing:
                    add(report, "errors", "xml_controller_pages_missing", f"Controller {controller} XML pages 缺少: {missing}", xml_path)

        named_elements = {
            normalized(elem.attrib.get("name")): elem
            for elem in root.iter()
            if elem.attrib.get("name")
        }
        for row in gear_rows:
            if not aliases_match(row.get("component"), component):
                continue
            target_name = row.get("gear target", "").strip().strip("`")
            gear_type = row.get("gear type", "").strip().strip("`")
            if not target_name or normalized(target_name) in {normalized(item) for item in NONE_VALUES}:
                continue
            target = named_elements.get(normalized(target_name))
            if target is None:
                add(report, "errors", "xml_gear_target_missing", f"Gear 目标对象不存在: {target_name}", xml_path)
                continue
            matching_gears = [child for child in target if xml_local_name(child.tag) == gear_type]
            if not matching_gears:
                add(report, "errors", "xml_gear_missing", f"对象 {target_name} 缺少计划中的 {gear_type}", xml_path)


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = ["# Semantic Controller Mapping Report", "", f"- result: {'PASS' if report['ok'] else 'BLOCKED'}", f"- stage: {report['stage']}", ""]
    lines.extend(["## Errors", ""])
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
    specs = root / "specs"
    ui_spec_path = specs / "ui_spec.md"
    semantic_spec_path = specs / "uxui_semantic_spec.md"
    state_map_path = specs / "component_state_map.json"
    layout_path = specs / "layout_spec.json"
    fgui_spec_path = specs / "fgui_spec.md"

    report: dict[str, Any] = {
        "ok": False,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "stage": stage,
        "xmlDir": str(xml_dir.resolve()) if xml_dir else None,
        "errors": [],
        "warnings": [],
        "summary": {"components": 0, "stateGroups": 0, "controllers": 0, "gearMappings": 0},
    }

    if not require_file(report, ui_spec_path, "ui_spec_missing", "ui_spec.md"):
        return report
    if not require_file(report, semantic_spec_path, "semantic_spec_missing", "uxui_semantic_spec.md"):
        return report
    if not require_file(report, state_map_path, "component_state_map_missing", "component_state_map.json"):
        return report

    try:
        state_map = load_json(state_map_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        add(report, "errors", "component_state_map_invalid", f"component_state_map.json 无法解析: {exc}", state_map_path)
        return report

    semantic_text = read_text(semantic_spec_path)
    validate_semantic_sources(report, root, state_map_path, semantic_spec_path, state_map, semantic_text)
    components, state_groups, component_index, _ = validate_semantic_map(report, state_map_path, state_map)
    report["summary"]["components"] = len(components)
    report["summary"]["stateGroups"] = len(state_groups)
    validate_ui_state_matrix(report, ui_spec_path, component_index)

    if stage in {"layout_analysis", "fairygui_assembly", "xml_generation"}:
        if require_file(report, layout_path, "layout_spec_missing", "layout_spec.json"):
            try:
                layout = load_json(layout_path)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                add(report, "errors", "layout_spec_invalid", f"layout_spec.json 无法解析: {exc}", layout_path)
            else:
                validate_layout(report, layout_path, layout, component_index)

    controller_rows: list[dict[str, str]] = []
    gear_rows: list[dict[str, str]] = []
    files_by_component: dict[str, str] = {}
    if stage in {"fairygui_assembly", "xml_generation"}:
        if require_file(report, fgui_spec_path, "fgui_spec_missing", "fgui_spec.md"):
            fgui_text = read_text(fgui_spec_path)
            controller_rows, gear_rows, files_by_component = validate_fgui_spec(
                report, fgui_spec_path, fgui_text, components, state_groups
            )
            report["summary"]["controllers"] = len(controller_rows)
            report["summary"]["gearMappings"] = len(gear_rows)

    if xml_dir is not None:
        if stage != "xml_generation":
            add(report, "warnings", "xml_check_outside_xml_stage", "提供了 --xml-dir，但当前 stage 不是 xml_generation", xml_dir)
        validate_xml(report, xml_dir.resolve(), components, state_groups, controller_rows, gear_rows, files_by_component)

    report["ok"] = not report["errors"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate semantic Controller/Gear mapping across FairyGUI pipeline files.")
    parser.add_argument("--root", type=Path, required=True, help="UIProduction root directory")
    parser.add_argument("--stage", choices=sorted(STAGES), default="xml_generation")
    parser.add_argument("--xml-dir", type=Path, help="Optional component XML directory for implementation cross-check")
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
