from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AssetIsolationIntegrationTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8-sig")

    def test_xml_readiness_integrates_asset_isolation(self) -> None:
        text = self.read("scripts/check_xml_readiness.py")
        self.assertIn("from validate_asset_isolation import validate as validate_asset_isolation", text)
        self.assertIn('"assetIsolation": None', text)
        self.assertIn('"assetIsolationApplicable": None', text)
        self.assertIn('"assetIsolationContract"', text)
        self.assertIn('"assetIsolationValidator"', text)
        self.assertIn('validate_asset_isolation(root, "xml_generation")', text)
        self.assertIn('production.get("requiresAssetIsolation") is not True', text)

    def test_pipeline_validator_integrates_asset_isolation(self) -> None:
        text = self.read("scripts/validate_pipeline.py")
        self.assertIn("from validate_asset_isolation import validate as validate_asset_isolation", text)
        self.assertIn('production.get("requiresAssetIsolation") is True', text)
        self.assertIn('validate_asset_isolation(project_root, "asset_planning")', text)
        self.assertIn('"asset_isolation_checked": False', text)
        self.assertIn('"asset_isolation_applicable": None', text)
        self.assertIn('"asset_isolation_status": None', text)

    def test_xml_validator_integrates_asset_isolation(self) -> None:
        text = self.read("scripts/validate_fgui_xml.py")
        self.assertIn("from validate_asset_isolation import validate as validate_asset_isolation", text)
        self.assertIn('validate_asset_isolation(project_root, "xml_generation", xml_dir)', text)
        self.assertIn('"asset_isolation_checked": asset_isolation_checked', text)
        self.assertIn('"asset_isolation_applicable": asset_isolation_applicable', text)

    def test_cut_report_lineage_is_enforced(self) -> None:
        validator = self.read("scripts/validate_asset_isolation.py")
        contract = self.read("references/asset-isolation-contract.md")
        self.assertIn("cut_report_source_mismatch", validator)
        self.assertIn("cut_report_exact_crop_pixel_mismatch", validator)
        self.assertIn("processorScriptSha256", contract)
        self.assertIn("cut_report.outputs[].sourceFile", contract)

    def test_contract_and_usage_are_linked(self) -> None:
        contract = ROOT / "references" / "asset-isolation-contract.md"
        self.assertTrue(contract.is_file())
        for relative in (
            "SKILL.md",
            "USAGE.md",
            "references/pipeline.md",
            "references/manifest-contract.md",
            "references/design-to-layout-contract.md",
            "references/xml-strict-generation.md",
            "references/fairygui-xml-contract.md",
        ):
            text = self.read(relative)
            self.assertIn("asset-isolation-contract.md", text, relative)
            self.assertIn("validate_asset_isolation.py", text, relative)


if __name__ == "__main__":
    unittest.main()
