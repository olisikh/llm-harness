---
name: hermes-agent
description: "Configure, extend, or contribute to Hermes Agent."
version: 2.0.0
author: Hermes Agent + Teknium
license: MIT
metadata:
  hermes:
    tags: [hermes, setup, configuration, multi-agent, spawning, cli, gateway, development]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [claude-code, codex, opencode, openclaw-ops]
---

# Hermes Agent

Hermes Agent is an open-source AI agent framework by Nous Research that runs in your terminal, messaging platforms, and IDEs. It belongs to the same category as Claude Code (Anthropic), Codex (OpenAI), and OpenClaw — autonomous coding and task-execution agents that use tool calling to interact with your system. Hermes works with any LLM provider (OpenRouter, Anthropic, OpenAI, DeepSeek, local models, and 15+ others) and runs on Linux, macOS, and WSL.

What makes Hermes different:

- **Self-improving through skills** — Hermes learns from experience by saving reusable procedures as skills. When it solves a complex problem, discovers a workflow, or gets corrected, it can persist that knowledge as a skill document that loads into future sessions. Skills accumulate over time, making the agent better at your specific tasks and environment.
- **Persistent memory across sessions** — remembers who you are, your preferences, environment details, and lessons learned. Pluggable memory backends (built-in, Honcho, Mem0, and more) let you choose how memory works.
- **Multi-platform gateway** — the same agent runs on Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Email, and 10+ other platforms with full tool access, not just chat.
- **Provider-agnostic** — swap models and providers mid-workflow without changing anything else. Credential pools rotate across multiple API keys automatically.
- **Profiles** — run multiple independent Hermes instances with isolated configs, sessions, skills, and memory.
- **Extensible** — plugins, MCP servers, custom tools, webhook triggers, cron scheduling, and the full Python ecosystem.

People use Hermes for software development, research, system administration, data analysis, content creation, home automation, and anything else that benefits from an AI agent with persistent context and full system access.

**This skill helps you work with Hermes Agent effectively** — setting it up, configuring features, spawning additional agent instances, troubleshooting issues, finding the right commands and settings, and understanding how the system works when you need to extend or contribute to it.

**Docs:** https://hermes-agent.nousresearch.com/docs/

## Quick Start

```bash
# Install
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# Interactive chat (default)
hermes

# Single query
hermes chat -q "What is the capital of France?"

# Setup wizard
hermes setup

# Change model/provider
hermes model

# Check health
hermes doctor
```

---

## CLI Reference

### Global Flags

```
hermes [flags] [command]

  --version, -V             Show version
  --resume, -r SESSION      Resume session by ID or title
  --continue, -c [NAME]     Resume by name, or most recent session
  --worktree, -w            Isolated git worktree mode (parallel agents)
  --skills, -s SKILL        Preload skills (comma-separate or repeat)
  --profile, -p NAME        Use a named profile
  --yolo                    Skip dangerous command approval
  --pass-session-id         Include session ID in system prompt
```

No subcommand defaults to `chat`.

### Chat

```
hermes chat [flags]
  -q, --query TEXT          Single query, non-interactive
  -m, --model MODEL         Model (e.g. anthropic/claude-sonnet-4)
  -t, --toolsets LIST       Comma-separated toolsets
  --provider PROVIDER       Force provider (openrouter, anthropic, nous, etc.)
  -v, --verbose             Verbose output
  -Q, --quiet               Suppress banner, spinner, tool previews
  --checkpoints             Enable filesystem checkpoints (/rollback)
  --source TAG              Session source tag (default: cli)
```

### Configuration

```
hermes setup [section]      Interactive wizard (model|terminal|gateway|tools|agent)
hermes model                Interactive model/provider picker
hermes config               View current config
hermes config edit          Open config.yaml in $EDITOR
hermes config set KEY VAL   Set a config value
hermes config path          Print config.yaml path
hermes config env-path      Print .env path
hermes config check         Check for missing/outdated config
hermes config migrate       Update config with new options
hermes login [--provider P] OAuth login (nous, openai-codex)
hermes logout               Clear stored auth
hermes doctor [--fix]       Check dependencies and config
hermes status [--all]       Show component status
```

### Tools & Skills

```
hermes tools                Interactive tool enable/disable (curses UI)
hermes tools list           Show all tools and status
hermes tools enable NAME    Enable a toolset
hermes tools disable NAME   Disable a toolset

hermes skills list          List installed skills
hermes skills search QUERY  Search the skills hub
hermes skills install ID    Install a skill (ID can be a hub identifier OR a direct https://…/SKILL.md URL; pass --name to override when frontmatter has no name)
hermes skills inspect ID    Preview without installing
hermes skills config        Enable/disable skills per platform
hermes skills check         Check for updates
hermes skills update        Update outdated skills
hermes skills uninstall N   Remove a hub skill
hermes skills publish PATH  Publish to registry
hermes skills browse        Browse all available skills
hermes skills tap add REPO  Add a GitHub repo as skill source
```

### MCP Servers

```
hermes mcp serve            Run Hermes as an MCP server
hermes mcp add NAME         Add an MCP server (--url or --command)
hermes mcp remove NAME      Remove an MCP server
hermes mcp list             List configured servers
hermes mcp test NAME        Test connection
hermes mcp configure NAME   Toggle tool selection
```

MCP servers can be added/removed at runtime by editing `mcp_servers` and running `/reload-mcp` in the active session/gateway. This reconnects servers and refreshes the session tool list, but it invalidates provider prompt cache because tool schemas changed; the next turn resends full static context. Use this for on-demand heavy MCPs such as Peekaboo, but prefer lean default Telegram/control-room toolsets when cost/context matters.

### Gateway (Messaging Platforms)

```
hermes gateway run          Start gateway foreground
hermes gateway install      Install as background service
hermes gateway start/stop   Control the service
hermes gateway restart      Restart the service
hermes gateway status       Check status
hermes gateway setup        Configure platforms
```

Supported platforms: Telegram, Discord, Slack, WhatsApp, Signal, Email, SMS, Matrix, Mattermost, Home Assistant, DingTalk, Feishu, WeCom, BlueBubbles (iMessage), Weixin (WeChat), API Server, Webhooks. Open WebUI connects via the API Server adapter.

Platform docs: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/

**Restricting gateway access by user ID:**  
Hermes supports per-platform allowlists so the bot ignores messages from unauthorized users. These are stored in `~/.hermes/.env` and set during `hermes gateway setup`:

| Platform | Env var | Example value |
|----------|---------|---------------|
| Telegram | `TELEGRAM_ALLOWED_USERS` | `3942079` or `3942079,1234567` |
| Discord | `DISCORD_ALLOWED_USERS` | `user-id-1,user-id-2` |
| Slack | `SLACK_ALLOWED_USERS` | `U12345678,U87654321` |
| Matrix | `MATRIX_ALLOWED_USERS` | `@alice:server,@bob:server` |

If the env var is set, the platform adapter silently drops messages from anyone not on the list before they reach the agent. If it is absent or empty, the bot is open-access. Check `~/.hermes/.env` to verify or change the allowed list.

### Sessions

