"""Generate audio pronunciation files for Chinese characters.

Supports two TTS backends:
  1. Azure Speech (default) — high-quality neural TTS via REST API
  2. gTTS (fallback) — free Google Translate TTS

Azure Speech requires environment variables:
  AZURE_SPEECH_KEY    — your Azure Speech resource key
  AZURE_SPEECH_REGION — your Azure region (e.g. eastus)
"""

from __future__ import annotations

import os
from pathlib import Path

import requests

# Azure Speech configuration
AZURE_VOICE = "zh-CN-XiaoxiaoNeural"  # clear, natural female Mandarin voice
AZURE_OUTPUT_FORMAT = "audio-24khz-96kbitrate-mono-mp3"


def char_to_filename(char: str) -> str:
    """Convert a character/word to a unique mp3 filename using Unicode codepoints."""
    codepoints = "_".join(f"{ord(c):04X}" for c in char)
    return f"char_{codepoints}.mp3"


def _get_azure_config() -> tuple[str, str] | None:
    """Return (key, region) if Azure Speech env vars are set, else None."""
    key = os.environ.get("AZURE_SPEECH_KEY")
    region = os.environ.get("AZURE_SPEECH_REGION")
    if key and region:
        return key, region
    return None


def _generate_audio_azure(char: str, filepath: Path, key: str, region: str) -> None:
    """Synthesize speech for a character using Azure Speech REST API."""
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

    ssml = (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
        f"xml:lang='zh-CN'><voice name='{AZURE_VOICE}'>{char}</voice></speak>"
    )

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": AZURE_OUTPUT_FORMAT,
        "User-Agent": "CPRFlashcards",
    }

    resp = requests.post(url, headers=headers, data=ssml.encode("utf-8"), timeout=30)
    resp.raise_for_status()

    filepath.write_bytes(resp.content)


def _generate_audio_gtts(char: str, filepath: Path) -> None:
    """Synthesize speech for a character using gTTS (fallback)."""
    from gtts import gTTS

    tts = gTTS(char, lang="zh-cn")
    tts.save(str(filepath))


def generate_audio(char: str, output_dir: Path) -> Path:
    """Generate an mp3 file for a single Chinese character.

    Uses Azure Speech if AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are set,
    otherwise falls back to gTTS.

    Args:
        char: A single Chinese character.
        output_dir: Directory to save the mp3 file.

    Returns:
        Path to the generated mp3 file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = char_to_filename(char)
    filepath = output_dir / filename

    if filepath.exists():
        return filepath

    azure_cfg = _get_azure_config()
    if azure_cfg:
        key, region = azure_cfg
        _generate_audio_azure(char, filepath, key, region)
    else:
        print("⚠️  AZURE_SPEECH_KEY/AZURE_SPEECH_REGION not set — falling back to gTTS")
        _generate_audio_gtts(char, filepath)

    return filepath


def generate_audio_batch(characters: list[str], output_dir: Path) -> dict[str, Path]:
    """Generate audio for a list of characters, skipping already-generated ones.

    Args:
        characters: List of Chinese characters.
        output_dir: Directory to save mp3 files.

    Returns:
        Dict mapping character → mp3 file path.
    """
    azure_cfg = _get_azure_config()
    backend = "Azure Speech" if azure_cfg else "gTTS"
    print(f"🔊 Audio backend: {backend}")
    if azure_cfg:
        print(f"   Voice: {AZURE_VOICE}")

    results: dict[str, Path] = {}
    for char in characters:
        results[char] = generate_audio(char, output_dir)
    return results
