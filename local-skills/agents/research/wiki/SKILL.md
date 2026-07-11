---
name: wiki
description: >
  Universal agent skill for managing and querying an Obsidian-compatible,
  Karpathy-style LLM-compiled wiki stored at ~/.llm-wiki/hub. Supports
  ingestion, compilation, query, lint, and ambient recall from topic
  sub-wikis. Activates on any wiki, knowledge-base, ingest, compile, query,
  lint, or long-term memory request, or when the current conversation looks
  like it should read from or write to the configured wiki.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [wiki, llm-wiki, knowledge-base, obsidian, long-term-memory, research]
    category: research
    related_skills: [obsidian, llm-wiki]
---

# Wiki

You manage and query an LLM-compiled, Obsidian-compatible knowledge base stored in
a Git repository at `~/.llm-wiki`.

**Design goal:** this is the long-term memory layer — shared by Hermes, OpenClaw,
OpenCode, Codex, Claude, and the human. Short-term hot memory stays in the
harness's native memory; durable compiled knowledge lives here.

## Canonical paths

- Wiki repository: `~/.llm-wiki`
- Hub (registry of topic wikis): `~/.llm-wiki/hub`
- Hub config (optional): `~/.config/llm-wiki/config.json`
  ```json
  { "hub_path": "~/.llm-wiki/hub" }
  ```
- Topic wikis: `~/.llm-wiki/hub/topics/<slug>/`
- Default topic for this profile: `dotfiles`

Always resolve the hub path by reading `~/.config/llm-wiki/config.json` first.
If it is missing or has no `hub_path`, fall back to `~/.llm-wiki/hub`.

## Topic wiki layout

```
~/.llm-wiki/hub/topics/<slug>/
├── _index.md                 # Master index
├── config.md                 # Title, scope, conventions
├── schema.md                 # Topic-local conventions
├── log.md                    # Append-only activity log
├── inbox/                    # Human quick-capture drop zone
├── raw/                      # Immutable sources
│   ├── _index.md
│   ├── articles/
│   ├── papers/
│   ├── repos/
│   ├── notes/
│   └── data/
├── wiki/                     # Compiled articles
│   ├── _index.md
│   ├── concepts/
│   ├── topics/
│   ├── references/
│   └── theses/
└── output/                   # Generated artifacts
    └── _index.md
```

## Core principles

1. **Topic isolation.** One domain per topic wiki. The hub only registers topics.
2. **Indexes first.** Read `_index.md` files before scanning full articles.
3. **Raw is immutable.** Once ingested, sources are never edited. Synthesis happens in `wiki/`.
4. **Dual links for Obsidian + agents.** Use `[[slug|Name]] ([Name](../category/slug.md))`.
5. **Frontmatter on every file.** `title`, `summary`, `type`, `tags`, `created`, `updated`, `sources`.
6. **Append-only logs.** Every mutating operation logs one line.
7. **Honest gaps.** If the wiki does not have the answer, say so.

## Ambient behavior

When this skill is loaded, any user request that might be answered by the wiki
should trigger a lightweight check:

1. Resolve HUB.
2. If `HUB/_index.md` exists, read it.
3. If the request matches a known topic or the default topic (`dotfiles`), read
   that topic's `_index.md`.
4. If relevant articles exist, read them and answer with citations.
5. If nothing relevant exists, answer normally and optionally suggest:
   "This could be added to the dotfiles wiki — say `/wiki remember` or `/wiki ingest <url>`."

Do not dump index contents unless asked. Cite exact file paths for claims drawn
from the wiki.

## Commands (natural-language aliases)

| Intent | Example invocation |
|---|---|
| Initialize topic | `/wiki init <slug>` or "init a wiki for X" |
| Ingest | `/wiki ingest <url/file/text>` or "add this to the wiki" |
| Compile | `/wiki compile` or "compile uncompiled sources" |
| Query | `/wiki query <question>` or "what does the wiki say about X" |
| Search | `/wiki search <terms>` or "search wiki for X" |
| Remember | `/wiki remember [topic]` — capture a durable note from the current turn |
| Lint | `/wiki lint` or "lint the wiki" |
| Status | `/wiki status` or "show wiki status" |
| Help | `/wiki help` or "what can the wiki do?" |