```
hermes sessions list        List recent sessions
hermes sessions browse      Interactive picker
hermes sessions export OUT  Export to JSONL
hermes sessions rename ID T Rename a session
hermes sessions delete ID   Delete a session
hermes sessions prune       Clean up old sessions (--older-than N days)
hermes sessions stats       Session store statistics
```

### Cron Jobs

```
hermes cron list            List jobs (--all for disabled)
hermes cron create SCHED    Create: '30m', 'every 2h', '0 9 * * *'
hermes cron edit ID         Edit schedule, prompt, delivery
hermes cron pause/resume ID Control job state
hermes cron run ID          Trigger on next tick
hermes cron remove ID       Delete a job
hermes cron status          Scheduler status
```

When taking over scheduled work from OpenClaw, inspect OpenClaw's `~/.openclaw/cron/jobs.json` plus `jobs-state.json`, recreate active jobs in Hermes with copied delivery targets, then disable the old OpenClaw jobs to avoid double-posting. See `references/openclaw-cron-takeover.md` for the concrete migration/verification checklist and pitfalls.

When taking over OpenClaw "projects" or topic memories, do **not** assume the user means cron jobs or SQLite task-run records. Check `~/.openclaw/workspace/memory/projects/*.md` first and import useful files to `~/.hermes/memories/projects/`; for example, Oleksii's jogging log lived at `~/.openclaw/workspace/memory/projects/run.md`. See `references/openclaw-project-memory-takeover.md` for the discovery/import checklist and pitfalls.

For updating an OpenClaw installation that was built from source (`~/openclaw`), the committed `dist/` folder can be stale after a git checkout, and the LaunchAgent plist may have a hardcoded `OPENCLAW_SERVICE_VERSION`. See `references/openclaw-source-update.md` for the rebuild-and-reload checklist.

For non-interactive OpenClaw repairs, prefer `openclaw doctor --repair --non-interactive` for safe fixes without prompts. `--fix` is an alias for `--repair`, `--lint` is read-only, and `openclaw status` is the post-repair verification step. See `references/openclaw-doctor-noninteractive.md` for the exact flow and auth-inspection commands.

For scheduled scouting/planning jobs that should write to Apple Calendar, keep calendar write logic in a narrow `$HERMES_HOME/scripts/` helper, give the cron job `file + terminal` tools, make writes idempotent, back up Calendar data before edits, and require a delivered `Calendar: created/skipped` count. See `references/cron-calendar-integration.md` for the concrete pattern and Oleksii's `Hermes Events` setup.

### Webhooks

```
hermes webhook subscribe N  Create route at /webhooks/<name>
hermes webhook list         List subscriptions
hermes webhook remove NAME  Remove a subscription
hermes webhook test NAME    Send a test POST
```

### Profiles

```
hermes profile list         List all profiles
hermes profile create NAME  Create (--clone, --clone-all, --clone-from)
hermes profile use NAME     Set sticky default
hermes profile delete NAME  Delete a profile
hermes profile show NAME    Show details
hermes profile alias NAME   Manage wrapper scripts
hermes profile rename A B   Rename a profile
hermes profile export NAME  Export to tar.gz
hermes profile import FILE  Import from archive
```

### Credential Pools

```
hermes auth add             Interactive credential wizard
hermes auth list [PROVIDER] List pooled credentials
hermes auth remove P INDEX  Remove by provider + index
hermes auth reset PROVIDER  Clear exhaustion status
```

### Other

```
hermes insights [--days N]  Usage analytics
hermes update               Update to latest version
hermes pairing list/approve/revoke  DM authorization
hermes plugins list/install/remove  Plugin management
hermes honcho setup/status  Honcho memory integration (requires honcho plugin)
hermes memory setup/status/off  Memory provider config
hermes completion bash|zsh  Shell completions
hermes acp                  ACP server (IDE integration)
hermes claw migrate         Migrate from OpenClaw
hermes uninstall            Uninstall Hermes
```

---

## Slash Commands (In-Session)

Type these during an interactive chat session.

### Session Control
```
/new (/reset)        Fresh session
/clear               Clear screen + new session (CLI)
/retry               Resend last message
/undo                Remove last exchange
/title [name]        Name the session
/compress            Manually compress context
/stop                Kill background processes
/rollback [N]        Restore filesystem checkpoint
/background <prompt> Run prompt in background
/queue <prompt>      Queue for next turn
/resume [name]       Resume a named session
```

### Configuration
```
/config              Show config (CLI)
/model [name]        Show or change model
/personality [name]  Set personality
/reasoning [level]   Set reasoning (none|minimal|low|medium|high|xhigh|show|hide)
/verbose             Cycle: off → new → all → verbose
/voice [on|off|tts]  Voice mode
/yolo                Toggle approval bypass
/skin [name]         Change theme (CLI)
/statusbar           Toggle status bar (CLI)
```

### Tools & Skills
```
/tools               Manage tools (CLI)
/toolsets            List toolsets (CLI)
/skills              Search/install skills (CLI)
/skill <name>        Load a skill into session
/cron                Manage cron jobs (CLI)
/reload-mcp          Reload MCP servers
/plugins             List plugins (CLI)
```

### Gateway
```
/approve             Approve a pending command (gateway)
/deny                Deny a pending command (gateway)
/restart             Restart gateway (gateway)
/sethome             Set current chat as home channel (gateway)
/update              Update Hermes to latest (gateway)
/platforms (/gateway) Show platform connection status (gateway)
```

### Utility
```
/branch (/fork)      Branch the current session
/fast                Toggle priority/fast processing
/browser             Open CDP browser connection
/history             Show conversation history (CLI)
/save                Save conversation to file (CLI)
/paste               Attach clipboard image (CLI)
/image               Attach local image file (CLI)
```

### Info
```
/help                Show commands
/commands [page]     Browse all commands (gateway)
/usage               Token usage
/insights [days]     Usage analytics
/status              Session info (gateway)
/profile             Active profile info
```

### Exit
```
/quit (/exit, /q)    Exit CLI
```

---

## Key Paths & Config

```
~/.hermes/config.yaml       Main configuration
~/.hermes/.env              API keys and secrets
$HERMES_HOME/skills/        Installed runtime skills (on Oleksii's setup, durable physical skill sources live under ~/llm-harness/harness/<harness>/skills and install into harness homes such as ~/.agents/skills and ~/.hermes/skills)
See `references/shared-skills-repo.md` for the canonical layout and symlink rule.
~/.hermes/sessions/         Session transcripts
~/.hermes/logs/             Gateway and error logs
~/.hermes/auth.json         OAuth tokens and credential pools
~/.hermes/hermes-agent/     Source code (if git-installed)
```

Profiles use `~/.hermes/profiles/<name>/` with the same layout.

### Backing Up Hermes State with Git

Use this when the user asks to back up, version, sync, or push Hermes state/config/skills to a private Git repository. The class of task is: **create a safe, private Git backup for durable agent state while excluding secrets, sessions, logs, and runtime databases.**

Recommended local repo root is `$HERMES_HOME` (usually `~/.hermes`). Prefer a deny-by-default `.gitignore`: ignore `*`, then explicitly allow durable state such as `config.yaml`, `SOUL.md`, `skills/**`, `memories/**`, `profiles/**`, `scripts/**`, and selected cron job definition files. Always exclude:

