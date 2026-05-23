#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
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
    "opencodego": "OpenCode Go",
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


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()


def map_provider(name: str) -> str:
    key = name.strip().lower().replace("_", "-")
    return PROVIDER_MAP.get(key, key)


def providers_from_config(include_aux: bool = False) -> list[str]:
    path = hermes_home() / "config.yaml"
    if not path.exists():
        return []

    providers: list[str] = []
    section: str | None = None
    current_aux_provider: str | None = None

    for raw in path.read_text(errors="ignore").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()

        if indent == 0 and not line.startswith("-"):
            section = line[:-1] if line.endswith(":") else None
            continue

        m = re.match(r"(?:-\s*)?provider:\s*['\"]?([^'\"#]+?)['\"]?\s*(?:#.*)?$", line)
        if not m:
            continue
        val = m.group(1).strip()
        if not val or val == "auto":
            continue

        if section in {"model", "fallback_providers"} or (include_aux and section == "auxiliary"):
            mapped = map_provider(val)
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
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
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
    rem_s = str(int(remaining)) if remaining.is_integer() else f"{remaining:.1f}".rstrip("0").rstrip(".")
    return f"{rem_s}%/{window_label(win.get('windowMinutes'))}"


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
    ap.add_argument("--include-aux", action="store_true")
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
        providers = providers_from_config(include_aux=args.include_aux)

    # Deduplicate while preserving order.
    providers = list(dict.fromkeys(providers))
    if not providers:
        print("No providers found")
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
