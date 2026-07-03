# Hermes central skill install and verification

Use this when a session establishes, migrates, or repairs the central-skills workflow for Hermes.

## Canonical layout

- Repo root: `~/.llm-harness`
- First-party skill source tree: `~/.llm-harness/local-skills/skills/<category>/<skill>`
- Default local-skills target harness: `agents`
- Hermes-targeted exceptions are declared under `local-skills.overrides` in `~/.llm-harness/config.yaml`
- Runtime install tree: `~/.hermes/skills/<category>/<skill>`

## Required installer behavior

`./harness.py install` must discover every directory containing `SKILL.md` under configured sources and preserve nested category paths in the installed runtime tree. A flat direct-child-only sync is insufficient for Hermes.

## Cron coupling

If a scheduled job keeps `~/.llm-harness` current, it should:

1. work from `~/.llm-harness`
2. update repo state and submodules/sources as needed
3. run `./harness.py install`
4. report final `git status --short --branch`

## Verification recipe

1. Check that canonical repo paths exist.
2. Confirm the skill source lives under `~/.llm-harness/local-skills/skills/...`.
3. Confirm any Hermes-targeted skill has the appropriate `local-skills.overrides` entry in `~/.llm-harness/config.yaml`.
4. Run `cd ~/.llm-harness && ./harness.py install`.
5. Verify runtime paths resolve into the repo, for example:
   - `~/.hermes/skills/autonomous-ai-agents/harness-managed-skills`
   - `~/.hermes/skills/autonomous-ai-agents/llm-harness-ops`
   - `~/.hermes/skills/software-development/hermes-agent-skill-authoring`
6. Confirm docs/instructions no longer describe `~/.agents` or `~/.hermes/skills` as the preferred physical source location for durable skills.
