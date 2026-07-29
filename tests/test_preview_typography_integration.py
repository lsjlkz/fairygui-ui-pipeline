from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PreviewTypographyIntegrationTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8-sig")

    def test_pipeline_validator_integrates_both_gates(self) -> None:
        text = self.read("scripts/validate_pipeline.py")
        self.assertIn("validate_production_preview_lineage", text)
        self.assertIn("validate_typography_fidelity", text)
        self.assertIn("requiresProductionPreviewLineage", text)
        self.assertIn("requiresTypographyFidelity", text)
        self.assertIn("production_preview_lineage_checked", text)
        self.assertIn("typography_fidelity_checked", text)
        self.assertIn("sourceLineage", self.read("references/production-preview-lineage-contract.md"))
        self.assertIn("typography_render_trace.json", self.read("references/typography-fidelity-contract.md"))

    def test_readiness_integrates_both_gates(self) -> None:
        text = self.read("scripts/check_xml_readiness.py")
        self.assertIn("productionPreviewLineage", text)
        self.assertIn("typographyFidelity", text)
        self.assertIn("production-preview-lineage-contract.md", text)
        self.assertIn("typography-fidelity-contract.md", text)
        self.assertIn('validate_production_preview_lineage(root, "xml_generation")', text)
        self.assertIn('validate_typography_fidelity(root, "xml_generation")', text)
        self.assertIn('source_paths["typographyRenderTrace"]', text)

    def test_xml_validator_integrates_both_gates(self) -> None:
        text = self.read("scripts/validate_fgui_xml.py")
        self.assertIn('validate_production_preview_lineage(project_root, "xml_generation")', text)
        self.assertIn('validate_typography_fidelity(project_root, "xml_generation", xml_dir)', text)
        self.assertIn('"production_preview_lineage_checked": production_preview_lineage_checked', text)
        self.assertIn('"typography_fidelity_checked": typography_fidelity_checked', text)

    def test_lineage_validator_checks_source_derivation(self) -> None:
        text = self.read("scripts/validate_production_preview_lineage.py")
        self.assertIn("runtime_asset_source_lineage_missing", text)
        self.assertIn("runtime_asset_exact_crop_pixel_mismatch", text)
        self.assertIn("generated_asset_must_declare_reference_reconstruction", text)
        self.assertIn("runtime_asset_manifest_source_mismatch", text)
        self.assertIn("runtime_asset_manifest_crop_mismatch", text)

    def test_typography_validator_checks_render_trace(self) -> None:
        text = self.read("scripts/validate_typography_fidelity.py")
        self.assertIn("typography_render_trace_spec_hash_mismatch", text)
        self.assertIn("typography_render_trace_instance_missing", text)
        self.assertIn("typography_render_trace_attributes_mismatch", text)
        self.assertIn("typography_host_extension_override_missing", text)
        self.assertIn("effective_host_bbox", text)

    def test_contracts_are_linked_from_primary_docs(self) -> None:
        for contract in (
            "references/production-preview-lineage-contract.md",
            "references/typography-fidelity-contract.md",
        ):
            self.assertTrue((ROOT / contract).is_file())
        for relative in (
            "SKILL.md",
            "USAGE.md",
            "references/pipeline.md",
            "references/manifest-contract.md",
            "references/design-mockup-approval-contract.md",
            "references/design-to-layout-contract.md",
            "references/xml-strict-generation.md",
            "references/fairygui-xml-contract.md",
        ):
            text = self.read(relative)
            self.assertIn("production-preview-lineage-contract.md", text, relative)
            self.assertIn("typography-fidelity-contract.md", text, relative)


if __name__ == "__main__":
    unittest.main()
