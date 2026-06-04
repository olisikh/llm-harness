#!/usr/bin/env bash

set -euo pipefail

AGENTS_DIR="${HOME}/.agents"
HERMES_SKILLS_DIR="${HOME}/.hermes/skills"
HERMES_STATE_SUBMODULE_PATH="hermes-state"
HERMES_SKILLS_RELATIVE_IN_SUBMODULE="skills"

if [[ ! -d "${AGENTS_DIR}/.git" ]]; then
  echo "error: ~/.agents is not a git repository"
  exit 1
fi

if [[ ! -d "${HERMES_SKILLS_DIR}" ]]; then
  echo "error: ~/.hermes/skills does not exist"
  exit 1
fi

echo "[hermes-state] initializing submodule"
cd "${AGENTS_DIR}"
git submodule update --init --recursive -- "${HERMES_STATE_SUBMODULE_PATH}"

submodule_skills_dir="${AGENTS_DIR}/${HERMES_STATE_SUBMODULE_PATH}/${HERMES_SKILLS_RELATIVE_IN_SUBMODULE}"
if [[ ! -d "${submodule_skills_dir}" ]]; then
  echo "error: submodule path missing: ${submodule_skills_dir}"
  exit 1
fi

echo "[hermes-state] syncing submodule with origin"
cd "${AGENTS_DIR}/${HERMES_STATE_SUBMODULE_PATH}"

git fetch --quiet origin
if git rev-parse --verify --quiet origin/main >/dev/null; then
  git checkout --quiet origin/main
elif git rev-parse --verify --quiet origin/master >/dev/null; then
  git checkout --quiet origin/master
fi

echo "[hermes-state] linking ~/.hermes/skills -> submodule"
for item in "${HERMES_SKILLS_DIR}"/*; do
  [[ -e "${item}" ]] || continue
  base="$(basename "${item}")"
  src="${submodule_skills_dir}/${base}"

  if [[ ! -e "${src}" && ! -L "${src}" ]]; then
    echo "[hermes-state] skipping ${base} (not in submodule)"
    continue
  fi

  if [[ -L "${item}" ]]; then
    current_target="$(readlink "${item}")"
    if [[ "${current_target}" == "${src}" ]]; then
      continue
    fi
    rm "${item}"
    ln -s "${src}" "${item}"
    continue
  fi

  if [[ -d "${item}" ]]; then
    backup="${item}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "[hermes-state] backing up real directory ${item} -> ${backup}"
    mv "${item}" "${backup}"
    ln -s "${src}" "${item}"
    continue
  fi

  backup="${item}.backup.$(date +%Y%m%d_%H%M%S)"
  echo "[hermes-state] backing up file ${item} -> ${backup}"
  mv "${item}" "${backup}"
  ln -s "${src}" "${item}"
done

echo "[hermes-state] done"
