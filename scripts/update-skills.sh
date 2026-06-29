#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/update-skills.sh [--commit] [--push] [submodule...]

Examples:
  ./scripts/update-skills.sh
  ./scripts/update-skills.sh --commit
  ./scripts/update-skills.sh --commit --push
  ./scripts/update-skills.sh obsidian-skills mattpocock-skills

Notes:
  - Updates pinned submodule commit(s) to latest origin default branch tip.
  - Syncs shared skills into harness/<name>/skills using skills-config.yaml.
  - Shared skills default to harness/agents/skills unless explicitly overridden.
  - Skips submodules with local uncommitted changes.
EOF
}

log() {
  printf '[update-skills] %s\n' "$*"
}

die() {
  log "ERROR: $*"
  exit 1
}

resolve_path() {
  python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$1"
}

path_is_within() {
  local path="$1"
  local root="$2"
  [[ "$path" == "$root" || "$path" == "$root"/* ]]
}

read_sync_config() {
  local submodule_path="$1"

  python3 - "$SYNC_CONFIG_FILE" "$submodule_path" <<'PY'
import sys
from pathlib import Path

import yaml

config_path = Path(sys.argv[1])
submodule_path = sys.argv[2]
data = yaml.safe_load(config_path.read_text()) or {}
entry = (data.get("submodules") or {}).get(submodule_path) or {}

sources = entry.get("sources")
if sources is None:
    root = entry.get("root", "")
    harness = entry.get("harness", "")
    if root or harness:
        sources = [{"root": root, "harness": harness}]
    else:
        sources = []

exclude = entry.get("exclude") or []
overrides = entry.get("overrides") or {}

if exclude and not isinstance(exclude, list):
    raise SystemExit(f"exclude for {submodule_path} must be a list")
if overrides and not isinstance(overrides, dict):
    raise SystemExit(f"overrides for {submodule_path} must be a mapping")
if sources and not isinstance(sources, list):
    raise SystemExit(f"sources for {submodule_path} must be a list")

print(len(sources))
for source in sources:
    if not isinstance(source, dict):
        raise SystemExit(f"source entries for {submodule_path} must be mappings")
    print(f"source\t{source.get('root', '')}\t{source.get('harness', '')}")
for value in exclude:
    print(f"exclude\t{value}")
for key, value in sorted(overrides.items()):
    print(f"override\t{key}\t{value}")
PY
}

load_sync_config_for_submodule() {
  local submodule_path="$1"
  local line

  submodule_source_roots=()
  submodule_source_harnesses=()
  submodule_skills_excludes=()
  declare -gA submodule_skill_overrides=()
  local source_count=0
  local sources_read=0

  while IFS= read -r line; do
    if (( sources_read == 0 )); then
      source_count="$line"
      sources_read=1
      continue
    fi

    if (( ${#submodule_source_roots[@]} < source_count )) && [[ "$line" == source$'\t'* ]]; then
      local payload="${line#*$'\t'}"
      local root="${payload%%$'\t'*}"
      local harness_name="${payload#*$'\t'}"
      submodule_source_roots+=("$root")
      submodule_source_harnesses+=("$harness_name")
      continue
    fi

    if [[ "$line" == exclude$'\t'* ]]; then
      submodule_skills_excludes+=("${line#*$'\t'}")
    elif [[ "$line" == override$'\t'* ]]; then
      local payload="${line#*$'\t'}"
      local rel_path="${payload%%$'\t'*}"
      local harness_name="${payload#*$'\t'}"
      submodule_skill_overrides["$rel_path"]="$harness_name"
    fi
  done < <(read_sync_config "$submodule_path")
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

SYNC_CONFIG_FILE="$repo_root/skills-config.yaml"
[[ -f "$SYNC_CONFIG_FILE" ]] || die "missing sync config: $SYNC_CONFIG_FILE"

commit_changes=false
push_changes=false

declare -a requested=()
while (($# > 0)); do
  case "$1" in
    --commit)
      commit_changes=true
      ;;
    --push)
      push_changes=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      requested+=("$1")
      ;;
  esac
  shift
done

if $push_changes && ! $commit_changes; then
  die "--push only makes sense together with --commit"
fi

declare -a declared_submodules=()
while IFS= read -r path; do
  [[ -n "$path" ]] && declared_submodules+=("$path")
done < <(git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}')

if ((${#requested[@]} == 0)); then
  requested=("${declared_submodules[@]}")
fi

for path in "${requested[@]}"; do
  found=false
  for declared in "${declared_submodules[@]}"; do
    if [[ "$declared" == "$path" ]]; then
      found=true
      break
    fi
  done

  if [[ "$found" != true ]]; then
    die "submodule '$path' is not declared in $repo_root/.gitmodules"
  fi
done

current_branch="$(git branch --show-current)"
[[ -n "$current_branch" ]] || die "parent repo is not on a branch"

declare -a changed_paths=()
declare -a syncable_submodules=()
declare -a submodule_source_roots=()
declare -a submodule_source_harnesses=()
declare -a submodule_skills_excludes=()
declare -A submodule_skill_overrides=()

synced_any=false

sync_link() {
  local dest_rel="$1"
  local source_abs="$2"
  local dest_abs="$repo_root/$dest_rel"
  local dest_parent
  dest_parent="$(dirname "$dest_abs")"

  mkdir -p "$dest_parent"

  if [[ -L "$dest_abs" ]]; then
    if [[ "$(resolve_path "$dest_abs")" == "$source_abs" ]]; then
      return 1
    fi

    rm "$dest_abs"
  elif [[ -e "$dest_abs" ]]; then
    log "Skipping local path $dest_rel"
    return 1
  fi

  ln -s "$source_abs" "$dest_abs"
  changed_paths+=("$dest_rel")
  synced_any=true
  log "Synced $dest_rel -> $source_abs"
  return 0
}

remove_link() {
  local dest_rel="$1"
  local dest_abs="$repo_root/$dest_rel"

  [[ -L "$dest_abs" ]] || return 1

  rm "$dest_abs"
  changed_paths+=("$dest_rel")
  synced_any=true
  log "Removed stale $dest_rel"
  return 0
}

sync_submodule_skills() {
  local submodule_path="$1"

  load_sync_config_for_submodule "$submodule_path"

  if ((${#submodule_source_roots[@]} == 0)); then
    log "Skipping symlink sync for $submodule_path because skills-config.yaml has no entry"
    return 0
  fi

  local rel_path
  local skill_name
  local harness_name
  local source_abs
  local dest_rel
  local source_root
  local source_index
  declare -A desired_dest_to_source=()
  declare -A desired_dest_seen=()
  declare -A source_roots_seen=()

  for ((source_index = 0; source_index < ${#submodule_source_roots[@]}; source_index++)); do
    local source_root_rel="${submodule_source_roots[$source_index]}"
    local default_harness="${submodule_source_harnesses[$source_index]}"

    if [[ -z "$source_root_rel" || -z "$default_harness" ]]; then
      die "incomplete source config for $submodule_path in $SYNC_CONFIG_FILE"
    fi

    source_root="$repo_root/$submodule_path/$source_root_rel"
    [[ -d "$source_root" ]] || die "expected skills directory missing: $source_root"
    source_roots_seen["$source_root"]="1"

    while IFS= read -r rel_path; do
      [[ -n "$rel_path" ]] || continue

      local skip=false
      local excluded
      for excluded in "${submodule_skills_excludes[@]}"; do
        if [[ "$excluded" == "$rel_path" ]]; then
          skip=true
          break
        fi
      done
      $skip && continue

      skill_name="$(basename "$rel_path")"
      harness_name="${submodule_skill_overrides[$rel_path]:-$default_harness}"
      source_abs="$source_root/$rel_path"
      dest_rel="harness/$harness_name/skills/$skill_name"

      if [[ -n "${desired_dest_seen[$dest_rel]:-}" ]]; then
        die "duplicate destination '$dest_rel' while syncing $submodule_path"
      fi

      desired_dest_seen["$dest_rel"]="1"
      desired_dest_to_source["$dest_rel"]="$source_abs"
      sync_link "$dest_rel" "$source_abs" || true
    done < <(python3 - "$source_root" <<'PY'
import os
import sys

root = sys.argv[1]
for current_root, dirs, files in os.walk(root):
    dirs.sort()
    if "SKILL.md" in files:
        print(os.path.relpath(current_root, root))
        dirs[:] = []
PY
)
  done

  local harness_dir
  for harness_dir in "$repo_root/harness"/*; do
    [[ -d "$harness_dir/skills" ]] || continue
    local existing_path
    for existing_path in "$harness_dir/skills"/*; do
      [[ -e "$existing_path" || -L "$existing_path" ]] || continue
      [[ -L "$existing_path" ]] || continue

      local existing_rel="${existing_path#$repo_root/}"
      local resolved
      resolved="$(resolve_path "$existing_path")"

      local from_known_source=false
      local known_source_root
      for known_source_root in "${!source_roots_seen[@]}"; do
        if path_is_within "$resolved" "$known_source_root"; then
          from_known_source=true
          break
        fi
      done

      if [[ "$from_known_source" != true ]]; then
        continue
      fi

      if [[ -n "${desired_dest_to_source[$existing_rel]:-}" ]]; then
        continue
      fi

      remove_link "$existing_rel" || true
    done
  done
}

sync_requested_links() {
  local path

  for path in "${syncable_submodules[@]}"; do
    sync_submodule_skills "$path"
  done

  if ((${#changed_paths[@]} > 0)); then
    git add -A -- "${changed_paths[@]}"
  fi
}

log "Initializing submodules"
git submodule update --init --recursive -- "${requested[@]}"

updated_any=false

for path in "${requested[@]}"; do
  log "Checking $path"

  if [[ -n "$(git -C "$path" status --short)" ]]; then
    log "Skipping $path because it has local changes"
    continue
  fi

  syncable_submodules+=("$path")

  git -C "$path" fetch --prune origin

  remote_head_ref="$(git -C "$path" symbolic-ref --quiet refs/remotes/origin/HEAD || true)"
  if [[ -z "$remote_head_ref" ]]; then
    if git -C "$path" rev-parse --verify --quiet origin/main >/dev/null; then
      remote_head_ref="refs/remotes/origin/main"
    elif git -C "$path" rev-parse --verify --quiet origin/master >/dev/null; then
      remote_head_ref="refs/remotes/origin/master"
    else
      log "Skipping $path because origin HEAD is unavailable"
      continue
    fi
  fi

  target_commit="$(git -C "$path" rev-parse "$remote_head_ref")"
  current_commit="$(git -C "$path" rev-parse HEAD)"

  if [[ "$current_commit" == "$target_commit" ]]; then
    log "$path is already up to date"
    continue
  fi

  git -C "$path" checkout --detach "$target_commit" >/dev/null
  git add "$path"
  updated_any=true
  log "Updated $path to $(git -C "$path" rev-parse --short HEAD)"
done

sync_requested_links

if ! $updated_any && ! $synced_any; then
  log "No submodule pointer or symlink changes detected"
  exit 0
fi

log "Staged shared skill updates:"
git diff --cached --submodule=short

if ! $commit_changes; then
  log "Done. Review and commit when ready."
  exit 0
fi

git commit -m "chore: update shared skill submodules"
log "Committed on $current_branch"

if $push_changes; then
  git push origin "$current_branch"
  log "Pushed $current_branch"
fi
