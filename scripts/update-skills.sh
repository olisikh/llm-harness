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
  - Only considers sources with `type: submodule` in config.yaml.
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

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

SYNC_CONFIG_FILE="$repo_root/config.yaml"

read_configured_submodules() {
  python3 - "$SYNC_CONFIG_FILE" <<'PY'
import sys
from pathlib import Path

import yaml

config_path = Path(sys.argv[1])
if not config_path.exists():
    raise SystemExit(0)

data = yaml.safe_load(config_path.read_text()) or {}
sources = data.get("sources") or {}
for name, entry in sources.items():
    if entry.get("type") == "submodule":
        print(name)
PY
}

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

declare -a configured_submodules=()
while IFS= read -r path; do
  [[ -n "$path" ]] && configured_submodules+=("$path")
done < <(read_configured_submodules)

declare -a declared_submodules=()
while IFS= read -r path; do
  [[ -n "$path" ]] && declared_submodules+=("$path")
done < <(git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}')

if ((${#requested[@]} == 0)); then
  requested=("${configured_submodules[@]}")
fi

for path in "${requested[@]}"; do
  found=false
  for configured in "${configured_submodules[@]}"; do
    if [[ "$configured" == "$path" ]]; then
      found=true
      break
    fi
  done

  if [[ "$found" != true ]]; then
    die "submodule '$path' is not configured as a submodule source in $SYNC_CONFIG_FILE"
  fi

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

updated_any=false

log "Initializing submodules"
git submodule update --init --recursive -- "${requested[@]}"

for path in "${requested[@]}"; do
  log "Checking $path"

  if [[ -n "$(git -C "$path" status --short)" ]]; then
    log "Skipping $path because it has local changes"
    continue
  fi

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

if ! $updated_any; then
  log "No submodule pointer changes detected"
  exit 0
fi

log "Staged submodule updates:"
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
