# Gateway TTS current-turn dedup regression (Apr 2026)

Class: Hermes gateway voice/TTS troubleshooting and contribution work.

## Symptom

When `/voice tts` is enabled in Telegram, replies may remain text-only after a manual `text_to_speech` tool call occurred earlier in the same resumed/long session. Gateway logs show normal text response sending, but no new auto-TTS/send_voice activity.

## Root cause pattern

The auto voice reply guard in `gateway/run.py` must deduplicate only against tool calls from the **current turn**, not the entire persisted/resumed message history. If it scans all historical messages, an old `text_to_speech` call can suppress every future automatic voice reply in that chat/session.

This can show up after context compression or long gateway sessions because historical tool calls remain in session history even though they are not part of the active assistant response being delivered.

## Fix pattern

- Identify the current-turn message slice/window before deciding whether auto-TTS has already happened.
- Restrict the `text_to_speech`/TTS tool-call dedup check to that current-turn window.
- Be careful with compressed-session or resumed-session edge cases: do not infer current turn from the whole transcript if compression inserted synthetic messages.
- Restart gateway after code change.

## Regression tests

Add/verify coverage in `tests/gateway/test_voice_command.py::TestAutoVoiceReply` for:

- historical/manual `text_to_speech` tool call does **not** suppress later auto-TTS;
- current-turn `text_to_speech` tool call still suppresses duplicate auto-TTS for the same response;
- compressed/resumed session shapes preserve the current-turn boundary.

Recommended targeted verification:

```bash
python -m pytest tests/gateway/test_voice_command.py -q -o 'addopts='
git diff --check
```

## Session artifact

A concrete implementation of this fix was submitted as PR `NousResearch/hermes-agent#18078` from branch `fix/gateway-tts-current-turn-dedup` with commit message:

```text
fix(gateway): scope TTS dedup to current turn
```

The session's independent review specifically tightened the implementation for compressed-session edge cases before opening the PR.
