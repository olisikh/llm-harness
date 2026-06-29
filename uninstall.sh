#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[uninstall] %s\n' "$*"
}

die() {
  printf '[uninstall] ERROR: %s\n' "$*" >&2
  exit 1
}

resolve_path() {
  python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$1"
}

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
harness_root="$repo_root/harness"
harness_paths_file="$repo_root/harness-paths.yaml"

[[ -d "$harness_root" ]] || die "missing harness directory: $harness_root"

read_harness_root() {
  local harness_name="$1"

  python3 - "$harness_paths_file" "$harness_name" <<'PY'
import os
import sys
from pathlib import Path

import yaml

config_path = Path(sys.argv[1])
harness_name = sys.argv[2]

defaults = {
    "agents": "~/.agents",
    "claude": "~/.claude",
    "codex": "~/.codex",
}

root = defaults.get(harness_name)
if config_path.exists():
    data = yaml.safe_load(config_path.read_text()) or {}
    overrides = data.get("harness") or {}
    if harness_name in overrides:
        root = overrides[harness_name]

if not root:
    raise SystemExit(f"No install root configured for harness '{harness_name}'")

print(os.path.expanduser(root))
PY
}

remove_if_managed() {
  local target_abs="$1"
  local source_abs="$2"
  local expected_resolved
  expected_resolved="$(resolve_path "$source_abs")"

  if [[ -L "$target_abs" ]] && [[ "$(resolve_path "$target_abs")" == "$expected_resolved" ]]; then
    rm "$target_abs"
    log "Removed $target_abs"
  fi
}

uninstall_harness() {
  local harness_name="$1"
  local source_dir="$harness_root/$harness_name"
  local target_root
  target_root="$(read_harness_root "$harness_name")"

  log "[$harness_name]"

  local source_entry
  local base_name
  for source_entry in "$source_dir"/*; do
    [[ -e "$source_entry" ]] || continue
    base_name="$(basename "$source_entry")"
    [[ "$base_name" == ".gitkeep" ]] && continue
    if [[ "$base_name" == "skills" ]]; then
      local skill_source
      for skill_source in "$source_entry"/*; do
        [[ -e "$skill_source" ]] || continue
        [[ "$(basename "$skill_source")" == ".gitkeep" ]] && continue
        remove_if_managed "$target_root/skills/$(basename "$skill_source")" "$skill_source"
      done
      continue
    fi

    remove_if_managed "$target_root/$base_name" "$source_entry"
  done
}

shopt -s nullglob
harnesses=("$harness_root"/*)
shopt -u nullglob

((${#harnesses[@]} > 0)) || die "no harness directories found in $harness_root"

for harness_path in "${harnesses[@]}"; do
  [[ -d "$harness_path" ]] || continue
  uninstall_harness "$(basename "$harness_path")"
done

log "Done."