When the user says `/wiki ...`, treat it as a shorthand for the equivalent
natural-language request. The skill has no actual slash command — it is invoked
by the harness skill system when the request matches the description, or by
the agent noticing a wiki-relevant request.

In Hermes, invoke the skill with the registered name `wiki`, e.g.
`/wiki help`, `/wiki query ...`, `/wiki ingest ...`.

## Help workflow

When the user asks for help on the wiki (e.g. `/wiki help`, `/wiki help`,
"what can the wiki do?", or "how do I use the wiki?"), respond with a concise
reference card:

```markdown
# LLM Wiki — quick reference

Repo: ~/.llm-wiki  |  Hub: ~/.llm-wiki/hub  |  Default topic: dotfiles

Commands (use `/wiki <cmd>` in Hermes, or `/wiki <cmd>` as alias):

| Command | Purpose |
|---|---|
| help | This reference |
| status | Active topics and stats |
| init <slug> | Create a new topic wiki |
| ingest <url/file/text> | Save a source to raw/ |
| compile | Turn uncompiled sources into wiki articles |
| query <question> | Answer from the wiki |
| search <terms> | Search the topic wiki |
| remember [topic] | Capture a durable note from the current turn |
| lint | Rebuild indexes, list orphans/broken links |

Ambient behavior: I read wiki indexes before answering domain questions and
suggest adding durable knowledge when relevant.
```

Keep the help response under ~600 tokens. Do not perform any other wiki operation
unless the user explicitly asks for one.

## Ingestion workflow

1. Resolve source: URL → use `web_extract` or equivalent; file → read; pasted text → save as note.
2. Write source into `raw/<type>/` with frontmatter including `source_url` and `ingested` date.
3. Add source to `raw/_index.md`.
4. Append to `log.md`: `## [YYYY-MM-DD] ingest | <source-title>`.
5. If 3+ uncompiled sources exist, suggest running `/wiki compile`.

## Compilation workflow

1. List uncompiled sources by comparing `raw/_index.md` entries to `wiki/` update dates.
2. For each source or batch, plan required articles: concept, topic, reference, entity.
3. Write or update `wiki/` articles with synthesized content, dual-links, and frontmatter.
4. Update all `_index.md` files affected.
5. Append to `log.md`.

## Query workflow

1. Read topic `_index.md`.
2. Read relevant branch index (`wiki/_index.md`, `raw/_index.md`, etc.).
3. Read matched articles.
4. If indexes are insufficient, search the topic wiki for key terms.
5. Synthesize and cite exact file paths.

## Lint workflow

Run a lightweight structural check:

1. Verify required directories exist (`raw/`, `wiki/`, `output/`).
2. Rebuild stale indexes by comparing file counts to table rows.
3. List orphan pages (not in any `_index.md`).
4. List broken wikilinks.
5. Append summary to `log.md`.

## Dual-link format

Always use both Obsidian wikilink and markdown relative link on the same line:

```markdown
See [[nix-darwin|nix-darwin]] ([nix-darwin](../concepts/nix-darwin.md)) for details.
```

## Frontmatter template

```yaml
---
title: Page Title
summary: One-sentence summary
type: concept | topic | reference | entity | source | note | output
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [raw/articles/source-name.md]
confidence: high | medium | low
---
```

## Human collaboration

The user may edit any wiki file directly in Obsidian or any editor. Treat manual
edits as authoritative. On the next query or lint, detect staleness and rebuild
indexes from the actual files.

## Safety

- Never recursively delete wiki files.
- Never modify `raw/` sources after ingest.
- Never merge unrelated topics.
- Keep large writes chunked (under ~200 lines per file operation).
