import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "harness" / "scripts" / "orchestrate.py"


def update_frontmatter(path, values):
    lines = path.read_text(encoding="utf-8").splitlines()
    output = []
    for line in lines:
        if ":" in line:
            key = line.split(":", 1)[0]
            if key in values:
                line = "{}: {}".format(key, json.dumps(values[key], ensure_ascii=False))
        output.append(line)
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


class OrchestratorTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.runs_root = Path(self.tempdir.name) / "runs"
        self.env = dict(os.environ, HARNESS_RUNS_ROOT=str(self.runs_root), PYTHONDONTWRITEBYTECODE="1")

    def tearDown(self):
        self.tempdir.cleanup()

    def run_command(self, *args, expected=0):
        process = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            env=self.env,
            text=True,
            capture_output=True,
            check=False
        )
        self.assertEqual(process.returncode, expected, process.stderr or process.stdout)
        return json.loads(process.stdout) if process.stdout.strip() else None

    def start_run(self):
        result = self.run_command(
            "start",
            "--name", "테스트 작업",
            "--reference", "https://example.com/one",
            "--screen", "링크 추가",
            "--screen", "추출 결과 확인"
        )
        return result["run_id"], Path(result["run_dir"])

    def test_start_creates_scoped_templates_and_state(self):
        run_id, run_dir = self.start_run()
        state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        active = json.loads((self.runs_root / ".active.json").read_text(encoding="utf-8"))
        self.assertEqual(state["stages"]["1"], "in_progress")
        self.assertEqual(state["current_role"], "research-agent")
        self.assertEqual(active["run_id"], run_id)
        self.assertTrue((run_dir / "agents/research/01-reference-analysis.md").is_file())
        self.assertTrue((run_dir / "agents/screen/02-screen-spec.md").is_file())
        self.assertTrue((run_dir / "agents/design/03-key-screens.md").is_file())

    def test_first_three_stages_wait_for_human_then_approve(self):
        run_id, run_dir = self.start_run()
        update_frontmatter(run_dir / "agents/research/01-reference-analysis.md", {
            "references": 1,
            "missing_source_count": 0,
            "reflection_candidates": 1,
            "unknown_category_count": 0,
            "unverified_fact_count": 0
        })
        self.run_command("complete-stage", "--run", run_id, "--stage", "1")

        update_frontmatter(run_dir / "agents/screen/02-screen-spec.md", {
            "planned_key_screens": 2,
            "missing_required_sections": 0,
            "unknown_category_count": 0,
            "unverified_fact_count": 0
        })
        self.run_command("complete-stage", "--run", run_id, "--stage", "2")

        update_frontmatter(run_dir / "agents/design/03-key-screens.md", {
            "key_screens": 2,
            "frame_width": 390,
            "frame_height": 844,
            "unknown_category_count": 0,
            "unverified_fact_count": 0
        })
        self.run_command("complete-stage", "--run", run_id, "--stage", "3")

        waiting = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(waiting["stages"]["3"], "waiting_approval")
        self.assertEqual(waiting["stages"]["4"], "pending")

        self.run_command("approve", "--run", run_id, "--approver", "내부 관계자")
        approved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(approved["human_approval"], "approved")
        self.assertEqual(approved["stages"]["4"], "in_progress")
        self.assertIn("approved", (run_dir / "approval.md").read_text(encoding="utf-8"))

    def test_start_rejects_wrong_screen_count(self):
        process = subprocess.run(
            [sys.executable, str(SCRIPT), "start", "--name", "실패", "--reference", "one", "--screen", "하나"],
            cwd=ROOT,
            env=self.env,
            text=True,
            capture_output=True,
            check=False
        )
        self.assertEqual(process.returncode, 2)
        self.assertIn("2~3개", process.stderr)


if __name__ == "__main__":
    unittest.main()
