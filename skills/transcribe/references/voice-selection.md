# Voice selection notes

This skill should default to **Edge TTS neural voices** for quality-sensitive readout tasks.

## Default policy
- Detect the language from the provided text.
- Match the detected language to an available Edge locale.
- Prefer a **feminine** voice by default unless the user asks otherwise.
- Render **MP3** output to `~/.hermes/audio_cache/`.

## Durable lessons from real use
1. Falling back to an English/default voice for non-English text is unacceptable even if the tool technically returns audio.
2. macOS `say` voices may support a language but still sound noticeably worse than Microsoft neural voices for polished readout.
3. User feedback about voice quality outranks automatic detection; rerender with a better locale/voice instead of defending the first output.

## Practical examples
- Dutch text -> prefer `nl-NL-ColetteNeural` by default; `nl-NL-FennaNeural` is also viable.
- Ukrainian text -> choose a Ukrainian voice such as `uk-UA-PolinaNeural`, not a default English voice.
- If the user asks for a poem to be read aloud, first fetch/prepare the exact poem text, then synthesize from that text.

## Override rules
Honor explicit user requests for:
- exact voice
- locale/region variant
- male voice instead of feminine default
- slower or more presentation-friendly pacing
