import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CodexStructureTest(unittest.TestCase):
    def test_skill_has_complete_frontmatter(self):
        text = (ROOT / ".codex/skills/run-design-harness/SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: run-design-harness\n"))
        self.assertIn("\ndescription:", text.split("---", 2)[1])
        self.assertNotIn("TODO", text)

    def test_hooks_have_required_events(self):
        hooks = json.loads((ROOT / ".codex/hooks.json").read_text(encoding="utf-8"))["hooks"]
        self.assertIn("SessionStart", hooks)
        self.assertIn("PreToolUse", hooks)
        self.assertIn("Stop", hooks)

    def test_project_config_enables_hooks_and_multi_agent(self):
        text = (ROOT / ".codex/config.toml").read_text(encoding="utf-8")
        self.assertIn('sandbox_mode = "workspace-write"', text)
        self.assertIn("hooks = true", text)
        self.assertIn("multi_agent = true", text)

    def test_agents_points_to_repo_skill(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn(".codex/skills/run-design-harness/SKILL.md", text)
        self.assertIn("$run-design-harness", text)


if __name__ == "__main__":
    unittest.main()
