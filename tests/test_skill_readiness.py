"""Behavior tests for user-owned skill paths and readiness checks."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.agent_paths import artifact_directory, configured_path
from lib.readiness import audit_skill_readiness


class SkillReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.skill_paths = self.root / "skill-paths.json"
        self.skill_paths.write_text(
            json.dumps(
                {
                    "version": 1,
                    "artifacts": {"handoffs": "~/agent-data/handoffs"},
                    "paths": {"obsidian_vault": "~/agent-data/notes"},
                }
            )
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_artifact_directory_expands_configured_path_and_creates_it_on_request(self):
        result = artifact_directory(
            "handoffs", config_path=self.skill_paths, home=self.root, create=True
        )

        self.assertEqual(result, self.root / "agent-data" / "handoffs")
        self.assertTrue(result.is_dir())

    def test_configured_path_returns_named_user_choice_without_creating_it(self):
        result = configured_path(
            "obsidian_vault", config_path=self.skill_paths, home=self.root
        )

        self.assertEqual(result, self.root / "agent-data" / "notes")
        self.assertFalse(result.exists())

    def test_readiness_reports_required_and_optional_missing_requirements_separately(self):
        manifest = self.root / "skill-readiness.yaml"
        manifest.write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "skills": {
                        "agents:productivity/handoff": {
                            "scope": "global",
                            "requirements": [
                                {"type": "artifact_directory", "name": "handoffs"},
                                {"type": "command", "name": "python3"},
                            ],
                        },
                        "agents:resemble-detect": {
                            "scope": "global",
                            "requirements": [
                                {
                                    "type": "environment",
                                    "name": "RESEMBLE_API_KEY",
                                    "optional": True,
                                }
                            ],
                        },
                    },
                },
                sort_keys=False,
            )
        )

        artifact_directory("handoffs", config_path=self.skill_paths, home=self.root, create=True)
        result = audit_skill_readiness(
            manifest, skill_paths_path=self.skill_paths, home=self.root, environ={}
        )

        self.assertEqual(result.ready, ["agents:productivity/handoff"])
        self.assertEqual(result.blocked, {})
        self.assertEqual(result.optional_missing, {"agents:resemble-detect": ["environment:RESEMBLE_API_KEY"]})


if __name__ == "__main__":
    unittest.main()
