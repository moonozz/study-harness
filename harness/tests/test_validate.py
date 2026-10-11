import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("harness_validate", ROOT / "harness" / "scripts" / "validate.py")
VALIDATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATE)


def markdown(metadata):
    lines = ["---"]
    for key, value in metadata.items():
        lines.append("{}: {}".format(key, json.dumps(value, ensure_ascii=False)))
    lines.extend(["---", "", "# Fixture", ""])
    return "\n".join(lines)


class ValidateHarnessTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.run_dir = Path(self.tempdir.name) / "20261011-1200-test"
        self.run_dir.mkdir()
        self.state = {
            "run_id": self.run_dir.name,
            "human_approval": "approved",
            "stages": {"1": "passed", "2": "passed", "3": "passed", "4": "passed", "5": "passed"},
            "retry_counts": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
            "metrics": {"write_scope_violation_count": 0, "parallel_stage_count": 0, "gate_bypass_count": 0}
        }
        self.metadata = {
            "01-reference-analysis.md": {
                "references": 1,
                "missing_source_count": 0,
                "reflection_candidates": 1,
                "unknown_category_count": 0,
                "unverified_fact_count": 0
            },
            "02-screen-spec.md": {
                "planned_key_screens": 2,
                "missing_required_sections": 0,
                "unknown_category_count": 0,
                "unverified_fact_count": 0
            },
            "03-key-screens.md": {
                "key_screens": 2,
                "frame_width": 390,
                "frame_height": 844,
                "unknown_category_count": 0,
                "unverified_fact_count": 0
            },
            "04-design-output.md": {
                "used_color_values": ["#141414", "#ffffff", "#0066ff"],
                "used_radii_px": [0, 8, 16, 24, 9999],
                "shadow_count": 0,
                "decorative_gradient_count": 0,
                "minimum_touch_target_px": 44,
                "mobile_input_font_size_px": 16,
                "letter_spacing": 0,
                "unknown_category_count": 0,
                "unverified_fact_count": 0
            }
        }
        self.guide = {
            "checked_rules": 10,
            "total_rules": 10,
            "failed_rules": 0,
            "unresolved_violations": 0,
            "judge_write_attempts": 0
        }
        self.write_fixture()

    def tearDown(self):
        self.tempdir.cleanup()

    def write_fixture(self):
        (self.run_dir / "state.json").write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        for name, metadata in self.metadata.items():
            (self.run_dir / name).write_text(markdown(metadata), encoding="utf-8")
        (self.run_dir / "05-guide-check.json").write_text(json.dumps(self.guide, ensure_ascii=False, indent=2), encoding="utf-8")

    def validate(self):
        self.write_fixture()
        return VALIDATE.validate_run(self.run_dir)

    def test_01_happy_path(self):
        self.assertEqual(self.validate()["exit_code"], 0)

    def test_02_zero_references_returns_to_stage_one(self):
        self.metadata["01-reference-analysis.md"]["references"] = 0
        result = self.validate()
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["return_stage"], 1)

    def test_03_missing_source_returns_to_stage_one(self):
        self.metadata["01-reference-analysis.md"]["missing_source_count"] = 1
        result = self.validate()
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["return_stage"], 1)

    def test_04_key_screen_count_returns_to_stage_three(self):
        self.metadata["03-key-screens.md"]["key_screens"] = 1
        result = self.validate()
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["return_stage"], 3)

    def test_05_wrong_frame_size_returns_to_stage_three(self):
        self.metadata["03-key-screens.md"]["frame_width"] = 393
        result = self.validate()
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["return_stage"], 3)

    def test_06_unknown_category_fails(self):
        self.metadata["02-screen-spec.md"]["unknown_category_count"] = 1
        result = self.validate()
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["return_stage"], 2)

    def test_07_unverified_fact_fails(self):
        self.metadata["01-reference-analysis.md"]["unverified_fact_count"] = 1
        result = self.validate()
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["return_stage"], 1)

    def test_08_missing_human_approval_waits(self):
        self.state["human_approval"] = "pending"
        self.state["stages"] = {"1": "passed", "2": "passed", "3": "waiting_approval", "4": "pending", "5": "pending"}
        result = self.validate()
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["return_stage"], 3)

    def test_09_guide_failure_returns_to_stage_four(self):
        self.guide["failed_rules"] = 1
        self.guide["unresolved_violations"] = 1
        result = self.validate()
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["return_stage"], 4)

    def test_10_resume_uses_first_non_passed_stage(self):
        self.state["stages"] = {"1": "passed", "2": "passed", "3": "failed", "4": "pending", "5": "pending"}
        result = self.validate()
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["return_stage"], 3)

    def test_11_judge_write_attempt_fails(self):
        self.guide["judge_write_attempts"] = 1
        result = self.validate()
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["return_stage"], 4)

    def test_12_missing_metadata_is_format_error(self):
        del self.metadata["02-screen-spec.md"]["planned_key_screens"]
        result = self.validate()
        self.assertEqual(result["exit_code"], 2)

    def test_13_invalid_run_id_is_format_error(self):
        self.state["run_id"] = "invalid"
        result = self.validate()
        self.assertEqual(result["exit_code"], 2)

    def test_14_design_rule_violation_returns_to_stage_four(self):
        self.metadata["04-design-output.md"]["used_radii_px"] = [12]
        result = self.validate()
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["return_stage"], 4)


if __name__ == "__main__":
    unittest.main()
