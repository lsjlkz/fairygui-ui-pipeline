#!/usr/bin/env python3
"""Validate that an approved production preview uses the exact runtime assets."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

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
FIDELITY_MODES = {
    "exact_production_composite",
    "direct_source_assets",
    "reference_reinterpretation",
}
EXACT_MODES = {"exact_production_composite", "direct_source_assets"}
PREVIEW_USAGES = {"exact_file", "exact_crop", "not_visible"}
DESIGN_RELATIONS = {"exact_approved_source", "exact_provided_source", "reference_reconstruction"}
DERIVATION_MODES = {"exact_file", "exact_crop", "deterministic_transform"}
HUMAN_CONFIRMATIONS = {"user_confirmation", "manual_review"}
HUMAN_RECORDERS = {"user", "human_reviewer"}


@dataclass
class Issue:
    code: str
    message: str
    path: str | None = None
    asset: str | None = None
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


def normalize_manifest_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return str(PurePosixPath(value.replace("\\", "/"))).lstrip("./")


def registered_sheet_files(manifest: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    sheets = manifest.get("sheets")
    if not isinstance(sheets, list):
        return result
    for sheet in sheets:
        if not isinstance(sheet, dict):
            continue
        for key in ("file", "sourceFile", "previewFile", "outputFile"):
            normalized = normalize_manifest_path(sheet.get(key))
            if normalized:
                result.add(normalized)
    return result


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


def exact_crop_matches(source: Path, runtime: Path, crop: Any) -> bool | None:
    if Image is None or ImageChops is None:
        return None
    if not (isinstance(crop, list) and len(crop) == 4 and all(isinstance(v, int) for v in crop)):
        return False
    x, y, width, height = crop
    if width <= 0 or height <= 0:
        return False
    try:
        with Image.open(source) as source_image, Image.open(runtime) as runtime_image:
            expected = source_image.convert("RGBA").crop((x, y, x + width, y + height))
            actual = runtime_image.convert("RGBA")
            if expected.size != actual.size:
                return False
            return ImageChops.difference(expected, actual).getbbox() is None
    except Exception:
        return False


def bitmap_assets(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        return result
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        file_value = asset.get("file")
        fgui = asset.get("fgui") if isinstance(asset.get("fgui"), dict) else {}
        extension = PurePosixPath(str(file_value or "").replace("\\", "/")).suffix.lower()
        if fgui.get("resourceType") in {"image", "atlas", "movieclip"} or extension in {".png", ".jpg", ".jpeg", ".webp"}:
            result.append(asset)
    return result


def build_report(
    root: Path,
    stage: str,
    checked: list[dict[str, Any]],
    issues: list[Issue],
    applicable: bool = True,
) -> dict[str, Any]:
    values = [asdict(item) for item in issues]
    errors = [item for item in values if item["severity"] == "error"]
    warnings = [item for item in values if item["severity"] == "warning"]
    return {
        "validator": "production_preview_lineage",
        "root": str(root),
        "stage": stage,
        "applicable": applicable,
        "production_preview_lineage_checked": applicable,
        "ok": not errors,
        "status": "PASS" if not errors else "FAIL",
        "checkedAssets": checked,
        "errors": errors,
        "warnings": warnings,
        "issues": values,
        "summary": {
            "assetsChecked": len(checked),
            "errors": len(errors),
            "warnings": len(warnings),
        },
    }


def validate(root: Path, stage: str = "asset_planning") -> dict[str, Any]:
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
    gate = production.get("requiresProductionPreviewLineage") is True
    if full_screen and not gate:
        issues.append(Issue(
            "production_preview_lineage_not_required",
            "Full-screen projects must set production.requiresProductionPreviewLineage=true.",
            str(manifest_path),
        ))
    if not full_screen and not gate:
        report = build_report(root, stage, checked, issues, applicable=False)
        report["status"] = "SKIPPED"
        report["production_preview_lineage_checked"] = False
        return report

    lineage_path = root / "specs" / "production_preview_lineage.json"
    try:
        lineage = read_json(lineage_path)
    except ValueError as exc:
        issues.append(Issue("production_preview_lineage_invalid", str(exc), str(lineage_path)))
        return build_report(root, stage, checked, issues)
    if not lineage:
        issues.append(Issue(
            "production_preview_lineage_missing",
            "specs/production_preview_lineage.json is required.",
            str(lineage_path),
        ))
        return build_report(root, stage, checked, issues)

    if lineage.get("blockingForXml") is True:
        issues.append(Issue("production_preview_lineage_blocks_xml", "Lineage file sets blockingForXml=true.", str(lineage_path)))

    mode = str(lineage.get("fidelityMode") or "")
    if mode not in FIDELITY_MODES:
        issues.append(Issue("production_preview_fidelity_mode_invalid", f"Unsupported fidelityMode: {mode!r}.", str(lineage_path)))
    if mode == "reference_reinterpretation" and STAGE_ORDER.get(stage, 50) >= STAGE_ORDER["fairygui_assembly"]:
        issues.append(Issue(
            "reference_reinterpretation_cannot_be_final_preview",
            "Final production preview must use exact production assets, not a new image-model reinterpretation.",
            str(lineage_path),
        ))

    preview = lineage.get("productionPreview") if isinstance(lineage.get("productionPreview"), dict) else {}
    preview_path = resolve(root, preview.get("file"))
    renderer_path = resolve(root, preview.get("rendererScript"))
    approval_path = resolve(root, preview.get("approvalRecord"))
    file_checks_required = STAGE_ORDER.get(stage, 50) >= STAGE_ORDER["fairygui_assembly"]

    if not isinstance(preview.get("file"), str) or not preview.get("file"):
        issues.append(Issue("production_preview_file_missing", "productionPreview.file is required.", str(lineage_path)))
    if mode in EXACT_MODES and preview.get("usesProductionAssets") is not True:
        issues.append(Issue(
            "approved_preview_not_composed_from_production_assets",
            "Exact production preview must declare usesProductionAssets=true.",
            str(lineage_path),
        ))
    if not isinstance(preview.get("rendererScript"), str) or not preview.get("rendererScript"):
        issues.append(Issue("production_preview_renderer_missing", "productionPreview.rendererScript is required.", str(lineage_path)))
    if not isinstance(preview.get("approvalRecord"), str) or not preview.get("approvalRecord"):
        issues.append(Issue("production_preview_approval_target_missing", "productionPreview.approvalRecord is required.", str(lineage_path)))

    renderer_text = ""
    if renderer_path and renderer_path.is_file():
        renderer_text = renderer_path.read_text(encoding="utf-8", errors="ignore")
    elif file_checks_required:
        issues.append(Issue("production_preview_renderer_file_missing", "Preview renderer script does not exist.", str(renderer_path)))

    current_preview_hash: str | None = None
    if file_checks_required:
        if preview_path is None or not preview_path.is_file():
            issues.append(Issue("production_preview_output_missing", "Approved production preview image does not exist.", str(preview_path)))
        else:
            current_preview_hash = sha256_file(preview_path)
            declared_hash = str(preview.get("sha256") or "")
            if not declared_hash:
                issues.append(Issue("production_preview_hash_missing", "productionPreview.sha256 is required after assembly.", str(lineage_path)))
            elif declared_hash != current_preview_hash:
                issues.append(Issue("production_preview_hash_mismatch", "Production preview bytes changed after lineage freeze.", str(preview_path)))

    entries = lineage.get("assets")
    if not isinstance(entries, list):
        issues.append(Issue("production_preview_assets_invalid", "lineage.assets must be an array.", str(lineage_path)))
        entries = []
    by_name: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            issues.append(Issue("production_preview_asset_invalid", f"assets[{index}] must be an object.", str(lineage_path)))
            continue
        name = str(entry.get("assetName") or "")
        if not name:
            issues.append(Issue("production_preview_asset_name_missing", f"assets[{index}].assetName is required.", str(lineage_path)))
            continue
        if name in by_name:
            issues.append(Issue("production_preview_asset_duplicate", f"Duplicate assetName: {name}.", str(lineage_path), name))
        by_name[name] = entry

    manifest_assets = bitmap_assets(manifest)
    sheet_files = registered_sheet_files(manifest)
    for asset in manifest_assets:
        name = str(asset.get("name") or "")
        entry = by_name.get(name)
        if entry is None:
            issues.append(Issue(
                "runtime_asset_missing_from_preview_lineage",
                "Every runtime bitmap must have one lineage entry.",
                str(lineage_path),
                name,
            ))
            continue
        usage = str(entry.get("previewUsage") or "")
        if usage not in PREVIEW_USAGES:
            issues.append(Issue("production_preview_usage_invalid", f"Unsupported previewUsage: {usage!r}.", str(lineage_path), name))
        if usage == "not_visible" and not str(entry.get("reason") or "").strip():
            issues.append(Issue("production_preview_not_visible_reason_missing", "not_visible assets require a reason.", str(lineage_path), name))

        source_lineage = entry.get("sourceLineage") if isinstance(entry.get("sourceLineage"), dict) else None
        design_relation = str(source_lineage.get("designRelation") or "") if source_lineage else ""
        derivation_mode = str(source_lineage.get("derivationMode") or "") if source_lineage else ""
        derivation_source = resolve(root, source_lineage.get("sourceFile")) if source_lineage else None
        source_hash = str(source_lineage.get("sourceSha256") or "") if source_lineage else ""
        source_crop = source_lineage.get("crop") if source_lineage else None
        transform_script = resolve(root, source_lineage.get("transformScript")) if source_lineage else None
        transform_script_hash = str(source_lineage.get("transformScriptSha256") or "") if source_lineage else ""
        if source_lineage is None:
            issues.append(Issue(
                "runtime_asset_source_lineage_missing",
                "Every runtime bitmap must declare sourceLineage.",
                str(lineage_path),
                name,
            ))
        else:
            if design_relation not in DESIGN_RELATIONS:
                issues.append(Issue(
                    "runtime_asset_design_relation_invalid",
                    f"designRelation must be one of {sorted(DESIGN_RELATIONS)}.",
                    str(lineage_path),
                    name,
                ))
            if derivation_mode not in DERIVATION_MODES:
                issues.append(Issue(
                    "runtime_asset_derivation_mode_invalid",
                    f"derivationMode must be one of {sorted(DERIVATION_MODES)}.",
                    str(lineage_path),
                    name,
                ))
            if not isinstance(source_lineage.get("sourceFile"), str) or not source_lineage.get("sourceFile"):
                issues.append(Issue("runtime_asset_derivation_source_missing", "sourceLineage.sourceFile is required.", str(lineage_path), name))
            if design_relation == "reference_reconstruction" and not str(source_lineage.get("reconstructionReason") or "").strip():
                issues.append(Issue(
                    "runtime_asset_reconstruction_reason_missing",
                    "Reference reconstruction requires a reason explaining why exact copy/crop is not possible.",
                    str(lineage_path),
                    name,
                ))
            if derivation_mode == "exact_crop" and not (
                isinstance(source_crop, list)
                and len(source_crop) == 4
                and all(isinstance(value, int) for value in source_crop)
                and source_crop[2] > 0
                and source_crop[3] > 0
            ):
                issues.append(Issue("runtime_asset_exact_crop_invalid", "exact_crop requires integer [x,y,width,height].", str(lineage_path), name))
            if derivation_mode == "deterministic_transform" and not isinstance(source_lineage.get("transformScript"), str):
                issues.append(Issue(
                    "runtime_asset_transform_script_missing",
                    "deterministic_transform requires transformScript.",
                    str(lineage_path),
                    name,
                ))

            asset_source = asset.get("assetSource") if isinstance(asset.get("assetSource"), dict) else {}
            asset_source_mode = str(asset_source.get("mode") or "")
            manifest_source_file = normalize_manifest_path(asset_source.get("sourceFile"))
            lineage_source_file = normalize_manifest_path(source_lineage.get("sourceFile"))
            manifest_crop = asset_source.get("crop")
            if manifest_source_file and lineage_source_file and manifest_source_file != lineage_source_file:
                issues.append(Issue(
                    "runtime_asset_manifest_source_mismatch",
                    f"assetSource.sourceFile and sourceLineage.sourceFile must identify the same exact source: manifest={manifest_source_file}, lineage={lineage_source_file}.",
                    str(lineage_path),
                    name,
                ))
            if manifest_crop is not None and source_crop is not None and manifest_crop != source_crop:
                issues.append(Issue(
                    "runtime_asset_manifest_crop_mismatch",
                    f"assetSource.crop and sourceLineage.crop must match exactly: manifest={manifest_crop}, lineage={source_crop}.",
                    str(lineage_path),
                    name,
                ))
            if asset_source_mode == "approved_sheet_slice":
                if not manifest_source_file:
                    issues.append(Issue(
                        "approved_sheet_source_missing",
                        "approved_sheet_slice requires assetSource.sourceFile.",
                        str(manifest_path),
                        name,
                    ))
                elif manifest_source_file not in sheet_files:
                    issues.append(Issue(
                        "approved_sheet_source_not_registered",
                        "approved_sheet_slice sourceFile must be registered in manifest.sheets.",
                        str(manifest_path),
                        name,
                    ))
                if derivation_mode not in {"exact_crop", "deterministic_transform"}:
                    issues.append(Issue(
                        "approved_sheet_derivation_mode_invalid",
                        "approved_sheet_slice must declare derivationMode=exact_crop or deterministic_transform.",
                        str(lineage_path),
                        name,
                    ))
            if asset_source_mode == "image_generation_with_reference" and design_relation != "reference_reconstruction":
                issues.append(Issue(
                    "generated_asset_must_declare_reference_reconstruction",
                    "Image-generated assets cannot claim exact approved/provided-source fidelity.",
                    str(lineage_path),
                    name,
                ))
            if asset_source_mode == "provided_bitmap" and design_relation != "exact_provided_source":
                issues.append(Issue(
                    "provided_asset_must_use_exact_source_relation",
                    "A provided production bitmap must use designRelation=exact_provided_source unless an explicit transform is recorded.",
                    str(lineage_path),
                    name,
                ))
            if asset_source_mode == "approved_design_slice" and design_relation != "exact_approved_source":
                issues.append(Issue(
                    "approved_design_slice_must_use_exact_relation",
                    "An approved-design slice must use designRelation=exact_approved_source.",
                    str(lineage_path),
                    name,
                ))

        runtime_file = str(entry.get("runtimeFile") or "")
        manifest_file = str(asset.get("file") or "")
        if runtime_file.replace("\\", "/") != manifest_file.replace("\\", "/"):
            issues.append(Issue(
                "preview_runtime_file_manifest_mismatch",
                f"runtimeFile must exactly equal manifest asset.file: {manifest_file}",
                str(lineage_path),
                name,
            ))
        runtime_path = resolve(root, runtime_file)
        current_hash: str | None = None
        if file_checks_required:
            if runtime_path is None or not runtime_path.is_file():
                issues.append(Issue("preview_runtime_asset_missing", "Runtime bitmap does not exist.", str(runtime_path), name))
            else:
                current_hash = sha256_file(runtime_path)
                frozen_hash = str(entry.get("runtimeSha256") or "")
                if not frozen_hash:
                    issues.append(Issue("preview_runtime_asset_hash_missing", "runtimeSha256 is required after assembly.", str(lineage_path), name))
                elif frozen_hash != current_hash:
                    issues.append(Issue(
                        "production_asset_regenerated_after_preview_approval",
                        "Runtime asset bytes no longer match the frozen preview lineage.",
                        str(runtime_path),
                        name,
                    ))

        if file_checks_required and source_lineage is not None:
            if derivation_source is None or not derivation_source.is_file():
                issues.append(Issue("runtime_asset_derivation_source_file_missing", "sourceLineage source file does not exist.", str(derivation_source), name))
            else:
                current_source_hash = sha256_file(derivation_source)
                if not source_hash:
                    issues.append(Issue("runtime_asset_source_hash_missing", "sourceSha256 is required after resource generation.", str(lineage_path), name))
                elif source_hash != current_source_hash:
                    issues.append(Issue("runtime_asset_source_hash_mismatch", "Source bytes changed after lineage freeze.", str(derivation_source), name))
                if runtime_path is not None and runtime_path.is_file():
                    if derivation_mode == "exact_file" and current_hash != current_source_hash:
                        issues.append(Issue(
                            "runtime_asset_exact_file_mismatch",
                            "exact_file runtime bytes must equal the declared source bytes.",
                            str(runtime_path),
                            name,
                        ))
                    elif derivation_mode == "exact_crop":
                        crop_match = exact_crop_matches(derivation_source, runtime_path, source_crop)
                        if crop_match is False:
                            issues.append(Issue(
                                "runtime_asset_exact_crop_pixel_mismatch",
                                "Runtime pixels do not equal the declared exact source crop.",
                                str(runtime_path),
                                name,
                            ))
                        elif crop_match is None:
                            issues.append(Issue(
                                "runtime_asset_exact_crop_pixel_check_unavailable",
                                "Pillow is unavailable; exact crop pixel equality was not checked.",
                                str(runtime_path),
                                name,
                                severity="warning",
                            ))
            if derivation_mode == "deterministic_transform":
                if transform_script is None or not transform_script.is_file():
                    issues.append(Issue("runtime_asset_transform_script_file_missing", "transformScript does not exist.", str(transform_script), name))
                else:
                    current_script_hash = sha256_file(transform_script)
                    if not transform_script_hash:
                        issues.append(Issue("runtime_asset_transform_script_hash_missing", "transformScriptSha256 is required.", str(lineage_path), name))
                    elif transform_script_hash != current_script_hash:
                        issues.append(Issue("runtime_asset_transform_script_hash_mismatch", "Transform script changed after lineage freeze.", str(transform_script), name))

        if usage in {"exact_file", "exact_crop"} and renderer_text:
            candidates = {name, Path(runtime_file).name, Path(runtime_file).stem}
            if not any(candidate and candidate in renderer_text for candidate in candidates):
                issues.append(Issue(
                    "runtime_asset_not_used_by_preview_renderer",
                    "Renderer script does not reference the declared visible runtime asset.",
                    str(renderer_path),
                    name,
                ))
        if usage == "exact_crop":
            source_file = resolve(root, entry.get("sourceFile"))
            crop = entry.get("crop")
            if source_file is None or not source_file.is_file():
                issues.append(Issue("preview_exact_crop_source_missing", "exact_crop requires an existing sourceFile.", str(source_file), name))
            if not (isinstance(crop, list) and len(crop) == 4 and all(isinstance(v, int) for v in crop)):
                issues.append(Issue("preview_exact_crop_invalid", "exact_crop requires integer [x,y,width,height].", str(lineage_path), name))

        checked.append({
            "asset": name,
            "previewUsage": usage or None,
            "runtimeFile": runtime_file or None,
            "currentSha256": current_hash,
            "designRelation": design_relation or None,
            "derivationMode": derivation_mode or None,
            "derivationSource": str(derivation_source) if derivation_source else None,
        })

    if file_checks_required:
        if approval_path is None or not approval_path.is_file():
            issues.append(Issue("production_preview_approval_missing", "Human production-preview approval record is required.", str(approval_path)))
        else:
            try:
                approval = read_json(approval_path)
            except ValueError as exc:
                issues.append(Issue("production_preview_approval_invalid", str(exc), str(approval_path)))
                approval = {}
            if approval.get("status") != "approved":
                issues.append(Issue("production_preview_not_approved", "Production preview status must be approved.", str(approval_path)))
            approved_file = str(approval.get("approvedFile") or "")
            if approved_file.replace("\\", "/") != str(preview.get("file") or "").replace("\\", "/"):
                issues.append(Issue("production_preview_approval_file_mismatch", "Approval does not identify the lineage preview file.", str(approval_path)))
            if current_preview_hash and approval.get("approvedFileSha256") != current_preview_hash:
                issues.append(Issue("production_preview_approval_hash_mismatch", "Approval hash does not match current preview bytes.", str(approval_path)))
            confirmation = approval.get("confirmation") if isinstance(approval.get("confirmation"), dict) else {}
            if confirmation.get("type") not in HUMAN_CONFIRMATIONS or confirmation.get("recordedBy") not in HUMAN_RECORDERS:
                issues.append(Issue("production_preview_ai_self_approval_forbidden", "Production preview approval must be human-originated.", str(approval_path)))
            approved_hashes = approval.get("approvedAssetHashes")
            if not isinstance(approved_hashes, dict):
                issues.append(Issue("production_preview_asset_hashes_missing", "Approval must freeze approvedAssetHashes.", str(approval_path)))
            else:
                for item in checked:
                    if item["currentSha256"] and approved_hashes.get(item["asset"]) != item["currentSha256"]:
                        issues.append(Issue(
                            "approved_preview_asset_hash_mismatch",
                            "Approval asset hash does not match current runtime bitmap.",
                            str(approval_path),
                            item["asset"],
                        ))

            evidence_paths = {
                "productionPreviewLineage": lineage_path,
                "typographySpec": root / "specs" / "typography_spec.json",
                "typographyRenderTrace": root / "reports" / "typography_render_trace.json",
            }
            current_evidence_hashes = {
                key: sha256_file(path) for key, path in evidence_paths.items() if path.is_file()
            }
            approved_evidence_hashes = approval.get("approvedEvidenceHashes")
            if not isinstance(approved_evidence_hashes, dict):
                issues.append(Issue(
                    "production_preview_evidence_hashes_missing",
                    "Approval must freeze production lineage and available typography evidence hashes.",
                    str(approval_path),
                ))
            else:
                for evidence_name, current_evidence_hash in current_evidence_hashes.items():
                    if approved_evidence_hashes.get(evidence_name) != current_evidence_hash:
                        issues.append(Issue(
                            "production_preview_evidence_hash_mismatch",
                            f"Approved evidence hash no longer matches {evidence_name}.",
                            str(evidence_paths[evidence_name]),
                        ))
                stale_evidence_names = sorted(set(approved_evidence_hashes) - set(current_evidence_hashes))
                for evidence_name in stale_evidence_names:
                    issues.append(Issue(
                        "production_preview_evidence_file_missing",
                        f"Previously approved evidence file is now missing: {evidence_name}.",
                        str(evidence_paths.get(evidence_name, root)),
                    ))

    return build_report(root, stage, checked, issues)


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Production Preview Lineage Report",
        "",
        f"- Status: **{report['status']}**",
        f"- Stage: `{report['stage']}`",
        f"- Assets checked: {report['summary']['assetsChecked']}",
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--stage", choices=tuple(STAGE_ORDER), default="asset_planning")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report-md", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    report = validate(root, args.stage)
    out = args.out or root / "reports" / "production_preview_lineage_report.json"
    report_md = args.report_md or root / "reports" / "production_preview_lineage_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, report_md)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
