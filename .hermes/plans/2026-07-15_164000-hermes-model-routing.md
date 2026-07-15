# Hermes Model Routing Implementation Plan

> **For Hermes:** Execute only after Oleksii explicitly approves this plan. Use bounded delegation for review, not for unreviewed runtime configuration changes.

**Goal:** Implement cost-conscious model routing using existing Hermes configuration, `delegate_task`, a compact parent instruction, a harness-managed skill, explicit OpenCode specialists, and isolated Sol escalation.

**Architecture:** Terra remains the judgment-bearing main agent. Luna is globally pinned for native bounded children. Per-task specialist selection uses the existing OpenCode CLI, while deterministic work uses direct tools or `execute_code`. The detailed policy lives in a portable skill; `SOUL.md` contains only the trigger to load it. No Hermes core patch or hook is required.

**Repositories:** `~/.llm-harness`, `~/.hermes`, `~/.llm-wiki`

**Durable project record:** `~/.llm-wiki/hub/topics/hermes/wiki/topics/model-routing-policy.md`

---

## Preconditions and approval gate

- [x] Fetch all three repositories.
- [x] Validate and commit pre-existing changes.
- [x] Push `~/.llm-harness` and verify `HEAD == origin/main` at `169983bba060e8b34f15063e8977aab065bbad85`.
- [x] Push `~/.hermes` and verify `HEAD == origin/main` at `34c97c4a46d010823168104b70e64c22e3744261`.
- [x] Confirm `~/.llm-wiki` started clean and synchronized at `25752b9`.
- [x] Select llm-wiki topic `hermes` and create the kickoff and compiled plan documents.
- [ ] Commit and push this plan documentation, then verify all repositories are clean.
- [ ] Obtain Oleksii's explicit approval before implementing the feature.

## Task 1: Create the portable routing skill

**Files:**

- Create: `~/.llm-harness/local-skills/agents/model-routing/SKILL.md`

**Required content:**

- decision tree for direct tools, `execute_code`, Luna delegates, OpenCode specialists, and Sol review;
- exact provider/model identifiers;
- bounded-worker allowlist and prohibited uses;
- retry, fallback, malformed-output, and failed-tool rules;
- escalation and reviewer criteria;
- Ollama Cloud/local privacy and verification rules;
- compact handoff schema;
- cost caps and examples.

**Validation:**

1. Validate YAML frontmatter.
2. Confirm the skill description reliably matches non-trivial routing tasks.
3. Run `cd ~/.llm-harness && ./harness.py install`.
4. Verify the installed skill is a managed link resolving to the canonical source.
5. Load the skill through Hermes with `skill_view`.
6. Run `git diff --check`.

**Commit:** `feat(skills): add cost-conscious model routing`

## Task 2: Review the policy before runtime changes

**Workers:**

1. Luna `delegate_task`: requirements-compliance matrix against the approved plan.
2. `opencode-go/qwen3.7-max`: independent review of routing logic, cost failure modes, provider switching, and verification.

**Rules:**

- Reviews are read-only.
- Each finding cites an exact section or file.
- Terra resolves findings and reruns static validation.
- Sol is used only if reviews materially conflict or a high-impact unresolved risk remains.

## Task 3: Add compact parent-only orchestration guidance

**File:**

- Modify: `~/.hermes/SOUL.md`

**Change:** Append a short `Work Routing` section instructing the main agent to classify non-trivial work, load the `model-routing` skill, avoid delegating simple work, and verify delegated evidence.

**Validation:**

- Existing identity text remains unchanged.
- Full routing tables are not copied into `SOUL.md`.
- Prompt remains small and stable.
- Confirm delegated children skip context files, so the instruction is parent-only.

## Task 4: Apply routing configuration

**File:**

- Modify: `~/.hermes/config.yaml`

**Target values:**

```yaml
model.provider: openai-codex
model.default: gpt-5.6-terra
agent.reasoning_effort: high
delegation.provider: openai-codex
delegation.model: gpt-5.6-luna
delegation.reasoning_effort: low
delegation.max_concurrent_children: 2
delegation.max_spawn_depth: 1
delegation.max_iterations: 15
```

**Fallback order:**

1. `opencode-go/kimi-k2.7-code`
2. `opencode-go/deepseek-v4-flash`
3. `ollama-cloud/kimi-k2.7-code`
4. low-cost OpenCode Zen hosted fallback(s)

Do not add a local Ollama entry while no local model is installed.

**Validation:**

- Load configuration through `hermes_cli.config.load_config`.
- Run `hermes fallback list`.
- Confirm unrelated config keys and TTS settings are unchanged.
- Run YAML parsing and `git diff --check`.

## Task 5: Run isolated behavioral smoke tests

Do not use the active Telegram conversation for diagnostic prompts.

1. **Direct path:** a simple single-tool request must not delegate.
2. **Cheap parallel path:** a two-part bounded extraction must use two Luna children.
3. **Specialist path:** an explicit OpenCode run must report the selected `opencode-go` model and produce the requested structured output.
4. **Deterministic path:** schema/test validation must use tools, not an LLM subagent.
5. **Reviewer path:** a synthetic high-impact brief must use an isolated Sol reviewer only after explicit escalation.
6. **Handoff path:** verify objective, evidence, tool results, files changed, unresolved questions, and validation status.

Do not deliberately exhaust quotas or simulate a destructive provider outage. Validate fallback configuration structurally.

## Task 6: Deploy, verify, document, and push

1. Commit the Hermes state change with `chore(hermes): configure cost-aware model routing` or a more precise Conventional Commit.
2. Push `~/.llm-harness` and verify remote equality.
3. Push `~/.hermes` using the allowlisted state backup workflow and verify remote equality.
4. Update the llm-wiki article with actual commands, results, review findings, and final model map.
5. Append the Hermes topic log.
6. Commit and push `~/.llm-wiki`.
7. Verify all three repositories are clean and `HEAD == origin/main`.
8. Restart the Hermes gateway after static validation.
9. Verify gateway health and automatic TTS configuration without poisoning active-chat dedup state.

## Rollback

1. Revert only the Hermes-state routing commit.
2. Restart the gateway and verify previous model/delegation/TTS settings.
3. If needed, revert the llm-harness skill commit and rerun `./harness.py install`.
4. Append the rollback result to llm-wiki; never delete the history.

## Out of scope

- Hermes core changes
- hooks
- local Ollama installation
- recursive delegation
- making Sol the default
- changing auxiliary Gemini routes
- unrelated config or skill cleanup
