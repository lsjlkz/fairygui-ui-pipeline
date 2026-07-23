#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate FairyGUI display-list back-to-front ordering.

The validator checks fgui_spec.md Display List planning, optional layout z-order
fields, and optional generated XML direct-child order.
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

STAGES = {"fairygui_assembly", "xml_generation"}
Z_LAYERS = {
    "background": 0,
    "content": 1,
    "foreground": 2,
    "overlay": 3,
    "modal": 4,
    "debug": 5,
}
OCCLUSION_POLICIES = {
    "opaque_background",
    "normal",
    "transparent_frame",
    "intentional_overlay",
    "modal_blocker",
    "non_visual",
}
NONE_VALUES = {"", "none", "n/a", "na", "null", "无", "—", "-"}
BACKGROUND_NAME_RE = re.compile(r"(?:^|[_\-])(bg|background|backdrop)(?:$|[_\-])", re.IGNORECASE)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def normalized(value: Any) -> str:
    return "".join(character.lower() for character in str(value) if character.isalnum())


def normalize_file(value: Any) -> str:
    return str(PurePosixPath(str(value).replace("\\", "/"))).lower().lstrip("./")


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


def numeric_order(value: Any) -> int | None:
    text = str(value).strip().strip("`")
    try:
        return int(text)
    except ValueError:
        return None


def visible_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        order = numeric_order(row.get("order"))
        if order is None:
            continue
        copied: dict[str, Any] = dict(row)
        copied["_order"] = order
        result.append(copied)
    return result


