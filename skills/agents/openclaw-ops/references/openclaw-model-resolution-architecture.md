# OpenClaw Model Resolution Architecture

## The Two Resolution Paths

OpenClaw resolves models through two **completely separate** paths that often diverge:

| Path | Source Code Chain | Data Source | Used By |
|------|------------------|-------------|---------|
| **CLI / live API** | `list.list-command.ts` → `list.registry.ts` → `loadProviderCatalogModelsForList()` → `runProviderCatalog()` → provider plugin | Provider API (e.g. `https://opencode.ai/zen/v1/models`) | `openclaw models list`, `--refresh`, `--provider <id>` |
| **Agent runtime / cache** | `model.ts` → `resolveModelWithRegistry()` → `modelRegistry.find()` → reads `models.json` | `~/.openclaw/agents/<agent-id>/agent/models.json` | Agent inference, fallback chain |

## How `models.json` Gets Built

The cache is written by `ensureOpenClawModelsJson()` in `src/agents/models-config.ts`. It is called:

1. **During gateway startup** from `server-startup-post-attach.ts` (line 568). It passes `providerDiscoveryProviderIds: [defaultProvider]` — meaning it **only discovers models for the default model's provider** (e.g. `openai-codex`). Other providers are NOT cached.

2. **During config-model parsing** — models listed in `agents.defaults.models` are written into `models.json` from the user's `openclaw.json` config. Models only in `fallbacks` are NOT cached.

The merge logic is in `planOpenClawModelsJson()` which combines:
- Provider models discovered during startup prewarm
- Models from `agents.defaults.models` (the configured models map)
- OAuth provider modifications

### The Startup Prewarm Gap

When the gateway starts, `ensureOpenClawModelsJson` is called with `providerDiscoveryProviderIds: [defaultProvider]` — it only discovers models for the **default model's provider** (e.g. `openai-codex`). If that provider's discovery fails (auth expired, API down), `providers: {}` is written, **silently wiping any previously cached providers**.

The discovery can fail silently because:
- The `openai-codex` provider's `resolveDynamicModel` hook queries Codex CLI state which may be stale
- The startup code does no validation of the discovery result before passing it to the merge/write
- `filterWritableProviders` then drops any provider entry lacking `baseUrl` or `apiKey`

**The merge-mode survival trick**: If `models.json` already has valid provider entries (with `apiKey: "***"` placeholder) before the gateway starts, the merge mode in `ensureOpenClawModelsJson` preserves them. The merge combines the empty discovery result with the existing file. This means you can **pre-write a correct `models.json` before restarting the gateway** and it will survive — as long as every provider with models has the `apiKey: "***"` placeholder.

## The `models` vs `fallbacks` Trap

In the user's `openclaw.json`, models are configured under `agents.defaults`:
- `models` — key-value map of `"provider/model-id": { "alias": "..." }`. These get written to `models.json`.
- `model.fallbacks` — ordered array of `"provider/model-id"`. These do NOT get written to `models.json`.

If a model is only in `fallbacks`, not in `models`, the agent runtime will fail with `"Unknown model"` when it tries to fall back to it. You must also add it to `models` to ensure it's cached.

## The `resolveDynamicModel` Runtime Hook Gap (Critical)

Model resolution at agent runtime uses **two** mechanisms in sequence:

1. **Plugin `resolveDynamicModel` hook**: `runProviderDynamicModel()` (~/openclaw/src/plugins/provider-runtime.ts:195) calls `resolveDynamicModel()` on the provider plugin. This resolves the model dynamically from the provider's own auth/config without touching `models.json`.
2. **Cached `models.json`**: Only if (1) returns `undefined` does it fall through to the model registry cache.

**The gap**: The `opencode` (Zen) plugin does **NOT** implement `resolveDynamicModel`. Unlike `opencode-go`, `openai-codex`, `codex`, `anthropic`, `openrouter`, `google`, and every other major bundled plugin — which all have this hook — the opencode Zen plugin only registers replay-family hooks (`PASSTHROUGH_GEMINI_REPLAY_HOOKS`). This means:

