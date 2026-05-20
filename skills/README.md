# LLM Skills

A personal collection of LLM skills for customizing AI workflows across Claude Code, Codex, Gemini CLI, Qwen Code, OpenCode, and other LLM-powered tools.

---

## What Are LLM Skills?

Skills are reusable instruction sets that teach LLMs how to perform specific tasks according to your requirements. By packaging context, best practices, and workflows into structured `SKILL.md` files, you can make AI assistance more consistent, repeatable, and aligned with how you work.

Each skill in this repository is self-contained and ready to use with any LLM platform that supports file-based context or custom instructions.

---

## Quick Start

### Automated Setup (Recommended)

Run the install script from the repository root to symlink `skills/` to supported tool skill paths and expose `AGENTS.md` to Claude as `~/.claude/CLAUDE.md`:

```bash
./install.sh
```

This will link this repository's `skills/` directory to the appropriate tool-specific locations and link `AGENTS.md` to `~/.claude/CLAUDE.md`. Since this repository already lives at `~/.agents`, no `~/.agents/skills` symlink is created.

To remove the symlinks later:

```bash
./uninstall.sh
```

### Manual Setup

If you prefer to manage skills per-project or per-tool, copy individual skill folders to the correct location:

**Claude Code**

```bash
# Project-local (recommended for team/shared projects)
mkdir -p .claude/skills
cp -r /path/to/this/repo/webapp-testing .claude/skills/

# Or user-global (available in all projects)
mkdir -p ~/.claude/skills
cp -r /path/to/this/repo/webapp-testing ~/.claude/skills/
```

**Other Platforms (Codex, Gemini, OpenCode, Qwen Code)**

Most CLI tools don't natively load Anthropic's skill format, but you can still use them by referencing the `SKILL.md` directly in your prompts:

```bash
# Example with Gemini CLI
@/path/to/repo/webapp-testing/SKILL.md "Test the login page and report any issues."
```

Or copy the relevant sections from `SKILL.md` into your system prompt or configuration.

### Using a Skill

Just ask in natural language, optionally mentioning the skill by name:
> "Use the **Webapp Testing** skill to validate the checkout flow and generate `report.md`."

---

## Discovering and Installing New Skills

When you want a new `SKILL.md`-based skill added to this repository, ask for it by name or describe the capability you need. The expected workflow is:

1. Find the best matching skill from a trusted registry or source repository.
2. Review the skill folder before installing it, including `SKILL.md` and any associated `scripts/`, `references/`, `assets/`, templates, examples, or dependency files.
3. Copy the complete skill folder into this repository using the existing kebab-case directory naming style.
4. Preserve helper files that the skill depends on, but avoid copying unrelated repository metadata or unrelated skills.
5. Update this README's skill inventory and platform notes if the new skill changes the documented setup.
6. Run any lightweight validation that fits the skill, such as checking file layout, script executability, or referenced paths.
7. Commit and push the new skill when requested.

### Primary Discovery Sources

