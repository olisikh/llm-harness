"""Contract tests for human-facing CodexBar quota formatting."""

import importlib.util
import sys
import unittest
from pathlib import Path

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
    def test_ollama_uses_fixed_label_and_whole_remaining_percentages(self):
        item = {
            "provider": "ollama",
            "usage": {
                "primary": {"usedPercent": 0, "windowMinutes": 300},
                "secondary": {"usedPercent": 2.4, "windowMinutes": 10080},
            },
        }

        self.assertEqual(limits.format_line(item), "Ollama Cloud: 100%/5h 98%/7d")


if __name__ == "__main__":
    unittest.main()
