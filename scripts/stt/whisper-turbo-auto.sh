#!/usr/bin/env bash
# Local Whisper large-v3-turbo transcription for Hermes and OpenClaw.
#
# Usage:
#   whisper-turbo-auto.sh INPUT_AUDIO [OUTPUT_TEXT]
#
# The model's language is intentionally left unspecified so Whisper detects
# English, Ukrainian, and code-switched speech automatically. This emits the
# transcript to stdout and, when OUTPUT_TEXT is supplied, writes it there too.

set -euo pipefail

if (( $# < 1 || $# > 2 )); then
  echo "Usage: $(basename "$0") INPUT_AUDIO [OUTPUT_TEXT]" >&2
  exit 64
fi

input_path=$1
output_path=${2:-}
whisper_bin=${WHISPER_BIN:-/etc/profiles/per-user/olisikh/bin/whisper}
model=${WHISPER_MODEL:-turbo}

if [[ ! -f "$input_path" ]]; then
  echo "Input audio does not exist: $input_path" >&2
  exit 66
fi
if [[ ! -x "$whisper_bin" ]]; then
  echo "Whisper CLI is unavailable: $whisper_bin" >&2
  exit 69
fi

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/whisper-turbo.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT

# No --language flag: Whisper performs source-language detection.
# --task transcribe preserves Ukrainian rather than translating it to English.
run_log="$work_dir/whisper.log"
if ! "$whisper_bin" "$input_path" \
  --model "$model" \
  --task transcribe \
  --output_format txt \
  --output_dir "$work_dir" \
  --verbose False \
  >"$run_log" 2>&1; then
  cat "$run_log" >&2
  exit 70
fi

shopt -s nullglob
transcripts=("$work_dir"/*.txt)
if (( ${#transcripts[@]} != 1 )) || [[ ! -s "${transcripts[0]}" ]]; then
  echo "Whisper did not produce exactly one non-empty text transcript" >&2
  exit 70
fi

if [[ -n "$output_path" ]]; then
  mkdir -p "$(dirname "$output_path")"
  cp "${transcripts[0]}" "$output_path"
fi

cat "${transcripts[0]}"