```gitignore
.env
.env.*
auth.json
**/auth.json
sessions/
logs/
sandboxes/
state.db
state.db-*
*.db
*.sqlite*
*.lock
*.pid
*.sock
*.log
.hermes_history
.update_check
.skills_prompt_snapshot.json
context_length_cache.yaml
models_dev_cache.json
channel_directory.json
gateway_state.json
migration/
bin/
platforms/
*token*.json
*credential*.json
*secret*.json
*secrets*.json
*.key
*.pem
```

Before committing, verify:

```bash
cd "${HERMES_HOME:-$HOME/.hermes}"
git diff --cached --name-only | grep -E '(^|/)(\.env(\.|$)|auth\.json$|sessions/|logs/|state\.db|.*\.key$|.*\.pem$|.*\.token$|.*credentials.*\.json$|.*secrets?.*\.json$)' || true
git diff --cached --name-only -z | xargs -0 grep -nE --binary-files=without-match 'AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{30,}|sk-ant-[A-Za-z0-9_-]{32,}|sk-[A-Za-z0-9_-]{32,}|xox[baprs]-[A-Za-z0-9-]{20,}|BEGIN (RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY' || true
```

If either check returns real findings, unstage/remove those files before committing. Use Conventional Commits, e.g. `chore(hermes): initial state backup`. Do not push until the remote is confirmed private. For full disaster recovery including `.env`, `auth.json`, `sessions/`, or logs, recommend a separate encrypted backup tool (`restic`, `borg`, `age`, `sops`, or `git-crypt`) instead of plaintext Git.

For always-on sync, add a conservative backup script under `$HERMES_HOME/scripts/backup-hermes-state.sh` that:

1. Acquires a simple lock dir to prevent overlapping runs.
2. Runs `git pull --rebase --autostash origin main` if a remote exists.
3. Stages only the allowlisted durable paths.
4. Re-runs the forbidden-path check above before committing.
5. Commits only when `git diff --cached` is non-empty.
6. Pushes if `origin` exists.

On macOS, prefer a per-user LaunchAgent instead of cron:

```bash
mkdir -p ~/Library/LaunchAgents "$HERMES_HOME/logs"
plutil -lint ~/Library/LaunchAgents/com.$USER.hermes-state-backup.plist
launchctl bootout "gui/$(id -u)/com.$USER.hermes-state-backup" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.$USER.hermes-state-backup.plist
launchctl enable "gui/$(id -u)/com.$USER.hermes-state-backup"
launchctl kickstart -k "gui/$(id -u)/com.$USER.hermes-state-backup"
launchctl print "gui/$(id -u)/com.$USER.hermes-state-backup" | grep -E 'state =|runs =|last exit code|run interval'
```

Use `StartInterval` around `1800` seconds for a practical default. Put stdout/stderr logs under `$HERMES_HOME/logs/`. Verify with a real run: clean `git status --short --branch`, `origin/main` at `HEAD`, and LaunchAgent `last exit code = 0`.

### Feature Completeness Audit

Use this when the user asks "what am I missing?", "how do I get the full experience?", or is migrating from another agent (OpenClaw, Claude Code, Codex) and wants to know which Hermes capabilities are not yet configured. The class of task is: **systematically audit a Hermes installation for missing high-value features and configure them without exposing secrets.**

Audit checklist (run via Python from the Hermes source venv):

```python
import os, yaml, json, pathlib
home = pathlib.Path(os.getenv('HERMES_HOME', pathlib.Path.home() / '.hermes'))
config = yaml.safe_load((home / 'config.yaml').read_text()) if (home / 'config.yaml').exists() else {}

# Load .env key names only
env_names = set(os.environ)
env_path = home / '.env'
if env_path.exists():
    for line in env_path.read_text(errors='ignore').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k = line.split('=', 1)[0].replace('export ', '').strip()
        if k: env_names.add(k)

summary = {
    'model': {'provider': config.get('model', {}).get('provider'), 'default': config.get('model', {}).get('default')},
    'fallback_count': len(config.get('fallback_providers') or []),
    'memory': config.get('memory', {}),
    'stt': config.get('stt', {}),
    'tts': config.get('tts', {}),
    'web_search_backend': (config.get('web_search') or config.get('search', {})),
    'browser': config.get('browser', {}),
    'auxiliary': config.get('auxiliary', {}),
    'mcp_servers': list(config.get('mcp_servers', {}).keys()) or 'NOT SET',
    'approvals': config.get('approvals', {}),
    'checkpoints': config.get('checkpoints', {}),
    'gateway_platforms': [k for k, v in (config.get('gateway', {}).get('platforms', {}) or {}).items() if isinstance(v, dict) and v.get('enabled')],
    'env_presence': {k: k in env_names for k in ['GOOGLE_API_KEY', 'GEMINI_API_KEY', 'OPENROUTER_API_KEY', 'TAVILY_API_KEY', 'BRAVE_API_KEY', 'FIRECRAWL_API_KEY', 'EXA_API_KEY', 'ANTHROPIC_API_KEY', 'GITHUB_PERSONAL_ACCESS_TOKEN', 'MISTRAL_API_KEY']},
}
print(json.dumps(summary, indent=2, sort_keys=True, default=str))
```

Also verify web backend availability by importing `tools.web_tools._get_backend` and `_is_backend_available` from the Hermes source tree (requires venv activation).

Common gaps and fixes:

| Gap | Why it matters | Fix |
|-----|---------------|-----|
| **No web search backend key** | `web` toolset is enabled but `WEB_BACKEND_AVAILABLE: False` | Add `FIRECRAWL_API_KEY`, `TAVILY_API_KEY`, `EXA_API_KEY`, or `PARALLEL_API_KEY` to `.env` |
| **No Gemini/Google key in Hermes** | Auxiliary tasks (vision, compression, session search) silently fail when `provider: auto` can't find a backend | Add `GOOGLE_API_KEY=...` or `GEMINI_API_KEY=...` to `.env` |
| **No external memory provider** | Only built-in text memory active; no semantic/vector recall | Run `hermes memory setup` and choose mem0, honcho, supermemory, or holographic (local) |
| **No MCP servers** | Missing first-class tools for GitHub, filesystem, databases, etc. | Add to `config.yaml` `mcp_servers:` block; ensure `pip install mcp` in venv |
| **Manual approvals** | Every destructive command prompts | `hermes config set approvals.mode smart` |
| **Missing gateway platforms** | Telegram/Discord/Slack not enabled | `hermes gateway setup` |

Web search backend selection notes (for personal/default setups):