| Provider | Has `resolveDynamicModel`? | Can resolve without `models.json`? |
|----------|---------------------------|-------------------------------------|
| `opencode` (Zen) | ❌ No | ❌ No — depends entirely on cache |
| `opencode-go` | ✅ Yes | ✅ Yes — runtime hook works |
| `openai-codex` | ✅ Yes | ✅ Yes — runtime hook works |
| `codex` | ✅ Yes | ✅ Yes — runtime hook works |
| All other bundled providers | ✅ Yes | ✅ Yes |

**Consequence**: `opencode/deepseek-v4-flash-free` can ONLY be resolved via the `models.json` cache. If it's missing from the cache (which it usually is — see startup prewarm gap above), the agent always reports `⚠️ Unknown model: opencode/deepseek-v4-flash-free`.

The `models list` CLI command works because it uses `runProviderCatalog()` (different code path) which queries the OpenCode `/v1/models` API directly.

## The `isWritableProviderConfig` Filter (aka `apiKey: "***"` Rule)

When `ensureOpenClawModelsJson()` writes `models.json`, every provider entry goes through `filterWritableProviders()` in `src/agents/models-config.plan.ts`:

```typescript
function isWritableProviderConfig(provider: ProviderConfig): boolean {
  if (!Array.isArray(provider.models) || provider.models.length === 0) {
    return true;             // empty providers are kept
  }
  return Boolean(provider.baseUrl?.trim() && provider.apiKey);  // 👈 requires BOTH
}
```

Providers with models MUST have both `baseUrl` AND `apiKey` set. If either is missing, the entire provider entry is **silently dropped** from `models.json`.

### The `apiKey: "***"` Placeholder

Most providers resolve their API key at runtime from env vars or auth profiles, not from a literal key in `models.json`. To satisfy the filter, the cached `models.json` stores a redacted placeholder:

```json
{
  "opencode": {
    "baseUrl": "https://opencode.ai/zen/v1",
    "apiKey": "***",
    "auth": "env",
    "api": "openai-responses",
    "models": [...]
  }
}
```

When manually constructing a provider entry in `models.json` (hot-fix), you **must** include `"apiKey": "***"` or `filterWritableProviders` will silently discard it on the next gateway restart. The actual API key (`OPENCODE_ZEN_API_KEY` env var, Codex OAuth token, etc.) is resolved at request time by the provider's transport layer, not from the `apiKey` field in `models.json`.

### Why the merge SURVIVES with the placeholder, but gets wiped without it

When `ensureOpenClawModelsJson` runs on startup:
1. Discovery for `openai-codex` runs → fails → empty
2. Merge: new (empty) + existing (your manual entry with `apiKey: "***"`) → keeps existing
3. **Filter**: `isWritableProviderConfig(opencode)` checks `baseUrl` (set) AND `apiKey` (`"***"` truthy) → `true` → **kept**
4. Without `apiKey: "***"`: check returns `false` → entire provider entry **silently dropped** → only `providers: {}` survives

## Manual `models.json` Injection (Hot Fix Pattern)

Use this when a provider's models exist in the CLI (`models list --refresh` shows them) but the agent runtime can't find them.

### 1. Get model IDs from the live API

```bash
cd ~/openclaw && pnpm openclaw models list --json > /tmp/all-models.json
```

Parse the output to see what models are available for the missing provider:

```bash
python3 -c "
import json
d = json.load(open('/tmp/all-models.json'))
for p in d:
    print(f'{p[\"provider\"]}: {p[\"id\"]} ({p[\"name\"]})  ctx={p.get(\"contextWindow\",\"?\")}')
"
```

Collect the model `id`, `name`, `contextWindow`, and `input` type for each model you want to add.

### 2. Construct the provider entry

