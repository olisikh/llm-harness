#!/usr/bin/env bash
# Shared command TTS router for Hermes and OpenClaw: language-aware Voicebox or Edge.
set -euo pipefail

if [[ $# -ne 2 ]]; then
  printf 'usage: tts-router.sh <input_path> <output_path>\n' >&2
  exit 2
fi

input_path=$1
output_path=$2
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
edge_helper="$HOME/.agents/skills/transcribe/scripts/read-aloud.sh"
voicebox_bridge="$script_dir/voicebox-tts.py"
config_python="$HOME/.hermes/hermes-agent/venv/bin/python"
ffmpeg_bin="${FFMPEG_BIN:-}"

if [[ -z "$ffmpeg_bin" ]]; then
  for candidate in \
    "$(command -v ffmpeg 2>/dev/null || true)" \
    "/etc/profiles/per-user/$(id -un)/bin/ffmpeg" \
    "/run/current-system/sw/bin/ffmpeg" \
    "/opt/homebrew/bin/ffmpeg" \
    "/usr/local/bin/ffmpeg"; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      ffmpeg_bin=$candidate
      break
    fi
  done
fi

if [[ -z "$ffmpeg_bin" || ! -x "$ffmpeg_bin" ]]; then
  printf 'tts-router: ffmpeg was not found; set FFMPEG_BIN to an executable path\n' >&2
  exit 1
fi

for required in "$edge_helper" "$voicebox_bridge" "$config_python"; do
  if [[ ! -x "$required" && ! -f "$required" ]]; then
    printf 'tts_router: missing required helper: %s\n' "$required" >&2
    exit 1
  fi
done

route_json=$("$edge_helper" --text-file "$input_path" --dry-run --json)
detected_language=$(python3 -c 'import json, sys; print(json.load(sys.stdin)["detected_language"])' <<<"$route_json")

IFS=$'\x1f' read -r provider profile engine preset voicebox_language http_timeout poll_timeout edge_voice < <("$config_python" - "$detected_language" <<'PY'
import os
import sys
from pathlib import Path

import yaml

config_path = Path(
    os.environ.get(
        "TTS_ROUTING_CONFIG",
        os.environ.get("HERMES_TTS_ROUTING_CONFIG", Path.home() / ".llm-harness" / "scripts" / "tts" / "tts-routing.yaml"),
    )
)
routing = yaml.safe_load(config_path.read_text()) or {}
route = routing.get("languages", {}).get(sys.argv[1], routing.get("default", {}))
voicebox = route.get("voicebox", {})
edge = route.get("edge", {})
fields = (
    route.get("provider", "edge"),
    voicebox.get("profile", ""),
    voicebox.get("engine", ""),
    voicebox.get("preset_voice_id", ""),
    voicebox.get("language", ""),
    voicebox.get("http_timeout_seconds", "3"),
    voicebox.get("poll_timeout_seconds", "15"),
    edge.get("voice", ""),
)
print("\x1f".join(map(str, fields)))
PY
)

render_edge() {
  local voice=$1
  local tmp_base tmp_mp3
  tmp_base=$(mktemp "${TMPDIR:-/tmp}/tts-router.XXXXXX")
  tmp_mp3="${tmp_base}.mp3"
  trap 'rm -f "$tmp_base" "$tmp_mp3"' RETURN

  local args=(--text-file "$input_path" --output "$tmp_mp3" --gender female --json)
  if [[ -n "$voice" ]]; then
    args+=(--voice "$voice")
  fi
  "$edge_helper" "${args[@]}"
  "$ffmpeg_bin" -y -loglevel error -i "$tmp_mp3" "$output_path"
}

if [[ "$provider" == "voicebox" ]]; then
  if [[ -n "$profile" && -n "$engine" && -n "$preset" && -n "$voicebox_language" ]]; then
    if env \
      VOICEBOX_PROFILE_NAME="$profile" \
      VOICEBOX_ENGINE="$engine" \
      VOICEBOX_PRESET_VOICE_ID="$preset" \
      VOICEBOX_LANGUAGE="$voicebox_language" \
      VOICEBOX_HTTP_TIMEOUT_SECONDS="$http_timeout" \
      VOICEBOX_POLL_TIMEOUT_SECONDS="$poll_timeout" \
      python3 "$voicebox_bridge" "$input_path" "$output_path"; then
      exit 0
    fi
    printf 'tts_router: configured Voicebox route unavailable\n' >&2
  else
    printf 'tts_router: incomplete Voicebox route for language %s\n' "$detected_language" >&2
  fi

  exit 1
fi

if [[ "$provider" == "edge" ]]; then
  render_edge "$edge_voice"
  exit 0
fi

printf 'tts_router: unsupported provider %q for language %s\n' "$provider" "$detected_language" >&2
exit 1