- Gemini/Google API keys are useful for auxiliary LLM work (`web_extract` summarization, vision, compression), but Hermes `web` tools still require a dedicated search/extract backend key. Gemini is not currently a web backend in `tools/web_tools.py`.
- Current Hermes backend compatibility: **Tavily** supports search, extract, and crawl; **Exa** supports search and extract; **Firecrawl** supports search, extract, and crawl; **Parallel** supports search and extract.
- Current Hermes backend selection is single-backend, not true per-query fallback/rotation: `web.backend` in `config.yaml` wins when set; otherwise `_get_backend()` in `tools/web_tools.py` chooses the first available backend in priority order `firecrawl → parallel → tavily → exa` and individual `web_search` calls do not automatically retry a second backend on quota/rate-limit/provider failure. If the user asks for multi-provider free-tier fallback, explain this limitation and propose/implement a code patch rather than assuming config alone can do it.
- Tavily is a strong default first backend for personal use: free tier observed as 1,000 API credits/month, no credit card; basic search costs 1 credit, advanced search 2 credits, basic extract costs 1 credit per 5 successful URL extractions, and crawl costs more because it combines map + extraction. Hermes' Tavily search path uses basic search parameters unless changed. Tavily PAYG was observed at $0.008/credit; remind cost-sensitive users to leave PAYG disabled if they want hard free-tier limits.
- Exa is more semantic/research-search oriented: free tier observed as up to 1,000 requests/month; pricing page listed Search $7/1k requests, Deep Search $12/1k, Contents $1/1k pages, Answer $5/1k. It can be better for conceptually relevant pages, docs, people/company search, and research workflows, but it is not the best first choice if the user wants crawl support in Hermes.
- Caveats to mention before choosing any provider: search queries/URLs go to the provider; extracted content may also go to the configured auxiliary LLM for summarization; free tiers have rate limits; use only legitimate free tiers/API keys, not duplicate-account limit evasion; search/extract APIs are not a full browser and may struggle with JS-heavy sites.

When migrating from OpenClaw, inspect `~/.openclaw/openclaw.json` for:
- `memorySearch.provider` / `memorySearch.model` → map to Hermes memory provider
- `providers.*` API keys → copy relevant ones to `~/.hermes/.env`
- Web search provider config → map to Hermes `FIRECRAWL_API_KEY` / `TAVILY_API_KEY` / etc.

If the user is maintaining an existing source-installed OpenClaw alongside Hermes (not migrating away), load the `openclaw-ops` skill for update, rebuild, and restart workflows.

Never expose secret values in chat. Always write keys to `~/.hermes/.env` via `patch` or `terminal` with redacted output, then verify presence with name-only checks.

If the user manages secrets through external tooling (sops-nix, macOS Keychain, 1Password CLI, Bitwarden, etc.), read from the existing secret file or vault and append to `~/.hermes/.env` without printing the value. Example for sops-nix:

```bash
printf 'GEMINI_API_KEY=' >> ~/.hermes/.env
cat /Users/$USER/.config/sops-nix/secrets/ai/gemini >> ~/.hermes/.env
printf '\n' >> ~/.hermes/.env
```

Verify with a redacted grep: `grep -E '^(GEMINI|FIRECRAWL|TAVILY)_API_KEY=' ~/.hermes/.env | sed 's/=.*/=[REDACTED]/'`

### Config Sections

Edit with `hermes config edit` or `hermes config set section.key value`.

| Section | Key options |
|---------|-------------|
| `model` | `default`, `provider`, `base_url`, `api_key`, `context_length` |
| `agent` | `max_turns` (90), `tool_use_enforcement` |
| `terminal` | `backend` (local/docker/ssh/modal), `cwd`, `timeout` (180) |
| `compression` | `enabled`, `threshold` (0.50), `target_ratio` (0.20) |
| `display` | `skin`, `tool_progress`, `show_reasoning`, `show_cost` |
| `stt` | `enabled`, `provider` (local/groq/openai/mistral) |
| `tts` | `provider` (edge/elevenlabs/openai/minimax/mistral/neutts) |
| `memory` | `memory_enabled`, `user_profile_enabled`, `provider` |
| `security` | `tirith_enabled`, `website_blocklist` |
| `delegation` | `model`, `provider`, `base_url`, `api_key`, `max_iterations` (50), `reasoning_effort` |
| `checkpoints` | `enabled`, `max_snapshots` (50) |

Full config reference: https://hermes-agent.nousresearch.com/docs/user-guide/configuration

### Provider Fallbacks

Use this when the user asks to add a backup/fallback model or provider for Hermes, especially to continue after primary provider rate limits, overload, billing, or connection failures. The class of task is: **configure Hermes' native fallback provider chain while keeping secrets in `.env` and durable routing config in `config.yaml`.**

Hermes stores fallbacks as top-level `fallback_providers` in `~/.hermes/config.yaml`:

```yaml
fallback_providers:
  - provider: opencode-go
    model: kimi-k2.6
    api_mode: chat_completions
    # optional: base_url: https://...
```

Preferred flow:

```bash
hermes config env-path          # locate .env for secrets
hermes fallback list            # inspect current chain
hermes fallback add             # interactive picker; requires a real TTY
```

Secrets belong in `.env`, never `config.yaml` or chat transcripts. For OpenCode Go:

```env
OPENCODE_GO_API_KEY=...
# optional only for custom endpoints:
OPENCODE_GO_BASE_URL=https://...
```

If `hermes fallback add` cannot run because the environment is non-interactive, edit `config.yaml` directly and verify with `hermes fallback list`. Known OpenCode Go setup details:

- Provider id: `opencode-go`
- API key env var: `OPENCODE_GO_API_KEY`
- Optional base URL env var: `OPENCODE_GO_BASE_URL`
- Example coding fallback model: `kimi-k2.6` with `api_mode: chat_completions`
- Other observed examples: `glm-5.1`, `glm-5`, `kimi-k2.5`, `qwen3.6-plus` use `chat_completions`; `minimax-m2.7` uses `anthropic_messages`

After changing provider/fallback config, restart long-running gateway sessions (`/restart` or `hermes gateway restart`). Current `hermes chat --provider …` argparse may not list Hermes-only providers like `opencode-go`, even though runtime config and fallback support them. To smoke-test OpenCode Go directly, use a temporary Hermes home whose primary model is `opencode-go`:

```bash
TMP_HOME="$(mktemp -d /tmp/hermes-opencode-test.XXXXXX)"
cp ~/.hermes/.env "$TMP_HOME/.env"
cat > "$TMP_HOME/config.yaml" <<'YAML'
model:
  provider: opencode-go
  default: kimi-k2.6
  api_mode: chat_completions
agent:
  max_turns: 1
fallback_providers: []
YAML
HERMES_HOME="$TMP_HOME" hermes chat -Q -q "Respond with exactly: OK"
python3 - <<PY
import shutil
shutil.rmtree('$TMP_HOME', ignore_errors=True)
PY
```

To test actual failover without altering the real config, create a temporary Hermes home with an intentionally bad primary and the real fallback chain, then run a one-shot query; success proves the fallback path activates.

If the Hermes state backup workflow is installed, the durable `config.yaml` change will be backed up automatically, but `.env` remains intentionally untracked.

### Providers

20+ providers supported. Set via `hermes model` or `hermes setup`.

For user-facing subscription/value recommendations, see `references/ai-subscription-value-guide.md`.