Every provider entry in `models.json` needs:
- `baseUrl` — the provider's API endpoint
- `apiKey`: `"***"` — the placeholder (required by `isWritableProviderConfig`)
- `api` — the API format (e.g. `"openai-responses"`, `"openai-codex-responses"`)
- `auth` — runtime auth method (e.g. `"token"`, `"env"`)
- `models` — array of model objects with `id`, `name`, `input`, `cost`, `contextWindow`, `maxTokens`

Known provider configs:

| Provider | `provider` key | `baseUrl` | `api` | `auth` |
|----------|---------------|-----------|-------|--------|
| Codex | `codex` | `https://chatgpt.com/backend-api` | `openai-codex-responses` | `token` |
| OpenCode Go | `opencode-go` | `https://api.opencode.ai/v1` | `openai-responses` | env |
| OpenCode Zen | `opencode` | `https://opencode.ai/zen/v1` | `openai-responses` | `env` |
| Google | `google` | varies by plugin | `google-gemini` | env/OAuth |

### 3. Write the complete file

```bash
cat > ~/.openclaw/agents/main/agent/models.json << 'JSONEOF'
{
  "providers": {
    "opencode": {
      "baseUrl": "https://opencode.ai/zen/v1",
      "apiKey": "***",
      "auth": "env",
      "api": "openai-responses",
      "models": [
        {
          "id": "deepseek-v4-flash-free",
          "name": "DeepSeek V4 Flash Free",
          "input": ["text"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
          "contextWindow": 195000,
          "maxTokens": 16384
        }
      ]
    }
  }
}
JSONEOF
```

**Critical**: If you're replacing a file that the gateway startup wipes, pre-write with `apiKey: "***"` BEFORE restarting. The merge mode keeps it.

### 4. Restart the gateway

```bash
kill $(pgrep -f "openclaw.*gateway")
sleep 8
# Verify:
curl -s http://localhost:18789/health
python3 -c "
import json
d = json.load(open('$HOME/.openclaw/agents/main/agent/models.json'))
providers = d.get('providers', {})
print('Providers:', list(providers.keys()))
for k,v in providers.items():
    models = [m['id'] for m in v.get('models',[])]
    print(f'  {k}: {models}')
"
```

### 5. If the entry gets wiped on restart

Check the gateway startup logs:
```bash
grep -iE 'startup failed|filterWritable|model.*json|provider.*config' ~/.openclaw/logs/gateway.log 2>/dev/null | tail -20
```

Common causes of wipe:
- Missing `apiKey: "***"` → silently filtered out
- `baseUrl` is blank or typo'd
- The startup wrote `providers: {}` because `openai-codex` discovery failed AND the merge mode wasn't actually preserving your entry (check that the file was written BEFORE the gateway started, not after)

The merge mode keeps any entry that was in models.json at the time of startup. It does NOT keep entries added after the gateway has already started and written the empty file.

## Config-Based Fix: `models.providers` (Alternative to Manual `models.json` Injection)

When the agent reports the error:

```
⚠️ Unknown model: opencode/deepseek-v4-flash-free.
Found agents.defaults.models["opencode/deepseek-v4-flash-free"],
but no matching models.providers["opencode"].models[] entry.
Add { "id": "deepseek-v4-flash-free" } to
models.providers["opencode"].models[] to register this provider model.
```

The error means the agent **found** the model in `agents.defaults.models` (the alias/config map) but **did not find** it in `models.providers["opencode"].models[]` — the explicit provider definition section. This is resolved by adding the provider definition to the **top-level `models`** section of `openclaw.json`, not by editing `models.json`.

### Add to `models.providers` in `openclaw.json`

```json
{
  "models": {
    "providers": {
      "opencode": {
        "baseUrl": "https://opencode.ai/zen/v1",
        "apiKey": {
          "id": "OPENCODE_ZEN_API_KEY",
          "source": "env"
        },
        "api": "openai-responses",
        "models": [
          {
            "id": "deepseek-v4-flash-free",
            "name": "DeepSeek V4 Flash Free",
            "input": ["text"],
            "contextWindow": 195000,
            "maxTokens": 16384
          }
        ]
      }
    }
  }
}
```

