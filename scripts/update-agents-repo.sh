#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
LOCKDIR="/tmp/update-llm-harness-repo.lock"

cleanup() {
  rmdir "$LOCKDIR" 2>/dev/null || true
}
trap cleanup EXIT

if ! mkdir "$LOCKDIR" 2>/dev/null; then
  echo "update-llm-harness: skipped (lock held)"
  exit 0
fi

if [[ ! -d "$REPO_ROOT/.git" ]]; then
  echo "update-llm-harness: repo missing: $REPO_ROOT"
  exit 1
fi

cd "$REPO_ROOT"

echo "== repo =="
pwd

echo "== pull =="
git pull --rebase --autostash origin main

echo "== update shared skill submodules =="
./scripts/update-skills.sh --commit --push

echo "== install harness links =="
./install.sh

echo "== git status =="
git status --short --branch
