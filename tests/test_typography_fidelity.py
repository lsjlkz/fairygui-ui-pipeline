from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_typography_fidelity.py"
spec = importlib.util.spec_from_file_location("validate_typography_fidelity", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


class TypographyFidelityTests(unittest.TestCase):
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
        })
        report = module.validate(root)
        self.assertIn("typography_fidelity_not_required", self.codes(report))

    def test_hardcoded_preview_font_is_rejected(self) -> None:
        root = self.root()
        renderer = root / "scripts" / "render.py"
        renderer.parent.mkdir()
        renderer.write_text("ImageFont.truetype('Arial.ttf', 20)", encoding="utf-8")
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresTypographyFidelity": True,
            },
        })
        write_json(root / "specs" / "typography_spec.json", {
            "fidelityMode": "exact",
            "productionPreview": {
                "file": "generated/preview/screen.png",
                "textRenderingMode": "deterministic_text_overlay",
                "rendererScript": "scripts/render.py",
                "renderTrace": "reports/typography_render_trace.json",
                "usesTypographySpec": True,
            },
            "styles": [{
                "styleId": "title",
                "xmlAttributes": {
                    "font": "Arial",
                    "fontSize": "20",
                    "color": "#ffffff",
                    "align": "center",
                    "vAlign": "middle",
                    "autoSize": "none",
                    "singleLine": "true",
                },
            }],
            "instances": [{
                "componentFile": "panel.xml",
                "xmlNodeName": "title",
                "styleId": "title",
                "previewText": "TITLE",
                "bbox": [0, 0, 100, 30],
            }],
            "reviewStatus": "approved",
            "review": {"type": "user_confirmation", "recordedBy": "user"},
        })
        report = module.validate(root, "fairygui_assembly")
        self.assertIn("preview_renderer_does_not_load_typography_spec", self.codes(report))
        self.assertIn("preview_renderer_hardcoded_font", self.codes(report))

    def test_xml_attributes_must_match(self) -> None:
        root = self.root()
        renderer = root / "scripts" / "render.py"
        renderer.parent.mkdir()
        renderer.write_text("typography_spec.json", encoding="utf-8")
        xml_dir = root / "fgui_xml" / "pkg"
        xml_dir.mkdir(parents=True)
        (xml_dir / "panel.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<component size="100,30"><displayList>'
            '<text id="n0_abcd" name="title" xy="0,0" size="100,30" '
            'font="Arial" fontSize="18" color="#000000" align="center" '
            'vAlign="middle" autoSize="none" singleLine="true" '
            'text="TITLE" customData="loc:ui_title"/>'
            '</displayList></component>',
            encoding="utf-8",
        )
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresTypographyFidelity": True,
            },
            "package": {"outputPath": "fgui_xml/pkg"},
        })
        typography_spec = {
            "fidelityMode": "exact",
            "productionPreview": {
                "file": "generated/preview/screen.png",
                "textRenderingMode": "deterministic_text_overlay",
                "rendererScript": "scripts/render.py",
                "renderTrace": "reports/typography_render_trace.json",
                "usesTypographySpec": True,
            },
            "styles": [{
                "styleId": "title",
                "xmlAttributes": {
                    "font": "Arial",
                    "fontSize": "20",
                    "color": "#ffffff",
                    "align": "center",
                    "vAlign": "middle",
                    "autoSize": "none",
                    "singleLine": "true",
                },
            }],
            "instances": [{
                "componentFile": "panel.xml",
                "xmlNodeName": "title",
                "styleId": "title",
                "previewText": "TITLE",
                "localizationKey": "ui_title",
                "bbox": [0, 0, 100, 30],
            }],
            "reviewStatus": "approved",
            "review": {"type": "user_confirmation", "recordedBy": "user"},
        }
        typography_spec_path = root / "specs" / "typography_spec.json"
        write_json(typography_spec_path, typography_spec)
        write_json(root / "reports" / "typography_render_trace.json", {
            "typographySpecSha256": sha256(typography_spec_path.read_bytes()).hexdigest(),
            "rendererScript": "scripts/render.py",
            "previewFile": "generated/preview/screen.png",
            "instances": [{
                "componentFile": "panel.xml",
                "xmlNodeName": "title",
                "styleId": "title",
                "previewText": "TITLE",
                "bbox": [0, 0, 100, 30],
                "xmlAttributes": {
                    "font": "Arial",
                    "fontSize": "20",
                    "color": "#ffffff",
                    "align": "center",
                    "vAlign": "middle",
                    "autoSize": "none",
                    "singleLine": "true",
                },
            }],
        })
        report = module.validate(root, "xml_generation", xml_dir)
        self.assertIn("typography_xml_attribute_mismatch", self.codes(report))
        mismatch_messages = [
            item["message"] for item in report["issues"]
            if item["code"] == "typography_xml_attribute_mismatch"
        ]
        self.assertTrue(any("fontSize" in message for message in mismatch_messages))
        self.assertTrue(any("color" in message for message in mismatch_messages))
        text = (xml_dir / "panel.xml").read_text(encoding="utf-8")
        text = text.replace('fontSize="18"', 'fontSize="20"').replace('color="#000000"', 'color="#ffffff"')
        (xml_dir / "panel.xml").write_text(text, encoding="utf-8")
        report = module.validate(root, "xml_generation", xml_dir)
        self.assertTrue(report["ok"], report["issues"])

    def test_button_instance_typography_override_is_validated(self) -> None:
        root = self.root()
        renderer = root / "scripts" / "render.py"
        renderer.parent.mkdir()
        renderer.write_text("typography_spec.json", encoding="utf-8")
        xml_dir = root / "fgui_xml" / "pkg"
        xml_dir.mkdir(parents=True)
        (xml_dir / "action_button.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<component size="333,111" extention="Button"><displayList>'
            '<text id="n0_abcd" name="title" xy="20,12" size="293,84" '
            'font="Arial" fontSize="27" color="#f7ead0" align="center" '
            'vAlign="middle" autoSize="none" singleLine="true" '
            'text="ENTER STAGE" customData="loc:ui_enter_stage">'
            '<relation target="" sidePair="width-width,height-height"/>'
            '</text></displayList><Button title="ENTER STAGE" titleColor="#f7ead0" '
            'titleFontSize="27"/></component>',
            encoding="utf-8",
        )
        host_path = xml_dir / "main.xml"
        host_path.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<component size="1280,720"><displayList>'
            '<component id="n0_abcd" name="restart" xy="286,596" size="251,78" '
            'src="act01" fileName="action_button.xml" customData="loc:ui_restart">'
            '<Button title="RESTART" titleColor="#563a2b" titleFontSize="22"/>'
            '</component></displayList></component>',
            encoding="utf-8",
        )
        write_json(root / "manifests" / "asset_manifest.json", {
            "production": {
                "generateFullScreenDesign": True,
                "requiresTypographyFidelity": True,
            },
            "package": {"outputPath": "fgui_xml/pkg"},
        })
        typography_spec = {
            "fidelityMode": "exact",
            "productionPreview": {
                "file": "generated/preview/screen.png",
                "textRenderingMode": "deterministic_text_overlay",
                "rendererScript": "scripts/render.py",
                "renderTrace": "reports/typography_render_trace.json",
                "usesTypographySpec": True,
            },
            "styles": [{
                "styleId": "secondary_button_title",
                "xmlAttributes": {
                    "font": "Arial",
                    "fontSize": "22",
                    "color": "#563a2b",
                    "align": "center",
                    "vAlign": "middle",
                    "autoSize": "none",
                    "singleLine": "true",
                },
            }],
            "instances": [{
                "componentFile": "action_button.xml",
                "xmlNodeName": "title",
                "hostComponentFile": "main.xml",
                "hostInstanceName": "restart",
                "styleId": "secondary_button_title",
                "previewText": "RESTART",
                "localizationKey": "ui_restart",
                "bbox": [306, 608, 211, 51],
            }],
            "reviewStatus": "approved",
            "review": {"type": "user_confirmation", "recordedBy": "user"},
        }
        typography_spec_path = root / "specs" / "typography_spec.json"
        write_json(typography_spec_path, typography_spec)
        write_json(root / "reports" / "typography_render_trace.json", {
            "typographySpecSha256": sha256(typography_spec_path.read_bytes()).hexdigest(),
            "rendererScript": "scripts/render.py",
            "previewFile": "generated/preview/screen.png",
            "instances": [{
                "componentFile": "action_button.xml",
                "xmlNodeName": "title",
                "hostComponentFile": "main.xml",
                "hostInstanceName": "restart",
                "styleId": "secondary_button_title",
                "previewText": "RESTART",
                "bbox": [306, 608, 211, 51],
                "xmlAttributes": typography_spec["styles"][0]["xmlAttributes"],
            }],
        })
        report = module.validate(root, "xml_generation", xml_dir)
        self.assertTrue(report["ok"], report["issues"])

        host_path.write_text(
            host_path.read_text(encoding="utf-8").replace(
                'titleColor="#563a2b"', 'titleColor="#f7ead0"'
            ),
            encoding="utf-8",
        )
        report = module.validate(root, "xml_generation", xml_dir)
        messages = [
            item["message"] for item in report["issues"]
            if item["code"] == "typography_xml_attribute_mismatch"
        ]
        self.assertTrue(any("color" in message for message in messages), report["issues"])


if __name__ == "__main__":
    unittest.main()