Key differences from `models.json` hot-fix:
| Aspect | Manual `models.json` injection | `models.providers` config |
|--------|-------------------------------|---------------------------|
| Where | `~/.openclaw/agents/<id>/agent/models.json` | `~/.openclaw/openclaw.json` |
| `apiKey` format | Literal `"***"` placeholder | `{ "id": "ENV_VAR", "source": "env" }` object |
| Persistence | Overwritten on gateway restart | Always loaded from config |
| Scope | Single agent | All agents and model resolution paths |

### The `apiKey` format in `models.providers`

In the config, `apiKey` uses an **object form** that tells the secrets resolver where to find the key:

```json
"apiKey": {
  "id": "OPENCODE_ZEN_API_KEY",
  "source": "env"
}
```

This is different from the `models.json` placeholder `"***"` because the config is read by the secrets resolver which needs to know the source and env var name. The `models.json` placeholder only needs to satisfy the `isWritableProviderConfig` filter — the actual key is resolved at request time.

**⚠️ `SecretRef` format requirement — 3 fields required**

The `apiKey` object MUST be a valid `SecretRef` (defined in `src/config/types.secrets.ts`):

```typescript
type SecretRef = {
  source: SecretRefSource;   // "env" | "file" | "exec"
  provider: string;          // e.g. "default" — REQUIRED
  id: string;                // e.g. "OPENCODE_ZEN_API_KEY"
};
```

The `isSecretRef()` validator checks `Object.keys(value).length === 3`. If you omit `provider`, config validation rejects it with:

```text
Invalid config at openclaw.json. models.providers.opencode.apiKey: Invalid input
Run "openclaw doctor --fix" to repair, then retry.
```

This causes a **gateway crash-loop**: the startup fails, launchd restarts repeatedly. The error does NOT appear in `gateway.log` — it only shows in stability bundles under `~/.openclaw/logs/stability/*.json`. Crash-loop symptom: repeated log cycles of `loading configuration...` → `resolving authentication...` → `starting...` with no `http server listening` or `ready` message.

**When `apiKey` can be removed entirely**

For providers that handle auth through their own plugin mechanism (env var reflection, built-in auth profiles), the `apiKey` field in `models.providers` is optional. If removing it fixes the startup failure (missing env var in LaunchAgent env file), the gateway starts without the initial secret lookup:

```json
"opencode": {
  "baseUrl": "https://opencode.ai/zen/v1",
  "api": "openai-responses",
  "models": [
    { "id": "deepseek-v4-flash-free", ... }
  ]
}
```

The provider plugin handles auth at inference time via its own env var reading (e.g. `OPENCODE_ZEN_API_KEY`). The model in `models.providers` still gets written to `models.json` with `apiKey: "***"` placeholder because the merge process generates it from the existing cache. This works because `isWritableProviderConfig` checks the merged output (which has the placeholder), not the raw config entry.

**Pitfall**: Remove the `apiKey` only when the provider has its own auth mechanism that doesn't need a config-level secret ref. For providers that DO need it (`codex`, `openai-codex` with token auth), keep the `apiKey` with correct 3-field `SecretRef` format.

### Auth profile requirement

A provider defined in `models.providers` but lacking a matching `auth.profiles` entry will fail at inference time (not during model resolution). To use the model, also add:

```json
"auth": {
  "profiles": {
    "opencode:default": {
      "mode": "api_key",
      "provider": "opencode"
    }
  }
}
```

If the API key comes from an env var that the LaunchAgent service env file does not contain, injection into the env file is also required unless the provider's `apiKey` resolver reads it via a `$(cat ...)` pattern from sops-nix. For the `opencode` (Zen) provider, ensure `OPENCODE_ZEN_API_KEY` is exported in `~/.openclaw/service-env/ai.openclaw.gateway.env`.

### When to use which fix