def validate_spec_rows(
    report: dict[str, Any],
    path: Path,
    rows: list[dict[str, str]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(visible_rows(rows)):
        parent = row.get("parent", "").strip().strip("`")
        name = row.get("name", "").strip().strip("`")
        layer = row.get("z layer", "").strip().strip("`").lower()
        policy = row.get("occlusion policy", "").strip().strip("`").lower()
        if not parent:
            add(report, "errors", "display_list_parent_missing", f"Display List 数字顺序行 {index} 缺少 Parent", path)
            continue
        if not name:
            add(report, "errors", "display_list_name_missing", f"Display List 数字顺序行 {index} 缺少 Name", path)
        if layer not in Z_LAYERS:
            add(report, "errors", "display_list_z_layer_invalid", f"{parent}.{name} 的 Z Layer 非法: {layer}", path)
        if policy not in OCCLUSION_POLICIES:
            add(report, "errors", "display_list_occlusion_policy_invalid", f"{parent}.{name} 的 Occlusion Policy 非法: {policy}", path)
        row["_layer"] = layer
        row["_policy"] = policy
        grouped.setdefault(normalized(parent), []).append(row)

    for parent_key, parent_rows in grouped.items():
        parent_rows.sort(key=lambda item: item["_order"])
        seen_orders: set[int] = set()
        previous_rank = -1
        for row in parent_rows:
            order = row["_order"]
            name = row.get("name", "")
            layer = row.get("_layer", "")
            policy = row.get("_policy", "")
            if order in seen_orders:
                add(report, "errors", "display_list_order_duplicate", f"Parent={parent_key} 存在重复 Order={order}", path)
            seen_orders.add(order)
            if layer in Z_LAYERS:
                rank = Z_LAYERS[layer]
                if rank < previous_rank:
                    add(report, "errors", "display_list_z_layer_order_invalid", f"Parent={parent_key} 的 {name} 在 XML 后部却回退到更低 Z Layer={layer}", path)
                previous_rank = max(previous_rank, rank)
            background_evidence = " ".join(
                str(row.get(field, ""))
                for field in ("name", "asset name", "resource")
            )
            background_like = bool(BACKGROUND_NAME_RE.search(background_evidence))
            if policy == "opaque_background":
                if layer != "background":
                    add(report, "errors", "opaque_background_layer_invalid", f"{parent_key}.{name} 必须使用 Z Layer=background", path)
                if row is not parent_rows[0]:
                    add(report, "errors", "opaque_background_not_backmost", f"{parent_key}.{name} 是不透明背景，必须是该 Parent 最早的 XML 子节点", path)
            if background_like:
                if layer != "background":
                    add(report, "errors", "background_like_layer_invalid", f"{parent_key}.{name} 名称/资源表明它是背景，必须使用 Z Layer=background", path)
                if policy != "opaque_background":
                    add(report, "errors", "background_like_policy_invalid", f"{parent_key}.{name} 名称/资源表明它是背景，必须显式声明 Occlusion Policy=opaque_background", path)
                if row is not parent_rows[0]:
                    add(report, "errors", "background_like_node_not_backmost", f"{parent_key}.{name} 名称/资源表明它是背景，必须位于该 Parent 最前部", path)
            if policy == "transparent_frame" and layer not in {"foreground", "overlay"}:
                add(report, "errors", "transparent_frame_layer_invalid", f"{parent_key}.{name} 必须位于 foreground 或 overlay", path)
            if policy == "modal_blocker" and layer != "modal":
                add(report, "errors", "modal_blocker_layer_invalid", f"{parent_key}.{name} 必须使用 Z Layer=modal", path)

    return grouped


def validate_layout_alignment(
    report: dict[str, Any],
    path: Path,
    layout: dict[str, Any],
    spec_rows: list[dict[str, str]],
) -> None:
    spec_index = {
        normalized(row.get("name")): row
        for row in visible_rows(spec_rows)
        if row.get("name")
    }
    for collection_name in ("objects", "slots"):
        entries = layout.get(collection_name, [])
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            name = entry.get("name") or entry.get("componentName") or entry.get("slotId")
            if not isinstance(name, str) or not name:
                continue
            z_layer = entry.get("zLayer")
            policy = entry.get("occlusionPolicy")
            if not isinstance(z_layer, str) or z_layer not in Z_LAYERS:
                add(report, "errors", "layout_z_layer_missing", f"{collection_name}[{index}] {name} 缺少合法 zLayer", path)
            if not isinstance(policy, str) or policy not in OCCLUSION_POLICIES:
                add(report, "errors", "layout_occlusion_policy_missing", f"{collection_name}[{index}] {name} 缺少合法 occlusionPolicy", path)
            spec_row = spec_index.get(normalized(name))
            if spec_row is None:
                continue
            if isinstance(z_layer, str) and normalized(spec_row.get("z layer")) != normalized(z_layer):
                add(report, "errors", "layout_z_layer_mismatch", f"{name} 的 layout.zLayer 与 fgui_spec Z Layer 不一致", path)
            if isinstance(policy, str) and normalized(spec_row.get("occlusion policy")) != normalized(policy):
                add(report, "errors", "layout_occlusion_policy_mismatch", f"{name} 的 layout.occlusionPolicy 与 fgui_spec 不一致", path)


def resolve_component_file(xml_dir: Path, file_name: str) -> Path | None:
    direct = xml_dir / Path(file_name.replace("\\", "/"))
    if direct.is_file():
        return direct
    matches = [path for path in xml_dir.rglob(Path(file_name.replace("\\", "/")).name) if path.is_file()]
    return matches[0] if len(matches) == 1 else None


def direct_display_names(root: ET.Element) -> list[str]:
    display = next((child for child in list(root) if child.tag.rsplit("}", 1)[-1] == "displayList"), None)
    if display is None:
        return []
    return [child.attrib.get("name", "") for child in list(display) if child.attrib.get("name")]


def parent_file_map(component_rows: list[dict[str, str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in component_rows:
        component = row.get("component", "").strip().strip("`")
        file_name = row.get("file", "").strip().strip("`")
        if component and file_name:
            result[normalized(component)] = file_name
            result[normalized(Path(file_name).stem)] = file_name
    return result


def find_parent_file(mapping: dict[str, str], parent: str) -> str | None:
    key = normalized(parent)
    if key in mapping:
        return mapping[key]
    candidates = {value for alias, value in mapping.items() if key and (key in alias or alias in key)}
    return next(iter(candidates)) if len(candidates) == 1 else None


def validate_xml_order(
    report: dict[str, Any],
    xml_dir: Path,
    grouped_rows: dict[str, list[dict[str, Any]]],
    component_rows: list[dict[str, str]],
) -> None:
    mapping = parent_file_map(component_rows)
    for parent_key, rows in grouped_rows.items():
        parent_label = rows[0].get("parent", parent_key) if rows else parent_key
        file_name = find_parent_file(mapping, str(parent_label))
        if not file_name:
            add(report, "errors", "xml_display_list_parent_unresolved", f"无法从 Components 表解析 Parent={parent_label} 的 XML 文件", xml_dir)
            continue
        xml_path = resolve_component_file(xml_dir, file_name)
        if xml_path is None:
            add(report, "errors", "xml_display_list_file_missing", f"Parent={parent_label} 的 XML 文件不存在或同名不唯一: {file_name}", xml_dir)
            continue
        try:
            root = ET.fromstring(read_text(xml_path))
        except (OSError, ET.ParseError) as exc:
            add(report, "errors", "xml_display_list_file_invalid", f"无法解析 {file_name}: {exc}", xml_path)
            continue
        actual_names = direct_display_names(root)
        actual_index = {normalized(name): index for index, name in enumerate(actual_names)}
        expected_names = [str(row.get("name", "")) for row in sorted(rows, key=lambda item: item["_order"])]
        last_index = -1
        for expected_name in expected_names:
            index = actual_index.get(normalized(expected_name))
            if index is None:
                add(report, "errors", "xml_display_list_node_missing", f"{file_name} 缺少计划中的直接子节点: {expected_name}", xml_path)
                continue
            if index < last_index:
                add(report, "errors", "xml_display_list_order_mismatch", f"{file_name} 的节点 {expected_name} 顺序与 fgui_spec 不一致", xml_path)
            last_index = max(last_index, index)

        opaque_rows = [row for row in rows if row.get("_policy") == "opaque_background"]
        for row in opaque_rows:
            background_index = actual_index.get(normalized(row.get("name")))
            if background_index is not None and background_index != min(actual_index.values(), default=background_index):
                add(report, "errors", "xml_opaque_background_not_backmost", f"{file_name} 的不透明背景 {row.get('name')} 必须位于 displayList 最前部", xml_path)


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Display List Z-Order Report",
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
    fgui_spec_path = root / "specs" / "fgui_spec.md"
    layout_path = root / "specs" / "layout_spec.json"
    report: dict[str, Any] = {
        "ok": False,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "stage": stage,
        "xmlDir": str(xml_dir.resolve()) if xml_dir else None,
        "errors": [],
        "warnings": [],
        "summary": {"parents": 0, "plannedNodes": 0, "xmlChecked": xml_dir is not None},
    }

    if not require_file(report, fgui_spec_path, "display_list_fgui_spec_missing", "fgui_spec.md"):
        return report
    text = read_text(fgui_spec_path)
    headers, rows = parse_markdown_table(text, "Display List")
    required = {
        "parent", "order", "name", "node type", "asset name", "resource", "position",
        "size", "size source", "z layer", "occlusion policy", "binding",
    }
    missing = sorted(required.difference(headers))
    if missing:
        add(report, "errors", "display_list_columns_missing", f"fgui_spec Display List 缺少列: {missing}", fgui_spec_path)
        return report

    grouped = validate_spec_rows(report, fgui_spec_path, rows)
    report["summary"]["parents"] = len(grouped)
    report["summary"]["plannedNodes"] = sum(len(items) for items in grouped.values())

    if layout_path.is_file():
        try:
            layout = load_json(layout_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            add(report, "errors", "display_list_layout_invalid", f"layout_spec.json 无法解析: {exc}", layout_path)
        else:
            validate_layout_alignment(report, layout_path, layout, rows)

    component_headers, component_rows = parse_markdown_table(text, "Components")
    if xml_dir is not None:
        if not {"component", "file"}.issubset(set(component_headers)):
            add(report, "errors", "display_list_components_columns_missing", "fgui_spec Components 必须包含 Component 和 File 列", fgui_spec_path)
        else:
            validate_xml_order(report, xml_dir.resolve(), grouped, component_rows)

    report["ok"] = not report["errors"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate FairyGUI display-list z-order.")
    parser.add_argument("--root", type=Path, required=True, help="UIProduction root directory")
    parser.add_argument("--stage", choices=sorted(STAGES), default="xml_generation")
    parser.add_argument("--xml-dir", type=Path, help="Optional package XML directory")
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
