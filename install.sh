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
shared_skills_config="$repo_root/config.yaml"

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

list_configured_skills() {
  python3 - "$shared_skills_config" "$repo_root" <<'PY'
import os
import sys
from pathlib import Path

import yaml

config_path = Path(sys.argv[1])
repo_root = Path(sys.argv[2])

if not config_path.exists():
    raise SystemExit(0)

data = yaml.safe_load(config_path.read_text()) or {}
sources = data.get("sources") or {}

for source_name, entry in sources.items():
    source_base = repo_root / source_name
    if not source_base.exists():
        continue

    child_sources = entry.get("sources")
    if child_sources is None:
        root = entry.get("root", "")
        harness = entry.get("harness", "")
        if root or harness:
            child_sources = [{"root": root, "harness": harness}]
        else:
            child_sources = []

    excludes = set(entry.get("exclude") or [])
    overrides = entry.get("overrides") or {}

    for source in child_sources:
        root_rel = source.get("root", "")
        default_harness = source.get("harness", "")
        if not root_rel or not default_harness:
            continue

        source_root = source_base / root_rel
        if not source_root.exists():
            continue

        for current_root, dirs, files in os.walk(source_root, followlinks=False):
            dirs.sort()
            files.sort()
            if "SKILL.md" in files:
                rel = os.path.relpath(current_root, source_root)
                if rel in excludes:
                    dirs[:] = []
                    continue
                harness = overrides.get(rel, default_harness)
                print(f"{harness}\t{rel}\t{current_root}")
                dirs[:] = []
PY
}

list_target_managed_symlinks() {
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

sync_target() {
  local source_abs="$1"
  local target_abs="$2"
  local expected_resolved
  expected_resolved="$(resolve_path "$source_abs")"

  if [[ -L "$target_abs" ]]; then
    if [[ "$(resolve_path "$target_abs")" == "$expected_resolved" ]]; then
      log "Link already exists at $target_abs"
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

sync_harness() {
  local harness_name="$1"
  local source_dir="$harness_root/$harness_name"
  local target_root
  target_root="$(read_harness_root "$harness_name")"

  log "[$harness_name] -> $target_root"
  mkdir -p "$target_root"

  local target_skills_dir="$target_root/skills"
  mkdir -p "$target_skills_dir"

  declare -A desired_sources=()
  declare -A desired_targets_by_source=()
  local rel_path
  local source_skill
  local target_skill
  local harness_for_skill
  local configured_source

  # Configured skill sources (submodules and local) install directly to target,
  # preserving nested category paths. Later sources in config order win on
  # target-path collision.
  while IFS=$'\t' read -r harness_for_skill rel_path configured_source; do
    [[ -n "$harness_for_skill" ]] || continue
    [[ "$harness_for_skill" == "$harness_name" ]] || continue

    target_skill="$target_skills_dir/$rel_path"
    if [[ -n "${desired_sources[$target_skill]:-}" ]]; then
      warn "Source collision at $target_skill; later config wins"
    fi
    desired_sources["$target_skill"]="$configured_source"
    desired_targets_by_source["$configured_source"]="$target_skill"
  done < <(list_configured_skills)

  for target_skill in "${!desired_sources[@]}"; do
    source_skill="${desired_sources[$target_skill]}"
    sync_target "$source_skill" "$target_skill" || true
  done

  local existing_symlink
  local existing_target
  while IFS= read -r existing_symlink; do
    [[ -n "$existing_symlink" ]] || continue

    existing_target="$(resolve_path "$existing_symlink")"
    if [[ -n "${desired_targets_by_source[$existing_target]:-}" ]]; then
      continue
    fi

    rm "$existing_symlink"
    log "Removed stale $existing_symlink"
    prune_empty_parent_dirs "$existing_symlink" "$target_skills_dir"
  done < <(list_target_managed_symlinks "$target_skills_dir" "$repo_root")

  local source_entry
  local base_name
  for source_entry in "$source_dir"/*; do
    [[ -e "$source_entry" || -L "$source_entry" ]] || continue
    base_name="$(basename "$source_entry")"
    [[ "$base_name" == ".gitkeep" ]] && continue
    [[ "$base_name" == "skills" ]] && continue

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
