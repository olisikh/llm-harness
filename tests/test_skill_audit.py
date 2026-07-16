"""Behavior tests for the persistent llm-harness skill installation audit."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.audit import audit_skill_installations
from lib.config import Config
from lib.sync import sync_harness


class SkillAuditTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.home = self.root / "home" / ".agents"
        self.home.mkdir(parents=True)
        self.source = self.root / "local-skills" / "agents" / "category" / "example"
        self.source.mkdir(parents=True)
        (self.source / "SKILL.md").write_text("---\nname: example\n---\n")
        (self.root / "config.yaml").write_text(
            """sources:
  local-skills/agents:
    type: local
    root: .
    harness: agents
"""
        )
        (self.root / "harness-paths.yaml").write_text(
            f"harness:\n  agents: {self.home}\n"
        )
        self.config = Config(self.root)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_audit_marks_exact_managed_skill_complete_and_only_new_once(self):
        sync_harness(self.config, "agents")

        first = audit_skill_installations(self.config)
        second = audit_skill_installations(self.config)

        self.assertEqual(first.new_keys, ["agents:category/example"])
        self.assertEqual(first.invalid_keys, [])
        self.assertEqual(second.new_keys, [])
        state = json.loads((self.root / "state" / "skill-installation.json").read_text())
        self.assertEqual(state["skills"]["agents:category/example"], {
            "harness": "agents",
            "path": "category/example",
            "source": "local-skills/agents/category/example",
            "status": "complete",
        })

    def test_sync_removes_old_target_when_a_skill_is_rehomed(self):
        old_target = self.home / "skills" / "old-category" / "example"
        old_target.parent.mkdir(parents=True)
        old_target.symlink_to(self.source)

        sync_harness(self.config, "agents")

        self.assertTrue((self.home / "skills" / "category" / "example").is_symlink())
        self.assertFalse(old_target.exists() or old_target.is_symlink())

    def test_audit_repairs_a_wrong_managed_symlink_before_marking_complete(self):
        target = self.home / "skills" / "category" / "example"
        target.parent.mkdir(parents=True)
        old_source = self.root / "retired" / "example"
        old_source.mkdir(parents=True)
        target.symlink_to(old_source)

        result = audit_skill_installations(self.config)

        self.assertTrue(target.is_symlink())
        self.assertEqual(target.resolve(), self.source.resolve())
        self.assertEqual(result.invalid_keys, [])
        self.assertEqual(result.repaired_keys, ["agents:category/example"])


if __name__ == "__main__":
    unittest.main()
