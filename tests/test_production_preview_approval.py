from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "record_production_preview_approval.py"
spec = importlib.util.spec_from_file_location("record_production_preview_approval", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


class ProductionPreviewApprovalTests(unittest.TestCase):
    def root(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def prepare(self, root: Path) -> None:
        preview = root / "generated" / "preview" / "screen.png"
        preview.parent.mkdir(parents=True)
        preview.write_bytes(b"preview")
        asset = root / "fgui_xml" / "pkg" / "art" / "icon.png"
        asset.parent.mkdir(parents=True)
        asset.write_bytes(b"asset")
        write_json(root / "specs" / "production_preview_lineage.json", {
            "productionPreview": {"file": "generated/preview/screen.png"},
            "assets": [{
                "assetName": "icon",
                "runtimeFile": "fgui_xml/pkg/art/icon.png",
                "previewUsage": "exact_file",
            }],
        })

    def test_pending_freezes_candidate_hashes(self) -> None:
        root = self.root()
        self.prepare(root)
        record = module.pending_record(root, "review")
        self.assertEqual(record["status"], "pending")
        self.assertTrue(record["candidateFileSha256"])
        self.assertTrue(record["candidateAssetHashes"]["icon"])
        self.assertTrue(record["candidateEvidenceHashes"]["productionPreviewLineage"])

    def test_human_approval_freezes_approved_hashes(self) -> None:
        root = self.root()
        self.prepare(root)
        record = module.approved_record(root, "user_confirmation", "user", "approved")
        self.assertEqual(record["status"], "approved")
        self.assertEqual(record["candidateFileSha256"], record["approvedFileSha256"])
        self.assertEqual(record["candidateAssetHashes"], record["approvedAssetHashes"])
        self.assertEqual(record["candidateEvidenceHashes"], record["approvedEvidenceHashes"])

    def test_non_human_approval_is_rejected(self) -> None:
        root = self.root()
        self.prepare(root)
        with self.assertRaises(ValueError):
            module.approved_record(root, "automatic", "assistant", "approved")


if __name__ == "__main__":
    unittest.main()