| Provider | Auth | Key env var |
|----------|------|-------------|
| OpenRouter | API key | `OPENROUTER_API_KEY` |
| Anthropic | API key | `ANTHROPIC_API_KEY` |
| Nous Portal | OAuth | `hermes auth` |
| OpenAI Codex | OAuth | `hermes auth` |
| GitHub Copilot | Token | `COPILOT_GITHUB_TOKEN` |
| Google Gemini | API key | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| DeepSeek | API key | `DEEPSEEK_API_KEY` |
| xAI / Grok | API key | `XAI_API_KEY` |
| Hugging Face | Token | `HF_TOKEN` |
| Z.AI / GLM | API key | `GLM_API_KEY` |
| MiniMax | API key | `MINIMAX_API_KEY` |
| MiniMax CN | API key | `MINIMAX_CN_API_KEY` |
| Kimi / Moonshot | API key | `KIMI_API_KEY` |
| Alibaba / DashScope | API key | `DASHSCOPE_API_KEY` |
| Xiaomi MiMo | API key | `XIAOMI_API_KEY` |
| Kilo Code | API key | `KILOCODE_API_KEY` |
| AI Gateway (Vercel) | API key | `AI_GATEWAY_API_KEY` |
| OpenCode Zen | API key | `OPENCODE_ZEN_API_KEY` |
| OpenCode Go | API key | `OPENCODE_GO_API_KEY` |
| Qwen OAuth | OAuth | `hermes login --provider qwen-oauth` |
| Custom endpoint | Config | `model.base_url` + `model.api_key` in config.yaml |
| GitHub Copilot ACP | External | `COPILOT_CLI_PATH` or Copilot CLI |

Full provider docs: https://hermes-agent.nousresearch.com/docs/integrations/providers

### Toolsets

Enable/disable via `hermes tools` (interactive) or `hermes tools enable/disable NAME`.

| Toolset | What it provides |
|---------|-----------------|
| `web` | Web search and content extraction |
| `browser` | Browser automation (Browserbase, Camofox, or local Chromium) |
| `terminal` | Shell commands and process management |
| `file` | File read/write/search/patch |
| `code_execution` | Sandboxed Python execution |
| `vision` | Image analysis |
| `image_gen` | AI image generation |
| `tts` | Text-to-speech |
| `skills` | Skill browsing and management |
| `memory` | Persistent cross-session memory |
| `session_search` | Search past conversations |
| `delegation` | Subagent task delegation |
| `cronjob` | Scheduled task management |
| `clarify` | Ask user clarifying questions |
| `messaging` | Cross-platform message sending |
| `search` | Web search only (subset of `web`) |
| `todo` | In-session task planning and tracking |
| `rl` | Reinforcement learning tools (off by default) |
| `moa` | Mixture of Agents (off by default) |
| `homeassistant` | Smart home control (off by default) |

Tool changes take effect on `/reset` (new session). They do NOT apply mid-conversation to preserve prompt caching.

### Token / Context Overhead Audit

Use this when the user asks why Hermes uses more tokens than another agent, how much static context it burns, or how to make a gateway profile leaner. The class of task is: **measure and reduce Hermes' static prompt/tool-schema overhead for a specific profile/platform/model.**

Quick measurement from the Hermes source venv (uses the live config and enabled tools; do not print secrets):

```bash
cd ~/hermes-agent
source venv/bin/activate
set -a; [ -f ~/.hermes/.env ] && . ~/.hermes/.env; set +a
python - <<'PY'
from run_agent import AIAgent
import json
try:
    import tiktoken
    enc = tiktoken.get_encoding('o200k_base')
    ntok = lambda s: len(enc.encode(s))
except Exception:
    ntok = lambda s: round(len(s) / 4)
agent = AIAgent(provider='openai-codex', model='gpt-5.5', platform='telegram', quiet_mode=True)
sp = agent._build_system_prompt()
tools_json = json.dumps(agent.tools, separators=(',', ':'), ensure_ascii=False)
print('valid_tools', len(agent.valid_tool_names))
print('system_chars', len(sp), 'system_tokens_est', ntok(sp))
print('tools_tokens_est', ntok(tools_json))
print('combined_static_tokens_est', ntok(sp) + ntok(tools_json))
for tok, name in sorted((ntok(json.dumps(t, separators=(',', ':'), ensure_ascii=False)), t.get('function', {}).get('name') or t.get('name')) for t in agent.tools)[-15:][::-1]:
    print(tok, name)
PY
```

Observed on Oleksii's Telegram/control-room profile in Apr 2026: 87 tools, ~5.2k system-prompt tokens, ~19.7k tool-schema tokens, ~24.9k combined static tokens. Largest schemas were `delegate_task`, `cronjob`, `terminal`, `skill_manage`, `execute_code`, `session_search`, `memory`, `fact_store`, `search_files`, and GitHub/MCP review tools. A comparable OpenClaw full prompt estimate was ~3k system tokens plus lower tool overhead, so Hermes was roughly ~2× heavier in that rich-tool setup.

Recommendations for reducing cost/context:

- Treat Telegram DM as a control room: keep only high-value always-on toolsets (`web`, `terminal`, `file`, `code_execution`, `memory`, `session_search`, `skills`, `delegation`, `cronjob`, `messaging`, maybe `clarify`) and disable broad browser/vision/image-gen/TTS/todo unless needed.
- Disable MCP on high-traffic platforms when not needed. MCP servers such as GitHub/filesystem can add many tool schemas. Hermes supports a per-platform `no_mcp` sentinel in `platform_toolsets` to prevent globally enabled MCP servers from loading there, e.g.:

```yaml
platform_toolsets:
  telegram:
    - web
    - terminal
    - file
    - code_execution
    - memory
    - session_search
    - skills
    - delegation
    - cronjob
    - messaging
    - clarify
    - no_mcp
```

  Tool changes take effect only on a fresh session (`/reset`) or gateway restart. Preserve MCP on CLI/project profiles if useful; avoid globally removing servers just to slim Telegram.
- Route implementation work to topic-specific sessions/subagents with scoped tools rather than one giant gateway context.
- Use prompt caching where available, but remember cached static tokens still consume context window and cache misses/new sessions still pay the full overhead.
- For exact comparisons, measure both agents on the same platform/model/tool profile; otherwise give a range and label estimates.

---

## Security & Privacy Toggles

Common "why is Hermes doing X to my output / tool calls / commands?" toggles — and the exact commands to change them. Most of these need a fresh session (`/reset` in chat, or start a new `hermes` invocation) because they're read once at startup.

### Secret redaction in tool output

Hermes auto-redacts strings that look like API keys, tokens, and secrets in all tool output (terminal stdout, `read_file`, web content, subagent summaries, etc.) so the model never sees raw credentials. If the user is intentionally working with mock tokens, share-management tokens, or their own secrets and the redaction is getting in the way:

```bash
hermes config set security.redact_secrets false      # disable globally
```

**Restart required.** `security.redact_secrets` is snapshotted at import time — setting it mid-session (e.g. via `export HERMES_REDACT_SECRETS=false` from a tool call) will NOT take effect for the running process. Tell the user to run `hermes config set security.redact_secrets false` in a terminal, then start a new session. This is deliberate — it prevents an LLM from turning off redaction on itself mid-task.

Re-enable with:
```bash
hermes config set security.redact_secrets true
```

### PII redaction in gateway messages

Separate from secret redaction. When enabled, the gateway hashes user IDs and strips phone numbers from the session context before it reaches the model:

