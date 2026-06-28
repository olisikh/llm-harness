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
  - Syncs managed skill symlinks using skills-config.yaml.
  - Stages changed submodule pointers and symlink paths in parent repo.
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

relative_path() {
  python3 -c 'import os, sys; print(os.path.relpath(sys.argv[2], sys.argv[1]))' "$1" "$2"
}

path_is_within() {
  local path="$1"
  local root="$2"
  [[ "$path" == "$root" || "$path" == "$root"/* ]]
}

contains_item() {
  local needle="$1"
  shift || true

  local item
  for item in "$@"; do
    if [[ "$item" == "$needle" ]]; then
      return 0
    fi
  done

  return 1
}

list_skill_dirs() {
  python3 - "$1" <<'PY'
import os
import sys

root = sys.argv[1]
for current_root, dirs, files in os.walk(root):
    dirs.sort()
    if "SKILL.md" in files:
        print(os.path.relpath(current_root, root))
        dirs[:] = []
PY
}

list_symlink_paths() {
  python3 - "$1" <<'PY'
import os
import sys

root = sys.argv[1]
for current_root, dirs, files in os.walk(root):
    dirs.sort()
    names = sorted(dirs + files)
    for name in names:
        path = os.path.join(current_root, name)
        if os.path.islink(path):
            print(os.path.relpath(path, root))
PY
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
submodules = data.get("submodules") or {}
entry = submodules.get(submodule_path) or {}

skills_root = entry.get("root", "")
skills_dest = entry.get("dest", "")
skills_exclude = entry.get("exclude") or []

if not isinstance(skills_exclude, list):
    raise SystemExit(f"skillsExclude for {submodule_path} must be list")

print(skills_root)
print(skills_dest)
for value in skills_exclude:
    print(f"exclude\t{value}")
PY
}

load_sync_config_for_submodule() {
  local submodule_path="$1"
  local line
  local index=0

  submodule_skills_root=""
  submodule_skills_dest=""
  submodule_skills_excludes=()

  while IFS= read -r line; do
    case "$index" in
      0)
        submodule_skills_root="$line"
        ;;
      1)
        submodule_skills_dest="$line"
        ;;
      *)
        if [[ "$line" == exclude$'\t'* ]]; then
          submodule_skills_excludes+=("${line#*$'\t'}")
        fi
        ;;
    esac
    index=$((index + 1))
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
declare -a submodule_skills_excludes=()

synced_any=false
submodule_skills_root=""
submodule_skills_dest=""

sync_link() {
  local dest_rel="$1"
  local link_target="$2"
  local source_abs="$3"

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
    die "refusing to replace non-symlink path '$dest_rel'"
  fi

  ln -s "$link_target" "$dest_abs"
  changed_paths+=("$dest_rel")
  synced_any=true
  log "Synced $dest_rel -> $link_target"
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

  if [[ -z "$submodule_skills_root" && -z "$submodule_skills_dest" ]]; then
    log "Skipping symlink sync for $submodule_path because skills-config.yaml has no entry"
    return 0
  fi

  if [[ -z "$submodule_skills_root" || -z "$submodule_skills_dest" ]]; then
    die "incomplete sync config for $submodule_path in $SYNC_CONFIG_FILE"
  fi

  local source_root="$repo_root/$submodule_path/$submodule_skills_root"
  local dest_root="$repo_root/$submodule_skills_dest"
  [[ -d "$source_root" ]] || die "expected skills directory missing: $source_root"

  mkdir -p "$dest_root"

  local desired=()
  local rel_path
  local source_abs
  local dest_rel
  local link_target
  local dest_abs
  local resolved

  while IFS= read -r rel_path; do
    [[ -n "$rel_path" ]] || continue
    if contains_item "$rel_path" "${submodule_skills_excludes[@]}"; then
      continue
    fi

    desired+=("$rel_path")
    source_abs="$source_root/$rel_path"
    dest_rel="$submodule_skills_dest/$rel_path"
    link_target="$(relative_path "$(dirname "$repo_root/$dest_rel")" "$source_abs")"
    sync_link "$dest_rel" "$link_target" "$source_abs" || true
  done < <(list_skill_dirs "$source_root")

  while IFS= read -r rel_path; do
    [[ -n "$rel_path" ]] || continue

    dest_rel="$submodule_skills_dest/$rel_path"
    dest_abs="$repo_root/$dest_rel"
    resolved="$(resolve_path "$dest_abs")"

    if ! path_is_within "$resolved" "$source_root"; then
      continue
    fi

    if contains_item "$rel_path" "${desired[@]}"; then
      continue
    fi

    remove_link "$dest_rel" || true
  done < <(list_symlink_paths "$dest_root")
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
