from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_asset_isolation.py"
spec = importlib.util.spec_from_file_location("validate_asset_isolation", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def approved_review(root: Path) -> None:
    path = root / "reports" / "asset_isolation_review.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("approved", encoding="utf-8")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class AssetIsolationTests(unittest.TestCase):
    def make_root(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    @staticmethod
    def codes(report: dict) -> set[str]:
        return {item["code"] for item in report["issues"]}

    def test_non_visual_project_reports_skipped(self) -> None:
        root = self.make_root()
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {"generateFullScreenDesign": False},
            "assets": [],
        })
        report = module.validate(root, "asset_planning")
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "SKIPPED")
        self.assertFalse(report["applicable"])
        self.assertFalse(report["asset_isolation_checked"])

    def test_full_screen_design_requires_gate(self) -> None:
        root = self.make_root()
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {"generateFullScreenDesign": True},
            "assets": [],
        })
        report = module.validate(root, "asset_planning")
        self.assertIn("asset_isolation_gate_not_required", self.codes(report))

    def test_full_screen_design_cannot_be_runtime_background(self) -> None:
        root = self.make_root()
        design = root / "generated" / "design" / "screen.png"
        design.parent.mkdir(parents=True)
        Image.new("RGBA", (1280, 720), (10, 20, 30, 255)).save(design)
        approved_review(root)
        write_json(root / "reports" / "design_approval.json", {
            "approvedFile": "generated/design/screen.png"
        })
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresAssetIsolation": True
            },
            "assets": [{
                "name": "runtime_background",
                "file": "generated/design/screen.png",
                "type": "background",
                "assetSource": {
                    "mode": "approved_design_slice",
                    "sourceFile": "generated/design/screen.png",
                    "crop": [0, 0, 1280, 720]
                },
                "assetIsolation": {
                    "role": "environment_background",
                    "cleanEnvironmentOnly": True,
                    "reviewStatus": "approved",
                    "reviewEvidence": "reports/asset_isolation_review.md"
                },
                "fgui": {"resourceType": "image"}
            }]
        })
        report = module.validate(root, "resource_generation")
        self.assertIn("full_screen_design_used_as_runtime_background", self.codes(report))

    def test_v4_style_plain_crop_is_rejected(self) -> None:
        root = self.make_root()
        design = root / "generated" / "design" / "screen.png"
        design.parent.mkdir(parents=True)
        Image.new("RGBA", (100, 100), (10, 20, 30, 255)).save(design)
        scripts = root / "scripts"
        scripts.mkdir()
        (scripts / "slice.py").write_text(
            "from PIL import Image\n"
            "img=Image.open('x.png')\n"
            "img.crop((0,0,10,10)).save('y.png')\n",
            encoding="utf-8",
        )
        write_json(root / "reports" / "design_approval.json", {
            "approvedFile": "generated/design/screen.png"
        })
        write_json(root / "specs" / "slice_plan.json", {
            "entries": [{
                "name": "portrait",
                "output": "portrait.png",
                "extractionMode": "from_sheet",
                "reason": "Transparent character asset."
            }]
        })
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresAssetIsolation": True
            },
            "assets": [{
                "name": "portrait",
                "file": "generated/portrait.png",
                "type": "portrait",
                "transparent": False,
                "assetSource": {
                    "mode": "approved_design_slice",
                    "sourceFile": "generated/design/screen.png",
                    "crop": [10, 10, 50, 50]
                },
                "assetIsolation": {
                    "role": "isolated_subject",
                    "requiresTransparentBackground": True,
                    "forbidNeighborPixels": True,
                    "sourceRegionContainsOnlyAsset": True,
                    "reviewEvidence": "reports/asset_isolation_review.md"
                },
                "fgui": {"resourceType": "image"}
            }]
        })
        report = module.validate(root, "asset_planning")
        codes = self.codes(report)
        self.assertIn("plain_rectangular_crop_used_for_isolated_asset", codes)
        self.assertIn("slice_plan_claims_unimplemented_isolation", codes)
        self.assertIn("isolated_asset_manifest_not_transparent", codes)

    def test_transparent_icon_passes_after_generation(self) -> None:
        root = self.make_root()
        approved_review(root)
        art = root / "fgui_xml" / "pkg" / "art"
        art.mkdir(parents=True)
        image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        for x in range(8, 24):
            for y in range(8, 24):
                image.putpixel((x, y), (255, 255, 255, 255))
        image.save(art / "icon.png")
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresAssetIsolation": True
            },
            "assets": [{
                "name": "icon",
                "file": "fgui_xml/pkg/art/icon.png",
                "type": "icon",
                "transparent": True,
                "assetSource": {
                    "mode": "provided_bitmap",
                    "sourceFile": "fgui_xml/pkg/art/icon.png"
                },
                "assetIsolation": {
                    "role": "isolated_icon",
                    "requiresTransparentBackground": True,
                    "forbidNeighborPixels": True,
                    "sourceRegionContainsOnlyAsset": True,
                    "forbidBakedText": True,
                    "reviewStatus": "approved",
                    "reviewedBy": "user",
                    "reviewType": "user_confirmation",
                    "reviewEvidence": "reports/asset_isolation_review.md"
                },
                "fgui": {"resourceType": "image"}
            }]
        })
        report = module.validate(root, "resource_generation", root / "fgui_xml" / "pkg")
        self.assertTrue(report["ok"], report["issues"])

    def test_ai_self_approval_is_rejected(self) -> None:
        root = self.make_root()
        approved_review(root)
        art = root / "fgui_xml" / "pkg" / "art"
        art.mkdir(parents=True)
        image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        image.putpixel((8, 8), (255, 255, 255, 255))
        image.save(art / "icon.png")
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresAssetIsolation": True
            },
            "assets": [{
                "name": "icon",
                "file": "fgui_xml/pkg/art/icon.png",
                "type": "icon",
                "transparent": True,
                "assetSource": {"mode": "provided_bitmap"},
                "assetIsolation": {
                    "role": "isolated_icon",
                    "requiresTransparentBackground": True,
                    "forbidNeighborPixels": True,
                    "sourceRegionContainsOnlyAsset": True,
                    "forbidBakedText": True,
                    "reviewStatus": "approved",
                    "reviewedBy": "ai",
                    "reviewType": "human_visual_review",
                    "reviewEvidence": "reports/asset_isolation_review.md"
                },
                "fgui": {"resourceType": "image"}
            }]
        })
        report = module.validate(root, "resource_generation", root / "fgui_xml" / "pkg")
        self.assertIn("asset_isolation_ai_self_approval_forbidden", self.codes(report))

    def test_dynamic_skin_requires_no_baked_content(self) -> None:
        root = self.make_root()
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresAssetIsolation": True
            },
            "assets": [{
                "name": "button_skin",
                "file": "button.png",
                "type": "button_skin",
                "assetSource": {
                    "mode": "provided_bitmap",
                    "sourceFile": "button.png"
                },
                "assetIsolation": {
                    "role": "component_skin",
                    "forbidBakedText": False,
                    "containsBakedText": True,
                    "containsDynamicChildContent": True,
                    "reviewEvidence": "reports/asset_isolation_review.md"
                },
                "fgui": {"resourceType": "image"}
            }]
        })
        report = module.validate(root, "asset_planning")
        codes = self.codes(report)
        self.assertIn("dynamic_component_asset_allows_baked_text", codes)
        self.assertIn("asset_isolation_baked_text_not_reviewed", codes)
        self.assertIn("asset_contains_dynamic_child_content", codes)

    def test_approved_sheet_source_must_be_registered(self) -> None:
        root = self.make_root()
        sheet = root / "generated" / "sheets" / "icon_preview.png"
        sheet.parent.mkdir(parents=True)
        Image.new("RGBA", (128, 128), (0, 0, 0, 0)).save(sheet)
        write_json(root / "specs" / "slice_plan.json", {
            "sourceImages": ["generated/sheets/icon_preview.png"],
            "entries": [],
        })
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresAssetIsolation": True,
            },
            "sheets": [],
            "assets": [{
                "name": "icon_preview_asset",
                "file": "generated/icon_preview_asset.png",
                "type": "icon",
                "transparent": True,
                "assetSource": {
                    "mode": "approved_sheet_slice",
                    "sourceFile": "generated/sheets/icon_preview.png",
                    "crop": [0, 0, 64, 64],
                },
                "assetIsolation": {
                    "role": "isolated_icon",
                    "requiresTransparentBackground": True,
                    "forbidNeighborPixels": True,
                    "sourceRegionContainsOnlyAsset": True,
                    "forbidBakedText": True,
                    "reviewEvidence": "reports/asset_isolation_review.md",
                },
                "fgui": {"resourceType": "image"},
            }],
        })
        report = module.validate(root, "asset_planning")
        self.assertIn("approved_sheet_source_not_registered", self.codes(report))

    def test_slice_plan_must_include_exact_resource_preview_sheet(self) -> None:
        root = self.make_root()
        sheet = root / "generated" / "sheets" / "icon_preview.png"
        sheet.parent.mkdir(parents=True)
        Image.new("RGBA", (128, 128), (0, 0, 0, 0)).save(sheet)
        write_json(root / "specs" / "slice_plan.json", {
            "sourceImages": ["generated/design/screen_design.png"],
            "entries": [],
        })
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresAssetIsolation": True,
            },
            "sheets": [{"name": "icon_preview", "file": "generated/sheets/icon_preview.png"}],
            "assets": [{
                "name": "icon_preview_asset",
                "file": "generated/icon_preview_asset.png",
                "type": "icon",
                "transparent": True,
                "assetSource": {
                    "mode": "approved_sheet_slice",
                    "sourceFile": "generated/sheets/icon_preview.png",
                    "crop": [0, 0, 64, 64],
                },
                "assetIsolation": {
                    "role": "isolated_icon",
                    "requiresTransparentBackground": True,
                    "forbidNeighborPixels": True,
                    "sourceRegionContainsOnlyAsset": True,
                    "forbidBakedText": True,
                    "reviewEvidence": "reports/asset_isolation_review.md",
                },
                "fgui": {"resourceType": "image"},
            }],
        })
        report = module.validate(root, "asset_planning")
        self.assertIn("slice_plan_missing_approved_sheet_source", self.codes(report))

    def test_approved_sheet_ai_self_approval_is_rejected(self) -> None:
        root = self.make_root()
        approved_review(root)
        sheet = root / "generated" / "sheets" / "icon_preview.png"
        sheet.parent.mkdir(parents=True)
        Image.new("RGBA", (64, 64), (0, 0, 0, 0)).save(sheet)
        output = root / "fgui_xml" / "pkg" / "art" / "icon.png"
        output.parent.mkdir(parents=True)
        Image.new("RGBA", (32, 32), (0, 0, 0, 0)).save(output)
        write_json(root / "specs" / "slice_plan.json", {
            "sourceImages": ["generated/sheets/icon_preview.png"],
            "slices": [{
                "name": "icon",
                "sourceFile": "generated/sheets/icon_preview.png",
                "crop": [0, 0, 32, 32],
                "output": "fgui_xml/pkg/art/icon.png",
                "extractionMode": "exact_crop",
            }],
        })
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresAssetIsolation": True,
            },
            "sheets": [{
                "name": "icon_preview",
                "file": "generated/sheets/icon_preview.png",
                "reviewStatus": "approved",
                "reviewedBy": "ai",
                "reviewType": "human_visual_review",
                "reviewEvidence": "reports/asset_isolation_review.md",
            }],
            "assets": [{
                "name": "icon",
                "file": "fgui_xml/pkg/art/icon.png",
                "type": "icon",
                "transparent": True,
                "assetSource": {
                    "mode": "approved_sheet_slice",
                    "sourceFile": "generated/sheets/icon_preview.png",
                    "crop": [0, 0, 32, 32],
                },
                "assetIsolation": {
                    "role": "isolated_icon",
                    "requiresTransparentBackground": True,
                    "forbidNeighborPixels": True,
                    "sourceRegionContainsOnlyAsset": True,
                    "forbidBakedText": True,
                    "reviewStatus": "approved",
                    "reviewedBy": "user",
                    "reviewType": "user_confirmation",
                    "reviewEvidence": "reports/asset_isolation_review.md",
                },
                "fgui": {"resourceType": "image"},
            }],
        })
        report = module.validate(root, "resource_generation", root / "fgui_xml" / "pkg")
        self.assertIn("approved_sheet_ai_self_approval_forbidden", self.codes(report))

    def test_cut_report_exact_sheet_crop_passes(self) -> None:
        root = self.make_root()
        approved_review(root)
        sheet = root / "generated" / "sheets" / "icon_preview.png"
        sheet.parent.mkdir(parents=True)
        source = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        for x in range(8, 24):
            for y in range(8, 24):
                source.putpixel((x, y), (255, 255, 255, 255))
        source.save(sheet)
        output = root / "fgui_xml" / "pkg" / "art" / "icon.png"
        output.parent.mkdir(parents=True)
        source.crop((0, 0, 32, 32)).save(output)
        write_json(root / "specs" / "slice_plan.json", {
            "sourceImages": ["generated/sheets/icon_preview.png"],
            "slices": [{
                "name": "icon",
                "sourceFile": "generated/sheets/icon_preview.png",
                "crop": [0, 0, 32, 32],
                "output": "fgui_xml/pkg/art/icon.png",
                "extractionMode": "exact_crop",
            }],
        })
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresAssetIsolation": True,
            },
            "sheets": [{
                "name": "icon_preview",
                "file": "generated/sheets/icon_preview.png",
                "reviewStatus": "approved",
                "reviewedBy": "user",
                "reviewType": "user_confirmation",
                "reviewEvidence": "reports/asset_isolation_review.md",
            }],
            "assets": [{
                "name": "icon",
                "file": "fgui_xml/pkg/art/icon.png",
                "type": "icon",
                "transparent": True,
                "assetSource": {
                    "mode": "approved_sheet_slice",
                    "sourceFile": "generated/sheets/icon_preview.png",
                    "crop": [0, 0, 32, 32],
                },
                "assetIsolation": {
                    "role": "isolated_icon",
                    "requiresTransparentBackground": True,
                    "forbidNeighborPixels": True,
                    "sourceRegionContainsOnlyAsset": True,
                    "forbidBakedText": True,
                    "reviewStatus": "approved",
                    "reviewedBy": "user",
                    "reviewType": "user_confirmation",
                    "reviewEvidence": "reports/asset_isolation_review.md",
                },
                "fgui": {"resourceType": "image"},
            }],
        })
        write_json(root / "reports" / "cut_report.json", {
            "ok": True,
            "outputs": [{
                "name": "icon",
                "file": "fgui_xml/pkg/art/icon.png",
                "sourceFile": "generated/sheets/icon_preview.png",
                "crop": [0, 0, 32, 32],
                "derivationMode": "exact_crop",
                "sourceSha256": digest(sheet),
                "outputSha256": digest(output),
                "status": "ok",
            }],
        })
        report = module.validate(root, "sheet_slicing", root / "fgui_xml" / "pkg")
        self.assertTrue(report["ok"], report["issues"])

    def test_cut_report_actual_source_must_match_manifest(self) -> None:
        root = self.make_root()
        approved_review(root)
        sheet = root / "generated" / "sheets" / "icon_preview.png"
        alternate = root / "generated" / "sheets" / "icon_preview_alpha.png"
        sheet.parent.mkdir(parents=True)
        source = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        source.putpixel((16, 16), (255, 255, 255, 255))
        source.save(sheet)
        source.save(alternate)
        output = root / "fgui_xml" / "pkg" / "art" / "icon.png"
        output.parent.mkdir(parents=True)
        source.crop((0, 0, 32, 32)).save(output)
        write_json(root / "specs" / "slice_plan.json", {
            "sourceImages": ["generated/sheets/icon_preview.png"],
            "entries": [],
        })
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresAssetIsolation": True,
            },
            "sheets": [{
                "name": "icon_preview",
                "file": "generated/sheets/icon_preview.png",
                "reviewStatus": "approved",
                "reviewedBy": "user",
                "reviewType": "user_confirmation",
                "reviewEvidence": "reports/asset_isolation_review.md",
            }],
            "assets": [{
                "name": "icon",
                "file": "fgui_xml/pkg/art/icon.png",
                "type": "icon",
                "transparent": True,
                "assetSource": {
                    "mode": "approved_sheet_slice",
                    "sourceFile": "generated/sheets/icon_preview.png",
                    "crop": [0, 0, 32, 32],
                },
                "assetIsolation": {
                    "role": "isolated_icon",
                    "requiresTransparentBackground": True,
                    "forbidNeighborPixels": True,
                    "sourceRegionContainsOnlyAsset": True,
                    "forbidBakedText": True,
                    "reviewStatus": "approved",
                    "reviewedBy": "user",
                    "reviewType": "user_confirmation",
                    "reviewEvidence": "reports/asset_isolation_review.md",
                },
                "fgui": {"resourceType": "image"},
            }],
        })
        write_json(root / "reports" / "cut_report.json", {
            "ok": True,
            "outputs": [{
                "name": "icon",
                "file": "fgui_xml/pkg/art/icon.png",
                "sourceFile": "generated/sheets/icon_preview_alpha.png",
                "crop": [0, 0, 32, 32],
                "derivationMode": "exact_crop",
                "sourceSha256": digest(alternate),
                "outputSha256": digest(output),
                "status": "ok",
            }],
        })
        report = module.validate(root, "sheet_slicing", root / "fgui_xml" / "pkg")
        self.assertIn("cut_report_source_mismatch", self.codes(report))


if __name__ == "__main__":
    unittest.main()
