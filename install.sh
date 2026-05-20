#!/usr/bin/env bash
set -euo pipefail

# This repository now lives at ~/.agents, so ~/.agents/skills is the source
# directory itself. Only create provider-specific links that still need it.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/skills"
AGENTS_FILE="$SCRIPT_DIR/AGENTS.md"

declare -A TOOLS=(
  ["claude"]="$HOME/.claude/skills"
)

declare -A DOCS=(
  ["claude"]="$HOME/.claude/CLAUDE.md"
)

if [[ ! -d "$SKILLS_DIR" ]]; then
  echo "Error: Source directory $SKILLS_DIR does not exist."
  exit 1
fi

if [[ ! -f "$AGENTS_FILE" ]]; then
  echo "Error: Source file $AGENTS_FILE does not exist."
  exit 1
fi

echo "Installing skills symlinks..."
echo "Source: $SKILLS_DIR"
echo ""

for tool in "${!TOOLS[@]}"; do
  target="${TOOLS[$tool]}"
  parent="$(dirname "$target")"

  echo "[$tool]"

  if [[ -L "$target" && "$(readlink "$target")" == "$SKILLS_DIR" ]]; then
    echo "  Already linked. Skipping."
    echo ""
    continue
  fi

  if [[ -d "$target" ]] && [[ "$(ls -A "$target" 2>/dev/null)" ]]; then
    backup="${target}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  Existing directory with content found. Backing up to: $backup"
    mv "$target" "$backup"
  elif [[ -e "$target" || -L "$target" ]]; then
    backup="${target}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  Backing up existing path to: $backup"
    mv "$target" "$backup"
  fi

  if [[ ! -d "$parent" ]]; then
    echo "  Creating parent directory: $parent"
    mkdir -p "$parent"
  fi

  ln -s "$SKILLS_DIR" "$target"
  echo "  Linked: $target -> $SKILLS_DIR"
  echo ""
done

echo "Installing Claude instructions..."
echo "Source: $AGENTS_FILE"
echo ""

for tool in "${!DOCS[@]}"; do
  target="${DOCS[$tool]}"
  parent="$(dirname "$target")"

  echo "[$tool]"

  if [[ -L "$target" && "$(readlink "$target")" == "$AGENTS_FILE" ]]; then
    echo "  Already linked. Skipping."
    echo ""
    continue
  fi

  if [[ -d "$target" ]] && [[ "$(ls -A "$target" 2>/dev/null)" ]]; then
    backup="${target}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  Existing directory with content found. Backing up to: $backup"
    mv "$target" "$backup"
  elif [[ -e "$target" || -L "$target" ]]; then
    backup="${target}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  Backing up existing path to: $backup"
    mv "$target" "$backup"
  fi

  if [[ ! -d "$parent" ]]; then
    echo "  Creating parent directory: $parent"
    mkdir -p "$parent"
  fi

  ln -s "$AGENTS_FILE" "$target"
  echo "  Linked: $target -> $AGENTS_FILE"
  echo ""
done

echo "Done."
