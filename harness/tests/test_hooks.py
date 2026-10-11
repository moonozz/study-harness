import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GUARD_WRITE = ROOT / "harness" / "scripts" / "guard_write.py"
GUARD_JUDGE = ROOT / "harness" / "scripts" / "guard_judge.py"


class HookTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.runs_root = Path(self.tempdir.name) / "runs"
        self.run_id = "20261011-1200-test"
        self.run_dir = self.runs_root / self.run_id
        (self.run_dir / "agents/research").mkdir(parents=True)
        self.env = dict(os.environ, HARNESS_RUNS_ROOT=str(self.runs_root), PYTHONDONTWRITEBYTECODE="1")

    def tearDown(self):
        self.tempdir.cleanup()

    def set_role(self, role):
        (self.runs_root / ".active.json").write_text(
            json.dumps({"run_id": self.run_id, "role": role}), encoding="utf-8"
        )

    def invoke(self, script, event):
        process = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            env=self.env,
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=False
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout) if process.stdout.strip() else {}

    def test_write_guard_allows_role_folder(self):
        self.set_role("research-agent")
        target = self.run_dir / "agents/research/01-reference-analysis.md"
        result = self.invoke(GUARD_WRITE, {
            "tool_name": "apply_patch",
            "tool_input": {"command": "*** Begin Patch\n*** Update File: {}\n*** End Patch".format(target)}
        })
        self.assertEqual(result, {})

    def test_write_guard_denies_outside_role_folder(self):
        self.set_role("research-agent")
        result = self.invoke(GUARD_WRITE, {
            "tool_name": "apply_patch",
            "tool_input": {"command": "*** Begin Patch\n*** Update File: AGENTS.md\n*** End Patch"}
        })
        decision = result["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")

    def test_judge_guard_denies_patch(self):
        self.set_role("judge-agent")
        result = self.invoke(GUARD_JUDGE, {
            "tool_name": "apply_patch",
            "tool_input": {"command": "*** Begin Patch\n*** Update File: anything.md\n*** End Patch"}
        })
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
