"""Tests for the Apple Notes importer vault configuration."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "local-skills"
    / "agents"
    / "apple-notes-to-obsidian"
    / "scripts"
    / "export_apple_notes.py"
)
SPEC = importlib.util.spec_from_file_location("apple_notes_importer", SCRIPT_PATH)
assert SPEC and SPEC.loader
IMPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORTER)


class AppleNotesPathTests(unittest.TestCase):
    def test_default_vault_uses_shared_obsidian_vault_configuration(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            config = root / "skill-paths.json"
            config.write_text(
                json.dumps({"version": 1, "paths": {"obsidian_vault": "~/notes"}})
            )

            result = IMPORTER.default_vault_from_config(config_path=config, home=root)

            self.assertEqual(result, root / "notes")


if __name__ == "__main__":
    unittest.main()
