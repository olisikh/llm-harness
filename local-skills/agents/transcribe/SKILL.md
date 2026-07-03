---
name: transcribe
description: Read user-provided text aloud as an MP3 using Microsoft Edge TTS with automatic language detection and voice selection. Use when the user asks for TTS, asks you to read text aloud, wants an MP3/voice note from text, or provides text in an arbitrary language and expects you to pick the correct voice.
---

# Transcribe

Despite the name, this skill is for **text-to-speech readout**.

## Goal
Turn arbitrary user text into a good-quality **MP3** using **Edge TTS neural voices**, while automatically:
- detecting the language of the text
- choosing a matching locale/voice
- writing the output MP3 to `~/.hermes/audio_cache/`

See `references/voice-selection.md` for durable voice-selection policy and quality pitfalls.

## Use this workflow
1. Put the source text in a temp file when it is more than a short sentence.
2. Run:
   ```bash
   ~/.agents/skills/transcribe/scripts/read-aloud.sh --text-file /absolute/path/to/text.txt --json
   ```
3. Read the returned JSON and send back:
   - `MEDIA:<mp3_path>`
   - optionally a short note with detected language + chosen voice when useful

## Short text
For short text, you can pass it inline:
```bash
~/.agents/skills/transcribe/scripts/read-aloud.sh --text "Hallo wereld" --json
```

## Useful overrides
- Force locale:
  ```bash
  ~/.agents/skills/transcribe/scripts/read-aloud.sh --text-file /tmp/input.txt --locale nl-BE --json
  ```
- Force a specific voice:
  ```bash
  ~/.agents/skills/transcribe/scripts/read-aloud.sh --text-file /tmp/input.txt --voice nl-NL-ColetteNeural --json
  ```
- Prefer male voice:
  ```bash
  ~/.agents/skills/transcribe/scripts/read-aloud.sh --text-file /tmp/input.txt --gender male --json
  ```
- Dry-run language/voice selection without rendering:
  ```bash
  ~/.agents/skills/transcribe/scripts/read-aloud.sh --text-file /tmp/input.txt --dry-run --json
  ```

## Rules
- Default output format: **MP3**.
- Prefer **Microsoft Edge TTS neural voices** over lower-quality system voices for polished readout.
- Prefer **feminine** locale-matching **Neural** voices by default.
- If the user specifies a language, country variant, gender, or exact voice, honor it.
- If automatic language detection is obviously wrong for a very short or mixed-language text, ask a brief clarifying question or force the locale manually.
- If the user says the previous voice was wrong, rerun with a better locale/voice instead of debating detection.

## Notes
- The helper bootstraps its own local venv and installs `edge-tts` + `langid` if needed.
- Automatic region selection is best-effort: language detection identifies the language, then the helper picks a sensible default locale when several regional voices exist.
- This skill supports whatever languages are currently exposed by `edge-tts --list-voices` on the machine at runtime.
- Prefer the helper in `scripts/read-aloud.sh` for quality-sensitive multilingual readout instead of generic TTS paths that may fall back to an English/default voice.
- See `references/voice-selection.md` for the durable voice-selection policy and concrete locale examples.

## Pitfalls
- Do **not** assume a built-in/default TTS voice can read the target language well just because it produces audio. Verify the detected language and chosen Edge voice, especially for non-English text.
- For polished readout, prefer Microsoft **Neural** voices over macOS `say` voices unless the user explicitly asks for the system voice.
- If the user says the voice sounds wrong, treat that as authoritative feedback and rerender with a better locale/voice immediately.
- When the user asks to "find a poem/text and read it", first obtain the source text, then feed the text into the helper; do not narrate a summary when the request is clearly for spoken audio.
