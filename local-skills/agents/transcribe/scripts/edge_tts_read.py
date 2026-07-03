#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import edge_tts
import langid  # type: ignore[import-not-found]

PREFERRED_LOCALES: dict[str, list[str]] = {
    "ar": ["ar-EG", "ar-SA", "ar-AE"],
    "bn": ["bn-BD", "bn-IN"],
    "en": ["en-US", "en-GB", "en-AU", "en-IN"],
    "es": ["es-ES", "es-MX", "es-US", "es-AR"],
    "fr": ["fr-FR", "fr-CA", "fr-BE", "fr-CH"],
    "nl": ["nl-NL", "nl-BE"],
    "pt": ["pt-BR", "pt-PT"],
    "zh": ["zh-CN", "zh-TW", "zh-HK"],
    "sw": ["sw-KE", "sw-TZ"],
}

LANGUAGE_ALIASES = {
    "nb": "no",
    "nn": "no",
    "jw": "jv",
}

DEFAULT_RATE = "+0%"
DEFAULT_PITCH = "+0Hz"
DEFAULT_VOLUME = "+0%"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render multilingual Edge TTS audio with automatic language detection.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="Inline text to render")
    src.add_argument("--text-file", help="Path to UTF-8 text file to render")
    src.add_argument("--stdin", action="store_true", help="Read text from stdin")
    parser.add_argument("--output", help="Output mp3 path")
    parser.add_argument("--locale", help="Force locale like nl-NL or fr-FR")
    parser.add_argument("--voice", help="Force exact Edge voice short name like nl-NL-ColetteNeural")
    parser.add_argument("--gender", choices=["female", "male", "any"], default="female")
    parser.add_argument("--rate", default=DEFAULT_RATE, help="Edge TTS rate, e.g. -5%% or +10%%")
    parser.add_argument("--pitch", default=DEFAULT_PITCH, help="Edge TTS pitch, e.g. +0Hz")
    parser.add_argument("--volume", default=DEFAULT_VOLUME, help="Edge TTS volume, e.g. +0%%")
    parser.add_argument("--dry-run", action="store_true", help="Detect language and choose voice without rendering audio")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    return parser.parse_args()


def load_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text.strip()
    if args.text_file is not None:
        return Path(args.text_file).read_text(encoding="utf-8").strip()
    if args.stdin:
        return sys.stdin.read().strip()
    raise ValueError("No input text provided")


def normalize_lang_code(code: str) -> str:
    code = code.lower().strip()
    return LANGUAGE_ALIASES.get(code, code)


def build_output_path(text: str, locale: str) -> Path:
    cache_dir = Path.home() / ".hermes" / "audio_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    slug_source = re.sub(r"\s+", " ", text).strip()[:40].lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug_source).strip("-") or "tts"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return cache_dir / f"tts_{locale}_{slug}_{timestamp}.mp3"


def voice_language(locale: str) -> str:
    return normalize_lang_code(locale.split("-", 1)[0])


def score_voice(voice: dict[str, Any], gender: str) -> tuple[int, int, int, str]:
    voice_gender = str(voice.get("Gender", "")).lower()
    short_name = str(voice.get("ShortName", ""))
    status = str(voice.get("Status", ""))
    gender_score = 0
    if gender == "any":
        gender_score = 0
    elif voice_gender == gender:
        gender_score = 0
    else:
        gender_score = 1
    status_score = 0 if status == "GA" else 1
    multilingual_score = 1 if "Multilingual" in short_name else 0
    return (gender_score, status_score, multilingual_score, short_name)


def choose_locale_for_language(language: str, locales: list[str]) -> str:
    preferred = PREFERRED_LOCALES.get(language, [])
    for locale in preferred:
        if locale in locales:
            return locale
    return sorted(locales)[0]


def classify_language(text: str, available_languages: set[str]) -> tuple[str, float]:
    code, score = langid.classify(text)
    code = normalize_lang_code(code)
    if code in available_languages:
        return code, float(score)

    # langid can emit language codes that don't exactly match Edge locale prefixes.
    # Fall back to a prefix-style match when available.
    for candidate in sorted(available_languages):
        if candidate.startswith(code) or code.startswith(candidate):
            return candidate, float(score)

    raise RuntimeError(f"Detected language '{code}' is not supported by the current Edge voice catalog")


async def list_voices() -> Any:
    return await edge_tts.list_voices()


def choose_voice(
    voices: list[dict[str, Any]],
    detected_language: str,
    gender: str,
    forced_locale: str | None,
    forced_voice: str | None,
) -> tuple[str, dict[str, Any]]:
    if forced_voice:
        for voice in voices:
            if voice.get("ShortName") == forced_voice:
                return str(voice["Locale"]), voice
        raise RuntimeError(f"Requested voice not found: {forced_voice}")

    if forced_locale:
        locale = forced_locale
    else:
        locales = sorted({str(v["Locale"]) for v in voices if voice_language(str(v["Locale"])) == detected_language})
        if not locales:
            raise RuntimeError(f"No Edge locales found for detected language: {detected_language}")
        locale = choose_locale_for_language(detected_language, locales)

    locale_voices = [v for v in voices if str(v.get("Locale")) == locale]
    if not locale_voices:
        raise RuntimeError(f"No Edge voices found for locale: {locale}")

    locale_voices.sort(key=lambda v: score_voice(v, gender))
    return locale, locale_voices[0]


async def main() -> int:
    args = parse_args()
    text = load_text(args)
    if not text:
        raise RuntimeError("Input text is empty")

    voices = await list_voices()
    available_languages = {voice_language(str(v["Locale"])) for v in voices}
    detected_language, confidence = classify_language(text, available_languages)
    chosen_locale, chosen_voice = choose_voice(
        voices=voices,
        detected_language=detected_language,
        gender=args.gender,
        forced_locale=args.locale,
        forced_voice=args.voice,
    )

    output_path = Path(args.output) if args.output else build_output_path(text, chosen_locale)

    result = {
        "detected_language": detected_language,
        "confidence": confidence,
        "locale": chosen_locale,
        "voice": chosen_voice.get("ShortName"),
        "gender": chosen_voice.get("Gender"),
        "output_path": str(output_path),
        "text_length": len(text),
        "dry_run": bool(args.dry_run),
    }

    if not args.dry_run:
        communicate = edge_tts.Communicate(
            text,
            str(chosen_voice["ShortName"]),
            rate=args.rate,
            pitch=args.pitch,
            volume=args.volume,
        )
        await communicate.save(str(output_path))

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        for key, value in result.items():
            print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        message = {"error": str(exc)}
        print(json.dumps(message, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
