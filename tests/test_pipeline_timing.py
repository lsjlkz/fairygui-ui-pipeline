#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for pipeline-stage timing records."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_ROOT / "scripts" / "record_pipeline_timing.py"
STAGE_IDS = [
    "requirement_intake",
    "ux_ui_spec",
    "visual_design_brief",
    "design_mockup_generation",
    "design_approval",
    "semantic_analysis",
    "layout_analysis",
    "asset_planning",
    "resource_generation",
    "sheet_slicing",
    "fairygui_assembly",
    "package_staging",
    "xml_generation",
    "validation",
    "editor_publish",
    "unity_smoke_test",
]


class PipelineTimingTests(unittest.TestCase):
    def run_timing(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def load_report(self, root: Path) -> dict[str, object]:
        return json.loads(
            (root / "reports" / "pipeline_stage_timings.json").read_text(encoding="utf-8")
        )

    def test_complete_run_outputs_every_stage_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            result = self.run_timing(root, "init")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

            result = self.run_timing(
                root,
                "start",
                "--stage",
                "requirement_intake",
                "--note",
                "requirements opened",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            result = self.run_timing(
                root,
                "finish",
                "--stage",
                "requirement_intake",
                "--status",
                "completed",
                "--artifact",
                "specs/ui_spec.md",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

            for stage_id in STAGE_IDS[1:]:
                result = self.run_timing(
                    root,
                    "skip",
                    "--stage",
                    stage_id,
                    "--note",
                    "not required by this test run",
                )
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

            result = self.run_timing(root, "finalize", "--status", "completed")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            result = self.run_timing(root, "validate")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('"ok": true', result.stdout)

            report = self.load_report(root)
            self.assertEqual(report["status"], "completed")
            self.assertEqual(len(report["stages"]), 16)
            summary = report["summary"]
            self.assertIn("wallClockDurationMs", summary)
            self.assertIn("activeDurationMs", summary)
            self.assertIn("waitingDurationMs", summary)
            self.assertIn("externalDurationMs", summary)
            self.assertIn("untrackedDurationMs", summary)

            markdown = (root / "reports" / "pipeline_stage_timings.md").read_text(
                encoding="utf-8"
            )
            for stage_id in STAGE_IDS:
                self.assertIn(stage_id, markdown)
            self.assertIn("total wall-clock", markdown)
            self.assertIn("active processing", markdown)
            self.assertIn("human waiting", markdown)
            self.assertIn("external tools", markdown)

    def test_completed_finalize_rejects_pending_stages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.assertEqual(self.run_timing(root, "init").returncode, 0)
            result = self.run_timing(root, "finalize", "--status", "completed")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires every canonical stage", result.stderr)

    def test_only_one_stage_may_run_at_a_time(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.assertEqual(self.run_timing(root, "init").returncode, 0)
            self.assertEqual(
                self.run_timing(root, "start", "--stage", "requirement_intake").returncode,
                0,
            )
            result = self.run_timing(root, "start", "--stage", "ux_ui_spec")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already running", result.stderr)

    def test_design_approval_is_counted_as_waiting(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.assertEqual(self.run_timing(root, "init").returncode, 0)
            self.assertEqual(
                self.run_timing(root, "start", "--stage", "design_approval").returncode,
                0,
            )
            self.assertEqual(
                self.run_timing(
                    root,
                    "finish",
                    "--stage",
                    "design_approval",
                    "--status",
                    "completed",
                ).returncode,
                0,
            )
            report = self.load_report(root)
            design_stage = next(
                stage for stage in report["stages"] if stage["stageId"] == "design_approval"
            )
            self.assertEqual(design_stage["attempts"][0]["category"], "waiting")
            self.assertGreaterEqual(report["summary"]["waitingDurationMs"], 0)

    def test_rework_appends_attempt_instead_of_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.assertEqual(self.run_timing(root, "init").returncode, 0)
            for attempt in range(2):
                args = ["start", "--stage", "design_mockup_generation"]
                if attempt == 1:
                    args.append("--rework")
                self.assertEqual(self.run_timing(root, *args).returncode, 0)
                self.assertEqual(
                    self.run_timing(
                        root,
                        "finish",
                        "--stage",
                        "design_mockup_generation",
                        "--status",
                        "completed",
                    ).returncode,
                    0,
                )
            report = self.load_report(root)
            stage = next(
                stage
                for stage in report["stages"]
                if stage["stageId"] == "design_mockup_generation"
            )
            self.assertEqual(stage["attemptCount"], 2)
            self.assertEqual([item["attempt"] for item in stage["attempts"]], [1, 2])

    def test_command_wrapper_records_command_duration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "UIProduction"
            self.assertEqual(self.run_timing(root, "init").returncode, 0)
            result = self.run_timing(
                root,
                "run",
                "--stage",
                "validation",
                "--",
                sys.executable,
                "-c",
                "print('timed')",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = self.load_report(root)
            stage = next(
                stage for stage in report["stages"] if stage["stageId"] == "validation"
            )
            self.assertEqual(stage["status"], "completed")
            self.assertGreaterEqual(stage["durationMs"], 0)


if __name__ == "__main__":
    unittest.main()
