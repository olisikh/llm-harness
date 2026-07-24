"""Regression test ensuring the controller test suite can import scripts modules."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_telemetry_store_imports_without_manual_pythonpath():
    """pytest collection must not fail when telemetry_store lives under scripts/."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_lifecycle_telemetry.py", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "test_lifecycle_telemetry.py" in result.stdout


def test_scripts_directory_is_on_sys_path_from_conftest():
    import telemetry_store

    assert hasattr(telemetry_store, "record")
    assert hasattr(telemetry_store, "prune")
