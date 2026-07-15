#!/usr/bin/env bash
# OpenClaw tts-local-cli adapter: stdin text -> shared router input file.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf 'usage: openclaw-tts-adapter.sh <output_path>\n' >&2
  exit 2
fi

output_path=$1
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
input_path=$(mktemp "${TMPDIR:-/tmp}/openclaw-tts-input.XXXXXX")
trap 'rm -f "$input_path"' EXIT

cat >"$input_path"
"$script_dir/tts-router.sh" "$input_path" "$output_path"
