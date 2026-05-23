# OpenClaw Billing Retry Loop (Token Drain)

## Pattern

When the primary model works but the **only configured fallback** fails with a **billing/credits error**, OpenClaw enters a ~30-minute retry loop that repeatedly probes the cooldowned profile. Each probe burns a request. If the fallback has `next=none`, the loop never resolves.

## Log Signature

```text
[model-fallback/decision] model fallback decision: decision=probe_cooldown_candidate requested=opencode-go/kimi-k2.5 candidate=opencode-go/kimi-k2.5 reason=billing next=none
[agent/embedded] probing cooldowned auth profile for opencode-go/kimi-k2.5 due to billing unavailability
[agent/embedded] embedded run agent end: … isError=true model=kimi-k2.5 provider=opencode-go error=…billing error…
[agent/embedded] auth profile failure state updated: … reason=billing window=disabled reused=true
[agent/embedded] embedded run failover decision: … decision=fallback_model reason=billing …
[diagnostic] lane task error: … FailoverError: … billing error …
Embedded agent failed before reply: … billing error …
```

This repeats every 30 minutes (`:03` and `:33` past the hour in observed logs).

## Root Causes

1. Fallback model has no credits / monthly spending limit reached.
2. Fallback chain ends at that model (`next=none` → no further fallback).

## Fix

Add at least one working model to the fallback chain in `~/.openclaw/openclaw.json`:

```json
"agents": {
  "defaults": {
    "model": {
      "primary": "google/gemini-2.5-flash",
      "fallbacks": [
        "opencode-go/kimi-k2.5",
        "opencode/kimi-k2.6"
      ]
    }
  }
}
```

Verify available models:

```bash
node ~/openclaw/dist/index.js models list
```

Then restart the gateway:

```bash
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
```

## Prevention

- Always keep **≥2 fallbacks** from different providers.
- Monitor `gateway.err.log` for `probe_cooldown_candidate` + `next=none`.
- If a provider is known to be in billing cooldown, remove it from fallbacks temporarily rather than letting it loop.