| Situation | Best fix |
|-----------|----------|
| Provider has `resolveDynamicModel` (e.g. `opencode-go`) | Add to `agents.defaults.models` only — runtime hook handles the rest |
| Provider lacks `resolveDynamicModel` (e.g. `opencode` Zen) | **Both**: add to `agents.defaults.models` AND add to `models.providers` (OR use manual `models.json` injection) |
| Quick hot-fix during debugging | Manual `models.json` injection (no restart needed if file already has merge-compatible entries) |
| Permanent solution | `models.providers` config entry + auth profile — survives restarts |

## Upstream PR Fix: Adding `resolveDynamicModel` to the OpenCode Zen Plugin

The **proper** upstream fix is to add a `resolveDynamicModel` runtime hook to the `opencode` (Zen) provider plugin, identical to what `opencode-go` already has.

### Current state

File: `extensions/opencode/index.ts`

```typescript
export default definePluginEntry({
  id: PROVIDER_ID,
  name: "OpenCode Zen Provider",
  register(api) {
    api.registerProvider({
      id: PROVIDER_ID,
      // ...
      ...PASSTHROUGH_GEMINI_REPLAY_HOOKS,    // has replay hooks only
      isModernModelRef: ({ modelId }) => isModernOpencodeModel(modelId),
      resolveThinkingProfile: ({ modelId }) => resolveClaudeThinkingProfile(modelId),
      // ❌ NO resolveDynamicModel
      // ❌ NO augmentModelCatalog
    });
  },
});
```

### Required additions

Model the changes on `extensions/opencode-go/index.ts` (line 91-92):

```typescript
import {
  listOpencodeZenModelCatalogEntries,
  normalizeOpencodeZenBaseUrl,
  normalizeOpencodeZenResolvedModel,
  resolveOpencodeZenModel,
} from "./provider-catalog.js";

// Inside registerProvider():
api.registerProvider({
  id: PROVIDER_ID,
  // ...
  resolveDynamicModel: ({ modelId }) => resolveOpencodeZenModel(modelId),
  augmentModelCatalog: () => listOpencodeZenModelCatalogEntries(),
  // also needs:
  normalizeTransport: ({ api, baseUrl }) => {
    const normalizedBaseUrl = normalizeOpencodeZenBaseUrl({ api, baseUrl });
    return normalizedBaseUrl && normalizedBaseUrl !== baseUrl
      ? { api, baseUrl: normalizedBaseUrl }
      : undefined;
  },
  // ...
});
```

This requires:
- `provider-catalog.ts` in `extensions/opencode/` with `resolveOpencodeZenModel()` and `listOpencodeZenModelCatalogEntries()` — modeled after `extensions/opencode-go/provider-catalog.ts`
- The catalog function queries `https://opencode.ai/zen/v1/models` for model list
- The resolve function handles model ids like `deepseek-v4-flash-free`
- The `-free` models must be included (not filtered out by `isModernModelRef`)
- The normalize function adjusts base URLs to the Zen endpoint

### Benefits of the fix

| Before | After |
|--------|-------|
| Agent can only find `opencode` models via `models.json` cache | Agent can resolve models dynamically at inference time |
| `models.providers` config entry required for every model | No config changes needed — runtime hook handles resolution |
| Startup prewarm gap means models may be missing from cache | Runtime hook doesn't depend on cache |
| Config workaround needed for each new model | Any model the Zen API returns is automatically usable |

### Concrete implementation (PR #1)

The full implementation was created at `olisikh/openclaw` PR #1 (https://github.com/olisikh/openclaw/pull/1), branch `feat/opencode-split-provider-keys`.

**Files changed:**

- `extensions/opencode/provider-catalog.ts` **(new)** — static model catalog + `resolveOpencodeZenModel()` + `listOpencodeZenModelCatalogEntries()` + normalization functions, modeled after `extensions/opencode-go/provider-catalog.ts`
- `extensions/opencode/index.ts` **(modified)** — added imports and wired `resolveDynamicModel`, `augmentModelCatalog`, `normalizeConfig`, `normalizeResolvedModel`, and `normalizeTransport` hooks into the provider registration

**Verification commands:**

