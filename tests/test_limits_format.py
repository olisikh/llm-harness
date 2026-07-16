"""Contract tests for human-facing CodexBar quota formatting."""

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "local-skills"
    / "agents"
    / "mlops"
    / "limits"
    / "scripts"
    / "limits.py"
)
spec = importlib.util.spec_from_file_location("limits_script", SCRIPT)
limits = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = limits
spec.loader.exec_module(limits)


class LimitsFormatTests(unittest.TestCase):
    def test_provider_id_is_unformatted_and_remaining_is_rounded(self):
        item = {
            "provider": "ollama",
            "usage": {
                "primary": {"usedPercent": 0, "windowMinutes": 300},
                "secondary": {"usedPercent": 2.4, "windowMinutes": 10080},
            },
        }

        self.assertEqual(limits.format_line(item), "ollama: 100%/5h 98%/7d")

    def test_fetches_all_provider_usage_in_one_json_call(self):
        with patch.object(
            limits.subprocess,
            "run",
            return_value=SimpleNamespace(stdout='[{"provider":"codex"}]'),
        ) as run:
            self.assertEqual(limits.run_usage(15), [{"provider": "codex"}])

        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["codexbar", "usage", "--json"])
        self.assertNotIn("CODEX_HOME", run.call_args.kwargs["env"])


if __name__ == "__main__":
    unittest.main()
