from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_production_preview_lineage.py"
spec = importlib.util.spec_from_file_location("validate_production_preview_lineage", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class ProductionPreviewLineageTests(unittest.TestCase):
    def root(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    @staticmethod
    def codes(report: dict) -> set[str]:
        return {item["code"] for item in report["issues"]}

    def test_full_screen_requires_gate(self) -> None:
        root = self.root()
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {"generateFullScreenDesign": True},
            "assets": [],
        })
        report = module.validate(root)
        self.assertIn("production_preview_lineage_not_required", self.codes(report))

    def test_reference_reinterpretation_not_final(self) -> None:
        root = self.root()
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {"generateFullScreenDesign": True, "requiresProductionPreviewLineage": True},
            "assets": [],
        })
        write_json(root / "specs" / "production_preview_lineage.json", {
            "fidelityMode": "reference_reinterpretation",
            "productionPreview": {
                "file": "generated/preview/p.png",
                "rendererScript": "scripts/render.py",
                "approvalRecord": "reports/production_preview_approval.json",
            },
            "assets": [],
        })
        report = module.validate(root, "fairygui_assembly")
        self.assertIn("reference_reinterpretation_cannot_be_final_preview", self.codes(report))

    def test_exact_preview_freezes_runtime_hashes(self) -> None:
        root = self.root()
        art = root / "fgui_xml" / "pkg" / "art"
        art.mkdir(parents=True)
        asset = art / "icon.png"
        asset.write_bytes(b"asset-v1")
        preview = root / "generated" / "preview" / "screen.png"
        preview.parent.mkdir(parents=True)
        preview.write_bytes(b"preview-v1")
        renderer = root / "scripts" / "render.py"
        renderer.parent.mkdir()
        renderer.write_text("icon\n", encoding="utf-8")
        asset_hash = digest(asset)
        preview_hash = digest(preview)
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresProductionPreviewLineage": True,
            },
            "assets": [{
                "name": "icon",
                "file": "fgui_xml/pkg/art/icon.png",
                "assetSource": {"mode": "provided_bitmap"},
                "fgui": {"resourceType": "image"},
            }],
        })
        lineage_path = root / "specs" / "production_preview_lineage.json"
        write_json(lineage_path, {
            "fidelityMode": "exact_production_composite",
            "productionPreview": {
                "file": "generated/preview/screen.png",
                "sha256": preview_hash,
                "rendererScript": "scripts/render.py",
                "usesProductionAssets": True,
                "approvalRecord": "reports/production_preview_approval.json",
            },
            "assets": [{
                "assetName": "icon",
                "runtimeFile": "fgui_xml/pkg/art/icon.png",
                "runtimeSha256": asset_hash,
                "previewUsage": "exact_file",
                "sourceLineage": {
                    "designRelation": "exact_provided_source",
                    "derivationMode": "exact_file",
                    "sourceFile": "fgui_xml/pkg/art/icon.png",
                    "sourceSha256": asset_hash
                }
            }],
            "blockingForXml": False,
        })
        write_json(root / "reports" / "production_preview_approval.json", {
            "status": "approved",
            "approvedFile": "generated/preview/screen.png",
            "approvedFileSha256": preview_hash,
            "approvedAssetHashes": {"icon": asset_hash},
            "approvedEvidenceHashes": {"productionPreviewLineage": digest(lineage_path)},
            "confirmation": {"type": "user_confirmation", "recordedBy": "user"},
        })
        report = module.validate(root, "fairygui_assembly")
        self.assertTrue(report["ok"], report["issues"])
        asset.write_bytes(b"asset-v2")
        report = module.validate(root, "xml_generation")
        self.assertIn("production_asset_regenerated_after_preview_approval", self.codes(report))

        asset.write_bytes(b"asset-v1")
        lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
        lineage["assets"][0]["sourceLineage"]["designRelation"] = "reference_reconstruction"
        lineage["assets"][0]["sourceLineage"]["reconstructionReason"] = "changed after approval"
        write_json(lineage_path, lineage)
        report = module.validate(root, "xml_generation")
        self.assertIn("production_preview_evidence_hash_mismatch", self.codes(report))

    def test_generated_asset_requires_reconstruction_relation_and_reason(self) -> None:
        root = self.root()
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresProductionPreviewLineage": True,
            },
            "assets": [{
                "name": "generated_icon",
                "file": "fgui_xml/pkg/art/generated_icon.png",
                "assetSource": {"mode": "image_generation_with_reference"},
                "fgui": {"resourceType": "image"},
            }],
        })
        write_json(root / "specs" / "production_preview_lineage.json", {
            "fidelityMode": "exact_production_composite",
            "productionPreview": {
                "file": "generated/preview/screen.png",
                "rendererScript": "scripts/render.py",
                "usesProductionAssets": True,
                "approvalRecord": "reports/production_preview_approval.json",
            },
            "assets": [{
                "assetName": "generated_icon",
                "runtimeFile": "fgui_xml/pkg/art/generated_icon.png",
                "previewUsage": "exact_file",
                "sourceLineage": {
                    "designRelation": "exact_approved_source",
                    "derivationMode": "deterministic_transform",
                    "sourceFile": "generated/sheets/icon_sheet.png",
                    "transformScript": "scripts/slice.py"
                }
            }],
        })
        report = module.validate(root, "asset_planning")
        codes = self.codes(report)
        self.assertIn("generated_asset_must_declare_reference_reconstruction", codes)

    def test_manifest_and_lineage_must_use_same_sheet_source_and_crop(self) -> None:
        root = self.root()
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresProductionPreviewLineage": True,
            },
            "sheets": [{"name": "icons", "file": "generated/sheets/icons.png"}],
            "assets": [{
                "name": "sheet_icon",
                "file": "fgui_xml/pkg/art/sheet_icon.png",
                "assetSource": {
                    "mode": "approved_sheet_slice",
                    "sourceFile": "generated/sheets/icons.png",
                    "crop": [0, 0, 32, 32],
                },
                "fgui": {"resourceType": "image"},
            }],
        })
        write_json(root / "specs" / "production_preview_lineage.json", {
            "fidelityMode": "exact_production_composite",
            "productionPreview": {
                "file": "generated/preview/screen.png",
                "rendererScript": "scripts/render.py",
                "usesProductionAssets": True,
                "approvalRecord": "reports/production_preview_approval.json",
            },
            "assets": [{
                "assetName": "sheet_icon",
                "runtimeFile": "fgui_xml/pkg/art/sheet_icon.png",
                "previewUsage": "exact_file",
                "sourceLineage": {
                    "designRelation": "exact_approved_source",
                    "derivationMode": "exact_crop",
                    "sourceFile": "generated/sheets/icons_alpha.png",
                    "crop": [1, 0, 32, 32],
                },
            }],
        })
        report = module.validate(root, "asset_planning")
        codes = self.codes(report)
        self.assertIn("runtime_asset_manifest_source_mismatch", codes)
        self.assertIn("runtime_asset_manifest_crop_mismatch", codes)


if __name__ == "__main__":
    unittest.main()