```bash
cd ~/openclaw
pnpm build                                    # must pass — regenerates dist
pnpm test -- extensions/opencode              # must pass — all 13 opencode tests
pnpm openclaw models list --provider opencode # must show deepseek-v4-flash-free
```

**Design notes:**

- The static model catalog in `provider-catalog.ts` covers `deepseek-v4-flash-free` (the free tier model) plus the default `claude-opus-4-6` model. The `-free` model is classified as "not modern" by `isModernModelRef` — this only affects streaming/replay policy, not model resolution. The Zen API can proxy many more models (Claude, Gemini, GPT, etc.) but those are covered by other provider plugins; the catalog focuses on Zen-specific models.
- `augmentModelCatalog` returns catalog entries so the model appears in provider discovery feeds.
- `resolveDynamicModel` returns a `ProviderRuntimeModel` by ID lookup in the static catalog. If the model isn't in the catalog, it returns `undefined` (safe fallback — the agent falls through to the `models.json` cache or the next fallback).
- `normalizeConfig`, `normalizeResolvedModel`, and `normalizeTransport` ensure base URLs and model parameters are consistent with the Zen endpoint.
- The implementation mirrors `extensions/opencode-go/provider-catalog.ts` exactly, which is the canonical pattern for provider plugins in the OpenClaw codebase.
- The PR was rebased against `origin/main` and the opencode extension tests pass (13/13).

### All bundled providers that implement resolveDynamicModel

This list helps confirm the off-by-one gap:

- `opencode-go` ✅ — `resolveOpencodeGoModel(modelId)`
- `openai-codex` ✅ — codex provider handles it
- `anthropic` ✅
- `openrouter` ✅
- `google` ✅
- `openai` ✅
- `ollama` ✅
- `lmstudio` ✅
- `xai` ✅
- `github-copilot` ✅
- `fireworks` ✅
- `zai` ✅
- `codex` ✅
- `opencode` (Zen) ❌ — **the only bundled provider without it**

## Diagnostic Flow

### 1. Check models.json content

```bash
python3 -c "
import json
d = json.load(open('$HOME/.openclaw/agents/main/agent/models.json'))
providers = d.get('providers', {})
print('Providers in cache:', list(providers.keys()))
for k, v in providers.items():
    print(f'  {k}: {[m[\"id\"] for m in v.get(\"models\", [])]}')
"
```

### 2. Check which providers have auth configured

```bash
cd ~/openclaw && pnpm openclaw models status
```

Look for:
- `Configured models (N)` — models from `agents.defaults.models`
- `Fallbacks (N) (defaults)` — fallback chain from `agents.defaults.model.fallbacks`
- `Auth profiles` — which provider profiles exist (e.g. `opencode-go:default` but not `opencode:default`)

### 3. Force a fresh discovery to compare

```bash
cd ~/openclaw && pnpm openclaw models list --provider opencode --refresh
```

If the model appears here but NOT in models.json → cache gap. The agent won't see it.

### 4. Fix the cache gap

**Option A: Add to `agents.defaults.models`** in `~/.openclaw/openclaw.json` + manually inject provider entry into `models.json`, then restart the gateway. This is the most reliable method for providers without `resolveDynamicModel`.

**Option B: Manual hot fix** — construct the provider entry directly in `models.json` (see "Manual models.json Injection" section above). Requires `apiKey: "***"` to survive the startup merge.

**Option C: Delete and restart** — only works if the startup prewarm can discover ALL the providers you need. If the default provider's discovery fails, you get `providers: {}`.

## Provider Name Aliasing in the Model Registry

The model registry maps `modelRegistry.find(provider, modelId)` against the `models.json` provider keys. However, the user's `openclaw.json` config often uses a different provider name than what's stored in `models.json`:

| Config ref namespace | `models.json` provider key | Example |
|---------------------|---------------------------|---------|
| `openai-codex/...` | `codex` | `openai-codex/gpt-5.4` → model stored under `codex` provider |
| `opencode/...` | `opencode` | Same name — no alias |
| `opencode-go/...` | `opencode-go` | Same name — no alias |

