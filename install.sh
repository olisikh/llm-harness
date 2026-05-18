#!/usr/bin/env bash
set -euo pipefail

# Philosophy: Only create symlinks for paths that are NOT covered by the
# generic ~/.agents/skills standard. Many harnesses (GitHub Copilot, OpenCode,
# Cursor, and others that follow the Agent Skills spec) read from the generic
# ~/.agents/skills path — no provider-specific symlink needed for those.
#
# Paths we DO create:
#   ~/.claude/skills   -> Anthropic-specific; does not read ~/.agents/skills
#   ~/.agents/skills   -> Generic standard shared across Copilot, OpenCode, etc.
#
# Paths we intentionally SKIP:
#   ~/.copilot/skills  -> Covered by ~/.agents/skills (Copilot reads both)
#   ~/.codex/skills    -> Codex CLI has no native skills directory support
#   ~/.opencode/skills -> Covered by ~/.agents/skills
#   ~/.cursor/skills   -> Covered by ~/.agents/skills

SKILLS_DIR="$HOME/.skills"

declare -A TOOLS=(
  ["claude"]="$HOME/.claude/skills"
  ["agents"]="$HOME/.agents/skills"
)

if [[ ! -d "$SKILLS_DIR" ]]; then
  echo "Error: Source directory $SKILLS_DIR does not exist."
  exit 1
fi

echo "Installing skills symlinks..."
echo "Source: $SKILLS_DIR"
echo ""

for tool in "${!TOOLS[@]}"; do
  target="${TOOLS[$tool]}"
  parent="$(dirname "$target")"

  echo "[$tool]"

  # Already correctly linked?
  if [[ -L "$target" && "$(readlink "$target")" == "$SKILLS_DIR" ]]; then
    echo "  Already linked. Skipping."
    echo ""
    continue
  fi

  # Exists as a real directory with content — don't clobber native skills
  if [[ -d "$target" ]] && [[ "$(ls -A "$target" 2>/dev/null)" ]]; then
    backup="${target}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  Existing directory with content found. Backing up to: $backup"
    mv "$target" "$backup"
  elif [[ -e "$target" || -L "$target" ]]; then
    # Empty dir, file, or broken/incorrect symlink — safe to replace
    backup="${target}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  Backing up existing path to: $backup"
    mv "$target" "$backup"
  fi

  # Create parent directory if needed
  if [[ ! -d "$parent" ]]; then
    echo "  Creating parent directory: $parent"
    mkdir -p "$parent"
  fi

  ln -s "$SKILLS_DIR" "$target"
  echo "  Linked: $target -> $SKILLS_DIR"
  echo ""
done

echo "Done."
