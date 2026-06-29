#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[install] %s\n' "$*"
}

warn() {
  printf '[install] WARNING: %s\n' "$*" >&2
}

die() {
  printf '[install] ERROR: %s\n' "$*" >&2
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

sync_target() {
  local source_abs="$1"
  local target_abs="$2"
  local expected_resolved
  expected_resolved="$(resolve_path "$source_abs")"

  if [[ -L "$target_abs" ]]; then
    if [[ "$(resolve_path "$target_abs")" == "$expected_resolved" ]]; then
      return 0
    fi

    warn "Skipping existing symlink at $target_abs (points elsewhere)"
    return 1
  fi

  if [[ -e "$target_abs" ]]; then
    warn "Skipping existing path at $target_abs"
    return 1
  fi

  mkdir -p "$(dirname "$target_abs")"
  ln -s "$source_abs" "$target_abs"
  log "Linked $target_abs -> $source_abs"
}

remove_stale_symlink() {
  local target_abs="$1"
  local source_root_abs="$2"
  local source_root_resolved
  source_root_resolved="$(resolve_path "$source_root_abs")"

  [[ -L "$target_abs" ]] || return 1

  local resolved
  resolved="$(resolve_path "$target_abs")"
  if [[ "$resolved" == "$source_root_resolved" || "$resolved" == "$source_root_resolved"/* ]]; then
    rm "$target_abs"
    log "Removed stale $target_abs"
    return 0
  fi

  return 1
}

sync_skills_dir() {
  local source_skills_dir="$1"
  local target_root="$2"
  local target_skills_dir="$target_root/skills"

  [[ -d "$source_skills_dir" ]] || return 0

  mkdir -p "$target_skills_dir"

  local source_skill
  local target_skill
  for source_skill in "$source_skills_dir"/*; do
    [[ -e "$source_skill" ]] || continue
    [[ -d "$source_skill" || -L "$source_skill" ]] || continue
    [[ "$(basename "$source_skill")" == ".gitkeep" ]] && continue
    target_skill="$target_skills_dir/$(basename "$source_skill")"
    sync_target "$source_skill" "$target_skill" || true
  done

  local existing_skill
  for existing_skill in "$target_skills_dir"/*; do
    [[ -e "$existing_skill" || -L "$existing_skill" ]] || continue
    local source_match="$source_skills_dir/$(basename "$existing_skill")"
    if [[ -e "$source_match" || -L "$source_match" ]]; then
      continue
    fi
    remove_stale_symlink "$existing_skill" "$source_skills_dir" || true
  done
}

sync_harness() {
  local harness_name="$1"
  local source_dir="$harness_root/$harness_name"
  local target_root
  target_root="$(read_harness_root "$harness_name")"

  log "[$harness_name] -> $target_root"
  mkdir -p "$target_root"

  local source_entry
  local base_name
  for source_entry in "$source_dir"/*; do
    [[ -e "$source_entry" ]] || continue
    base_name="$(basename "$source_entry")"
    [[ "$base_name" == ".gitkeep" ]] && continue
    if [[ "$base_name" == "skills" ]]; then
      sync_skills_dir "$source_entry" "$target_root"
      continue
    fi

    sync_target "$source_entry" "$target_root/$base_name" || true
  done

  local existing_entry
  for existing_entry in "$target_root"/*; do
    [[ -e "$existing_entry" || -L "$existing_entry" ]] || continue
    base_name="$(basename "$existing_entry")"
    [[ "$base_name" == "skills" ]] && continue

    if [[ -e "$source_dir/$base_name" || -L "$source_dir/$base_name" ]]; then
      continue
    fi

    remove_stale_symlink "$existing_entry" "$source_dir" || true
  done
}

shopt -s nullglob
harnesses=("$harness_root"/*)
shopt -u nullglob

((${#harnesses[@]} > 0)) || die "no harness directories found in $harness_root"

for harness_path in "${harnesses[@]}"; do
  [[ -d "$harness_path" ]] || continue
  sync_harness "$(basename "$harness_path")"
done

log "Done."
