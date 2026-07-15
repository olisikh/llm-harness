# Shared TTS router

Shared command-based TTS implementation for Hermes and OpenClaw.

- `tts-router.sh <input_path> <output_path>` detects the input language and selects the configured Edge or Voicebox route from `tts-routing.yaml`.
- `openclaw-tts-adapter.sh <output_path>` adapts OpenClaw's `tts-local-cli` contract (text on stdin) to the router's file-input contract.
- `voicebox-tts.py` is the Voicebox REST bridge used by Voicebox routes.
- `tts-routing.yaml` is the single source of truth for language-to-provider/voice mappings. Routes fail directly; no fallback routing is performed.

Runtime configuration remains native and intentionally small:

- Hermes command provider: `~/.llm-harness/scripts/tts/tts-router.sh {input_path} {output_path}`
- OpenClaw `tts-local-cli`: `~/.llm-harness/scripts/tts/openclaw-tts-adapter.sh` with `args: ["{{OutputPath}}"]` and `outputFormat: "opus"`.

`opus` is required for OpenClaw Telegram voice-note requests on this macOS/Nix install: it prevents OpenClaw's own post-processing layer from needing an `ffmpeg` binary on the LaunchAgent's restricted `PATH`. The router itself resolves `ffmpeg` from the standard Nix/macOS locations, or from `FFMPEG_BIN` when explicitly set.
