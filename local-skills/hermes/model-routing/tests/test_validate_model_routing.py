"""Behavioral tests for the routing-policy validator CLI."""

from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-model-routing.py"
SCHEMA = ROOT / "schemas" / "routing-policy.v1.schema.json"

ROLE_MODELS = {
    "cheap_worker": [
        {"provider": "openai-codex", "model": "gpt-5.6-luna", "reasoning_effort": "low"},
        {"provider": "ollama-cloud", "model": "deepseek-v4-flash"},
    ],
    "coder": [
        {"provider": "openai-codex", "model": "gpt-5.6-terra", "reasoning_effort": "high"},
        {"provider": "ollama-cloud", "model": "kimi-k2.7-code"},
    ],
    "coding_expert": [
        {"provider": "openai-codex", "model": "gpt-5.6-sol", "reasoning_effort": "high"},
    ],
    "researcher": [
        {"provider": "openai-codex", "model": "gpt-5.6-terra", "reasoning_effort": "high"},
        {"provider": "ollama-cloud", "model": "qwen3.5:397b", "reasoning_effort": "high"},
        {"provider": "ollama-cloud", "model": "deepseek-v4-pro", "reasoning_effort": "high"},
    ],
    "final_reviewer": [
        {"provider": "openai-codex", "model": "gpt-5.6-sol", "reasoning_effort": "high"},
    ],
}


def valid_policy() -> dict:
    roles = {}
    for name, models in ROLE_MODELS.items():
        roles[name] = {
            "models": copy.deepcopy(models),
            "contract": {"mode": "writer" if name == "coder" else "read_only"},
            "timeout_seconds": 1200 if name == "coder" else 600,
        }
    roles["cheap_worker"]["allowed_tasks"] = ["extraction", "classification"]
    return {
        "version": 1,
        "roles": roles,
        "switching": {
            "transport_failures": ["rate_limit", "timeout", "provider_error"],
            "configured_api_retries": 3,
            "same_model_structured_output_repairs": 1,
            "escalation_after_distinct_model_failures": 2,
        },
        "limits": {
            "max_parallel_workers": 2,
            "max_expensive_workers": 1,
        },
        "isolation": {"writer_execution": "git_worktree"},
        "review": {
            "role": "final_reviewer",
            "required_for_routed_tasks": True,
            "max_rejections": 2,
        },
    }


class ValidateModelRoutingTests(unittest.TestCase):
    def run_validator(self, policy: dict | str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            policy_path = Path(directory) / "policy.yaml"
            policy_path.write_text(
                policy if isinstance(policy, str) else yaml.safe_dump(policy, sort_keys=False),
                encoding="utf-8",
            )
            return subprocess.run(
                [sys.executable, str(VALIDATOR), "--policy", str(policy_path), "--schema", str(SCHEMA)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_valid_policy_passes(self):
        result = self.run_validator(valid_policy())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "routing_policy=valid\nversion=1\n")

    def test_reasoning_effort_is_optional(self):
        policy = valid_policy()
        del policy["roles"]["coder"]["models"][0]["reasoning_effort"]
        result = self.run_validator(policy)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_duplicate_role_has_stable_diagnostic(self):
        policy = yaml.safe_dump(valid_policy(), sort_keys=False)
        duplicate = policy.replace("roles:\n", "roles:\n  coder:\n    models: []\n", 1)
        result = self.run_validator(duplicate)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "ERROR [duplicate_yaml_key] roles.coder: duplicate mapping key\n")

    def test_duplicate_model_has_stable_diagnostic(self):
        policy = valid_policy()
        policy["roles"]["coder"]["models"].append(copy.deepcopy(policy["roles"]["coder"]["models"][0]))
        result = self.run_validator(policy)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "ERROR [duplicate_model] roles.coder.models[2]: duplicate provider/model entry\n")

    def test_malformed_model_has_stable_diagnostic(self):
        policy = valid_policy()
        del policy["roles"]["coder"]["models"][0]["provider"]
        result = self.run_validator(policy)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "ERROR [schema] roles.coder.models[0]: 'provider' is a required property\n")

    def test_runtime_fields_are_rejected(self):
        for forbidden in ("runtime_projection", "fallback_providers", "model", "agent", "delegation"):
            with self.subTest(forbidden=forbidden):
                policy = valid_policy()
                policy[forbidden] = {"provider": "example", "model": "example"}
                result = self.run_validator(policy)
                self.assertEqual(result.returncode, 2)
                self.assertIn("ERROR [schema] <root>:", result.stderr)
                self.assertIn(forbidden, result.stderr)

    def test_legacy_model_labels_are_rejected(self):
        for forbidden in ("primary", "secondary", "tertiary"):
            with self.subTest(forbidden=forbidden):
                policy = valid_policy()
                policy["roles"]["coder"]["models"][0][forbidden] = True
                result = self.run_validator(policy)
                self.assertEqual(result.returncode, 2)
                self.assertIn("ERROR [schema] roles.coder.models[0]:", result.stderr)
                self.assertIn(forbidden, result.stderr)


if __name__ == "__main__":
    unittest.main()
