#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal end-to-end tests for FairyGUI XML Strict Mode validators."""

from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_ROOT / "scripts"
FULL_VISUAL_BRIEF = """# Visual Design Brief

## Confirmed Requirement Sources
## Screen Goal
## Design Resolution
## Primary Reference And Allowed Uses
## Functional Region Map
## Required Components And States
## Visual Hierarchy
## Art Direction
## Text And Localization Policy
## Asset Separation Constraints
## Negative Constraints
## Mockup Acceptance Criteria
## Known Risks
"""


def write_png(path: Path, width: int, height: int, *, alpha: bool = False) -> None:
    color_type = 6 if alpha else 2
    channels = 4 if alpha else 3
    pixel = b"\x00" * channels
    raw = b"".join(b"\x00" + pixel * width for _ in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        payload = kind + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


class StrictValidatorTests(unittest.TestCase):
    def run_script(self, script: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_embedded_full_documents_are_intact(self) -> None:
        result = self.run_script("verify_embedded_docs.py")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn('"ok": true', result.stdout)
        self.assertIn("fairygui-ai-generation-workflow.md", result.stdout)
        self.assertIn("fairygui-xml-parsing-specification.md", result.stdout)

    def create_project(self, root: Path, *, instance_id: str = "n0_3qpk") -> tuple[Path, Path]:
        specs = root / "specs"
        manifests = root / "manifests"
        sliced = root / "generated" / "sliced"
        references = root / "references"
        xml_dir = root / "fgui_xml" / "cooking"
        reports = root / "reports"
        for directory in (specs, manifests, sliced, references, xml_dir, reports):
            directory.mkdir(parents=True, exist_ok=True)

        fgui_spec = """# FairyGUI Assembly Spec

## Package
| Field | Value |
|---|---|
| package name | cooking |

## Components
| Component | File |
|---|---|
| cooking_view | cooking_view.xml |

## Display List
| Parent | Order | Name | Node Type | Asset Name | Resource | Position | Size | Size Source | Binding |
|---|---:|---|---|---|---|---|---|---|---|
| cooking_view | 0 | bg_main | image | bg_main | abc12 | 0,0 | 1920,1080 | asset_manifest.displaySize | bgMain |

## Layout Region Table
| Region | Parent |
|---|---|
| main | cooking_view |

## Slot Table
| Slot | Component Name |
|---|---|
| none | none |

## Component Ownership Table
| Responsibility | Owner Component |
|---|---|
| background | cooking_view |

## Controllers
| Component | Controller |
|---|---|
| cooking_view | none |

## Gear Mapping Table
| Component | Controller |
|---|---|
| cooking_view | none |

## Transitions
| Component | Transition |
|---|---|
| cooking_view | none |

## Relations
| Object | Relation |
|---|---|
| bg_main | center |

## Unity Bindings
| Field | Type |
|---|---|
| bgMain | GImage |

## Automation Risks
| Risk | Status |
|---|---|
| none | accepted |
"""
        (specs / "fgui_spec.md").write_text(fgui_spec, encoding="utf-8")

        manifest = {
            "version": "0.1.0",
            "screen": "cooking_view",
            "resolution": [1920, 1080],
            "production": {"generateVisualAssets": True, "requiresVisualReference": True},
            "referenceImages": [
                {
                    "file": "references/ui_reference.png",
                    "role": "style_and_layout",
                    "resolution": [64, 64],
                    "isPrimary": True,
                    "allowedUses": ["style", "layout", "asset_generation"],
                }
            ],
            "package": {"name": "cooking", "outputPath": "fgui_xml/cooking"},
            "sheets": [],
            "assets": [
                {
                    "name": "bg_main",
                    "file": "generated/sliced/bg_main.png",
                    "type": "background",
                    "sourcePixelSize": [64, 64],
                    "displaySize": [1920, 1080],
                    "scalePolicy": "explicit_scale",
                    "renderMode": "normal",
                    "nineSliceGrid": None,
                    "transparent": False,
                    "pivot": "top_left",
                    "fgui": {"resourceType": "image", "nodeType": "image"},
                }
            ],
        }
        (manifests / "asset_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        registry = {
            "version": "0.1.0",
            "packages": {
                "cooking": {
                    "id": "qdf53qpk",
                    "resources": {"bg_main": "abc12", "cooking_view.xml": "view1"},
                    "instances": {"cooking_view/bg_main": instance_id},
                    "retired": [],
                }
            },
        }
        (manifests / "fgui_id_registry.json").write_text(
            json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        write_png(references / "ui_reference.png", 64, 64)
        write_png(sliced / "bg_main.png", 64, 64)

        (xml_dir / "package.xml").write_text(
            """<?xml version="1.0" encoding="utf-8"?>
<packageDescription id="qdf53qpk">
  <resources>
    <image id="abc12" name="bg_main" path="/"/>
    <component id="view1" name="cooking_view.xml" path="/"/>
  </resources>
</packageDescription>
""",
            encoding="utf-8",
        )
        (xml_dir / "cooking_view.xml").write_text(
            f"""<?xml version="1.0" encoding="utf-8"?>
<component size="1920,1080">
  <displayList>
    <image id="{instance_id}" name="bg_main" src="abc12" fileName="generated/sliced/bg_main.png" size="1920,1080"/>
  </displayList>
</component>
""",
            encoding="utf-8",
        )

        full_spec = root / "full_xml_spec.md"
        full_spec.write_text("完整规范\n" + ("x" * 10_100), encoding="utf-8")
        return xml_dir, full_spec

    def add_design_approval(
        self,
        root: Path,
        *,
        status: str = "approved",
        approved_for: list[str] | None = None,
    ) -> Path:
        specs = root / "specs"
        design_dir = root / "generated" / "design"
        reports = root / "reports"
        design_dir.mkdir(parents=True, exist_ok=True)
        reports.mkdir(parents=True, exist_ok=True)
        specs.mkdir(parents=True, exist_ok=True)

        (specs / "ui_spec.md").write_text(
            "# UI Spec\n\n## Screen Goal\n",
            encoding="utf-8",
        )
        (specs / "visual_design_brief.md").write_text(FULL_VISUAL_BRIEF, encoding="utf-8")
        design_path = design_dir / "screen_design_final.png"
        write_png(design_path, 1920, 1080)
        digest = hashlib.sha256(design_path.read_bytes()).hexdigest()

        approval = {
            "version": "0.1.0",
            "status": status,
            "candidateFile": "generated/design/screen_design_final.png" if status == "approved" else None,
            "approvedFile": "generated/design/screen_design_final.png" if status == "approved" else None,
            "approvedFileSha256": digest if status == "approved" else None,
            "resolution": [1920, 1080],
            "approvedFor": approved_for or [
                "semantic_analysis",
                "layout_analysis",
                "asset_planning",
                "resource_generation",
                "fairygui_assembly",
                "xml_generation",
            ] if status == "approved" else [],
            "confirmation": {
                "type": "user_confirmation",
                "recordedBy": "user",
                "note": "User approved this exact design file.",
                "confirmedAt": "2026-07-21T00:00:00Z",
            } if status == "approved" else None,
            "knownDeviations": [],
            "reviewNotes": [],
            "updatedAt": "2026-07-21T00:00:00Z",
        }
        (reports / "design_approval.json").write_text(
            json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return design_path

    def test_record_design_approval_computes_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            specs = root / "specs"
            design_dir = root / "generated" / "design"
            specs.mkdir(parents=True, exist_ok=True)
            design_dir.mkdir(parents=True, exist_ok=True)
            (specs / "ui_spec.md").write_text("# UI Spec\n", encoding="utf-8")
            (specs / "visual_design_brief.md").write_text(FULL_VISUAL_BRIEF, encoding="utf-8")
            design_path = design_dir / "screen_design_final.png"
            write_png(design_path, 1920, 1080)

            record = self.run_script(
                "record_design_approval.py",
                "--root", str(root),
                "--action", "approve",
                "--file", "generated/design/screen_design_final.png",
                "--approved-for", "semantic_analysis", "layout_analysis",
                "--confirmation-type", "user_confirmation",
                "--recorded-by", "user",
                "--note", "User approved this exact file.",
            )
            self.assertEqual(record.returncode, 0, record.stderr + record.stdout)

            approval = json.loads((root / "reports" / "design_approval.json").read_text(encoding="utf-8"))
            self.assertEqual(approval["approvedFileSha256"], hashlib.sha256(design_path.read_bytes()).hexdigest())

            gate = self.run_script(
                "check_design_approval.py",
                "--root", str(root),
                "--stage", "semantic_analysis",
            )
            self.assertEqual(gate.returncode, 0, gate.stderr + gate.stdout)

    def test_design_approval_pending_blocks_semantic_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_design_approval(root, status="pending")

            result = self.run_script(
                "check_design_approval.py",
                "--root", str(root),
                "--stage", "semantic_analysis",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("design_not_approved", result.stdout)

    def test_ai_self_approval_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_design_approval(root)
            approval_path = root / "reports" / "design_approval.json"
            approval = json.loads(approval_path.read_text(encoding="utf-8"))
            approval["confirmation"] = {
                "type": "automatic",
                "recordedBy": "ai",
                "note": "AI selected this draft.",
                "confirmedAt": "2026-07-21T00:00:00Z",
            }
            approval_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")

            result = self.run_script(
                "check_design_approval.py",
                "--root", str(root),
                "--stage", "semantic_analysis",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("confirmation_type_invalid", result.stdout)
            self.assertIn("confirmation_origin_invalid", result.stdout)

    def test_approval_scope_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_design_approval(root, approved_for=["semantic_analysis"])

            result = self.run_script(
                "check_design_approval.py",
                "--root", str(root),
                "--stage", "xml_generation",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("stage_not_approved", result.stdout)

    def test_exact_human_approved_design_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_design_approval(root)

            result = self.run_script(
                "check_design_approval.py",
                "--root", str(root),
                "--stage", "layout_analysis",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('"approved": true', result.stdout)

    def test_changed_design_invalidates_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            design_path = self.add_design_approval(root)
            write_png(design_path, 1920, 1080, alpha=True)

            result = self.run_script(
                "check_design_approval.py",
                "--root", str(root),
                "--stage", "resource_generation",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("approved_file_changed", result.stdout)

    def declare_full_screen_design(self, root: Path) -> None:
        manifest_path = root / "manifests" / "asset_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["production"]["generateFullScreenDesign"] = True
        manifest["production"]["requiresDesignApproval"] = True
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_pipeline_validator_blocks_unapproved_full_screen_design(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            self.declare_full_screen_design(root)
            self.add_design_approval(root, status="pending")

            result = self.run_script("validate_pipeline.py", "--root", str(root))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("design approval", result.stdout)

    def test_pipeline_validator_accepts_approved_full_screen_design(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            self.declare_full_screen_design(root)
            self.add_design_approval(root)

            result = self.run_script("validate_pipeline.py", "--root", str(root))
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_xml_readiness_auto_blocks_unapproved_full_screen_design(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            _, full_spec = self.create_project(root)
            self.declare_full_screen_design(root)
            self.add_design_approval(root, status="pending")

            result = self.run_script(
                "check_xml_readiness.py",
                "--root", str(root),
                "--full-xml-spec", str(full_spec),
                "--profile", "fresh",
                "--resource-generation",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("design_approval_design_not_approved", result.stdout)

    def test_xml_readiness_accepts_exact_approved_full_screen_design(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            _, full_spec = self.create_project(root)
            self.declare_full_screen_design(root)
            self.add_design_approval(root)

            result = self.run_script(
                "check_xml_readiness.py",
                "--root", str(root),
                "--full-xml-spec", str(full_spec),
                "--profile", "fresh",
                "--resource-generation",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('"designApproved": true', result.stdout)

    def test_readiness_and_fresh_validation_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir, full_spec = self.create_project(root)

            readiness = self.run_script(
                "check_xml_readiness.py",
                "--root", str(root),
                "--full-xml-spec", str(full_spec),
                "--profile", "fresh",
                "--resource-generation",
                "--out", str(root / "reports" / "xml_readiness_report.json"),
                "--report-md", str(root / "reports" / "xml_blocking_report.md"),
                "--snapshot-out", str(root / "reports" / "xml_generation_input_snapshot.json"),
            )
            self.assertEqual(readiness.returncode, 0, readiness.stderr + readiness.stdout)
            self.assertTrue((root / "reports" / "xml_generation_input_snapshot.json").is_file())

            pipeline = self.run_script("validate_pipeline.py", "--root", str(root))
            self.assertEqual(pipeline.returncode, 0, pipeline.stderr + pipeline.stdout)

            xml_validation = self.run_script(
                "validate_fgui_xml.py",
                "--xml-dir", str(xml_dir),
                "--manifest", str(root / "manifests" / "asset_manifest.json"),
                "--registry", str(root / "manifests" / "fgui_id_registry.json"),
                "--mode", "fresh",
            )
            self.assertEqual(xml_validation.returncode, 0, xml_validation.stderr + xml_validation.stdout)

    def test_invalid_package_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            registry_path = root / "manifests" / "fgui_id_registry.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["packages"]["cooking"]["id"] = "abc12"
            registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

            result = self.run_script("validate_pipeline.py", "--root", str(root))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exactly 8", result.stdout)

    def test_missing_reference_blocks_resource_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            _, full_spec = self.create_project(root)
            manifest_path = root / "manifests" / "asset_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["referenceImages"] = []
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            result = self.run_script(
                "check_xml_readiness.py",
                "--root", str(root),
                "--full-xml-spec", str(full_spec),
                "--profile", "fresh",
                "--resource-generation",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("visual_reference_missing", result.stdout)

    def test_fgui_spec_display_size_mismatch_blocks_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            _, full_spec = self.create_project(root)
            fgui_spec_path = root / "specs" / "fgui_spec.md"
            fgui_spec_path.write_text(
                fgui_spec_path.read_text(encoding="utf-8").replace(
                    "| cooking_view | 0 | bg_main | image | bg_main | abc12 | 0,0 | 1920,1080 |",
                    "| cooking_view | 0 | bg_main | image | bg_main | abc12 | 0,0 | 1280,720 |",
                ),
                encoding="utf-8",
            )

            result = self.run_script(
                "check_xml_readiness.py",
                "--root", str(root),
                "--full-xml-spec", str(full_spec),
                "--profile", "fresh",
                "--resource-generation",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("fgui_display_size_mismatch", result.stdout)

    def test_xml_display_size_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir, _ = self.create_project(root)
            component_path = xml_dir / "cooking_view.xml"
            component_path.write_text(
                component_path.read_text(encoding="utf-8").replace('size="1920,1080"/>', 'size="1280,720"/>'),
                encoding="utf-8",
            )

            result = self.run_script(
                "validate_fgui_xml.py",
                "--xml-dir", str(xml_dir),
                "--manifest", str(root / "manifests" / "asset_manifest.json"),
                "--registry", str(root / "manifests" / "fgui_id_registry.json"),
                "--mode", "fresh",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("displaySize", result.stdout)

    def test_actual_pixel_size_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            manifest_path = root / "manifests" / "asset_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["assets"][0]["sourcePixelSize"] = [32, 32]
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            result = self.run_script("validate_pipeline.py", "--root", str(root))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("actual pixels", result.stdout)

    def test_editor_compatible_preserves_existing_instance_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir, _ = self.create_project(root, instance_id="editor_instance_01")
            common_args = (
                "--xml-dir", str(xml_dir),
                "--manifest", str(root / "manifests" / "asset_manifest.json"),
                "--registry", str(root / "manifests" / "fgui_id_registry.json"),
            )

            fresh = self.run_script("validate_fgui_xml.py", *common_args, "--mode", "fresh")
            self.assertNotEqual(fresh.returncode, 0)

            compatible = self.run_script(
                "validate_fgui_xml.py", *common_args, "--mode", "editor-compatible"
            )
            self.assertEqual(compatible.returncode, 0, compatible.stderr + compatible.stdout)
            self.assertIn("warning", compatible.stdout)


if __name__ == "__main__":
    unittest.main()
