#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
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

LABELS = {
    "codex": "Codex",
    "ollama": "Ollama Cloud",
    "opencodego": "Opencode GO",
    "gemini": "Gemini",
    "claude": "Claude",
    "openrouter": "OpenRouter",
    "zai": "Z.ai",
    "minimax": "MiniMax",
    "kimi": "Kimi",
    "mistral": "Mistral",
    "deepseek": "DeepSeek",
    "alibaba-coding-plan": "Alibaba Coding Plan",
    "copilot": "Copilot",
    "kilo": "Kilo",
}

PREFERRED_SOURCE = {"codex": "cli"}


def map_provider(name: str) -> str:
    key = name.strip().lower().replace("_", "-")
    return PROVIDER_MAP.get(key, key)


def codexbar_home() -> Path:
    return Path(os.environ.get("CODEXBAR_HOME", Path.home() / ".codexbar")).expanduser()


def providers_from_codexbar_config() -> list[str]:
    path = codexbar_home() / "config.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return []
    items = payload.get("providers")
    if not isinstance(items, list):
        return []
    providers: list[str] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("enabled"):
            continue
        provider_id = item.get("id")
        if not isinstance(provider_id, str) or not provider_id.strip():
            continue
        mapped = map_provider(provider_id)
        if mapped not in providers:
            providers.append(mapped)
    return providers


def extract_json(stdout: str) -> Any:
    for i, ch in enumerate(stdout):
        if ch in "[{":
            try:
                return json.loads(stdout[i:])
            except Exception:
                pass
    raise ValueError("no JSON found")


def run_provider(provider: str, timeout: int) -> dict[str, Any]:
    cmd = ["codexbar", "usage", "--provider", provider, "--format", "json", "--pretty"]
    source = PREFERRED_SOURCE.get(provider)
    if source:
        cmd[cmd.index("--format"):cmd.index("--format")] = ["--source", source]
    env = dict(os.environ)
    env.pop("CODEX_HOME", None)
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return {"provider": provider, "error": f"timeout after {timeout}s"}
    try:
        payload = extract_json(proc.stdout)
        item = payload[0] if isinstance(payload, list) and payload else payload
    except Exception as exc:
        return {"provider": provider, "error": str(exc)}
    if not isinstance(item, dict):
        return {"provider": provider, "error": "empty result"}
    item.setdefault("provider", provider)
    return item


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
    provider = item.get("provider", "unknown")
    label = LABELS.get(provider, provider)
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

    providers = []
    if args.provider:
        providers = [map_provider(p) for p in args.provider]
    else:
        providers = providers_from_codexbar_config()

    # Deduplicate while preserving order.
    providers = list(dict.fromkeys(providers))
    if not providers:
        print("No enabled CodexBar providers found")
        return 2

    results = [run_provider(p, args.timeout) for p in providers]
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
