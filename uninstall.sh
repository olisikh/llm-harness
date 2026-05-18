#!/usr/bin/env bash
set -euo pipefail

SKILLS_DIR="$HOME/.skills"

# Same paths as install.sh — only the ones we actually manage.
declare -A TOOLS=(
  ["claude"]="$HOME/.claude/skills"
  ["agents"]="$HOME/.agents/skills"
)

echo "Uninstalling skills symlinks..."
echo ""

for tool in "${!TOOLS[@]}"; do
  target="${TOOLS[$tool]}"

  echo "[$tool]"

  if [[ -L "$target" && "$(readlink "$target")" == "$SKILLS_DIR" ]]; then
    rm "$target"
    echo "  Removed symlink: $target"
  elif [[ -e "$target" || -L "$target" ]]; then
    echo "  Skipped: $target exists but does not point to $SKILLS_DIR"
  else
    echo "  Nothing to do: $target does not exist"
  fi
  echo ""
done

echo "Done."
