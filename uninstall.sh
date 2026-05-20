#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/skills"
AGENTS_FILE="$SCRIPT_DIR/AGENTS.md"

declare -A TOOLS=(
  ["claude"]="$HOME/.claude/skills"
)

declare -A DOCS=(
  ["claude"]="$HOME/.claude/CLAUDE.md"
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

for tool in "${!DOCS[@]}"; do
  target="${DOCS[$tool]}"

  echo "[$tool CLAUDE.md]"

  if [[ -L "$target" && "$(readlink "$target")" == "$AGENTS_FILE" ]]; then
    rm "$target"
    echo "  Removed symlink: $target"
  elif [[ -e "$target" || -L "$target" ]]; then
    echo "  Skipped: $target exists but does not point to $AGENTS_FILE"
  else
    echo "  Nothing to do: $target does not exist"
  fi
  echo ""
done

echo "Done."
