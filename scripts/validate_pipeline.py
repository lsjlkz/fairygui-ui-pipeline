#!/usr/bin/env python3
"""Validate FairyGUI UI pipeline manifest and ID registry files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from check_design_approval import validate as validate_design_approval_gate
from image_metadata import ImageMetadataError, read_image_metadata
from validate_visual_part_coverage import validate as validate_visual_part_coverage


NAME_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
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


def load_json(path: Path) -> tuple[Any, str | None]:
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            return json.load(f), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)


def add(report: dict[str, Any], level: str, message: str, path: str = "") -> None:
    report[level].append({"path": path, "message": message})


def expect(condition: bool, report: dict[str, Any], message: str, path: str) -> None:
    if not condition:
        add(report, "errors", message, path)


def warn(condition: bool, report: dict[str, Any], message: str, path: str) -> None:
    if not condition:
        add(report, "warnings", message, path)


def is_pair(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(v, int) and v > 0 for v in value)
    )


def validate_manifest(manifest: dict[str, Any], report: dict[str, Any]) -> None:
    expect(isinstance(manifest.get("version"), str), report, "version is required", "version")
    expect(isinstance(manifest.get("screen"), str), report, "screen is required", "screen")
    expect(is_pair(manifest.get("resolution")), report, "resolution must be [width,height]", "resolution")

    production = manifest.get("production", {})
    expect(isinstance(production, dict), report, "production must be an object", "production")
    generate_visual_assets = False
    requires_visual_reference = False
    generate_full_screen_design = False
    requires_design_approval = False
    if isinstance(production, dict):
        generate_full_screen_design = production.get("generateFullScreenDesign") is True
        requires_design_approval = production.get("requiresDesignApproval") is True
        generate_visual_assets = production.get("generateVisualAssets") is True
        requires_visual_reference = production.get("requiresVisualReference") is True
        if generate_full_screen_design:
            expect(requires_design_approval, report, "full-screen design generation must require explicit design approval", "production.requiresDesignApproval")
            expect(production.get("requiresVisualPartCoverage") is True, report, "full-screen design generation must require visual-part coverage", "production.requiresVisualPartCoverage")
        if generate_visual_assets:
            expect(requires_visual_reference, report, "visual asset generation must require a visual reference", "production.requiresVisualReference")

    references = manifest.get("referenceImages", [])
    expect(isinstance(references, list), report, "referenceImages must be a list", "referenceImages")
    primary_count = 0
    if isinstance(references, list):
        for i, reference in enumerate(references):
            base = f"referenceImages[{i}]"
            expect(isinstance(reference, dict), report, "reference image must be an object", base)
            if not isinstance(reference, dict):
                continue
            expect(isinstance(reference.get("file"), str) and bool(reference.get("file")), report, "reference file is required", f"{base}.file")
            expect(reference.get("role") in REFERENCE_ROLES, report, "reference role is invalid", f"{base}.role")
            expect(is_pair(reference.get("resolution")), report, "reference resolution must be [width,height]", f"{base}.resolution")
            expect(isinstance(reference.get("isPrimary"), bool), report, "reference isPrimary must be boolean", f"{base}.isPrimary")
            if reference.get("isPrimary") is True:
                primary_count += 1
            allowed_uses = reference.get("allowedUses")
            expect(isinstance(allowed_uses, list) and bool(allowed_uses), report, "reference allowedUses must be a non-empty list", f"{base}.allowedUses")
            if isinstance(allowed_uses, list):
                for use_index, use in enumerate(allowed_uses):
                    expect(use in REFERENCE_USES, report, "reference allowed use is invalid", f"{base}.allowedUses[{use_index}]")
    if generate_visual_assets or requires_visual_reference:
        expect(bool(references), report, "visual asset generation requires at least one reference image", "referenceImages")
        expect(primary_count >= 1, report, "visual asset generation requires a primary reference image", "referenceImages")
    warn(primary_count <= 1, report, "multiple primary references require an explicit blending rule", "referenceImages")

    package = manifest.get("package", {})
    expect(isinstance(package, dict), report, "package must be an object", "package")
    package_output_path: str | None = None
    if isinstance(package, dict):
        name = package.get("name")
        expect(isinstance(name, str) and bool(name), report, "package.name is required", "package.name")
        if isinstance(name, str):
            warn(bool(NAME_RE.match(name)), report, "package.name should be lowercase snake_case", "package.name")
        output_path = package.get("outputPath")
        expect(isinstance(output_path, str) and bool(output_path), report, "package.outputPath is required", "package.outputPath")
        if isinstance(output_path, str) and output_path:
            package_output_path = str(PurePosixPath(output_path.replace("\\", "/"))).strip("/")

    sheets = manifest.get("sheets", [])
    assets = manifest.get("assets", [])
    expect(isinstance(sheets, list), report, "sheets must be a list", "sheets")
    expect(isinstance(assets, list), report, "assets must be a list", "assets")

    sheet_names: set[str] = set()
    sheet_capacities: dict[str, int] = {}
    sheet_dimensions: dict[str, tuple[int, int]] = {}
    sheet_items: dict[str, list[str]] = {}
    if isinstance(sheets, list):
        for i, sheet in enumerate(sheets):
            base = f"sheets[{i}]"
            expect(isinstance(sheet, dict), report, "sheet must be an object", base)
            if not isinstance(sheet, dict):
                continue
            name = sheet.get("name")
            expect(isinstance(name, str) and bool(name), report, "sheet.name is required", f"{base}.name")
            if isinstance(name, str):
                warn(bool(NAME_RE.match(name)), report, "sheet.name should be lowercase snake_case", f"{base}.name")
                expect(name not in sheet_names, report, "duplicate sheet.name", f"{base}.name")
                sheet_names.add(name)
            rows = sheet.get("rows")
            cols = sheet.get("cols")
            expect(isinstance(rows, int) and rows > 0, report, "sheet.rows must be a positive integer", f"{base}.rows")
            expect(isinstance(cols, int) and cols > 0, report, "sheet.cols must be a positive integer", f"{base}.cols")
            expect(is_pair(sheet.get("cellSize")), report, "sheet.cellSize must be [width,height]", f"{base}.cellSize")
            if isinstance(name, str) and isinstance(rows, int) and isinstance(cols, int):
                sheet_capacities[name] = rows * cols
                sheet_dimensions[name] = (rows, cols)
            items = sheet.get("items", [])
            expect(isinstance(items, list), report, "sheet.items must be a list", f"{base}.items")
            if isinstance(name, str) and isinstance(items, list):
                sheet_items[name] = [item for item in items if isinstance(item, str)]
                if name in sheet_capacities:
                    expect(len(items) <= sheet_capacities[name], report, "sheet item count exceeds rows*cols", f"{base}.items")

    asset_names: set[str] = set()
    cell_claims: set[tuple[str, int, int]] = set()
    if isinstance(assets, list):
        for i, asset in enumerate(assets):
            base = f"assets[{i}]"
            expect(isinstance(asset, dict), report, "asset must be an object", base)
            if not isinstance(asset, dict):
                continue
            name = asset.get("name")
            expect(isinstance(name, str) and bool(name), report, "asset.name is required", f"{base}.name")
            if isinstance(name, str):
                warn(bool(NAME_RE.match(name)), report, "asset.name should be lowercase snake_case", f"{base}.name")
                expect(name not in asset_names, report, "duplicate asset.name", f"{base}.name")
                asset_names.add(name)
            expect(isinstance(asset.get("file"), str) and bool(asset.get("file")), report, "asset.file is required", f"{base}.file")
            fgui = asset.get("fgui", {})
            file_value = asset.get("file")
            extension = PurePosixPath(file_value.replace("\\", "/")).suffix.lower() if isinstance(file_value, str) else ""
            resource_type = fgui.get("resourceType") if isinstance(fgui, dict) else None
            is_bitmap = resource_type in {"image", "atlas", "movieclip"} or extension in {".png", ".jpg", ".jpeg", ".webp"}
            if is_bitmap:
                source_size = asset.get("sourcePixelSize")
                display_size = asset.get("displaySize")
                scale_policy = asset.get("scalePolicy")
                render_mode = asset.get("renderMode")
                package_relative_file = asset.get("packageRelativeFile")
                expect(
                    isinstance(package_relative_file, str) and bool(package_relative_file),
                    report,
                    "bitmap asset.packageRelativeFile is required",
                    f"{base}.packageRelativeFile",
                )
                if isinstance(package_relative_file, str) and package_relative_file:
                    package_relative_raw = package_relative_file.replace("\\", "/")
                    package_relative_path = PurePosixPath(package_relative_raw)
                    package_relative_normalized = str(package_relative_path).lstrip("./")
                    expect(
                        not package_relative_raw.startswith("/")
                        and not package_relative_path.is_absolute()
                        and ".." not in package_relative_path.parts,
                        report,
                        "asset.packageRelativeFile must be a safe package-relative path",
                        f"{base}.packageRelativeFile",
                    )
                    if package_output_path and isinstance(file_value, str):
                        expected_project_file = str(PurePosixPath(package_output_path) / PurePosixPath(package_relative_normalized))
                        actual_project_file = str(PurePosixPath(file_value.replace("\\", "/"))).lstrip("./")
                        expect(
                            actual_project_file == expected_project_file,
                            report,
                            f"asset.file must equal package.outputPath/packageRelativeFile: expected={expected_project_file}",
                            f"{base}.file",
                        )
                expect(is_pair(source_size), report, "asset.sourcePixelSize must be [width,height]", f"{base}.sourcePixelSize")
                expect(is_pair(display_size), report, "asset.displaySize must be [width,height]", f"{base}.displaySize")
                expect(scale_policy in SCALE_POLICIES, report, "asset.scalePolicy is invalid", f"{base}.scalePolicy")
                expect(render_mode in RENDER_MODES, report, "asset.renderMode is invalid", f"{base}.renderMode")
                if scale_policy in RENDER_MODES_BY_POLICY:
                    expect(render_mode in RENDER_MODES_BY_POLICY[scale_policy], report, "asset.renderMode does not match scalePolicy", f"{base}.renderMode")
                if "size" in asset:
                    warn(False, report, "asset.size is legacy-only; use sourcePixelSize and displaySize", f"{base}.size")
                if is_pair(source_size) and is_pair(display_size) and scale_policy == "pixel_exact":
                    expect(source_size == display_size, report, "pixel_exact requires sourcePixelSize == displaySize", base)
                if scale_policy == "nine_slice":
                    expect(render_mode == "nine_slice", report, "nine_slice scalePolicy requires renderMode=nine_slice", f"{base}.renderMode")
                    grid = asset.get("nineSliceGrid")
                    valid_grid = (
                        isinstance(grid, list) and len(grid) == 4
                        and all(isinstance(v, int) and v >= 0 for v in grid)
                        and grid[2] > 0 and grid[3] > 0
                    )
                    expect(valid_grid, report, "nineSliceGrid must be [x,y,width,height]", f"{base}.nineSliceGrid")
                    if valid_grid and is_pair(source_size):
                        expect(grid[0] + grid[2] <= source_size[0] and grid[1] + grid[3] <= source_size[1], report, "nineSliceGrid exceeds sourcePixelSize", f"{base}.nineSliceGrid")
                expect(isinstance(asset.get("transparent"), bool), report, "asset.transparent must be boolean", f"{base}.transparent")
                expect("pivot" in asset, report, "asset.pivot is required", f"{base}.pivot")

            sheet_name = asset.get("sheet")
            if sheet_name is not None:
                expect(sheet_name in sheet_names, report, "asset.sheet does not exist in sheets", f"{base}.sheet")
                cell = asset.get("cell")
                expect(
                    isinstance(cell, list)
                    and len(cell) == 2
                    and all(isinstance(v, int) and v >= 0 for v in cell),
                    report,
                    "asset.cell must be [row,col]",
                    f"{base}.cell",
                )
                if isinstance(cell, list) and len(cell) == 2 and all(isinstance(v, int) for v in cell):
                    claim = (str(sheet_name), cell[0], cell[1])
                    expect(claim not in cell_claims, report, "duplicate sheet cell assignment", f"{base}.cell")
                    cell_claims.add(claim)
                    dimensions = sheet_dimensions.get(str(sheet_name))
                    if dimensions:
                        rows, cols = dimensions
                        expect(cell[0] < rows and cell[1] < cols, report, "asset.cell is outside sheet rows/cols", f"{base}.cell")

            expect(isinstance(fgui, dict), report, "asset.fgui must be an object", f"{base}.fgui")
            if isinstance(fgui, dict):
                expect(isinstance(fgui.get("resourceType"), str), report, "asset.fgui.resourceType is required", f"{base}.fgui.resourceType")
                node_type = fgui.get("nodeType")
                if node_type is not None:
                    warn(node_type in {"image", "loader", "component", "button", "list", "text", "graph"}, report, "unknown fgui.nodeType", f"{base}.fgui.nodeType")

    for sheet_name, items in sheet_items.items():
        for item_index, item_name in enumerate(items):
            expect(item_name in asset_names, report, "sheet item does not exist in assets", f"sheets.{sheet_name}.items[{item_index}]")


def validate_registry(registry: dict[str, Any], report: dict[str, Any]) -> None:
    packages = registry.get("packages", {})
    expect(isinstance(packages, dict), report, "packages must be an object", "packages")
    if not isinstance(packages, dict):
        return

    package_ids: set[str] = set()
    resource_ids: set[str] = set()
    for package_name, package in packages.items():
        base = f"packages.{package_name}"
        warn(bool(NAME_RE.match(package_name)), report, "registry package key should be lowercase snake_case", base)
        expect(isinstance(package, dict), report, "package registry entry must be an object", base)
        if not isinstance(package, dict):
            continue
        package_id = package.get("id") or package.get("packageId")
        package_id_path = f"{base}.id" if "id" in package else f"{base}.packageId"
        expect(
            isinstance(package_id, str) and bool(PACKAGE_ID_RE.fullmatch(package_id or "")),
            report,
            "package id must be exactly 8 lowercase alphanumeric characters",
            package_id_path,
        )
        if isinstance(package_id, str):
            expect(package_id not in package_ids, report, "duplicate package id", package_id_path)
            package_ids.add(package_id)

        resources = package.get("resources", {})
        expect(isinstance(resources, dict), report, "resources must be an object", f"{base}.resources")
        if isinstance(resources, dict):
            local_ids: set[str] = set()
            for resource_name, resource_id in resources.items():
                expect(
                    isinstance(resource_id, str) and bool(RESOURCE_ID_RE.fullmatch(resource_id or "")),
                    report,
                    "resource id must be 2-16 lowercase alphanumeric characters",
                    f"{base}.resources.{resource_name}",
                )
                if isinstance(resource_id, str):
                    expect(resource_id not in local_ids, report, "duplicate resource id within package", f"{base}.resources.{resource_name}")
                    local_ids.add(resource_id)
                    resource_ids.add(f"{package_name}:{resource_id}")

        instances = package.get("instances", {})
        if instances is not None:
            expect(isinstance(instances, dict), report, "instances must be an object", f"{base}.instances")
            if isinstance(instances, dict):
                seen_instances: set[str] = set()
                for instance_path, instance_id in instances.items():
                    expect(isinstance(instance_id, str) and bool(instance_id), report, "instance id must be a non-empty string", f"{base}.instances.{instance_path}")
                    if isinstance(instance_id, str):
                        expect(instance_id not in seen_instances, report, "duplicate instance id within package", f"{base}.instances.{instance_path}")
                        seen_instances.add(instance_id)


def normalize_relative_path(value: str) -> Path:
    normalized = str(PurePosixPath(value.replace("\\", "/"))).lstrip("./")
    return Path(*PurePosixPath(normalized).parts)


def validate_project_image_files(root: Path, manifest: dict[str, Any], report: dict[str, Any]) -> None:
    references = manifest.get("referenceImages", [])
    if isinstance(references, list):
        for index, reference in enumerate(references):
            if not isinstance(reference, dict):
                continue
            file_name = reference.get("file")
            declared = reference.get("resolution")
            if not isinstance(file_name, str) or not file_name:
                continue
            path = root / normalize_relative_path(file_name)
            if not path.is_file():
                add(report, "errors", "reference image file not found", f"referenceImages[{index}].file={path}")
                continue
            try:
                metadata = read_image_metadata(path)
            except (OSError, ImageMetadataError) as exc:
                add(report, "errors", f"reference image metadata cannot be read: {exc}", f"referenceImages[{index}].file")
                continue
            actual = [metadata["width"], metadata["height"]]
            expect(declared == actual, report, f"reference resolution does not match actual pixels: actual={actual}", f"referenceImages[{index}].resolution")

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
        if not is_bitmap:
            continue
        declared = asset.get("sourcePixelSize")
        if not isinstance(file_name, str) or not file_name:
            continue
        path = root / normalize_relative_path(file_name)
        if not path.is_file():
            add(report, "errors", "asset image file not found", f"assets[{index}].file={path}")
            continue
        try:
            metadata = read_image_metadata(path)
        except (OSError, ImageMetadataError) as exc:
            add(report, "errors", f"asset image metadata cannot be read: {exc}", f"assets[{index}].file")
            continue
        actual = [metadata["width"], metadata["height"]]
        expect(declared == actual, report, f"asset sourcePixelSize does not match actual pixels: actual={actual}", f"assets[{index}].sourcePixelSize")
        if asset.get("transparent") is True and metadata.get("format") == "png":
            expect(metadata.get("hasAlphaCapability") is True, report, "transparent PNG is not alpha-capable", f"assets[{index}].transparent")


def validate_alignment(manifest: dict[str, Any], registry: dict[str, Any], report: dict[str, Any]) -> None:
    package = manifest.get("package", {})
    package_name = package.get("name") if isinstance(package, dict) else None
    packages = registry.get("packages", {})
    if not isinstance(package_name, str) or not isinstance(packages, dict):
        return

    registry_package = packages.get(package_name)
    expect(isinstance(registry_package, dict), report, "manifest package is missing from registry", f"packages.{package_name}")
    if not isinstance(registry_package, dict):
        return

    resources = registry_package.get("resources", {})
    if not isinstance(resources, dict):
        return

    registry_names: set[str] = set()
    for resource_name in resources:
        normalized = str(resource_name).replace("\\", "/")
        file_name = normalized.rsplit("/", 1)[-1]
        stem = file_name.rsplit(".", 1)[0]
        registry_names.update({normalized, file_name, stem})

    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        return
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            continue
        candidates: set[str] = set()
        name = asset.get("name")
        file_path = asset.get("file")
        if isinstance(name, str):
            candidates.add(name)
        if isinstance(file_path, str):
            file_name = file_path.replace("\\", "/").rsplit("/", 1)[-1]
            candidates.update({file_name, file_name.rsplit(".", 1)[0]})
        expect(bool(candidates.intersection(registry_names)), report, "manifest asset is missing from registry.resources", f"assets[{index}]")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, help="UIProduction root directory")
    parser.add_argument("--manifest", type=Path, help="asset_manifest.json path")
    parser.add_argument("--registry", type=Path, help="fgui_id_registry.json path")
    parser.add_argument("--out", type=Path, help="report output path")
    parser.add_argument("--skip-image-metadata", action="store_true", help="Skip reference/asset file existence and pixel-size checks")
    args = parser.parse_args()

    manifest_path = args.manifest
    registry_path = args.registry
    if args.root:
        manifest_path = manifest_path or args.root / "manifests" / "asset_manifest.json"
        registry_path = registry_path or args.root / "manifests" / "fgui_id_registry.json"

    report: dict[str, Any] = {
        "ok": True,
        "errors": [],
        "warnings": [],
        "summary": {"assets": 0, "sheets": 0, "packages": 0},
    }

    manifest: dict[str, Any] = {}
    registry: dict[str, Any] = {}

    if manifest_path and manifest_path.exists():
        loaded_manifest, manifest_error = load_json(manifest_path)
        if manifest_error or not isinstance(loaded_manifest, dict):
            add(report, "errors", f"manifest JSON is invalid: {manifest_error or 'top-level value must be an object'}", str(manifest_path))
        else:
            manifest = loaded_manifest
            validate_manifest(manifest, report)
            report["summary"]["assets"] = len(manifest.get("assets", []))
            report["summary"]["sheets"] = len(manifest.get("sheets", []))
    else:
        add(report, "errors", "manifest file not found", str(manifest_path or ""))

    if registry_path and registry_path.exists():
        loaded_registry, registry_error = load_json(registry_path)
        if registry_error or not isinstance(loaded_registry, dict):
            add(report, "errors", f"registry JSON is invalid: {registry_error or 'top-level value must be an object'}", str(registry_path))
        else:
            registry = loaded_registry
            validate_registry(registry, report)
            packages = registry.get("packages", {})
            report["summary"]["packages"] = len(packages) if isinstance(packages, dict) else 0
    else:
        add(report, "warnings", "registry file not found; create it before XML generation", str(registry_path or ""))

    if manifest and registry:
        validate_alignment(manifest, registry, report)

    if manifest:
        production = manifest.get("production", {})
        requires_design_approval = isinstance(production, dict) and (
            production.get("generateFullScreenDesign") is True
            or production.get("requiresDesignApproval") is True
        )
        if requires_design_approval:
            project_root = args.root.resolve() if args.root else (manifest_path.parent.parent.resolve() if manifest_path else None)
            if project_root:
                design_report = validate_design_approval_gate(project_root, "asset_planning")
                for item in design_report.get("blockers", []):
                    add(
                        report,
                        "errors",
                        "design approval: " + item.get("message", "blocked"),
                        item.get("path", str(project_root)),
                    )
                for item in design_report.get("warnings", []):
                    add(
                        report,
                        "warnings",
                        "design approval: " + item.get("message", "warning"),
                        item.get("path", str(project_root)),
                    )

                visual_part_report = validate_visual_part_coverage(project_root, "asset_planning")
                for item in visual_part_report.get("errors", []):
                    add(
                        report,
                        "errors",
                        "visual part coverage: " + item.get("message", "invalid"),
                        item.get("path", str(project_root)),
                    )
                for item in visual_part_report.get("warnings", []):
                    add(
                        report,
                        "warnings",
                        "visual part coverage: " + item.get("message", "warning"),
                        item.get("path", str(project_root)),
                    )

    if manifest and not args.skip_image_metadata:
        project_root = args.root.resolve() if args.root else (manifest_path.parent.parent.resolve() if manifest_path else None)
        if project_root:
            validate_project_image_files(project_root, manifest, report)
    elif manifest and args.skip_image_metadata:
        add(report, "warnings", "image metadata validation was skipped", "--skip-image-metadata")

    report["ok"] = not report["errors"]

    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
