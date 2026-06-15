#!/usr/bin/env bash

set -euo pipefail

AGENTS_DIR="${HOME}/.agents"
HERMES_STATE_SUBMODULE_PATH="hermes-state"
SUBMODULE_COMMIT_MSG="chore(hermes): backup state"

if [[ ! -d "${AGENTS_DIR}/.git" ]]; then
  echo "error: ~/.agents is not a git repository"
  exit 1
fi

echo "[hermes-state] initializing submodule"
cd "${AGENTS_DIR}"
git submodule update --init --recursive -- "${HERMES_STATE_SUBMODULE_PATH}"

submodule_dir="${AGENTS_DIR}/${HERMES_STATE_SUBMODULE_PATH}"
if [[ ! -d "${submodule_dir}" ]]; then
  echo "error: submodule path missing: ${submodule_dir}"
  exit 1
fi

echo "[hermes-state] syncing submodule with origin"
cd "${submodule_dir}"

git fetch --quiet origin
if git rev-parse --verify --quiet origin/main >/dev/null; then
  target_branch="main"
elif git rev-parse --verify --quiet origin/master >/dev/null; then
  target_branch="master"
else
  echo "error: hermes-state origin has neither main nor master"
  exit 1
fi

git switch --quiet "${target_branch}" 2>/dev/null || git switch --quiet -c "${target_branch}" --track "origin/${target_branch}"

if ! git diff --quiet || ! git diff --cached --quiet || [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
  git add -A
  if ! git diff --cached --quiet; then
    git commit -m "${SUBMODULE_COMMIT_MSG}" >/dev/null
    echo "[hermes-state] committed local changes on ${target_branch}"
  fi
fi

git pull --quiet --rebase origin "${target_branch}"
if [[ "$(git rev-parse HEAD)" != "$(git rev-parse "origin/${target_branch}")" ]]; then
  git push --quiet origin "${target_branch}"
  echo "[hermes-state] pushed ${target_branch}"
fi

echo "[hermes-state] synced submodule worktree on ${target_branch}"
