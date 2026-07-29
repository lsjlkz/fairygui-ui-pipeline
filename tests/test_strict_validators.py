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

    def test_semantic_controller_mapping_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_semantic_controller_specs(root)
            result = self.run_script(
                "validate_semantic_controller_mapping.py",
                "--root", str(root),
                "--stage", "xml_generation",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('"ok": true', result.stdout)

    def test_semantic_controller_missing_page_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_semantic_controller_specs(root, omit_ready_page=True)
            result = self.run_script(
                "validate_semantic_controller_mapping.py",
                "--root", str(root),
                "--stage", "xml_generation",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("fgui_controller_pages_missing", result.stdout)

    def test_semantic_controller_missing_gear_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_semantic_controller_specs(root, omit_ready_gear=True)
            result = self.run_script(
                "validate_semantic_controller_mapping.py",
                "--root", str(root),
                "--stage", "xml_generation",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("fgui_gear_mapping_missing", result.stdout)

    def test_xml_missing_planned_gear_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_semantic_controller_specs(root)
            xml_dir = root / "fgui_xml" / "cooking"
            xml_dir.mkdir(parents=True, exist_ok=True)
            (xml_dir / "equipment_slot.xml").write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<component size="320,280">
  <controller name="state" pages="idle,ready"/>
  <displayList>
    <image id="n0_test" name="highlight_ready" src="abc12" fileName="highlight.png" size="320,280"/>
  </displayList>
</component>
""",
                encoding="utf-8",
            )
            result = self.run_script(
                "validate_semantic_controller_mapping.py",
                "--root", str(root),
                "--stage", "xml_generation",
                "--xml-dir", str(xml_dir),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("xml_gear_missing", result.stdout)

    def test_validate_fgui_xml_auto_checks_semantic_controller_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir, _ = self.create_project(root)
            self.add_semantic_controller_specs(root)
            (xml_dir / "equipment_slot.xml").write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<component size="320,280">
  <controller name="state" pages="idle,ready"/>
  <displayList>
    <group id="n1_3qpk" name="highlight_ready"/>
  </displayList>
</component>
""",
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
            self.assertIn("semantic controller mapping [xml_gear_missing]", result.stdout)
            self.assertIn('"semantic_controller_mapping_checked": true', result.stdout)
            self.assertIn('"component_reuse_checked": true', result.stdout)
            self.assertIn('"display_list_z_order_checked": true', result.stdout)
            self.assertIn('"bitmap_asset_provenance_checked": true', result.stdout)

    def create_project(self, root: Path, *, instance_id: str = "n0_3qpk") -> tuple[Path, Path]:
        specs = root / "specs"
        manifests = root / "manifests"
        sliced = root / "generated" / "sliced"
        references = root / "references"
        xml_dir = root / "fgui_xml" / "cooking"
        package_art = xml_dir / "art"
        reports = root / "reports"
        for directory in (specs, manifests, sliced, references, xml_dir, package_art, reports):
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
| Parent | Order | Name | Node Type | Asset Name | Resource | Position | Size | Size Source | Z Layer | Occlusion Policy | Binding |
|---|---:|---|---|---|---|---|---|---|---|---|---|
| cooking_view | 0 | bg_main | image | bg_main | abc12 | 0,0 | 1920,1080 | asset_manifest.displaySize | background | opaque_background | bgMain |

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
                    "file": "fgui_xml/cooking/art/bg_main.png",
                    "packageRelativeFile": "art/bg_main.png",
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
        write_png(package_art / "bg_main.png", 64, 64)

        (xml_dir / "package.xml").write_text(
            """<?xml version="1.0" encoding="utf-8"?>
<packageDescription id="qdf53qpk">
  <resources>
    <image id="abc12" name="bg_main.png" path="/art/"/>
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
    <image id="{instance_id}" name="bg_main" src="abc12" fileName="art/bg_main.png" size="1920,1080"/>
  </displayList>
</component>
""",
            encoding="utf-8",
        )

        full_spec = root / "full_xml_spec.md"
        full_spec.write_text("完整规范\n" + ("x" * 10_100), encoding="utf-8")
        return xml_dir, full_spec

    def add_semantic_controller_specs(self, root: Path, *, omit_ready_page: bool = False, omit_ready_gear: bool = False) -> None:
        specs = root / "specs"
        specs.mkdir(parents=True, exist_ok=True)
        (specs / "visual_design_brief.md").write_text(FULL_VISUAL_BRIEF, encoding="utf-8")
        design_dir = root / "generated" / "design"
        design_dir.mkdir(parents=True, exist_ok=True)
        design_path = design_dir / "screen_design_final.png"
        if not design_path.is_file():
            write_png(design_path, 1920, 1080)
        (specs / "ui_spec.md").write_text(
            """# UI Spec

## State Matrix
| Component | States | Trigger | Visual Change | Image Needed | Controller | Business Owner | Visual Owner | Dynamic Data Owner | Requirement IDs |
|---|---|---|---|---|---|---|---|---|---|
| EquipmentSlot | idle,ready | timer completed | food and highlight change | yes | state | GamePlay | FGUI | GameUI | REQ-EQUIPMENT-STATE |
""",
            encoding="utf-8",
        )
        (specs / "uxui_semantic_spec.md").write_text(
            """# UX/UI Semantic Spec

## Sources
- specs/ui_spec.md
- specs/visual_design_brief.md
- generated/design/screen_design_final.png
""",
            encoding="utf-8",
        )
        state_map = {
            "version": "0.1.0",
            "screen": "cooking_view",
            "requirementSources": ["specs/ui_spec.md"],
            "designDocumentSources": ["specs/visual_design_brief.md"],
            "designSources": ["generated/design/screen_design_final.png"],
            "components": [
                {
                    "componentType": "EquipmentSlot",
                    "fguiComponent": "equipment_slot",
                    "purpose": "One cooking equipment slot",
                    "runtimeOwner": "Mixed",
                    "businessStateOwner": "GamePlay",
                    "visualStateOwner": "FGUI",
                    "dynamicDataOwner": "GameUI",
                    "states": ["idle", "ready"],
                    "controllers": ["state"],
                    "reusable": True,
                    "reusePlan": {
                        "strategy": "single_component",
                        "baseComponentFile": "equipment_slot.xml",
                        "extension": "none",
                        "parameterizableFields": ["controller.state", "runtime.foodId", "runtime.state"],
                        "childComponentFiles": [],
                        "variantReasons": [],
                    },
                    "requirementIds": ["REQ-EQUIPMENT-STATE"],
                }
            ],
            "visualInstances": [],
            "stateGroups": [
                {
                    "componentType": "EquipmentSlot",
                    "stateName": "idle",
                    "trigger": "reset",
                    "visualDifference": "ready highlight hidden",
                    "runtimeData": [],
                    "fguiController": "state",
                    "gearType": ["gearDisplay"],
                    "requirementIds": ["REQ-EQUIPMENT-STATE"],
                },
                {
                    "componentType": "EquipmentSlot",
                    "stateName": "ready",
                    "trigger": "timer completed",
                    "visualDifference": "ready highlight visible",
                    "runtimeData": ["foodId"],
                    "fguiController": "state",
                    "gearType": ["gearDisplay"],
                    "requirementIds": ["REQ-EQUIPMENT-STATE"],
                },
            ],
            "requirementLinks": [],
            "reviewStatus": "reviewed",
            "blockingForLayout": False,
            "blockingForXml": False,
        }
        (specs / "component_state_map.json").write_text(
            json.dumps(state_map, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        visual_parts = {
            "version": "0.1.0",
            "screen": "cooking_view",
            "designSources": ["generated/design/screen_design_final.png"],
            "components": [
                {
                    "componentType": "EquipmentSlot",
                    "componentFiles": ["equipment_slot.xml"],
                    "requirementIds": ["REQ-EQUIPMENT-STATE"],
                    "parts": [
                        {
                            "partId": "ready_highlight",
                            "role": "state_marker",
                            "required": True,
                            "visibleInApprovedDesign": True,
                            "visualImportance": "semantic",
                            "complexity": "simple",
                            "requirementIds": ["REQ-EQUIPMENT-STATE"],
                            "implementation": {
                                "mode": "group",
                                "xmlNodeNames": ["highlight_ready"],
                                "appliesToFiles": ["equipment_slot.xml"],
                                "nodeMatch": "all",
                                "fallbackPolicy": "forbidden",
                            },
                        }
                    ],
                }
            ],
            "reviewStatus": "reviewed",
            "blockingForXml": False,
        }
        (specs / "component_visual_parts.json").write_text(
            json.dumps(visual_parts, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        layout = {
            "version": "0.1.0",
            "screen": "cooking_view",
            "designResolution": [1920, 1080],
            "sourceImages": ["generated/design/screen_design_final.png"],
            "semanticSources": ["specs/component_state_map.json"],
            "coordinateSystem": {"origin": "top_left", "unit": "px", "space": "design_resolution"},
            "regions": [],
            "objects": [
                {
                    "name": "equipment_slot_left",
                    "semanticId": "equipment.slot",
                    "instanceId": "equipment_slot_left_01",
                    "componentType": "EquipmentSlot",
                    "stateVariant": "idle",
                    "nodeType": "component",
                    "component": "equipment_slot",
                    "region": "work_area",
                    "bbox": [100, 200, 320, 280],
                    "binding": "equipmentSlotLeft",
                    "stateOwner": "FGUI",
                    "runtimeRole": "cook_source",
                    "zLayer": "content",
                    "occlusionPolicy": "normal",
                    "requirementIds": ["REQ-EQUIPMENT-STATE"],
                    "slicePolicy": "use_component",
                }
            ],
            "slots": [],
            "relations": [],
            "reviewStatus": "reviewed",
            "blockingForXml": False,
        }
        (specs / "layout_spec.json").write_text(
            json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (specs / "slice_plan.json").write_text(
            json.dumps(
                {
                    "version": "0.1.0",
                    "screen": "cooking_view",
                    "sourceLayout": "specs/layout_spec.json",
                    "sourceImages": ["generated/design/screen_design_final.png"],
                    "rules": {
                        "doNotSliceDynamicStatesFromFlatDesign": True,
                        "requireOverlayReviewBeforeXml": True,
                    },
                    "slices": [],
                    "blockingForXml": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        reports = root / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        (reports / "layout_overlay_review.md").write_text(
            "# Layout Overlay Review\n\n- status: approved\n",
            encoding="utf-8",
        )
        pages = "idle" if omit_ready_page else "idle,ready"
        ready_gear_row = "" if omit_ready_gear else "| equipment_slot | state | ready | highlight_ready | gearDisplay | visible | REQ-EQUIPMENT-STATE |\n"
        fgui_spec = f"""# FairyGUI Assembly Spec

## Package
| Field | Value |
|---|---|
| package name | cooking |
| package id | qdf53qpk |
| design resolution | 1920,1080 |

## Components
| Component | File | Extension | Exported | Purpose |
|---|---|---|---|---|
| cooking_view | cooking_view.xml | none | true | main screen |
| equipment_slot | equipment_slot.xml | none | true | cooking equipment state component |

## Display List
| Parent | Order | Name | Node Type | Asset Name | Resource | Position | Size | Size Source | Z Layer | Occlusion Policy | Binding |
|---|---:|---|---|---|---|---|---|---|---|---|---|
| cooking_view | 0 | bg_main | image | bg_main | abc12 | 0,0 | 1920,1080 | asset_manifest.displaySize | background | opaque_background | bgMain |
| cooking_view | 1 | equipment_slot_left | component | none | equipment_slot | 100,200 | 320,280 | layout_spec.bbox | content | normal | equipmentSlotLeft |

## Layout Region Table
| Region | Parent | Bounds | Anchor / Relation | Type | Interaction Responsibility |
|---|---|---|---|---|---|
| work_area | cooking_view | 0,0,1920,1080 | center | interactive | equipment interaction |

## Slot Table
| Slot | Component Name | Region | XY | Size | Pivot | Binding | State Owner |
|---|---|---|---|---|---|---|---|
| equipment_slot_left | equipment_slot | work_area | 100,200 | 320,280 | top_left | equipmentSlotLeft | FGUI |

## Component Ownership Table
| Responsibility | Owner Component | Should Not Live In |
|---|---|---|
| equipment state visuals | equipment_slot | cooking_view |

## Component Reuse Plan
| Component Type | Strategy | Base Component File | Extension | Parameterizable Fields | Child Components | Variant Reasons | Requirement IDs |
|---|---|---|---|---|---|---|---|
| EquipmentSlot | single_component | equipment_slot.xml | none | controller.state,runtime.foodId,runtime.state | none | none | REQ-EQUIPMENT-STATE |

## Controllers
| Component | Controller | Pages | Default | Exported | Used By | Requirement IDs | State Owner |
|---|---|---|---|---|---|---|---|
| equipment_slot | state | {pages} | idle | false | highlight_ready | REQ-EQUIPMENT-STATE | FGUI |

## Gear Mapping Table
| Component | Controller | Page | Gear Target | Gear Type | Result | Requirement IDs |
|---|---|---|---|---|---|---|
| equipment_slot | state | idle | highlight_ready | gearDisplay | hidden | REQ-EQUIPMENT-STATE |
{ready_gear_row}
## Visual Part Coverage
| Component Type | Part ID | Role | Required | Importance | Complexity | Implementation Mode | Asset Name | XML Nodes | Applies To Files | Fallback Policy | Requirement IDs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EquipmentSlot | ready_highlight | state_marker | true | semantic | simple | group | none | highlight_ready | equipment_slot.xml | forbidden | REQ-EQUIPMENT-STATE |

## Transitions
| Component | Transition | Trigger | Draft Behavior | Needs Editor Review |
|---|---|---|---|---|
| equipment_slot | none | none | none | false |

## Relations
| Object | Relation |
|---|---|
| bg_main | center |

## Unity Bindings
| Field | Type | FairyGUI Path | Notes |
|---|---|---|---|
| equipmentSlotLeft | GComponent | cooking_view/equipment_slot_left | stateful equipment slot |

## Automation Risks
| Risk | Status |
|---|---|
| none | accepted |
"""
        (specs / "fgui_spec.md").write_text(fgui_spec, encoding="utf-8")

    def add_instance_configuration_fixture(
        self,
        root: Path,
        *,
        selected_page: int = 1,
        raw_localization_key: bool = False,
    ) -> Path:
        self.add_semantic_controller_specs(root)
        specs = root / "specs"
        state_map_path = specs / "component_state_map.json"
        state_map = json.loads(state_map_path.read_text(encoding="utf-8"))
        state_map["components"][0]["reusePlan"] = {
            "strategy": "variant_allowed",
            "baseComponentFile": "equipment_slot.xml",
            "extension": "none",
            "parameterizableFields": ["controller.state", "runtime.foodId", "runtime.state"],
            "childComponentFiles": [],
            "variantReasons": ["structural_difference"],
        }
        state_map["visualInstances"] = [
            {
                "instanceId": "equipment_slot_left_01",
                "componentType": "EquipmentSlot",
                "xmlInstanceName": "equipment_slot_left",
                "stateVariant": "ready",
                "controllerPages": {"state": "ready"},
                "slotRole": "cook_source",
                "requirementIds": ["REQ-EQUIPMENT-STATE"],
                "implementation": {
                    "configurationMode": "variant_component",
                    "componentFile": "equipment_slot_ready.xml",
                    "previewValues": {"state": "ready", "title": "READY"},
                    "runtimeBindings": ["foodId", "state"],
                    "variantJustification": {
                        "reason": "structural_difference",
                        "structuralDifferences": ["The ready preview contains an additional title node."],
                    },
                },
            }
        ]
        state_map_path.write_text(json.dumps(state_map, ensure_ascii=False, indent=2), encoding="utf-8")

        fgui_spec_path = specs / "fgui_spec.md"
        fgui_spec = fgui_spec_path.read_text(encoding="utf-8")
        fgui_spec = fgui_spec.replace(
            "| EquipmentSlot | single_component | equipment_slot.xml | none | controller.state,runtime.foodId,runtime.state | none | none | REQ-EQUIPMENT-STATE |",
            "| EquipmentSlot | variant_allowed | equipment_slot.xml | none | controller.state,runtime.foodId,runtime.state | none | structural_difference | REQ-EQUIPMENT-STATE |",
        )
        instance_table = """## Instance Configuration

| Instance ID | XML Name | Component Type | Component File | Configuration Mode | Controller Pages | Controller Parameters | Extension Parameters | Preview Values | Runtime Bindings | Requirement IDs |
|---|---|---|---|---|---|---|---|---|---|---|
| equipment_slot_left_01 | equipment_slot_left | EquipmentSlot | equipment_slot_ready.xml | variant_component | state=ready | none | none | state=ready,title=READY | foodId,state | REQ-EQUIPMENT-STATE |

"""
        fgui_spec = fgui_spec.replace("## Transitions", instance_table + "## Transitions")
        fgui_spec_path.write_text(fgui_spec, encoding="utf-8")

        xml_dir = root / "fgui_xml" / "cooking"
        xml_dir.mkdir(parents=True, exist_ok=True)
        (xml_dir / "cooking_view.xml").write_text(
            """<?xml version="1.0" encoding="utf-8"?>
<component size="1920,1080">
  <displayList>
    <component id="n0_3qpk" name="equipment_slot_left" src="slot1" fileName="equipment_slot_ready.xml" xy="100,200" size="320,280"/>
  </displayList>
</component>
""",
            encoding="utf-8",
        )
        generic_xml = """<?xml version="1.0" encoding="utf-8"?>
<component size="320,280">
  <controller name="state" pages="0,idle,1,ready" selected="0"/>
  <displayList>
    <group id="n1_3qpk" name="highlight_ready">
      <gearDisplay controller="state" pages="1"/>
    </group>
  </displayList>
</component>
"""
        (xml_dir / "equipment_slot.xml").write_text(generic_xml, encoding="utf-8")
        preview_text = "@ui_ready" if raw_localization_key else "READY"
        (xml_dir / "equipment_slot_ready.xml").write_text(
            f"""<?xml version="1.0" encoding="utf-8"?>
<component size="320,280">
  <controller name="state" pages="0,idle,1,ready" selected="{selected_page}"/>
  <displayList>
    <group id="n2_3qpk" name="highlight_ready">
      <gearDisplay controller="state" pages="1"/>
    </group>
    <text id="n3_3qpk" name="title" xy="0,0" size="120,40" text="{preview_text}"/>
  </displayList>
</component>
""",
            encoding="utf-8",
        )
        return xml_dir

    def test_reusable_different_instances_cannot_use_static_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_semantic_controller_specs(root)
            state_map_path = root / "specs" / "component_state_map.json"
            state_map = json.loads(state_map_path.read_text(encoding="utf-8"))
            state_map["visualInstances"] = [
                {
                    "instanceId": "slot_idle",
                    "componentType": "EquipmentSlot",
                    "xmlInstanceName": "slot_idle",
                    "stateVariant": "idle",
                    "controllerPages": {"state": "idle"},
                    "slotRole": "source_a",
                    "requirementIds": ["REQ-EQUIPMENT-STATE"],
                    "implementation": {
                        "configurationMode": "static_default",
                        "componentFile": "equipment_slot.xml",
                        "previewValues": {"state": "idle"},
                        "runtimeBindings": ["state"],
                    },
                },
                {
                    "instanceId": "slot_ready",
                    "componentType": "EquipmentSlot",
                    "xmlInstanceName": "slot_ready",
                    "stateVariant": "ready",
                    "controllerPages": {"state": "ready"},
                    "slotRole": "source_b",
                    "requirementIds": ["REQ-EQUIPMENT-STATE"],
                    "implementation": {
                        "configurationMode": "static_default",
                        "componentFile": "equipment_slot.xml",
                        "previewValues": {"state": "ready"},
                        "runtimeBindings": ["state"],
                    },
                },
            ]
            state_map_path.write_text(json.dumps(state_map, ensure_ascii=False, indent=2), encoding="utf-8")
            result = self.run_script(
                "validate_semantic_controller_mapping.py",
                "--root", str(root),
                "--stage", "semantic_analysis",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("reusable_instance_configuration_missing", result.stdout)

    def test_variant_component_default_page_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir = self.add_instance_configuration_fixture(root, selected_page=0)
            result = self.run_script(
                "validate_semantic_controller_mapping.py",
                "--root", str(root),
                "--stage", "xml_generation",
                "--xml-dir", str(xml_dir),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("xml_variant_controller_default_mismatch", result.stdout)

    def test_variant_component_default_page_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir = self.add_instance_configuration_fixture(root, selected_page=1)
            result = self.run_script(
                "validate_semantic_controller_mapping.py",
                "--root", str(root),
                "--stage", "xml_generation",
                "--xml-dir", str(xml_dir),
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('"visualInstances": 1', result.stdout)
            self.assertIn('"instanceConfigurations": 1', result.stdout)

    def test_raw_localization_key_in_instance_preview_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir = self.add_instance_configuration_fixture(root, selected_page=1, raw_localization_key=True)
            result = self.run_script(
                "validate_semantic_controller_mapping.py",
                "--root", str(root),
                "--stage", "xml_generation",
                "--xml-dir", str(xml_dir),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("xml_preview_raw_localization_key", result.stdout)

    def test_component_reuse_single_component_plan_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_semantic_controller_specs(root)
            result = self.run_script(
                "validate_component_reuse.py",
                "--root", str(root),
                "--stage", "fairygui_assembly",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('"ok": true', result.stdout)

    def test_component_reuse_plan_missing_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_semantic_controller_specs(root)
            state_map_path = root / "specs" / "component_state_map.json"
            state_map = json.loads(state_map_path.read_text(encoding="utf-8"))
            del state_map["components"][0]["reusePlan"]
            state_map_path.write_text(json.dumps(state_map, ensure_ascii=False, indent=2), encoding="utf-8")
            result = self.run_script(
                "validate_component_reuse.py",
                "--root", str(root),
                "--stage", "semantic_analysis",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("component_reuse_plan_missing", result.stdout)

    def test_single_component_cannot_use_variant_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_semantic_controller_specs(root)
            state_map_path = root / "specs" / "component_state_map.json"
            state_map = json.loads(state_map_path.read_text(encoding="utf-8"))
            state_map["visualInstances"] = [
                {
                    "instanceId": "slot_ready",
                    "componentType": "EquipmentSlot",
                    "xmlInstanceName": "slot_ready",
                    "stateVariant": "ready",
                    "controllerPages": {"state": "ready"},
                    "requirementIds": ["REQ-EQUIPMENT-STATE"],
                    "implementation": {
                        "configurationMode": "variant_component",
                        "componentFile": "equipment_slot_ready.xml",
                        "previewValues": {"state": "ready"},
                        "runtimeBindings": ["state"],
                    },
                }
            ]
            state_map_path.write_text(json.dumps(state_map, ensure_ascii=False, indent=2), encoding="utf-8")
            result = self.run_script(
                "validate_component_reuse.py",
                "--root", str(root),
                "--stage", "semantic_analysis",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("variant_component_forbidden_by_reuse_plan", result.stdout)

    def test_extension_override_field_must_be_declared(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_semantic_controller_specs(root)
            state_map_path = root / "specs" / "component_state_map.json"
            state_map = json.loads(state_map_path.read_text(encoding="utf-8"))
            state_map["components"][0]["reusePlan"]["extension"] = "Label"
            state_map["components"][0]["reusePlan"]["parameterizableFields"] = ["Label.title"]
            state_map["visualInstances"] = [
                {
                    "instanceId": "slot_ready",
                    "componentType": "EquipmentSlot",
                    "xmlInstanceName": "slot_ready",
                    "stateVariant": "ready",
                    "controllerPages": {"state": "ready"},
                    "requirementIds": ["REQ-EQUIPMENT-STATE"],
                    "implementation": {
                        "configurationMode": "extension_override",
                        "componentFile": "equipment_slot.xml",
                        "extensionParameters": {
                            "Label": {"title": "READY", "icon": "ui://qdf53qpkabc12"}
                        },
                        "previewValues": {"state": "ready"},
                        "runtimeBindings": ["state"],
                    },
                }
            ]
            state_map_path.write_text(json.dumps(state_map, ensure_ascii=False, indent=2), encoding="utf-8")
            result = self.run_script(
                "validate_component_reuse.py",
                "--root", str(root),
                "--stage", "semantic_analysis",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("extension_parameter_not_declared", result.stdout)

    def test_xml_extension_override_field_must_be_declared(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_semantic_controller_specs(root)
            state_map_path = root / "specs" / "component_state_map.json"
            state_map = json.loads(state_map_path.read_text(encoding="utf-8"))
            state_map["components"][0]["reusePlan"]["extension"] = "Label"
            state_map["components"][0]["reusePlan"]["parameterizableFields"] = ["Label.title"]
            state_map_path.write_text(json.dumps(state_map, ensure_ascii=False, indent=2), encoding="utf-8")

            fgui_spec_path = root / "specs" / "fgui_spec.md"
            fgui_spec = fgui_spec_path.read_text(encoding="utf-8").replace(
                "| EquipmentSlot | single_component | equipment_slot.xml | none | controller.state,runtime.foodId,runtime.state | none | none | REQ-EQUIPMENT-STATE |",
                "| EquipmentSlot | single_component | equipment_slot.xml | Label | Label.title | none | none | REQ-EQUIPMENT-STATE |",
            )
            fgui_spec_path.write_text(fgui_spec, encoding="utf-8")

            xml_dir = root / "fgui_xml" / "cooking"
            xml_dir.mkdir(parents=True, exist_ok=True)
            (xml_dir / "equipment_slot.xml").write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<component size="320,280" extention="Label"><displayList/></component>
""",
                encoding="utf-8",
            )
            (xml_dir / "cooking_view.xml").write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<component size="1920,1080"><displayList>
  <component id="n0_3qpk" name="slot" src="slot1" fileName="equipment_slot.xml" xy="0,0" size="320,280">
    <Label title="READY" icon="ui://qdf53qpkabc12"/>
  </component>
</displayList></component>
""",
                encoding="utf-8",
            )
            result = self.run_script(
                "validate_component_reuse.py",
                "--root", str(root),
                "--stage", "xml_generation",
                "--xml-dir", str(xml_dir),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("xml_extension_parameter_not_declared", result.stdout)

    def test_duplicate_variant_structure_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir = self.add_instance_configuration_fixture(root, selected_page=1)
            base_xml = (xml_dir / "equipment_slot.xml").read_text(encoding="utf-8")
            renamed_duplicate = base_xml.replace("highlight_ready", "renamed_highlight")
            (xml_dir / "equipment_slot_ready.xml").write_text(renamed_duplicate, encoding="utf-8")
            result = self.run_script(
                "validate_component_reuse.py",
                "--root", str(root),
                "--stage", "xml_generation",
                "--xml-dir", str(xml_dir),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate_variant_structure_should_reuse_base", result.stdout)

    def test_composite_component_must_reference_declared_child(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_semantic_controller_specs(root)
            state_map_path = root / "specs" / "component_state_map.json"
            state_map = json.loads(state_map_path.read_text(encoding="utf-8"))
            state_map["components"][0]["reusePlan"] = {
                "strategy": "composite_component",
                "baseComponentFile": "equipment_slot.xml",
                "extension": "none",
                "parameterizableFields": ["controller.state"],
                "childComponentFiles": ["stat_item.xml"],
                "variantReasons": [],
            }
            state_map_path.write_text(json.dumps(state_map, ensure_ascii=False, indent=2), encoding="utf-8")

            fgui_spec_path = root / "specs" / "fgui_spec.md"
            fgui_spec = fgui_spec_path.read_text(encoding="utf-8").replace(
                "| EquipmentSlot | single_component | equipment_slot.xml | none | controller.state,runtime.foodId,runtime.state | none | none | REQ-EQUIPMENT-STATE |",
                "| EquipmentSlot | composite_component | equipment_slot.xml | none | controller.state | stat_item.xml | none | REQ-EQUIPMENT-STATE |",
            )
            fgui_spec_path.write_text(fgui_spec, encoding="utf-8")

            xml_dir = root / "fgui_xml" / "cooking"
            xml_dir.mkdir(parents=True, exist_ok=True)
            (xml_dir / "equipment_slot.xml").write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<component size="320,280"><displayList/></component>
""",
                encoding="utf-8",
            )
            (xml_dir / "stat_item.xml").write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<component size="120,40" extention="Label"><displayList/></component>
""",
                encoding="utf-8",
            )
            result = self.run_script(
                "validate_component_reuse.py",
                "--root", str(root),
                "--stage", "xml_generation",
                "--xml-dir", str(xml_dir),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("composite_child_reuse_plan_missing", result.stdout)
            self.assertIn("composite_child_not_referenced", result.stdout)

    def add_exported_controller_fixture(
        self,
        root: Path,
        *,
        exported: bool = True,
        parent_encoding: str = "state,1",
    ) -> Path:
        self.add_semantic_controller_specs(root)
        state_map_path = root / "specs" / "component_state_map.json"
        state_map = json.loads(state_map_path.read_text(encoding="utf-8"))
        state_map["visualInstances"] = [
            {
                "instanceId": "equipment_slot_left_01",
                "componentType": "EquipmentSlot",
                "xmlInstanceName": "equipment_slot_left",
                "stateVariant": "ready",
                "controllerPages": {"state": "ready"},
                "slotRole": "cook_source",
                "requirementIds": ["REQ-EQUIPMENT-STATE"],
                "implementation": {
                    "configurationMode": "controller_pages",
                    "componentFile": "equipment_slot.xml",
                    "controllerParameters": {"state": "ready"},
                    "previewValues": {"state": "ready"},
                    "runtimeBindings": ["state"],
                },
            }
        ]
        state_map_path.write_text(json.dumps(state_map, ensure_ascii=False, indent=2), encoding="utf-8")

        fgui_spec_path = root / "specs" / "fgui_spec.md"
        fgui_spec = fgui_spec_path.read_text(encoding="utf-8")
        fgui_spec = fgui_spec.replace(
            "| equipment_slot | state | idle,ready | idle | false | highlight_ready | REQ-EQUIPMENT-STATE | FGUI |",
            f"| equipment_slot | state | idle,ready | idle | {'true' if exported else 'false'} | highlight_ready | REQ-EQUIPMENT-STATE | FGUI |",
        )
        instance_table = """## Instance Configuration

| Instance ID | XML Name | Component Type | Component File | Configuration Mode | Controller Pages | Controller Parameters | Extension Parameters | Preview Values | Runtime Bindings | Requirement IDs |
|---|---|---|---|---|---|---|---|---|---|---|
| equipment_slot_left_01 | equipment_slot_left | EquipmentSlot | equipment_slot.xml | controller_pages | state=ready | state=ready | none | state=ready | state | REQ-EQUIPMENT-STATE |

"""
        fgui_spec = fgui_spec.replace("## Transitions", instance_table + "## Transitions")
        fgui_spec_path.write_text(fgui_spec, encoding="utf-8")

        xml_dir = root / "fgui_xml" / "cooking"
        xml_dir.mkdir(parents=True, exist_ok=True)
        exported_attr = ' exported="true"' if exported else ""
        (xml_dir / "equipment_slot.xml").write_text(
            f"""<?xml version="1.0" encoding="utf-8"?>
<component size="320,280">
  <controller name="state"{exported_attr} pages="0,idle,1,ready" selected="0"/>
  <displayList>
    <group id="n1_3qpk" name="highlight_ready">
      <gearDisplay controller="state" pages="1"/>
    </group>
  </displayList>
</component>
""",
            encoding="utf-8",
        )
        (xml_dir / "cooking_view.xml").write_text(
            f"""<?xml version="1.0" encoding="utf-8"?>
<component size="1920,1080">
  <displayList>
    <image id="n0_3qpk" name="bg_main" src="abc12" fileName="art/bg_main.png" size="1920,1080"/>
    <component id="n1_3qpk" name="equipment_slot_left" src="slot1" fileName="equipment_slot.xml" xy="100,200" size="320,280" controller="{parent_encoding}"/>
  </displayList>
</component>
""",
            encoding="utf-8",
        )
        return xml_dir

    def test_exported_controller_parameter_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir = self.add_exported_controller_fixture(root)
            result = self.run_script(
                "validate_semantic_controller_mapping.py",
                "--root", str(root),
                "--stage", "xml_generation",
                "--xml-dir", str(xml_dir),
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('"ok": true', result.stdout)

    def test_controller_parameter_requires_exported_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir = self.add_exported_controller_fixture(root, exported=False)
            result = self.run_script(
                "validate_semantic_controller_mapping.py",
                "--root", str(root),
                "--stage", "xml_generation",
                "--xml-dir", str(xml_dir),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("fgui_controller_not_exported", result.stdout)
            self.assertIn("xml_controller_not_exported", result.stdout)

    def test_controller_parameter_page_index_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir = self.add_exported_controller_fixture(root, parent_encoding="state,0")
            result = self.run_script(
                "validate_semantic_controller_mapping.py",
                "--root", str(root),
                "--stage", "xml_generation",
                "--xml-dir", str(xml_dir),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("xml_instance_controller_encoding_mismatch", result.stdout)

    def test_display_list_background_after_content_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_semantic_controller_specs(root)
            fgui_spec_path = root / "specs" / "fgui_spec.md"
            text = fgui_spec_path.read_text(encoding="utf-8")
            text = text.replace(
                "| cooking_view | 0 | bg_main | image | bg_main | abc12 | 0,0 | 1920,1080 | asset_manifest.displaySize | background | opaque_background | bgMain |",
                "| cooking_view | 1 | bg_main | image | bg_main | abc12 | 0,0 | 1920,1080 | asset_manifest.displaySize | background | opaque_background | bgMain |",
            ).replace(
                "| cooking_view | 1 | equipment_slot_left | component | none | equipment_slot | 100,200 | 320,280 | layout_spec.bbox | content | normal | equipmentSlotLeft |",
                "| cooking_view | 0 | equipment_slot_left | component | none | equipment_slot | 100,200 | 320,280 | layout_spec.bbox | content | normal | equipmentSlotLeft |",
            )
            fgui_spec_path.write_text(text, encoding="utf-8")
            result = self.run_script(
                "validate_display_list_z_order.py",
                "--root", str(root),
                "--stage", "fairygui_assembly",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("opaque_background_not_backmost", result.stdout)
            self.assertIn("display_list_z_layer_order_invalid", result.stdout)

    def test_xml_display_list_background_after_content_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.add_semantic_controller_specs(root)
            xml_dir = root / "fgui_xml" / "cooking"
            xml_dir.mkdir(parents=True, exist_ok=True)
            (xml_dir / "cooking_view.xml").write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<component size="1920,1080"><displayList>
  <component id="n1_3qpk" name="equipment_slot_left" src="slot1" fileName="equipment_slot.xml" xy="100,200" size="320,280"/>
  <image id="n0_3qpk" name="bg_main" src="abc12" fileName="art/bg_main.png" size="1920,1080"/>
</displayList></component>
""",
                encoding="utf-8",
            )
            (xml_dir / "equipment_slot.xml").write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<component size="320,280"><displayList/></component>
""",
                encoding="utf-8",
            )
            result = self.run_script(
                "validate_display_list_z_order.py",
                "--root", str(root),
                "--stage", "xml_generation",
                "--xml-dir", str(xml_dir),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("xml_display_list_order_mismatch", result.stdout)
            self.assertIn("xml_opaque_background_not_backmost", result.stdout)

    def add_icon_asset(
        self,
        root: Path,
        *,
        asset_source: dict[str, object] | None,
    ) -> None:
        manifest_path = root / "manifests" / "asset_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        asset = {
            "name": "icon_test",
            "file": "fgui_xml/cooking/art/icon_test.png",
            "packageRelativeFile": "art/icon_test.png",
            "type": "icon",
            "sourcePixelSize": [48, 48],
            "displaySize": [48, 48],
            "scalePolicy": "pixel_exact",
            "renderMode": "normal",
            "transparent": True,
            "pivot": "center",
            "fgui": {"resourceType": "image", "nodeType": "image", "layer": "icon"},
        }
        if asset_source is not None:
            asset["assetSource"] = asset_source
        manifest["assets"].append(asset)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        write_png(root / "fgui_xml" / "cooking" / "art" / "icon_test.png", 48, 48, alpha=True)

    def test_icon_bitmap_provenance_passes_for_provided_bitmap(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            self.add_icon_asset(
                root,
                asset_source={
                    "mode": "provided_bitmap",
                    "sourceFile": "references/ui_reference.png",
                    "reviewStatus": "approved",
                },
            )
            result = self.run_script(
                "validate_bitmap_asset_provenance.py",
                "--root", str(root),
                "--stage", "asset_planning",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_icon_missing_bitmap_provenance_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            self.add_icon_asset(root, asset_source=None)
            result = self.run_script(
                "validate_bitmap_asset_provenance.py",
                "--root", str(root),
                "--stage", "asset_planning",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("icon_asset_source_missing", result.stdout)

    def test_procedural_icon_generator_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            self.add_icon_asset(
                root,
                asset_source={
                    "mode": "provided_bitmap",
                    "sourceFile": "references/ui_reference.png",
                    "reviewStatus": "approved",
                },
            )
            scripts = root / "scripts"
            scripts.mkdir(parents=True, exist_ok=True)
            (scripts / "generate_icons.py").write_text(
                "from PIL import ImageDraw\n# icon_test\nd = ImageDraw.Draw(None)\nd.polygon([(0,0),(1,1)])\n",
                encoding="utf-8",
            )
            result = self.run_script(
                "validate_bitmap_asset_provenance.py",
                "--root", str(root),
                "--stage", "asset_planning",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("procedural_icon_generator_detected", result.stdout)

    def test_icon_visual_part_cannot_use_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            self.add_semantic_controller_specs(root)
            coverage_path = root / "specs" / "component_visual_parts.json"
            coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
            part = coverage["components"][0]["parts"][0]
            part["partId"] = "status_icon"
            part["role"] = "status_icon"
            part["implementation"]["mode"] = "graph"
            coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")
            result = self.run_script(
                "validate_visual_part_coverage.py",
                "--root", str(root),
                "--stage", "asset_planning",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("icon_visual_part_graph_forbidden", result.stdout)

    def test_visual_part_role_is_project_defined_not_hardcoded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            self.add_semantic_controller_specs(root)
            coverage_path = root / "specs" / "component_visual_parts.json"
            coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
            coverage["components"][0]["parts"][0]["role"] = "project_specific_ornament_marker"
            coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")
            result = self.run_script(
                "validate_visual_part_coverage.py",
                "--root", str(root),
                "--stage", "asset_planning",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('"ok": true', result.stdout)

    def test_missing_visual_part_asset_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            self.add_semantic_controller_specs(root)
            coverage_path = root / "specs" / "component_visual_parts.json"
            coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
            implementation = coverage["components"][0]["parts"][0]["implementation"]
            implementation["mode"] = "asset_image"
            implementation["assetName"] = "missing_required_icon"
            coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")
            result = self.run_script(
                "validate_visual_part_coverage.py",
                "--root", str(root),
                "--stage", "asset_planning",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing_visual_part_asset", result.stdout)

    def test_detailed_visual_part_graph_without_human_approval_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            self.add_semantic_controller_specs(root)
            coverage_path = root / "specs" / "component_visual_parts.json"
            coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
            part = coverage["components"][0]["parts"][0]
            part["complexity"] = "detailed"
            part["implementation"]["mode"] = "graph"
            part["implementation"]["fallbackPolicy"] = "forbidden"
            coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")
            result = self.run_script(
                "validate_visual_part_coverage.py",
                "--root", str(root),
                "--stage", "asset_planning",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("visual_part_degraded_to_graph_without_approval", result.stdout)

    def test_required_visual_part_xml_node_missing_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            self.add_semantic_controller_specs(root)
            xml_dir = root / "fgui_xml" / "cooking"
            (xml_dir / "equipment_slot.xml").write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<component size="320,280">
  <controller name="state" pages="0,idle,1,ready" selected="0"/>
  <displayList/>
</component>
""",
                encoding="utf-8",
            )
            result = self.run_script(
                "validate_visual_part_coverage.py",
                "--root", str(root),
                "--stage", "xml_generation",
                "--xml-dir", str(xml_dir),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("xml_visual_part_missing", result.stdout)

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
        manifest["production"].update({
            "generateFullScreenDesign": True,
            "requiresDesignApproval": True,
            "requiresVisualPartCoverage": True,
            "requiresAssetIsolation": True,
            "requiresProductionPreviewLineage": True,
            "requiresTypographyFidelity": True,
        })
        background = manifest["assets"][0]
        background["assetSource"] = {
            "mode": "provided_bitmap",
            "sourceFile": "fgui_xml/cooking/art/bg_main.png",
        }
        background["assetIsolation"] = {
            "role": "environment_background",
            "cleanEnvironmentOnly": True,
            "forbidBakedText": True,
            "containsBakedText": False,
            "containsDynamicChildContent": False,
            "occlusionPolicy": "not_occluded",
            "reviewStatus": "approved",
            "reviewedBy": "user",
            "reviewType": "user_confirmation",
            "reviewEvidence": "reports/asset_isolation_review.md",
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        reports = root / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        (reports / "asset_isolation_review.md").write_text(
            "# Asset Isolation Review\n\n- status: approved\n",
            encoding="utf-8",
        )

        preview_path = root / "generated" / "preview" / "assembled_screen.png"
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        write_png(preview_path, 1920, 1080)
        runtime_path = root / "fgui_xml" / "cooking" / "art" / "bg_main.png"
        preview_hash = hashlib.sha256(preview_path.read_bytes()).hexdigest()
        runtime_hash = hashlib.sha256(runtime_path.read_bytes()).hexdigest()

        scripts = root / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        (scripts / "render_production_preview.py").write_text(
            "# exact runtime asset: bg_main / art/bg_main.png\n",
            encoding="utf-8",
        )
        lineage = {
            "version": "0.1.0",
            "screen": "cooking_view",
            "fidelityMode": "exact_production_composite",
            "productionPreview": {
                "file": "generated/preview/assembled_screen.png",
                "sha256": preview_hash,
                "rendererScript": "scripts/render_production_preview.py",
                "usesProductionAssets": True,
                "approvalRecord": "reports/production_preview_approval.json",
            },
            "assets": [{
                "assetName": "bg_main",
                "runtimeFile": "fgui_xml/cooking/art/bg_main.png",
                "runtimeSha256": runtime_hash,
                "previewUsage": "exact_file",
                "sourceLineage": {
                    "designRelation": "exact_provided_source",
                    "derivationMode": "exact_file",
                    "sourceFile": "fgui_xml/cooking/art/bg_main.png",
                    "sourceSha256": runtime_hash,
                },
            }],
            "blockingForXml": False,
        }
        (root / "specs" / "production_preview_lineage.json").write_text(
            json.dumps(lineage, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        approval = {
            "version": "0.1.0",
            "status": "approved",
            "approvedFile": "generated/preview/assembled_screen.png",
            "approvedFileSha256": preview_hash,
            "approvedAssetHashes": {"bg_main": runtime_hash},
            "confirmation": {
                "type": "user_confirmation",
                "recordedBy": "user",
                "note": "User approved exact production preview.",
                "confirmedAt": "2026-07-21T00:00:00Z",
            },
        }
        (reports / "production_preview_approval.json").write_text(
            json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        typography = {
            "version": "0.1.0",
            "screen": "cooking_view",
            "containsText": False,
            "fidelityMode": "exact",
            "reviewStatus": "approved",
            "review": {
                "type": "user_confirmation",
                "recordedBy": "user",
                "note": "This fixture intentionally contains no text.",
            },
            "blockingForXml": False,
        }
        typography_path = root / "specs" / "typography_spec.json"
        typography_path.write_text(
            json.dumps(typography, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        lineage_path = root / "specs" / "production_preview_lineage.json"
        approval_path = reports / "production_preview_approval.json"
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        approval["approvedEvidenceHashes"] = {
            "productionPreviewLineage": hashlib.sha256(lineage_path.read_bytes()).hexdigest(),
            "typographySpec": hashlib.sha256(typography_path.read_bytes()).hexdigest(),
        }
        approval_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")

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
            self.add_semantic_controller_specs(root)

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
            self.add_semantic_controller_specs(root)

            result = self.run_script(
                "check_xml_readiness.py",
                "--root", str(root),
                "--full-xml-spec", str(full_spec),
                "--profile", "fresh",
                "--resource-generation",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('"designApproved": true', result.stdout)
            self.assertIn('"componentReuse": true', result.stdout)
            self.assertIn('"displayListZOrder": true', result.stdout)
            self.assertIn('"bitmapAssetProvenance": true', result.stdout)

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

    def test_package_xml_project_relative_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir, _ = self.create_project(root)
            package_path = xml_dir / "package.xml"
            package_path.write_text(
                package_path.read_text(encoding="utf-8").replace(
                    'name="bg_main.png" path="/art/"',
                    'name="fgui_xml/cooking/art/bg_main.png" path="/"',
                ),
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
            self.assertIn("package.xml 资源文件不存在", result.stdout)
            self.assertIn("packageRelativeFile", result.stdout)

    def test_component_image_project_relative_file_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir, _ = self.create_project(root)
            component_path = xml_dir / "cooking_view.xml"
            component_path.write_text(
                component_path.read_text(encoding="utf-8").replace(
                    'fileName="art/bg_main.png"',
                    'fileName="fgui_xml/cooking/art/bg_main.png"',
                ),
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
            self.assertIn("精确包内路径", result.stdout)
            self.assertIn("在包目录中不存在", result.stdout)

    def add_external_controller_parameter(
        self,
        root: Path,
        *,
        exported: bool = True,
        encoding: str = "state,1",
    ) -> Path:
        xml_dir = root / "fgui_xml" / "cooking"
        registry_path = root / "manifests" / "fgui_id_registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["packages"]["cooking"]["resources"]["equipment_slot.xml"] = "slot1"
        registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")

        package_path = xml_dir / "package.xml"
        package_path.write_text(
            package_path.read_text(encoding="utf-8").replace(
                "  </resources>",
                '    <component id="slot1" name="equipment_slot.xml" path="/" exported="true"/>\n  </resources>',
            ),
            encoding="utf-8",
        )
        exported_attr = ' exported="true"' if exported else ""
        (xml_dir / "equipment_slot.xml").write_text(
            f"""<?xml version="1.0" encoding="utf-8"?>
<component size="320,280">
  <controller name="state"{exported_attr} pages="0,idle,1,ready" selected="0"/>
  <displayList/>
</component>
""",
            encoding="utf-8",
        )
        component_path = xml_dir / "cooking_view.xml"
        component_path.write_text(
            component_path.read_text(encoding="utf-8").replace(
                "  </displayList>",
                f'    <component id="n1_3qpk" name="equipment_slot" src="slot1" fileName="equipment_slot.xml" xy="10,10" size="320,280" controller="{encoding}"/>\n  </displayList>',
            ),
            encoding="utf-8",
        )
        return xml_dir

    def test_generic_external_controller_parameter_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            xml_dir = self.add_external_controller_parameter(root)
            result = self.run_script(
                "validate_fgui_xml.py",
                "--xml-dir", str(xml_dir),
                "--manifest", str(root / "manifests" / "asset_manifest.json"),
                "--registry", str(root / "manifests" / "fgui_id_registry.json"),
                "--mode", "fresh",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('"component_controller_parameters_checked": true', result.stdout)

    def test_generic_external_controller_must_be_exported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            xml_dir = self.add_external_controller_parameter(root, exported=False)
            result = self.run_script(
                "validate_fgui_xml.py",
                "--xml-dir", str(xml_dir),
                "--manifest", str(root / "manifests" / "asset_manifest.json"),
                "--registry", str(root / "manifests" / "fgui_id_registry.json"),
                "--mode", "fresh",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("未设置 exported", result.stdout)

    def test_generic_external_controller_index_must_be_in_range(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            xml_dir = self.add_external_controller_parameter(root, encoding="state,2")
            result = self.run_script(
                "validate_fgui_xml.py",
                "--xml-dir", str(xml_dir),
                "--manifest", str(root / "manifests" / "asset_manifest.json"),
                "--registry", str(root / "manifests" / "fgui_id_registry.json"),
                "--mode", "fresh",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("页索引越界", result.stdout)

    def test_fresh_controller_pages_require_id_name_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir, _ = self.create_project(root)
            component_path = xml_dir / "cooking_view.xml"
            component_path.write_text(
                component_path.read_text(encoding="utf-8").replace(
                    "  <displayList>",
                    '  <controller name="state" pages="idle,ready" selected="0"/>\n  <displayList>',
                ),
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
            self.assertIn("数字 pageId,pageName 成对序列", result.stdout)

    def test_gear_look_requires_five_serialized_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            xml_dir, _ = self.create_project(root)
            component_path = xml_dir / "cooking_view.xml"
            xml = component_path.read_text(encoding="utf-8")
            xml = xml.replace(
                "  <displayList>",
                '  <controller name="state" pages="0,normal,1,disabled" selected="0"/>\n  <displayList>',
            ).replace(
                '    <image id="n0_3qpk" name="bg_main" src="abc12" fileName="art/bg_main.png" size="1920,1080"/>',
                '    <image id="n0_3qpk" name="bg_main" src="abc12" fileName="art/bg_main.png" size="1920,1080">\n'
                '      <gearLook controller="state" pages="0,1" values="1,0,1,0|0.5,0,1,1" default="1,0,1,0"/>\n'
                '    </image>',
            )
            component_path.write_text(xml, encoding="utf-8")
            result = self.run_script(
                "validate_fgui_xml.py",
                "--xml-dir", str(xml_dir),
                "--manifest", str(root / "manifests" / "asset_manifest.json"),
                "--registry", str(root / "manifests" / "fgui_id_registry.json"),
                "--mode", "fresh",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("gearLook 每个 values 状态必须包含 5 个字段", result.stdout)
            self.assertIn("gearLook@default 必须包含 5 个字段", result.stdout)

    def add_external_button_override(
        self,
        root: Path,
        *,
        target_extension: str = "Button",
        override_tag: str = "Button",
        icon_url: str = "ui://qdf53qpkabc12",
        extra_attribute: str = "",
    ) -> Path:
        xml_dir = root / "fgui_xml" / "cooking"
        registry_path = root / "manifests" / "fgui_id_registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["packages"]["cooking"]["resources"]["btn_action.xml"] = "btn01"
        registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")

        package_path = xml_dir / "package.xml"
        package_path.write_text(
            package_path.read_text(encoding="utf-8").replace(
                "  </resources>",
                '    <component id="btn01" name="btn_action.xml" path="/" exported="true"/>\n  </resources>',
            ),
            encoding="utf-8",
        )

        extension_node = target_extension if target_extension in {"Button", "Label"} else "Button"
        (xml_dir / "btn_action.xml").write_text(
            f'''<?xml version="1.0" encoding="utf-8"?>
<component size="240,80" extention="{target_extension}">
  <displayList>
    <text id="n0_3qpk" name="title" xy="48,10" size="180,60"/>
    <loader id="n1_3qpk" name="icon" xy="8,8" size="40,40"/>
  </displayList>
  <{extension_node}/>
</component>
''',
            encoding="utf-8",
        )

        component_path = xml_dir / "cooking_view.xml"
        extra = f" {extra_attribute}" if extra_attribute else ""
        component_path.write_text(
            component_path.read_text(encoding="utf-8").replace(
                "  </displayList>",
                f'''    <component id="n1_3qpk" name="btn_confirm" src="btn01" fileName="btn_action.xml" xy="10,10" size="240,80">
      <{override_tag} title="@ui_confirm" icon="{icon_url}"{extra}/>
    </component>
  </displayList>''',
            ),
            encoding="utf-8",
        )
        return xml_dir

    def test_external_button_title_and_icon_override_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            xml_dir = self.add_external_button_override(root)
            result = self.run_script(
                "validate_fgui_xml.py",
                "--xml-dir", str(xml_dir),
                "--manifest", str(root / "manifests" / "asset_manifest.json"),
                "--registry", str(root / "manifests" / "fgui_id_registry.json"),
                "--mode", "fresh",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('"component_extension_overrides_checked": true', result.stdout)

    def test_external_label_title_and_icon_override_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            xml_dir = self.add_external_button_override(root, target_extension="Label", override_tag="Label")
            result = self.run_script(
                "validate_fgui_xml.py",
                "--xml-dir", str(xml_dir),
                "--manifest", str(root / "manifests" / "asset_manifest.json"),
                "--registry", str(root / "manifests" / "fgui_id_registry.json"),
                "--mode", "fresh",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('"component_extension_overrides_checked": true', result.stdout)

    def test_external_override_extension_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            xml_dir = self.add_external_button_override(root, target_extension="Label", override_tag="Button")
            result = self.run_script(
                "validate_fgui_xml.py",
                "--xml-dir", str(xml_dir),
                "--manifest", str(root / "manifests" / "asset_manifest.json"),
                "--registry", str(root / "manifests" / "fgui_id_registry.json"),
                "--mode", "fresh",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("extention 不匹配", result.stdout)

    def test_external_override_unregistered_icon_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            xml_dir = self.add_external_button_override(root, icon_url="ui://qdf53qpkbad99")
            result = self.run_script(
                "validate_fgui_xml.py",
                "--xml-dir", str(xml_dir),
                "--manifest", str(root / "manifests" / "asset_manifest.json"),
                "--registry", str(root / "manifests" / "fgui_id_registry.json"),
                "--mode", "fresh",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("引用未注册资源", result.stdout)

    def test_external_override_unsupported_attribute_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            xml_dir = self.add_external_button_override(root, extra_attribute='bogus="x"')
            result = self.run_script(
                "validate_fgui_xml.py",
                "--xml-dir", str(xml_dir),
                "--manifest", str(root / "manifests" / "asset_manifest.json"),
                "--registry", str(root / "manifests" / "fgui_id_registry.json"),
                "--mode", "fresh",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("不支持的属性", result.stdout)

    def test_fresh_button_enum_spelling_is_strict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.create_project(root)
            xml_dir = self.add_external_button_override(
                root,
                extra_attribute='mode="Common" downEffect="dark"',
            )
            result = self.run_script(
                "validate_fgui_xml.py",
                "--xml-dir", str(xml_dir),
                "--manifest", str(root / "manifests" / "asset_manifest.json"),
                "--registry", str(root / "manifests" / "fgui_id_registry.json"),
                "--mode", "fresh",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Button@mode 必须使用小写合法值", result.stdout)
            self.assertIn("Button@downEffect 必须使用合法值", result.stdout)

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