```bash
hermes config set privacy.redact_pii true    # enable
hermes config set privacy.redact_pii false   # disable (default)
```

### Command approval prompts

By default (`approvals.mode: manual`), Hermes prompts the user before running shell commands flagged as destructive (`rm -rf`, `git reset --hard`, etc.). The modes are:

- `manual` — always prompt (default)
- `smart` — use an auxiliary LLM to auto-approve low-risk commands, prompt on high-risk
- `off` — skip all approval prompts (equivalent to `--yolo`)

```bash
hermes config set approvals.mode smart       # recommended middle ground
hermes config set approvals.mode off         # bypass everything (not recommended)
```

Per-invocation bypass without changing config:
- `hermes --yolo …`
- `export HERMES_YOLO_MODE=1`

Note: YOLO / `approvals.mode: off` does NOT turn off secret redaction. They are independent.

### Shell hooks allowlist

Some shell-hook integrations require explicit allowlisting before they fire. Managed via `~/.hermes/shell-hooks-allowlist.json` — prompted interactively the first time a hook wants to run.

### Disabling the web/browser/image-gen tools

To keep the model away from network or media tools entirely, open `hermes tools` and toggle per-platform. Takes effect on next session (`/reset`). See the Tools & Skills section above.

---

## Voice & Transcription

### STT (Voice → Text)

Voice messages from messaging platforms are auto-transcribed.

Provider priority (auto-detected):
1. **Local faster-whisper** — free, no API key: `pip install faster-whisper`
2. **Groq Whisper** — free tier: set `GROQ_API_KEY`
3. **OpenAI Whisper** — paid: set `VOICE_TOOLS_OPENAI_KEY`
4. **Mistral Voxtral** — set `MISTRAL_API_KEY`

Config:
```yaml
stt:
  enabled: true
  provider: local        # local, groq, openai, mistral
  local:
    model: base          # tiny, base, small, medium, large-v3
```

### TTS (Text → Voice)

| Provider | Env var | Free? |
|----------|---------|-------|
| Edge TTS | None | Yes (default) |
| ElevenLabs | `ELEVENLABS_API_KEY` | Free tier |
| OpenAI | `VOICE_TOOLS_OPENAI_KEY` | Paid |
| MiniMax | `MINIMAX_API_KEY` | Paid |
| Mistral (Voxtral) | `MISTRAL_API_KEY` | Paid |
| NeuTTS (local) | None (`pip install neutts[all]` + `espeak-ng`) | Free |

Voice commands:
- `/voice on` — voice replies only when the user sends a voice message.
- `/voice tts` — voice replies for all messages in the current chat.
- `/voice off` — text-only replies.
- `/voice status` — show the current mode.

Gateway voice mode is persisted per chat in `$HERMES_HOME/gateway_voice_mode.json` with platform-prefixed keys, for example:

```json
{
  "telegram:123456": "all"
}
```

Valid persisted modes are `off`, `voice_only`, and `all`. If changing this file directly, restart the gateway or use `/voice tts` in the chat so the running adapter updates in memory. Do not commit this file to the Hermes state backup repo unless intentionally tracking per-chat runtime preferences; it is runtime-ish state and is usually ignored.

For Microsoft-style free TTS, use Edge TTS:

```yaml
tts:
  provider: edge
  edge:
    voice: en-US-JennyNeural
```

For non-English text, set an Edge voice matching the message language before generating voice. In particular, Ukrainian text should not be read with the English default; use one of:

```bash
# Ukrainian Edge voices observed available via edge_tts:
# uk-UA-OstapNeural  (male)
# uk-UA-PolinaNeural (female)
hermes config set tts.edge.voice uk-UA-OstapNeural
```

Hermes currently uses one global TTS provider/voice from `tts.provider` and the provider block; it does **not** have native per-language voice routing. When the user asks for language-based orchestration, explain that limitation and offer one of two practical paths:

- Quick path: choose a genuinely multilingual provider/voice (ElevenLabs multilingual, Gemini TTS, Mistral Voxtral, etc.). This avoids per-message config churn but may not preserve per-language voice identity.
- Robust path: define a custom `tts.providers.<name>` command provider that detects the dominant language, selects the appropriate underlying voice (e.g. `uk-UA-OstapNeural` for Ukrainian, `en-US-JennyNeural`/`en-US-AriaNeural` for English), writes audio to `{output_path}`, and sets `voice_compatible: true`. This works with gateway auto-TTS because Hermes just calls the configured command provider. For mixed-language messages, a future native implementation should split by sentence and stitch audio segments.

If implementing native Hermes support, target a config shape like `tts.language_routing.enabled`, `default_language`, and `languages.<code>.provider/voice`, then route inside `tools/tts_tool.py` before provider dispatch. Keep prompt caching stable: routing must happen in tool execution/config, not by changing tool schemas or system prompt mid-session.

If the user complains that TTS sounds wrong for Ukrainian, immediately switch `tts.edge.voice` to a `uk-UA-*Neural` voice, regenerate the audio, and mention the correction briefly. Restart the gateway only if automatic gateway voice replies need the new config; direct `text_to_speech` tool calls can be smoke-tested immediately.

**Language-based TTS routing:** As of the observed source tree in May 2026, Hermes' built-in `text_to_speech` tool reads a single global `tts.provider` / provider voice from `config.yaml`; there is no native `tts.language_routing` section. If the user asks for per-language orchestration, do not claim it exists. Practical options are:

1. Use a multilingual provider/voice (ElevenLabs multilingual, Gemini TTS, Mistral Voxtral, etc.).
2. Configure a custom command-type TTS provider as a local router: detect dominant language, dispatch to Edge/Piper/etc. with the matching voice, write the audio file, and opt into `voice_compatible: true` for Telegram.
3. For a real Hermes feature, implement native language routing in `tools/tts_tool.py`: detect language before dispatch, override provider voice for whole-message routing, and eventually split mixed-language messages by sentence and concatenate audio.

A quick tool-level smoke test is to call the `text_to_speech` tool with a short phrase; it should return an `.ogg` file plus `[[audio_as_voice]]` / `MEDIA:` tags that Telegram can deliver as a voice bubble. When running Hermes source-tree Python checks from a shell, activate the Hermes venv first (`cd ~/hermes-agent && source venv/bin/activate`) because a plain login shell may not have `hermes` or Python packages like `edge_tts` on PATH.

1. Use a multilingual provider/voice (ElevenLabs multilingual, Gemini TTS, Mistral Voxtral) when one voice is acceptable across languages.
2. For Edge per-language voices, implement a custom command TTS provider that detects dominant language, selects the matching Edge voice, writes audio to `{output_path}`, and set `voice_compatible: true` for Telegram voice bubbles. This works with gateway auto-TTS because Hermes only sees a single configured command provider.
3. For a proper upstream feature, add native language routing before provider dispatch, e.g. `tts.language_routing.enabled`, `default_language`, and `languages.<code>.provider/voice`; for mixed-language messages, split by sentence and stitch generated audio segments.

A quick tool-level smoke test is to call the `text_to_speech` tool with a short phrase; it should return an `.ogg` file plus `[[audio_as_voice]]` / `MEDIA:` tags that Telegram can deliver as a voice bubble. When running Hermes source-tree Python checks from a shell, activate the Hermes venv first (`cd ~/hermes-agent && source venv/bin/activate`) because a plain login shell may not have `hermes` or Python packages like `edge_tts` on PATH.

