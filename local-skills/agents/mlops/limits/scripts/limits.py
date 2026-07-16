#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Any

PROVIDER_MAP = {
    "openai-codex": "codex",
    "codex": "codex",
    "openai": "openai",
    "opencode-go": "opencodego",
    "opencodego": "opencodego",
    "opencode": "opencode",
    "google": "gemini",
    "gemini": "gemini",
    "anthropic": "claude",
    "claude": "claude",
    "openrouter": "openrouter",
    "zai": "zai",
    "glm": "zai",
    "minimax": "minimax",
    "kimi": "kimi",
    "moonshot": "kimi",
    "mistral": "mistral",
    "deepseek": "deepseek",
    "qwen": "alibaba-coding-plan",
    "dashscope": "alibaba-coding-plan",
    "alibaba": "alibaba-coding-plan",
    "vertex-ai": "vertexai",
    "vertexai": "vertexai",
    "copilot": "copilot",
    "kilo": "kilo",
}



def map_provider(name: str) -> str:
    key = name.strip().lower().replace("_", "-")
    return PROVIDER_MAP.get(key, key)


def extract_json(stdout: str) -> Any:
    for i, ch in enumerate(stdout):
        if ch in "[{":
            try:
                return json.loads(stdout[i:])
            except Exception:
                pass
    raise ValueError("no JSON found")


def run_usage(timeout: int) -> list[dict[str, Any]]:
    """Fetch all configured providers in one CodexBar JSON request."""
    cmd = ["codexbar", "usage", "--json"]
    env = dict(os.environ)
    env.pop("CODEX_HOME", None)
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return [{"provider": "codexbar", "error": f"timeout after {timeout}s"}]
    try:
        payload = extract_json(proc.stdout)
    except Exception as exc:
        return [{"provider": "codexbar", "error": str(exc)}]
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return [{"provider": "codexbar", "error": "empty result"}]
    return [item for item in payload if isinstance(item, dict)]


def window_label(minutes: Any) -> str:
    try:
        m = int(minutes)
    except Exception:
        return "?"
    if m % 10080 == 0:
        return f"{m // 10080 * 7}d" if m // 10080 != 1 else "7d"
    if m % 1440 == 0:
        return f"{m // 1440}d"
    if m % 60 == 0:
        return f"{m // 60}h"
    return f"{m}m"


def remaining_token(win: dict[str, Any]) -> str | None:
    if not win or "usedPercent" not in win or "windowMinutes" not in win:
        return None
    try:
        used = float(win["usedPercent"])
    except Exception:
        return None
    remaining = max(0.0, min(100.0, 100.0 - used))
    return f"{int(remaining + 0.5)}%/{window_label(win.get('windowMinutes'))}"


def format_line(item: dict[str, Any]) -> str | None:
    provider = str(item.get("provider", "unknown"))
    label = provider
    if err := item.get("error"):
        return f"{label}: error ({err})"
    usage = item.get("usage") or {}
    tokens = []
    for name in ("primary", "secondary", "tertiary"):
        tok = remaining_token(usage.get(name) or {})
        if tok:
            tokens.append(tok)
    if not tokens:
        return f"{label}: no limits"
    return f"{label}: {' '.join(tokens)}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", action="append")
    ap.add_argument("--timeout", type=int, default=75)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not shutil.which("codexbar"):
        print("codexbar not found", file=sys.stderr)
        return 127

    results = run_usage(args.timeout)
    if args.provider:
        requested = {map_provider(provider) for provider in args.provider}
        results = [
            item
            for item in results
            if map_provider(str(item.get("provider", ""))) in requested
        ]

    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
        return 0

    lines = [line for r in results if (line := format_line(r))]

    # Default: keep noise down. Hide errors if at least one useful line exists.
    useful = [ln for ln in lines if "error (" not in ln and "no limits" not in ln]
    if useful and not args.provider:
        lines = useful

    print("\n".join(lines))
    return 0 if useful else 1


if __name__ == "__main__":
    raise SystemExit(main())
