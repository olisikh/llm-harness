#!/usr/bin/env bash
set -euo pipefail

REPO="${HOME}/.agents"
LOCKDIR="/tmp/update-agents-repo.lock"

cleanup() {
  rmdir "$LOCKDIR" 2>/dev/null || true
}
trap cleanup EXIT

if ! mkdir "$LOCKDIR" 2>/dev/null; then
  echo "update-agents-repo: skipped (lock held)"
  exit 0
fi

if [[ ! -d "$REPO/.git" ]]; then
  echo "update-agents-repo: repo missing: $REPO"
  exit 1
fi

cd "$REPO"
./scripts/update-skills.sh --commit --push