---

## Spawning Additional Hermes Instances

Run additional Hermes processes as fully independent subprocesses — separate sessions, tools, and environments.

### When to Use This vs delegate_task

| | `delegate_task` | Spawning `hermes` process |
|-|-----------------|--------------------------|
| Isolation | Separate conversation, shared process | Fully independent process |
| Duration | Minutes (bounded by parent loop) | Hours/days |
| Tool access | Subset of parent's tools | Full tool access |
| Interactive | No | Yes (PTY mode) |
| Use case | Quick parallel subtasks | Long autonomous missions |

### One-Shot Mode

```
terminal(command="hermes chat -q 'Research GRPO papers and write summary to ~/research/grpo.md'", timeout=300)

# Background for long tasks:
terminal(command="hermes chat -q 'Set up CI/CD for ~/myapp'", background=true)
```

### Interactive PTY Mode (via tmux)

Hermes uses prompt_toolkit, which requires a real terminal. Use tmux for interactive spawning:

```
# Start
terminal(command="tmux new-session -d -s agent1 -x 120 -y 40 'hermes'", timeout=10)

# Wait for startup, then send a message
terminal(command="sleep 8 && tmux send-keys -t agent1 'Build a FastAPI auth service' Enter", timeout=15)

# Read output
terminal(command="sleep 20 && tmux capture-pane -t agent1 -p", timeout=5)

# Send follow-up
terminal(command="tmux send-keys -t agent1 'Add rate limiting middleware' Enter", timeout=5)

# Exit
terminal(command="tmux send-keys -t agent1 '/exit' Enter && sleep 2 && tmux kill-session -t agent1", timeout=10)
```

### Multi-Agent Coordination

```
# Agent A: backend
terminal(command="tmux new-session -d -s backend -x 120 -y 40 'hermes -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t backend 'Build REST API for user management' Enter", timeout=15)

# Agent B: frontend
terminal(command="tmux new-session -d -s frontend -x 120 -y 40 'hermes -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t frontend 'Build React dashboard for user management' Enter", timeout=15)

# Check progress, relay context between them
terminal(command="tmux capture-pane -t backend -p | tail -30", timeout=5)
terminal(command="tmux send-keys -t frontend 'Here is the API schema from the backend agent: ...' Enter", timeout=5)
```

### Session Resume

```
# Resume most recent session
terminal(command="tmux new-session -d -s resumed 'hermes --continue'", timeout=10)

# Resume specific session
terminal(command="tmux new-session -d -s resumed 'hermes --resume 20260225_143052_a1b2c3'", timeout=10)
```

### Tips

- **Prefer `delegate_task` for quick subtasks** — less overhead than spawning a full process
- **Use `-w` (worktree mode)** when spawning agents that edit code — prevents git conflicts
- **Set timeouts** for one-shot mode — complex tasks can take 5-10 minutes
- **Use `hermes chat -q` for fire-and-forget** — no PTY needed
- **Use tmux for interactive sessions** — raw PTY mode has `\r` vs `\n` issues with prompt_toolkit
- **For scheduled tasks**, use the `cronjob` tool instead of spawning — handles delivery and retry

---

## Troubleshooting

### Voice not working
1. Check `stt.enabled: true` in config.yaml for voice input/transcription issues.
2. For TTS output, confirm `tts.provider` is configured (Edge TTS needs no key) and `/voice status` shows the expected mode: `TTS (voice reply to all messages)` for `/voice tts`.
3. Verify provider dependencies from the Hermes source venv when needed: `cd ~/hermes-agent && source venv/bin/activate && python -c 'import edge_tts, tools.tts_tool'`.
4. Inspect `$HERMES_HOME/gateway_voice_mode.json`; Telegram DMs should have a platform-prefixed key like `telegram:<chat_id>: "all"` for text+voice replies.
5. Check gateway logs for `Auto voice reply failed`, `Auto voice reply TTS failed`, `send_voice`, or only `Sending response` lines with no TTS activity.
6. If `/voice tts` is enabled but replies remain text-only after a manual `text_to_speech` tool call earlier in the same long session, inspect `_should_send_voice_reply` in `gateway/run.py`: the TTS dedup check must only consider current-turn messages, not the whole resumed session history. A historical `text_to_speech` tool call can otherwise suppress all future auto-TTS. Add/verify a regression in `tests/gateway/test_voice_command.py::TestAutoVoiceReply`, including compressed/resumed-session edge cases, and restart the gateway. See `references/gateway-tts-current-turn-dedup.md` for the concrete PR pattern and test checklist.
7. In gateway: `/restart`. In CLI: exit and relaunch.

### Tool not available
1. `hermes tools` — check if toolset is enabled for your platform
2. Some tools need env vars (check `.env`)
3. `/reset` after enabling tools

### Model/provider issues
1. `hermes doctor` — check config and dependencies
2. `hermes login` — re-authenticate OAuth providers
3. Check `.env` has the right API key
4. **Copilot 403**: `gh auth login` tokens do NOT work for Copilot API. You must use the Copilot-specific OAuth device code flow via `hermes model` → GitHub Copilot.

### Changes not taking effect
- **Tools/skills:** `/reset` starts a new session with updated toolset
- **Config changes:** In gateway: `/restart`. In CLI: exit and relaunch.
- **Code changes:** Restart the CLI or gateway process

### Skills not showing
1. `hermes skills list` — verify installed
2. `hermes skills config` — check platform enablement
3. Load explicitly: `/skill name` or `hermes -s name`

### Gateway issues
Check logs first:
```bash
grep -i "failed to send\|error" ~/.hermes/logs/gateway.log | tail -20
```

Common gateway problems:
- **macOS unattended restart does not bring Hermes back**: user LaunchAgents only run after a user session exists. If FileVault is enabled and no one unlocks the disk/login screen, Wi-Fi and the Hermes gateway can remain unavailable after a cold reboot. For an always-on home agent host, the practical recovery setup is: disable FileVault if acceptable, enable auto-login for the Hermes user, keep `ai.hermes.gateway` as a user LaunchAgent with `RunAtLoad`, and optionally add a post-login watchdog that powers Wi-Fi on, waits for a default route/HTTP probe, and kickstarts `ai.hermes.gateway`. If physical access is a concern, add a delayed `CGSession -suspend` LaunchAgent after auto-login; this locks the screen while preserving the logged-in user session and running LaunchAgents. For planned reboots while keeping FileVault, use `sudo fdesetup authrestart -delayminutes 0` before rebooting; it is one-shot and does not solve crash/power-loss cold boot.
- **Gateway dies on SSH logout**: Enable linger: `sudo loginctl enable-linger $USER`
- **Gateway dies on WSL2 close**: WSL2 requires `systemd=true` in `/etc/wsl.conf` for systemd services to work. Without it, gateway falls back to `nohup` (dies when session closes).
- **Gateway crash loop**: Reset the failed state: `systemctl --user reset-failed hermes-gateway`

