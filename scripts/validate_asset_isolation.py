#!/usr/bin/env python3
"""Validate semantic and pixel isolation of production FairyGUI bitmaps."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

try:
    from PIL import Image, ImageChops
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[assignment]
    ImageChops = None  # type: ignore[assignment]


STAGE_ORDER = {
    "asset_planning": 10,
    "resource_generation": 20,
    "sheet_slicing": 30,
    "fairygui_assembly": 40,
    "xml_generation": 50,
    "validation": 60,
}

ALLOWED_SOURCE_MODES = {
    "provided_bitmap",
    "existing_package_bitmap",
    "approved_design_slice",
    "approved_sheet_slice",
    "image_generation_with_reference",
    "manual_reconstruction",
    "inpainted_environment",
}

ISOLATION_ROLES = {
    "environment_background",
    "isolated_subject",
    "isolated_icon",
    "decorative_frame",
    "component_skin",
    "full_screen_reference_only",
}

ISOLATED_ROLES = {"isolated_subject", "isolated_icon"}
DYNAMIC_SKIN_ROLES = {"decorative_frame", "component_skin"}
BITMAP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
HUMAN_REVIEW_TYPES = {"user_confirmation", "human_visual_review", "artist_review", "designer_review", "qa_review"}
AI_REVIEWER_ALIASES = {"ai", "assistant", "model", "agent", "chatgpt", "codex"}

ROLE_BY_TYPE = {
    "background": "environment_background",
    "environment": "environment_background",
    "portrait": "isolated_subject",
    "character": "isolated_subject",
    "hero": "isolated_subject",
    "icon": "isolated_icon",
    "badge": "isolated_icon",
    "crest": "isolated_icon",
    "emblem": "isolated_icon",
    "frame": "decorative_frame",
    "border": "decorative_frame",
    "title_plate": "decorative_frame",
    "panel": "component_skin",
    "button_skin": "component_skin",
    "card_skin": "component_skin",
    "bar": "component_skin",
}

CROP_PATTERNS = (
    re.compile(r"\.crop\s*\("),
    re.compile(r"Image\.open\s*\("),
)
TRANSFORM_PATTERNS = (
    re.compile(r"remove[_-]?background", re.I),
    re.compile(r"inpaint", re.I),
    re.compile(r"rembg", re.I),
    re.compile(r"putalpha", re.I),
    re.compile(r"alpha_composite", re.I),
    re.compile(r"mask", re.I),
    re.compile(r"segmentation", re.I),
    re.compile(r"image_generation", re.I),
)


@dataclass
class Issue:
    code: str
    message: str
    asset: str | None = None
    path: str | None = None
    severity: str = "error"


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {path}: {exc}") from exc
    return value if isinstance(value, dict) else {}


def first_existing(root: Path, candidates: Iterable[str]) -> Path | None:
    for relative in candidates:
        candidate = root / relative
        if candidate.is_file():
            return candidate
    return None


def normalize_relative(value: str) -> Path:
    normalized = str(PurePosixPath(value.replace("\\", "/"))).lstrip("./")
    return Path(*PurePosixPath(normalized).parts)


def resolve_project_path(root: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    candidate = Path(raw)
    return candidate if candidate.is_absolute() else root / normalize_relative(raw)


def list_assets(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    value = manifest.get("assets")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def is_bitmap_asset(asset: dict[str, Any]) -> bool:
    file_value = asset.get("file")
    extension = PurePosixPath(str(file_value).replace("\\", "/")).suffix.lower() if isinstance(file_value, str) else ""
    fgui = asset.get("fgui") if isinstance(asset.get("fgui"), dict) else {}
    resource_type = str(fgui.get("resourceType") or "").lower()
    return resource_type in {"image", "atlas", "movieclip"} or extension in BITMAP_EXTENSIONS


def asset_name(asset: dict[str, Any]) -> str:
    return str(asset.get("name") or asset.get("id") or asset.get("file") or "<unnamed>")


def infer_role(asset: dict[str, Any]) -> str | None:
    asset_type = str(asset.get("type") or "").strip().lower()
    if asset_type in ROLE_BY_TYPE:
        return ROLE_BY_TYPE[asset_type]
    fgui = asset.get("fgui") if isinstance(asset.get("fgui"), dict) else {}
    layer = str(fgui.get("layer") or "").strip().lower()
    if layer in ROLE_BY_TYPE:
        return ROLE_BY_TYPE[layer]
    name = asset_name(asset).lower()
    for token, role in ROLE_BY_TYPE.items():
        if token in name:
            return role
    return None


def normalized_crop(value: Any) -> tuple[int, int, int, int] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        x, y, width, height = (int(round(float(item))) for item in value)
    except (TypeError, ValueError):
        return None
    return x, y, width, height


def same_full_bounds(crop: tuple[int, int, int, int], size: tuple[int, int], tolerance: int = 1) -> bool:
    x, y, width, height = crop
    source_width, source_height = size
    return (
        abs(x) <= tolerance
        and abs(y) <= tolerance
        and abs(width - source_width) <= tolerance
        and abs(height - source_height) <= tolerance
    )


def image_size(path: Path | None) -> tuple[int, int] | None:
    if path is None or not path.is_file() or Image is None:
        return None
    try:
        with Image.open(path) as image:
            return image.size
    except Exception:
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def exact_crop_matches(source: Path, output: Path, crop: tuple[int, int, int, int]) -> bool | None:
    if Image is None or ImageChops is None:
        return None
    x, y, width, height = crop
    try:
        with Image.open(source) as source_image, Image.open(output) as output_image:
            expected = source_image.convert("RGBA").crop((x, y, x + width, y + height))
            actual = output_image.convert("RGBA")
            if expected.size != actual.size:
                return False
            return ImageChops.difference(expected, actual).getbbox() is None
    except Exception:
        return False


def alpha_metrics(path: Path) -> dict[str, float] | None:
    if Image is None:
        return None
    try:
        with Image.open(path) as image:
            rgba = image.convert("RGBA")
            alpha = rgba.getchannel("A")
            width, height = rgba.size
            if width <= 0 or height <= 0:
                return None
            histogram = alpha.histogram()
            total = width * height
            transparent = sum(histogram[:250])
            opaque = histogram[255]
            pixels = alpha.load()
            edge_values: list[int] = []
            for x in range(width):
                edge_values.append(pixels[x, 0])
                if height > 1:
                    edge_values.append(pixels[x, height - 1])
            for y in range(1, max(1, height - 1)):
                edge_values.append(pixels[0, y])
                if width > 1:
                    edge_values.append(pixels[width - 1, y])
            edge_opaque = sum(1 for value in edge_values if value >= 250)
            return {
                "transparentRatio": transparent / total,
                "opaqueRatio": opaque / total,
                "edgeOpaqueRatio": edge_opaque / max(1, len(edge_values)),
            }
    except Exception:
        return None


def approved_design_paths(root: Path, manifest: dict[str, Any]) -> set[Path]:
    values: list[str] = []
    approval = read_json(root / "reports" / "design_approval.json")
    for key in ("approvedFile", "candidateFile", "designFile", "file", "path"):
        value = approval.get(key)
        if isinstance(value, str):
            values.append(value)
    approved_design = manifest.get("approvedDesign")
    if isinstance(approved_design, dict) and isinstance(approved_design.get("file"), str):
        values.append(approved_design["file"])
    resolved: set[Path] = set()
    for value in values:
        path = resolve_project_path(root, value)
        if path is not None:
            try:
                resolved.add(path.resolve())
            except OSError:
                resolved.add(path)
    return resolved


def source_is_approved_design(source_file: Path | None, approved: set[Path]) -> bool:
    if source_file is None:
        return False
    try:
        return source_file.resolve() in approved
    except OSError:
        return source_file in approved


def find_asset_file(root: Path, asset: dict[str, Any], xml_dir: Path | None) -> Path | None:
    for raw in (asset.get("file"), asset.get("path"), asset.get("output"), asset.get("outputPath")):
        path = resolve_project_path(root, raw)
        if path is not None and path.is_file():
            return path
    source = asset.get("assetSource")
    if isinstance(source, dict):
        for raw in (source.get("outputFile"), source.get("generatedFile")):
            path = resolve_project_path(root, raw)
            if path is not None and path.is_file():
                return path
    name = asset_name(asset)
    candidate_names = {Path(name).name}
    if Path(name).suffix.lower() not in BITMAP_EXTENSIONS:
        candidate_names.update(f"{name}{extension}" for extension in BITMAP_EXTENSIONS)
    roots = [candidate for candidate in (xml_dir, root / "fgui_xml", root / "generated") if candidate and candidate.exists()]
    for search_root in roots:
        for candidate_name in candidate_names:
            match = next(search_root.rglob(candidate_name), None)
            if match is not None:
                return match
    return None


def script_is_plain_crop(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return all(pattern.search(text) for pattern in CROP_PATTERNS) and not any(
        pattern.search(text) for pattern in TRANSFORM_PATTERNS
    )


def collect_plain_crop_scripts(root: Path) -> list[Path]:
    scripts_dir = root / "scripts"
    return [path for path in scripts_dir.rglob("*.py") if script_is_plain_crop(path)] if scripts_dir.is_dir() else []


def normalize_manifest_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return str(PurePosixPath(value.replace("\\", "/"))).lstrip("./")


def registered_sheet_records(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    sheets = manifest.get("sheets")
    if not isinstance(sheets, list):
        return result
    for sheet in sheets:
        if not isinstance(sheet, dict):
            continue
        for key in ("file", "sourceFile", "previewFile", "outputFile"):
            normalized = normalize_manifest_path(sheet.get(key))
            if normalized:
                result[normalized] = sheet
    return result


def load_slice_plan(root: Path) -> tuple[dict[str, dict[str, Any]], set[str]]:
    plan = read_json(root / "specs" / "slice_plan.json")
    entries = plan.get("entries")
    if not isinstance(entries, list):
        entries = plan.get("slices")
    result: dict[str, dict[str, Any]] = {}
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for key in (entry.get("name"), entry.get("output")):
                if isinstance(key, str) and key:
                    result[key] = entry
                    result[Path(key).stem] = entry

    sources: set[str] = set()
    for raw in plan.get("sourceImages", []) if isinstance(plan.get("sourceImages"), list) else []:
        if isinstance(raw, dict):
            raw = raw.get("file")
        normalized = normalize_manifest_path(raw)
        if normalized:
            sources.add(normalized)
    return result, sources


def load_cut_entries(root: Path) -> tuple[Path, dict[str, dict[str, Any]], set[str], dict[str, Any]]:
    path = root / "reports" / "cut_report.json"
    report = read_json(path)
    outputs = report.get("outputs")
    result: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    if isinstance(outputs, list):
        for entry in outputs:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or entry.get("assetName") or "").strip()
            if not name:
                continue
            if name in result:
                duplicates.add(name)
            result[name] = entry
    return path, result, duplicates, report


def review_required(stage: str) -> bool:
    return STAGE_ORDER.get(stage, STAGE_ORDER["xml_generation"]) >= STAGE_ORDER["resource_generation"]


def cut_evidence_required(stage: str) -> bool:
    return STAGE_ORDER.get(stage, STAGE_ORDER["xml_generation"]) >= STAGE_ORDER["sheet_slicing"]


def output_required(stage: str) -> bool:
    return STAGE_ORDER.get(stage, STAGE_ORDER["xml_generation"]) >= STAGE_ORDER["resource_generation"]


def validate(root: Path, stage: str = "asset_planning", xml_dir: Path | None = None) -> dict[str, Any]:
    issues: list[Issue] = []
    manifest_path = first_existing(root, ("manifests/asset_manifest.json", "specs/asset_manifest.json"))
    if manifest_path is None:
        issues.append(Issue("asset_manifest_missing", "Asset manifest is required for asset-isolation validation."))
        return build_report(root, stage, None, [], issues, [])

    try:
        manifest = read_json(manifest_path)
    except ValueError as exc:
        issues.append(Issue("asset_manifest_invalid", str(exc), path=str(manifest_path)))
        return build_report(root, stage, manifest_path, [], issues, [])

    production = manifest.get("production") if isinstance(manifest.get("production"), dict) else {}
    requires_gate = production.get("requiresAssetIsolation") is True
    full_screen_design = production.get("generateFullScreenDesign") is True
    approved_paths = approved_design_paths(root, manifest)
    plain_crop_scripts = collect_plain_crop_scripts(root)
    slice_entries, slice_source_images = load_slice_plan(root)
    sheet_records = registered_sheet_records(manifest)
    cut_report_path = root / "reports" / "cut_report.json"
    cut_entries: dict[str, dict[str, Any]] = {}
    duplicate_cut_entries: set[str] = set()
    cut_report_data: dict[str, Any] = {}
    try:
        cut_report_path, cut_entries, duplicate_cut_entries, cut_report_data = load_cut_entries(root)
    except ValueError as exc:
        issues.append(Issue("cut_report_invalid", str(exc), path=str(cut_report_path)))
    has_approved_sheet_slices = any(
        isinstance(asset.get("assetSource"), dict)
        and asset["assetSource"].get("mode") == "approved_sheet_slice"
        for asset in list_assets(manifest)
        if is_bitmap_asset(asset)
    )
    if cut_evidence_required(stage) and has_approved_sheet_slices:
        if not cut_report_data:
            issues.append(Issue(
                "cut_report_missing",
                "approved_sheet_slice assets require reports/cut_report.json after sheet slicing.",
                path=str(cut_report_path),
            ))
        elif cut_report_data.get("ok") is not True:
            issues.append(Issue(
                "cut_report_not_ok",
                "cut_report.json must set ok=true before downstream assembly.",
                path=str(cut_report_path),
            ))
        for duplicate_name in sorted(duplicate_cut_entries):
            issues.append(Issue(
                "cut_report_asset_duplicate",
                "cut_report.outputs must contain exactly one row per sliced asset.",
                duplicate_name,
                str(cut_report_path),
            ))

    if full_screen_design and not requires_gate:
        issues.append(Issue(
            "asset_isolation_gate_not_required",
            "Full-screen design projects must set production.requiresAssetIsolation=true.",
            path=str(manifest_path),
        ))
    if not requires_gate and not full_screen_design:
        report = build_report(root, stage, manifest_path, [], [], plain_crop_scripts)
        report["status"] = "SKIPPED"
        report["applicable"] = False
        report["asset_isolation_checked"] = False
        report["skipped"] = True
        report["skipReason"] = "production.requiresAssetIsolation is not enabled."
        return report

    checked: list[dict[str, Any]] = []
    for asset in list_assets(manifest):
        if not is_bitmap_asset(asset):
            continue
        name = asset_name(asset)
        source = asset.get("assetSource") if isinstance(asset.get("assetSource"), dict) else {}
        isolation = asset.get("assetIsolation") if isinstance(asset.get("assetIsolation"), dict) else None
        inferred_role = infer_role(asset)
        declared_role = str(isolation.get("role") or "") if isolation else ""
        role = declared_role or inferred_role or ""
        source_mode = str(source.get("mode") or "")
        source_file_raw = source.get("sourceFile")
        source_file_key = normalize_manifest_path(source_file_raw)
        source_file = resolve_project_path(root, source_file_raw)
        crop = normalized_crop(source.get("crop") or asset.get("crop"))
        source_size = image_size(source_file)
        output_file = find_asset_file(root, asset, xml_dir)
        metrics = alpha_metrics(output_file) if output_file is not None else None
        slice_entry = slice_entries.get(name) or slice_entries.get(Path(str(asset.get("file") or "")).name)

        if source_mode not in ALLOWED_SOURCE_MODES:
            issues.append(Issue("asset_source_mode_invalid", f"Unsupported assetSource.mode: {source_mode!r}.", name))

        if source_mode == "approved_sheet_slice":
            if source_file_key is None:
                issues.append(Issue(
                    "approved_sheet_source_missing",
                    "approved_sheet_slice requires assetSource.sourceFile pointing to the exact approved resource preview sheet.",
                    name,
                    str(manifest_path),
                ))
            else:
                sheet_record = sheet_records.get(source_file_key)
                if sheet_record is None:
                    issues.append(Issue(
                        "approved_sheet_source_not_registered",
                        "approved_sheet_slice sourceFile must be registered in manifest.sheets.",
                        name,
                        source_file_key,
                    ))
                else:
                    sheet_evidence = sheet_record.get("reviewEvidence")
                    sheet_evidence_path = resolve_project_path(root, sheet_evidence)
                    if review_required(stage):
                        if source_file is None or not source_file.is_file():
                            issues.append(Issue(
                                "approved_sheet_source_file_missing",
                                "The exact approved resource preview sheet does not exist.",
                                name,
                                str(source_file) if source_file else source_file_key,
                            ))
                        if sheet_record.get("reviewStatus") != "approved":
                            issues.append(Issue(
                                "approved_sheet_review_not_approved",
                                "The resource preview sheet must have reviewStatus=approved before slicing.",
                                name,
                                source_file_key,
                            ))
                        sheet_reviewer = str(sheet_record.get("reviewedBy") or "").strip()
                        sheet_review_type = str(sheet_record.get("reviewType") or "").strip()
                        if not sheet_reviewer:
                            issues.append(Issue(
                                "approved_sheet_reviewer_missing",
                                "Approved resource preview sheet must record reviewedBy.",
                                name,
                                source_file_key,
                            ))
                        elif sheet_reviewer.lower() in AI_REVIEWER_ALIASES:
                            issues.append(Issue(
                                "approved_sheet_ai_self_approval_forbidden",
                                "AI/model self-approval is not valid resource-preview-sheet approval.",
                                name,
                                source_file_key,
                            ))
                        if sheet_review_type not in HUMAN_REVIEW_TYPES:
                            issues.append(Issue(
                                "approved_sheet_review_type_invalid",
                                f"Resource preview sheet reviewType must be one of {sorted(HUMAN_REVIEW_TYPES)}.",
                                name,
                                source_file_key,
                            ))
                        if not isinstance(sheet_evidence, str) or not sheet_evidence.strip() or sheet_evidence_path is None or not sheet_evidence_path.is_file():
                            issues.append(Issue(
                                "approved_sheet_review_evidence_missing",
                                "Approved resource preview sheet review evidence is required.",
                                name,
                                source_file_key,
                            ))
                    elif not isinstance(sheet_evidence, str) or not sheet_evidence.strip():
                        issues.append(Issue(
                            "approved_sheet_review_target_missing",
                            "Asset planning must declare the resource preview sheet reviewEvidence path.",
                            name,
                            source_file_key,
                        ))
                if source_file_key not in slice_source_images:
                    issues.append(Issue(
                        "slice_plan_missing_approved_sheet_source",
                        "slice_plan.sourceImages must include the exact resource preview sheet used for slicing.",
                        name,
                        str(root / "specs" / "slice_plan.json"),
                    ))
            if slice_entry is None:
                issues.append(Issue(
                    "slice_plan_asset_missing",
                    "Every approved_sheet_slice asset must have one matching slice-plan entry.",
                    name,
                    str(root / "specs" / "slice_plan.json"),
                ))
            else:
                slice_source_key = normalize_manifest_path(slice_entry.get("sourceFile"))
                if slice_source_key != source_file_key:
                    issues.append(Issue(
                        "slice_plan_source_mismatch",
                        f"Slice entry sourceFile must equal assetSource.sourceFile exactly: manifest={source_file_key}, slicePlan={slice_source_key}.",
                        name,
                        str(root / "specs" / "slice_plan.json"),
                    ))
                slice_crop = normalized_crop(slice_entry.get("crop"))
                if slice_crop != crop:
                    issues.append(Issue(
                        "slice_plan_crop_mismatch",
                        f"Slice entry crop must equal assetSource.crop exactly: manifest={list(crop) if crop else None}, slicePlan={list(slice_crop) if slice_crop else None}.",
                        name,
                        str(root / "specs" / "slice_plan.json"),
                    ))
                manifest_output_key = normalize_manifest_path(asset.get("file"))
                slice_output_key = normalize_manifest_path(slice_entry.get("output"))
                if slice_output_key != manifest_output_key:
                    issues.append(Issue(
                        "slice_plan_output_mismatch",
                        f"Slice entry output must equal manifest asset.file exactly: manifest={manifest_output_key}, slicePlan={slice_output_key}.",
                        name,
                        str(root / "specs" / "slice_plan.json"),
                    ))
                extraction_mode = str(slice_entry.get("extractionMode") or slice_entry.get("derivationMode") or "")
                if extraction_mode not in {"exact_crop", "deterministic_transform"}:
                    issues.append(Issue(
                        "slice_plan_derivation_mode_invalid",
                        "approved_sheet_slice requires extractionMode=exact_crop or deterministic_transform in the per-asset slice entry.",
                        name,
                        str(root / "specs" / "slice_plan.json"),
                    ))
            if source_is_approved_design(source_file, approved_paths):
                issues.append(Issue(
                    "approved_sheet_slice_uses_full_screen_design",
                    "approved_sheet_slice cannot point to the approved full-screen design; use an approved resource preview sheet.",
                    name,
                    str(source_file) if source_file else None,
                ))
            if crop is None or crop[0] < 0 or crop[1] < 0 or crop[2] <= 0 or crop[3] <= 0:
                issues.append(Issue(
                    "approved_sheet_crop_invalid",
                    "approved_sheet_slice requires a positive crop=[x,y,width,height].",
                    name,
                    str(manifest_path),
                ))
            elif source_size and (crop[0] + crop[2] > source_size[0] or crop[1] + crop[3] > source_size[1]):
                issues.append(Issue(
                    "approved_sheet_crop_out_of_bounds",
                    f"Declared sheet crop {list(crop)} exceeds source size {list(source_size)}.",
                    name,
                    str(source_file) if source_file else None,
                ))

            if cut_evidence_required(stage):
                cut_entry = cut_entries.get(name)
                if cut_entry is None:
                    issues.append(Issue(
                        "cut_report_asset_missing",
                        "cut_report.outputs must record the actual source, crop, derivation mode, and output for this sliced asset.",
                        name,
                        str(cut_report_path),
                    ))
                else:
                    if cut_entry.get("status") != "ok":
                        issues.append(Issue(
                            "cut_report_asset_not_ok",
                            "Each sliced asset row must set status=ok before downstream assembly.",
                            name,
                            str(cut_report_path),
                        ))
                    cut_source_key = normalize_manifest_path(cut_entry.get("sourceFile") or cut_entry.get("actualSourceFile"))
                    if cut_source_key != source_file_key:
                        issues.append(Issue(
                            "cut_report_source_mismatch",
                            f"Cut report source must equal assetSource.sourceFile exactly: manifest={source_file_key}, cutReport={cut_source_key}.",
                            name,
                            str(cut_report_path),
                        ))
                    cut_crop = normalized_crop(cut_entry.get("crop"))
                    if cut_crop != crop:
                        issues.append(Issue(
                            "cut_report_crop_mismatch",
                            f"Cut report crop must equal assetSource.crop exactly: manifest={list(crop) if crop else None}, cutReport={list(cut_crop) if cut_crop else None}.",
                            name,
                            str(cut_report_path),
                        ))
                    manifest_output_key = normalize_manifest_path(asset.get("file"))
                    cut_output_key = normalize_manifest_path(cut_entry.get("file") or cut_entry.get("outputFile"))
                    if cut_output_key != manifest_output_key:
                        issues.append(Issue(
                            "cut_report_output_mismatch",
                            f"Cut report output must equal manifest asset.file exactly: manifest={manifest_output_key}, cutReport={cut_output_key}.",
                            name,
                            str(cut_report_path),
                        ))
                    derivation_mode = str(cut_entry.get("derivationMode") or "")
                    if derivation_mode not in {"exact_crop", "deterministic_transform"}:
                        issues.append(Issue(
                            "cut_report_derivation_mode_invalid",
                            "approved_sheet_slice cut evidence requires derivationMode=exact_crop or deterministic_transform.",
                            name,
                            str(cut_report_path),
                        ))
                    if source_file is not None and source_file.is_file():
                        declared_source_hash = str(cut_entry.get("sourceSha256") or "")
                        current_source_hash = sha256_file(source_file)
                        if not declared_source_hash:
                            issues.append(Issue(
                                "cut_report_source_hash_missing",
                                "Cut report must freeze sourceSha256 for the exact resource preview sheet.",
                                name,
                                str(cut_report_path),
                            ))
                        elif declared_source_hash != current_source_hash:
                            issues.append(Issue(
                                "cut_report_source_hash_mismatch",
                                "Cut report sourceSha256 does not match the current declared source sheet.",
                                name,
                                str(source_file),
                            ))
                    if output_file is not None and output_file.is_file():
                        declared_output_hash = str(cut_entry.get("outputSha256") or "")
                        current_output_hash = sha256_file(output_file)
                        if not declared_output_hash:
                            issues.append(Issue(
                                "cut_report_output_hash_missing",
                                "Cut report must freeze outputSha256 for the staged runtime bitmap.",
                                name,
                                str(cut_report_path),
                            ))
                        elif declared_output_hash != current_output_hash:
                            issues.append(Issue(
                                "cut_report_output_hash_mismatch",
                                "Cut report outputSha256 does not match the current staged runtime bitmap.",
                                name,
                                str(output_file),
                            ))
                    if derivation_mode == "exact_crop" and source_file and output_file and crop:
                        crop_match = exact_crop_matches(source_file, output_file, crop)
                        if crop_match is False:
                            issues.append(Issue(
                                "cut_report_exact_crop_pixel_mismatch",
                                "Runtime bitmap pixels do not equal the declared crop from the approved resource preview sheet.",
                                name,
                                str(output_file),
                            ))
                        elif crop_match is None:
                            issues.append(Issue(
                                "cut_report_exact_crop_pixel_check_unavailable",
                                "Pillow is unavailable; exact crop pixel equality was not checked.",
                                name,
                                str(output_file),
                                severity="warning",
                            ))
                    if derivation_mode == "deterministic_transform":
                        processor_raw = cut_entry.get("processorScript") or cut_entry.get("transformScript")
                        processor_path = resolve_project_path(root, processor_raw)
                        if processor_path is None or not processor_path.is_file():
                            issues.append(Issue(
                                "cut_report_processor_script_missing",
                                "deterministic_transform requires an existing processorScript.",
                                name,
                                str(processor_path) if processor_path else str(cut_report_path),
                            ))
                        else:
                            declared_script_hash = str(cut_entry.get("processorScriptSha256") or cut_entry.get("transformScriptSha256") or "")
                            current_script_hash = sha256_file(processor_path)
                            if not declared_script_hash:
                                issues.append(Issue(
                                    "cut_report_processor_script_hash_missing",
                                    "Cut report must freeze processorScriptSha256.",
                                    name,
                                    str(cut_report_path),
                                ))
                            elif declared_script_hash != current_script_hash:
                                issues.append(Issue(
                                    "cut_report_processor_script_hash_mismatch",
                                    "Cut report processor script hash does not match the current script bytes.",
                                    name,
                                    str(processor_path),
                                ))

        if isolation is None:
            issues.append(Issue(
                "asset_isolation_declaration_missing",
                "Every production bitmap must declare assetIsolation when the gate is enabled.",
                name,
                str(manifest_path),
            ))
        else:
            if declared_role not in ISOLATION_ROLES:
                issues.append(Issue("asset_isolation_role_invalid", f"Unsupported assetIsolation.role: {declared_role!r}.", name))
            evidence = isolation.get("reviewEvidence")
            evidence_path = resolve_project_path(root, evidence)
            if review_required(stage):
                if isolation.get("reviewStatus") != "approved":
                    issues.append(Issue("asset_isolation_review_not_approved", "assetIsolation.reviewStatus must be approved after resource generation.", name))
                reviewed_by = str(isolation.get("reviewedBy") or "").strip()
                review_type = str(isolation.get("reviewType") or "").strip()
                if not reviewed_by:
                    issues.append(Issue("asset_isolation_reviewer_missing", "Approved isolation review must record reviewedBy.", name))
                elif reviewed_by.lower() in AI_REVIEWER_ALIASES:
                    issues.append(Issue("asset_isolation_ai_self_approval_forbidden", "AI/model self-approval is not valid asset-isolation evidence.", name))
                if review_type not in HUMAN_REVIEW_TYPES:
                    issues.append(Issue("asset_isolation_review_type_invalid", f"reviewType must be one of {sorted(HUMAN_REVIEW_TYPES)}.", name))
                if not isinstance(evidence, str) or not evidence.strip() or evidence_path is None or not evidence_path.is_file():
                    issues.append(Issue("asset_isolation_review_missing", "Approved isolation review evidence file is required.", name))
            elif not isinstance(evidence, str) or not evidence.strip():
                issues.append(Issue("asset_isolation_review_target_missing", "Asset planning must declare the future reviewEvidence path.", name))

        if output_required(stage) and output_file is None:
            issues.append(Issue("asset_isolation_output_missing", "Generated bitmap is missing and cannot be inspected.", name))

        is_approved_design_source = source_is_approved_design(source_file, approved_paths)
        if role == "full_screen_reference_only" and output_file and xml_dir and xml_dir.resolve() in output_file.resolve().parents:
            issues.append(Issue("full_screen_reference_registered_as_runtime_asset", "Reference-only design is staged inside the runtime package.", name, str(output_file)))

        if role == "environment_background":
            clean_environment = bool(isolation and isolation.get("cleanEnvironmentOnly") is True)
            if source_mode == "approved_design_slice" and crop and source_size and same_full_bounds(crop, source_size) and is_approved_design_source:
                issues.append(Issue(
                    "full_screen_design_used_as_runtime_background",
                    "A complete approved UI mockup cannot be used as the runtime environment background.",
                    name,
                    str(source_file) if source_file else None,
                ))
            if not clean_environment:
                issues.append(Issue("environment_background_source_not_clean", "Environment background must declare cleanEnvironmentOnly=true.", name))
            occlusion_policy = str(isolation.get("occlusionPolicy") or "") if isolation else ""
            if source_mode == "approved_design_slice" and occlusion_policy in {"remove_ui", "reconstruct_hidden", "inpaint_required"}:
                issues.append(Issue("crop_claims_occlusion_reconstruction", "A design crop cannot remove UI or reconstruct hidden environment pixels.", name))

        if role in ISOLATED_ROLES:
            if not isolation or isolation.get("forbidNeighborPixels") is not True:
                issues.append(Issue("isolated_asset_neighbor_pixels_not_forbidden", "Isolated subject/icon must set forbidNeighborPixels=true.", name))
            if not isolation or isolation.get("sourceRegionContainsOnlyAsset") is not True:
                issues.append(Issue("approved_design_slice_not_self_contained", "Source region must contain only the intended isolated asset.", name))
            requires_alpha = not isolation or isolation.get("requiresTransparentBackground") is not False
            if requires_alpha:
                if asset.get("transparent") is not True:
                    issues.append(Issue("isolated_asset_manifest_not_transparent", "Transparent isolated assets must set asset.transparent=true.", name))
                if output_required(stage):
                    if metrics is None or metrics["transparentRatio"] < 0.005:
                        issues.append(Issue("isolated_asset_requires_transparency", "Usable transparent pixels were not detected.", name, str(output_file) if output_file else None))
                    elif metrics["edgeOpaqueRatio"] > 0.98 and metrics["opaqueRatio"] > 0.98 and not (isolation and isolation.get("intentionalPlateApproved") is True):
                        issues.append(Issue("isolated_asset_opaque_rectangle", "Asset has screenshot-like opaque rectangular edges.", name, str(output_file)))

        if role in DYNAMIC_SKIN_ROLES:
            if not isolation or isolation.get("forbidBakedText") is not True:
                issues.append(Issue("dynamic_component_asset_allows_baked_text", "Dynamic frame/skin assets must set forbidBakedText=true.", name))
            if not isolation or isolation.get("containsBakedText") is not False:
                issues.append(Issue("asset_isolation_baked_text_not_reviewed", "Review must explicitly declare containsBakedText=false.", name))
            if not isolation or isolation.get("containsDynamicChildContent") is not False:
                issues.append(Issue("asset_contains_dynamic_child_content", "Review must explicitly declare containsDynamicChildContent=false.", name))

        requires_transform = role in ISOLATED_ROLES or role == "environment_background" or bool(
            isolation and isolation.get("requiresTransparentBackground") is True
        )
        if source_mode == "approved_design_slice" and requires_transform and plain_crop_scripts:
            issues.append(Issue(
                "plain_rectangular_crop_used_for_isolated_asset",
                "Project uses plain crop logic for an asset that requires isolation, alpha extraction, cleanup, or reconstruction.",
                name,
                ", ".join(str(path.relative_to(root)) for path in plain_crop_scripts),
            ))

        if isinstance(slice_entry, dict):
            extraction_mode = str(slice_entry.get("extractionMode") or "")
            reason = str(slice_entry.get("reason") or "").lower()
            claims_transform = any(token in reason for token in (
                "clean environment", "without ui", "without heroes", "transparent", "separate text",
                "not direct crop", "remove", "reconstruct", "isolate",
            ))
            if extraction_mode in {"from_sheet", "crop", "slice_static"} and claims_transform:
                issues.append(Issue(
                    "slice_plan_claims_unimplemented_isolation",
                    "Slice plan claims cleanup/isolation that a direct rectangular crop does not implement.",
                    name,
                    str(root / "specs" / "slice_plan.json"),
                ))

        checked.append({
            "asset": name,
            "role": role or None,
            "declaredRole": declared_role or None,
            "inferredRole": inferred_role,
            "sourceMode": source_mode or None,
            "sourceFile": str(source_file) if source_file else None,
            "approvedDesignSource": is_approved_design_source,
            "crop": list(crop) if crop else None,
            "outputFile": str(output_file) if output_file else None,
            "alphaMetrics": metrics,
        })

    return build_report(root, stage, manifest_path, checked, issues, plain_crop_scripts)


def build_report(
    root: Path,
    stage: str,
    manifest_path: Path | None,
    checked: list[dict[str, Any]],
    issues: list[Issue],
    scripts: list[Path],
) -> dict[str, Any]:
    issue_values = [asdict(item) for item in issues]
    errors = [item for item in issue_values if item["severity"] == "error"]
    warnings = [item for item in issue_values if item["severity"] == "warning"]
    return {
        "validator": "asset_isolation",
        "root": str(root),
        "stage": stage,
        "manifest": str(manifest_path) if manifest_path else None,
        "ok": not errors,
        "status": "PASS" if not errors else "FAIL",
        "applicable": True,
        "asset_isolation_checked": True,
        "checkedAssets": checked,
        "plainCropScripts": [str(path) for path in scripts],
        "errors": errors,
        "warnings": warnings,
        "issues": issue_values,
        "summary": {
            "assetsChecked": len(checked),
            "errors": len(errors),
            "warnings": len(warnings),
        },
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Asset Isolation Report",
        "",
        f"- Status: **{report['status']}**",
        f"- Stage: `{report['stage']}`",
        f"- Assets checked: {report['summary']['assetsChecked']}",
        f"- Errors: {report['summary']['errors']}",
        f"- Warnings: {report['summary']['warnings']}",
        "",
        "## Issues",
        "",
    ]
    if not report["issues"]:
        lines.append("- None")
    else:
        for item in report["issues"]:
            subject = f" `{item['asset']}`" if item.get("asset") else ""
            location = f" ({item['path']})" if item.get("path") else ""
            lines.append(f"- **{item['code']}**{subject}: {item['message']}{location}")
    lines.extend([
        "",
        "## Checked assets",
        "",
        "| Asset | Role | Source mode | Approved design source | Output |",
        "|---|---|---|---|---|",
    ])
    for item in report["checkedAssets"]:
        lines.append(
            f"| {item['asset']} | {item.get('role') or ''} | {item.get('sourceMode') or ''} | "
            f"{item.get('approvedDesignSource')} | {item.get('outputFile') or ''} |"
        )
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

    report = validate(args.root.resolve(), args.stage, args.xml_dir.resolve() if args.xml_dir else None)
    out = args.out or args.root / "reports" / "asset_isolation_report.json"
    report_md = args.report_md or args.root / "reports" / "asset_isolation_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, report_md)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
