"""Tests for gating new skills until their configured routing is approved."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import Config
from lib.routing import approve_skill, discover_unapproved_skills, seed_routing_index
from lib.sync import sync_harness


class SkillRoutingTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.source = self.root / "local-skills" / "agents" / "category" / "example"
        self.source.mkdir(parents=True)
        (self.source / "SKILL.md").write_text("---\nname: example\n---\n")
        for harness in ("agents", "claude", "hermes"):
            (self.root / "home" / f".{harness}").mkdir(parents=True)
        (self.root / "harness-paths.yaml").write_text(
            "harness:\n"
            f"  agents: {self.root / 'home' / '.agents'}\n"
            f"  claude: {self.root / 'home' / '.claude'}\n"
            f"  hermes: {self.root / 'home' / '.hermes'}\n"
        )
        self.write_config("")
        self.config = Config(self.root)
        self.source_id = "local-skills/agents/category/example"

    def tearDown(self):
        self.tempdir.cleanup()

    def write_config(self, extra: str):
        (self.root / "config.yaml").write_text(
            """sources:
  local-skills/agents:
    type: local
    root: .
    harness: agents
"""
            + extra
        )

    def test_unapproved_skill_is_withheld_until_its_configured_route_is_approved(self):
        (self.root / "state").mkdir()
        (self.root / "state" / "skill-routing-index.json").write_text(
            '{"version": 1, "skills": {}}\n'
        )

        candidates = discover_unapproved_skills(self.config)

        self.assertEqual(
            [candidate.source for candidate in candidates], [self.source_id]
        )
        self.assertEqual(candidates[0].harness, "agents")
        self.assertEqual(list(self.config.list_configured_skills()), [])

        approve_skill(
            self.config, self.source_id, "agents", reason="general-use workflow"
        )

        self.assertEqual(
            [
                (harness, relative_path)
                for harness, relative_path, _ in self.config.list_configured_skills()
            ],
            [("agents", "category/example")],
        )
        index = json.loads(
            (self.root / "state" / "skill-routing-index.json").read_text()
        )
        self.assertEqual(
            index["skills"][self.source_id],
            {
                "harness": "agents",
                "path": "category/example",
                "reason": "general-use workflow",
            },
        )

    def test_source_specific_config_route_is_the_route_that_must_be_approved(self):
        self.write_config(
            """routes:
  local-skills/agents/category/example: claude
"""
        )
        (self.root / "state").mkdir()
        (self.root / "state" / "skill-routing-index.json").write_text(
            '{"version": 1, "skills": {}}\n'
        )

        candidate = discover_unapproved_skills(self.config)[0]

        self.assertEqual(candidate.harness, "claude")
        with self.assertRaises(SystemExit):
            approve_skill(self.config, self.source_id, "agents")
        approve_skill(self.config, self.source_id, "claude")
        self.assertEqual(
            [
                (harness, relative_path)
                for harness, relative_path, _ in self.config.list_configured_skills()
            ],
            [("claude", "category/example")],
        )

    def test_seed_indexes_existing_effective_routes(self):
        seeded = seed_routing_index(self.config)

        self.assertEqual(seeded, 1)
        self.assertEqual(len(discover_unapproved_skills(self.config)), 0)
        self.assertEqual(
            [
                (harness, relative_path)
                for harness, relative_path, _ in self.config.list_configured_skills()
            ],
            [("agents", "category/example")],
        )

    def test_artifacts_install_explicit_files_and_directories(self):
        source_root = self.root / "graphify" / "graphify"
        (source_root / "skills" / "opencode" / "references").mkdir(parents=True)
        (source_root / "skill-opencode.md").write_text("---\nname: graphify\n---\n")
        self.write_config(
            """  graphify:
    type: local
    artifacts:
      - from: graphify/skill-opencode.md
        harness: agents
        to: skills/graphify/SKILL.md
      - from: graphify/skills/opencode/references
        harness: agents
        to: skills/graphify/references
"""
        )

        self.assertEqual(
            [item[:3] for item in self.config.list_discovered_skills()],
            [
                (self.source_id, "agents", "category/example"),
                ("graphify/graphify/skill-opencode.md", "agents", "graphify/SKILL.md"),
                (
                    "graphify/graphify/skills/opencode/references",
                    "agents",
                    "graphify/references",
                ),
            ],
        )
        seed_routing_index(self.config)
        self.assertEqual(
            [
                (harness, path)
                for harness, path, _ in self.config.list_configured_skills()
            ],
            [
                ("agents", "category/example"),
                ("agents", "graphify/SKILL.md"),
                ("agents", "graphify/references"),
            ],
        )

    def test_source_install_commands_run_from_source_directory(self):
        source_root = self.root / "graphify"
        source_root.mkdir()
        self.write_config(
            """  graphify:
    type: local
    install:
      - tool setup --editable .
"""
        )

        self.assertEqual(
            list(self.config.source_install_commands()),
            [(source_root.resolve(), ["tool", "setup", "--editable", "."])],
        )

    def test_claude_mirror_flattens_approved_agent_skills(self):
        self.write_config(
            """skill_mirrors:
  claude:
    from: agents
    flatten: true
"""
        )
        (self.root / "state").mkdir()
        (self.root / "state" / "skill-routing-index.json").write_text(
            '{"version": 1, "skills": {}}\n'
        )

        self.assertEqual(list(self.config.list_skill_targets()), [])
        approve_skill(self.config, self.source_id, "agents")

        self.assertEqual(
            [(harness, path) for harness, path, _ in self.config.list_skill_targets()],
            [("agents", "category/example"), ("claude", "example")],
        )

        sync_harness(self.config, "claude")
        self.assertEqual(
            (self.root / "home" / ".claude" / "skills" / "example").resolve(),
            self.source.resolve(),
        )


if __name__ == "__main__":
    unittest.main()
