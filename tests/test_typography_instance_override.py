from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_typography_fidelity.py"
spec = importlib.util.spec_from_file_location("validate_typography_fidelity_instance", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


class TypographyInstanceOverrideTests(unittest.TestCase):
    def root(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def create_fixture(self) -> tuple[Path, Path, Path]:
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
        return root, xml_dir, host_path

    def test_button_instance_override_passes(self) -> None:
        root, xml_dir, _ = self.create_fixture()
        report = module.validate(root, "xml_generation", xml_dir)
        self.assertTrue(report["ok"], report["issues"])

    def test_button_instance_color_mismatch_is_rejected(self) -> None:
        root, xml_dir, host_path = self.create_fixture()
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

    def test_button_instance_bbox_mismatch_is_rejected(self) -> None:
        root, xml_dir, _ = self.create_fixture()
        spec_path = root / "specs" / "typography_spec.json"
        typography_spec = json.loads(spec_path.read_text(encoding="utf-8"))
        typography_spec["instances"][0]["bbox"] = [306, 607, 211, 56]
        write_json(spec_path, typography_spec)
        trace_path = root / "reports" / "typography_render_trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        trace["typographySpecSha256"] = sha256(spec_path.read_bytes()).hexdigest()
        trace["instances"][0]["bbox"] = [306, 607, 211, 56]
        write_json(trace_path, trace)
        report = module.validate(root, "xml_generation", xml_dir)
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("typography_xml_bbox_mismatch", codes)


if __name__ == "__main__":
    unittest.main()
