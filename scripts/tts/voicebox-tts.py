#!/usr/bin/env python3
import html
import json
import os
import re
import shutil
import sys
import time
import urllib.request

BASE = os.environ.get("VOICEBOX_BASE_URL", "http://127.0.0.1:17493")
DEFAULT_PROFILE_NAME = os.environ.get("VOICEBOX_PROFILE_NAME", "Hermes Bella")
DEFAULT_LANGUAGE = os.environ.get("VOICEBOX_LANGUAGE", "en")
DEFAULT_ENGINE = os.environ.get("VOICEBOX_ENGINE", "kokoro")
DEFAULT_PRESET_VOICE_ID = os.environ.get("VOICEBOX_PRESET_VOICE_ID", "af_bella")
HTTP_TIMEOUT_SECONDS = float(os.environ.get("VOICEBOX_HTTP_TIMEOUT_SECONDS", "120"))
POLL_TIMEOUT_SECONDS = int(os.environ.get("VOICEBOX_POLL_TIMEOUT_SECONDS", "180"))
DATA_DIR = os.environ.get(
    "VOICEBOX_DATA_DIR",
    os.path.expanduser("~/Library/Application Support/Voicebox"),
)
HEADERS = {"Content-Type": "application/json"}


def http_json(method: str, path: str, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers=HEADERS,
        method=method,
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
        body = resp.read().decode("utf-8")
        if not body:
            return None
        return json.loads(body)


def ensure_profile():
    profiles = http_json("GET", "/profiles") or []
    for profile in profiles:
        if profile.get("name") == DEFAULT_PROFILE_NAME:
            return profile["id"]
    profile = http_json(
        "POST",
        "/profiles",
        {
            "name": DEFAULT_PROFILE_NAME,
            "description": "Hermes Voicebox TTS default preset profile",
            "language": DEFAULT_LANGUAGE,
            "voice_type": "preset",
            "preset_engine": DEFAULT_ENGINE,
            "preset_voice_id": DEFAULT_PRESET_VOICE_ID,
            "default_engine": DEFAULT_ENGINE,
        },
    )
    return profile["id"]


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def sanitize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?im)^\s*MEDIA:[^\n]+$", " ", text)
    text = re.sub(r"(?is)<media\b[^>]*>.*?</media>", " ", text)
    text = re.sub(r"(?i)</?media\b[^>]*>", " ", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", lambda m: (m.group(1) or "image").strip() or "image", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<https?://[^>]+>", " ", text)
    text = re.sub(r"</?[A-Za-z][^>]*>", " ", text)
    text = text.replace("```", " ").replace("`", " ")
    text = text.replace("**", "").replace("__", " ").replace("~~", "").replace("||", "")
    text = text.replace("*", "").replace("_", " ")
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*>+\s?", "", text)
    text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)
    text = re.sub(r"(?m)^\s*\d+\.\s+", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def poll_generation(gen_id: str):
    for _ in range(POLL_TIMEOUT_SECONDS):
        with urllib.request.urlopen(BASE + f"/generate/{gen_id}/status", timeout=HTTP_TIMEOUT_SECONDS) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
        if "data:" in payload:
            line = payload.split("data:", 1)[1].strip().splitlines()[0].strip()
            status = json.loads(line)
        else:
            status = json.loads(payload)
        state = status.get("status")
        if state in {"completed", "failed", "error", "cancelled"}:
            return status
        time.sleep(1)
    raise TimeoutError("Voicebox generation timed out")


def resolve_audio_path(gen_id: str) -> str:
    entry = http_json("GET", f"/history/{gen_id}")
    rel = entry.get("audio_path")
    if not rel:
        raise RuntimeError("Voicebox generation completed without audio_path")
    if os.path.isabs(rel):
        return rel
    return os.path.join(DATA_DIR, rel)


def main():
    if len(sys.argv) != 3:
        print("usage: voicebox_tts.py <input_path> <output_path>", file=sys.stderr)
        sys.exit(2)

    input_path, output_path = sys.argv[1], sys.argv[2]
    raw_text = read_text(input_path)
    text = sanitize_text(raw_text)
    if not text:
        raise RuntimeError("Input text was empty after sanitization")

    profile_id = ensure_profile()
    gen = http_json(
        "POST",
        "/speak",
        {
            "text": text,
            "profile": profile_id,
            "engine": DEFAULT_ENGINE,
            "language": DEFAULT_LANGUAGE,
        },
    )
    gen_id = gen["id"]
    status = poll_generation(gen_id)
    if status.get("status") != "completed":
        raise RuntimeError(status.get("error") or f"Voicebox status={status.get('status')}")

    audio_path = resolve_audio_path(gen_id)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    shutil.copyfile(audio_path, output_path)
    print(output_path)


if __name__ == "__main__":
    main()
