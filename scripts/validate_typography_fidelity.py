#!/usr/bin/env python3
"""Validate deterministic typography from production preview to FairyGUI XML."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

STAGE_ORDER = {
    "asset_planning": 10,
    "fairygui_assembly": 40,
    "xml_generation": 50,
    "validation": 60,
}
FIDELITY_MODES = {"exact", "approximate_reference"}
PRODUCTION_TEXT_MODES = {"deterministic_text_overlay", "fairygui_capture"}
CORE_ATTRIBUTES = {"font", "fontSize", "color", "align", "vAlign", "autoSize", "singleLine"}
SUPPORTED_ATTRIBUTES = {
    "font", "fontSize", "color", "align", "vAlign", "leading", "letterSpacing",
    "autoSize", "singleLine", "bold", "italic", "underline", "strikethrough",
    "strokeColor", "strokeSize", "shadowColor", "shadowOffset",
}
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
EXTENSION_STYLE_ATTRIBUTES = {
    "fontSize": "titleFontSize",
    "color": "titleColor",
}


@dataclass
class Issue:
    code: str
    message: str
    path: str | None = None
    target: str | None = None
    severity: str = "error"


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {path}: {exc}") from exc
    return value if isinstance(value, dict) else {}


def normalize_relative(value: str) -> Path:
    normalized = str(PurePosixPath(value.replace("\\", "/"))).lstrip("./")
    return Path(*PurePosixPath(normalized).parts)


def resolve(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    return path if path.is_absolute() else root / normalize_relative(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_pair(value: str | None) -> list[int] | None:
    if not value:
        return None
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        return None
    try:
        return [int(float(parts[0])), int(float(parts[1]))]
    except ValueError:
        return None


def instance_key(value: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(value.get("componentFile") or ""),
        str(value.get("xmlNodeName") or ""),
        str(value.get("hostComponentFile") or ""),
        str(value.get("hostInstanceName") or ""),
    )


def instance_target(value: dict[str, Any]) -> str:
    component_file, node_name, host_file, host_instance = instance_key(value)
    base = f"{component_file}:{node_name}"
    return f"{host_file}:{host_instance}->{base}" if host_file or host_instance else base


def find_named_node(root_element: ET.Element, name: str, tags: set[str]) -> list[ET.Element]:
    return [
        element for element in root_element.iter()
        if element.attrib.get("name") == name and element.tag in tags
    ]


def relation_resizes_text(node: ET.Element) -> tuple[bool, bool]:
    resize_width = False
    resize_height = False
    for child in node:
        if child.tag != "relation" or child.attrib.get("target", "") != "":
            continue
        side_pair = child.attrib.get("sidePair", "")
        resize_width = resize_width or "width-width" in side_pair
        resize_height = resize_height or "height-height" in side_pair
    return resize_width, resize_height


def effective_host_bbox(
    base_root: ET.Element,
    text_node: ET.Element,
    host_node: ET.Element,
) -> list[int] | None:
    base_size = parse_pair(base_root.attrib.get("size"))
    node_xy = parse_pair(text_node.attrib.get("xy"))
    node_size = parse_pair(text_node.attrib.get("size"))
    host_xy = parse_pair(host_node.attrib.get("xy"))
    host_size = parse_pair(host_node.attrib.get("size"))
    if None in (base_size, node_xy, node_size, host_xy, host_size):
        return None
    assert base_size and node_xy and node_size and host_xy and host_size
    resize_width, resize_height = relation_resizes_text(text_node)
    width = node_size[0] + (host_size[0] - base_size[0] if resize_width else 0)
    height = node_size[1] + (host_size[1] - base_size[1] if resize_height else 0)
    if width <= 0 or height <= 0:
        return None
    return [host_xy[0] + node_xy[0], host_xy[1] + node_xy[1], width, height]


def build_report(root: Path, stage: str, checked: list[dict[str, Any]], issues: list[Issue], applicable: bool = True) -> dict[str, Any]:
    values = [asdict(item) for item in issues]
    errors = [item for item in values if item["severity"] == "error"]
    warnings = [item for item in values if item["severity"] == "warning"]
    return {
        "validator": "typography_fidelity",
        "root": str(root),
        "stage": stage,
        "applicable": applicable,
        "typography_fidelity_checked": applicable,
        "ok": not errors,
        "status": "PASS" if not errors else "FAIL",
        "checkedTextInstances": checked,
        "errors": errors,
        "warnings": warnings,
        "issues": values,
        "summary": {
            "instancesChecked": len(checked),
            "errors": len(errors),
            "warnings": len(warnings),
        },
    }


def validate(root: Path, stage: str = "asset_planning", xml_dir: Path | None = None) -> dict[str, Any]:
    issues: list[Issue] = []
    checked: list[dict[str, Any]] = []
    manifest_path = root / "manifests" / "asset_manifest.json"
    try:
        manifest = read_json(manifest_path)
    except ValueError as exc:
        issues.append(Issue("asset_manifest_invalid", str(exc), str(manifest_path)))
        return build_report(root, stage, checked, issues)
    if not manifest:
        issues.append(Issue("asset_manifest_missing", "asset_manifest.json is required.", str(manifest_path)))
        return build_report(root, stage, checked, issues)

    production = manifest.get("production") if isinstance(manifest.get("production"), dict) else {}
    full_screen = production.get("generateFullScreenDesign") is True
    gate = production.get("requiresTypographyFidelity") is True
    if full_screen and not gate:
        issues.append(Issue(
            "typography_fidelity_not_required",
            "Full-screen projects must set production.requiresTypographyFidelity=true.",
            str(manifest_path),
        ))
    if not full_screen and not gate:
        report = build_report(root, stage, checked, issues, applicable=False)
        report["status"] = "SKIPPED"
        report["typography_fidelity_checked"] = False
        return report

    spec_path = root / "specs" / "typography_spec.json"
    try:
        spec = read_json(spec_path)
    except ValueError as exc:
        issues.append(Issue("typography_spec_invalid", str(exc), str(spec_path)))
        return build_report(root, stage, checked, issues)
    if not spec:
        issues.append(Issue("typography_spec_missing", "specs/typography_spec.json is required.", str(spec_path)))
        return build_report(root, stage, checked, issues)
    if spec.get("blockingForXml") is True:
        issues.append(Issue("typography_spec_blocks_xml", "Typography spec sets blockingForXml=true.", str(spec_path)))

    fidelity_mode = str(spec.get("fidelityMode") or "")
    if fidelity_mode not in FIDELITY_MODES:
        issues.append(Issue("typography_fidelity_mode_invalid", f"Unsupported fidelityMode: {fidelity_mode!r}.", str(spec_path)))
    if fidelity_mode == "approximate_reference" and STAGE_ORDER.get(stage, 50) >= STAGE_ORDER["fairygui_assembly"]:
        issues.append(Issue(
            "approximate_typography_cannot_be_final_preview",
            "Final production preview and XML require deterministic exact typography.",
            str(spec_path),
        ))

    contains_text = spec.get("containsText") is not False
    assembly_checks = STAGE_ORDER.get(stage, 50) >= STAGE_ORDER["fairygui_assembly"]
    if not contains_text:
        if spec.get("reviewStatus") != "approved" and assembly_checks:
            issues.append(Issue("typography_review_not_approved", "No-text declaration must be human-approved before assembly.", str(spec_path)))
        review = spec.get("review") if isinstance(spec.get("review"), dict) else {}
        if assembly_checks and (review.get("recordedBy") not in {"user", "human_reviewer"} or review.get("type") not in {"user_confirmation", "manual_review"}):
            issues.append(Issue("typography_ai_self_approval_forbidden", "No-text declaration approval must be human-originated.", str(spec_path)))
        return build_report(root, stage, checked, issues)

    preview = spec.get("productionPreview") if isinstance(spec.get("productionPreview"), dict) else {}
    text_mode = str(preview.get("textRenderingMode") or "")
    renderer_path = resolve(root, preview.get("rendererScript"))
    render_trace_path = resolve(root, preview.get("renderTrace"))
    render_trace: dict[str, Any] = {}
    trace_entries_by_target: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    if fidelity_mode == "exact" and text_mode not in PRODUCTION_TEXT_MODES:
        issues.append(Issue(
            "production_preview_text_mode_invalid",
            f"Exact typography requires textRenderingMode in {sorted(PRODUCTION_TEXT_MODES)}.",
            str(spec_path),
        ))
    if not isinstance(preview.get("rendererScript"), str) or not preview.get("rendererScript"):
        issues.append(Issue("typography_preview_renderer_missing", "productionPreview.rendererScript is required.", str(spec_path)))
    if preview.get("usesTypographySpec") is not True:
        issues.append(Issue(
            "preview_renderer_does_not_declare_typography_spec",
            "productionPreview.usesTypographySpec must be true.",
            str(spec_path),
        ))
    if assembly_checks:
        if renderer_path is None or not renderer_path.is_file():
            issues.append(Issue("typography_preview_renderer_file_missing", "Typography preview renderer does not exist.", str(renderer_path)))
        else:
            renderer_text = renderer_path.read_text(encoding="utf-8", errors="ignore")
            if "typography_spec.json" not in renderer_text:
                issues.append(Issue(
                    "preview_renderer_does_not_load_typography_spec",
                    "Preview renderer must load specs/typography_spec.json instead of hardcoding fonts/colors/sizes.",
                    str(renderer_path),
                ))
            if "ImageFont.truetype" in renderer_text and "typography_spec.json" not in renderer_text:
                issues.append(Issue(
                    "preview_renderer_hardcoded_font",
                    "Hardcoded PIL font selection is not a reproducible FairyGUI typography source.",
                    str(renderer_path),
                ))

        if text_mode == "deterministic_text_overlay":
            if not isinstance(preview.get("renderTrace"), str) or not preview.get("renderTrace"):
                issues.append(Issue(
                    "typography_render_trace_missing",
                    "deterministic_text_overlay requires productionPreview.renderTrace.",
                    str(spec_path),
                ))
            elif render_trace_path is None or not render_trace_path.is_file():
                issues.append(Issue("typography_render_trace_file_missing", "Typography render trace does not exist.", str(render_trace_path)))
            else:
                try:
                    render_trace = read_json(render_trace_path)
                except ValueError as exc:
                    issues.append(Issue("typography_render_trace_invalid", str(exc), str(render_trace_path)))
                    render_trace = {}
                if render_trace:
                    if render_trace.get("typographySpecSha256") != sha256_file(spec_path):
                        issues.append(Issue(
                            "typography_render_trace_spec_hash_mismatch",
                            "Render trace was not produced from the current typography_spec.json bytes.",
                            str(render_trace_path),
                        ))
                    if str(render_trace.get("rendererScript") or "").replace("\\", "/") != str(preview.get("rendererScript") or "").replace("\\", "/"):
                        issues.append(Issue("typography_render_trace_renderer_mismatch", "Render trace rendererScript does not match the spec.", str(render_trace_path)))
                    if str(render_trace.get("previewFile") or "").replace("\\", "/") != str(preview.get("file") or "").replace("\\", "/"):
                        issues.append(Issue("typography_render_trace_preview_mismatch", "Render trace previewFile does not match the spec.", str(render_trace_path)))
                    trace_entries = render_trace.get("instances")
                    if not isinstance(trace_entries, list):
                        issues.append(Issue("typography_render_trace_instances_invalid", "Render trace instances must be an array.", str(render_trace_path)))
                    else:
                        for trace_index, trace_entry in enumerate(trace_entries):
                            if not isinstance(trace_entry, dict):
                                issues.append(Issue("typography_render_trace_instance_invalid", f"instances[{trace_index}] must be an object.", str(render_trace_path)))
                                continue
                            trace_component = str(trace_entry.get("componentFile") or "")
                            trace_node = str(trace_entry.get("xmlNodeName") or "")
                            trace_key = instance_key(trace_entry)
                            if not trace_component or not trace_node:
                                issues.append(Issue("typography_render_trace_target_missing", "Trace instance requires componentFile and xmlNodeName.", str(render_trace_path)))
                                continue
                            trace_host_file = str(trace_entry.get("hostComponentFile") or "")
                            trace_host_instance = str(trace_entry.get("hostInstanceName") or "")
                            if bool(trace_host_file) != bool(trace_host_instance):
                                issues.append(Issue(
                                    "typography_render_trace_host_target_incomplete",
                                    "Trace hostComponentFile and hostInstanceName must be provided together.",
                                    str(render_trace_path),
                                    instance_target(trace_entry),
                                ))
                            if trace_key in trace_entries_by_target:
                                issues.append(Issue("typography_render_trace_target_duplicate", "Trace contains a duplicate text target.", str(render_trace_path), instance_target(trace_entry)))
                            trace_entries_by_target[trace_key] = trace_entry

    styles_raw = spec.get("styles")
    if not isinstance(styles_raw, list) or not styles_raw:
        issues.append(Issue("typography_styles_missing", "styles must be a non-empty array.", str(spec_path)))
        styles_raw = []
    styles: dict[str, dict[str, str]] = {}
    for index, style in enumerate(styles_raw):
        if not isinstance(style, dict):
            issues.append(Issue("typography_style_invalid", f"styles[{index}] must be an object.", str(spec_path)))
            continue
        style_id = str(style.get("styleId") or "")
        attrs = style.get("xmlAttributes")
        if not style_id:
            issues.append(Issue("typography_style_id_missing", f"styles[{index}].styleId is required.", str(spec_path)))
            continue
        if style_id in styles:
            issues.append(Issue("typography_style_duplicate", f"Duplicate styleId: {style_id}.", str(spec_path), style_id))
        if not isinstance(attrs, dict):
            issues.append(Issue("typography_xml_attributes_missing", "xmlAttributes must be an object.", str(spec_path), style_id))
            continue
        normalized = {str(key): str(value) for key, value in attrs.items() if value is not None}
        missing = sorted(CORE_ATTRIBUTES - set(normalized))
        if missing:
            issues.append(Issue("typography_core_attributes_missing", f"Missing core XML attributes: {missing}.", str(spec_path), style_id))
        unsupported = sorted(set(normalized) - SUPPORTED_ATTRIBUTES)
        if unsupported:
            issues.append(Issue("typography_attribute_unsupported", f"Unsupported text attributes: {unsupported}.", str(spec_path), style_id))
        try:
            if int(normalized.get("fontSize", "0")) <= 0:
                raise ValueError
        except ValueError:
            issues.append(Issue("typography_font_size_invalid", "fontSize must be a positive integer.", str(spec_path), style_id))
        color = normalized.get("color", "")
        if color and not COLOR_RE.fullmatch(color):
            issues.append(Issue("typography_color_invalid", "color must be #RRGGBB.", str(spec_path), style_id))
        for color_key in ("strokeColor", "shadowColor"):
            value = normalized.get(color_key)
            if value and not COLOR_RE.fullmatch(value):
                issues.append(Issue("typography_color_invalid", f"{color_key} must be #RRGGBB.", str(spec_path), style_id))
        styles[style_id] = normalized

    instances_raw = spec.get("instances")
    if not isinstance(instances_raw, list) or not instances_raw:
        issues.append(Issue("typography_instances_missing", "instances must be a non-empty array.", str(spec_path)))
        instances_raw = []

    seen_targets: set[tuple[str, str, str, str]] = set()
    xml_checks = STAGE_ORDER.get(stage, 50) >= STAGE_ORDER["xml_generation"]
    package_xml_root = xml_dir or resolve(root, manifest.get("package", {}).get("outputPath") if isinstance(manifest.get("package"), dict) else None)
    for index, instance in enumerate(instances_raw):
        if not isinstance(instance, dict):
            issues.append(Issue("typography_instance_invalid", f"instances[{index}] must be an object.", str(spec_path)))
            continue
        component_file = str(instance.get("componentFile") or "")
        node_name = str(instance.get("xmlNodeName") or "")
        host_component_file = str(instance.get("hostComponentFile") or "")
        host_instance_name = str(instance.get("hostInstanceName") or "")
        style_id = str(instance.get("styleId") or "")
        target = instance_target(instance)
        if not component_file or not node_name:
            issues.append(Issue("typography_instance_target_missing", "componentFile and xmlNodeName are required.", str(spec_path), target))
            continue
        if bool(host_component_file) != bool(host_instance_name):
            issues.append(Issue(
                "typography_host_target_incomplete",
                "hostComponentFile and hostInstanceName must be provided together for instance-level typography.",
                str(spec_path),
                target,
            ))
        key = instance_key(instance)
        if key in seen_targets:
            issues.append(Issue("typography_instance_duplicate", "Duplicate componentFile/xmlNodeName target.", str(spec_path), target))
        seen_targets.add(key)
        attrs = styles.get(style_id)
        if attrs is None:
            issues.append(Issue("typography_style_unresolved", f"Unknown styleId: {style_id}.", str(spec_path), target))
            continue
        preview_text = str(instance.get("previewText") or "")
        if not preview_text:
            issues.append(Issue("typography_preview_text_missing", "previewText is required for visual review.", str(spec_path), target))
        bbox = instance.get("bbox")
        if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(v, int) for v in bbox) and bbox[2] > 0 and bbox[3] > 0):
            issues.append(Issue("typography_bbox_invalid", "bbox must be integer [x,y,width,height].", str(spec_path), target))

        if assembly_checks and text_mode == "deterministic_text_overlay" and render_trace:
            trace_entry = trace_entries_by_target.get(key)
            if trace_entry is None:
                issues.append(Issue(
                    "typography_render_trace_instance_missing",
                    "Render trace is missing this typography instance.",
                    str(render_trace_path),
                    target,
                ))
            else:
                if str(trace_entry.get("styleId") or "") != style_id:
                    issues.append(Issue("typography_render_trace_style_mismatch", "Trace styleId does not match typography_spec.json.", str(render_trace_path), target))
                if str(trace_entry.get("previewText") or "") != preview_text:
                    issues.append(Issue("typography_render_trace_text_mismatch", "Trace previewText does not match typography_spec.json.", str(render_trace_path), target))
                if trace_entry.get("bbox") != bbox:
                    issues.append(Issue("typography_render_trace_bbox_mismatch", "Trace bbox does not match typography_spec.json.", str(render_trace_path), target))
                trace_attrs = trace_entry.get("xmlAttributes")
                normalized_trace_attrs = {str(k): str(v) for k, v in trace_attrs.items()} if isinstance(trace_attrs, dict) else None
                if normalized_trace_attrs != attrs:
                    issues.append(Issue(
                        "typography_render_trace_attributes_mismatch",
                        "Trace xmlAttributes do not exactly match the resolved typography style.",
                        str(render_trace_path),
                        target,
                    ))

        xml_path = package_xml_root / normalize_relative(component_file) if package_xml_root else None
        xml_result: dict[str, Any] = {
            "target": target,
            "styleId": style_id,
            "xmlFile": str(xml_path) if xml_path else None,
        }
        if xml_checks:
            if xml_path is None or not xml_path.is_file():
                issues.append(Issue("typography_component_xml_missing", "Target component XML does not exist.", str(xml_path), target))
            else:
                try:
                    root_element = ET.parse(xml_path).getroot()
                except (OSError, ET.ParseError) as exc:
                    issues.append(Issue("typography_component_xml_invalid", str(exc), str(xml_path), target))
                else:
                    nodes = find_named_node(root_element, node_name, {"text", "richtext"})
                    if len(nodes) != 1:
                        issues.append(Issue(
                            "typography_xml_node_unresolved",
                            f"Expected exactly one text/richtext node named {node_name}, found {len(nodes)}.",
                            str(xml_path),
                            target,
                        ))
                    else:
                        node = nodes[0]
                        host_node: ET.Element | None = None
                        override_node: ET.Element | None = None
                        host_path: Path | None = None
                        if host_component_file and host_instance_name:
                            host_path = package_xml_root / normalize_relative(host_component_file) if package_xml_root else None
                            if host_path is None or not host_path.is_file():
                                issues.append(Issue(
                                    "typography_host_component_xml_missing",
                                    "Host component XML does not exist for instance-level typography.",
                                    str(host_path),
                                    target,
                                ))
                            else:
                                try:
                                    host_root = ET.parse(host_path).getroot()
                                except (OSError, ET.ParseError) as exc:
                                    issues.append(Issue("typography_host_component_xml_invalid", str(exc), str(host_path), target))
                                else:
                                    host_nodes = find_named_node(host_root, host_instance_name, {"component"})
                                    if len(host_nodes) != 1:
                                        issues.append(Issue(
                                            "typography_host_instance_unresolved",
                                            f"Expected exactly one component instance named {host_instance_name}, found {len(host_nodes)}.",
                                            str(host_path),
                                            target,
                                        ))
                                    else:
                                        host_node = host_nodes[0]
                                        expected_component_file = str(PurePosixPath(component_file.replace("\\", "/"))).lstrip("./")
                                        actual_component_file = str(PurePosixPath(str(host_node.attrib.get("fileName") or "").replace("\\", "/"))).lstrip("./")
                                        if actual_component_file != expected_component_file:
                                            issues.append(Issue(
                                                "typography_host_component_file_mismatch",
                                                f"Host instance fileName must equal {expected_component_file!r}, actual={actual_component_file!r}.",
                                                str(host_path),
                                                target,
                                            ))
                                        extension = str(root_element.attrib.get("extention") or "")
                                        if extension not in {"Button", "Label"}:
                                            issues.append(Issue(
                                                "typography_host_extension_unsupported",
                                                "Instance-level typography currently requires a Button or Label component extension.",
                                                str(xml_path),
                                                target,
                                            ))
                                        else:
                                            override_nodes = [child for child in host_node if child.tag == extension]
                                            if len(override_nodes) != 1:
                                                issues.append(Issue(
                                                    "typography_host_extension_override_missing",
                                                    f"Host instance must contain exactly one <{extension}> override node.",
                                                    str(host_path),
                                                    target,
                                                ))
                                            else:
                                                override_node = override_nodes[0]

                        for attr_name, expected in attrs.items():
                            actual = node.attrib.get(attr_name)
                            override_attribute = EXTENSION_STYLE_ATTRIBUTES.get(attr_name)
                            if override_node is not None and override_attribute in override_node.attrib:
                                actual = override_node.attrib.get(override_attribute)
                            if actual != expected:
                                issues.append(Issue(
                                    "typography_xml_attribute_mismatch",
                                    f"{attr_name}: expected={expected!r}, actual={actual!r}.",
                                    str(host_path or xml_path),
                                    target,
                                ))
                        if isinstance(bbox, list) and len(bbox) == 4:
                            if host_node is not None:
                                effective_bbox = effective_host_bbox(root_element, node, host_node)
                                if effective_bbox != bbox:
                                    issues.append(Issue(
                                        "typography_xml_bbox_mismatch",
                                        f"Effective host-instance bbox must equal {bbox}, actual={effective_bbox}.",
                                        str(host_path or xml_path),
                                        target,
                                    ))
                            else:
                                expected_xy = [bbox[0], bbox[1]]
                                expected_size = [bbox[2], bbox[3]]
                                if parse_pair(node.attrib.get("xy")) != expected_xy:
                                    issues.append(Issue("typography_xml_bbox_mismatch", f"xy must equal {expected_xy}.", str(xml_path), target))
                                if parse_pair(node.attrib.get("size")) != expected_size:
                                    issues.append(Issue("typography_xml_bbox_mismatch", f"size must equal {expected_size}.", str(xml_path), target))
                        effective_text = node.attrib.get("text")
                        if override_node is not None and "title" in override_node.attrib:
                            effective_text = override_node.attrib.get("title")
                        if preview_text and effective_text != preview_text:
                            issues.append(Issue(
                                "typography_preview_text_mismatch",
                                f"Effective XML preview text must equal {preview_text!r}.",
                                str(host_path or xml_path),
                                target,
                            ))
                        localization_key = str(instance.get("localizationKey") or "")
                        if localization_key:
                            expected_custom_data = f"loc:{localization_key}"
                            localization_ok = node.attrib.get("customData") == expected_custom_data
                            if host_node is not None:
                                localization_ok = host_node.attrib.get("customData") == expected_custom_data or (
                                    effective_text == node.attrib.get("text")
                                    and node.attrib.get("customData") == expected_custom_data
                                )
                            if not localization_ok:
                                issues.append(Issue(
                                    "typography_localization_mapping_missing",
                                    f"Effective instance localization must map to {expected_custom_data!r}.",
                                    str(host_path or xml_path),
                                    target,
                                ))
                        xml_result["xmlAttributes"] = dict(node.attrib)
                        if override_node is not None:
                            xml_result["extensionOverrideAttributes"] = dict(override_node.attrib)
                            xml_result["hostXmlFile"] = str(host_path) if host_path else None
        checked.append(xml_result)

    if assembly_checks and text_mode == "deterministic_text_overlay" and render_trace:
        extra_trace_targets = sorted(set(trace_entries_by_target) - seen_targets)
        for component_file, node_name, host_component_file, host_instance_name in extra_trace_targets:
            trace_target = f"{component_file}:{node_name}"
            if host_component_file or host_instance_name:
                trace_target = f"{host_component_file}:{host_instance_name}->{trace_target}"
            issues.append(Issue(
                "typography_render_trace_instance_extra",
                "Render trace contains a text target that is not declared in typography_spec.json.",
                str(render_trace_path),
                trace_target,
            ))

    if spec.get("reviewStatus") != "approved" and assembly_checks:
        issues.append(Issue("typography_review_not_approved", "Typography spec must be human-approved before assembly.", str(spec_path)))
    review = spec.get("review") if isinstance(spec.get("review"), dict) else {}
    if assembly_checks and (review.get("recordedBy") not in {"user", "human_reviewer"} or review.get("type") not in {"user_confirmation", "manual_review"}):
        issues.append(Issue("typography_ai_self_approval_forbidden", "Typography approval must be human-originated.", str(spec_path)))

    return build_report(root, stage, checked, issues)


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Typography Fidelity Report",
        "",
        f"- Status: **{report['status']}**",
        f"- Stage: `{report['stage']}`",
        f"- Text instances checked: {report['summary']['instancesChecked']}",
        "",
        "## Issues",
        "",
    ]
    if not report["issues"]:
        lines.append("- None")
    else:
        for item in report["issues"]:
            target = f" `{item['target']}`" if item.get("target") else ""
            location = f" ({item['path']})" if item.get("path") else ""
            lines.append(f"- **{item['code']}**{target}: {item['message']}{location}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--stage", choices=tuple(STAGE_ORDER), default="asset_planning")
    parser.add_argument("--xml-dir", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report-md", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    report = validate(root, args.stage, args.xml_dir.resolve() if args.xml_dir else None)
    out = args.out or root / "reports" / "typography_fidelity_report.json"
    report_md = args.report_md or root / "reports" / "typography_fidelity_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, report_md)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
