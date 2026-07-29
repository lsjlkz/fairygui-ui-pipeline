from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_pipeline.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("validate_pipeline", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class RegistryInstanceScopeTests(unittest.TestCase):
    def report(self) -> dict:
        return {"errors": [], "warnings": []}

    def test_same_instance_id_in_different_components_is_valid(self) -> None:
        report = self.report()
        module.validate_registry({
            "packages": {
                "pkg": {
                    "id": "abcd1234",
                    "resources": {"a.xml": "aa", "b.xml": "bb"},
                    "instances": {
                        "component_a/background": "n0_1234",
                        "component_b/background": "n0_1234",
                    },
                }
            }
        }, report)
        self.assertFalse(report["errors"], report["errors"])

    def test_duplicate_instance_id_in_same_component_is_invalid(self) -> None:
        report = self.report()
        module.validate_registry({
            "packages": {
                "pkg": {
                    "id": "abcd1234",
                    "resources": {"a.xml": "aa"},
                    "instances": {
                        "component_a/background": "n0_1234",
                        "component_a/title": "n0_1234",
                    },
                }
            }
        }, report)
        self.assertTrue(any("component scope" in item["message"] for item in report["errors"]))


if __name__ == "__main__":
    unittest.main()
