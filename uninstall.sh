#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[uninstall] %s\n' "$*"
}

warn() {
  printf '[uninstall] WARNING: %s\n' "$*" >&2
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

list_managed_symlinks() {
  local target_skills_dir="$1"
  local repo_root_abs="$2"

  python3 - "$target_skills_dir" "$repo_root_abs" <<'PY'
import os
import sys
from pathlib import Path

target_root = Path(sys.argv[1])
repo_root = Path(sys.argv[2]).resolve()

if not target_root.exists():
    raise SystemExit(0)

for current_root, dirs, files in os.walk(target_root, followlinks=False):
    dirs.sort()
    files.sort()
    for name in list(dirs) + files:
        path = Path(current_root) / name
        if not path.is_symlink():
            continue
        try:
            resolved = path.resolve()
        except OSError:
            continue
        try:
            resolved.relative_to(repo_root)
        except ValueError:
            continue
        print(path)
PY
}

remove_if_managed() {
  local target_abs="$1"
  local source_abs="$2"
  local expected_resolved
  expected_resolved="$(resolve_path "$source_abs")"

  if [[ ! -L "$target_abs" ]]; then
    if [[ -e "$target_abs" ]]; then
      warn "Skipping non-symlink at $target_abs"
    fi
    return 1
  fi

  if [[ "$(resolve_path "$target_abs")" != "$expected_resolved" ]]; then
    warn "Skipping symlink at $target_abs (points elsewhere)"
    return 1
  fi

  rm "$target_abs"
  log "Removed $target_abs"
  return 0
}

prune_empty_parent_dirs() {
  local path="$1"
  local stop_dir="$2"
  local current
  current="$(dirname "$path")"

  while [[ "$current" == "$stop_dir"/* ]]; do
    rmdir "$current" 2>/dev/null || break
    current="$(dirname "$current")"
  done
}

uninstall_harness() {
  local harness_name="$1"
  local source_dir="$harness_root/$harness_name"
  local target_root
  target_root="$(read_harness_root "$harness_name")"

  log "[$harness_name]"

  local target_skills_dir="$target_root/skills"
  if [[ -d "$target_skills_dir" ]]; then
    local existing_symlink
    while IFS= read -r existing_symlink; do
      [[ -n "$existing_symlink" ]] || continue
      rm "$existing_symlink"
      log "Removed $existing_symlink"
      prune_empty_parent_dirs "$existing_symlink" "$target_skills_dir"
    done < <(list_managed_symlinks "$target_skills_dir" "$repo_root")
  fi

  local source_entry
  local base_name
  for source_entry in "$source_dir"/*; do
    [[ -e "$source_entry" || -L "$source_entry" ]] || continue
    base_name="$(basename "$source_entry")"
    [[ "$base_name" == ".gitkeep" ]] && continue
    [[ "$base_name" == "skills" ]] && continue

    if remove_if_managed "$target_root/$base_name" "$source_entry"; then
      prune_empty_parent_dirs "$target_root/$base_name" "$target_root"
    fi
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