| Source | What to Use It For |
|--------|--------------------|
| [agentskills.io](https://agentskills.io/) | Canonical Agent Skills standard, complete format spec, and skill directory. Skills are folders with `SKILL.md` plus optional `scripts/`, `references/`, and `assets/`. |
| [github.com/anthropics/skills](https://github.com/anthropics/skills) | Anthropic's public skills repository with pre-built document skills and reference implementations. |
| [skillsllm.com](https://skillsllm.com/) | Marketplace for sharing, exploring, and installing skills. |
| [mcpservers.org/agent-skills](https://mcpservers.org/agent-skills) | Agent Skills Library with reusable skills for Claude Code, Codex, and similar coding agents. |
| [fast-agent.ai/agents/skills](https://fast-agent.ai/agents/skills) | fast-agent skill marketplace, including the fast-agent Skills registry, Hugging Face Skills, and other configured registries. |
| [OpenCode docs](https://opencode.ai/docs/) | OpenCode skill loading behavior and compatible `SKILL.md` paths. |

### Install Checklist

Use this checklist when importing a skill from an external source:

- Confirm the source license allows reuse in this repository.
- Prefer complete skill folders over single copied `SKILL.md` files when scripts or assets are referenced.
- Keep the upstream folder structure intact when `SKILL.md` references relative paths.
- Rename only when needed to avoid collisions or match local naming conventions; update internal references if renamed.
- Scan scripts before adding them, especially install scripts, shell commands, network calls, and file deletion logic.
- Add or keep dependency files such as `requirements.txt`, `package.json`, or lockfiles only when the skill's scripts require them.
- Avoid committing generated outputs, caches, local credentials, `.env` files, or platform-specific state.

---

## Skill Inventory

### Document Processing

| Skill | Description |
|-------|-------------|
| [docx](./document-skills/docx/) | Create, edit, and analyze Word documents with tracked changes, comments, and formatting. |
| [pdf](./document-skills/pdf/) | Extract text and tables, create, merge, split, and annotate PDFs. |
| [pptx](./document-skills/pptx/) | Create, edit, and analyze presentations with layouts, templates, and speaker notes. |
| [xlsx](./document-skills/xlsx/) | Spreadsheet manipulation with formulas, formatting, data analysis, and visualization. |

### Obsidian & Notes

| Skill | Description |
|-------|-------------|
| [defuddle](./defuddle/) | Extract clean Markdown from web pages for vault-ready notes. |
| [json-canvas](./json-canvas/) | Create and edit Obsidian JSON Canvas files. |
| [obsidian-bases](./obsidian-bases/) | Create and edit Obsidian Bases with views, filters, formulas, and summaries. |
| [obsidian-cli](./obsidian-cli/) | Manage Obsidian vaults through the Obsidian CLI. |
| [obsidian-markdown](./obsidian-markdown/) | Create and edit Obsidian-flavored Markdown with properties, wikilinks, embeds, and callouts. |

### Development & Engineering

| Skill | Description |
|-------|-------------|
| [artifacts-builder](./artifacts-builder/) | Create elaborate, multi-component HTML artifacts using React, Tailwind CSS, and shadcn/ui. |
| [changelog-generator](./changelog-generator/) | Generate user-facing changelogs from git commits, categorized and customer-friendly. |
| [explain](./explain/) | Explain code, concepts, or systems clearly. Adapts depth based on the question. |
| [fix-issue](./fix-issue/) | Fix GitHub issues by analyzing the problem, exploring the codebase, and implementing fixes. |
| [git-commit](./git-commit/) | Stage and commit changes with well-crafted commit messages based on diffs. |
| [mcp-builder](./mcp-builder/) | Guide for building MCP (Model Context Protocol) servers to integrate external APIs with LLMs. |
| [skill-creator](./skill-creator/) | Guidance for creating effective, reusable skills with proper structure and documentation. |
| [summarize-changes](./summarize-changes/) | Summarize uncommitted changes, flag risks, and highlight what changed in a reviewable format. |
| [template-skill](./template-skill/) | A starter template for creating new skills. Copy and customize to build your own. |
| [test-gen](./test-gen/) | Generate tests for functions, files, or features matching your project's existing test style. |
| [webapp-testing](./webapp-testing/) | Test local web applications with Playwright for UI validation, debugging, and screenshots. |

### Business & Marketing

| Skill | Description |
|-------|-------------|
| [brand-guidelines](./brand-guidelines/) | Apply Anthropic's official brand colors and typography to artifacts for consistent visual identity. |
| [competitive-ads-extractor](./competitive-ads-extractor/) | Extract and analyze competitor ads from ad libraries to understand messaging and creative approaches. |
| [domain-name-brainstormer](./domain-name-brainstormer/) | Generate creative domain name ideas and check availability across .com, .io, .dev, .ai, and more. |
| [internal-comms](./internal-comms/) | Write internal communications (status reports, updates, FAQs, newsletters) using standard formats. |
| [lead-research-assistant](./lead-research-assistant/) | Identify and qualify leads by analyzing your product and searching for target companies. |

### Communication & Writing

| Skill | Description |
|-------|-------------|
| [content-research-writer](./content-research-writer/) | Write high-quality content with research, citations, hooks, and real-time section feedback. |
| [meeting-insights-analyzer](./meeting-insights-analyzer/) | Analyze meeting transcripts for behavioral patterns, filler words, speaking ratios, and leadership insights. |

### Creative & Media

| Skill | Description |
|-------|-------------|
| [algorithmic-art](./algorithmic-art/) | Create algorithmic art using p5.js with seeded randomness and interactive parameter exploration. |
| [canvas-design](./canvas-design/) | Create beautiful visual art in PNG and PDF documents for posters, designs, and static pieces. |
| [image-enhancer](./image-enhancer/) | Improve image quality, resolution, sharpness, and clarity for presentations and documentation. |
| [slack-gif-creator](./slack-gif-creator/) | Create animated GIFs optimized for Slack with size validation and composable animation primitives. |
| [theme-factory](./theme-factory/) | Apply professional font and color themes to slides, docs, reports, and HTML landing pages. |
| [video-downloader](./video-downloader/) | Download videos from YouTube and other platforms for offline viewing, editing, or archival. |

### Productivity & Organization

| Skill | Description |
|-------|-------------|
| [apple-notes-to-obsidian](./apple-notes-to-obsidian/) | Export Apple Notes into the Obsidian vault with routing and sensitive-note triage. |
| [caveman](./caveman/) | Ultra-compressed communication mode. Cuts token usage while keeping full technical accuracy. |
| [caveman-commit](./caveman-commit/) | Generate ultra-compressed conventional commit messages. |
| [caveman-review](./caveman-review/) | Write terse, actionable code review comments. |
| [compress](./compress/) | Compress natural-language memory files while preserving technical content. |
| [file-organizer](./file-organizer/) | Intelligently organize files and folders by context, find duplicates, and suggest better structures. |
| [invoice-organizer](./invoice-organizer/) | Extract information from invoices and receipts, rename consistently, and sort for tax preparation. |
| [raffle-winner-picker](./raffle-winner-picker/) | Fairly pick random winners from lists, spreadsheets, or Google Sheets for giveaways and contests. |

### Security

| Skill | Description |
|-------|-------------|
| [resemble-detect](./resemble-detect/) | Detect deepfakes in audio, image, video, and text. Trace synthesis sources and verify speaker identity. |

---

## Skill Structure

Each skill follows a consistent structure:

```
skill-name/
  SKILL.md          # Required. Core instructions, examples, and metadata.
  scripts/          # Optional. Helper scripts referenced by the skill.
  templates/          # Optional. Reusable templates or fixtures.
  examples/           # Optional. Example inputs/outputs.
```

### Minimal SKILL.md Template

```markdown
---
name: my-skill-name
description: A clear description of what this skill does and when to use it.
---

# My Skill Name

## When to Use

- Use case 1
- Use case 2

## Instructions

[Detailed instructions for LLMs on how to execute this skill]

## Examples

[Real-world examples showing the skill in action]
```

---

## Platform Notes

| Platform | How to Load Skills |
|----------|-------------------|
| **Claude Code** | Place in `.claude/skills/` (project) or `~/.claude/skills/` (user). Discovered automatically. |
| **Claude Desktop** | Upload ZIP via Settings → Capabilities → Skills. |
| **Codex CLI** | Reference `SKILL.md` in prompts or system configuration. |
| **Gemini CLI** | Use `@` to attach `SKILL.md` files to prompts. |
| **OpenCode** | Loads `SKILL.md` files from `~/.config/opencode/skills/*/SKILL.md`, `~/.claude/skills/*/SKILL.md`, and `~/.agents/skills/*/SKILL.md`. This repository already lives at `~/.agents`, so the skills are available there directly. |
| **Qwen Code** | Create `skills/` directory and prompt Qwen Code to follow `SKILL.md` instructions. |

---

## Contributing

This is a personal collection, but improvements are welcome:

1. Ensure the skill solves a real, repeatable problem
2. Follow the existing structure and naming conventions
3. Include a clear `SKILL.md` with examples
4. Test across your target platforms before finalizing

---

## License

This repository is licensed under the Apache License 2.0.

Individual skills may have different licenses — check each skill's folder for specific licensing information.