### Platform-specific issues
- **Discord bot silent**: Must enable **Message Content Intent** in Bot → Privileged Gateway Intents.
- **Slack bot only works in DMs**: Must subscribe to `message.channels` event. Without it, the bot ignores public channels.
- **Windows HTTP 400 "No models provided"**: Config file encoding issue (BOM). Ensure `config.yaml` is saved as UTF-8 without BOM.

### Auxiliary models not working
If `auxiliary` tasks (vision, compression, session_search) fail silently, the `auto` provider can't find a backend. Either set `OPENROUTER_API_KEY` or `GOOGLE_API_KEY`, or explicitly configure each auxiliary task's provider:
```bash
hermes config set auxiliary.vision.provider <your_provider>
hermes config set auxiliary.vision.model <model_name>
```

---

## Where to Find Things

| Looking for... | Location |
|----------------|----------|
| Config options | `hermes config edit` or [Configuration docs](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) |
| Available tools | `hermes tools list` or [Tools reference](https://hermes-agent.nousresearch.com/docs/reference/tools-reference) |
| Slash commands | `/help` in session or [Slash commands reference](https://hermes-agent.nousresearch.com/docs/reference/slash-commands) |
| Skills catalog | `hermes skills browse` or [Skills catalog](https://hermes-agent.nousresearch.com/docs/reference/skills-catalog) |
| Provider setup | `hermes model` or [Providers guide](https://hermes-agent.nousresearch.com/docs/integrations/providers) |
| Platform setup | `hermes gateway setup` or [Messaging docs](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/) |
| MCP servers | `hermes mcp list` or [MCP guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) |
| Profiles | `hermes profile list` or [Profiles docs](https://hermes-agent.nousresearch.com/docs/user-guide/profiles) |
| Cron jobs | `hermes cron list` or [Cron docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) |
| Memory | `hermes memory status` or [Memory docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) |
| Env variables | `hermes config env-path` or [Env vars reference](https://hermes-agent.nousresearch.com/docs/reference/environment-variables) |
| CLI commands | `hermes --help` or [CLI reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands) |
| Gateway logs | `~/.hermes/logs/gateway.log` |
| Session files | `~/.hermes/sessions/` or `hermes sessions browse` |
| Source code | `~/.hermes/hermes-agent/` |

---

## Contributor Quick Reference

For occasional contributors and PR authors. Full developer docs: https://hermes-agent.nousresearch.com/docs/developer-guide/

### Project Layout

```
hermes-agent/
├── run_agent.py          # AIAgent — core conversation loop
├── model_tools.py        # Tool discovery and dispatch
├── toolsets.py           # Toolset definitions
├── cli.py                # Interactive CLI (HermesCLI)
├── hermes_state.py       # SQLite session store
├── agent/                # Prompt builder, context compression, memory, model routing, credential pooling, skill dispatch
├── hermes_cli/           # CLI subcommands, config, setup, commands
│   ├── commands.py       # Slash command registry (CommandDef)
│   ├── config.py         # DEFAULT_CONFIG, env var definitions
│   └── main.py           # CLI entry point and argparse
├── tools/                # One file per tool
│   └── registry.py       # Central tool registry
├── gateway/              # Messaging gateway
│   └── platforms/        # Platform adapters (telegram, discord, etc.)
├── cron/                 # Job scheduler
├── tests/                # ~3000 pytest tests
└── website/              # Docusaurus docs site
```

Config: `~/.hermes/config.yaml` (settings), `~/.hermes/.env` (API keys).

### Adding a Tool (3 files)

**1. Create `tools/your_tool.py`:**
```python
import json, os
from tools.registry import registry

def check_requirements() -> bool:
    return bool(os.getenv("EXAMPLE_API_KEY"))

def example_tool(param: str, task_id: str = None) -> str:
    return json.dumps({"success": True, "data": "..."})

registry.register(
    name="example_tool",
    toolset="example",
    schema={"name": "example_tool", "description": "...", "parameters": {...}},
    handler=lambda args, **kw: example_tool(
        param=args.get("param", ""), task_id=kw.get("task_id")),
    check_fn=check_requirements,
    requires_env=["EXAMPLE_API_KEY"],
)
```

**2. Add to `toolsets.py`** → `_HERMES_CORE_TOOLS` list.

Auto-discovery: any `tools/*.py` file with a top-level `registry.register()` call is imported automatically — no manual list needed.

All handlers must return JSON strings. Use `get_hermes_home()` for paths, never hardcode `~/.hermes`.

### Adding a Slash Command

1. Add `CommandDef` to `COMMAND_REGISTRY` in `hermes_cli/commands.py`
2. Add handler in `cli.py` → `process_command()`
3. (Optional) Add gateway handler in `gateway/run.py`

All consumers (help text, autocomplete, Telegram menu, Slack mapping) derive from the central registry automatically.

### Adding an i18n Locale

Hermes' thin static-message i18n layer lives in `agent/i18n.py` with catalogs under `locales/<lang>.yaml`. To add a supported language:

1. Add the language code to `SUPPORTED_LANGUAGES` in `agent/i18n.py` and update the module docstring.
2. Add natural aliases to `_LANGUAGE_ALIASES` (e.g. English name, regional tag like `uk-UA`, native language name, common shorthand if appropriate).
3. Add `locales/<lang>.yaml` with exactly the same key set and placeholders as `locales/en.yaml`; tests enforce parity.
4. Update the `display.language` supported-values comments in `hermes_cli/config.py` and `website/docs/user-guide/configuration.md`.
5. Update `tests/agent/test_i18n.py` with at least alias coverage and one explicit translation assertion for the new locale.
6. Run focused tests:
   ```bash
   python -m pytest tests/agent/test_i18n.py -q
   python -m pytest tests/agent/test_i18n.py tests/hermes_cli/test_config.py -q
   ```

Pitfall: when creating a PR body for i18n changes, use `gh pr create --body-file` if mentioning markdown code spans like `` `uk` `` or `locales/uk.yaml`; backticks inside a double-quoted shell argument execute command substitution and mangle the body.

### Agent Loop (High Level)

```
run_conversation():
  1. Build system prompt
  2. Loop while iterations < max:
     a. Call LLM (OpenAI-format messages + tool schemas)
     b. If tool_calls → dispatch each via handle_function_call() → append results → continue
     c. If text response → return
  3. Context compression triggers automatically near token limit
```

### Testing

```bash
python -m pytest tests/ -o 'addopts=' -q   # Full suite
python -m pytest tests/tools/ -q            # Specific area
```

- Tests auto-redirect `HERMES_HOME` to temp dirs — never touch real `~/.hermes/`
- Run full suite before pushing any change
- Use `-o 'addopts='` to clear any baked-in pytest flags

### Commit Conventions

```
type: concise subject line

Optional body.
```

Types: `fix:`, `feat:`, `refactor:`, `docs:`, `chore:`

### Key Rules

- **Never break prompt caching** — don't change context, tools, or system prompt mid-conversation
- **Message role alternation** — never two assistant or two user messages in a row
- Use `get_hermes_home()` from `hermes_constants` for all paths (profile-safe)
- Config values go in `config.yaml`, secrets go in `.env`
- New tools need a `check_fn` so they only appear when requirements are met
