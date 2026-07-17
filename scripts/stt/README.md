# Local Whisper Turbo STT

`whisper-turbo-auto.sh` is the shared local-only STT runner used by Hermes and
OpenClaw on this machine.

## Contract

```bash
whisper-turbo-auto.sh INPUT_AUDIO [OUTPUT_TEXT]
```

- Runs the locally installed OpenAI Whisper CLI using its `turbo` model
  (`large-v3-turbo.pt`, cached under `~/.cache/whisper/`).
- Uses `--task transcribe`, preserving the source language rather than
  translating Ukrainian into English.
- Intentionally omits `--language`, so Whisper performs automatic language
  detection for English, Ukrainian, and code-switched voice notes.
- Emits the plain-text transcript to stdout. If `OUTPUT_TEXT` is supplied, it
  also writes the same transcript there for Hermes command-provider use.
- Requires no API key and never uploads the audio.

## Runtime integration

- **Hermes:** `stt.provider: whisper-turbo-local`, a command provider that
  invokes this runner with `{input_path} {output_path}`.
- **OpenClaw:** `tools.media.audio.models[0]`, a `type: "cli"` entry that
  invokes this runner with `{{MediaPath}}`. This explicit local entry prevents
  configured cloud STT providers from being auto-selected first.

## Verify

```bash
scripts/stt/whisper-turbo-auto.sh /path/to/voice-note.ogg
```

The program exits non-zero when Whisper fails or does not produce exactly one
non-empty text transcript. The caller should keep its own timeout; Hermes and
OpenClaw are configured with a 120-second limit.