The alias resolution happens via `canonicalizeManifestModelCatalogProviderAlias()` in the static catalog path, but the `modelRegistry.find()` path may fail to match if the provider name differs between config and cache file. When debugging "Unknown model" errors, verify the provider key under which the model is actually stored in `models.json`.

## Common Error Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `⚠️ Unknown model: opencode/<model>` | Model not in `models.json` cache, AND opencode Zen plugin lacks `resolveDynamicModel` runtime hook | Add to `agents.defaults.models` + manually inject `opencode` provider entry into `models.json` (with `apiKey: "***"`) + restart gateway |
| Model appears in `models list` but agent can't use it | CLI path ≠ agent runtime path (see above) | Fix cache gap — either add to `agents.defaults.models` or manually construct provider entry in `models.json` |
| `Config invalid: Unrecognized key` | Config written by newer OpenClaw, running older binary | Use source build or run `doctor --fix` |
| `Models list --provider opencode` returns 0 models | Binary too old for config, or provider API error | Use source build; check `openclaw models status` for auth |
| Gateway crash-loop — repeated loading config... → starting... cycles, no ready message | (a) Config validation failure in models.providers apiKey (invalid SecretRef format — missing provider field), OR (b) `"models": null` in `openclaw.json` (schema rejects null — must remove key entirely) | Check stability bundles; fix SecretRef to have 3 fields (source, provider, id) or remove apiKey entirely if provider handles own auth; if error says `"models": Invalid input`, delete the `"models"` key (string must be absent, not null) |
| Gateway restarts wipe manually-added provider from `models.json` | Entry lacked `apiKey: "***"` placeholder → filtered out by `isWritableProviderConfig` | Re-add with `apiKey: "***"`; see rule above |
| `opencode-go` models work but `opencode` models don't, despite both being configured | `opencode-go` has `resolveDynamicModel` runtime hook; `opencode` doesn't | Both must be in `models.json` cache for the agent to resolve them at runtime |

## Key Code Paths (for future debugging)

| File | Function | Role |
|------|----------|------|
| `src/agents/models-config.ts` | `ensureOpenClawModelsJson()` | Writes `models.json` cache; called at startup with default-provider-only scope |
| `src/agents/models-config.plan.ts` | `planOpenClawModelsJson()` | Decides what goes into cache; contains `isWritableProviderConfig` + `filterWritableProviders` |
| `src/agents/models-config.plan.ts` | `isWritableProviderConfig()` | Gate filter requiring `baseUrl` AND `apiKey` for non-empty provider entries |
| `src/gateway/server-startup-post-attach.ts` | (line 548-577) | Calls `ensureOpenClawModelsJson` at startup with default-provider-only scope |
| `src/agents/embedded-agent-runner/model.ts` | `resolveModelWithRegistry()` | Agent runtime model lookup (2-step: dynamic hook → cached registry) |
| `src/agents/embedded-agent-runner/model.ts` | `resolvePluginDynamicModelWithRegistry()` | First step: tries provider plugin's `resolveDynamicModel` runtime hook |
| `src/agents/sessions/model-registry.ts` | `ModelRegistry.find()` | Second step: looks up model in cached `models.json` |
| `src/commands/models/list.provider-catalog.ts` | `loadProviderCatalogModelsForList()` | CLI models listing (live API) |
| `src/commands/models/list.registry.ts` | `loadModelRegistry()` | CLI registry loader |
| `src/plugins/provider-discovery.ts` | `runProviderCatalog()` | Live provider API query |
| `src/plugins/provider-runtime.ts` | `runProviderDynamicModel()` | Runtime model resolution: calls `resolveDynamicModel` on provider plugin |
| `extensions/opencode/index.ts` | — | OpenCode Zen plugin entry — NO `resolveDynamicModel` hook (the root cause) |
| `extensions/opencode-go/index.ts` | `resolveDynamicModel` | OpenCode Go plugin entry — HAS the hook |
